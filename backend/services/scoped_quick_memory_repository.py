from __future__ import annotations

from service_models.learning_core_models import UserScopedQuickMemoryRecord, db
from services.learning_scope_support import LearningScope


def get_user_scoped_quick_memory_record(user_id: int, *, scope_key: str, word: str):
    return UserScopedQuickMemoryRecord.query.filter_by(
        user_id=user_id,
        scope_key=scope_key,
        word=word,
    ).first()


def list_user_scoped_quick_memory_records(user_id: int, *, scope_key: str | None = None):
    query = UserScopedQuickMemoryRecord.query.filter_by(user_id=user_id)
    if scope_key is not None:
        query = query.filter_by(scope_key=scope_key)
    return query.all()


def list_user_scoped_quick_memory_records_for_words(
    user_id: int,
    *,
    scope_key: str,
    words: list[str],
):
    normalized_words = [word for word in words if word]
    if not normalized_words:
        return []
    return UserScopedQuickMemoryRecord.query.filter(
        UserScopedQuickMemoryRecord.user_id == user_id,
        UserScopedQuickMemoryRecord.scope_key == scope_key,
        UserScopedQuickMemoryRecord.word.in_(normalized_words),
    ).all()


def create_user_scoped_quick_memory_record(
    user_id: int,
    word: str,
    *,
    scope: LearningScope,
    status: str,
    first_seen: int,
    last_seen: int,
    known_count: int,
    unknown_count: int,
    next_review: int,
    fuzzy_count: int,
):
    record = UserScopedQuickMemoryRecord(
        user_id=user_id,
        word=word,
        scope_key=scope.scope_key,
        scope_type=scope.scope_type,
        origin_scope=scope.origin_scope_json,
        book_id=scope.book_id,
        chapter_id=scope.chapter_id,
        day=scope.day,
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
