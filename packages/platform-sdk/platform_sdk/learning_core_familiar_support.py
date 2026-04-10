from __future__ import annotations

from services import books_personalization_repository


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

    rows = books_personalization_repository.list_user_familiar_words_by_normalized(
        user_id,
        normalized_words,
    )
    return [row.normalized_word for row in rows]


def _upsert_familiar_record(user_id: int, payload: dict) -> tuple[object, bool]:
    normalized_word = _normalize_familiar_word(payload.get('word'))
    if not normalized_word:
        raise ValueError('缺少有效的 word')

    record = books_personalization_repository.get_user_familiar_word(user_id, normalized_word)
    created = record is None
    if created:
        record = books_personalization_repository.create_user_familiar_word(user_id, normalized_word)

    record.word = str(payload.get('word') or '').strip() or normalized_word
    for attr, payload_key in (
        ('phonetic', 'phonetic'),
        ('pos', 'pos'),
        ('definition', 'definition'),
    ):
        value = str(payload.get(payload_key) or '').strip()
        if value or not getattr(record, attr):
            setattr(record, attr, value)

    for attr, payload_key in (
        ('source_book_id', 'book_id'),
        ('source_book_title', 'book_title'),
        ('source_chapter_id', 'chapter_id'),
        ('source_chapter_title', 'chapter_title'),
    ):
        value = str(payload.get(payload_key) or '').strip()
        if value or not getattr(record, attr):
            setattr(record, attr, value or None)

    return record, created


def add_familiar_word(user_id: int, payload: dict | None) -> dict:
    record, created = _upsert_familiar_record(user_id, payload or {})
    books_personalization_repository.commit()
    return {
        'familiar': record.to_dict(),
        'created': created,
    }


def remove_familiar_word(user_id: int, word) -> dict:
    normalized_word = _normalize_familiar_word(word)
    if not normalized_word:
        raise ValueError('缺少有效的 word')

    record = books_personalization_repository.get_user_familiar_word(user_id, normalized_word)
    if record:
        books_personalization_repository.delete_row(record)

    books_personalization_repository.commit()
    return {'removed': record is not None}
