from __future__ import annotations

from functools import lru_cache


@lru_cache(maxsize=1)
def _load_sync_endpoint_support():
    from services.ai_progress_sync_service import (
        build_smart_stats_response,
        run_local_storage_migration_response,
        sync_quick_memory_response,
        sync_smart_stats_response,
    )

    return (
        build_smart_stats_response,
        run_local_storage_migration_response,
        sync_quick_memory_response,
        sync_smart_stats_response,
    )


@ai_bp.route('/quick-memory/sync', methods=['POST'])
@token_required
def sync_quick_memory(current_user: User):
    _, _, sync_quick_memory_response, _ = _load_sync_endpoint_support()
    payload, status = sync_quick_memory_response(
        current_user.id,
        request.get_json() or {},
    )
    return jsonify(payload), status


@ai_bp.route('/smart-stats', methods=['GET'])
@token_required
def get_smart_stats(current_user: User):
    build_smart_stats_response, _, _, _ = _load_sync_endpoint_support()
    payload, status = build_smart_stats_response(current_user.id)
    return jsonify(payload), status


@ai_bp.route('/smart-stats/sync', methods=['POST'])
@token_required
def sync_smart_stats(current_user: User):
    _, _, _, sync_smart_stats_response = _load_sync_endpoint_support()
    payload, status = sync_smart_stats_response(
        current_user.id,
        request.get_json() or {},
    )
    return jsonify(payload), status


@ai_bp.route('/local-storage-migration', methods=['POST'])
@token_required
def run_local_storage_migration(current_user: User):
    """One-shot migration for legacy browser localStorage learning keys."""
    _, run_local_storage_migration_response, _, _ = _load_sync_endpoint_support()
    payload, status = run_local_storage_migration_response(
        current_user.id,
        request.get_json() or {},
    )
    return jsonify(payload), status
