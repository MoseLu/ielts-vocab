from __future__ import annotations

from platform_sdk.identity_session_support import check_rate_limit, validate_email, verification_code_message
from services import auth_repository


def _delivery_mode(app) -> str:
    return app.config.get('EMAIL_CODE_DELIVERY_MODE', 'mock')


def _print_mock_code(email: str, code: str, purpose: str) -> None:
    print(f"\n{'=' * 50}")
    print(f"[Email Code] To: {email} | Purpose: {purpose} | Code: {code}")
    print(f"{'=' * 50}\n")


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
    _print_mock_code(email, record.code, 'bind_email')
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
    _print_mock_code(email, record.code, 'reset_password')
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
