from __future__ import annotations

from datetime import datetime

from service_models.learning_core_models import UserStudySession, db
from sqlalchemy import or_


def get_user_study_session(user_id: int, session_id):
    return UserStudySession.query.filter_by(
        id=session_id,
        user_id=user_id,
    ).first()


def find_recent_open_placeholder_session(
    *,
    user_id: int,
    threshold: datetime,
    mode: str | None = None,
    book_id: str | None = None,
    chapter_id: str | None = None,
):
    query = (
        UserStudySession.query
        .filter_by(user_id=user_id)
        .filter(
            UserStudySession.started_at >= threshold,
            UserStudySession.ended_at.is_(None),
            UserStudySession.words_studied == 0,
            UserStudySession.correct_count == 0,
            UserStudySession.wrong_count == 0,
            UserStudySession.duration_seconds == 0,
        )
    )
    if mode is not None:
        query = query.filter(UserStudySession.mode == mode)
    if book_id is not None:
        query = query.filter(UserStudySession.book_id == book_id)
    if chapter_id is not None:
        query = query.filter(UserStudySession.chapter_id == chapter_id)
    return query.order_by(UserStudySession.started_at.desc(), UserStudySession.id.desc()).first()


def newer_analytics_session_exists(
    *,
    user_id: int,
    exclude_session_id: int,
    started_after: datetime,
):
    return (
        UserStudySession.query
        .filter(
            UserStudySession.user_id == user_id,
            UserStudySession.id != exclude_session_id,
            UserStudySession.started_at > started_after,
            UserStudySession.analytics_clause(),
            or_(
                UserStudySession.words_studied > 0,
                UserStudySession.correct_count > 0,
                UserStudySession.wrong_count > 0,
            ),
        )
        .first()
        is not None
    )


def find_pending_session_in_window(
    *,
    user_id: int,
    mode: str | None,
    book_id: str | None,
    chapter_id: str | None,
    started_after: datetime,
    started_before: datetime | None = None,
):
    query = UserStudySession.query.filter_by(
        user_id=user_id,
        mode=mode,
        book_id=book_id,
        chapter_id=chapter_id,
    ).filter(
        UserStudySession.ended_at.is_(None),
        UserStudySession.words_studied == 0,
        UserStudySession.correct_count == 0,
        UserStudySession.wrong_count == 0,
        UserStudySession.duration_seconds == 0,
        UserStudySession.started_at >= started_after,
    )
    if started_before is not None:
        query = query.filter(UserStudySession.started_at <= started_before)
    return query.order_by(UserStudySession.started_at.desc()).first()


def create_study_session(
    *,
    user_id: int,
    mode: str | None,
    book_id: str | None,
    chapter_id: str | None,
    started_at: datetime,
):
    session = UserStudySession(
        user_id=user_id,
        mode=mode,
        book_id=book_id,
        chapter_id=chapter_id,
        started_at=started_at,
    )
    db.session.add(session)
    return session


def close_open_placeholder_sessions_before(
    *,
    user_id: int,
    started_before: datetime,
):
    rows = (
        UserStudySession.query
        .filter_by(user_id=user_id)
        .filter(
            UserStudySession.started_at < started_before,
            UserStudySession.ended_at.is_(None),
            UserStudySession.words_studied == 0,
            UserStudySession.correct_count == 0,
            UserStudySession.wrong_count == 0,
            UserStudySession.duration_seconds == 0,
        )
        .all()
    )
    for row in rows:
        row.ended_at = max(row.started_at, started_before)
    return rows


def delete_study_session(session) -> None:
    db.session.delete(session)


def flush() -> None:
    db.session.flush()


def commit() -> None:
    db.session.commit()


def rollback() -> None:
    db.session.rollback()
