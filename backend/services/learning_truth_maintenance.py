from __future__ import annotations

from collections import defaultdict
from datetime import datetime

from service_models.learning_core_models import (
    UserLearningDailyLedger,
    UserQuickMemoryRecord,
    UserSmartWordStat,
    UserStudySession,
    UserWordMasteryState,
    UserWrongWord,
    db,
)
from services.word_mastery_service import get_or_create_word_mastery_state
from services.word_mastery_support import (
    WORD_MASTERY_DIMENSIONS,
    WORD_MASTERY_TARGET_STREAK,
    build_legacy_source_maps,
    dimension_state_summary,
    dimension_states_from_record,
    legacy_states_for_word,
    normalize_word_key,
    normalize_word_text,
    scope_key,
    serialize_pending_dimensions,
    serialize_states,
    utc_now,
)


def _safe_int(value) -> int:
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return 0


def _normalize_user_ids(user_ids) -> list[int] | None:
    if user_ids is None:
        return None
    return sorted({int(value) for value in user_ids if value is not None})


def _query(model, user_ids: list[int] | None):
    query = model.query
    if user_ids is not None:
        query = query.filter(model.user_id.in_(user_ids))
    return query


def _collect_user_ids() -> list[int]:
    user_ids: set[int] = set()
    for model in (
        UserQuickMemoryRecord,
        UserWrongWord,
        UserSmartWordStat,
        UserWordMasteryState,
        UserLearningDailyLedger,
        UserStudySession,
    ):
        for row in db.session.query(model.user_id).distinct().all():
            if row[0] is not None:
                user_ids.add(int(row[0]))
    return sorted(user_ids)


def _empty_entry(user_id: int, word: str) -> dict:
    return {
        'user_id': user_id,
        'word': normalize_word_text(word),
        'book_id': None,
        'chapter_id': None,
        'sources': set(),
    }


def _legacy_entries(user_ids: list[int] | None) -> tuple[list[dict], dict]:
    entries: dict[tuple[int, str], dict] = {}
    source_counts = {'quick_memory': 0, 'smart_stats': 0, 'wrong_words': 0}

    def add(user_id: int, word: str, source: str, book_id=None, chapter_id=None) -> None:
        word_key = normalize_word_key(word)
        if not word_key:
            return
        entry = entries.setdefault((user_id, word_key), _empty_entry(user_id, word))
        entry['sources'].add(source)
        if book_id and not entry.get('book_id'):
            entry['book_id'] = str(book_id)
        if chapter_id and not entry.get('chapter_id'):
            entry['chapter_id'] = str(chapter_id)

    for row in _query(UserQuickMemoryRecord, user_ids).all():
        source_counts['quick_memory'] += 1
        add(row.user_id, row.word, 'quick_memory', row.book_id, row.chapter_id)
    for row in _query(UserWrongWord, user_ids).all():
        source_counts['wrong_words'] += 1
        add(row.user_id, row.word, 'wrong_words')
    for row in _query(UserSmartWordStat, user_ids).all():
        source_counts['smart_stats'] += 1
        add(row.user_id, row.word, 'smart_stats')

    result = []
    for entry in entries.values():
        result.append({
            **entry,
            'sources': sorted(entry['sources']),
        })
    result.sort(key=lambda item: (item['user_id'], normalize_word_key(item['word'])))
    return result, source_counts


def _sum_fields(rows, field_names: tuple[str, ...]) -> dict:
    totals = {'rows': 0}
    totals.update({field_name: 0 for field_name in field_names})
    for row in rows:
        totals['rows'] += 1
        for field_name in field_names:
            totals[field_name] += _safe_int(getattr(row, field_name, 0))
    return totals


def _ledger_totals(user_ids: list[int] | None) -> dict:
    return _sum_fields(
        _query(UserLearningDailyLedger, user_ids).all(),
        (
            'duration_seconds',
            'items_studied',
            'review_count',
            'correct_count',
            'wrong_count',
            'session_count',
        ),
    )


def _session_totals(user_ids: list[int] | None) -> dict:
    return _sum_fields(
        _query(UserStudySession, user_ids).all(),
        ('duration_seconds', 'words_studied', 'correct_count', 'wrong_count'),
    )


def audit_learning_truth(user_ids=None) -> dict:
    target_user_ids = _normalize_user_ids(user_ids)
    if target_user_ids == []:
        return {
            'ok': True,
            'users': 0,
            'legacy_word_count': 0,
            'mastery_word_count': 0,
            'missing_mastery_words': [],
            'legacy_sources': {'quick_memory': 0, 'smart_stats': 0, 'wrong_words': 0},
            'ledger': _ledger_totals([]),
            'sessions': _session_totals([]),
            'scope_mismatches': [],
        }
    if target_user_ids is None:
        target_user_ids = _collect_user_ids()

    legacy_entries, source_counts = _legacy_entries(target_user_ids)
    mastery_keys = {
        (row.user_id, normalize_word_key(row.word))
        for row in _query(UserWordMasteryState, target_user_ids).all()
        if normalize_word_key(row.word)
    }
    missing = [
        entry for entry in legacy_entries
        if (entry['user_id'], normalize_word_key(entry['word'])) not in mastery_keys
    ]
    ledger = _ledger_totals(target_user_ids)
    sessions = _session_totals(target_user_ids)
    scope_mismatches = []
    if sessions['rows'] and ledger['session_count'] < sessions['rows']:
        scope_mismatches.append({
            'scope': 'user_sessions',
            'expected_at_least': sessions['rows'],
            'actual': ledger['session_count'],
        })
    if sessions['duration_seconds'] and ledger['duration_seconds'] < sessions['duration_seconds']:
        scope_mismatches.append({
            'scope': 'duration_seconds',
            'expected_at_least': sessions['duration_seconds'],
            'actual': ledger['duration_seconds'],
        })

    return {
        'ok': not missing and not scope_mismatches,
        'users': len(target_user_ids),
        'legacy_word_count': len(legacy_entries),
        'mastery_word_count': len(mastery_keys),
        'missing_mastery_words': missing,
        'legacy_sources': source_counts,
        'ledger': ledger,
        'sessions': sessions,
        'scope_mismatches': scope_mismatches,
    }


def _merge_dimension_state(target: dict, incoming: dict, *, now_utc: datetime) -> bool:
    before = dict(target)
    target['history_wrong'] = max(_safe_int(target.get('history_wrong')), _safe_int(incoming.get('history_wrong')))
    target['pass_streak'] = max(_safe_int(target.get('pass_streak')), _safe_int(incoming.get('pass_streak')))
    target['attempt_count'] = max(
        _safe_int(target.get('attempt_count')),
        _safe_int(incoming.get('attempt_count')),
        target['history_wrong'] + target['pass_streak'],
    )
    for field_name in ('last_wrong_at', 'last_pass_at', 'next_review_at'):
        if incoming.get(field_name):
            target[field_name] = incoming[field_name]
    if incoming.get('source_mode'):
        target['source_mode'] = incoming['source_mode']
    if target['pass_streak'] > 0:
        target['last_result'] = 'pass'
        target['last_attempt_at'] = target.get('last_pass_at') or now_utc.isoformat()
    elif target['history_wrong'] > 0:
        target['last_result'] = 'fail'
        target['last_attempt_at'] = target.get('last_wrong_at') or now_utc.isoformat()
    if target['pass_streak'] >= WORD_MASTERY_TARGET_STREAK:
        target['status'] = 'passed'
    elif target['attempt_count'] > 0 or target['history_wrong'] > 0:
        target['status'] = 'in_progress'
    else:
        target['status'] = 'not_started'
    return target != before


def _merge_states(target: dict[str, dict], incoming: dict[str, dict], *, now_utc: datetime) -> bool:
    changed = False
    for dimension in WORD_MASTERY_DIMENSIONS:
        changed = _merge_dimension_state(
            target[dimension],
            incoming.get(dimension) or {},
            now_utc=now_utc,
        ) or changed
    return changed


def _apply_mastery_summary(record: UserWordMasteryState, states: dict[str, dict], now_utc: datetime) -> None:
    summary = dimension_state_summary(states)
    record.dimension_state = serialize_states(states)
    record.overall_status = summary['overall_status']
    record.current_round = summary['current_round']
    record.next_due_at = summary['next_due_at']
    record.pending_dimensions = serialize_pending_dimensions(summary['pending_dimensions'])
    if summary['unlock_count'] > 0 and record.unlocked_at is None:
        record.unlocked_at = now_utc
    if summary['overall_status'] == 'passed' and record.passed_at is None:
        record.passed_at = now_utc


def backfill_word_mastery_from_legacy(user_ids=None, *, commit: bool = True) -> dict:
    target_user_ids = _normalize_user_ids(user_ids)
    if target_user_ids == []:
        return {'users': 0, 'legacy_words': 0, 'created': 0, 'updated': 0, 'skipped': 0}
    if target_user_ids is None:
        target_user_ids = _collect_user_ids()

    legacy_entries, _source_counts = _legacy_entries(target_user_ids)
    entries_by_user: dict[int, list[dict]] = defaultdict(list)
    for entry in legacy_entries:
        entries_by_user[entry['user_id']].append(entry)

    summary = {
        'users': len(target_user_ids),
        'legacy_words': len(legacy_entries),
        'created': 0,
        'updated': 0,
        'skipped': 0,
    }
    now_utc = utc_now()
    for user_id, entries in entries_by_user.items():
        source_maps = build_legacy_source_maps(user_id, [entry['word'] for entry in entries])
        for entry in entries:
            word_key = normalize_word_key(entry['word'])
            if not word_key:
                summary['skipped'] += 1
                continue
            book_id = entry.get('book_id')
            chapter_id = entry.get('chapter_id')
            record = UserWordMasteryState.query.filter_by(
                user_id=user_id,
                word=normalize_word_text(entry['word']),
                scope_key=scope_key(book_id=book_id, chapter_id=chapter_id, day=None),
            ).first()
            created = record is None
            record = get_or_create_word_mastery_state(
                user_id,
                word=entry['word'],
                book_id=book_id,
                chapter_id=chapter_id,
                source_maps=source_maps,
            )
            states = dimension_states_from_record(record)
            incoming_states = legacy_states_for_word(word_key, source_maps)
            changed = _merge_states(states, incoming_states, now_utc=now_utc)
            _apply_mastery_summary(record, states, now_utc)
            if created:
                summary['created'] += 1
            elif changed:
                summary['updated'] += 1
    db.session.flush()
    if commit:
        db.session.commit()
    else:
        db.session.rollback()
    return summary
