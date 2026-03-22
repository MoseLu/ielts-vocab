from flask import Blueprint, request, jsonify
from models import db, User, EmailVerificationCode
import jwt
from datetime import datetime, timedelta
from functools import wraps

auth_bp = Blueprint('auth', __name__)


def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            if auth_header.startswith('Bearer '):
                token = auth_header.split(' ')[1]

        if not token:
            return jsonify({'error': '请先登录'}), 401

        try:
            data = jwt.decode(token, app.config['JWT_SECRET_KEY'], algorithms=['HS256'])
            current_user = User.query.get(data['user_id'])
            if not current_user:
                return jsonify({'error': '用户不存在'}), 401
        except jwt.ExpiredSignatureError:
            return jsonify({'error': '登录已过期，请重新登录'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': '登录凭证无效，请重新登录'}), 401

        return f(current_user, *args, **kwargs)

    return decorated


# Store app reference for token_required decorator
app = None


def init_auth(app_instance):
    global app
    app = app_instance


def _make_token(user_id):
    return jwt.encode({
        'user_id': user_id,
        'exp': datetime.utcnow() + timedelta(seconds=app.config['JWT_ACCESS_TOKEN_EXPIRES'])
    }, app.config['JWT_SECRET_KEY'], algorithm='HS256')


@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()

    email = (data.get('email') or '').strip()
    password = data.get('password', '')
    username = (data.get('username') or '').strip()

    if not username:
        return jsonify({'error': '请输入用户名'}), 400
    if len(username) < 3:
        return jsonify({'error': '用户名至少3个字符'}), 400
    if not password or len(password) < 6:
        return jsonify({'error': '密码至少6个字符'}), 400

    # Username uniqueness
    if User.query.filter_by(username=username).first():
        return jsonify({'error': '用户名已被使用'}), 400

    # Email checks (only when provided)
    if email:
        if '@' not in email:
            return jsonify({'error': '邮箱格式不正确'}), 400
        if User.query.filter_by(email=email).first():
            return jsonify({'error': '该邮箱已被注册'}), 400

    user = User(email=email or None, username=username)
    user.set_password(password)

    db.session.add(user)
    db.session.commit()

    token = _make_token(user.id)
    return jsonify({
        'message': '注册成功',
        'token': token,
        'user': user.to_dict()
    }), 201


@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()

    # Accept login by email OR username
    identifier = (data.get('email') or data.get('username') or '').strip()
    password = data.get('password', '')

    if not identifier or not password:
        return jsonify({'error': '请输入账号和密码'}), 400

    # Look up by email first, then by username
    if '@' in identifier:
        user = User.query.filter_by(email=identifier).first()
    else:
        user = User.query.filter_by(username=identifier).first()
        if not user:
            # Also try email field just in case
            user = User.query.filter_by(email=identifier).first()

    if not user or not user.check_password(password):
        return jsonify({'error': '账号或密码错误'}), 401

    token = _make_token(user.id)
    return jsonify({
        'message': '登录成功',
        'token': token,
        'user': user.to_dict()
    }), 200


@auth_bp.route('/logout', methods=['POST'])
@token_required
def logout(current_user):
    return jsonify({'message': '已退出登录'}), 200


@auth_bp.route('/me', methods=['GET'])
@token_required
def get_current_user(current_user):
    return jsonify({'user': current_user.to_dict()}), 200


@auth_bp.route('/avatar', methods=['PUT'])
@token_required
def update_avatar(current_user):
    data = request.get_json()
    avatar_url = data.get('avatar_url', '')
    if len(avatar_url) > 700000:
        return jsonify({'error': '头像图片过大，请选择小于500KB的图片'}), 400
    current_user.avatar_url = avatar_url
    db.session.commit()
    return jsonify({'message': '头像已更新', 'user': current_user.to_dict()}), 200


# ── Email Verification Code ────────────────────────────────────────────────────

def _send_code_mock(email, code, purpose):
    """In development, print the code to console. Replace with real SMTP in production."""
    print(f"\n{'='*50}")
    print(f"[Email Code] To: {email} | Purpose: {purpose} | Code: {code}")
    print(f"{'='*50}\n")


@auth_bp.route('/send-code', methods=['POST'])
@token_required
def send_bind_email_code(current_user):
    """Send a verification code for email binding (requires auth)."""
    data = request.get_json()
    email = (data.get('email') or '').strip().lower()

    if not email or '@' not in email:
        return jsonify({'error': '请输入有效的邮箱地址'}), 400

    # Check email not already used by another account
    existing = User.query.filter_by(email=email).first()
    if existing and existing.id != current_user.id:
        return jsonify({'error': '该邮箱已被其他账号绑定'}), 400

    # Invalidate previous unused codes for this user+purpose
    EmailVerificationCode.query.filter_by(
        user_id=current_user.id, purpose='bind_email', used=False
    ).update({'used': True})
    db.session.commit()

    record = EmailVerificationCode.create_for(email, 'bind_email', user_id=current_user.id)
    _send_code_mock(email, record.code, 'bind_email')

    return jsonify({'message': '验证码已发送，请查收邮件（有效期10分钟）', 'dev_code': record.code}), 200


@auth_bp.route('/bind-email', methods=['POST'])
@token_required
def bind_email(current_user):
    """Bind an email to the current account using verification code."""
    data = request.get_json()
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

    # Check email not taken
    existing = User.query.filter_by(email=email).first()
    if existing and existing.id != current_user.id:
        return jsonify({'error': '该邮箱已被其他账号绑定'}), 400

    record.used = True
    current_user.email = email
    db.session.commit()

    return jsonify({'message': '邮箱绑定成功', 'user': current_user.to_dict()}), 200


# ── Forgot / Reset Password ────────────────────────────────────────────────────

@auth_bp.route('/forgot-password', methods=['POST'])
def forgot_password():
    """Send a password reset code to the registered email (no auth required)."""
    data = request.get_json()
    email = (data.get('email') or '').strip().lower()

    if not email or '@' not in email:
        return jsonify({'error': '请输入有效的邮箱地址'}), 400

    user = User.query.filter_by(email=email).first()
    # Always return success to prevent email enumeration
    if not user:
        return jsonify({'message': '如果该邮箱已注册，验证码已发送，请查收邮件'}), 200

    # Invalidate previous codes
    EmailVerificationCode.query.filter_by(
        email=email, purpose='reset_password', used=False
    ).update({'used': True})
    db.session.commit()

    record = EmailVerificationCode.create_for(email, 'reset_password', user_id=user.id)
    _send_code_mock(email, record.code, 'reset_password')

    return jsonify({'message': '如果该邮箱已注册，验证码已发送，请查收邮件', 'dev_code': record.code}), 200


@auth_bp.route('/reset-password', methods=['POST'])
def reset_password():
    """Reset password using email + verification code."""
    data = request.get_json()
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
