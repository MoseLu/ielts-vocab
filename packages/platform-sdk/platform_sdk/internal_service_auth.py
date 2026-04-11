from __future__ import annotations

import os
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta

import jwt


INTERNAL_SERVICE_AUTH_HEADER = 'x-internal-service-auth'
REQUEST_ID_HEADER = 'x-request-id'
TRACE_ID_HEADER = 'x-trace-id'
SERVICE_NAME_HEADER = 'x-service-name'
USER_ID_HEADER = 'x-user-id'
USER_SCOPES_HEADER = 'x-user-scopes'

DEFAULT_SOURCE_SERVICE_NAME = 'gateway-bff'
DEFAULT_INTERNAL_TOKEN_TTL_SECONDS = 60


@dataclass(frozen=True)
class InternalServiceUser:
    id: int
    is_admin: bool = False
    username: str = ''
    email: str = ''
    scopes: tuple[str, ...] = ()
    auth_source: str = 'internal-service'
    tokens_revoked_before: None = None

    def to_dict(self) -> dict[str, object]:
        return {
            'id': self.id,
            'email': self.email,
            'username': self.username,
            'avatar_url': None,
            'is_admin': self.is_admin,
            'created_at': None,
        }


def internal_service_secret(*, env=os.environ) -> str:
    def _text(value) -> str:
        if value is None:
            return ''
        if isinstance(value, str):
            return value.strip()
        return str(value).strip()

    return (
        _text(env.get('INTERNAL_SERVICE_JWT_SECRET_KEY'))
        or _text(env.get('JWT_SECRET_KEY'))
    )


def internal_service_token_ttl_seconds(*, env=os.environ) -> int:
    raw_value = env.get('INTERNAL_SERVICE_TOKEN_TTL_SECONDS')
    if isinstance(raw_value, int):
        return max(10, raw_value)

    raw = (raw_value or '').strip() if isinstance(raw_value, str) else str(raw_value or '').strip()
    if not raw:
        return DEFAULT_INTERNAL_TOKEN_TTL_SECONDS
    try:
        return max(10, int(raw))
    except ValueError:
        return DEFAULT_INTERNAL_TOKEN_TTL_SECONDS


def extract_request_ids(request) -> tuple[str, str]:
    request_id = (
        request.headers.get(REQUEST_ID_HEADER)
        or request.headers.get(REQUEST_ID_HEADER.title())
        or ''
    ).strip()
    trace_id = (
        request.headers.get(TRACE_ID_HEADER)
        or request.headers.get(TRACE_ID_HEADER.title())
        or ''
    ).strip()
    if not request_id:
        request_id = uuid.uuid4().hex
    if not trace_id:
        trace_id = request_id
    return request_id, trace_id


def extract_access_token_from_request(request) -> str | None:
    cookies = getattr(request, 'cookies', None) or {}
    token = cookies.get('access_token')
    if token:
        return token

    auth_header = request.headers.get('authorization') or request.headers.get('Authorization') or ''
    if auth_header.startswith('Bearer '):
        return auth_header[7:] or None
    return None


def decode_external_access_token(token: str, *, secret: str) -> dict | None:
    if not token or not secret:
        return None
    try:
        payload = jwt.decode(token, secret, algorithms=['HS256'])
    except jwt.InvalidTokenError:
        return None
    if payload.get('type') != 'access':
        return None
    return payload


def create_internal_service_token(
    *,
    secret: str,
    source_service_name: str,
    user_id: int,
    is_admin: bool = False,
    username: str = '',
    email: str = '',
    scopes: tuple[str, ...] | list[str] = (),
    request_id: str = '',
    trace_id: str = '',
    ttl_seconds: int = DEFAULT_INTERNAL_TOKEN_TTL_SECONDS,
) -> str:
    now = datetime.utcnow()
    expires_at = now + timedelta(seconds=max(10, ttl_seconds))
    payload = {
        'type': 'internal-access',
        'iss': source_service_name,
        'sub': str(user_id),
        'user_id': user_id,
        'is_admin': bool(is_admin),
        'username': username or '',
        'email': email or '',
        'scopes': list(scopes or ()),
        'request_id': request_id or '',
        'trace_id': trace_id or '',
        'iat': now,
        'exp': expires_at,
    }
    return jwt.encode(payload, secret, algorithm='HS256')


def decode_internal_service_token(token: str, *, secret: str) -> dict:
    return jwt.decode(token, secret, algorithms=['HS256'])


def _normalize_scopes(raw_scopes) -> tuple[str, ...]:
    if isinstance(raw_scopes, str):
        values = [segment.strip() for segment in raw_scopes.split(',')]
    elif isinstance(raw_scopes, (list, tuple, set)):
        values = [str(segment).strip() for segment in raw_scopes]
    else:
        values = []
    return tuple(segment for segment in values if segment)


def try_build_internal_auth_headers(
    request,
    *,
    source_service_name: str = DEFAULT_SOURCE_SERVICE_NAME,
    env=os.environ,
) -> dict[str, str]:
    request_id, trace_id = extract_request_ids(request)
    headers = {
        REQUEST_ID_HEADER: request_id,
        TRACE_ID_HEADER: trace_id,
        SERVICE_NAME_HEADER: source_service_name,
    }

    secret = internal_service_secret(env=env)
    access_token = extract_access_token_from_request(request)
    payload = decode_external_access_token(access_token or '', secret=secret)
    if not payload:
        return headers

    user_id = payload.get('user_id')
    if user_id in (None, ''):
        return headers

    scopes = _normalize_scopes(payload.get('scopes'))
    headers[USER_ID_HEADER] = str(user_id)
    if scopes:
        headers[USER_SCOPES_HEADER] = ','.join(scopes)
    headers[INTERNAL_SERVICE_AUTH_HEADER] = create_internal_service_token(
        secret=secret,
        source_service_name=source_service_name,
        user_id=int(user_id),
        is_admin=bool(payload.get('is_admin')),
        username=str(payload.get('username') or ''),
        email=str(payload.get('email') or ''),
        scopes=scopes,
        request_id=request_id,
        trace_id=trace_id,
        ttl_seconds=internal_service_token_ttl_seconds(env=env),
    )
    return headers


def internal_user_from_payload(payload: dict) -> InternalServiceUser:
    return InternalServiceUser(
        id=int(payload['user_id']),
        is_admin=bool(payload.get('is_admin')),
        username=str(payload.get('username') or ''),
        email=str(payload.get('email') or ''),
        scopes=_normalize_scopes(payload.get('scopes')),
    )
