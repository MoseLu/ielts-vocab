from __future__ import annotations

from flask import Blueprint, jsonify, request

from platform_sdk.learning_core_context_application import build_learning_core_context_payload
from platform_sdk.learning_core_admin_detail_application import (
    list_internal_admin_book_progress_response,
    list_internal_admin_chapter_progress_response,
    list_internal_admin_favorite_words_response,
    list_internal_admin_session_word_events_response,
)
from platform_sdk.learning_core_notes_context_application import (
    list_internal_notes_study_sessions_response,
    list_internal_notes_wrong_words_response,
)
from platform_sdk.learning_core_events_application import record_internal_learning_event_response
from platform_sdk.learning_core_library_application import (
    add_my_book_response,
    build_my_books_response,
    remove_my_book_response,
    save_chapter_mode_progress_response,
)
from platform_sdk.learning_core_progress_sync_application import (
    build_learning_core_smart_stats_response,
    sync_learning_core_quick_memory_response,
    sync_learning_core_smart_stats_response,
)
from platform_sdk.learning_core_quick_memory_application import (
    build_learning_core_quick_memory_response,
    build_learning_core_quick_memory_review_queue_response,
)
from platform_sdk.learning_core_stats_application import build_learning_core_learning_stats_response
from platform_sdk.learning_core_study_session_application import (
    cancel_learning_core_session_response,
    log_learning_core_session_response,
    start_learning_core_session_response,
)
from platform_sdk.learning_core_tool_data_application import (
    count_internal_wrong_words_for_ai_response,
    list_internal_chapter_progress_for_ai_response,
    list_internal_wrong_words_for_ai_response,
)
from platform_sdk.learning_core_wrong_words_application import (
    build_learning_core_wrong_words_response,
    clear_learning_core_wrong_word_response,
    clear_learning_core_wrong_words_response,
    sync_learning_core_wrong_words_response,
)
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


@learning_core_bp.route('/internal/learning/notes-context/study-sessions', methods=['GET'])
@token_required
def get_internal_notes_context_study_sessions(current_user):
    payload, status = list_internal_notes_study_sessions_response(current_user.id, request.args)
    return jsonify(payload), status


@learning_core_bp.route('/internal/learning/notes-context/wrong-words', methods=['GET'])
@token_required
def get_internal_notes_context_wrong_words(current_user):
    payload, status = list_internal_notes_wrong_words_response(current_user.id, request.args)
    return jsonify(payload), status


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


@learning_core_bp.route('/internal/learning/study-sessions/start', methods=['POST'])
@token_required
def post_internal_study_session_start(current_user):
    payload, status = start_learning_core_session_response(
        current_user.id,
        request.get_json(silent=True),
    )
    return jsonify(payload), status


@learning_core_bp.route('/internal/learning/study-sessions/log', methods=['POST'])
@token_required
def post_internal_study_session_log(current_user):
    payload, status = log_learning_core_session_response(
        current_user.id,
        request.get_json(silent=True),
    )
    return jsonify(payload), status


@learning_core_bp.route('/internal/learning/study-sessions/cancel', methods=['POST'])
@token_required
def post_internal_study_session_cancel(current_user):
    payload, status = cancel_learning_core_session_response(
        current_user.id,
        (request.get_json(silent=True) or {}).get('sessionId'),
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


@learning_core_bp.route('/internal/learning/admin/book-progress', methods=['GET'])
@token_required
def get_internal_admin_book_progress(current_user):
    payload, status = list_internal_admin_book_progress_response(current_user.id)
    return jsonify(payload), status


@learning_core_bp.route('/internal/learning/admin/favorite-words', methods=['GET'])
@token_required
def get_internal_admin_favorite_words(current_user):
    payload, status = list_internal_admin_favorite_words_response(current_user.id)
    return jsonify(payload), status


@learning_core_bp.route('/internal/learning/admin/chapter-progress', methods=['GET'])
@token_required
def get_internal_admin_chapter_progress(current_user):
    payload, status = list_internal_admin_chapter_progress_response(current_user.id, request.args)
    return jsonify(payload), status


@learning_core_bp.route('/internal/learning/admin/session-word-events', methods=['GET'])
@token_required
def get_internal_admin_session_word_events(current_user):
    payload, status = list_internal_admin_session_word_events_response(current_user.id, request.args)
    return jsonify(payload), status


@learning_core_bp.route('/internal/learning/ai-tool/wrong-words', methods=['GET'])
@token_required
def get_internal_ai_tool_wrong_words(current_user):
    payload, status = list_internal_wrong_words_for_ai_response(current_user.id, request.args)
    return jsonify(payload), status


@learning_core_bp.route('/internal/learning/ai-tool/chapter-progress', methods=['GET'])
@token_required
def get_internal_ai_tool_chapter_progress(current_user):
    payload, status = list_internal_chapter_progress_for_ai_response(current_user.id, request.args)
    return jsonify(payload), status


@learning_core_bp.route('/internal/learning/ai-tool/wrong-word-count', methods=['GET'])
@token_required
def get_internal_ai_tool_wrong_word_count(current_user):
    payload, status = count_internal_wrong_words_for_ai_response(current_user.id)
    return jsonify(payload), status


@learning_core_bp.route('/internal/learning/quick-memory', methods=['GET'])
@token_required
def get_internal_quick_memory(current_user):
    payload, status = build_learning_core_quick_memory_response(current_user.id)
    return jsonify(payload), status


@learning_core_bp.route('/internal/learning/quick-memory/review-queue', methods=['GET'])
@token_required
def get_internal_quick_memory_review_queue(current_user):
    payload, status = build_learning_core_quick_memory_review_queue_response(
        current_user.id,
        request.args,
    )
    return jsonify(payload), status


@learning_core_bp.route('/internal/learning/quick-memory/sync', methods=['POST'])
@token_required
def post_internal_quick_memory_sync(current_user):
    payload, status = sync_learning_core_quick_memory_response(
        current_user.id,
        request.get_json(silent=True),
    )
    return jsonify(payload), status


@learning_core_bp.route('/internal/learning/smart-stats', methods=['GET'])
@token_required
def get_internal_smart_stats(current_user):
    payload, status = build_learning_core_smart_stats_response(current_user.id)
    return jsonify(payload), status


@learning_core_bp.route('/internal/learning/smart-stats/sync', methods=['POST'])
@token_required
def post_internal_smart_stats_sync(current_user):
    payload, status = sync_learning_core_smart_stats_response(
        current_user.id,
        request.get_json(silent=True),
    )
    return jsonify(payload), status


@learning_core_bp.route('/internal/learning/wrong-words', methods=['GET'])
@token_required
def get_internal_wrong_words(current_user):
    payload, status = build_learning_core_wrong_words_response(
        current_user.id,
        search_value=request.args.get('search'),
        detail_mode=request.args.get('details'),
    )
    return jsonify(payload), status


@learning_core_bp.route('/internal/learning/wrong-words/sync', methods=['POST'])
@token_required
def post_internal_wrong_words_sync(current_user):
    payload, status = sync_learning_core_wrong_words_response(
        current_user.id,
        request.get_json(silent=True),
    )
    return jsonify(payload), status


@learning_core_bp.route('/internal/learning/wrong-words/clear', methods=['POST'])
@token_required
def post_internal_wrong_words_clear(current_user):
    word = (request.get_json(silent=True) or {}).get('word')
    if isinstance(word, str) and word.strip():
        payload, status = clear_learning_core_wrong_word_response(current_user.id, word.strip())
    else:
        payload, status = clear_learning_core_wrong_words_response(current_user.id)
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


@learning_core_bp.route('/api/books/<book_id>/chapters/<chapter_id>/progress', methods=['POST'])
@token_required
def save_chapter_progress(current_user, book_id, chapter_id):
    payload, status = save_chapter_progress_response(
        current_user.id,
        book_id,
        chapter_id,
        request.get_json(silent=True),
    )
    return jsonify(payload), status


@learning_core_bp.route('/api/books/<book_id>/chapters/<chapter_id>/mode-progress', methods=['POST'])
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
