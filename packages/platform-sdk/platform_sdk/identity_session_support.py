from __future__ import annotations

import hashlib
import re
import uuid
from datetime import datetime, timedelta

import jwt
from flask import has_request_context, request

from platform_sdk.identity_repository_adapter import auth_repository


_EMAIL_RE = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]{2,}$')
_AVATAR_DATA_URL_RE = re.compile(
    r'^data:image/(?:jpeg|jpg|png|webp|gif);base64,[A-Za-z0-9+/=\s]+$',
    re.IGNORECASE,
)
_AVATAR_HTTP_URL_RE = re.compile(r'^https?://', re.IGNORECASE)


def rate_limit_bucket_key(ip: str, purpose: str, subject: str | None = None) -> str:
    normalized_ip = (ip or '0.0.0.0').strip() or '0.0.0.0'
    if not subject:
        return normalized_ip
    digest = hashlib.sha256(
        f'{purpose}|{normalized_ip}|{subject}'.encode('utf-8')
    ).hexdigest()[:40]
    return f'v2:{digest}'


def check_rate_limit(app, ip: str, purpose: str = 'login', subject: str | None = None) -> tuple[bool, int]:
    return auth_repository.check_rate_limit(
        ip_address=rate_limit_bucket_key(ip, purpose, subject),
        purpose=purpose,
        max_attempts=app.config['LOGIN_MAX_ATTEMPTS'],
        window_minutes=app.config['LOGIN_LOCKOUT_MINUTES'],
    )


def reset_rate_limit(ip: str, purpose: str = 'login', subject: str | None = None):
    auth_repository.reset_rate_limit(
        ip_address=rate_limit_bucket_key(ip, purpose, subject),
        purpose=purpose,
    )


def find_user_by_identifier(identifier: str):
    return auth_repository.find_user_by_identifier(identifier)


def login_rate_limit_subject(identifier: str, user) -> str:
    if user is not None:
        return f'user:{user.id}'
    return f'identifier:{identifier.strip().casefold()}'


def validate_email(email: str) -> bool:
    return bool(_EMAIL_RE.match(email))


def is_mock_email_delivery(app) -> bool:
    return (app.config.get('EMAIL_CODE_DELIVERY_MODE') or 'mock') == 'mock'


def allow_mock_email_delivery(app) -> bool:
    return bool(app.config.get('ALLOW_MOCK_EMAIL_DELIVERY', False) or app.config.get('TESTING', False))


def verification_code_message(app, *, generic: bool) -> str:
    if is_mock_email_delivery(app):
        if not allow_mock_email_delivery(app):
            return '邮箱服务未配置，请稍后再试'
        prefix = '如果该邮箱已注册，验证码已生成' if generic else '验证码已生成'
        return f'{prefix}，开发环境请查看后端日志（有效期10分钟）'
    prefix = '如果该邮箱已注册，验证码已发送' if generic else '验证码已发送'
    return f'{prefix}，请查收邮件（有效期10分钟）'


def validate_avatar_value(avatar_url: str) -> str | None:
    if not avatar_url:
        return None
    if len(avatar_url) > 700_000:
        return '头像图片过大，请选择小于500KB的图片'
    if _AVATAR_HTTP_URL_RE.match(avatar_url):
        return None
    if _AVATAR_DATA_URL_RE.match(avatar_url):
        return None
    return '头像格式不受支持，请上传 JPG、PNG、WEBP 或 GIF 图片'


def request_client_details(flask_request) -> dict[str, str]:
    access_route = [segment for segment in flask_request.access_route if segment]
    client_ip = access_route[0] if access_route else (flask_request.remote_addr or '0.0.0.0')
    return {
        'client_ip': client_ip,
        'remote_addr': flask_request.remote_addr or '0.0.0.0',
        'forwarded_for': flask_request.headers.get('X-Forwarded-For') or '-',
        'origin': flask_request.headers.get('Origin') or '-',
        'referer': flask_request.headers.get('Referer') or '-',
        'user_agent': flask_request.headers.get('User-Agent') or '-',
    }


def log_registration_audit(
    app,
    flask_request,
    *,
    outcome: str,
    reason: str,
    username: str,
    email: str,
    user_id: int | None = None,
):
    details = request_client_details(flask_request)
    app.logger.info(
        'Registration audit | outcome=%s reason=%s user_id=%s username=%s email=%s client_ip=%s remote_addr=%s forwarded_for=%s origin=%s referer=%s user_agent=%s',
        outcome,
        reason,
        user_id if user_id is not None else '-',
        username or '-',
        email or '-',
        details['client_ip'],
        details['remote_addr'],
        details['forwarded_for'],
        details['origin'],
        details['referer'],
        details['user_agent'],
    )


def make_access_token(app, user_id: int) -> tuple[str, str, datetime]:
    jti = str(uuid.uuid4())
    now = datetime.utcnow()
    expires_at = now + timedelta(seconds=app.config['JWT_ACCESS_TOKEN_EXPIRES'])
    user = auth_repository.get_user(user_id)
    scopes = ['admin', 'user'] if user and user.is_admin else ['user']
    token = jwt.encode(
        {
            'user_id': user_id,
            'type': 'access',
            'jti': jti,
            'exp': expires_at,
            'iat': now,
            'username': user.username if user else '',
            'email': (user.email if user and user.email else ''),
            'is_admin': bool(user.is_admin) if user else False,
            'scopes': scopes,
        },
        app.config['JWT_SECRET_KEY'],
        algorithm='HS256',
    )
    return token, jti, expires_at


def make_refresh_token(app, user_id: int) -> tuple[str, str, datetime]:
    jti = str(uuid.uuid4())
    now = datetime.utcnow()
    expires_at = now + timedelta(seconds=app.config['JWT_REFRESH_TOKEN_EXPIRES'])
    token = jwt.encode(
        {'user_id': user_id, 'type': 'refresh', 'jti': jti, 'exp': expires_at, 'iat': now},
        app.config['JWT_SECRET_KEY'],
        algorithm='HS256',
    )
    return token, jti, expires_at


def _should_use_secure_cookies(app) -> bool:
    if not app.config['COOKIE_SECURE']:
        return False
    if not has_request_context():
        return True
    if request.is_secure:
        return True
    forwarded_proto = (request.headers.get('X-Forwarded-Proto') or '').split(',')[0].strip().lower()
    return forwarded_proto == 'https'


def set_auth_cookies(app, response, user_id: int) -> dict:
    access_token, access_jti, access_exp = make_access_token(app, user_id)
    refresh_token, refresh_jti, refresh_exp = make_refresh_token(app, user_id)
    secure_cookie = _should_use_secure_cookies(app)
    response.set_cookie(
        'access_token',
        access_token,
        httponly=True,
        secure=secure_cookie,
        samesite=app.config['COOKIE_SAMESITE'],
        max_age=app.config['JWT_ACCESS_TOKEN_EXPIRES'],
        path='/',
    )
    response.set_cookie(
        'refresh_token',
        refresh_token,
        httponly=True,
        secure=secure_cookie,
        samesite=app.config['COOKIE_SAMESITE'],
        max_age=app.config['JWT_REFRESH_TOKEN_EXPIRES'],
        path='/api/auth/refresh',
    )
    return {
        'access_jti': access_jti,
        'access_exp': access_exp,
        'refresh_jti': refresh_jti,
        'refresh_exp': refresh_exp,
        'access_expires_in': app.config['JWT_ACCESS_TOKEN_EXPIRES'],
    }


def clear_auth_cookies(app, response):
    secure_cookie = _should_use_secure_cookies(app)
    for name, path in [('access_token', '/'), ('refresh_token', '/api/auth/refresh')]:
        response.set_cookie(
            name,
            '',
            httponly=True,
            secure=secure_cookie,
            samesite=app.config['COOKIE_SAMESITE'],
            max_age=0,
            expires=0,
            path=path,
        )


def revoke_token_if_present(app, token: str | None):
    if not token:
        return
    try:
        payload = jwt.decode(token, app.config['JWT_SECRET_KEY'], algorithms=['HS256'])
        jti = payload.get('jti')
        if jti:
            auth_repository.revoke_token(
                jti,
                expires_at=datetime.utcfromtimestamp(payload['exp']),
            )
    except Exception:
        pass
