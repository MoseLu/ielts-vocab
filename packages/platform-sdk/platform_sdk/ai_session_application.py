from __future__ import annotations

from platform_sdk.cross_service_boundary import run_with_legacy_cross_service_fallback
from platform_sdk.learning_core_internal_client import (
    cancel_learning_core_study_session_response,
    log_learning_core_study_session_response,
)
from platform_sdk.learning_core_quick_memory_read_adapter import (
    build_quick_memory_response,
    build_quick_memory_review_queue_response,
)
from platform_sdk.learning_core_study_session_application import (
    cancel_learning_core_session_response as build_learning_core_cancel_session_response,
    log_learning_core_session_response as build_learning_core_log_session_response,
)


def cancel_session_response(user_id: int, session_id) -> tuple[dict, int]:
    return run_with_legacy_cross_service_fallback(
        upstream_name='learning-core-service',
        action='study-session-cancel',
        primary=lambda: cancel_learning_core_study_session_response(user_id, session_id),
        fallback=lambda: build_learning_core_cancel_session_response(user_id, session_id),
    )


def log_session_response(user_id: int, body: dict | None) -> tuple[dict, int]:
    payload = body or {}
    return run_with_legacy_cross_service_fallback(
        upstream_name='learning-core-service',
        action='study-session-log',
        primary=lambda: log_learning_core_study_session_response(user_id, payload),
        fallback=lambda: build_learning_core_log_session_response(user_id, payload),
    )
