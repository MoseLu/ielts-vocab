from __future__ import annotations

from platform_sdk.learning_core_familiar_support import (
    add_familiar_word as _add_familiar_word,
    get_familiar_status_words as _get_familiar_status_words,
    remove_familiar_word as _remove_familiar_word,
)
from platform_sdk.learning_core_favorites_support import (
    FAVORITES_BOOK_ID,
    add_favorite_word as _add_favorite_word,
    get_favorite_status_words as _get_favorite_status_words,
    remove_favorite_word as _remove_favorite_word,
)


def get_favorite_status_words(user_id: int, words) -> list[str]:
    return _get_favorite_status_words(user_id, words)


def add_favorite_word(user_id: int, data: dict | None) -> dict:
    return _add_favorite_word(user_id, data)


def remove_favorite_word(user_id: int, word) -> dict:
    return _remove_favorite_word(user_id, word)


def get_familiar_status_words(user_id: int, words) -> list[str]:
    return _get_familiar_status_words(user_id, words)


def add_familiar_word(user_id: int, data: dict | None) -> dict:
    return _add_familiar_word(user_id, data)


def remove_familiar_word(user_id: int, word) -> dict:
    return _remove_familiar_word(user_id, word)
