from __future__ import annotations

import os
from datetime import datetime

import jwt

from platform_sdk.internal_service_auth import (
    INTERNAL_SERVICE_AUTH_HEADER,
    InternalServiceUser,
    SERVICE_NAME_HEADER,
    decode_internal_service_token,
    internal_user_from_payload,
)
from services import auth_repository

AuthError = tuple[dict, int]
_BROWSER_TOKEN_SERVICES = {'', 'backend-monolith', 'identity-service'}


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


def _resolve_internal_current_user(app, request, *, allow_missing: bool):
    token = request.headers.get(INTERNAL_SERVICE_AUTH_HEADER) or ''
    if not token:
        return None, None

    try:
        payload = decode_internal_service_token(
            token,
            secret=app.config.get('INTERNAL_SERVICE_JWT_SECRET_KEY') or app.config['JWT_SECRET_KEY'],
        )
    except jwt.ExpiredSignatureError:
        return None, _auth_error(
            allow_missing=allow_missing,
            error='内部服务凭证已过期',
            code='INTERNAL_TOKEN_EXPIRED',
        )
    except jwt.InvalidTokenError:
        return None, _auth_error(
            allow_missing=allow_missing,
            error='内部服务凭证无效',
            code='INVALID_INTERNAL_TOKEN',
        )

    if payload.get('type') != 'internal-access':
        return None, _auth_error(
            allow_missing=allow_missing,
            error='内部服务凭证类型错误',
            code='WRONG_INTERNAL_TOKEN_TYPE',
        )

    header_service_name = (request.headers.get(SERVICE_NAME_HEADER) or '').strip()
    payload_service_name = str(payload.get('iss') or '').strip()
    if header_service_name and payload_service_name and header_service_name != payload_service_name:
        return None, _auth_error(
            allow_missing=allow_missing,
            error='内部服务来源不匹配',
            code='INTERNAL_SERVICE_MISMATCH',
        )

    try:
        return internal_user_from_payload(payload), None
    except Exception:
        return None, _auth_error(
            allow_missing=allow_missing,
            error='内部服务用户上下文无效',
            code='INVALID_INTERNAL_USER',
        )


def resolve_current_user(app, request, *, allow_missing: bool):
    token = extract_access_token(request)
    service_name = (os.environ.get('CURRENT_SERVICE_NAME') or '').strip()
    prefer_cookie_user = (
        service_name == 'identity-service'
        and bool(token)
    )
    if not prefer_cookie_user:
        internal_user, internal_error = _resolve_internal_current_user(
            app,
            request,
            allow_missing=allow_missing,
        )
        if internal_error is not None:
            return None, internal_error
        if internal_user is not None:
            return internal_user, None

    if not token:
        return None, _auth_error(allow_missing=allow_missing, error='请先登录', code='NO_TOKEN')
    if service_name not in _BROWSER_TOKEN_SERVICES:
        return None, _auth_error(
            allow_missing=allow_missing,
            error='内部服务必须使用网关注入的内部鉴权上下文',
            code='INTERNAL_AUTH_REQUIRED',
        )

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


def resolve_admin_user(app, request) -> tuple[InternalServiceUser | object | None, AuthError | None]:
    current_user, error_response = resolve_current_user(app, request, allow_missing=False)
    if error_response is not None:
        return None, error_response

    if not current_user.is_admin:
        return None, ({'error': '权限不足', 'code': 'FORBIDDEN'}, 403)

    return current_user, None
