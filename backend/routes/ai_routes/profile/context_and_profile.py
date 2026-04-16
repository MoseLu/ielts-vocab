from services.ai_route_support_service import SYSTEM_PROMPT, _get_context_data
from platform_sdk.ai_home_todo_application import build_home_todos_response


@ai_bp.route('/context', methods=['GET'])
@token_required
def get_context(current_user: User):
    """Return structured learning summary for AI context."""
    return jsonify(_get_context_data(current_user.id))


@ai_bp.route('/learner-profile', methods=['GET'])
@token_required
def get_learner_profile(current_user: User):
    target_date = request.args.get('date') or None
    view = request.args.get('view') or 'full'
    try:
        profile = build_learner_profile(current_user.id, target_date, view)
    except ValueError:
        return jsonify({'error': 'date must be YYYY-MM-DD'}), 400
    return jsonify(profile)


@ai_bp.route('/home-todos', methods=['GET'])
@token_required
def get_home_todos(current_user: User):
    payload, status = build_home_todos_response(
        current_user.id,
        target_date=request.args.get('date') or None,
    )
    return jsonify(payload), status
