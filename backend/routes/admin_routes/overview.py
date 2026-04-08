from flask import Blueprint, jsonify, request

from routes.middleware import admin_required
from services.admin_overview_service import (
    build_overview_response as _service_build_overview_response,
    build_users_response as _service_build_users_response,
)

admin_bp = Blueprint('admin', __name__)


def init_admin(app_instance):
    pass


# ── Overview stats ─────────────────────────────────────────────────────────────

@admin_bp.route('/overview', methods=['GET'])
@admin_required
def get_overview(current_user):
    """Platform-wide statistics."""
    del current_user
    payload, status = _service_build_overview_response()
    return jsonify(payload), status


# ── Users list ─────────────────────────────────────────────────────────────────

@admin_bp.route('/users', methods=['GET'])
@admin_required
def get_users(current_user):
    """Paginated user list with summary stats.
    Query params: page, per_page, search, sort (username|created_at|study_time|accuracy), order (asc|desc)
    """
    del current_user
    payload, status = _service_build_users_response(
        page=int(request.args.get('page', 1)),
        per_page=min(int(request.args.get('per_page', 20)), 100),
        search=request.args.get('search', '').strip(),
        sort=request.args.get('sort', 'created_at'),
        order=request.args.get('order', 'desc'),
    )
    return jsonify(payload), status


# ── Single user detail ─────────────────────────────────────────────────────────
