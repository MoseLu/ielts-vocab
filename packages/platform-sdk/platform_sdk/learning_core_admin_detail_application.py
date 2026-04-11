from __future__ import annotations

from datetime import datetime

from platform_sdk.books_user_state_repository_adapter import (
    list_user_book_progress_rows,
    list_user_chapter_progress_rows,
)
from platform_sdk.learning_core_personalization_repository_adapter import (
    list_user_favorite_words,
)
from platform_sdk.learning_repository_adapters import learning_event_repository


def _parse_dt(value, *, fallback: datetime) -> datetime:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str) and value.strip():
        return datetime.fromisoformat(value.replace('Z', '+00:00')).replace(tzinfo=None)
    return fallback


def list_internal_admin_book_progress_response(user_id: int) -> tuple[dict, int]:
    return {
        'progress': [row.to_dict() for row in list_user_book_progress_rows(user_id)],
    }, 200


def list_internal_admin_favorite_words_response(user_id: int) -> tuple[dict, int]:
    return {
        'favorite_words': [row.to_dict() for row in list_user_favorite_words(user_id)],
    }, 200


def list_internal_admin_chapter_progress_response(user_id: int, args) -> tuple[dict, int]:
    book_id = (args.get('book_id') or '').strip() or None
    limit_raw = args.get('limit')
    limit = None
    if limit_raw not in (None, ''):
        try:
            limit = max(1, min(500, int(limit_raw)))
        except (TypeError, ValueError):
            return {'error': 'limit must be an integer'}, 400

    rows = list_user_chapter_progress_rows(user_id, book_id=book_id)
    rows.sort(key=lambda row: row.updated_at or datetime.min, reverse=True)
    if limit is not None:
        rows = rows[:limit]
    return {
        'chapter_progress': [row.to_dict() for row in rows],
    }, 200


def list_internal_admin_session_word_events_response(user_id: int, args) -> tuple[dict, int]:
    now = datetime.utcnow()
    start_at = _parse_dt(args.get('start_at'), fallback=now)
    end_at = _parse_dt(args.get('end_at'), fallback=now)
    if end_at < start_at:
        return {'error': 'end_at must be greater than or equal to start_at'}, 400

    events = learning_event_repository.list_user_learning_events_in_window(
        user_id,
        start_at=start_at,
        end_at=end_at,
    )
    return {
        'events': [
            row.to_dict()
            for row in events
            if row.word and row.event_type in ('quick_memory_review', 'wrong_word_recorded')
        ],
    }, 200
