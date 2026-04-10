from __future__ import annotations

from services.books_registry_service import get_vocab_book_title_map
from services.books_structure_service import load_book_chapters
from services.learning_stats_service import build_learning_stats_payload
from services.local_time import utc_now_naive
from services.study_sessions import normalize_chapter_id, start_or_reuse_study_session

from platform_sdk.ai_learning_summary_support import (
    alltime_words_display,
    calc_streak_days,
    chapter_title_map,
    quick_memory_word_stats,
)

_PENDING_SESSION_REUSE_WINDOW_SECONDS = 5


def _resolve_book_title_map() -> dict[str, str]:
    return get_vocab_book_title_map()


def _resolve_chapter_title_map(book_id: str) -> dict:
    return chapter_title_map(book_id, load_book_chapters=load_book_chapters)


def _resolve_quick_memory_word_stats(user_id: int) -> dict:
    return quick_memory_word_stats(user_id, now_utc=utc_now_naive())


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
    payload = build_learning_stats_payload(
        user_id=user_id,
        days=days,
        book_id_filter=book_id_filter,
        mode_filter_raw=mode_filter_raw,
        now_utc=utc_now_naive(),
        book_title_map=_resolve_book_title_map(),
        chapter_title_map_resolver=_resolve_chapter_title_map,
        alltime_words_display_resolver=alltime_words_display,
        quick_memory_word_stats_resolver=_resolve_quick_memory_word_stats,
        streak_days_resolver=calc_streak_days,
    )
    return payload, 200


def start_session_response(user_id: int, body: dict | None) -> tuple[dict, int]:
    payload = body or {}
    session = start_or_reuse_study_session(
        user_id=user_id,
        mode=_normalize_start_session_mode(payload.get('mode') or 'smart'),
        book_id=payload.get('bookId') or None,
        chapter_id=normalize_chapter_id(payload.get('chapterId')),
        reuse_window_seconds=_PENDING_SESSION_REUSE_WINDOW_SECONDS,
    )
    return {'sessionId': session.id}, 201
