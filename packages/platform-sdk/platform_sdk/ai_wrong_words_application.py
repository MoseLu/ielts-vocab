from __future__ import annotations

from platform_sdk.ai_wrong_word_projection_support import list_projected_wrong_words_for_ai
from platform_sdk.cross_service_boundary import (
    build_strict_internal_contract_error,
    legacy_cross_service_fallback_enabled,
    run_with_legacy_cross_service_fallback,
)
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
        return (
            fetch_learning_core_wrong_words_response(
                user_id,
                search_value=search_value,
                detail_mode=detail_mode,
            ),
            200,
        )
    except Exception:
        compact_mode = str(detail_mode or '').strip().lower() in {'compact', 'summary', 'basic', 'lite'}
        projection_ready, projected_words = list_projected_wrong_words_for_ai(
            user_id,
            query=search_value,
            recent_first=True,
            decorate=not compact_mode,
        )
        if projection_ready:
            return {'words': projected_words}, 200
        if legacy_cross_service_fallback_enabled():
            return build_learning_core_wrong_words_response(
                user_id,
                search_value=search_value,
                detail_mode=detail_mode,
            )
        return build_strict_internal_contract_error(
            upstream_name='learning-core-service',
            action='wrong-words-read',
        )


def sync_wrong_words_response(user_id: int, body: dict | None) -> tuple[dict, int]:
    payload = body or {}
    return run_with_legacy_cross_service_fallback(
        upstream_name='learning-core-service',
        action='wrong-words-sync',
        primary=lambda: (sync_learning_core_wrong_words(user_id, payload), 200),
        fallback=lambda: sync_learning_core_wrong_words_response(user_id, payload),
    )


def clear_wrong_word_response(user_id: int, word: str) -> tuple[dict, int]:
    return run_with_legacy_cross_service_fallback(
        upstream_name='learning-core-service',
        action='wrong-word-clear',
        primary=lambda: (clear_learning_core_wrong_words(user_id, word=word), 200),
        fallback=lambda: clear_learning_core_wrong_word_response(user_id, word),
    )


def clear_wrong_words_response(user_id: int) -> tuple[dict, int]:
    return run_with_legacy_cross_service_fallback(
        upstream_name='learning-core-service',
        action='wrong-words-clear-all',
        primary=lambda: (clear_learning_core_wrong_words(user_id), 200),
        fallback=lambda: clear_learning_core_wrong_words_response(user_id),
    )
