from __future__ import annotations

from datetime import datetime

from models import UserConversationHistory, UserLearningNote, UserMemory, db


def add_conversation_turn(
    user_id: int,
    *,
    user_message: str,
    assistant_reply: str,
) -> None:
    db.session.add(UserConversationHistory(
        user_id=user_id,
        role='user',
        content=user_message,
    ))
    db.session.add(UserConversationHistory(
        user_id=user_id,
        role='assistant',
        content=assistant_reply,
    ))


def prune_conversation_history_before(
    user_id: int,
    *,
    cutoff: datetime,
) -> None:
    UserConversationHistory.query.filter(
        UserConversationHistory.user_id == user_id,
        UserConversationHistory.created_at < cutoff,
    ).delete(synchronize_session=False)


def get_user_memory(user_id: int):
    return UserMemory.query.filter_by(user_id=user_id).first()


def create_user_memory(user_id: int):
    memory = UserMemory(user_id=user_id)
    db.session.add(memory)
    return memory


def count_conversation_history(user_id: int) -> int:
    return UserConversationHistory.query.filter_by(user_id=user_id).count()


def list_conversation_history(
    user_id: int,
    *,
    limit: int | None = None,
    offset: int = 0,
    descending: bool = True,
):
    query = (
        UserConversationHistory.query
        .filter_by(user_id=user_id)
    )
    if descending:
        query = query.order_by(
            UserConversationHistory.created_at.desc(),
            UserConversationHistory.id.desc(),
        )
    else:
        query = query.order_by(
            UserConversationHistory.created_at.asc(),
            UserConversationHistory.id.asc(),
        )
    if offset > 0:
        query = query.offset(offset)
    if limit is not None:
        query = query.limit(limit)
    return query.all()


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


def flush() -> None:
    db.session.flush()
