"""
Authentication routes — secure cookie-based JWT.

Access token  : 15 min, HttpOnly cookie `access_token`
Refresh token : 7 days, HttpOnly cookie `refresh_token` (rotated on each use)
Both tokens carry a `jti` that is stored in `revoked_tokens` on logout
or refresh, preventing replay attacks.
"""

from flask import Blueprint, jsonify, make_response, request

from routes.middleware import optional_token_required, token_required
from services.auth_session_service import (
    get_current_user_payload as _service_get_current_user_payload,
    clear_auth_cookies as _service_clear_auth_cookies,
    make_mobile_token_payload as _service_make_mobile_token_payload,
    perform_login as _service_perform_login,
    perform_logout as _service_perform_logout,
    perform_refresh as _service_perform_refresh,
    perform_register as _service_perform_register,
    set_auth_cookies as _service_set_auth_cookies,
    update_avatar as _service_update_avatar,
)
from platform_sdk.identity_wechat_application import perform_mobile_wechat_login as _service_perform_mobile_wechat_login

auth_bp = Blueprint('auth', __name__)

_app = None


def init_auth(app_instance):
    global _app
    _app = app_instance


@auth_bp.route('/register', methods=['POST'])
def register():
    payload, status, user_id = _service_perform_register(_app, request, request.get_json() or {})
    response = make_response(jsonify(payload), status)
    if user_id is not None:
        _service_set_auth_cookies(_app, response, user_id)
    return response


@auth_bp.route('/login', methods=['POST'])
def login():
    payload, status, user_id = _service_perform_login(_app, request, request.get_json() or {})
    response = make_response(jsonify(payload), status)
    if user_id is not None:
        _service_set_auth_cookies(_app, response, user_id)
    return response


@auth_bp.route('/mobile/login', methods=['POST'])
def mobile_login():
    payload, status, user_id = _service_perform_login(_app, request, request.get_json() or {})
    if user_id is None:
        return jsonify(payload), status
    token_payload = _service_make_mobile_token_payload(_app, user_id)
    return jsonify({**payload, **token_payload}), status


@auth_bp.route('/mobile/wechat-login', methods=['POST'])
def mobile_wechat_login():
    payload, status, user_id = _service_perform_mobile_wechat_login(_app, request, request.get_json() or {})
    if user_id is None:
        return jsonify(payload), status
    token_payload = _service_make_mobile_token_payload(_app, user_id)
    return jsonify({**payload, **token_payload}), status


@auth_bp.route('/refresh', methods=['POST'])
def refresh():
    payload, status, user_id = _service_perform_refresh(_app, request.cookies.get('refresh_token'))
    response = make_response(jsonify(payload), status)
    if user_id is not None:
        _service_set_auth_cookies(_app, response, user_id)
    return response


@auth_bp.route('/mobile/refresh', methods=['POST'])
def mobile_refresh():
    data = request.get_json() or {}
    refresh_token = (data.get('refresh_token') or '').strip()
    payload, status, user_id = _service_perform_refresh(_app, refresh_token)
    if user_id is None:
        return jsonify(payload), status
    token_payload = _service_make_mobile_token_payload(_app, user_id)
    return jsonify({**payload, **token_payload}), status


@auth_bp.route('/logout', methods=['POST'])
@token_required
def logout(current_user):
    del current_user
    payload, status = _service_perform_logout(
        _app,
        request.cookies.get('access_token') or '',
        request.cookies.get('refresh_token') or '',
    )
    response = make_response(jsonify(payload), status)
    _service_clear_auth_cookies(_app, response)
    return response


@auth_bp.route('/mobile/logout', methods=['POST'])
@token_required
def mobile_logout(current_user):
    del current_user
    data = request.get_json(silent=True) or {}
    auth_header = request.headers.get('Authorization', '')
    access_token = auth_header[7:] if auth_header.startswith('Bearer ') else ''
    refresh_token = (data.get('refresh_token') or '').strip()
    payload, status = _service_perform_logout(_app, access_token, refresh_token)
    return jsonify(payload), status


@auth_bp.route('/me', methods=['GET'])
@optional_token_required
def get_current_user(current_user):
    if current_user is None:
        return jsonify({'user': None, 'authenticated': False}), 200
    payload, status = _service_get_current_user_payload(_app, request, current_user)
    return jsonify(payload), status


@auth_bp.route('/avatar', methods=['PUT'])
@token_required
def update_avatar(current_user):
    payload, status = _service_update_avatar(current_user, request.get_json() or {})
    return jsonify(payload), status


# ── Email verification ────────────────────────────────────────────────────────
