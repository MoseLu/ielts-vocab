from __future__ import annotations

from typing import Any

from services import phonetic_lookup_service
from services.word_catalog_service import build_word_seed_index, normalize_word_key


SYSTEM_CUSTOM_IMPORT_BOOK_IDS = (
    'ielts_reading_premium',
    'ielts_listening_premium',
    'ielts_comprehensive',
    'ielts_ultimate',
    'awl_academic',
    'ielts_9400_extended',
    'ielts_confusable_match',
)


def _clean_text(value: Any) -> str:
    return str(value or '').strip()


def build_custom_book_import_index() -> dict[str, dict]:
    return build_word_seed_index(SYSTEM_CUSTOM_IMPORT_BOOK_IDS)


def resolve_custom_book_word(
    word_payload: dict[str, Any],
    *,
    source_order: int,
    input_index: int,
    chapter_index: int,
    import_index: dict[str, dict] | None = None,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    word = _clean_text(word_payload.get('word'))
    word_key = normalize_word_key(word)
    seed = (import_index or build_custom_book_import_index()).get(word_key) or {}
    if not seed.get('book_refs'):
        return None, {
            'input_index': input_index,
            'chapter_index': chapter_index,
            'word': word,
            'reason': 'not_found_in_system_vocabulary',
        }

    phonetic = phonetic_lookup_service.normalize_phonetic_text(
        word_payload.get('phonetic'),
    ) or _clean_text(seed.get('phonetic'))
    pos = _clean_text(word_payload.get('pos')) or _clean_text(seed.get('pos'))
    definition = (
        _clean_text(word_payload.get('definition', word_payload.get('translation')))
        or _clean_text(seed.get('definition'))
    )
    return {
        'chapter_id': word_payload['chapter_id'],
        'word': _clean_text(seed.get('display_word')) or word,
        'phonetic': phonetic,
        'pos': pos,
        'definition': definition,
        'is_incomplete': not phonetic or not pos or not definition,
        'source_order': source_order,
    }, None
