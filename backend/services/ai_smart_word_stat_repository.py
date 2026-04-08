from __future__ import annotations

from models import UserSmartWordStat, db


def list_user_smart_word_stats(user_id: int):
    return UserSmartWordStat.query.filter_by(user_id=user_id).all()


def get_user_smart_word_stat(user_id: int, word: str):
    return UserSmartWordStat.query.filter_by(user_id=user_id, word=word).first()


def create_user_smart_word_stat(
    user_id: int,
    word: str,
    *,
    listening_correct: int,
    listening_wrong: int,
    meaning_correct: int,
    meaning_wrong: int,
    dictation_correct: int,
    dictation_wrong: int,
):
    record = UserSmartWordStat(
        user_id=user_id,
        word=word,
        listening_correct=listening_correct,
        listening_wrong=listening_wrong,
        meaning_correct=meaning_correct,
        meaning_wrong=meaning_wrong,
        dictation_correct=dictation_correct,
        dictation_wrong=dictation_wrong,
    )
    db.session.add(record)
    return record


def commit() -> None:
    db.session.commit()


def rollback() -> None:
    db.session.rollback()
