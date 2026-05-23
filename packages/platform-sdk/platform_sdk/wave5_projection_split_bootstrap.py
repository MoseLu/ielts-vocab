from __future__ import annotations

from datetime import datetime
from pathlib import Path

import sqlalchemy as sa

from platform_sdk.wave5_projection_split_verification import (
    BOOTSTRAP_TOPIC,
    GROUP_SPECS,
    _resolve_database_uris,
)


STUDY_SESSION_COLUMNS = (
    'id',
    'user_id',
    'mode',
    'book_id',
    'chapter_id',
    'words_studied',
    'correct_count',
    'wrong_count',
    'duration_seconds',
    'started_at',
    'ended_at',
)
WRONG_WORD_COLUMNS = (
    'user_id',
    'word',
    'phonetic',
    'pos',
    'definition',
    'wrong_count',
    'listening_correct',
    'listening_wrong',
    'meaning_correct',
    'meaning_wrong',
    'dictation_correct',
    'dictation_wrong',
    'dimension_state',
    'updated_at',
)
USER_COLUMNS = ('id', 'email', 'username', 'avatar_url', 'is_admin', 'created_at')
DAILY_SUMMARY_COLUMNS = ('id', 'user_id', 'date', 'content', 'generated_at')


def _fetch_rows(
    connection: sa.engine.Connection,
    *,
    table_name: str,
    columns: tuple[str, ...],
) -> list[dict[str, object]]:
    column_sql = ', '.join(columns)
    rows = connection.execute(sa.text(f'SELECT {column_sql} FROM {table_name}')).all()
    return [dict(row._mapping) for row in rows]


def _projected_rows(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    now = datetime.utcnow()
    return [dict(row, projected_at=now) for row in rows]


def _upsert_rows(
    connection: sa.engine.Connection,
    *,
    table_name: str,
    rows: list[dict[str, object]],
    key_columns: tuple[str, ...],
) -> dict[str, int]:
    inserted = 0
    updated = 0
    source_keys = {tuple(row[column] for column in key_columns) for row in rows}
    for row in rows:
        update_columns = tuple(column for column in row if column not in key_columns)
        set_sql = ', '.join(f'{column} = :{column}' for column in update_columns)
        where_sql = ' AND '.join(f'{column} = :{column}' for column in key_columns)
        result = connection.execute(
            sa.text(f'UPDATE {table_name} SET {set_sql} WHERE {where_sql}'),
            row,
        )
        if int(result.rowcount or 0) > 0:
            updated += 1
            continue

        columns_sql = ', '.join(row.keys())
        values_sql = ', '.join(f':{column}' for column in row)
        connection.execute(
            sa.text(f'INSERT INTO {table_name} ({columns_sql}) VALUES ({values_sql})'),
            row,
        )
        inserted += 1

    pruned = _prune_stale_rows(
        connection,
        table_name=table_name,
        source_keys=source_keys,
        key_columns=key_columns,
    )
    return {
        'source_count': len(rows),
        'inserted': inserted,
        'updated': updated,
        'pruned': pruned,
    }


def _prune_stale_rows(
    connection: sa.engine.Connection,
    *,
    table_name: str,
    source_keys: set[tuple[object, ...]],
    key_columns: tuple[str, ...],
) -> int:
    columns_sql = ', '.join(key_columns)
    target_keys = connection.execute(sa.text(f'SELECT {columns_sql} FROM {table_name}')).all()
    pruned = 0
    where_sql = ' AND '.join(f'{column} = :{column}' for column in key_columns)
    for target_key in target_keys:
        key_tuple = tuple(target_key)
        if key_tuple in source_keys:
            continue
        params = {
            column: key_tuple[index]
            for index, column in enumerate(key_columns)
        }
        result = connection.execute(
            sa.text(f'DELETE FROM {table_name} WHERE {where_sql}'),
            params,
        )
        pruned += int(result.rowcount or 0)
    return pruned


def _touch_projection_cursor(
    connection: sa.engine.Connection,
    *,
    cursor_table: str,
    projection_name: str,
) -> None:
    now = datetime.utcnow()
    event_id = f'split-bootstrap:{projection_name}:{now.strftime("%Y%m%d%H%M%S")}'
    for cursor_name in (projection_name, f'{projection_name}.bootstrap'):
        payload = {
            'projection_name': cursor_name,
            'last_event_id': event_id,
            'last_topic': BOOTSTRAP_TOPIC,
            'last_processed_at': now,
        }
        result = connection.execute(
            sa.text(
                f'''
                UPDATE {cursor_table}
                SET last_event_id = :last_event_id,
                    last_topic = :last_topic,
                    last_processed_at = :last_processed_at
                WHERE projection_name = :projection_name
                '''
            ),
            payload,
        )
        if int(result.rowcount or 0) > 0:
            continue
        connection.execute(
            sa.text(
                f'''
                INSERT INTO {cursor_table}
                    (projection_name, last_event_id, last_topic, last_processed_at)
                VALUES
                    (:projection_name, :last_event_id, :last_topic, :last_processed_at)
                '''
            ),
            payload,
        )


def bootstrap_split_runtime_projections(*, env_file: Path | None = None) -> dict[str, object]:
    engines = {
        service_name: sa.create_engine(uri)
        for service_name, uri in _resolve_database_uris(env_file=env_file).items()
    }
    source_connections = {
        service_name: engine.connect()
        for service_name, engine in engines.items()
    }
    try:
        learning = source_connections['learning-core-service']
        admin_source = source_connections['admin-ops-service']
        notes_source = source_connections['notes-service']
        study_sessions = _projected_rows(
            _fetch_rows(learning, table_name='user_study_sessions', columns=STUDY_SESSION_COLUMNS)
        )
        wrong_words = _projected_rows(
            _fetch_rows(learning, table_name='user_wrong_words', columns=WRONG_WORD_COLUMNS)
        )
        admin_users = _projected_rows(
            _fetch_rows(admin_source, table_name='users', columns=USER_COLUMNS)
        )
        daily_summaries = _projected_rows(
            _fetch_rows(notes_source, table_name='user_daily_summaries', columns=DAILY_SUMMARY_COLUMNS)
        )

        return {
            'admin': _bootstrap_admin(engines['admin-ops-service'], admin_users, study_sessions, wrong_words),
            'notes': _bootstrap_notes(engines['notes-service'], study_sessions, wrong_words),
            'ai': _bootstrap_ai(engines['ai-execution-service'], wrong_words, daily_summaries),
        }
    finally:
        for connection in source_connections.values():
            connection.close()
        for engine in engines.values():
            engine.dispose()


def _bootstrap_admin(
    engine: sa.engine.Engine,
    users: list[dict[str, object]],
    study_sessions: list[dict[str, object]],
    wrong_words: list[dict[str, object]],
) -> dict[str, dict[str, int]]:
    with engine.begin() as target:
        summary = {
            'user_directory': _upsert_rows(
                target,
                table_name='admin_projected_users',
                rows=users,
                key_columns=('id',),
            ),
            'study_sessions': _upsert_rows(
                target,
                table_name='admin_projected_study_sessions',
                rows=study_sessions,
                key_columns=('id',),
            ),
            'wrong_words': _upsert_rows(
                target,
                table_name='admin_projected_wrong_words',
                rows=wrong_words,
                key_columns=('user_id', 'word'),
            ),
        }
        for spec in GROUP_SPECS['admin'].values():
            _touch_projection_cursor(
                target,
                cursor_table=spec.cursor.table_name,
                projection_name=spec.projection_name,
            )
        return summary


def _bootstrap_notes(
    engine: sa.engine.Engine,
    study_sessions: list[dict[str, object]],
    wrong_words: list[dict[str, object]],
) -> dict[str, dict[str, int]]:
    with engine.begin() as target:
        summary = {
            'study_sessions': _upsert_rows(
                target,
                table_name='notes_projected_study_sessions',
                rows=study_sessions,
                key_columns=('id',),
            ),
            'wrong_words': _upsert_rows(
                target,
                table_name='notes_projected_wrong_words',
                rows=wrong_words,
                key_columns=('user_id', 'word'),
            ),
        }
        for spec in GROUP_SPECS['notes'].values():
            _touch_projection_cursor(
                target,
                cursor_table=spec.cursor.table_name,
                projection_name=spec.projection_name,
            )
        return summary


def _bootstrap_ai(
    engine: sa.engine.Engine,
    wrong_words: list[dict[str, object]],
    daily_summaries: list[dict[str, object]],
) -> dict[str, dict[str, int]]:
    with engine.begin() as target:
        summary = {
            'wrong_words': _upsert_rows(
                target,
                table_name='ai_projected_wrong_words',
                rows=wrong_words,
                key_columns=('user_id', 'word'),
            ),
            'daily_summaries': _upsert_rows(
                target,
                table_name='ai_projected_daily_summaries',
                rows=daily_summaries,
                key_columns=('id',),
            ),
        }
        for spec in GROUP_SPECS['ai'].values():
            _touch_projection_cursor(
                target,
                cursor_table=spec.cursor.table_name,
                projection_name=spec.projection_name,
            )
        return summary
