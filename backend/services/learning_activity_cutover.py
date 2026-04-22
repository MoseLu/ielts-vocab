from __future__ import annotations

from datetime import timedelta

from sqlalchemy import or_

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
    UserProgress,
    UserStudySession,
    db,
)
from services.legacy_day_progress_compat import LEGACY_DAY_PROGRESS_PREFIX
from services.learning_activity_service import normalize_learning_mode


_SESSION_REPAIR_WINDOW = timedelta(minutes=2)


def _normalize_user_ids(user_ids) -> list[int] | None:
    if user_ids is None:
        return None
    normalized = sorted({int(value) for value in user_ids if value is not None})
    return normalized or []


def _scoped_query(model, user_ids: list[int] | None):
    query = model.query
    if user_ids is not None:
        query = query.filter(model.user_id.in_(user_ids))
    return query


def _session_needs_scope_repair(row: UserStudySession) -> bool:
    return not str(row.book_id or '').strip() or not str(row.chapter_id or '').strip()


def _candidate_events_for_session(row: UserStudySession) -> list[UserLearningEvent]:
    anchor = row.ended_at or row.started_at
    if anchor is None:
        return []
    lower = (row.started_at or anchor) - _SESSION_REPAIR_WINDOW
    upper = (row.ended_at or anchor) + _SESSION_REPAIR_WINDOW
    mode = normalize_learning_mode(row.mode)
    query = UserLearningEvent.query.filter(
        UserLearningEvent.user_id == row.user_id,
        UserLearningEvent.occurred_at >= lower,
        UserLearningEvent.occurred_at <= upper,
        UserLearningEvent.event_type != 'study_session',
        or_(
            UserLearningEvent.book_id.isnot(None),
            UserLearningEvent.chapter_id.isnot(None),
        ),
    )
    if mode:
        query = query.filter(or_(
            UserLearningEvent.mode == mode,
            UserLearningEvent.mode.is_(None),
        ))
    if row.book_id:
        query = query.filter(UserLearningEvent.book_id == row.book_id)
    if row.chapter_id:
        query = query.filter(UserLearningEvent.chapter_id == row.chapter_id)
    return query.order_by(UserLearningEvent.occurred_at.asc(), UserLearningEvent.id.asc()).all()


def _repair_session_scope(row: UserStudySession) -> tuple[bool, bool]:
    events = _candidate_events_for_session(row)
    if not events:
        return False, False

    book_candidates = {str(event.book_id).strip() for event in events if str(event.book_id or '').strip()}
    repaired_book = False
    repaired_chapter = False
    if not str(row.book_id or '').strip() and len(book_candidates) == 1:
        row.book_id = next(iter(book_candidates))
        repaired_book = True

    resolved_book = str(row.book_id or '').strip()
    chapter_candidates = {
        str(event.chapter_id).strip()
        for event in events
        if str(event.chapter_id or '').strip()
        and (not resolved_book or event.book_id == resolved_book)
    }
    if not str(row.chapter_id or '').strip() and len(chapter_candidates) == 1:
        row.chapter_id = next(iter(chapter_candidates))
        repaired_chapter = True

    return repaired_book, repaired_chapter


def repair_learning_activity_evidence(user_ids=None, *, commit: bool = True) -> dict:
    target_user_ids = _normalize_user_ids(user_ids)
    summary = {
        'sessions_checked': 0,
        'sessions_repaired': 0,
        'book_id_repaired': 0,
        'chapter_id_repaired': 0,
    }
    for row in _scoped_query(UserStudySession, target_user_ids).filter(
        or_(
            UserStudySession.book_id.is_(None),
            UserStudySession.book_id == '',
            UserStudySession.chapter_id.is_(None),
            UserStudySession.chapter_id == '',
        )
    ).all():
        if not _session_needs_scope_repair(row):
            continue
        summary['sessions_checked'] += 1
        repaired_book, repaired_chapter = _repair_session_scope(row)
        if repaired_book or repaired_chapter:
            summary['sessions_repaired'] += 1
            summary['book_id_repaired'] += 1 if repaired_book else 0
            summary['chapter_id_repaired'] += 1 if repaired_chapter else 0

    if commit:
        db.session.commit()
    else:
        db.session.flush()
    return summary


def purge_deprecated_learning_progress(user_ids=None, *, commit: bool = True) -> dict:
    target_user_ids = _normalize_user_ids(user_ids)
    summary = {}
    for model in (
        UserProgress,
        UserBookProgress,
        UserChapterProgress,
        UserChapterModeProgress,
    ):
        query = _scoped_query(model, target_user_ids)
        count = query.count()
        query.delete(synchronize_session=False)
        summary[model.__tablename__] = count
    if commit:
        db.session.commit()
    else:
        db.session.flush()
    return summary


def learning_activity_cutover_report(user_ids=None) -> dict:
    target_user_ids = _normalize_user_ids(user_ids)
    daily_query = _scoped_query(UserLearningDailyLedger, target_user_ids)
    return {
        'deprecated_rows': {
            model.__tablename__: _scoped_query(model, target_user_ids).count()
            for model in (
                UserProgress,
                UserBookProgress,
                UserChapterProgress,
                UserChapterModeProgress,
            )
        },
        'rollup_rows': {
            'daily_ledgers': daily_query.count(),
            'chapter_rollups': _scoped_query(UserLearningChapterRollup, target_user_ids).count(),
            'mode_rollups': _scoped_query(UserLearningModeRollup, target_user_ids).count(),
            'book_rollups': _scoped_query(UserLearningBookRollup, target_user_ids).count(),
            'user_rollups': _scoped_query(UserLearningUserRollup, target_user_ids).count(),
        },
        'fallback_ledgers': {
            'direct_user_ledgers': daily_query.filter(
                UserLearningDailyLedger.book_id == '',
                ~UserLearningDailyLedger.chapter_id.like(f'{LEGACY_DAY_PROGRESS_PREFIX}%'),
            ).count(),
            'direct_book_ledgers': daily_query.filter(
                UserLearningDailyLedger.book_id != '',
                UserLearningDailyLedger.mode == '',
            ).count(),
            'direct_mode_ledgers': daily_query.filter(
                UserLearningDailyLedger.book_id != '',
                UserLearningDailyLedger.mode != '',
                UserLearningDailyLedger.chapter_id == '',
            ).count(),
            'legacy_day_progress_ledgers': daily_query.filter(
                UserLearningDailyLedger.book_id == '',
                UserLearningDailyLedger.chapter_id.like(f'{LEGACY_DAY_PROGRESS_PREFIX}%'),
            ).count(),
        },
    }
