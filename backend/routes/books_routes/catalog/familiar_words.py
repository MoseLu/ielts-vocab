from flask import jsonify, request

from routes.middleware import token_required
from services.books_familiar_service import (
    add_familiar_word as _add_familiar_word,
    get_familiar_status_words,
    remove_familiar_word as _remove_familiar_word,
)


@books_bp.route('/familiar/status', methods=['POST'])
@token_required
def get_familiar_status(current_user):
    data = request.get_json(silent=True) or {}
    return jsonify({
        'words': get_familiar_status_words(current_user.id, data.get('words')),
    }), 200


@books_bp.route('/familiar', methods=['POST'])
@token_required
def add_familiar_word(current_user):
    data = request.get_json(silent=True) or {}
    try:
        result = _add_familiar_word(current_user.id, data)
    except ValueError as error:
        return jsonify({'error': str(error)}), 400

    return jsonify(result), 200


@books_bp.route('/familiar', methods=['DELETE'])
@token_required
def remove_familiar_word(current_user):
    data = request.get_json(silent=True) or {}
    try:
        result = _remove_familiar_word(current_user.id, data.get('word'))
    except ValueError as error:
        return jsonify({'error': str(error)}), 400
    return jsonify(result), 200
