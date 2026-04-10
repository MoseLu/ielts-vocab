from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, or_, text

from service_models.learning_core_models import (
    UserBookProgress,
    UserChapterModeProgress,
    UserChapterProgress,
    UserStudySession,
    UserWrongWord,
    db,
)


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


def list_user_book_progress_rows(user_id: int, *, book_id: str | None = None):
    query = UserBookProgress.query.filter_by(user_id=user_id)
    if book_id:
        query = query.filter_by(book_id=book_id)
    return query.all()


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
    if limit is not None:
        query = query.limit(limit)
    return query.all()


def list_user_chapter_mode_progress_rows(user_id: int, *, book_id: str | None = None):
    query = UserChapterModeProgress.query.filter_by(user_id=user_id)
    if book_id:
        query = query.filter_by(book_id=book_id)
    return query.all()


def list_user_wrong_words_for_stats(user_id: int, *, limit: int | None = None):
    query = (
        UserWrongWord.query
        .filter_by(user_id=user_id)
        .order_by(UserWrongWord.wrong_count.desc(), UserWrongWord.word.asc())
    )
    if limit is not None:
        query = query.limit(limit)
    return query.all()


def list_user_wrong_words_for_ai(
    user_id: int,
    *,
    limit: int | None = None,
    query: str | None = None,
    recent_first: bool = True,
):
    normalized_query = ' '.join(str(query or '').strip().lower().split())
    query_builder = UserWrongWord.query.filter_by(user_id=user_id)

    if normalized_query:
        pattern = f"%{normalized_query}%"
        query_builder = query_builder.filter(or_(
            func.lower(func.coalesce(UserWrongWord.word, '')).like(pattern),
            func.lower(func.coalesce(UserWrongWord.phonetic, '')).like(pattern),
            func.lower(func.coalesce(UserWrongWord.pos, '')).like(pattern),
            func.lower(func.coalesce(UserWrongWord.definition, '')).like(pattern),
        ))

    if recent_first:
        query_builder = query_builder.order_by(
            UserWrongWord.updated_at.desc(),
            UserWrongWord.wrong_count.desc(),
            UserWrongWord.word.asc(),
        )
    else:
        query_builder = query_builder.order_by(
            UserWrongWord.wrong_count.desc(),
            UserWrongWord.updated_at.desc(),
            UserWrongWord.word.asc(),
        )

    if limit is not None:
        query_builder = query_builder.limit(limit)
    return query_builder.all()


def count_user_wrong_words(user_id: int) -> int:
    return int(UserWrongWord.query.filter_by(user_id=user_id).count())


def count_alltime_distinct_practiced_words(user_id: int) -> int:
    result = db.session.execute(
        text(
            """
            SELECT COUNT(*) FROM (
                SELECT LOWER(TRIM(word)) AS w FROM user_smart_word_stats
                WHERE user_id = :uid AND word IS NOT NULL AND TRIM(word) != ''
                UNION
                SELECT LOWER(TRIM(word)) FROM user_quick_memory_records
                WHERE user_id = :uid AND word IS NOT NULL AND TRIM(word) != ''
                UNION
                SELECT LOWER(TRIM(word)) FROM user_wrong_words
                WHERE user_id = :uid AND word IS NOT NULL AND TRIM(word) != ''
            ) AS distinct_words
            """
        ),
        {'uid': user_id},
    ).scalar()
    return int(result or 0)
