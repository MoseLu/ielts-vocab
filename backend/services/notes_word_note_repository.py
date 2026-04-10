from __future__ import annotations

from service_models.notes_models import UserWordNote, db


def get_user_word_note(user_id: int, normalized_word: str):
    return UserWordNote.query.filter_by(
        user_id=user_id,
        normalized_word=normalized_word,
    ).first()


def create_user_word_note(user_id: int, *, word: str, normalized_word: str):
    record = UserWordNote(
        user_id=user_id,
        word=word,
        normalized_word=normalized_word,
    )
    db.session.add(record)
    return record


def delete_row(record) -> None:
    db.session.delete(record)


def commit() -> None:
    db.session.commit()
