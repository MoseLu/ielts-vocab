from services.ai_assistant_ask_service import (
    ask_response as _ask_response,
    ask_stream_response as _ask_stream_response,
)
from services.ai_custom_books_service import (
    GENERATE_BOOK_PROMPT,
    build_incoming_wrong_word_dimension_states as _build_incoming_wrong_word_dimension_states,
    clamp_wrong_word_pass_streak as _clamp_wrong_word_pass_streak,
    generate_book_response as _generate_book_response,
    get_custom_book_response as _get_custom_book_response,
    list_custom_books_response as _list_custom_books_response,
    max_wrong_word_counter as _max_wrong_word_counter,
    merge_wrong_word_dimension_states as _merge_wrong_word_dimension_states,
    normalize_wrong_word_counter as _normalize_wrong_word_counter,
    normalize_wrong_word_iso as _normalize_wrong_word_iso,
    pick_later_wrong_word_iso as _pick_later_wrong_word_iso,
)


@ai_bp.route('/ask', methods=['POST'])
@token_required
def ask(current_user):
    return _ask_response(current_user, request.get_json() or {})


@ai_bp.route('/ask/stream', methods=['POST'])
@token_required
def ask_stream(current_user):
    return _ask_stream_response(current_user, request.get_json() or {})


@ai_bp.route('/generate-book', methods=['POST'])
@token_required
def generate_book(current_user):
    return _generate_book_response(current_user, request.get_json() or {})


@ai_bp.route('/custom-books', methods=['GET'])
@token_required
def list_custom_books(current_user):
    return _list_custom_books_response(current_user)


@ai_bp.route('/custom-books/<book_id>', methods=['GET'])
@token_required
def get_custom_book(current_user, book_id: str):
    return _get_custom_book_response(current_user, book_id)
