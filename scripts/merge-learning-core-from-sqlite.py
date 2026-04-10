from __future__ import annotations

import argparse
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from dotenv import dotenv_values
from sqlalchemy import MetaData, Table, and_, create_engine, select


LEARNING_CORE_SERVICE_NAME = 'learning-core-service'
DEFAULT_ENV_FILE = Path('/etc/ielts-vocab/microservices.env')

STATE_TABLE_SPECS: dict[str, tuple[str, ...]] = {
    'user_progress': ('user_id', 'day'),
    'user_added_books': ('user_id', 'book_id'),
    'user_book_progress': ('user_id', 'book_id'),
    'user_chapter_progress': ('user_id', 'book_id', 'chapter_id'),
    'user_chapter_mode_progress': ('user_id', 'book_id', 'chapter_id', 'mode'),
    'user_favorite_words': ('user_id', 'normalized_word'),
    'user_familiar_words': ('user_id', 'normalized_word'),
    'user_wrong_words': ('user_id', 'word'),
    'user_quick_memory_records': ('user_id', 'word'),
    'user_smart_word_stats': ('user_id', 'word'),
}

MERGE_TABLE_ORDER = (
    'user_progress',
    'user_added_books',
    'user_book_progress',
    'user_chapter_progress',
    'user_chapter_mode_progress',
    'user_favorite_words',
    'user_familiar_words',
    'user_wrong_words',
    'user_quick_memory_records',
    'user_smart_word_stats',
    'user_study_sessions',
    'user_learning_events',
)

WRONG_WORD_DIMENSIONS = ('recognition', 'meaning', 'listening', 'dictation')


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description='Merge learning-core state from a SQLite snapshot into a live target database.',
    )
    parser.add_argument(
        '--source-sqlite',
        required=True,
        help='Path to the source SQLite database snapshot.',
    )
    parser.add_argument(
        '--env-file',
        default=str(DEFAULT_ENV_FILE),
        help='Env file that contains LEARNING_CORE_SERVICE_DATABASE_URL.',
    )
    parser.add_argument(
        '--target-url',
        default='',
        help='Explicit target database URL. Overrides --env-file when provided.',
    )
    parser.add_argument(
        '--passes',
        type=int,
        default=2,
        help='How many merge passes to run against the live target.',
    )
    parser.add_argument(
        '--sleep-between',
        type=float,
        default=2.0,
        help='Seconds to sleep between passes.',
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Compute merge results without mutating the target database.',
    )
    return parser.parse_args()


def load_target_database_url(*, target_url: str, env_file: Path) -> str:
    if target_url.strip():
        return target_url.strip()

    env_values = dotenv_values(env_file)
    prefix = LEARNING_CORE_SERVICE_NAME.replace('-', '_').upper()
    for key in (f'{prefix}_SQLALCHEMY_DATABASE_URI', f'{prefix}_DATABASE_URL'):
        value = env_values.get(key)
        if value:
            return value
    raise RuntimeError(f'Missing learning-core database URL in {env_file}')


def reflect_tables(engine, table_names: tuple[str, ...]) -> dict[str, Table]:
    metadata = MetaData()
    return {
        name: Table(name, metadata, autoload_with=engine)
        for name in table_names
    }


def _normalize_text(value: Any) -> str:
    if value is None:
        return ''
    return str(value).strip()


def _truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value in (0, 1):
        return bool(value)
    return str(value).strip().lower() in {'1', 'true', 'yes'}


def _safe_int(value: Any) -> int:
    if value in (None, ''):
        return 0
    return int(value)


def _parse_datetime(value: Any) -> datetime | None:
    if value in (None, ''):
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        text = text.replace('Z', '+00:00')
        try:
            return datetime.fromisoformat(text)
        except ValueError:
            return None
    return None


def _min_datetime_value(*values: Any) -> datetime | None:
    parsed = [item for item in (_parse_datetime(value) for value in values) if item is not None]
    return min(parsed) if parsed else None


def _max_datetime_value(*values: Any) -> datetime | None:
    parsed = [item for item in (_parse_datetime(value) for value in values) if item is not None]
    return max(parsed) if parsed else None


def _min_positive_int(*values: Any) -> int:
    positive = [item for item in (_safe_int(value) for value in values) if item > 0]
    return min(positive) if positive else 0


def _prefer_non_empty(target_value: Any, source_value: Any) -> Any:
    return target_value if _normalize_text(target_value) else source_value


def _pick_latest_row(source_row: dict[str, Any], target_row: dict[str, Any]) -> dict[str, Any]:
    source_score = (_safe_int(source_row.get('last_seen')), _safe_int(source_row.get('next_review')))
    target_score = (_safe_int(target_row.get('last_seen')), _safe_int(target_row.get('next_review')))
    return source_row if source_score > target_score else target_row


def _normalize_dimension_state(raw_value: Any) -> dict[str, dict[str, Any]]:
    if isinstance(raw_value, str):
        text = raw_value.strip()
        if text:
            try:
                raw_value = json.loads(text)
            except json.JSONDecodeError:
                raw_value = {}
    if not isinstance(raw_value, dict):
        raw_value = {}

    normalized: dict[str, dict[str, Any]] = {}
    for dimension in WRONG_WORD_DIMENSIONS:
        payload = raw_value.get(dimension)
        payload = payload if isinstance(payload, dict) else {}
        normalized[dimension] = {
            'history_wrong': max(0, _safe_int(payload.get('history_wrong'))),
            'pass_streak': max(0, _safe_int(payload.get('pass_streak'))),
            'last_wrong_at': _max_datetime_value(payload.get('last_wrong_at')),
            'last_pass_at': _max_datetime_value(payload.get('last_pass_at')),
        }
    return normalized


def _merge_dimension_state(source_value: Any, target_value: Any) -> str:
    source_state = _normalize_dimension_state(source_value)
    target_state = _normalize_dimension_state(target_value)
    merged: dict[str, dict[str, Any]] = {}
    for dimension in WRONG_WORD_DIMENSIONS:
        source_payload = source_state[dimension]
        target_payload = target_state[dimension]
        last_wrong_at = _max_datetime_value(
            source_payload['last_wrong_at'],
            target_payload['last_wrong_at'],
        )
        last_pass_at = _max_datetime_value(
            source_payload['last_pass_at'],
            target_payload['last_pass_at'],
        )
        merged[dimension] = {
            'history_wrong': max(
                source_payload['history_wrong'],
                target_payload['history_wrong'],
            ),
            'pass_streak': max(
                source_payload['pass_streak'],
                target_payload['pass_streak'],
            ),
            'last_wrong_at': last_wrong_at.isoformat() if last_wrong_at else None,
            'last_pass_at': last_pass_at.isoformat() if last_pass_at else None,
        }
    return json.dumps(merged, ensure_ascii=False, sort_keys=True)


def build_state_merge_payload(table_name: str, source_row: dict[str, Any], target_row: dict[str, Any]) -> dict[str, Any]:
    merged = dict(target_row)
    merged.update({key: source_row[key] for key in STATE_TABLE_SPECS[table_name]})

    if table_name == 'user_added_books':
        merged['added_at'] = _min_datetime_value(source_row.get('added_at'), target_row.get('added_at'))
        return merged

    if table_name == 'user_progress':
        for field in ('current_index', 'correct_count', 'wrong_count'):
            merged[field] = max(_safe_int(source_row.get(field)), _safe_int(target_row.get(field)))
        merged['updated_at'] = _max_datetime_value(source_row.get('updated_at'), target_row.get('updated_at'))
        return merged

    if table_name in {'user_book_progress', 'user_chapter_progress', 'user_chapter_mode_progress'}:
        numeric_fields = ['correct_count', 'wrong_count']
        if table_name == 'user_book_progress':
            numeric_fields = ['current_index', 'correct_count', 'wrong_count']
        if table_name == 'user_chapter_progress':
            numeric_fields = ['words_learned', 'correct_count', 'wrong_count']
        for field in numeric_fields:
            merged[field] = max(_safe_int(source_row.get(field)), _safe_int(target_row.get(field)))
        merged['is_completed'] = _truthy(source_row.get('is_completed')) or _truthy(target_row.get('is_completed'))
        merged['updated_at'] = _max_datetime_value(source_row.get('updated_at'), target_row.get('updated_at'))
        return merged

    if table_name in {'user_favorite_words', 'user_familiar_words'}:
        for field in (
            'word',
            'normalized_word',
            'phonetic',
            'pos',
            'definition',
            'source_book_id',
            'source_book_title',
            'source_chapter_id',
            'source_chapter_title',
        ):
            merged[field] = _prefer_non_empty(target_row.get(field), source_row.get(field))
        merged['created_at'] = _min_datetime_value(source_row.get('created_at'), target_row.get('created_at'))
        merged['updated_at'] = _max_datetime_value(source_row.get('updated_at'), target_row.get('updated_at'))
        return merged

    if table_name == 'user_wrong_words':
        for field in (
            'phonetic',
            'pos',
            'definition',
        ):
            merged[field] = _prefer_non_empty(target_row.get(field), source_row.get(field))
        for field in (
            'wrong_count',
            'listening_correct',
            'listening_wrong',
            'meaning_correct',
            'meaning_wrong',
            'dictation_correct',
            'dictation_wrong',
        ):
            merged[field] = max(_safe_int(source_row.get(field)), _safe_int(target_row.get(field)))
        merged['dimension_state'] = _merge_dimension_state(
            source_row.get('dimension_state'),
            target_row.get('dimension_state'),
        )
        merged['updated_at'] = _max_datetime_value(source_row.get('updated_at'), target_row.get('updated_at'))
        return merged

    if table_name == 'user_quick_memory_records':
        latest_row = _pick_latest_row(source_row, target_row)
        fallback_row = target_row if latest_row is source_row else source_row
        for field in ('book_id', 'chapter_id', 'status'):
            merged[field] = _prefer_non_empty(latest_row.get(field), fallback_row.get(field))
        merged['first_seen'] = _min_positive_int(source_row.get('first_seen'), target_row.get('first_seen'))
        merged['last_seen'] = max(_safe_int(source_row.get('last_seen')), _safe_int(target_row.get('last_seen')))
        merged['known_count'] = max(_safe_int(source_row.get('known_count')), _safe_int(target_row.get('known_count')))
        merged['unknown_count'] = max(_safe_int(source_row.get('unknown_count')), _safe_int(target_row.get('unknown_count')))
        merged['next_review'] = max(_safe_int(source_row.get('next_review')), _safe_int(target_row.get('next_review')))
        merged['fuzzy_count'] = max(_safe_int(source_row.get('fuzzy_count')), _safe_int(target_row.get('fuzzy_count')))
        return merged

    if table_name == 'user_smart_word_stats':
        for field in (
            'listening_correct',
            'listening_wrong',
            'meaning_correct',
            'meaning_wrong',
            'dictation_correct',
            'dictation_wrong',
        ):
            merged[field] = max(_safe_int(source_row.get(field)), _safe_int(target_row.get(field)))
        merged['updated_at'] = _max_datetime_value(source_row.get('updated_at'), target_row.get('updated_at'))
        return merged

    raise KeyError(f'Unsupported state table: {table_name}')


def _canonical_json_text(value: Any) -> str:
    if value in (None, ''):
        return ''
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return ''
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            return text
        return json.dumps(parsed, ensure_ascii=False, sort_keys=True)
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def build_append_signature(table_name: str, row: dict[str, Any]) -> tuple[Any, ...]:
    if table_name == 'user_study_sessions':
        return (
            _safe_int(row.get('user_id')),
            _normalize_text(row.get('mode')),
            _normalize_text(row.get('book_id')),
            _normalize_text(row.get('chapter_id')),
            _safe_int(row.get('words_studied')),
            _safe_int(row.get('correct_count')),
            _safe_int(row.get('wrong_count')),
            _safe_int(row.get('duration_seconds')),
            _parse_datetime(row.get('started_at')),
            _parse_datetime(row.get('ended_at')),
        )
    if table_name == 'user_learning_events':
        return (
            _safe_int(row.get('user_id')),
            _normalize_text(row.get('event_type')),
            _normalize_text(row.get('source')),
            _normalize_text(row.get('mode')),
            _normalize_text(row.get('book_id')),
            _normalize_text(row.get('chapter_id')),
            _normalize_text(row.get('word')),
            _safe_int(row.get('item_count')),
            _safe_int(row.get('correct_count')),
            _safe_int(row.get('wrong_count')),
            _safe_int(row.get('duration_seconds')),
            _canonical_json_text(row.get('payload')),
            _parse_datetime(row.get('occurred_at')),
        )
    raise KeyError(f'Unsupported append table: {table_name}')


def _normalize_for_compare(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, str):
        text = value.strip()
        if text.startswith('{') or text.startswith('['):
            return _canonical_json_text(text)
        return text
    if isinstance(value, bool):
        return bool(value)
    return value


def _rows_differ(payload: dict[str, Any], target_row: dict[str, Any]) -> bool:
    for key, value in payload.items():
        if key == 'id':
            continue
        if _normalize_for_compare(value) != _normalize_for_compare(target_row.get(key)):
            return True
    return False


def _coerce_value(column, value: Any) -> Any:
    if value is None:
        return None
    type_name = column.type.__class__.__name__.lower()
    if 'date' in type_name or 'time' in type_name:
        return _parse_datetime(value)
    if 'bool' in type_name:
        return _truthy(value)
    if any(token in type_name for token in ('int', 'numeric', 'float')):
        return _safe_int(value)
    if column.name in {'dimension_state', 'payload'}:
        return _canonical_json_text(value)
    return value


def _prepare_values(table: Table, row: dict[str, Any]) -> dict[str, Any]:
    values: dict[str, Any] = {}
    for column in table.columns:
        if column.name == 'id':
            continue
        if column.name not in row:
            continue
        values[column.name] = _coerce_value(column, row[column.name])
    return values


def _build_key_filter(table: Table, key_fields: tuple[str, ...], row: dict[str, Any]):
    clauses = [table.c[field] == row[field] for field in key_fields]
    return and_(*clauses)


def _validate_target_users(source_tables: dict[str, Table], target_tables: dict[str, Table], source_engine, target_engine) -> None:
    if 'users' not in target_tables:
        return

    source_user_ids: set[int] = set()
    with source_engine.connect() as source_connection:
        for table_name in MERGE_TABLE_ORDER:
            table = source_tables.get(table_name)
            if table is None or 'user_id' not in table.c:
                continue
            for row in source_connection.execute(select(table.c.user_id)).mappings():
                source_user_ids.add(_safe_int(row['user_id']))

    with target_engine.connect() as target_connection:
        target_user_ids = {
            _safe_int(row['id'])
            for row in target_connection.execute(select(target_tables['users'].c.id)).mappings()
        }

    missing_user_ids = sorted(user_id for user_id in source_user_ids if user_id not in target_user_ids)
    if missing_user_ids:
        raise RuntimeError(
            'Target users table is missing source user IDs: '
            + ', '.join(str(item) for item in missing_user_ids[:20])
        )


def merge_state_table(*, table_name: str, source_table: Table, target_table: Table, source_connection, target_connection, dry_run: bool) -> dict[str, int]:
    key_fields = STATE_TABLE_SPECS[table_name]
    stats = {'inserted': 0, 'updated': 0, 'skipped': 0}
    target_rows = {
        tuple(row[field] for field in key_fields): dict(row)
        for row in target_connection.execute(select(target_table)).mappings()
    }

    for source_row_raw in source_connection.execute(select(source_table)).mappings():
        source_row = dict(source_row_raw)
        key = tuple(source_row[field] for field in key_fields)
        target_row = target_rows.get(key)
        if target_row is None:
            stats['inserted'] += 1
            target_rows[key] = dict(source_row)
            if not dry_run:
                target_connection.execute(target_table.insert().values(**_prepare_values(target_table, source_row)))
            continue

        merged_row = build_state_merge_payload(table_name, source_row, target_row)
        if not _rows_differ(merged_row, target_row):
            stats['skipped'] += 1
            continue

        stats['updated'] += 1
        target_rows[key] = dict(merged_row)
        if not dry_run:
            target_connection.execute(
                target_table.update()
                .where(_build_key_filter(target_table, key_fields, source_row))
                .values(**_prepare_values(target_table, merged_row))
            )

    return stats


def merge_append_table(*, table_name: str, source_table: Table, target_table: Table, source_connection, target_connection, dry_run: bool) -> dict[str, int]:
    stats = {'inserted': 0, 'updated': 0, 'skipped': 0}
    existing_signatures = {
        build_append_signature(table_name, dict(row))
        for row in target_connection.execute(select(target_table)).mappings()
    }

    for source_row_raw in source_connection.execute(select(source_table)).mappings():
        source_row = dict(source_row_raw)
        signature = build_append_signature(table_name, source_row)
        if signature in existing_signatures:
            stats['skipped'] += 1
            continue
        stats['inserted'] += 1
        existing_signatures.add(signature)
        if not dry_run:
            target_connection.execute(target_table.insert().values(**_prepare_values(target_table, source_row)))

    return stats


def run_merge_pass(*, source_engine, target_engine, tables: dict[str, Table], dry_run: bool) -> dict[str, dict[str, int]]:
    results: dict[str, dict[str, int]] = {}
    with source_engine.connect() as source_connection, target_engine.begin() as target_connection:
        for table_name in MERGE_TABLE_ORDER:
            source_table = tables[f'source:{table_name}']
            target_table = tables[f'target:{table_name}']
            if table_name in STATE_TABLE_SPECS:
                stats = merge_state_table(
                    table_name=table_name,
                    source_table=source_table,
                    target_table=target_table,
                    source_connection=source_connection,
                    target_connection=target_connection,
                    dry_run=dry_run,
                )
            else:
                stats = merge_append_table(
                    table_name=table_name,
                    source_table=source_table,
                    target_table=target_table,
                    source_connection=source_connection,
                    target_connection=target_connection,
                    dry_run=dry_run,
                )
            results[table_name] = stats
    return results


def main() -> int:
    args = parse_args()
    source_sqlite = Path(args.source_sqlite).resolve()
    env_file = Path(args.env_file).resolve()
    target_url = load_target_database_url(target_url=args.target_url, env_file=env_file)

    if not source_sqlite.exists():
        raise FileNotFoundError(f'Source SQLite not found: {source_sqlite}')

    source_engine = create_engine(f'sqlite:///{source_sqlite.as_posix()}')
    target_engine = create_engine(target_url)

    source_tables = reflect_tables(source_engine, MERGE_TABLE_ORDER)
    target_tables = reflect_tables(target_engine, MERGE_TABLE_ORDER + ('users',))
    merged_tables = {
        **{f'source:{name}': table for name, table in source_tables.items()},
        **{f'target:{name}': table for name, table in target_tables.items() if name in MERGE_TABLE_ORDER},
    }

    _validate_target_users(source_tables, target_tables, source_engine, target_engine)

    for pass_index in range(1, max(1, args.passes) + 1):
        print(f'=== Pass {pass_index}/{max(1, args.passes)} ===')
        results = run_merge_pass(
            source_engine=source_engine,
            target_engine=target_engine,
            tables=merged_tables,
            dry_run=args.dry_run,
        )
        for table_name in MERGE_TABLE_ORDER:
            stats = results[table_name]
            print(
                f'{table_name}: '
                f"inserted={stats['inserted']} "
                f"updated={stats['updated']} "
                f"skipped={stats['skipped']}"
            )
        if pass_index < args.passes and args.sleep_between > 0:
            time.sleep(args.sleep_between)

    return 0


if __name__ == '__main__':
    raise SystemExit(main())
