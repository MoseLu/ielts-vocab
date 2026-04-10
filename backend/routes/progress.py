from flask import Blueprint, jsonify, request
from routes.middleware import token_required
from services.legacy_progress_service import (
    get_legacy_progress_for_day,
    list_legacy_progress,
    save_legacy_progress,
)

progress_bp = Blueprint('progress', __name__)


@progress_bp.route('', methods=['GET'])
@token_required
def get_all_progress(current_user):
    """Get all progress for current user"""
    return jsonify({
        'progress': list_legacy_progress(current_user.id)
    }), 200


@progress_bp.route('', methods=['POST'])
@token_required
def save_progress(current_user):
    """Save or update progress for a specific day"""
    data = request.get_json(silent=True) or {}
    try:
        progress = save_legacy_progress(current_user.id, data)
    except ValueError as error:
        return jsonify({'error': str(error)}), 400

    return jsonify({
        'message': 'Progress saved',
        'progress': progress
    }), 200


@progress_bp.route('/<int:day>', methods=['GET'])
@token_required
def get_day_progress(current_user, day):
    """Get progress for a specific day"""
    progress = get_legacy_progress_for_day(current_user.id, day)
    if not progress:
        return jsonify({'error': 'No progress found for this day'}), 404

    return jsonify({
        'progress': progress
    }), 200
