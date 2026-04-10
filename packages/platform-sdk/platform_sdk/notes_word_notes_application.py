from __future__ import annotations

from services import books_personalization_repository
from services.word_catalog_service import normalize_word_key


WORD_NOTE_LIMIT = 500


def _empty_note(word: str) -> dict:
    return {'word': word, 'content': '', 'updated_at': None}


def _word_note_record(user_id: int, normalized_word: str):
    return books_personalization_repository.get_user_word_note(user_id, normalized_word)


def save_word_detail_note_response(user_id: int, data: dict | None) -> tuple[dict, int]:
    payload = data or {}
    word = str(payload.get('word') or '').strip()
    if not word:
        return {'error': 'word is required'}, 400

    content = str(payload.get('content') or '')[:WORD_NOTE_LIMIT]
    normalized_word = normalize_word_key(word)
    record = _word_note_record(user_id, normalized_word)

    if not content.strip():
        if record:
            books_personalization_repository.delete_row(record)
            books_personalization_repository.commit()
        return {'note': _empty_note(word)}, 200

    if not record:
        record = books_personalization_repository.create_user_word_note(
            user_id,
            word=word,
            normalized_word=normalized_word,
        )

    record.word = word
    record.content = content
    books_personalization_repository.commit()
    return {'note': record.to_dict()}, 200
