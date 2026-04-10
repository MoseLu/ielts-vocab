from __future__ import annotations

from platform_sdk.ai_progress_sync_application import (
    build_smart_stats_response,
    sync_quick_memory_response,
    sync_smart_stats_response,
)
from platform_sdk.ai_wrong_words_application import (
    build_wrong_words_response,
    clear_wrong_word_response,
    clear_wrong_words_response,
    sync_wrong_words_response,
)


def build_wrong_words_api_response(
    user_id: int,
    *,
    search_value=None,
    detail_mode=None,
) -> tuple[dict, int]:
    return build_wrong_words_response(
        user_id,
        search_value=search_value,
        detail_mode=detail_mode,
    )


def sync_wrong_words_api_response(user_id: int, body: dict | None) -> tuple[dict, int]:
    return sync_wrong_words_response(user_id, body or {})


def clear_wrong_word_api_response(user_id: int, word: str) -> tuple[dict, int]:
    return clear_wrong_word_response(user_id, word)


def clear_wrong_words_api_response(user_id: int) -> tuple[dict, int]:
    return clear_wrong_words_response(user_id)


def sync_quick_memory_api_response(user_id: int, body: dict | None) -> tuple[dict, int]:
    return sync_quick_memory_response(user_id, body or {})


def build_smart_stats_api_response(user_id: int) -> tuple[dict, int]:
    return build_smart_stats_response(user_id)


def sync_smart_stats_api_response(user_id: int, body: dict | None) -> tuple[dict, int]:
    return sync_smart_stats_response(user_id, body or {})
