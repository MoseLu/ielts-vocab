from __future__ import annotations

from platform_sdk.learning_core_internal_client import fetch_learning_core_learning_stats_response
from platform_sdk.learning_core_stats_application import build_learning_core_learning_stats_response
from platform_sdk.study_session_repository_adapter import (
    commit as commit_study_session,
    create_study_session,
    find_pending_session_in_window,
)
from platform_sdk.study_session_support import normalize_chapter_id, start_or_reuse_study_session

_PENDING_SESSION_REUSE_WINDOW_SECONDS = 5


def _normalize_start_session_mode(value) -> str:
    if isinstance(value, str):
        return value.strip()[:30] or 'smart'
    return 'smart'


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
    session = start_or_reuse_study_session(
        user_id=user_id,
        mode=_normalize_start_session_mode(payload.get('mode') or 'smart'),
        book_id=payload.get('bookId') or None,
        chapter_id=normalize_chapter_id(payload.get('chapterId')),
        reuse_window_seconds=_PENDING_SESSION_REUSE_WINDOW_SECONDS,
        find_pending_session_in_window=find_pending_session_in_window,
        create_study_session=create_study_session,
        commit=commit_study_session,
    )
    return {'sessionId': session.id}, 201
