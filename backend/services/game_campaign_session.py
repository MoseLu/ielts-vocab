from __future__ import annotations

from services import game_session_service
from services.game_theme_catalog_service import build_theme_state_context
from services.word_mastery_campaign_state import build_game_practice_state
from services.word_mastery_support import scope_key


def start_game_campaign_session(
    user_id: int,
    *,
    book_id: str | None = None,
    chapter_id: str | None = None,
    day: int | None = None,
    theme_id: str | None = None,
    theme_chapter_id: str | None = None,
    task: str | None = None,
    dimension: str | None = None,
    enabled_boosts: dict | None = None,
) -> dict:
    scope_state = build_game_practice_state(
        user_id,
        book_id=book_id,
        chapter_id=chapter_id,
        day=day,
        theme_id=theme_id,
        theme_chapter_id=theme_chapter_id,
        task=task,
        dimension=dimension,
    )
    theme_context = build_theme_state_context(theme_id=theme_id, theme_chapter_id=theme_chapter_id)
    scope_book_id = theme_context['scopeBookId'] if theme_context else book_id
    scope_chapter_id = theme_context['scopeChapterId'] if theme_context else chapter_id
    scope_day = None if theme_context else day
    launcher = scope_state.get('launcher') or {}
    game_session_service.start_game_session(
        user_id,
        scope_key=scope_key(book_id=scope_book_id, chapter_id=scope_chapter_id, day=scope_day),
        book_id=scope_book_id,
        chapter_id=scope_chapter_id,
        day=scope_day,
        lesson_id=str(launcher.get('lessonId') or 'lesson-1'),
        segment_index=int(launcher.get('segmentIndex') or 0),
        enabled_boosts=enabled_boosts,
    )
    return build_game_practice_state(
        user_id,
        book_id=book_id,
        chapter_id=chapter_id,
        day=day,
        theme_id=theme_id,
        theme_chapter_id=theme_chapter_id,
        task=task,
        dimension=dimension,
    )
