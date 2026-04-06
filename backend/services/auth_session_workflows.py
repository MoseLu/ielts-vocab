from __future__ import annotations

from datetime import datetime

import jwt

from models import RevokedToken, User, db
from services.auth_session_helpers import (
    check_rate_limit,
    find_user_by_identifier,
    log_registration_audit,
    login_rate_limit_subject,
    reset_rate_limit,
    revoke_token_if_present,
    validate_avatar_value,
    validate_email,
)


def perform_register(app, request, data: dict) -> tuple[dict, int, int | None]:
    email = (data.get('email') or '').strip()
    password = data.get('password', '')
    username = (data.get('username') or '').strip()

    if not username:
        log_registration_audit(app, request, outcome='rejected', reason='missing_username', username=username, email=email)
        return {'error': '请输入用户名'}, 400, None
    if len(username) < 3:
        log_registration_audit(app, request, outcome='rejected', reason='short_username', username=username, email=email)
        return {'error': '用户名至少3个字符'}, 400, None
    if not password or len(password) < 6:
        log_registration_audit(app, request, outcome='rejected', reason='short_password', username=username, email=email)
        return {'error': '密码至少6个字符'}, 400, None
    if User.query.filter_by(username=username).first():
        log_registration_audit(app, request, outcome='rejected', reason='duplicate_username', username=username, email=email)
        return {'error': '用户名已被使用'}, 400, None
    if email:
        if not validate_email(email):
            log_registration_audit(app, request, outcome='rejected', reason='invalid_email', username=username, email=email)
            return {'error': '邮箱格式不正确'}, 400, None
        if User.query.filter_by(email=email).first():
            log_registration_audit(app, request, outcome='rejected', reason='duplicate_email', username=username, email=email)
            return {'error': '该邮箱已被注册'}, 400, None

    user = User(email=email or None, username=username)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    log_registration_audit(
        app,
        request,
        outcome='created',
        reason='ok',
        username=username,
        email=email,
        user_id=user.id,
    )
    return {
        'message': '注册成功',
        'user': user.to_dict(),
        'access_expires_in': app.config['JWT_ACCESS_TOKEN_EXPIRES'],
    }, 201, user.id


def perform_login(app, request, data: dict) -> tuple[dict, int, int | None]:
    ip = request.remote_addr or '0.0.0.0'
    identifier = (data.get('email') or data.get('username') or '').strip()
    password = data.get('password', '')

    if not identifier or not password:
        return {'error': '请输入账号和密码'}, 400, None

    user = find_user_by_identifier(identifier)
    subject = login_rate_limit_subject(identifier, user)
    allowed, wait = check_rate_limit(app, ip, subject=subject)
    if not allowed:
        return {
            'error': f'登录尝试过于频繁，请 {wait} 秒后再试',
            'retry_after': wait,
        }, 429, None

    if not user or not user.check_password(password):
        return {'error': '账号或密码错误'}, 401, None

    reset_rate_limit(ip, subject=subject)
    return {
        'message': '登录成功',
        'user': user.to_dict(),
        'access_expires_in': app.config['JWT_ACCESS_TOKEN_EXPIRES'],
    }, 200, user.id


def perform_refresh(app, refresh_token: str | None) -> tuple[dict, int, int | None]:
    if not refresh_token:
        return {'error': '请先登录', 'code': 'NO_TOKEN'}, 401, None

    try:
        payload = jwt.decode(
            refresh_token,
            app.config['JWT_SECRET_KEY'],
            algorithms=['HS256'],
        )
    except jwt.ExpiredSignatureError:
        return {'error': '登录已过期，请重新登录', 'code': 'TOKEN_EXPIRED'}, 401, None
    except jwt.InvalidTokenError:
        return {'error': '登录凭证无效', 'code': 'INVALID_TOKEN'}, 401, None

    if payload.get('type') != 'refresh':
        return {'error': '登录凭证类型错误', 'code': 'WRONG_TOKEN_TYPE'}, 401, None

    old_jti = payload.get('jti')
    if old_jti and RevokedToken.is_revoked(old_jti):
        try:
            victim = User.query.get(payload['user_id'])
            if victim:
                victim.tokens_revoked_before = datetime.utcnow()
                db.session.commit()
        except Exception:
            pass
        return {'error': '登录凭证已失效，请重新登录', 'code': 'TOKEN_REVOKED'}, 401, None

    user = User.query.get(payload['user_id'])
    if not user:
        return {'error': '用户不存在', 'code': 'USER_NOT_FOUND'}, 401, None

    if old_jti:
        RevokedToken.revoke(old_jti, datetime.utcfromtimestamp(payload['exp']))

    return {
        'message': 'ok',
        'user': user.to_dict(),
        'access_expires_in': app.config['JWT_ACCESS_TOKEN_EXPIRES'],
    }, 200, user.id


def perform_logout(app, access_token: str | None, refresh_token: str | None) -> tuple[dict, int]:
    revoke_token_if_present(app, access_token)
    revoke_token_if_present(app, refresh_token)
    try:
        RevokedToken.prune_expired()
    except Exception:
        pass
    return {'message': '已退出登录'}, 200


def get_current_user_payload(app, request, current_user) -> tuple[dict, int]:
    try:
        token = request.cookies.get('access_token') or ''
        payload = jwt.decode(token, app.config['JWT_SECRET_KEY'], algorithms=['HS256'])
        expires_in = max(0, int(payload['exp'] - datetime.utcnow().timestamp()))
    except Exception:
        expires_in = app.config['JWT_ACCESS_TOKEN_EXPIRES']
    return {'user': current_user.to_dict(), 'access_expires_in': expires_in}, 200


def update_avatar(current_user, data: dict) -> tuple[dict, int]:
    avatar_url = data.get('avatar_url', '')
    error = validate_avatar_value(avatar_url)
    if error:
        return {'error': error}, 400
    current_user.avatar_url = avatar_url
    db.session.commit()
    return {'message': '头像已更新', 'user': current_user.to_dict()}, 200
