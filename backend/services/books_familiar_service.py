from __future__ import annotations

from services import learning_core_personalization_repository


def _normalize_familiar_word(value) -> str:
    if not isinstance(value, str):
        return ''
    return value.strip().lower()


def get_familiar_status_words(user_id: int, raw_words) -> list[str]:
    if not isinstance(raw_words, list) or not raw_words:
        return []

    normalized_words: list[str] = []
    seen: set[str] = set()
    for value in raw_words:
        normalized = _normalize_familiar_word(value)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        normalized_words.append(normalized)

    if not normalized_words:
        return []

    rows = learning_core_personalization_repository.list_user_familiar_words_by_normalized(
        user_id,
        normalized_words,
    )
    return [row.normalized_word for row in rows]


def _upsert_familiar_record(user_id: int, payload: dict) -> tuple[UserFamiliarWord, bool]:
    normalized_word = _normalize_familiar_word(payload.get('word'))
    if not normalized_word:
        raise ValueError('缺少有效的 word')

    record = learning_core_personalization_repository.get_user_familiar_word(user_id, normalized_word)
    created = record is None
    if created:
        record = learning_core_personalization_repository.create_user_familiar_word(user_id, normalized_word)

    word_text = str(payload.get('word') or '').strip()
    phonetic = str(payload.get('phonetic') or '').strip()
    pos = str(payload.get('pos') or '').strip()
    definition = str(payload.get('definition') or '').strip()
    source_book_id = str(payload.get('book_id') or '').strip()
    source_book_title = str(payload.get('book_title') or '').strip()
    source_chapter_id = str(payload.get('chapter_id') or '').strip()
    source_chapter_title = str(payload.get('chapter_title') or '').strip()

    record.word = word_text or normalized_word
    if phonetic or not record.phonetic:
        record.phonetic = phonetic
    if pos or not record.pos:
        record.pos = pos
    if definition or not record.definition:
        record.definition = definition
    if source_book_id or not record.source_book_id:
        record.source_book_id = source_book_id or None
    if source_book_title or not record.source_book_title:
        record.source_book_title = source_book_title or None
    if source_chapter_id or not record.source_chapter_id:
        record.source_chapter_id = source_chapter_id or None
    if source_chapter_title or not record.source_chapter_title:
        record.source_chapter_title = source_chapter_title or None

    return record, created


def add_familiar_word(user_id: int, payload: dict | None) -> dict:
    record, created = _upsert_familiar_record(user_id, payload or {})
    learning_core_personalization_repository.commit()
    return {
        'familiar': record.to_dict(),
        'created': created,
    }


def remove_familiar_word(user_id: int, word) -> dict:
    normalized_word = _normalize_familiar_word(word)
    if not normalized_word:
        raise ValueError('缺少有效的 word')

    record = learning_core_personalization_repository.get_user_familiar_word(user_id, normalized_word)
    if record:
        learning_core_personalization_repository.delete_row(record)

    learning_core_personalization_repository.commit()
    return {
        'removed': record is not None,
    }
