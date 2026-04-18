from __future__ import annotations

from service_models.learning_core_models import UserGameWrongWord, db


def get_game_wrong_word(user_id: int, *, scope_key: str, node_key: str):
    return UserGameWrongWord.query.filter_by(
        user_id=user_id,
        scope_key=scope_key,
        node_key=node_key,
    ).first()


def list_scope_game_wrong_words(user_id: int, *, scope_key: str):
    return (
        UserGameWrongWord.query
        .filter_by(user_id=user_id, scope_key=scope_key)
        .order_by(UserGameWrongWord.updated_at.desc())
        .all()
    )


def create_game_wrong_word(
    user_id: int,
    *,
    scope_key: str,
    node_key: str,
    node_type: str,
    book_id: str | None,
    chapter_id: str | None,
    day: int | None,
):
    record = UserGameWrongWord(
        user_id=user_id,
        scope_key=scope_key,
        node_key=node_key,
        node_type=node_type,
        book_id=book_id,
        chapter_id=chapter_id,
        day=day,
    )
    db.session.add(record)
    return record
