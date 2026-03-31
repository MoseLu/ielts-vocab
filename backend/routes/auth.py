"""
Authentication routes — secure cookie-based JWT.

Access token  : 15 min, HttpOnly cookie `access_token`
Refresh token : 7 days, HttpOnly cookie `refresh_token`  (rotated on each use)
Both tokens carry a `jti` (UUID) that is stored in `revoked_tokens` on logout
or refresh, preventing replay attacks.

Login is rate-limited: 10 failures per IP → 15-min lockout.
"""

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


# ── Rate limiter (database-backed, per IP) ─────────────────────────────────────
# Uses database instead of in-memory dict to support multi-process deployments.
# For multi-server deployments (multiple app servers), use Redis instead.

def _check_rate_limit(ip: str, purpose: str = 'login') -> tuple[bool, int]:
    """
    Returns (allowed, seconds_until_reset).
    Uses database-backed rate limiting to work across gunicorn/uwsgi workers.
    """
    allowed, wait = RateLimitBucket.check_and_increment(
        ip_address=ip,
        purpose=purpose,
        max_attempts=_app.config['LOGIN_MAX_ATTEMPTS'],
        window_minutes=_app.config['LOGIN_LOCKOUT_MINUTES']
    )
    return allowed, wait


def _reset_rate_limit(ip: str, purpose: str = 'login'):
    """Clear rate limit bucket after a successful action."""
    RateLimitBucket.reset(ip_address=ip, purpose=purpose)


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
        return jsonify({'error': '请输入用户名'}), 400
    if len(username) < 3:
        return jsonify({'error': '用户名至少3个字符'}), 400
    if not password or len(password) < 6:
        return jsonify({'error': '密码至少6个字符'}), 400
    if User.query.filter_by(username=username).first():
        return jsonify({'error': '用户名已被使用'}), 400
    if email:
        if not _validate_email(email):
            return jsonify({'error': '邮箱格式不正确'}), 400
        if User.query.filter_by(email=email).first():
            return jsonify({'error': '该邮箱已被注册'}), 400

    user = User(email=email or None, username=username)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()

    resp = make_response(jsonify({'message': '注册成功', 'user': user.to_dict(),
                                   'access_expires_in': _app.config['JWT_ACCESS_TOKEN_EXPIRES']}), 201)
    _set_auth_cookies(resp, user.id)
    return resp


@auth_bp.route('/login', methods=['POST'])
def login():
    ip = request.remote_addr or '0.0.0.0'
    allowed, wait = _check_rate_limit(ip)
    if not allowed:
        return jsonify({
            'error': f'登录尝试过于频繁，请 {wait} 秒后再试',
            'retry_after': wait,
        }), 429

    data = request.get_json() or {}
    identifier = (data.get('email') or data.get('username') or '').strip()
    password = data.get('password', '')

    if not identifier or not password:
        return jsonify({'error': '请输入账号和密码'}), 400

    if '@' in identifier:
        user = User.query.filter_by(email=identifier).first()
    else:
        user = User.query.filter_by(username=identifier).first()
        if not user:
            user = User.query.filter_by(email=identifier).first()

    if not user or not user.check_password(password):
        return jsonify({'error': '账号或密码错误'}), 401

    _reset_rate_limit(ip)

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

def _send_code_mock(email, code, purpose):
    print(f"\n{'='*50}")
    print(f"[Email Code] To: {email} | Purpose: {purpose} | Code: {code}")
    print(f"{'='*50}\n")


@auth_bp.route('/send-code', methods=['POST'])
@token_required
def send_bind_email_code(current_user):
    ip = request.remote_addr or '0.0.0.0'
    allowed, wait = _check_rate_limit(ip, purpose='send_code')
    if not allowed:
        return jsonify({'error': f'操作过于频繁，请 {wait} 秒后再试'}), 429

    data = request.get_json() or {}
    email = (data.get('email') or '').strip().lower()
    if not email or not _validate_email(email):
        return jsonify({'error': '请输入有效的邮箱地址'}), 400
    existing = User.query.filter_by(email=email).first()
    if existing and existing.id != current_user.id:
        return jsonify({'error': '该邮箱已被其他账号绑定'}), 400
    EmailVerificationCode.query.filter_by(
        user_id=current_user.id, purpose='bind_email', used=False
    ).update({'used': True})
    db.session.commit()
    record = EmailVerificationCode.create_for(email, 'bind_email', user_id=current_user.id)
    _send_code_mock(email, record.code, 'bind_email')
    return jsonify({
        'message': _verification_code_message(generic=False),
        'delivery_mode': _app.config.get('EMAIL_CODE_DELIVERY_MODE', 'mock'),
    }), 200


@auth_bp.route('/bind-email', methods=['POST'])
@token_required
def bind_email(current_user):
    data = request.get_json() or {}
    email = (data.get('email') or '').strip().lower()
    code = (data.get('code') or '').strip()
    if not email or not code:
        return jsonify({'error': '请输入邮箱和验证码'}), 400
    record = EmailVerificationCode.query.filter_by(
        email=email, purpose='bind_email', user_id=current_user.id, used=False
    ).order_by(EmailVerificationCode.created_at.desc()).first()
    if not record or not record.is_valid():
        return jsonify({'error': '验证码无效或已过期'}), 400
    if record.code != code:
        return jsonify({'error': '验证码错误'}), 400
    existing = User.query.filter_by(email=email).first()
    if existing and existing.id != current_user.id:
        return jsonify({'error': '该邮箱已被其他账号绑定'}), 400
    record.used = True
    current_user.email = email
    db.session.commit()
    return jsonify({'message': '邮箱绑定成功', 'user': current_user.to_dict()}), 200


@auth_bp.route('/forgot-password', methods=['POST'])
def forgot_password():
    ip = request.remote_addr or '0.0.0.0'
    allowed, wait = _check_rate_limit(ip, purpose='forgot_password')
    if not allowed:
        return jsonify({'error': f'操作过于频繁，请 {wait} 秒后再试'}), 429

    data = request.get_json() or {}
    email = (data.get('email') or '').strip().lower()
    if not email or not _validate_email(email):
        return jsonify({'error': '请输入有效的邮箱地址'}), 400
    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({
            'message': _verification_code_message(generic=True),
            'delivery_mode': _app.config.get('EMAIL_CODE_DELIVERY_MODE', 'mock'),
        }), 200
    EmailVerificationCode.query.filter_by(
        email=email, purpose='reset_password', used=False
    ).update({'used': True})
    db.session.commit()
    record = EmailVerificationCode.create_for(email, 'reset_password', user_id=user.id)
    _send_code_mock(email, record.code, 'reset_password')
    return jsonify({
        'message': _verification_code_message(generic=True),
        'delivery_mode': _app.config.get('EMAIL_CODE_DELIVERY_MODE', 'mock'),
    }), 200


@auth_bp.route('/reset-password', methods=['POST'])
def reset_password():
    data = request.get_json() or {}
    email = (data.get('email') or '').strip().lower()
    code = (data.get('code') or '').strip()
    new_password = data.get('password', '')
    if not email or not code or not new_password:
        return jsonify({'error': '请填写所有字段'}), 400
    if len(new_password) < 6:
        return jsonify({'error': '密码至少6个字符'}), 400
    record = EmailVerificationCode.query.filter_by(
        email=email, purpose='reset_password', used=False
    ).order_by(EmailVerificationCode.created_at.desc()).first()
    if not record or not record.is_valid():
        return jsonify({'error': '验证码无效或已过期'}), 400
    if record.code != code:
        return jsonify({'error': '验证码错误'}), 400
    user = User.query.get(record.user_id)
    if not user:
        return jsonify({'error': '用户不存在'}), 400
    record.used = True
    user.set_password(new_password)
    db.session.commit()
    return jsonify({'message': '密码重置成功，请用新密码登录'}), 200
