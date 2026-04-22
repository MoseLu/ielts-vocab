from __future__ import annotations

import smtplib
from email.message import EmailMessage

from services import auth_repository
from services.auth_session_helpers import (
    allow_mock_email_delivery,
    check_rate_limit,
    validate_email,
    verification_code_message,
)


def _delivery_mode(app) -> str:
    return app.config.get('EMAIL_CODE_DELIVERY_MODE', 'mock')


def _print_mock_code(email: str, code: str, purpose: str) -> None:
    print(f"\n{'='*50}")
    print(f"[Email Code] To: {email} | Purpose: {purpose} | Code: {code}")
    print(f"{'='*50}\n")


def _verification_payload(app, *, generic: bool) -> dict:
    return {
        'message': verification_code_message(app, generic=generic),
        'delivery_mode': _delivery_mode(app),
    }


def _normalized_email(value) -> str:
    return str(value or '').strip().lower()


def _latest_unused_code(email: str, purpose: str, *, user_id: int | None = None):
    return auth_repository.latest_unused_verification_code(
        email,
        purpose,
        user_id=user_id,
    )


def _smtp_is_configured(app) -> bool:
    return bool(app.config.get('SMTP_HOST') and app.config.get('SMTP_FROM_EMAIL'))


def _build_email_message(app, email: str, code: str, purpose: str) -> EmailMessage:
    subject = 'IELTS Vocabulary 验证码'
    purpose_label = '绑定邮箱' if purpose == 'bind_email' else '重置密码'
    message = EmailMessage()
    message['Subject'] = subject
    message['From'] = app.config['SMTP_FROM_EMAIL']
    message['To'] = email
    message.set_content(
        '\n'.join((
            '你好，',
            '',
            f'你正在使用 IELTS Vocabulary 执行“{purpose_label}”操作。',
            f'本次验证码是：{code}',
            '验证码 10 分钟内有效。',
            '',
            '如果这不是你的操作，请忽略这封邮件。',
        )),
        subtype='plain',
        charset='utf-8',
    )
    return message


def _send_via_smtp(app, email: str, code: str, purpose: str) -> None:
    message = _build_email_message(app, email, code, purpose)
    host = app.config['SMTP_HOST']
    port = app.config['SMTP_PORT']
    username = app.config.get('SMTP_USERNAME') or ''
    password = app.config.get('SMTP_PASSWORD') or ''
    use_ssl = bool(app.config.get('SMTP_USE_SSL'))
    use_tls = bool(app.config.get('SMTP_USE_TLS'))

    if use_ssl:
        with smtplib.SMTP_SSL(host, port, timeout=15) as client:
            if username or password:
                client.login(username, password)
            client.send_message(message)
        return

    with smtplib.SMTP(host, port, timeout=15) as client:
        client.ehlo()
        if use_tls:
            client.starttls()
            client.ehlo()
        if username or password:
            client.login(username, password)
        client.send_message(message)


def _deliver_verification_code(app, email: str, code: str, purpose: str) -> tuple[bool, str | None]:
    delivery_mode = _delivery_mode(app)
    if delivery_mode == 'mock':
        if not allow_mock_email_delivery(app):
            app.logger.error('Mock email delivery is disabled outside development/test environments.')
            return False, '邮箱服务未配置'
        _print_mock_code(email, code, purpose)
        return True, None

    if delivery_mode == 'smtp':
        if not _smtp_is_configured(app):
            app.logger.error('SMTP delivery mode is enabled but SMTP_HOST/SMTP_FROM_EMAIL are missing.')
            return False, '邮箱服务未配置'
        try:
            _send_via_smtp(app, email, code, purpose)
        except Exception:
            app.logger.exception('Failed to send verification email via SMTP.')
            return False, '邮件发送失败，请稍后重试'
        return True, None

    app.logger.error('Unsupported email delivery mode: %s', delivery_mode)
    return False, '邮箱服务未配置'


def send_bind_email_code_response(app, current_user, ip: str, data: dict | None) -> tuple[dict, int]:
    allowed, wait = check_rate_limit(app, ip, purpose='send_code')
    if not allowed:
        return {'error': f'操作过于频繁，请 {wait} 秒后再试'}, 429

    email = _normalized_email((data or {}).get('email'))
    if not email or not validate_email(email):
        return {'error': '请输入有效的邮箱地址'}, 400

    existing = auth_repository.get_user_by_email(email)
    if existing and existing.id != current_user.id:
        return {'error': '该邮箱已被其他账号绑定'}, 400

    auth_repository.mark_verification_codes_used(
        user_id=current_user.id,
        purpose='bind_email',
    )

    record = auth_repository.create_verification_code(
        email,
        'bind_email',
        user_id=current_user.id,
    )
    delivered, error_message = _deliver_verification_code(app, email, record.code, 'bind_email')
    if not delivered:
        return {'error': error_message or '邮箱服务未配置'}, 503
    return _verification_payload(app, generic=False), 200


def bind_email_response(current_user, data: dict | None) -> tuple[dict, int]:
    payload = data or {}
    email = _normalized_email(payload.get('email'))
    code = str(payload.get('code') or '').strip()
    if not email or not code:
        return {'error': '请输入邮箱和验证码'}, 400

    record = _latest_unused_code(email, 'bind_email', user_id=current_user.id)
    if not record or not record.is_valid():
        return {'error': '验证码无效或已过期'}, 400
    if record.code != code:
        return {'error': '验证码错误'}, 400

    existing = auth_repository.get_user_by_email(email)
    if existing and existing.id != current_user.id:
        return {'error': '该邮箱已被其他账号绑定'}, 400

    record.used = True
    current_user.email = email
    auth_repository.commit_user(current_user)
    return {'message': '邮箱绑定成功', 'user': current_user.to_dict()}, 200


def forgot_password_response(app, ip: str, data: dict | None) -> tuple[dict, int]:
    allowed, wait = check_rate_limit(app, ip, purpose='forgot_password')
    if not allowed:
        return {'error': f'操作过于频繁，请 {wait} 秒后再试'}, 429

    email = _normalized_email((data or {}).get('email'))
    if not email or not validate_email(email):
        return {'error': '请输入有效的邮箱地址'}, 400

    user = auth_repository.get_user_by_email(email)
    if not user:
        return _verification_payload(app, generic=True), 200

    auth_repository.mark_verification_codes_used(
        email=email,
        purpose='reset_password',
    )

    record = auth_repository.create_verification_code(
        email,
        'reset_password',
        user_id=user.id,
    )
    delivered, error_message = _deliver_verification_code(app, email, record.code, 'reset_password')
    if not delivered:
        return {'error': error_message or '邮箱服务未配置'}, 503
    return _verification_payload(app, generic=True), 200


def reset_password_response(data: dict | None) -> tuple[dict, int]:
    payload = data or {}
    email = _normalized_email(payload.get('email'))
    code = str(payload.get('code') or '').strip()
    new_password = payload.get('password', '')
    if not email or not code or not new_password:
        return {'error': '请填写所有字段'}, 400
    if len(new_password) < 6:
        return {'error': '密码至少6个字符'}, 400

    record = _latest_unused_code(email, 'reset_password')
    if not record or not record.is_valid():
        return {'error': '验证码无效或已过期'}, 400
    if record.code != code:
        return {'error': '验证码错误'}, 400

    user = auth_repository.get_user(record.user_id)
    if not user:
        return {'error': '用户不存在'}, 400

    record.used = True
    user.set_password(new_password)
    auth_repository.commit_user(user)
    return {'message': '密码重置成功，请用新密码登录'}, 200
