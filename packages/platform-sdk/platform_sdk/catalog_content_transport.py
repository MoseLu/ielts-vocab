from __future__ import annotations

from flask import Blueprint, jsonify, request

from platform_sdk.catalog_content_catalog_application import (
    build_book_chapters_response,
    build_book_response,
    build_book_words_response,
    build_books_response,
    build_books_stats_response,
    build_categories_response,
    build_chapter_words_response,
    build_levels_response,
    build_search_words_response,
    build_word_details_response,
    build_word_examples_response,
)
from platform_sdk.catalog_content_custom_books_application import (
    append_catalog_content_custom_book_chapters_response,
    create_catalog_content_custom_book_response,
    get_catalog_content_custom_book_response,
    list_catalog_content_custom_books_response,
)
from platform_sdk.catalog_content_confusable_application import (
    CONFUSABLE_MATCH_BOOK_ID,
    create_confusable_custom_chapters_response,
    resolve_optional_current_user,
    update_confusable_custom_chapter_response,
)
from routes.middleware import token_required


catalog_content_bp = Blueprint('catalog_content', __name__)


@catalog_content_bp.route('/api/books', methods=['GET'])
def get_books():
    payload, status = build_books_response(
        category=request.args.get('category'),
        level=request.args.get('level'),
        study_type=request.args.get('study_type'),
    )
    return jsonify(payload), status


@catalog_content_bp.route('/api/books/search', methods=['GET'])
def search_words():
    payload, status = build_search_words_response(
        raw_query=request.args.get('q'),
        limit_value=request.args.get('limit'),
    )
    return jsonify(payload), status


@catalog_content_bp.route('/api/books/categories', methods=['GET'])
def get_categories():
    payload, status = build_categories_response()
    return jsonify(payload), status


@catalog_content_bp.route('/api/books/levels', methods=['GET'])
def get_levels():
    payload, status = build_levels_response()
    return jsonify(payload), status


@catalog_content_bp.route('/api/books/stats', methods=['GET'])
def get_books_stats():
    payload, status = build_books_stats_response()
    return jsonify(payload), status


@catalog_content_bp.route('/api/books/examples', methods=['GET'])
def get_word_examples():
    payload, status = build_word_examples_response(
        single_word=request.args.get('word'),
        batch_words=request.args.get('words'),
    )
    return jsonify(payload), status


@catalog_content_bp.route('/api/books/word-details', methods=['GET'])
def get_word_details():
    payload, status = build_word_details_response(
        request.args.get('word'),
        resolve_optional_current_user(),
    )
    return jsonify(payload), status


@catalog_content_bp.route('/api/books/custom-books', methods=['POST'])
@token_required
def create_custom_book(current_user):
    payload, status = create_catalog_content_custom_book_response(
        current_user.id,
        request.get_json(silent=True),
    )
    return jsonify(payload), status


@catalog_content_bp.route('/api/books/custom-books', methods=['GET'])
@token_required
def list_custom_books(current_user):
    payload, status = list_catalog_content_custom_books_response(current_user.id)
    return jsonify(payload), status


@catalog_content_bp.route('/api/books/custom-books/<book_id>', methods=['GET'])
@token_required
def get_custom_book(current_user, book_id):
    payload, status = get_catalog_content_custom_book_response(current_user.id, book_id)
    return jsonify(payload), status


@catalog_content_bp.route('/api/books/custom-books/<book_id>/chapters', methods=['POST'])
@token_required
def append_custom_book_chapters(current_user, book_id):
    payload, status = append_catalog_content_custom_book_chapters_response(
        current_user.id,
        book_id,
        request.get_json(silent=True),
    )
    return jsonify(payload), status


@catalog_content_bp.route('/api/books/<book_id>', methods=['GET'])
def get_book(book_id):
    payload, status = build_book_response(book_id)
    return jsonify(payload), status


@catalog_content_bp.route('/api/books/<book_id>/chapters', methods=['GET'])
def get_book_chapters(book_id):
    payload, status = build_book_chapters_response(book_id)
    return jsonify(payload), status


@catalog_content_bp.route('/api/books/<book_id>/chapters/<chapter_id>', methods=['GET'])
def get_chapter_words(book_id, chapter_id):
    payload, status = build_chapter_words_response(book_id, chapter_id)
    return jsonify(payload), status


@catalog_content_bp.route('/api/books/<book_id>/words', methods=['GET'])
def get_book_words(book_id):
    payload, status = build_book_words_response(
        book_id,
        page=request.args.get('page', 1, type=int),
        per_page=request.args.get('per_page', 100, type=int),
    )
    return jsonify(payload), status


@catalog_content_bp.route('/internal/catalog/custom-books', methods=['POST'])
@token_required
def create_internal_custom_book(current_user):
    payload, status = create_catalog_content_custom_book_response(
        current_user.id,
        request.get_json(silent=True),
    )
    return jsonify(payload), status


@catalog_content_bp.route('/internal/catalog/custom-books', methods=['GET'])
@token_required
def list_internal_custom_books(current_user):
    payload, status = list_catalog_content_custom_books_response(current_user.id)
    return jsonify(payload), status


@catalog_content_bp.route('/internal/catalog/custom-books/<book_id>', methods=['GET'])
@token_required
def get_internal_custom_book(current_user, book_id):
    payload, status = get_catalog_content_custom_book_response(current_user.id, book_id)
    return jsonify(payload), status


@catalog_content_bp.route('/internal/catalog/custom-books/<book_id>/chapters', methods=['POST'])
@token_required
def append_internal_custom_book_chapters(current_user, book_id):
    payload, status = append_catalog_content_custom_book_chapters_response(
        current_user.id,
        book_id,
        request.get_json(silent=True),
    )
    return jsonify(payload), status


@catalog_content_bp.route(f'/api/books/{CONFUSABLE_MATCH_BOOK_ID}/custom-chapters', methods=['POST'])
@token_required
def create_confusable_custom_chapters(current_user):
    payload, status = create_confusable_custom_chapters_response(
        current_user.id,
        (request.get_json(silent=True) or {}).get('groups'),
    )
    return jsonify(payload), status


@catalog_content_bp.route(
    f'/api/books/{CONFUSABLE_MATCH_BOOK_ID}/custom-chapters/<int:chapter_id>',
    methods=['PUT'],
)
@token_required
def update_confusable_custom_chapter(current_user, chapter_id):
    payload, status = update_confusable_custom_chapter_response(
        current_user.id,
        chapter_id,
        (request.get_json(silent=True) or {}).get('words'),
    )
    return jsonify(payload), status
