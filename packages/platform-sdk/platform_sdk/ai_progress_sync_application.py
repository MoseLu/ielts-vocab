from __future__ import annotations

from platform_sdk.learning_core_internal_client import (
    fetch_learning_core_smart_stats_response,
    sync_learning_core_quick_memory,
    sync_learning_core_smart_stats,
)
from platform_sdk.learning_core_progress_sync_application import (
    build_learning_core_smart_stats_response,
    sync_learning_core_quick_memory_response as build_learning_core_quick_memory_sync_response,
    sync_learning_core_smart_stats_response as build_learning_core_smart_stats_sync_response,
)


def sync_quick_memory_response(user_id: int, body: dict | None) -> tuple[dict, int]:
    payload = body or {}
    try:
        return sync_learning_core_quick_memory(user_id, payload), 200
    except Exception:
        return build_learning_core_quick_memory_sync_response(user_id, payload)


def build_smart_stats_response(user_id: int) -> tuple[dict, int]:
    try:
        return fetch_learning_core_smart_stats_response(user_id), 200
    except Exception:
        return build_learning_core_smart_stats_response(user_id)


def sync_smart_stats_response(user_id: int, body: dict | None) -> tuple[dict, int]:
    payload = body or {}
    try:
        return sync_learning_core_smart_stats(user_id, payload), 200
    except Exception:
        return build_learning_core_smart_stats_sync_response(user_id, payload)
