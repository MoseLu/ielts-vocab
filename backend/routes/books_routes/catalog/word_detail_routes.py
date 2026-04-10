from flask import jsonify, request

from routes.middleware import token_required
from services.books_confusable_service import resolve_optional_current_user
from services.books_word_detail_service import (
    build_word_details_response as _service_build_word_details_response,
    save_word_detail_note_response as _service_save_word_detail_note_response,
)


@books_bp.route('/word-details', methods=['GET'])
def get_word_details():
    payload, status = _service_build_word_details_response(
        request.args.get('word'),
        resolve_optional_current_user(),
    )
    return jsonify(payload), status


@books_bp.route('/word-details/note', methods=['PUT'])
@token_required
def save_word_detail_note(current_user):
    payload, status = _service_save_word_detail_note_response(
        current_user.id,
        request.get_json() or {},
    )
    return jsonify(payload), status
