from services.quick_memory_review_queue_service import (
    build_review_queue_payload,
    parse_review_queue_options,
)
from services.session_logging_service import (
    cancel_empty_session,
    persist_study_session_response,
)


@ai_bp.route('/cancel-session', methods=['POST'])
@token_required
def cancel_session(current_user: User):
    payload, status = cancel_empty_session(
        user_id=current_user.id,
        session_id=(request.get_json() or {}).get('sessionId'),
    )
    return jsonify(payload), status


@ai_bp.route('/log-session', methods=['POST'])
@token_required
def log_session(current_user: User):
    """Persist a study session row or reconcile it with an existing placeholder."""
    payload, status = persist_study_session_response(
        user_id=current_user.id,
        body=request.get_json() or {},
        parse_client_epoch_ms=_parse_client_epoch_ms,
        normalize_chapter_id=_normalize_chapter_id,
        find_pending_session=_find_pending_session,
    )
    return jsonify(payload), status


@ai_bp.route('/quick-memory', methods=['GET'])
@token_required
def get_quick_memory(current_user: User):
    records = load_user_quick_memory_records(current_user.id)
    return jsonify({'records': [record.to_dict() for record in records]}), 200


@ai_bp.route('/quick-memory/review-queue', methods=['GET'])
@token_required
def get_quick_memory_review_queue(current_user: User):
    options = parse_review_queue_options(
        request.args,
        normalize_chapter_id=_normalize_chapter_id,
        now_ms=utc_naive_to_epoch_ms(utc_now_naive()),
    )
    payload = build_review_queue_payload(
        user_id=current_user.id,
        normalize_chapter_id=_normalize_chapter_id,
        load_user_quick_memory_records=load_user_quick_memory_records,
        resolve_quick_memory_vocab_entry=_resolve_quick_memory_vocab_entry,
        get_global_vocab_pool=_get_global_vocab_pool,
        **options,
    )
    return jsonify(payload), 200
