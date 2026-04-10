from __future__ import annotations

from flask import Blueprint, jsonify, request

from platform_sdk.learning_core_context_application import build_learning_core_context_payload
from platform_sdk.learning_core_events_application import record_internal_learning_event_response
from platform_sdk.learning_core_library_application import (
    add_my_book_response,
    build_my_books_response,
    remove_my_book_response,
    save_chapter_mode_progress_response,
)
from platform_sdk.learning_core_stats_application import build_learning_core_learning_stats_response
from platform_sdk.learning_core_personalization_application import (
    FAVORITES_BOOK_ID,
    add_familiar_word,
    add_favorite_word,
    get_familiar_status_words,
    get_favorite_status_words,
    remove_familiar_word,
    remove_favorite_word,
)
from platform_sdk.learning_core_progress_application import (
    build_book_progress_response,
    build_chapter_progress_response,
    build_user_progress_response,
    get_legacy_progress_for_day,
    list_legacy_progress,
    save_book_progress_response,
    save_chapter_progress_response,
    save_legacy_progress,
)
from routes.middleware import token_required


learning_core_bp = Blueprint('learning_core', __name__)


@learning_core_bp.route('/internal/learning/context', methods=['GET'])
@token_required
def get_internal_learning_context(current_user):
    return jsonify(build_learning_core_context_payload(current_user.id)), 200


@learning_core_bp.route('/internal/learning/stats', methods=['GET'])
@token_required
def get_internal_learning_stats(current_user):
    payload, status = build_learning_core_learning_stats_response(
        current_user.id,
        days=min(int(request.args.get('days', 30)), 90),
        book_id_filter=request.args.get('book_id') or None,
        mode_filter_raw=request.args.get('mode') or None,
    )
    return jsonify(payload), status


@learning_core_bp.route('/internal/learning/events', methods=['POST'])
@token_required
def create_internal_learning_event(current_user):
    payload, status = record_internal_learning_event_response(
        current_user.id,
        request.get_json(silent=True),
    )
    return jsonify(payload), status


@learning_core_bp.route('/api/progress', methods=['GET'])
@token_required
def get_all_progress(current_user):
    return jsonify({'progress': list_legacy_progress(current_user.id)}), 200


@learning_core_bp.route('/api/progress', methods=['POST'])
@token_required
def save_progress(current_user):
    try:
        progress = save_legacy_progress(current_user.id, request.get_json(silent=True) or {})
    except ValueError as error:
        return jsonify({'error': str(error)}), 400
    return jsonify({'message': 'Progress saved', 'progress': progress}), 200


@learning_core_bp.route('/api/progress/<int:day>', methods=['GET'])
@token_required
def get_day_progress(current_user, day):
    progress = get_legacy_progress_for_day(current_user.id, day)
    if not progress:
        return jsonify({'error': 'No progress found for this day'}), 404
    return jsonify({'progress': progress}), 200


@learning_core_bp.route('/api/books/progress', methods=['GET'])
@token_required
def get_user_progress(current_user):
    payload, status = build_user_progress_response(current_user.id)
    return jsonify(payload), status


@learning_core_bp.route('/api/books/progress/<book_id>', methods=['GET'])
@token_required
def get_book_progress(current_user, book_id):
    payload, status = build_book_progress_response(current_user.id, book_id)
    return jsonify(payload), status


@learning_core_bp.route('/api/books/progress', methods=['POST'])
@token_required
def save_book_progress(current_user):
    payload, status = save_book_progress_response(current_user.id, request.get_json(silent=True))
    return jsonify(payload), status


@learning_core_bp.route('/api/books/<book_id>/chapters/progress', methods=['GET'])
@token_required
def get_chapter_progress(current_user, book_id):
    payload, status = build_chapter_progress_response(current_user.id, book_id)
    return jsonify(payload), status


@learning_core_bp.route('/api/books/<book_id>/chapters/<int:chapter_id>/progress', methods=['POST'])
@token_required
def save_chapter_progress(current_user, book_id, chapter_id):
    payload, status = save_chapter_progress_response(
        current_user.id,
        book_id,
        chapter_id,
        request.get_json(silent=True),
    )
    return jsonify(payload), status


@learning_core_bp.route('/api/books/<book_id>/chapters/<int:chapter_id>/mode-progress', methods=['POST'])
@token_required
def save_chapter_mode_progress(current_user, book_id, chapter_id):
    payload, status = save_chapter_mode_progress_response(
        current_user.id,
        book_id,
        chapter_id,
        request.get_json(silent=True) or {},
    )
    return jsonify(payload), status


@learning_core_bp.route('/api/books/my', methods=['GET'])
@token_required
def get_my_books(current_user):
    payload, status = build_my_books_response(current_user.id)
    return jsonify(payload), status


@learning_core_bp.route('/api/books/my', methods=['POST'])
@token_required
def add_my_book(current_user):
    payload, status = add_my_book_response(current_user.id, request.get_json(silent=True) or {})
    return jsonify(payload), status


@learning_core_bp.route('/api/books/my/<book_id>', methods=['DELETE'])
@token_required
def remove_my_book(current_user, book_id):
    payload, status = remove_my_book_response(current_user.id, book_id)
    return jsonify(payload), status


@learning_core_bp.route('/api/books/favorites/status', methods=['POST'])
@token_required
def get_favorite_status(current_user):
    payload = request.get_json(silent=True) or {}
    return jsonify({
        'words': get_favorite_status_words(current_user.id, payload.get('words')),
        'book_id': FAVORITES_BOOK_ID,
    }), 200


@learning_core_bp.route('/api/books/favorites', methods=['POST'])
@token_required
def add_favorite_word_route(current_user):
    try:
        payload = add_favorite_word(current_user.id, request.get_json(silent=True) or {})
    except ValueError as error:
        return jsonify({'error': str(error)}), 400
    return jsonify(payload), 200


@learning_core_bp.route('/api/books/favorites', methods=['DELETE'])
@token_required
def remove_favorite_word_route(current_user):
    try:
        payload = remove_favorite_word(
            current_user.id,
            (request.get_json(silent=True) or {}).get('word'),
        )
    except ValueError as error:
        return jsonify({'error': str(error)}), 400
    return jsonify(payload), 200


@learning_core_bp.route('/api/books/familiar/status', methods=['POST'])
@token_required
def get_familiar_status(current_user):
    payload = request.get_json(silent=True) or {}
    return jsonify({'words': get_familiar_status_words(current_user.id, payload.get('words'))}), 200


@learning_core_bp.route('/api/books/familiar', methods=['POST'])
@token_required
def add_familiar_word_route(current_user):
    try:
        payload = add_familiar_word(current_user.id, request.get_json(silent=True) or {})
    except ValueError as error:
        return jsonify({'error': str(error)}), 400
    return jsonify(payload), 200


@learning_core_bp.route('/api/books/familiar', methods=['DELETE'])
@token_required
def remove_familiar_word_route(current_user):
    try:
        payload = remove_familiar_word(
            current_user.id,
            (request.get_json(silent=True) or {}).get('word'),
        )
    except ValueError as error:
        return jsonify({'error': str(error)}), 400
    return jsonify(payload), 200
