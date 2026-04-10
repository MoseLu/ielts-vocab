from platform_sdk.ai_learning_stats_application import (
    build_learning_stats_response,
    start_session_response,
)


@ai_bp.route('/learning-stats', methods=['GET'])
@token_required
def get_learning_stats(current_user: User):
    payload, status = build_learning_stats_response(
        current_user.id,
        days=min(int(request.args.get('days', 30)), 90),
        book_id_filter=request.args.get('book_id') or None,
        mode_filter_raw=request.args.get('mode') or None,
    )
    return jsonify(payload), status


@ai_bp.route('/start-session', methods=['POST'])
@token_required
def start_session(current_user: User):
    """Create or reuse an empty placeholder session and return its id."""
    payload, status = start_session_response(current_user.id, request.get_json() or {})
    return jsonify(payload), status
