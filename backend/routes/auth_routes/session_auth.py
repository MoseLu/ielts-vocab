"""
Authentication routes — secure cookie-based JWT.

Access token  : 15 min, HttpOnly cookie `access_token`
Refresh token : 7 days, HttpOnly cookie `refresh_token` (rotated on each use)
Both tokens carry a `jti` that is stored in `revoked_tokens` on logout
or refresh, preventing replay attacks.
"""

from flask import Blueprint, jsonify, make_response, request

from models import EmailVerificationCode, User, db
from routes.middleware import optional_token_required, token_required
from services.auth_session_service import (
    check_rate_limit as _service_check_rate_limit,
    clear_auth_cookies as _service_clear_auth_cookies,
    find_user_by_identifier as _service_find_user_by_identifier,
    get_current_user_payload as _service_get_current_user_payload,
    is_mock_email_delivery as _service_is_mock_email_delivery,
    login_rate_limit_subject as _service_login_rate_limit_subject,
    log_registration_audit as _service_log_registration_audit,
    make_access_token as _service_make_access_token,
    make_refresh_token as _service_make_refresh_token,
    perform_login as _service_perform_login,
    perform_logout as _service_perform_logout,
    perform_refresh as _service_perform_refresh,
    perform_register as _service_perform_register,
    rate_limit_bucket_key as _service_rate_limit_bucket_key,
    request_client_details as _service_request_client_details,
    reset_rate_limit as _service_reset_rate_limit,
    set_auth_cookies as _service_set_auth_cookies,
    update_avatar as _service_update_avatar,
    validate_avatar_value as _service_validate_avatar_value,
    validate_email as _service_validate_email,
    verification_code_message as _service_verification_code_message,
)

auth_bp = Blueprint('auth', __name__)

_app = None


def init_auth(app_instance):
    global _app
    _app = app_instance


def _rate_limit_bucket_key(ip: str, purpose: str, subject: str | None = None) -> str:
    return _service_rate_limit_bucket_key(ip, purpose, subject)


def _check_rate_limit(ip: str, purpose: str = 'login', subject: str | None = None) -> tuple[bool, int]:
    return _service_check_rate_limit(_app, ip, purpose, subject)


def _reset_rate_limit(ip: str, purpose: str = 'login', subject: str | None = None):
    return _service_reset_rate_limit(ip, purpose, subject)


def _find_user_by_identifier(identifier: str):
    return _service_find_user_by_identifier(identifier)


def _login_rate_limit_subject(identifier: str, user) -> str:
    return _service_login_rate_limit_subject(identifier, user)


def _validate_email(email: str) -> bool:
    return _service_validate_email(email)


def _is_mock_email_delivery() -> bool:
    return _service_is_mock_email_delivery(_app)


def _verification_code_message(*, generic: bool) -> str:
    return _service_verification_code_message(_app, generic=generic)


def _validate_avatar_value(avatar_url: str) -> str | None:
    return _service_validate_avatar_value(avatar_url)


def _request_client_details() -> dict[str, str]:
    return _service_request_client_details(request)


def _log_registration_audit(
    *,
    outcome: str,
    reason: str,
    username: str,
    email: str,
    user_id: int | None = None,
):
    return _service_log_registration_audit(
        _app,
        request,
        outcome=outcome,
        reason=reason,
        username=username,
        email=email,
        user_id=user_id,
    )


def _make_access_token(user_id: int):
    return _service_make_access_token(_app, user_id)


def _make_refresh_token(user_id: int):
    return _service_make_refresh_token(_app, user_id)


def _set_auth_cookies(response, user_id: int) -> dict:
    return _service_set_auth_cookies(_app, response, user_id)


def _clear_auth_cookies(response):
    return _service_clear_auth_cookies(_app, response)


@auth_bp.route('/register', methods=['POST'])
def register():
    payload, status, user_id = _service_perform_register(_app, request, request.get_json() or {})
    response = make_response(jsonify(payload), status)
    if user_id is not None:
        _set_auth_cookies(response, user_id)
    return response


@auth_bp.route('/login', methods=['POST'])
def login():
    payload, status, user_id = _service_perform_login(_app, request, request.get_json() or {})
    response = make_response(jsonify(payload), status)
    if user_id is not None:
        _set_auth_cookies(response, user_id)
    return response


@auth_bp.route('/refresh', methods=['POST'])
def refresh():
    payload, status, user_id = _service_perform_refresh(_app, request.cookies.get('refresh_token'))
    response = make_response(jsonify(payload), status)
    if user_id is not None:
        _set_auth_cookies(response, user_id)
    return response


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
    _clear_auth_cookies(response)
    return response


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
