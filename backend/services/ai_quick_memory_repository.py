from __future__ import annotations

from service_models.learning_core_models import UserQuickMemoryRecord, db


def get_user_quick_memory_record(user_id: int, word: str):
    return UserQuickMemoryRecord.query.filter_by(user_id=user_id, word=word).first()


def create_user_quick_memory_record(
    user_id: int,
    word: str,
    *,
    book_id: str | None,
    chapter_id: str | None,
    status: str,
    first_seen: int,
    last_seen: int,
    known_count: int,
    unknown_count: int,
    next_review: int,
    fuzzy_count: int,
):
    record = UserQuickMemoryRecord(
        user_id=user_id,
        word=word,
        book_id=book_id,
        chapter_id=chapter_id,
        status=status,
        first_seen=first_seen,
        last_seen=last_seen,
        known_count=known_count,
        unknown_count=unknown_count,
        next_review=next_review,
        fuzzy_count=fuzzy_count,
    )
    db.session.add(record)
    return record


def commit() -> None:
    db.session.commit()


def rollback() -> None:
    db.session.rollback()
