from flask import jsonify, request

from routes.middleware import token_required
from services.books_favorites_service import (
    FAVORITES_BOOK_ID,
    FAVORITES_BOOK_TITLE,
    FAVORITES_CHAPTER_ID,
    FAVORITES_CHAPTER_TITLE,
    _build_favorites_book_payload,
    _build_favorites_chapters_payload,
    _favorite_word_count,
    _favorite_words_query,
    _is_favorites_book,
    _normalize_favorite_word,
    _serialize_favorite_words,
    add_favorite_word as _add_favorite_word,
    get_favorite_status_words,
    remove_favorite_word as _remove_favorite_word,
)


@books_bp.route('/favorites/status', methods=['POST'])
@token_required
def get_favorite_status(current_user):
    data = request.get_json(silent=True) or {}
    return jsonify({
        'words': get_favorite_status_words(current_user.id, data.get('words')),
        'book_id': FAVORITES_BOOK_ID,
    }), 200


@books_bp.route('/favorites', methods=['POST'])
@token_required
def add_favorite_word(current_user):
    data = request.get_json(silent=True) or {}
    try:
        result = _add_favorite_word(current_user.id, data)
    except ValueError as error:
        return jsonify({'error': str(error)}), 400

    return jsonify(result), 200


@books_bp.route('/favorites', methods=['DELETE'])
@token_required
def remove_favorite_word(current_user):
    data = request.get_json(silent=True) or {}
    try:
        result = _remove_favorite_word(current_user.id, data.get('word'))
    except ValueError as error:
        return jsonify({'error': str(error)}), 400

    return jsonify(result), 200
