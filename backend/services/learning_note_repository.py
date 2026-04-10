from __future__ import annotations

from datetime import datetime

from service_models.notes_models import UserLearningNote, db


def _apply_learning_note_window_filters(
    query,
    *,
    start_at: datetime | None = None,
    end_before: datetime | None = None,
):
    if start_at is not None:
        query = query.filter(UserLearningNote.created_at >= start_at)
    if end_before is not None:
        query = query.filter(UserLearningNote.created_at < end_before)
    return query


def list_learning_notes(
    user_id: int,
    *,
    start_at: datetime | None = None,
    end_before: datetime | None = None,
    before_id: int | None = None,
    descending: bool = True,
    order_by: str = 'created_at',
    limit: int | None = None,
):
    query = _apply_learning_note_window_filters(
        UserLearningNote.query.filter_by(user_id=user_id),
        start_at=start_at,
        end_before=end_before,
    )
    if before_id is not None:
        query = query.filter(UserLearningNote.id < before_id)
    if order_by == 'id':
        order_clause = UserLearningNote.id.desc() if descending else UserLearningNote.id.asc()
    else:
        order_clause = (
            UserLearningNote.created_at.desc()
            if descending
            else UserLearningNote.created_at.asc()
        )
    query = query.order_by(order_clause)
    if limit is not None:
        query = query.limit(limit)
    return query.all()


def count_learning_notes(
    user_id: int,
    *,
    start_at: datetime | None = None,
    end_before: datetime | None = None,
) -> int:
    query = _apply_learning_note_window_filters(
        UserLearningNote.query.filter_by(user_id=user_id),
        start_at=start_at,
        end_before=end_before,
    )
    return query.count()


def create_learning_note(
    user_id: int,
    *,
    question: str,
    answer: str,
    word_context: str | None,
):
    note = UserLearningNote(
        user_id=user_id,
        question=question,
        answer=answer,
        word_context=word_context,
    )
    db.session.add(note)
    return note


def commit() -> None:
    db.session.commit()


def rollback() -> None:
    db.session.rollback()
