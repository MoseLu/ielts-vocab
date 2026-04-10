from __future__ import annotations

from service_models.learning_core_models import UserQuickMemoryRecord, db


def list_user_quick_memory_records(user_id: int):
    return UserQuickMemoryRecord.query.filter_by(user_id=user_id).all()


def list_user_quick_memory_records_for_words(user_id: int, words: list[str]):
    normalized_words = [word for word in words if word]
    if not normalized_words:
        return []
    return UserQuickMemoryRecord.query.filter(
        UserQuickMemoryRecord.user_id == user_id,
        UserQuickMemoryRecord.word.in_(normalized_words),
    ).all()


def commit() -> None:
    db.session.commit()
