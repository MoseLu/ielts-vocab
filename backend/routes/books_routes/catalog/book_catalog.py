from flask import jsonify, request

from routes.middleware import token_required
from services.books_catalog_service import (
    _build_global_word_search_catalog,
    build_book_chapters_response,
    build_book_response,
    build_books_response,
    build_search_words_response,
    get_book_chapter_count as _get_book_chapter_count,
    get_book_group_count as _get_book_group_count,
    get_book_word_count as _get_book_word_count,
    load_book_chapters,
    load_book_vocabulary,
    serialize_effective_book_progress as _serialize_effective_book_progress,
)
from services.books_confusable_service import (
    CONFUSABLE_MATCH_BOOK_ID,
    create_confusable_custom_chapters_response as _create_confusable_custom_chapters,
)


@books_bp.route('', methods=['GET'])
def get_books():
    payload, status = build_books_response(
        category=request.args.get('category'),
        level=request.args.get('level'),
        study_type=request.args.get('study_type'),
    )
    return jsonify(payload), status


@books_bp.route('/search', methods=['GET'])
def search_words():
    payload, status = build_search_words_response(
        raw_query=request.args.get('q'),
        limit_value=request.args.get('limit'),
    )
    return jsonify(payload), status


@books_bp.route('/<book_id>', methods=['GET'])
def get_book(book_id):
    payload, status = build_book_response(book_id)
    return jsonify(payload), status


@books_bp.route(f'/{CONFUSABLE_MATCH_BOOK_ID}/custom-chapters', methods=['POST'])
@token_required
def create_confusable_custom_chapters(current_user):
    data = request.get_json() or {}
    payload, status = _create_confusable_custom_chapters(current_user.id, data.get('groups'))
    return jsonify(payload), status


@books_bp.route('/<book_id>/chapters', methods=['GET'])
def get_book_chapters(book_id):
    payload, status = build_book_chapters_response(book_id)
    return jsonify(payload), status
