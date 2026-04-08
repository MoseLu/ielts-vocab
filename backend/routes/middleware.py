"""
Shared authentication middleware.

All route blueprints import token_required / admin_required from here so
that cookie-based JWT validation + revocation checks live in one place.
"""

from functools import wraps

from flask import jsonify, request

from services.auth_middleware_service import (
    decode_token as _service_decode_token,
    extract_access_token as _service_extract_access_token,
    resolve_admin_user as _service_resolve_admin_user,
    resolve_current_user as _service_resolve_current_user,
)

# Injected by init_middleware()
_app = None


def init_middleware(app_instance):
    global _app
    _app = app_instance


def _error_response(payload_and_status):
    payload, status = payload_and_status
    return jsonify(payload), status


def _extract_token() -> str | None:
    return _service_extract_access_token(request)


def _decode_token(token: str) -> dict:
    return _service_decode_token(_app, token)


def token_required(f):
    """Decorator: require a valid, non-revoked access token."""
    @wraps(f)
    def decorated(*args, **kwargs):
        current_user, error_response = _service_resolve_current_user(
            _app,
            request,
            allow_missing=False,
        )
        if error_response is not None:
            return _error_response(error_response)
        return f(current_user, *args, **kwargs)

    return decorated


def optional_token_required(f):
    """Decorator: resolve the current user when possible, otherwise pass None."""
    @wraps(f)
    def decorated(*args, **kwargs):
        current_user, _error_response = _service_resolve_current_user(
            _app,
            request,
            allow_missing=True,
        )
        return f(current_user, *args, **kwargs)

    return decorated


def admin_required(f):
    """Decorator: require a valid access token AND is_admin == True."""
    @wraps(f)
    def decorated(*args, **kwargs):
        current_user, error_response = _service_resolve_admin_user(_app, request)
        if error_response is not None:
            return _error_response(error_response)
        return f(current_user, *args, **kwargs)

    return decorated
