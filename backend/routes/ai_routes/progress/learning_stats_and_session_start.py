from services.books_registry_service import get_vocab_book_title_map
from services.ai_text_support import parse_client_epoch_ms
from services.learning_stats_service import build_learning_stats_payload
from services.study_sessions import normalize_chapter_id, start_or_reuse_study_session


def _resolve_book_title_map() -> dict[str, str]:
    return get_vocab_book_title_map()


def _normalize_start_session_mode(value) -> str:
    if isinstance(value, str):
        return value.strip()[:30] or 'smart'
    return 'smart'


@ai_bp.route('/learning-stats', methods=['GET'])
@token_required
def get_learning_stats(current_user: User):
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


@ai_bp.route('/start-session', methods=['POST'])
@token_required
def start_session(current_user: User):
    """Create or reuse an empty placeholder session and return its id."""
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
