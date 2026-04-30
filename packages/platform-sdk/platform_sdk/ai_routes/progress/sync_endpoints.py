from platform_sdk.ai_sync_application import (
    build_smart_stats_api_response,
    run_local_storage_migration_api_response,
    sync_quick_memory_api_response,
    sync_smart_stats_api_response,
)


@ai_bp.route('/quick-memory/sync', methods=['POST'])
@token_required
def sync_quick_memory(current_user: User):
    """Bulk upsert quick-memory records. Accepts {records: [{word, status, firstSeen, lastSeen, knownCount, unknownCount, nextReview}]}."""
    payload, status = sync_quick_memory_api_response(current_user.id, request.get_json() or {})
    return jsonify(payload), status


# ── GET /api/ai/smart-stats ───────────────────────────────────────────────────

@ai_bp.route('/smart-stats', methods=['GET'])
@token_required
def get_smart_stats(current_user: User):
    """Return all smart-mode word stats for the current user."""
    payload, status = build_smart_stats_api_response(current_user.id)
    return jsonify(payload), status


# ── POST /api/ai/smart-stats/sync ─────────────────────────────────────────────

@ai_bp.route('/smart-stats/sync', methods=['POST'])
@token_required
def sync_smart_stats(current_user: User):
    """Bulk upsert smart-mode word stats. Accepts {stats: [{word, listening, meaning, dictation}]}."""
    payload, status = sync_smart_stats_api_response(current_user.id, request.get_json() or {})
    return jsonify(payload), status


@ai_bp.route('/local-storage-migration', methods=['POST'])
@token_required
def run_local_storage_migration(current_user: User):
    """One-shot migration for legacy browser localStorage learning keys."""
    payload, status = run_local_storage_migration_api_response(
        current_user.id,
        request.get_json() or {},
    )
    return jsonify(payload), status
