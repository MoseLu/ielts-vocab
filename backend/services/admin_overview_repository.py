from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import desc, func

from services.admin_projection_repository_support import study_session_model, user_count_model
from service_models.eventing_models import AdminProjectedPromptRun, AdminProjectedTTSMedia
from service_models.admin_ops_models import db


def count_total_users() -> int:
    return user_count_model().query.count()


def count_distinct_active_users_since(since: datetime) -> int:
    session_model = study_session_model()
    return db.session.query(func.count(func.distinct(session_model.user_id))).filter(
        session_model.started_at >= since,
        session_model.analytics_clause(),
    ).scalar() or 0


def count_distinct_active_users_on(target_day: date) -> int:
    session_model = study_session_model()
    return db.session.query(func.count(func.distinct(session_model.user_id))).filter(
        func.date(session_model.started_at) == target_day,
        session_model.analytics_clause(),
    ).scalar() or 0


def count_total_analytics_sessions() -> int:
    session_model = study_session_model()
    return session_model.query.filter(session_model.analytics_clause()).count()


def get_analytics_totals() -> dict[str, int]:
    session_model = study_session_model()
    return {
        'study_seconds': db.session.query(func.sum(session_model.duration_seconds)).filter(
            session_model.analytics_clause()
        ).scalar() or 0,
        'words_studied': db.session.query(func.sum(session_model.words_studied)).filter(
            session_model.analytics_clause()
        ).scalar() or 0,
        'correct': db.session.query(func.sum(session_model.correct_count)).filter(
            session_model.analytics_clause()
        ).scalar() or 0,
        'wrong': db.session.query(func.sum(session_model.wrong_count)).filter(
            session_model.analytics_clause()
        ).scalar() or 0,
    }


def count_new_users_on(target_day: date) -> int:
    user_model = user_count_model()
    return user_model.query.filter(func.date(user_model.created_at) == target_day).count()


def count_new_users_since(since: datetime) -> int:
    user_model = user_count_model()
    return user_model.query.filter(user_model.created_at >= since).count()


def list_daily_activity_rows(*, since: datetime):
    session_model = study_session_model()
    return db.session.query(
        func.date(session_model.started_at).label('day'),
        func.count(session_model.id).label('sessions'),
        func.count(func.distinct(session_model.user_id)).label('users'),
        func.sum(session_model.duration_seconds).label('study_seconds'),
        func.sum(session_model.words_studied).label('words'),
    ).filter(
        session_model.started_at >= since,
        session_model.analytics_clause(),
    ).group_by(func.date(session_model.started_at)).order_by('day').all()


def list_mode_stats_rows():
    session_model = study_session_model()
    return db.session.query(
        session_model.mode,
        func.count(session_model.id).label('count'),
        func.sum(session_model.words_studied).label('words'),
    ).filter(
        session_model.analytics_clause()
    ).group_by(session_model.mode).all()


def list_top_book_rows(*, limit: int = 5):
    session_model = study_session_model()
    return db.session.query(
        session_model.book_id,
        func.count(session_model.id).label('sessions'),
        func.count(func.distinct(session_model.user_id)).label('users'),
    ).filter(
        session_model.book_id.isnot(None),
        session_model.analytics_clause(),
    ).group_by(
        session_model.book_id
    ).order_by(desc('sessions')).limit(limit).all()


def count_tts_media_events_since(since: datetime) -> int:
    return AdminProjectedTTSMedia.query.filter(
        AdminProjectedTTSMedia.generated_at >= since,
    ).count()


def count_prompt_run_events_since(since: datetime) -> int:
    return AdminProjectedPromptRun.query.filter(
        AdminProjectedPromptRun.completed_at >= since,
    ).count()


def list_recent_tts_media_rows(*, limit: int = 5):
    return (
        AdminProjectedTTSMedia.query
        .order_by(AdminProjectedTTSMedia.generated_at.desc(), AdminProjectedTTSMedia.id.desc())
        .limit(limit)
        .all()
    )


def list_recent_prompt_run_rows(*, limit: int = 5):
    return (
        AdminProjectedPromptRun.query
        .order_by(AdminProjectedPromptRun.completed_at.desc(), AdminProjectedPromptRun.id.desc())
        .limit(limit)
        .all()
    )
