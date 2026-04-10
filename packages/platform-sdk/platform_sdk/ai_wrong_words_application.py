from __future__ import annotations

from platform_sdk.learning_core_internal_client import (
    clear_learning_core_wrong_words,
    fetch_learning_core_wrong_words_response,
    sync_learning_core_wrong_words,
)
from platform_sdk.learning_core_wrong_words_application import (
    build_learning_core_wrong_words_response,
    clear_learning_core_wrong_word_response,
    clear_learning_core_wrong_words_response,
    sync_learning_core_wrong_words_response,
)


def build_wrong_words_response(
    user_id: int,
    *,
    search_value=None,
    detail_mode=None,
) -> tuple[dict, int]:
    try:
        return fetch_learning_core_wrong_words_response(
            user_id,
            search_value=search_value,
            detail_mode=detail_mode,
        ), 200
    except Exception:
        return build_learning_core_wrong_words_response(
            user_id,
            search_value=search_value,
            detail_mode=detail_mode,
        )


def sync_wrong_words_response(user_id: int, body: dict | None) -> tuple[dict, int]:
    payload = body or {}
    try:
        return sync_learning_core_wrong_words(user_id, payload), 200
    except Exception:
        return sync_learning_core_wrong_words_response(user_id, payload)


def clear_wrong_word_response(user_id: int, word: str) -> tuple[dict, int]:
    try:
        return clear_learning_core_wrong_words(user_id, word=word), 200
    except Exception:
        return clear_learning_core_wrong_word_response(user_id, word)


def clear_wrong_words_response(user_id: int) -> tuple[dict, int]:
    try:
        return clear_learning_core_wrong_words(user_id), 200
    except Exception:
        return clear_learning_core_wrong_words_response(user_id)
