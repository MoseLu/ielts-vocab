from __future__ import annotations

from services import (
    books_personalization_repository,
    books_vocabulary_loader_service,
    phonetic_lookup_service,
    word_catalog_repository,
)
from services.word_catalog_service import ensure_word_catalog_entry, normalize_word_key


WORD_NOTE_LIMIT = 500
def _empty_note(word: str) -> dict:
    return {'word': word, 'content': '', 'updated_at': None}


def _word_note_record(user_id: int, normalized_word: str) -> UserWordNote | None:
    return books_personalization_repository.get_user_word_note(user_id, normalized_word)


def serialize_note_for_user(user, word: str, normalized_word: str) -> dict:
    if not user:
        return _empty_note(word)

    record = _word_note_record(user.id, normalized_word)
    if not record:
        return _empty_note(word)
    return record.to_dict()


def build_word_details_response(raw_word: str, current_user) -> tuple[dict, int]:
    word = str(raw_word or '').strip()
    if not word:
        return {'error': 'word is required'}, 400

    catalog_entry, changed = ensure_word_catalog_entry(word)
    if changed:
        word_catalog_repository.commit()

    normalized_word = normalize_word_key(word)
    resolved_phonetic = (
        phonetic_lookup_service.lookup_local_phonetic(word)
        or phonetic_lookup_service.resolve_phonetic(word, allow_remote=True)
    )
    if resolved_phonetic and catalog_entry.phonetic != resolved_phonetic:
        catalog_entry.phonetic = resolved_phonetic
        word_catalog_repository.commit()

    catalog_payload = catalog_entry.to_dict()
    examples = books_vocabulary_loader_service.resolve_unified_examples(
        word,
        fallback_examples=catalog_payload['examples'],
        limit=1,
    )
    return {
        'word': word,
        'phonetic': catalog_payload['phonetic'],
        'pos': catalog_payload['pos'],
        'definition': catalog_payload['definition'],
        'root': catalog_payload['root'],
        'english': catalog_payload['english'],
        'examples': examples,
        'derivatives': catalog_payload['derivatives'],
        'books': catalog_payload['books'],
        'note': serialize_note_for_user(current_user, word, normalized_word),
    }, 200


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
