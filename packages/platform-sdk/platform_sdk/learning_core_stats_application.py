from __future__ import annotations

from platform_sdk.ai_learning_summary_support import (
    alltime_words_display,
    calc_streak_days,
    chapter_title_map,
    quick_memory_word_stats,
)
from platform_sdk.catalog_provider_adapter import get_vocab_book_title_map, load_book_chapters
from platform_sdk.learning_stats_payload_support import build_learning_stats_payload
from platform_sdk.local_time_support import utc_now_naive


def _resolve_book_title_map() -> dict[str, str]:
    return get_vocab_book_title_map()


def _resolve_chapter_title_map(book_id: str) -> dict:
    return chapter_title_map(book_id, load_book_chapters=load_book_chapters)


def _resolve_quick_memory_word_stats(user_id: int) -> dict:
    return quick_memory_word_stats(user_id, now_utc=utc_now_naive())


def build_learning_core_learning_stats_response(
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
