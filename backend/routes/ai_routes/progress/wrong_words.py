from services.ai_wrong_words_service import (
    build_wrong_words_response as _service_build_wrong_words_response,
    clear_wrong_word_response as _service_clear_wrong_word_response,
    clear_wrong_words_response as _service_clear_wrong_words_response,
    sync_wrong_words_response as _service_sync_wrong_words_response,
)


@ai_bp.route('/wrong-words', methods=['GET'])
@token_required
def get_wrong_words(current_user: User):
    """Get all wrong words for the current user from the backend."""
    payload, status = _service_build_wrong_words_response(
        current_user.id,
        search_value=request.args.get('search'),
        detail_mode=request.args.get('details'),
    )
    return jsonify(payload), status


# ── POST /api/wrong-words/sync ──────────────────────────────────────────────

@ai_bp.route('/wrong-words/sync', methods=['POST'])
@token_required
def sync_wrong_words(current_user: User):
    """Sync wrong words from client localStorage to backend DB."""
    payload, status = _service_sync_wrong_words_response(
        current_user.id,
        request.get_json() or {},
    )
    return jsonify(payload), status


@ai_bp.route('/wrong-words/<word>', methods=['DELETE'])
@token_required
def delete_wrong_word(current_user: User, word: str):
    """Clear pending status for a wrong word without deleting its history."""
    payload, status = _service_clear_wrong_word_response(current_user.id, word)
    return jsonify(payload), status


@ai_bp.route('/wrong-words', methods=['DELETE'])
@token_required
def clear_wrong_words(current_user: User):
    """Clear pending wrong-word state for all words without deleting history."""
    payload, status = _service_clear_wrong_words_response(current_user.id)
    return jsonify(payload), status


# ── POST /api/ai/log-session ─────────────────────────────────────────────────
