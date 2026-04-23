from __future__ import annotations

from functools import lru_cache


@lru_cache(maxsize=1)
def _load_ask_route_support():
    from services.ai_assistant_ask_service import ask_response, ask_stream_response

    return ask_response, ask_stream_response


@lru_cache(maxsize=1)
def _load_custom_book_route_support():
    from services.ai_custom_books_service import (
        generate_book_response,
        get_custom_book_response,
        list_custom_books_response,
    )

    return generate_book_response, get_custom_book_response, list_custom_books_response


@ai_bp.route('/ask', methods=['POST'])
@token_required
def ask(current_user):
    ask_response, _ = _load_ask_route_support()
    return ask_response(current_user, request.get_json() or {})


@ai_bp.route('/ask/stream', methods=['POST'])
@token_required
def ask_stream(current_user):
    _, ask_stream_response = _load_ask_route_support()
    return ask_stream_response(current_user, request.get_json() or {})


@ai_bp.route('/generate-book', methods=['POST'])
@token_required
def generate_book(current_user):
    generate_book_response, _, _ = _load_custom_book_route_support()
    return generate_book_response(current_user, request.get_json() or {})


@ai_bp.route('/custom-books', methods=['GET'])
@token_required
def list_custom_books(current_user):
    _, _, list_custom_books_response = _load_custom_book_route_support()
    return list_custom_books_response(current_user)


@ai_bp.route('/custom-books/<book_id>', methods=['GET'])
@token_required
def get_custom_book(current_user, book_id: str):
    _, get_custom_book_response, _ = _load_custom_book_route_support()
    return get_custom_book_response(current_user, book_id)
