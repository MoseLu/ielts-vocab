from flask import jsonify, request

from routes.middleware import token_required
from services.books_confusable_service import (
    CONFUSABLE_MATCH_BOOK_ID,
    update_confusable_custom_chapter_response,
)
from services.books_library_service import (
    add_my_book_response as _service_add_my_book_response,
    build_word_examples_response as _service_build_word_examples_response,
    build_my_books_response as _service_build_my_books_response,
    remove_my_book_response as _service_remove_my_book_response,
    save_chapter_mode_progress_response as _service_save_chapter_mode_progress_response,
)


@books_bp.route('/<book_id>/chapters/<chapter_id>/mode-progress', methods=['POST'])
@token_required
def save_chapter_mode_progress(current_user, book_id, chapter_id):
    """Save per-mode accuracy for a specific chapter. Each mode is stored independently."""
    payload, status = _service_save_chapter_mode_progress_response(
        current_user.id,
        book_id,
        chapter_id,
        request.get_json() or {},
    )
    return jsonify(payload), status


# ── User's Added Books ──────────────────────────────────────────────────────────

@books_bp.route('/my', methods=['GET'])
@token_required
def get_my_books(current_user):
    """Get all books added by the user."""
    payload, status = _service_build_my_books_response(current_user.id)
    return jsonify(payload), status


@books_bp.route('/my', methods=['POST'])
@token_required
def add_my_book(current_user):
    """Add a book to the user's list."""
    payload, status = _service_add_my_book_response(
        current_user.id,
        request.get_json() or {},
    )
    return jsonify(payload), status


@books_bp.route('/my/<book_id>', methods=['DELETE'])
@token_required
def remove_my_book(current_user, book_id):
    """Remove a book from the user's list."""
    payload, status = _service_remove_my_book_response(current_user.id, book_id)
    return jsonify(payload), status


@books_bp.route(f'/{CONFUSABLE_MATCH_BOOK_ID}/custom-chapters/<int:chapter_id>', methods=['PUT'])
@token_required
def update_confusable_custom_chapter(current_user, chapter_id):
    data = request.get_json() or {}
    payload, status = update_confusable_custom_chapter_response(
        current_user.id,
        chapter_id,
        data.get('words'),
    )
    return jsonify(payload), status


# ── GET /api/books/examples ───────────────────────────────────────────────────

@books_bp.route('/examples', methods=['GET'])
def get_word_examples():
    payload, status = _service_build_word_examples_response(
        single_word=request.args.get('word'),
        batch_words=request.args.get('words'),
    )
    return jsonify(payload), status
