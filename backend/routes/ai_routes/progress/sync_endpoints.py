from services.ai_progress_sync_service import (
    build_smart_stats_response as _service_build_smart_stats_response,
    sync_quick_memory_response as _service_sync_quick_memory_response,
    sync_smart_stats_response as _service_sync_smart_stats_response,
)


@ai_bp.route('/quick-memory/sync', methods=['POST'])
@token_required
def sync_quick_memory(current_user: User):
    """Bulk upsert quick-memory records. Accepts {records: [{word, status, firstSeen, lastSeen, knownCount, unknownCount, nextReview}]}."""
    payload, status = _service_sync_quick_memory_response(
        current_user.id,
        request.get_json() or {},
    )
    return jsonify(payload), status


# ── GET /api/ai/smart-stats ───────────────────────────────────────────────────

@ai_bp.route('/smart-stats', methods=['GET'])
@token_required
def get_smart_stats(current_user: User):
    """Return all smart-mode word stats for the current user."""
    payload, status = _service_build_smart_stats_response(current_user.id)
    return jsonify(payload), status


# ── POST /api/ai/smart-stats/sync ─────────────────────────────────────────────

@ai_bp.route('/smart-stats/sync', methods=['POST'])
@token_required
def sync_smart_stats(current_user: User):
    """Bulk upsert smart-mode word stats. Accepts {stats: [{word, listening, meaning, dictation}]}."""
    payload, status = _service_sync_smart_stats_response(
        current_user.id,
        request.get_json() or {},
    )
    return jsonify(payload), status
