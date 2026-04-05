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
