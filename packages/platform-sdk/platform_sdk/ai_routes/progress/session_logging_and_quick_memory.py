from platform_sdk.ai_session_application import (
    build_quick_memory_response,
    build_quick_memory_review_queue_response,
    cancel_session_response,
    log_session_response,
)


@ai_bp.route('/cancel-session', methods=['POST'])
@token_required
def cancel_session(current_user: User):
    payload, status = cancel_session_response(
        current_user.id,
        (request.get_json() or {}).get('sessionId'),
    )
    return jsonify(payload), status


@ai_bp.route('/log-session', methods=['POST'])
@token_required
def log_session(current_user: User):
    """Persist a study session row or reconcile it with an existing placeholder."""
    payload, status = log_session_response(current_user.id, request.get_json() or {})
    return jsonify(payload), status


@ai_bp.route('/quick-memory', methods=['GET'])
@token_required
def get_quick_memory(current_user: User):
    payload, status = build_quick_memory_response(current_user.id)
    return jsonify(payload), status


@ai_bp.route('/quick-memory/review-queue', methods=['GET'])
@token_required
def get_quick_memory_review_queue(current_user: User):
    payload, status = build_quick_memory_review_queue_response(current_user.id, request.args)
    return jsonify(payload), status
