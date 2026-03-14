from flask import Blueprint, request, jsonify
from models import db, UserProgress
from routes.auth import token_required

progress_bp = Blueprint('progress', __name__)


@progress_bp.route('', methods=['GET'])
@token_required
def get_all_progress(current_user):
    """Get all progress for current user"""
    progress = UserProgress.query.filter_by(user_id=current_user.id).all()
    return jsonify({
        'progress': [p.to_dict() for p in progress]
    }), 200


@progress_bp.route('', methods=['POST'])
@token_required
def save_progress(current_user):
    """Save or update progress for a specific day"""
    data = request.get_json()

    day = data.get('day')
    current_index = data.get('current_index', 0)
    correct_count = data.get('correct_count', 0)
    wrong_count = data.get('wrong_count', 0)

    if not day:
        return jsonify({'error': 'Day is required'}), 400

    # Check if progress exists
    progress = UserProgress.query.filter_by(
        user_id=current_user.id,
        day=day
    ).first()

    if progress:
        # Update existing progress
        progress.current_index = current_index
        progress.correct_count = correct_count
        progress.wrong_count = wrong_count
    else:
        # Create new progress
        progress = UserProgress(
            user_id=current_user.id,
            day=day,
            current_index=current_index,
            correct_count=correct_count,
            wrong_count=wrong_count
        )
        db.session.add(progress)

    db.session.commit()

    return jsonify({
        'message': 'Progress saved',
        'progress': progress.to_dict()
    }), 200


@progress_bp.route('/<int:day>', methods=['GET'])
@token_required
def get_day_progress(current_user, day):
    """Get progress for a specific day"""
    progress = UserProgress.query.filter_by(
        user_id=current_user.id,
        day=day
    ).first()

    if not progress:
        return jsonify({'error': 'No progress found for this day'}), 404

    return jsonify({
        'progress': progress.to_dict()
    }), 200
