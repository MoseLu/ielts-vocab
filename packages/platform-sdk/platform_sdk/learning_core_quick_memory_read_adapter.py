from __future__ import annotations

from platform_sdk.learning_core_internal_client import (
    fetch_learning_core_quick_memory_records_response,
    fetch_learning_core_quick_memory_review_queue_response,
)
from platform_sdk.learning_core_quick_memory_application import (
    build_learning_core_quick_memory_response,
    build_learning_core_quick_memory_review_queue_response,
)


def build_quick_memory_response(user_id: int) -> tuple[dict, int]:
    try:
        return fetch_learning_core_quick_memory_records_response(user_id), 200
    except Exception:
        return build_learning_core_quick_memory_response(user_id)


def build_quick_memory_review_queue_response(user_id: int, args) -> tuple[dict, int]:
    try:
        return fetch_learning_core_quick_memory_review_queue_response(user_id, args), 200
    except Exception:
        return build_learning_core_quick_memory_review_queue_response(user_id, args)
