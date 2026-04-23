from __future__ import annotations

from functools import lru_cache


_PENDING_SESSION_REUSE_WINDOW_SECONDS = 5


@lru_cache(maxsize=1)
def _load_learning_stats_route_support():
    from services.ai_learning_summary_service import (
        alltime_words_display,
        calc_streak_days,
        chapter_title_map,
        quick_memory_word_stats,
    )
    from services.books_catalog_service import load_book_chapters
    from services.books_registry_service import get_vocab_book_title_map
    from services.learning_stats_service import build_learning_stats_payload
    from services.local_time import utc_naive_to_local_date_key, utc_now_naive

    return (
        alltime_words_display,
        build_learning_stats_payload,
        calc_streak_days,
        chapter_title_map,
        get_vocab_book_title_map,
        load_book_chapters,
        quick_memory_word_stats,
        utc_naive_to_local_date_key,
        utc_now_naive,
    )


@lru_cache(maxsize=1)
def _load_session_start_route_support():
    from services.ai_text_support import parse_client_epoch_ms
    from services.study_sessions import normalize_chapter_id, start_or_reuse_study_session

    return normalize_chapter_id, parse_client_epoch_ms, start_or_reuse_study_session


def _resolve_book_title_map() -> dict[str, str]:
    _, _, _, _, get_vocab_book_title_map, _, _, _, _ = _load_learning_stats_route_support()
    return get_vocab_book_title_map()


def _chapter_title_map(book_id: str) -> dict:
    _, _, _, chapter_title_map, _, load_book_chapters, _, _, _ = _load_learning_stats_route_support()
    try:
        return chapter_title_map(book_id, load_book_chapters=load_book_chapters)
    except Exception:
        return {}


def _calc_streak_days(user_id: int, reference_date: str | None = None) -> int:
    _, _, calc_streak_days, _, _, _, _, utc_naive_to_local_date_key, _ = _load_learning_stats_route_support()
    now_utc = utc_now_naive()
    effective_reference_date = reference_date or utc_naive_to_local_date_key(now_utc)
    return calc_streak_days(user_id, effective_reference_date)


def _quick_memory_word_stats(user_id: int):
    _, _, _, _, _, _, quick_memory_word_stats, _, _ = _load_learning_stats_route_support()
    return quick_memory_word_stats(user_id, now_utc=utc_now_naive())


def _normalize_start_session_mode(value) -> str:
    if isinstance(value, str):
        return value.strip()[:30] or 'smart'
    return 'smart'


@ai_bp.route('/learning-stats', methods=['GET'])
@token_required
def get_learning_stats(current_user: User):
    _, build_learning_stats_payload, _, _, _, _, _, _, _ = _load_learning_stats_route_support()
    payload = build_learning_stats_payload(
        user_id=current_user.id,
        days=min(int(request.args.get('days', 30)), 90),
        book_id_filter=request.args.get('book_id') or None,
        mode_filter_raw=request.args.get('mode') or None,
        now_utc=utc_now_naive(),
        book_title_map=_resolve_book_title_map(),
        chapter_title_map_resolver=_chapter_title_map,
        alltime_words_display_resolver=_alltime_words_display,
        quick_memory_word_stats_resolver=_quick_memory_word_stats,
        streak_days_resolver=_calc_streak_days,
    )
    return jsonify(payload)


def _alltime_words_display(user_id: int, chapter_words_sum: int) -> int:
    alltime_words_display, _, _, _, _, _, _, _, _ = _load_learning_stats_route_support()
    return alltime_words_display(user_id, chapter_words_sum)


@ai_bp.route('/start-session', methods=['POST'])
@token_required
def start_session(current_user: User):
    normalize_chapter_id, parse_client_epoch_ms, start_or_reuse_study_session = _load_session_start_route_support()
    body = request.get_json() or {}
    session = start_or_reuse_study_session(
        user_id=current_user.id,
        mode=_normalize_start_session_mode(body.get('mode') or 'smart'),
        book_id=body.get('bookId') or None,
        chapter_id=normalize_chapter_id(body.get('chapterId')),
        reuse_window_seconds=_PENDING_SESSION_REUSE_WINDOW_SECONDS,
        started_at=parse_client_epoch_ms(body.get('startedAt')),
        force_new_session=bool(body.get('forceNewSession')),
    )
    return jsonify({'sessionId': session.id}), 201
