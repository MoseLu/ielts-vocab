from __future__ import annotations

from platform_sdk import notes_word_note_repository_adapter as word_note_repository
from platform_sdk.catalog_provider_adapter import normalize_word_key


WORD_NOTE_LIMIT = 500


def _empty_note(word: str) -> dict:
    return {'word': word, 'content': '', 'updated_at': None}


def _word_note_record(user_id: int, normalized_word: str):
    return word_note_repository.get_user_word_note(user_id, normalized_word)


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
            word_note_repository.delete_row(record)
            word_note_repository.commit()
        return {'note': _empty_note(word)}, 200

    if not record:
        record = word_note_repository.create_user_word_note(
            user_id,
            word=word,
            normalized_word=normalized_word,
        )

    record.word = word
    record.content = content
    word_note_repository.commit()
    return {'note': record.to_dict()}, 200
