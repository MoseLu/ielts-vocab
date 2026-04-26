from __future__ import annotations

from collections import defaultdict
from datetime import datetime

from service_models.learning_core_models import (
    UserBookProgress,
    UserChapterModeProgress,
    UserChapterProgress,
    UserLearningBookRollup,
    UserLearningChapterRollup,
    UserLearningDailyLedger,
    UserLearningEvent,
    UserLearningModeRollup,
    UserLearningUserRollup,
    UserQuickMemoryRecord,
    UserStudySession,
    UserWrongWord,
    db,
)
from services.local_time import utc_naive_to_local_date_key
from services.learning_activity_service import (
    normalize_learning_mode,
    rebuild_learning_activity_rollups,
    record_learning_activity,
)


_EVENT_TYPES_COVERED_BY_PRIMARY_SOURCES = {
    'study_session',
    'book_progress_updated',
    'chapter_progress_updated',
    'chapter_mode_progress_updated',
    'quick_memory_review',
}


def _safe_int(value, default: int = 0) -> int:
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return default


def _epoch_ms_to_datetime(value) -> datetime | None:
    milliseconds = _safe_int(value)
    if milliseconds <= 0:
        return None
    return datetime.utcfromtimestamp(milliseconds / 1000)


def _normalize_user_ids(user_ids) -> list[int] | None:
    if user_ids is None:
        return None
    normalized = sorted({int(value) for value in user_ids if value is not None})
    return normalized or []


def _collect_user_ids() -> list[int]:
    user_ids: set[int] = set()
    for model in (
        UserStudySession,
        UserLearningEvent,
        UserQuickMemoryRecord,
        UserWrongWord,
        UserChapterModeProgress,
        UserChapterProgress,
        UserBookProgress,
    ):
        for row in db.session.query(model.user_id).distinct().all():
            if row[0] is not None:
                user_ids.add(int(row[0]))
    return sorted(user_ids)


def _clear_existing(user_ids: list[int] | None) -> None:
    for model in (
        UserLearningDailyLedger,
        UserLearningChapterRollup,
        UserLearningModeRollup,
        UserLearningBookRollup,
        UserLearningUserRollup,
    ):
        query = db.session.query(model)
        if user_ids is not None:
            query = query.filter(model.user_id.in_(user_ids))
        query.delete(synchronize_session=False)
    db.session.flush()


def _scoped_query(model, user_ids: list[int]):
    return model.query.filter(model.user_id.in_(user_ids))


def _record(summary: dict, **kwargs) -> None:
    scope = record_learning_activity(rebuild_rollups=False, **kwargs)
    summary['ledger_writes'] += 1
    summary['touched_scopes'].add((
        scope['user_id'],
        scope['book_id'] or None,
        scope['mode'] or None,
        scope['chapter_id'] or None,
    ))


def _session_date_lookup(user_ids: list[int]) -> dict[tuple[int, str, str, str], str]:
    lookup: dict[tuple[int, str, str, str], tuple[datetime, str]] = {}
    for row in _scoped_query(UserStudySession, user_ids).all():
        mode = normalize_learning_mode(row.mode)
        if not mode:
            continue
        occurred_at = row.ended_at or row.started_at
        learning_date = utc_naive_to_local_date_key(occurred_at) if occurred_at else ''
        if not learning_date:
            continue
        key = (row.user_id, str(row.book_id or ''), mode, str(row.chapter_id or ''))
        previous = lookup.get(key)
        if previous is None or (occurred_at or datetime.min) >= previous[0]:
            lookup[key] = (occurred_at or datetime.min, learning_date)
    return {key: value[1] for key, value in lookup.items()}


def _backfill_sessions(user_ids: list[int], summary: dict) -> None:
    for row in _scoped_query(UserStudySession, user_ids).all():
        _record(
            summary,
            user_id=row.user_id,
            book_id=row.book_id,
            mode=row.mode,
            chapter_id=row.chapter_id,
            occurred_at=row.ended_at or row.started_at,
            item_delta=_safe_int(row.words_studied),
            duration_delta=_safe_int(row.duration_seconds),
            session_delta=1,
        )
        summary['study_sessions'] += 1


def _backfill_events(user_ids: list[int], summary: dict) -> None:
    for row in _scoped_query(UserLearningEvent, user_ids).all():
        if row.event_type in _EVENT_TYPES_COVERED_BY_PRIMARY_SOURCES:
            continue
        _record(
            summary,
            user_id=row.user_id,
            book_id=row.book_id,
            mode=row.mode,
            chapter_id=row.chapter_id,
            occurred_at=row.occurred_at,
            item_delta=_safe_int(row.item_count),
            duration_delta=_safe_int(row.duration_seconds),
            wrong_word_delta=(
                _safe_int(row.wrong_count)
                if row.event_type == 'wrong_word_recorded'
                else 0
            ),
        )
        summary['learning_events'] += 1


def _backfill_quick_memory(user_ids: list[int], summary: dict) -> None:
    for row in _scoped_query(UserQuickMemoryRecord, user_ids).all():
        review_count = max(
            1,
            _safe_int(row.known_count) + _safe_int(row.unknown_count) + _safe_int(row.fuzzy_count),
        )
        _record(
            summary,
            user_id=row.user_id,
            book_id=row.book_id,
            mode='quickmemory',
            chapter_id=row.chapter_id,
            occurred_at=_epoch_ms_to_datetime(row.last_seen),
            item_delta=1,
            review_delta=review_count,
        )
        summary['quick_memory_records'] += 1


def _backfill_wrong_words(user_ids: list[int], summary: dict) -> None:
    # Wrong-word rows are a functional sub-ledger, not the hierarchy truth source.
    # Only scoped wrong_word_recorded events should flow into the five-level ledgers.
    for _row in _scoped_query(UserWrongWord, user_ids).all():
        summary['wrong_words'] += 1


def _mode_lookup(user_ids: list[int]) -> dict[tuple[int, str, str], set[str]]:
    lookup: dict[tuple[int, str, str], set[str]] = defaultdict(set)
    for row in _scoped_query(UserChapterModeProgress, user_ids).all():
        mode = normalize_learning_mode(row.mode)
        if mode:
            lookup[(row.user_id, str(row.book_id), str(row.chapter_id))].add(mode)
    return lookup


def _backfill_chapter_modes(
    user_ids: list[int],
    summary: dict,
    session_dates: dict[tuple[int, str, str, str], str],
) -> None:
    for row in _scoped_query(UserChapterModeProgress, user_ids).all():
        mode = normalize_learning_mode(row.mode)
        if not mode:
            continue
        scope_key = (row.user_id, str(row.book_id or ''), mode, str(row.chapter_id or ''))
        _record(
            summary,
            user_id=row.user_id,
            book_id=row.book_id,
            mode=mode,
            chapter_id=row.chapter_id,
            occurred_at=row.updated_at,
            learning_date=session_dates.get(scope_key),
            correct_count=_safe_int(row.correct_count),
            wrong_count=_safe_int(row.wrong_count),
            is_completed=bool(row.is_completed),
        )
        summary['chapter_mode_progress'] += 1


def _backfill_chapters(
    user_ids: list[int],
    summary: dict,
    session_dates: dict[tuple[int, str, str, str], str],
) -> None:
    mode_lookup = _mode_lookup(user_ids)
    for row in _scoped_query(UserChapterProgress, user_ids).all():
        modes = mode_lookup.get((row.user_id, str(row.book_id), str(row.chapter_id)), set())
        kwargs = {
            'user_id': row.user_id,
            'book_id': row.book_id,
            'occurred_at': row.updated_at,
            'current_index': _safe_int(row.session_current_index),
            'words_learned': _safe_int(row.words_learned),
            'correct_count': _safe_int(row.correct_count),
            'wrong_count': _safe_int(row.wrong_count),
            'is_completed': bool(row.is_completed),
        }
        if len(modes) == 1:
            mode = next(iter(modes))
            scope_key = (row.user_id, str(row.book_id or ''), mode, str(row.chapter_id or ''))
            kwargs.update({
                'mode': mode,
                'chapter_id': row.chapter_id,
                'learning_date': session_dates.get(scope_key),
            })
        _record(summary, **kwargs)
        summary['chapter_progress'] += 1


def _backfill_books(user_ids: list[int], summary: dict) -> None:
    for row in _scoped_query(UserBookProgress, user_ids).all():
        _record(
            summary,
            user_id=row.user_id,
            book_id=row.book_id,
            occurred_at=row.updated_at,
            current_index=_safe_int(row.current_index),
            correct_count=_safe_int(row.correct_count),
            wrong_count=_safe_int(row.wrong_count),
            is_completed=bool(row.is_completed),
        )
        summary['book_progress'] += 1


def _rebuild_from_ledgers(user_ids: list[int], summary: dict) -> None:
    scopes = {
        (row.user_id, row.book_id or None, row.mode or None, row.chapter_id or None)
        for row in UserLearningDailyLedger.query.filter(
            UserLearningDailyLedger.user_id.in_(user_ids)
        ).all()
    }
    for user_id, book_id, mode, chapter_id in scopes:
        rebuild_learning_activity_rollups(
            user_id=user_id,
            book_id=book_id,
            mode=mode,
            chapter_id=chapter_id,
        )
    summary['rebuilt_scopes'] = len(scopes)


def backfill_learning_activity_rollups(user_ids=None, *, commit: bool = True) -> dict:
    target_user_ids = _normalize_user_ids(user_ids)
    if target_user_ids == []:
        return {'users': 0, 'ledger_writes': 0, 'rebuilt_scopes': 0}
    if target_user_ids is None:
        target_user_ids = _collect_user_ids()

    summary = {
        'users': len(target_user_ids),
        'study_sessions': 0,
        'learning_events': 0,
        'quick_memory_records': 0,
        'wrong_words': 0,
        'chapter_mode_progress': 0,
        'chapter_progress': 0,
        'book_progress': 0,
        'ledger_writes': 0,
        'rebuilt_scopes': 0,
        'touched_scopes': set(),
    }
    _clear_existing(target_user_ids)
    session_dates = _session_date_lookup(target_user_ids)
    _backfill_sessions(target_user_ids, summary)
    _backfill_events(target_user_ids, summary)
    _backfill_quick_memory(target_user_ids, summary)
    _backfill_wrong_words(target_user_ids, summary)
    _backfill_chapter_modes(target_user_ids, summary, session_dates)
    _backfill_chapters(target_user_ids, summary, session_dates)
    _backfill_books(target_user_ids, summary)
    db.session.flush()
    _rebuild_from_ledgers(target_user_ids, summary)
    if commit:
        db.session.commit()
    summary['touched_scopes'] = len(summary['touched_scopes'])
    return summary
