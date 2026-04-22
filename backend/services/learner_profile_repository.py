from __future__ import annotations

from datetime import datetime

from service_models.learner_profile_models import (
    CustomBook,
    UserAddedBook,
    UserBookProgress,
    UserChapterProgress,
    UserLearningEvent,
    UserLearningNote,
    UserSmartWordStat,
    UserStudySession,
    UserWrongWord,
)
from services.learning_activity_compat import (
    list_book_rollup_compat_rows,
    list_chapter_rollup_compat_rows,
)


def _merge_book_progress_records(base_records, override_records):
    merged = {record.book_id: record for record in base_records}
    for record in override_records:
        merged[record.book_id] = record
    return list(merged.values())


def _merge_chapter_progress_records(base_records, override_records):
    merged = {(record.book_id, str(record.chapter_id)): record for record in base_records}
    for record in override_records:
        merged[(record.book_id, str(record.chapter_id))] = record
    return list(merged.values())


def list_user_analytics_sessions(
    user_id: int,
    *,
    before: datetime | None = None,
    book_id: str | None = None,
    mode_candidates=None,
    descending: bool = False,
):
    query = UserStudySession.query.filter_by(user_id=user_id).filter(
        UserStudySession.analytics_clause()
    )
    if before is not None:
        query = query.filter(UserStudySession.started_at < before)
    if book_id:
        query = query.filter(UserStudySession.book_id == book_id)
    if mode_candidates:
        query = query.filter(UserStudySession.mode.in_(tuple(mode_candidates)))
    order_clause = (
        UserStudySession.started_at.desc()
        if descending
        else UserStudySession.started_at.asc()
    )
    return query.order_by(order_clause).all()


def list_user_study_sessions_with_words(
    user_id: int,
    *,
    descending: bool = False,
    limit: int | None = None,
):
    query = UserStudySession.query.filter_by(user_id=user_id).filter(
        UserStudySession.words_studied > 0
    )
    order_clause = (
        UserStudySession.started_at.desc()
        if descending
        else UserStudySession.started_at.asc()
    )
    query = query.order_by(order_clause)
    if limit is not None:
        query = query.limit(limit)
    return query.all()


def list_user_smart_word_stats(user_id: int):
    return UserSmartWordStat.query.filter_by(user_id=user_id).all()


def list_user_wrong_words_for_profile(user_id: int, *, limit: int | None = None):
    query = (
        UserWrongWord.query
        .filter_by(user_id=user_id)
        .order_by(UserWrongWord.wrong_count.desc(), UserWrongWord.updated_at.desc())
    )
    if limit is not None:
        query = query.limit(limit)
    return query.all()


def list_user_learning_events(
    user_id: int,
    *,
    before: datetime | None = None,
    after: datetime | None = None,
    book_id: str | None = None,
    event_types=None,
    descending: bool = False,
):
    query = UserLearningEvent.query.filter_by(user_id=user_id)
    if book_id is not None:
        query = query.filter_by(book_id=book_id)
    if after is not None:
        query = query.filter(UserLearningEvent.occurred_at >= after)
    if before is not None:
        query = query.filter(UserLearningEvent.occurred_at < before)
    if event_types:
        query = query.filter(UserLearningEvent.event_type.in_(tuple(event_types)))
    if descending:
        return query.order_by(
            UserLearningEvent.occurred_at.desc(),
            UserLearningEvent.id.desc(),
        ).all()
    return query.order_by(
        UserLearningEvent.occurred_at.asc(),
        UserLearningEvent.id.asc(),
    ).all()


def list_user_learning_notes(
    user_id: int,
    *,
    before: datetime | None = None,
    limit: int | None = None,
    descending: bool = True,
):
    query = UserLearningNote.query.filter_by(user_id=user_id)
    if before is not None:
        query = query.filter(UserLearningNote.created_at < before)
    order_clause = (
        UserLearningNote.created_at.desc()
        if descending
        else UserLearningNote.created_at.asc()
    )
    query = query.order_by(order_clause)
    if limit is not None:
        query = query.limit(limit)
    return query.all()


def list_user_added_books_for_focus(user_id: int):
    return (
        UserAddedBook.query
        .filter_by(user_id=user_id)
        .order_by(UserAddedBook.added_at.asc(), UserAddedBook.id.asc())
        .all()
    )


def list_user_book_progress_rows(user_id: int, *, book_id: str | None = None):
    query = UserBookProgress.query.filter_by(user_id=user_id)
    if book_id:
        query = query.filter_by(book_id=book_id)
    rollups = list_book_rollup_compat_rows(user_id)
    if book_id:
        rollups = [row for row in rollups if row.book_id == book_id]
    return _merge_book_progress_records(query.all(), rollups)


def list_user_chapter_progress_rows(
    user_id: int,
    *,
    book_id: str | None = None,
    updated_since: datetime | None = None,
    order_by_updated: bool = False,
    descending: bool = False,
    limit: int | None = None,
):
    query = UserChapterProgress.query.filter_by(user_id=user_id)
    if book_id:
        query = query.filter_by(book_id=book_id)
    if updated_since is not None:
        query = query.filter(UserChapterProgress.updated_at >= updated_since)
    if order_by_updated:
        order_clause = (
            UserChapterProgress.updated_at.desc()
            if descending
            else UserChapterProgress.updated_at.asc()
        )
        query = query.order_by(order_clause)
    rollups = list_chapter_rollup_compat_rows(user_id, book_id=book_id)
    if updated_since is not None:
        rollups = [row for row in rollups if row.updated_at and row.updated_at >= updated_since]
    rows = _merge_chapter_progress_records(query.all(), rollups)
    if order_by_updated:
        rows.sort(
            key=lambda row: row.updated_at or datetime.min,
            reverse=descending,
        )
    if limit is not None:
        rows = rows[:limit]
    return rows


def list_custom_books_for_ids(user_id: int, book_ids):
    normalized_ids = [book_id for book_id in book_ids if book_id]
    if not normalized_ids:
        return []
    return (
        CustomBook.query
        .filter(
            CustomBook.user_id == user_id,
            CustomBook.id.in_(normalized_ids),
        )
        .all()
    )
