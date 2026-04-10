from __future__ import annotations

from datetime import datetime

from models import UserLearningEvent, db


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


def add_learning_event(record) -> None:
    db.session.add(record)


def commit() -> None:
    db.session.commit()


def rollback() -> None:
    db.session.rollback()
