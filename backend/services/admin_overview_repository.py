from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import desc, func

from service_models.admin_ops_models import User, UserStudySession, db


def count_total_users() -> int:
    return User.query.count()


def count_distinct_active_users_since(since: datetime) -> int:
    return db.session.query(func.count(func.distinct(UserStudySession.user_id))).filter(
        UserStudySession.started_at >= since,
        UserStudySession.analytics_clause(),
    ).scalar() or 0


def count_distinct_active_users_on(target_day: date) -> int:
    return db.session.query(func.count(func.distinct(UserStudySession.user_id))).filter(
        func.date(UserStudySession.started_at) == target_day,
        UserStudySession.analytics_clause(),
    ).scalar() or 0


def count_total_analytics_sessions() -> int:
    return UserStudySession.query.filter(UserStudySession.analytics_clause()).count()


def get_analytics_totals() -> dict[str, int]:
    return {
        'study_seconds': db.session.query(func.sum(UserStudySession.duration_seconds)).filter(
            UserStudySession.analytics_clause()
        ).scalar() or 0,
        'words_studied': db.session.query(func.sum(UserStudySession.words_studied)).filter(
            UserStudySession.analytics_clause()
        ).scalar() or 0,
        'correct': db.session.query(func.sum(UserStudySession.correct_count)).filter(
            UserStudySession.analytics_clause()
        ).scalar() or 0,
        'wrong': db.session.query(func.sum(UserStudySession.wrong_count)).filter(
            UserStudySession.analytics_clause()
        ).scalar() or 0,
    }


def count_new_users_on(target_day: date) -> int:
    return User.query.filter(func.date(User.created_at) == target_day).count()


def count_new_users_since(since: datetime) -> int:
    return User.query.filter(User.created_at >= since).count()


def list_daily_activity_rows(*, since: datetime):
    return db.session.query(
        func.date(UserStudySession.started_at).label('day'),
        func.count(UserStudySession.id).label('sessions'),
        func.count(func.distinct(UserStudySession.user_id)).label('users'),
        func.sum(UserStudySession.duration_seconds).label('study_seconds'),
        func.sum(UserStudySession.words_studied).label('words'),
    ).filter(
        UserStudySession.started_at >= since,
        UserStudySession.analytics_clause(),
    ).group_by(func.date(UserStudySession.started_at)).order_by('day').all()


def list_mode_stats_rows():
    return db.session.query(
        UserStudySession.mode,
        func.count(UserStudySession.id).label('count'),
        func.sum(UserStudySession.words_studied).label('words'),
    ).filter(
        UserStudySession.analytics_clause()
    ).group_by(UserStudySession.mode).all()


def list_top_book_rows(*, limit: int = 5):
    return db.session.query(
        UserStudySession.book_id,
        func.count(UserStudySession.id).label('sessions'),
        func.count(func.distinct(UserStudySession.user_id)).label('users'),
    ).filter(
        UserStudySession.book_id.isnot(None),
        UserStudySession.analytics_clause(),
    ).group_by(
        UserStudySession.book_id
    ).order_by(desc('sessions')).limit(limit).all()
