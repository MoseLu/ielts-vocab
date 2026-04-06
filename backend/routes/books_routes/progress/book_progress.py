from services.books_catalog_endpoint_service import (
    build_books_stats_response,
    build_categories_response,
    build_levels_response,
)
from services.books_progress_service import (
    build_book_progress_response,
    build_book_words_response,
    build_chapter_progress_response,
    build_chapter_words_response,
    build_user_progress_response,
    save_book_progress_response,
    save_chapter_progress_response,
)


@books_bp.route('/<book_id>/chapters/<int:chapter_id>', methods=['GET'])
def get_chapter_words(book_id, chapter_id):
    payload, status = build_chapter_words_response(book_id, chapter_id)
    return jsonify(payload), status


@books_bp.route('/<book_id>/words', methods=['GET'])
def get_book_words(book_id):
    payload, status = build_book_words_response(
        book_id,
        page=request.args.get('page', 1, type=int),
        per_page=request.args.get('per_page', 100, type=int),
    )
    return jsonify(payload), status


@books_bp.route('/categories', methods=['GET'])
def get_categories():
    payload, status = build_categories_response()
    return jsonify(payload), status


@books_bp.route('/levels', methods=['GET'])
def get_levels():
    payload, status = build_levels_response()
    return jsonify(payload), status


@books_bp.route('/stats', methods=['GET'])
def get_books_stats():
    payload, status = build_books_stats_response()
    return jsonify(payload), status


@books_bp.route('/progress', methods=['GET'])
@token_required
def get_user_progress(current_user):
    payload, status = build_user_progress_response(current_user.id)
    return jsonify(payload), status


@books_bp.route('/progress/<book_id>', methods=['GET'])
@token_required
def get_book_progress(current_user, book_id):
    payload, status = build_book_progress_response(current_user.id, book_id)
    return jsonify(payload), status


@books_bp.route('/progress', methods=['POST'])
@token_required
def save_progress(current_user):
    payload, status = save_book_progress_response(current_user.id, request.get_json())
    return jsonify(payload), status


@books_bp.route('/<book_id>/chapters/progress', methods=['GET'])
@token_required
def get_chapter_progress(current_user, book_id):
    payload, status = build_chapter_progress_response(current_user.id, book_id)
    return jsonify(payload), status


@books_bp.route('/<book_id>/chapters/<int:chapter_id>/progress', methods=['POST'])
@token_required
def save_chapter_progress(current_user, book_id, chapter_id):
    payload, status = save_chapter_progress_response(
        current_user.id,
        book_id,
        chapter_id,
        request.get_json(),
    )
    return jsonify(payload), status
