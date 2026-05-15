from __future__ import annotations

from service_models.learning_core_models import UserScopedWrongWord, db
from services.learning_scope_support import LearningScope


def get_user_scoped_wrong_word(user_id: int, *, scope_key: str, word: str):
    return UserScopedWrongWord.query.filter_by(
        user_id=user_id,
        scope_key=scope_key,
        word=word,
    ).first()


def list_user_scoped_wrong_words(user_id: int, *, scope_key: str | None = None):
    query = UserScopedWrongWord.query.filter_by(user_id=user_id)
    if scope_key is not None:
        query = query.filter_by(scope_key=scope_key)
    return query.order_by(
        UserScopedWrongWord.wrong_count.desc(),
        UserScopedWrongWord.updated_at.desc(),
    ).all()


def list_user_scoped_wrong_words_for_words(user_id: int, *, scope_key: str, words: list[str]):
    normalized_words = [word for word in words if word]
    if not normalized_words:
        return []
    return UserScopedWrongWord.query.filter(
        UserScopedWrongWord.user_id == user_id,
        UserScopedWrongWord.scope_key == scope_key,
        UserScopedWrongWord.word.in_(normalized_words),
    ).all()


def create_user_scoped_wrong_word(
    user_id: int,
    word: str,
    *,
    scope: LearningScope,
    phonetic: str | None = None,
    pos: str | None = None,
    definition: str | None = None,
):
    record = UserScopedWrongWord(
        user_id=user_id,
        word=word,
        scope_key=scope.scope_key,
        scope_type=scope.scope_type,
        origin_scope=scope.origin_scope_json,
        book_id=scope.book_id,
        chapter_id=scope.chapter_id,
        day=scope.day,
        phonetic=phonetic,
        pos=pos,
        definition=definition,
        wrong_count=0,
        listening_correct=0,
        listening_wrong=0,
        meaning_correct=0,
        meaning_wrong=0,
        dictation_correct=0,
        dictation_wrong=0,
    )
    db.session.add(record)
    return record


def commit() -> None:
    db.session.commit()


def rollback() -> None:
    db.session.rollback()
