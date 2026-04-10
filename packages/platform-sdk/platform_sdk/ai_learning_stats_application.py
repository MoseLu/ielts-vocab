from __future__ import annotations

from platform_sdk.learning_core_internal_client import (
    fetch_learning_core_learning_stats_response,
    start_learning_core_study_session_response,
)
from platform_sdk.learning_core_stats_application import build_learning_core_learning_stats_response
from platform_sdk.learning_core_study_session_application import (
    start_learning_core_session_response as build_learning_core_start_session_response,
)


def build_learning_stats_response(
    user_id: int,
    *,
    days: int,
    book_id_filter: str | None,
    mode_filter_raw: str | None,
) -> tuple[dict, int]:
    try:
        return fetch_learning_core_learning_stats_response(
            user_id,
            days=days,
            book_id_filter=book_id_filter,
            mode_filter_raw=mode_filter_raw,
        )
    except Exception:
        return build_learning_core_learning_stats_response(
            user_id,
            days=days,
            book_id_filter=book_id_filter,
            mode_filter_raw=mode_filter_raw,
        )


def start_session_response(user_id: int, body: dict | None) -> tuple[dict, int]:
    payload = body or {}
    try:
        return start_learning_core_study_session_response(user_id, payload)
    except Exception:
        return build_learning_core_start_session_response(user_id, payload)
