from __future__ import annotations

from datetime import datetime

from sqlalchemy import desc, func

from service_models.admin_ops_models import UserStudySession, db


def _apply_session_filters(query, *, date_from, date_to, mode, book_id):
    if date_from:
        query = query.filter(UserStudySession.started_at >= date_from)
    if date_to:
        query = query.filter(UserStudySession.started_at <= date_to + ' 23:59:59')
    if mode:
        query = query.filter(UserStudySession.mode == mode)
    if book_id:
        query = query.filter(UserStudySession.book_id == book_id)
    return query


def list_user_analytics_sessions(user_id: int):
    return UserStudySession.query.filter_by(user_id=user_id).filter(
        UserStudySession.analytics_clause()
    ).all()


def get_user_last_analytics_session(user_id: int):
    return (
        UserStudySession.query.filter_by(user_id=user_id)
        .filter(UserStudySession.analytics_clause())
        .order_by(desc(UserStudySession.started_at))
        .first()
    )


def count_user_recent_analytics_sessions(user_id: int, *, since: datetime) -> int:
    return UserStudySession.query.filter(
        UserStudySession.user_id == user_id,
        UserStudySession.started_at >= since,
        UserStudySession.analytics_clause(),
    ).count()


def list_user_filtered_analytics_sessions(
    user_id: int,
    *,
    date_from: str | None,
    date_to: str | None,
    mode: str | None,
    book_id: str | None,
    limit: int = 100,
):
    query = _apply_session_filters(
        UserStudySession.query.filter_by(user_id=user_id).filter(
            UserStudySession.analytics_clause()
        ),
        date_from=date_from,
        date_to=date_to,
        mode=mode,
        book_id=book_id,
    )
    return query.order_by(desc(UserStudySession.started_at)).limit(limit).all()


def list_user_daily_study_rows(
    user_id: int,
    *,
    daily_base: str,
    date_to: str | None,
    mode: str | None,
    book_id: str | None,
):
    query = db.session.query(
        func.date(UserStudySession.started_at).label('day'),
        func.sum(UserStudySession.duration_seconds).label('seconds'),
        func.sum(UserStudySession.words_studied).label('words'),
        func.sum(UserStudySession.correct_count).label('correct'),
        func.sum(UserStudySession.wrong_count).label('wrong'),
    ).filter(
        UserStudySession.user_id == user_id,
        UserStudySession.started_at >= daily_base,
        UserStudySession.analytics_clause(),
    )
    if date_to:
        query = query.filter(UserStudySession.started_at <= date_to + ' 23:59:59')
    if mode:
        query = query.filter(UserStudySession.mode == mode)
    if book_id:
        query = query.filter(UserStudySession.book_id == book_id)
    return query.group_by(func.date(UserStudySession.started_at)).order_by('day').all()


def list_user_chapter_daily_rows(
    user_id: int,
    *,
    date_from: str | None,
    date_to: str | None,
    mode: str | None,
    book_id: str | None,
    default_since: str | None,
    limit: int = 500,
):
    query = db.session.query(
        UserStudySession.book_id,
        UserStudySession.chapter_id,
        func.date(UserStudySession.started_at).label('day'),
        UserStudySession.mode,
        func.count(UserStudySession.id).label('sessions'),
        func.sum(UserStudySession.words_studied).label('words'),
        func.sum(UserStudySession.correct_count).label('correct'),
        func.sum(UserStudySession.wrong_count).label('wrong'),
        func.sum(UserStudySession.duration_seconds).label('seconds'),
    ).filter(
        UserStudySession.user_id == user_id,
        UserStudySession.chapter_id.isnot(None),
        UserStudySession.chapter_id != '',
        UserStudySession.analytics_clause(),
    )
    query = _apply_session_filters(
        query,
        date_from=date_from,
        date_to=date_to,
        mode=mode,
        book_id=book_id,
    )
    if default_since and not date_from:
        query = query.filter(UserStudySession.started_at >= default_since)
    return query.group_by(
        UserStudySession.book_id,
        UserStudySession.chapter_id,
        func.date(UserStudySession.started_at),
        UserStudySession.mode,
    ).order_by(desc(func.date(UserStudySession.started_at))).limit(limit).all()
