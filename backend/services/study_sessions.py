from __future__ import annotations

from datetime import datetime

from platform_sdk.study_session_support import (
    _get_session_effective_end,
    _get_session_total_duration_seconds,
    find_pending_session as _find_pending_session,
    get_live_pending_session_snapshot as _get_live_pending_session_snapshot,
    get_live_pending_window_duration_seconds,
    get_session_window_metrics,
    normalize_chapter_id,
    start_or_reuse_study_session as _start_or_reuse_study_session,
)
from services import learning_event_repository
from services import study_session_repository


def get_live_pending_session_snapshot(
    user_id: int,
    *,
    mode: str | None = None,
    book_id: str | None = None,
    chapter_id: str | None = None,
    since: datetime | None = None,
    now: datetime | None = None,
) -> dict | None:
    return _get_live_pending_session_snapshot(
        user_id,
        find_recent_open_placeholder_session=study_session_repository.find_recent_open_placeholder_session,
        newer_analytics_session_exists=study_session_repository.newer_analytics_session_exists,
        find_latest_session_activity_at=learning_event_repository.find_latest_session_activity_at,
        mode=mode,
        book_id=book_id,
        chapter_id=chapter_id,
        since=since,
        now=now,
    )


def find_pending_session(
    *,
    user_id: int,
    mode: str | None,
    book_id: str | None,
    chapter_id: str | None,
    started_at: datetime | None = None,
    window_seconds: int = 15,
):
    return _find_pending_session(
        user_id=user_id,
        mode=mode,
        book_id=book_id,
        chapter_id=chapter_id,
        find_pending_session_in_window=study_session_repository.find_pending_session_in_window,
        started_at=started_at,
        window_seconds=window_seconds,
    )


def start_or_reuse_study_session(
    *,
    user_id: int,
    mode: str,
    book_id: str | None,
    chapter_id: str | None,
    reuse_window_seconds: int,
):
    return _start_or_reuse_study_session(
        user_id=user_id,
        mode=mode,
        book_id=book_id,
        chapter_id=chapter_id,
        reuse_window_seconds=reuse_window_seconds,
        find_pending_session_in_window=study_session_repository.find_pending_session_in_window,
        create_study_session=study_session_repository.create_study_session,
        commit=study_session_repository.commit,
    )
