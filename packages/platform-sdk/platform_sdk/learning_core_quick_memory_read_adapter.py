from __future__ import annotations

from platform_sdk.cross_service_boundary import run_with_legacy_cross_service_fallback
from platform_sdk.learning_core_internal_client import (
    fetch_learning_core_quick_memory_records_response,
    fetch_learning_core_quick_memory_review_queue_response,
)
from platform_sdk.learning_core_quick_memory_application import (
    build_learning_core_quick_memory_response,
    build_learning_core_quick_memory_review_queue_response,
)


def build_quick_memory_response(user_id: int) -> tuple[dict, int]:
    return run_with_legacy_cross_service_fallback(
        upstream_name='learning-core-service',
        action='quick-memory-read',
        primary=lambda: (fetch_learning_core_quick_memory_records_response(user_id), 200),
        fallback=lambda: build_learning_core_quick_memory_response(user_id),
    )


def build_quick_memory_review_queue_response(user_id: int, args) -> tuple[dict, int]:
    return run_with_legacy_cross_service_fallback(
        upstream_name='learning-core-service',
        action='quick-memory-review-queue-read',
        primary=lambda: (fetch_learning_core_quick_memory_review_queue_response(user_id, args), 200),
        fallback=lambda: build_learning_core_quick_memory_review_queue_response(user_id, args),
    )
