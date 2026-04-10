from __future__ import annotations

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
    try:
        return cancel_learning_core_study_session_response(user_id, session_id)
    except Exception:
        return build_learning_core_cancel_session_response(user_id, session_id)


def log_session_response(user_id: int, body: dict | None) -> tuple[dict, int]:
    payload = body or {}
    try:
        return log_learning_core_study_session_response(user_id, payload)
    except Exception:
        return build_learning_core_log_session_response(user_id, payload)
