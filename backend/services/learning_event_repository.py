from __future__ import annotations

from datetime import datetime

from service_models.learning_core_models import UserLearningEvent, db
from sqlalchemy import or_


_SESSION_ACTIVITY_SOURCES = (
    'practice',
    'quickmemory',
    'practice_reset',
    'wrong_words',
    'chapter_progress',
    'chapter_mode_progress',
    'book_progress',
)


def list_user_learning_events_in_window(
    user_id: int,
    *,
    start_at: datetime,
    end_at: datetime,
):
    return (
        UserLearningEvent.query
        .filter_by(user_id=user_id)
        .filter(
            UserLearningEvent.occurred_at >= start_at,
            UserLearningEvent.occurred_at < end_at,
        )
        .order_by(UserLearningEvent.occurred_at.asc(), UserLearningEvent.id.asc())
        .all()
    )


def find_latest_session_activity_at(
    user_id: int,
    *,
    started_at: datetime,
    end_at: datetime,
    mode: str | None = None,
    book_id: str | None = None,
    chapter_id: str | None = None,
) -> datetime | None:
    query = (
        UserLearningEvent.query
        .filter(
            UserLearningEvent.user_id == user_id,
            UserLearningEvent.occurred_at >= started_at,
            UserLearningEvent.occurred_at <= end_at,
            UserLearningEvent.source.in_(_SESSION_ACTIVITY_SOURCES),
            UserLearningEvent.event_type != 'study_session',
        )
    )
    if mode is not None:
        query = query.filter(or_(
            UserLearningEvent.mode == mode,
            UserLearningEvent.mode.is_(None),
        ))
    if book_id is not None:
        query = query.filter(UserLearningEvent.book_id == book_id)
    if chapter_id is not None:
        query = query.filter(or_(
            UserLearningEvent.chapter_id == chapter_id,
            UserLearningEvent.chapter_id.is_(None),
        ))

    event = query.order_by(
        UserLearningEvent.occurred_at.desc(),
        UserLearningEvent.id.desc(),
    ).first()
    return event.occurred_at if event is not None else None


def add_learning_event(record) -> None:
    db.session.add(record)


def commit() -> None:
    db.session.commit()


def rollback() -> None:
    db.session.rollback()
