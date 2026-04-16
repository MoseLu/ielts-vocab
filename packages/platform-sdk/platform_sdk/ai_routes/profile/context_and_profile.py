from platform_sdk.ai_context_application import (
    build_context_payload,
    build_learner_profile_response,
)
from platform_sdk.ai_home_todo_application import build_home_todos_response


@ai_bp.route('/context', methods=['GET'])
@token_required
def get_context(current_user: User):
    """Return structured learning summary for AI context."""
    return jsonify(build_context_payload(current_user.id))


@ai_bp.route('/learner-profile', methods=['GET'])
@token_required
def get_learner_profile(current_user: User):
    target_date = request.args.get('date') or None
    view = request.args.get('view') or 'full'
    payload, status = build_learner_profile_response(
        current_user.id,
        target_date=target_date,
        view=view,
    )
    return jsonify(payload), status


@ai_bp.route('/home-todos', methods=['GET'])
@token_required
def get_home_todos(current_user: User):
    payload, status = build_home_todos_response(
        current_user.id,
        target_date=request.args.get('date') or None,
    )
    return jsonify(payload), status
