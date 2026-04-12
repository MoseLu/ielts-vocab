from __future__ import annotations

from flask import Blueprint, current_app, jsonify, make_response, request

from platform_sdk.identity_email_application import (
    bind_email_response,
    forgot_password_response,
    reset_password_response,
    send_bind_email_code_response,
)
from platform_sdk.identity_admin_application import set_internal_identity_admin_response
from platform_sdk.identity_session_application import (
    get_current_user_payload,
    perform_login,
    perform_logout,
    perform_refresh,
    perform_register,
    update_avatar,
)
from platform_sdk.identity_session_support import clear_auth_cookies, set_auth_cookies
from routes.middleware import admin_required, optional_token_required, token_required


identity_auth_bp = Blueprint('identity_auth', __name__)
identity_internal_bp = Blueprint('identity_internal', __name__)


def _app():
    return current_app._get_current_object()


@identity_auth_bp.route('/register', methods=['POST'])
def register():
    payload, status, user_id = perform_register(_app(), request, request.get_json() or {})
    response = make_response(jsonify(payload), status)
    if user_id is not None:
        set_auth_cookies(_app(), response, user_id)
    return response


@identity_auth_bp.route('/login', methods=['POST'])
def login():
    payload, status, user_id = perform_login(_app(), request, request.get_json() or {})
    response = make_response(jsonify(payload), status)
    if user_id is not None:
        set_auth_cookies(_app(), response, user_id)
    return response


@identity_auth_bp.route('/refresh', methods=['POST'])
def refresh():
    payload, status, user_id = perform_refresh(_app(), request.cookies.get('refresh_token'))
    response = make_response(jsonify(payload), status)
    if user_id is not None:
        set_auth_cookies(_app(), response, user_id)
    return response


@identity_auth_bp.route('/logout', methods=['POST'])
@token_required
def logout(current_user):
    del current_user
    payload, status = perform_logout(
        _app(),
        request.cookies.get('access_token') or '',
        request.cookies.get('refresh_token') or '',
    )
    response = make_response(jsonify(payload), status)
    clear_auth_cookies(_app(), response)
    return response


@identity_auth_bp.route('/me', methods=['GET'])
@optional_token_required
def get_current_user(current_user):
    if current_user is None:
        return jsonify({'user': None, 'authenticated': False}), 200
    payload, status = get_current_user_payload(_app(), request, current_user)
    return jsonify(payload), status


@identity_auth_bp.route('/avatar', methods=['PUT'])
@token_required
def put_avatar(current_user):
    payload, status = update_avatar(current_user, request.get_json() or {})
    return jsonify(payload), status


@identity_auth_bp.route('/send-code', methods=['POST'])
@token_required
def send_bind_email_code(current_user):
    payload, status = send_bind_email_code_response(
        _app(),
        current_user,
        request.remote_addr or '0.0.0.0',
        request.get_json() or {},
    )
    return jsonify(payload), status


@identity_auth_bp.route('/bind-email', methods=['POST'])
@token_required
def bind_email(current_user):
    payload, status = bind_email_response(current_user, request.get_json() or {})
    return jsonify(payload), status


@identity_auth_bp.route('/forgot-password', methods=['POST'])
def forgot_password():
    payload, status = forgot_password_response(
        _app(),
        request.remote_addr or '0.0.0.0',
        request.get_json() or {},
    )
    return jsonify(payload), status


@identity_auth_bp.route('/reset-password', methods=['POST'])
def reset_password():
    payload, status = reset_password_response(request.get_json() or {})
    return jsonify(payload), status


@identity_internal_bp.route('/internal/identity/admin/users/<int:user_id>/set-admin', methods=['POST'])
@admin_required
def set_internal_admin_user(current_user, user_id):
    payload, status = set_internal_identity_admin_response(
        current_user.id,
        user_id,
        request.get_json() or {},
    )
    return jsonify(payload), status
