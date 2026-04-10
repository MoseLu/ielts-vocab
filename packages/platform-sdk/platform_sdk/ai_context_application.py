from __future__ import annotations

from platform_sdk.ai_assistant_memory_support import load_memory
from platform_sdk.learner_profile_application_support import build_learner_profile_response as build_local_learner_profile_response
from platform_sdk.learning_core_context_application import (
    build_learning_core_context_payload,
)
from platform_sdk.learning_core_internal_client import fetch_learning_core_context_payload


def build_context_payload(user_id: int) -> dict:
    try:
        core_payload = fetch_learning_core_context_payload(user_id)
    except Exception:
        core_payload = build_learning_core_context_payload(user_id)
    learner_profile, _status = build_local_learner_profile_response(
        user_id,
        target_date=None,
        view='full',
    )
    return {
        **core_payload,
        'learnerProfile': learner_profile,
        'activityTimeline': {
            'summary': learner_profile.get('activity_summary') or {},
            'source_breakdown': learner_profile.get('activity_source_breakdown') or [],
            'event_breakdown': learner_profile.get('activity_event_breakdown') or [],
            'recent_events': learner_profile.get('recent_activity') or [],
        },
        'memory': load_memory(user_id),
    }


def build_learner_profile_response(
    user_id: int,
    *,
    target_date: str | None,
    view: str,
) -> tuple[dict, int]:
    return build_local_learner_profile_response(
        user_id,
        target_date=target_date,
        view=view,
    )
