"""
Shared authentication middleware.

All route blueprints import token_required / admin_required from here so
that cookie-based JWT validation + revocation checks live in one place.

Token lookup order:
  1. HttpOnly cookie  `access_token`
  2. Authorization header  `Bearer <token>`   (kept for backward compat / tooling)
"""

from functools import wraps
from flask import request, jsonify
from models import User, RevokedToken
import jwt

# Injected by init_middleware()
_app = None


def init_middleware(app_instance):
    global _app
    _app = app_instance


def _extract_token() -> str | None:
    """Return raw JWT string from cookie or Authorization header."""
    token = request.cookies.get('access_token')
    if not token:
        auth_header = request.headers.get('Authorization', '')
        if auth_header.startswith('Bearer '):
            token = auth_header[7:]
    return token or None


def _decode_token(token: str) -> dict:
    """Decode and verify a JWT, raising on any failure."""
    return jwt.decode(
        token,
        _app.config['JWT_SECRET_KEY'],
        algorithms=['HS256'],
    )


def token_required(f):
    """Decorator: require a valid, non-revoked access token."""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = _extract_token()
        if not token:
            return jsonify({'error': '请先登录', 'code': 'NO_TOKEN'}), 401

        try:
            payload = _decode_token(token)
        except jwt.ExpiredSignatureError:
            return jsonify({'error': '登录已过期，请重新登录', 'code': 'TOKEN_EXPIRED'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': '登录凭证无效', 'code': 'INVALID_TOKEN'}), 401

        # Token type guard — must be an access token
        if payload.get('type') != 'access':
            return jsonify({'error': '登录凭证类型错误', 'code': 'WRONG_TOKEN_TYPE'}), 401

        # Revocation check
        jti = payload.get('jti')
        if jti and RevokedToken.is_revoked(jti):
            return jsonify({'error': '登录凭证已失效，请重新登录', 'code': 'TOKEN_REVOKED'}), 401

        current_user = User.query.get(payload['user_id'])
        if not current_user:
            return jsonify({'error': '用户不存在', 'code': 'USER_NOT_FOUND'}), 401

        return f(current_user, *args, **kwargs)

    return decorated


def admin_required(f):
    """Decorator: require a valid access token AND is_admin == True."""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = _extract_token()
        if not token:
            return jsonify({'error': '请先登录', 'code': 'NO_TOKEN'}), 401

        try:
            payload = _decode_token(token)
        except jwt.ExpiredSignatureError:
            return jsonify({'error': '登录已过期，请重新登录', 'code': 'TOKEN_EXPIRED'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': '登录凭证无效', 'code': 'INVALID_TOKEN'}), 401

        if payload.get('type') != 'access':
            return jsonify({'error': '登录凭证类型错误', 'code': 'WRONG_TOKEN_TYPE'}), 401

        jti = payload.get('jti')
        if jti and RevokedToken.is_revoked(jti):
            return jsonify({'error': '登录凭证已失效，请重新登录', 'code': 'TOKEN_REVOKED'}), 401

        current_user = User.query.get(payload['user_id'])
        if not current_user:
            return jsonify({'error': '用户不存在', 'code': 'USER_NOT_FOUND'}), 401

        if not current_user.is_admin:
            return jsonify({'error': '权限不足', 'code': 'FORBIDDEN'}), 403

        return f(current_user, *args, **kwargs)

    return decorated
