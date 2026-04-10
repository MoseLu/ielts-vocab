from __future__ import annotations

from datetime import datetime

from service_models.learning_core_models import UserStudySession, UserWrongWord


def list_study_sessions_in_window(
    user_id: int,
    *,
    start_at: datetime,
    end_before: datetime,
    descending: bool = False,
):
    order_clause = (
        UserStudySession.started_at.desc()
        if descending
        else UserStudySession.started_at.asc()
    )
    return (
        UserStudySession.query
        .filter_by(user_id=user_id)
        .filter(UserStudySession.started_at >= start_at, UserStudySession.started_at < end_before)
        .order_by(order_clause)
        .all()
    )


def list_study_sessions_before(
    user_id: int,
    *,
    end_before: datetime,
    descending: bool = False,
    require_words_studied: bool = False,
):
    query = (
        UserStudySession.query
        .filter_by(user_id=user_id)
        .filter(UserStudySession.started_at < end_before)
    )
    if require_words_studied:
        query = query.filter(UserStudySession.words_studied > 0)
    order_clause = (
        UserStudySession.started_at.desc()
        if descending
        else UserStudySession.started_at.asc()
    )
    return query.order_by(order_clause).all()


def list_wrong_words(user_id: int, *, limit: int | None = None):
    query = UserWrongWord.query.filter_by(user_id=user_id)
    if limit is not None:
        query = query.limit(limit)
    return query.all()
