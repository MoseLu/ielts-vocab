from flask import Blueprint, request, jsonify
from models import db, User
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
            return jsonify({'error': 'Token is missing'}), 401

        try:
            # Decode JWT token directly - no need to check active_tokens
            data = jwt.decode(token, app.config['JWT_SECRET_KEY'], algorithms=['HS256'])
            current_user = User.query.get(data['user_id'])
            if not current_user:
                return jsonify({'error': 'User not found'}), 401
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token has expired'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Invalid token'}), 401

        return f(current_user, *args, **kwargs)

    return decorated


# Store app reference for token_required decorator
app = None


def init_auth(app_instance):
    global app
    app = app_instance


@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()

    email = data.get('email', '').strip()
    password = data.get('password', '')
    username = data.get('username', '').strip()

    # Validation
    if not email or not password or not username:
        return jsonify({'error': 'Email, password and username are required'}), 400

    if len(username) < 3:
        return jsonify({'error': 'Username must be at least 3 characters'}), 400

    if len(password) < 6:
        return jsonify({'error': 'Password must be at least 6 characters'}), 400

    if '@' not in email:
        return jsonify({'error': 'Invalid email format'}), 400

    # Check if user exists
    if User.query.filter_by(email=email).first():
        return jsonify({'error': 'Email already registered'}), 400

    # Create user
    user = User(email=email, username=username)
    user.set_password(password)

    db.session.add(user)
    db.session.commit()

    # Generate token
    token = jwt.encode({
        'user_id': user.id,
        'exp': datetime.utcnow() + timedelta(seconds=app.config['JWT_ACCESS_TOKEN_EXPIRES'])
    }, app.config['JWT_SECRET_KEY'], algorithm='HS256')

    return jsonify({
        'message': 'Registration successful',
        'token': token,
        'user': user.to_dict()
    }), 201


@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()

    email = data.get('email', '').strip()
    password = data.get('password', '')

    if not email or not password:
        return jsonify({'error': 'Email and password are required'}), 400

    user = User.query.filter_by(email=email).first()

    if not user or not user.check_password(password):
        return jsonify({'error': 'Invalid email or password'}), 401

    # Generate token
    token = jwt.encode({
        'user_id': user.id,
        'exp': datetime.utcnow() + timedelta(seconds=app.config['JWT_ACCESS_TOKEN_EXPIRES'])
    }, app.config['JWT_SECRET_KEY'], algorithm='HS256')

    return jsonify({
        'message': 'Login successful',
        'token': token,
        'user': user.to_dict()
    }), 200


@auth_bp.route('/logout', methods=['POST'])
@token_required
def logout(current_user):
    # JWT tokens are stateless, just return success
    # Client should remove token from localStorage
    return jsonify({'message': 'Logout successful'}), 200


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
    return jsonify({'message': 'Avatar updated', 'user': current_user.to_dict()}), 200
