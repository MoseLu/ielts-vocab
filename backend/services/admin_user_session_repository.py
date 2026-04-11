from __future__ import annotations

from datetime import datetime

from sqlalchemy import desc, func

from services.admin_projection_repository_support import study_session_model
from service_models.admin_ops_models import db


def _apply_session_filters(query, session_model, *, date_from, date_to, mode, book_id):
    if date_from:
        query = query.filter(session_model.started_at >= date_from)
    if date_to:
        query = query.filter(session_model.started_at <= date_to + ' 23:59:59')
    if mode:
        query = query.filter(session_model.mode == mode)
    if book_id:
        query = query.filter(session_model.book_id == book_id)
    return query


def list_user_analytics_sessions(user_id: int):
    session_model = study_session_model()
    return session_model.query.filter_by(user_id=user_id).filter(
        session_model.analytics_clause()
    ).all()


def get_user_last_analytics_session(user_id: int):
    session_model = study_session_model()
    return (
        session_model.query.filter_by(user_id=user_id)
        .filter(session_model.analytics_clause())
        .order_by(desc(session_model.started_at))
        .first()
    )


def count_user_recent_analytics_sessions(user_id: int, *, since: datetime) -> int:
    session_model = study_session_model()
    return session_model.query.filter(
        session_model.user_id == user_id,
        session_model.started_at >= since,
        session_model.analytics_clause(),
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
    session_model = study_session_model()
    query = _apply_session_filters(
        session_model.query.filter_by(user_id=user_id).filter(
            session_model.analytics_clause()
        ),
        session_model,
        date_from=date_from,
        date_to=date_to,
        mode=mode,
        book_id=book_id,
    )
    return query.order_by(desc(session_model.started_at)).limit(limit).all()


def list_user_daily_study_rows(
    user_id: int,
    *,
    daily_base: str,
    date_to: str | None,
    mode: str | None,
    book_id: str | None,
):
    session_model = study_session_model()
    query = db.session.query(
        func.date(session_model.started_at).label('day'),
        func.sum(session_model.duration_seconds).label('seconds'),
        func.sum(session_model.words_studied).label('words'),
        func.sum(session_model.correct_count).label('correct'),
        func.sum(session_model.wrong_count).label('wrong'),
    ).filter(
        session_model.user_id == user_id,
        session_model.started_at >= daily_base,
        session_model.analytics_clause(),
    )
    if date_to:
        query = query.filter(session_model.started_at <= date_to + ' 23:59:59')
    if mode:
        query = query.filter(session_model.mode == mode)
    if book_id:
        query = query.filter(session_model.book_id == book_id)
    return query.group_by(func.date(session_model.started_at)).order_by('day').all()


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
    session_model = study_session_model()
    query = db.session.query(
        session_model.book_id,
        session_model.chapter_id,
        func.date(session_model.started_at).label('day'),
        session_model.mode,
        func.count(session_model.id).label('sessions'),
        func.sum(session_model.words_studied).label('words'),
        func.sum(session_model.correct_count).label('correct'),
        func.sum(session_model.wrong_count).label('wrong'),
        func.sum(session_model.duration_seconds).label('seconds'),
    ).filter(
        session_model.user_id == user_id,
        session_model.chapter_id.isnot(None),
        session_model.chapter_id != '',
        session_model.analytics_clause(),
    )
    query = _apply_session_filters(
        query,
        session_model,
        date_from=date_from,
        date_to=date_to,
        mode=mode,
        book_id=book_id,
    )
    if default_since and not date_from:
        query = query.filter(session_model.started_at >= default_since)
    return query.group_by(
        session_model.book_id,
        session_model.chapter_id,
        func.date(session_model.started_at),
        session_model.mode,
    ).order_by(desc(func.date(session_model.started_at))).limit(limit).all()
