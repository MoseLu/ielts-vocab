from __future__ import annotations

from sqlalchemy import func

from service_models.learning_core_models import UserFamiliarWord, UserFavoriteWord, db


def list_user_familiar_words_by_normalized(user_id: int, normalized_words: list[str]):
    if not normalized_words:
        return []
    return UserFamiliarWord.query.filter(
        UserFamiliarWord.user_id == user_id,
        UserFamiliarWord.normalized_word.in_(normalized_words),
    ).all()


def get_user_familiar_word(user_id: int, normalized_word: str):
    return UserFamiliarWord.query.filter_by(
        user_id=user_id,
        normalized_word=normalized_word,
    ).first()


def create_user_familiar_word(user_id: int, normalized_word: str):
    record = UserFamiliarWord(
        user_id=user_id,
        normalized_word=normalized_word,
    )
    db.session.add(record)
    return record


def count_user_favorite_words(user_id: int) -> int:
    return int(UserFavoriteWord.query.filter_by(user_id=user_id).count())


def list_user_favorite_words(user_id: int):
    return UserFavoriteWord.query.filter_by(user_id=user_id).order_by(
        UserFavoriteWord.updated_at.desc(),
        UserFavoriteWord.created_at.desc(),
        func.lower(UserFavoriteWord.word),
    ).all()


def list_user_favorite_words_by_normalized(user_id: int, normalized_words: list[str]):
    if not normalized_words:
        return []
    return UserFavoriteWord.query.filter(
        UserFavoriteWord.user_id == user_id,
        UserFavoriteWord.normalized_word.in_(normalized_words),
    ).all()


def get_user_favorite_word(user_id: int, normalized_word: str):
    return UserFavoriteWord.query.filter_by(
        user_id=user_id,
        normalized_word=normalized_word,
    ).first()


def create_user_favorite_word(user_id: int, normalized_word: str):
    record = UserFavoriteWord(
        user_id=user_id,
        normalized_word=normalized_word,
    )
    db.session.add(record)
    return record


def delete_row(record) -> None:
    db.session.delete(record)


def flush() -> None:
    db.session.flush()


def commit() -> None:
    db.session.commit()
