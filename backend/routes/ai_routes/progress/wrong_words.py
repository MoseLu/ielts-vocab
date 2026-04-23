from __future__ import annotations

from functools import lru_cache


@lru_cache(maxsize=1)
def _load_wrong_word_route_support():
    from services.ai_wrong_words_service import (
        build_wrong_words_response,
        clear_wrong_word_response,
        clear_wrong_words_response,
        sync_wrong_words_response,
    )

    return (
        build_wrong_words_response,
        clear_wrong_word_response,
        clear_wrong_words_response,
        sync_wrong_words_response,
    )


@ai_bp.route('/wrong-words', methods=['GET'])
@token_required
def get_wrong_words(current_user: User):
    build_wrong_words_response, _, _, _ = _load_wrong_word_route_support()
    payload, status = build_wrong_words_response(
        current_user.id,
        search_value=request.args.get('search'),
        detail_mode=request.args.get('details'),
    )
    return jsonify(payload), status


@ai_bp.route('/wrong-words/sync', methods=['POST'])
@token_required
def sync_wrong_words(current_user: User):
    _, _, _, sync_wrong_words_response = _load_wrong_word_route_support()
    payload, status = sync_wrong_words_response(
        current_user.id,
        request.get_json() or {},
    )
    return jsonify(payload), status


@ai_bp.route('/wrong-words/<word>', methods=['DELETE'])
@token_required
def delete_wrong_word(current_user: User, word: str):
    _, clear_wrong_word_response, _, _ = _load_wrong_word_route_support()
    payload, status = clear_wrong_word_response(current_user.id, word)
    return jsonify(payload), status


@ai_bp.route('/wrong-words', methods=['DELETE'])
@token_required
def clear_wrong_words(current_user: User):
    _, _, clear_wrong_words_response, _ = _load_wrong_word_route_support()
    payload, status = clear_wrong_words_response(current_user.id)
    return jsonify(payload), status
