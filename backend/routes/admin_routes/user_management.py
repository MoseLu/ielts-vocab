from flask import jsonify, request

from routes.middleware import admin_required
from services.admin_user_management_service import (
    build_user_detail_response as _service_build_user_detail_response,
    set_admin_response as _service_set_admin_response,
)


@admin_bp.route('/users/<int:user_id>', methods=['GET'])
@admin_required
def get_user_detail(current_user, user_id):
    """Detailed stats for a specific user.
    Query params (all optional):
      date_from  YYYY-MM-DD  filter sessions/daily from this date (inclusive)
      date_to    YYYY-MM-DD  filter sessions/daily to this date (inclusive)
      mode       practice mode filter (smart|listening|meaning|dictation|quickmemory|radio)
      book_id    book filter
      wrong_words_sort  wrong word sort (last_error|wrong_count), defaults to last_error
    """
    del current_user
    payload, status = _service_build_user_detail_response(
        user_id,
        date_from=request.args.get('date_from'),
        date_to=request.args.get('date_to'),
        mode=request.args.get('mode'),
        book_id=request.args.get('book_id'),
        wrong_words_sort=request.args.get('wrong_words_sort', 'last_error'),
    )
    return jsonify(payload), status


# ── Manage admin status ────────────────────────────────────────────────────────

@admin_bp.route('/users/<int:user_id>/set-admin', methods=['POST'])
@admin_required
def set_admin(current_user, user_id):
    """Grant or revoke admin privileges."""
    payload, status = _service_set_admin_response(
        current_user.id,
        user_id,
        request.get_json() or {},
    )
    return jsonify(payload), status
