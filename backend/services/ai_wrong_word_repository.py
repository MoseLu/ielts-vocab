from __future__ import annotations

from service_models.learning_core_models import UserWrongWord, db


def get_user_wrong_word(user_id: int, word: str):
    return UserWrongWord.query.filter_by(user_id=user_id, word=word).first()


def list_user_wrong_words(user_id: int):
    return (
        UserWrongWord.query
        .filter_by(user_id=user_id)
        .order_by(UserWrongWord.wrong_count.desc(), UserWrongWord.updated_at.desc())
        .all()
    )


def create_user_wrong_word(
    user_id: int,
    word: str,
    *,
    phonetic: str | None = None,
    pos: str | None = None,
    definition: str | None = None,
):
    record = UserWrongWord(
        user_id=user_id,
        word=word,
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
