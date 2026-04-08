from __future__ import annotations

from datetime import datetime

import jwt

from services import auth_repository

AuthError = tuple[dict, int]


def _auth_error(
    *,
    allow_missing: bool,
    error: str,
    code: str,
    status: int = 401,
) -> AuthError | None:
    if allow_missing:
        return None
    return {'error': error, 'code': code}, status


def extract_access_token(request) -> str | None:
    token = request.cookies.get('access_token')
    if token:
        return token

    auth_header = request.headers.get('Authorization', '')
    if auth_header.startswith('Bearer '):
        return auth_header[7:] or None
    return None


def decode_token(app, token: str) -> dict:
    return jwt.decode(
        token,
        app.config['JWT_SECRET_KEY'],
        algorithms=['HS256'],
    )


def resolve_current_user(app, request, *, allow_missing: bool):
    token = extract_access_token(request)
    if not token:
        return None, _auth_error(allow_missing=allow_missing, error='请先登录', code='NO_TOKEN')

    try:
        payload = decode_token(app, token)
    except jwt.ExpiredSignatureError:
        return None, _auth_error(
            allow_missing=allow_missing,
            error='登录已过期，请重新登录',
            code='TOKEN_EXPIRED',
        )
    except jwt.InvalidTokenError:
        return None, _auth_error(
            allow_missing=allow_missing,
            error='登录凭证无效',
            code='INVALID_TOKEN',
        )

    if payload.get('type') != 'access':
        return None, _auth_error(
            allow_missing=allow_missing,
            error='登录凭证类型错误',
            code='WRONG_TOKEN_TYPE',
        )

    jti = payload.get('jti')
    if jti and auth_repository.is_token_revoked(jti):
        return None, _auth_error(
            allow_missing=allow_missing,
            error='登录凭证已失效，请重新登录',
            code='TOKEN_REVOKED',
        )

    user_id = payload.get('user_id')
    current_user = auth_repository.get_user(user_id)
    if current_user is None:
        return None, _auth_error(
            allow_missing=allow_missing,
            error='用户不存在',
            code='USER_NOT_FOUND',
        )

    if current_user.tokens_revoked_before:
        issued_at = payload.get('iat')
        if issued_at and datetime.utcfromtimestamp(issued_at) < current_user.tokens_revoked_before:
            return None, _auth_error(
                allow_missing=allow_missing,
                error='登录凭证已失效，请重新登录',
                code='TOKEN_REVOKED',
            )

    return current_user, None


def resolve_admin_user(app, request) -> tuple[User | None, AuthError | None]:
    current_user, error_response = resolve_current_user(app, request, allow_missing=False)
    if error_response is not None:
        return None, error_response

    if not current_user.is_admin:
        return None, ({'error': '权限不足', 'code': 'FORBIDDEN'}, 403)

    return current_user, None
