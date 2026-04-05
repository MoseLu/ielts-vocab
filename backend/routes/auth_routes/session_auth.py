"""
Authentication routes — secure cookie-based JWT.

Access token  : 15 min, HttpOnly cookie `access_token`
Refresh token : 7 days, HttpOnly cookie `refresh_token`  (rotated on each use)
Both tokens carry a `jti` (UUID) that is stored in `revoked_tokens` on logout
or refresh, preventing replay attacks.

Login is rate-limited: 10 failures per IP → 15-min lockout.
"""

import hashlib
import re
import uuid
from datetime import datetime, timedelta

import jwt
from flask import Blueprint, jsonify, make_response, request

# RFC 5322-inspired email pattern — rejects obvious non-emails like "a@b"
_EMAIL_RE = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]{2,}$')
_AVATAR_DATA_URL_RE = re.compile(
    r'^data:image/(?:jpeg|jpg|png|webp|gif);base64,[A-Za-z0-9+/=\s]+$',
    re.IGNORECASE,
)
_AVATAR_HTTP_URL_RE = re.compile(r'^https?://', re.IGNORECASE)

from models import EmailVerificationCode, RateLimitBucket, RevokedToken, User, db
from routes.middleware import token_required

auth_bp = Blueprint('auth', __name__)

# ── App reference (set by init_auth) ─────────────────────────────────────────

_app = None


def init_auth(app_instance):
    global _app
    _app = app_instance


# ── Rate limiter (database-backed, per login subject + IP) ────────────────────
# Uses database instead of in-memory dict to support multi-process deployments.
# For multi-server deployments (multiple app servers), use Redis instead.

def _rate_limit_bucket_key(ip: str, purpose: str, subject: str | None = None) -> str:
    normalized_ip = (ip or '0.0.0.0').strip() or '0.0.0.0'
    if not subject:
        return normalized_ip

    digest = hashlib.sha256(
        f'{purpose}|{normalized_ip}|{subject}'.encode('utf-8')
    ).hexdigest()[:40]
    return f'v2:{digest}'


def _check_rate_limit(ip: str, purpose: str = 'login', subject: str | None = None) -> tuple[bool, int]:
    """
    Returns (allowed, seconds_until_reset).
    Uses database-backed rate limiting to work across gunicorn/uwsgi workers.
    """
    bucket_key = _rate_limit_bucket_key(ip, purpose, subject)
    allowed, wait = RateLimitBucket.check_and_increment(
        ip_address=bucket_key,
        purpose=purpose,
        max_attempts=_app.config['LOGIN_MAX_ATTEMPTS'],
        window_minutes=_app.config['LOGIN_LOCKOUT_MINUTES']
    )
    return allowed, wait


def _reset_rate_limit(ip: str, purpose: str = 'login', subject: str | None = None):
    """Clear rate limit bucket after a successful action."""
    bucket_key = _rate_limit_bucket_key(ip, purpose, subject)
    RateLimitBucket.reset(ip_address=bucket_key, purpose=purpose)


def _find_user_by_identifier(identifier: str):
    if '@' in identifier:
        return User.query.filter_by(email=identifier).first()

    user = User.query.filter_by(username=identifier).first()
    if not user:
        user = User.query.filter_by(email=identifier).first()
    return user


def _login_rate_limit_subject(identifier: str, user: User | None) -> str:
    if user is not None:
        return f'user:{user.id}'
    return f'identifier:{identifier.strip().casefold()}'


def _validate_email(email: str) -> bool:
    """Return True if email passes basic RFC-style format check."""
    return bool(_EMAIL_RE.match(email))


def _is_mock_email_delivery() -> bool:
    return (_app.config.get('EMAIL_CODE_DELIVERY_MODE') or 'mock') == 'mock'


def _verification_code_message(*, generic: bool) -> str:
    if _is_mock_email_delivery():
        prefix = '如果该邮箱已注册，验证码已生成' if generic else '验证码已生成'
        return f'{prefix}，开发环境请查看后端日志（有效期10分钟）'
    prefix = '如果该邮箱已注册，验证码已发送' if generic else '验证码已发送'
    return f'{prefix}，请查收邮件（有效期10分钟）'


def _validate_avatar_value(avatar_url: str) -> str | None:
    if not avatar_url:
        return None
    if len(avatar_url) > 700_000:
        return '头像图片过大，请选择小于500KB的图片'
    if _AVATAR_HTTP_URL_RE.match(avatar_url):
        return None
    if _AVATAR_DATA_URL_RE.match(avatar_url):
        return None
    return '头像格式不受支持，请上传 JPG、PNG、WEBP 或 GIF 图片'


def _request_client_details() -> dict[str, str]:
    access_route = [segment for segment in request.access_route if segment]
    client_ip = access_route[0] if access_route else (request.remote_addr or '0.0.0.0')
    return {
        'client_ip': client_ip,
        'remote_addr': request.remote_addr or '0.0.0.0',
        'forwarded_for': request.headers.get('X-Forwarded-For') or '-',
        'origin': request.headers.get('Origin') or '-',
        'referer': request.headers.get('Referer') or '-',
        'user_agent': request.headers.get('User-Agent') or '-',
    }


def _log_registration_audit(
    *,
    outcome: str,
    reason: str,
    username: str,
    email: str,
    user_id: int | None = None,
):
    details = _request_client_details()
    _app.logger.info(
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


# ── Token helpers ─────────────────────────────────────────────────────────────

def _make_access_token(user_id: int) -> tuple[str, str, datetime]:
    """Return (encoded_jwt, jti, expires_at)."""
    jti = str(uuid.uuid4())
    now = datetime.utcnow()
    exp = now + timedelta(seconds=_app.config['JWT_ACCESS_TOKEN_EXPIRES'])
    token = jwt.encode(
        {'user_id': user_id, 'type': 'access', 'jti': jti, 'exp': exp, 'iat': now},
        _app.config['JWT_SECRET_KEY'],
        algorithm='HS256',
    )
    return token, jti, exp


def _make_refresh_token(user_id: int) -> tuple[str, str, datetime]:
    """Return (encoded_jwt, jti, expires_at)."""
    jti = str(uuid.uuid4())
    now = datetime.utcnow()
    exp = now + timedelta(seconds=_app.config['JWT_REFRESH_TOKEN_EXPIRES'])
    token = jwt.encode(
        {'user_id': user_id, 'type': 'refresh', 'jti': jti, 'exp': exp, 'iat': now},
        _app.config['JWT_SECRET_KEY'],
        algorithm='HS256',
    )
    return token, jti, exp


def _set_auth_cookies(response, user_id: int) -> dict:
    """
    Mint a fresh access+refresh token pair, attach them as HttpOnly cookies,
    and return {'access_jti': ..., 'refresh_jti': ..., 'access_exp': ..., 'refresh_exp': ...}.
    """
    secure = _app.config['COOKIE_SECURE']
    samesite = _app.config['COOKIE_SAMESITE']

    access_token, access_jti, access_exp = _make_access_token(user_id)
    refresh_token, refresh_jti, refresh_exp = _make_refresh_token(user_id)

    response.set_cookie(
        'access_token', access_token,
        httponly=True,
        secure=secure,
        samesite=samesite,
        max_age=_app.config['JWT_ACCESS_TOKEN_EXPIRES'],
        path='/',
    )
    response.set_cookie(
        'refresh_token', refresh_token,
        httponly=True,
        secure=secure,
        samesite=samesite,
        max_age=_app.config['JWT_REFRESH_TOKEN_EXPIRES'],
        path='/api/auth/refresh',   # only sent to the refresh endpoint
    )
    return {
        'access_jti': access_jti, 'access_exp': access_exp,
        'refresh_jti': refresh_jti, 'refresh_exp': refresh_exp,
        'access_expires_in': _app.config['JWT_ACCESS_TOKEN_EXPIRES'],
    }


def _clear_auth_cookies(response):
    """Expire both auth cookies immediately."""
    for name, path in [('access_token', '/'), ('refresh_token', '/api/auth/refresh')]:
        response.set_cookie(
            name, '', httponly=True,
            secure=_app.config['COOKIE_SECURE'],
            samesite=_app.config['COOKIE_SAMESITE'],
            max_age=0, expires=0, path=path,
        )


# ── Routes ────────────────────────────────────────────────────────────────────

@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json() or {}

    email = (data.get('email') or '').strip()
    password = data.get('password', '')
    username = (data.get('username') or '').strip()

    if not username:
        _log_registration_audit(outcome='rejected', reason='missing_username', username=username, email=email)
        return jsonify({'error': '请输入用户名'}), 400
    if len(username) < 3:
        _log_registration_audit(outcome='rejected', reason='short_username', username=username, email=email)
        return jsonify({'error': '用户名至少3个字符'}), 400
    if not password or len(password) < 6:
        _log_registration_audit(outcome='rejected', reason='short_password', username=username, email=email)
        return jsonify({'error': '密码至少6个字符'}), 400
    if User.query.filter_by(username=username).first():
        _log_registration_audit(outcome='rejected', reason='duplicate_username', username=username, email=email)
        return jsonify({'error': '用户名已被使用'}), 400
    if email:
        if not _validate_email(email):
            _log_registration_audit(outcome='rejected', reason='invalid_email', username=username, email=email)
            return jsonify({'error': '邮箱格式不正确'}), 400
        if User.query.filter_by(email=email).first():
            _log_registration_audit(outcome='rejected', reason='duplicate_email', username=username, email=email)
            return jsonify({'error': '该邮箱已被注册'}), 400

    user = User(email=email or None, username=username)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    _log_registration_audit(
        outcome='created',
        reason='ok',
        username=username,
        email=email,
        user_id=user.id,
    )

    resp = make_response(jsonify({'message': '注册成功', 'user': user.to_dict(),
                                   'access_expires_in': _app.config['JWT_ACCESS_TOKEN_EXPIRES']}), 201)
    _set_auth_cookies(resp, user.id)
    return resp


@auth_bp.route('/login', methods=['POST'])
def login():
    ip = request.remote_addr or '0.0.0.0'
    data = request.get_json() or {}
    identifier = (data.get('email') or data.get('username') or '').strip()
    password = data.get('password', '')

    if not identifier or not password:
        return jsonify({'error': '请输入账号和密码'}), 400

    user = _find_user_by_identifier(identifier)
    login_subject = _login_rate_limit_subject(identifier, user)
    allowed, wait = _check_rate_limit(ip, subject=login_subject)
    if not allowed:
        return jsonify({
            'error': f'登录尝试过于频繁，请 {wait} 秒后再试',
            'retry_after': wait,
        }), 429

    if not user or not user.check_password(password):
        return jsonify({'error': '账号或密码错误'}), 401

    _reset_rate_limit(ip, subject=login_subject)

    resp = make_response(jsonify({'message': '登录成功', 'user': user.to_dict(),
                                   'access_expires_in': _app.config['JWT_ACCESS_TOKEN_EXPIRES']}), 200)
    _set_auth_cookies(resp, user.id)
    return resp


@auth_bp.route('/refresh', methods=['POST'])
def refresh():
    """
    Exchange a valid refresh token cookie for a new access+refresh token pair.
    The old refresh token is immediately revoked (rotation).
    """
    refresh_token = request.cookies.get('refresh_token')
    if not refresh_token:
        return jsonify({'error': '请先登录', 'code': 'NO_TOKEN'}), 401

    try:
        payload = jwt.decode(
            refresh_token,
            _app.config['JWT_SECRET_KEY'],
            algorithms=['HS256'],
        )
    except jwt.ExpiredSignatureError:
        return jsonify({'error': '登录已过期，请重新登录', 'code': 'TOKEN_EXPIRED'}), 401
    except jwt.InvalidTokenError:
        return jsonify({'error': '登录凭证无效', 'code': 'INVALID_TOKEN'}), 401

    if payload.get('type') != 'refresh':
        return jsonify({'error': '登录凭证类型错误', 'code': 'WRONG_TOKEN_TYPE'}), 401

    old_jti = payload.get('jti')
    if old_jti and RevokedToken.is_revoked(old_jti):
        # Refresh token replay detected — possible theft.
        # Mass-revoke ALL tokens for this user by setting tokens_revoked_before
        # to right now. Any token with iat < this timestamp will be rejected.
        try:
            victim = User.query.get(payload['user_id'])
            if victim:
                victim.tokens_revoked_before = datetime.utcnow()
                db.session.commit()
        except Exception:
            pass
        return jsonify({'error': '登录凭证已失效，请重新登录', 'code': 'TOKEN_REVOKED'}), 401

    user = User.query.get(payload['user_id'])
    if not user:
        return jsonify({'error': '用户不存在', 'code': 'USER_NOT_FOUND'}), 401

    # Revoke old refresh token immediately (rotation)
    if old_jti:
        old_exp = datetime.utcfromtimestamp(payload['exp'])
        RevokedToken.revoke(old_jti, old_exp)

    resp = make_response(jsonify({'message': 'ok', 'user': user.to_dict(),
                                   'access_expires_in': _app.config['JWT_ACCESS_TOKEN_EXPIRES']}), 200)
    _set_auth_cookies(resp, user.id)
    return resp


@auth_bp.route('/logout', methods=['POST'])
@token_required
def logout(current_user):
    """
    Revoke the current access token (and refresh token if present),
    then clear both cookies.
    """
    # Revoke access token
    access_token = request.cookies.get('access_token') or ''
    if access_token:
        try:
            p = jwt.decode(access_token, _app.config['JWT_SECRET_KEY'], algorithms=['HS256'])
            jti = p.get('jti')
            if jti:
                RevokedToken.revoke(jti, datetime.utcfromtimestamp(p['exp']))
        except Exception:
            pass

    # Revoke refresh token
    refresh_token = request.cookies.get('refresh_token') or ''
    if refresh_token:
        try:
            p = jwt.decode(refresh_token, _app.config['JWT_SECRET_KEY'], algorithms=['HS256'])
            jti = p.get('jti')
            if jti:
                RevokedToken.revoke(jti, datetime.utcfromtimestamp(p['exp']))
        except Exception:
            pass

    # Prune expired revocation records opportunistically
    try:
        RevokedToken.prune_expired()
    except Exception:
        pass

    resp = make_response(jsonify({'message': '已退出登录'}), 200)
    _clear_auth_cookies(resp)
    return resp


@auth_bp.route('/me', methods=['GET'])
@token_required
def get_current_user(current_user):
    # Include remaining token lifetime so the frontend can schedule proactive refresh
    try:
        import jwt as _jwt
        token = request.cookies.get('access_token') or ''
        payload = _jwt.decode(token, _app.config['JWT_SECRET_KEY'], algorithms=['HS256'])
        from datetime import timezone
        expires_in = max(0, int(payload['exp'] - datetime.utcnow().timestamp()))
    except Exception:
        expires_in = _app.config['JWT_ACCESS_TOKEN_EXPIRES']
    return jsonify({'user': current_user.to_dict(), 'access_expires_in': expires_in}), 200


@auth_bp.route('/avatar', methods=['PUT'])
@token_required
def update_avatar(current_user):
    data = request.get_json() or {}
    avatar_url = data.get('avatar_url', '')
    error = _validate_avatar_value(avatar_url)
    if error:
        return jsonify({'error': error}), 400
    current_user.avatar_url = avatar_url
    db.session.commit()
    return jsonify({'message': '头像已更新', 'user': current_user.to_dict()}), 200


# ── Email verification ────────────────────────────────────────────────────────
