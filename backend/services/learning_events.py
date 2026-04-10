from __future__ import annotations

from platform_sdk.learning_event_support import (
    AI_TOOL_EVENT_TYPES,
    EVENT_LABELS,
    MODE_LABELS,
    SOURCE_LABELS,
    build_learning_activity_timeline as _build_learning_activity_timeline,
    record_learning_event as _record_learning_event,
)
from services import learning_event_repository
from services.local_time import resolve_local_day_window


def record_learning_event(**kwargs):
    return _record_learning_event(
        add_learning_event=learning_event_repository.add_learning_event,
        **kwargs,
    )


def build_learning_activity_timeline(user_id: int, target_date: str | None = None, limit: int = 12) -> dict:
    return _build_learning_activity_timeline(
        user_id,
        target_date=target_date,
        limit=limit,
        list_user_learning_events_in_window=learning_event_repository.list_user_learning_events_in_window,
        resolve_local_day_window=resolve_local_day_window,
    )
