from __future__ import annotations

import logging

from platform_sdk.ai_assistant_memory_support import load_memory
from platform_sdk.ai_daily_summary_projection_support import (
    list_projected_daily_summaries_for_ai,
)
from platform_sdk.cross_service_boundary import legacy_cross_service_fallback_enabled
from platform_sdk.learner_profile_application_support import build_learner_profile_response as build_local_learner_profile_response
from platform_sdk.learning_core_context_application import (
    build_learning_core_context_payload,
)
from platform_sdk.learning_core_internal_client import fetch_learning_core_context_payload
from platform_sdk.notes_internal_client import list_recent_daily_summaries


def _empty_learning_core_context_payload() -> dict:
    return {
        'totalBooks': 0,
        'totalLearned': 0,
        'totalCorrect': 0,
        'totalWrong': 0,
        'accuracyRate': 0,
        'books': [],
        'wrongWords': [],
        'recentTrend': 'new',
        'recentSessions': [],
        'chapterSessionStats': [],
        'totalSessions': 0,
    }


def _serialize_daily_summary(summary) -> dict:
    generated_at = getattr(summary, 'generated_at', None)
    return {
        'id': int(getattr(summary, 'id', 0) or 0),
        'date': str(getattr(summary, 'date', '') or ''),
        'content': str(getattr(summary, 'content', '') or ''),
        'generated_at': generated_at.isoformat() if generated_at else None,
    }


def _load_recent_daily_summaries(user_id: int, *, limit: int = 7) -> list[dict]:
    try:
        return [
            _serialize_daily_summary(summary)
            for summary in list_recent_daily_summaries(user_id, limit=limit)
        ]
    except Exception as exc:
        projection_ready, projected_summaries = list_projected_daily_summaries_for_ai(user_id, limit=limit)
        if projection_ready:
            logging.warning('[Boundary] using projected notes summaries for AI context: %s', exc)
            return projected_summaries
        logging.warning('[Boundary] notes-service unavailable for AI context summaries, using empty snapshot: %s', exc)
        return []


def build_context_payload(user_id: int) -> dict:
    try:
        core_payload = fetch_learning_core_context_payload(user_id)
    except Exception as exc:
        if legacy_cross_service_fallback_enabled():
            logging.warning('[Boundary] using legacy local context fallback for learning-core: %s', exc)
            core_payload = build_learning_core_context_payload(user_id)
        else:
            logging.warning('[Boundary] learning-core unavailable for AI context, using empty snapshot: %s', exc)
            core_payload = _empty_learning_core_context_payload()
    learner_profile, _status = build_local_learner_profile_response(
        user_id,
        target_date=None,
        view='full',
    )
    recent_summaries = _load_recent_daily_summaries(user_id)
    return {
        **core_payload,
        'recentSummaries': recent_summaries,
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
