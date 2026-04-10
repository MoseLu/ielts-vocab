from platform_sdk.ai_assistant_application import (
    ask_api_response,
    ask_stream_api_response,
    generate_book_api_response,
    get_custom_book_api_response,
    list_custom_books_api_response,
)


@ai_bp.route('/ask', methods=['POST'])
@token_required
def ask(current_user):
    return ask_api_response(current_user, request.get_json() or {})


@ai_bp.route('/ask/stream', methods=['POST'])
@token_required
def ask_stream(current_user):
    return ask_stream_api_response(current_user, request.get_json() or {})


@ai_bp.route('/generate-book', methods=['POST'])
@token_required
def generate_book(current_user):
    return generate_book_api_response(current_user, request.get_json() or {})


@ai_bp.route('/custom-books', methods=['GET'])
@token_required
def list_custom_books(current_user):
    return list_custom_books_api_response(current_user)


@ai_bp.route('/custom-books/<book_id>', methods=['GET'])
@token_required
def get_custom_book(current_user, book_id: str):
    return get_custom_book_api_response(current_user, book_id)
