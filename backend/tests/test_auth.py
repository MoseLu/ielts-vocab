# ── Tests for backend/routes/auth.py ───────────────────────────────────────────

import pytest
from models import db, User, EmailVerificationCode
import jwt
from datetime import datetime, timedelta


# ── Helpers ────────────────────────────────────────────────────────────────────

def make_token(app, user_id):
    """Generate a valid JWT for the given user."""
    with app.app_context():
        return jwt.encode(
            {
                'user_id': user_id,
                'exp': datetime.utcnow() + timedelta(seconds=app.config['JWT_ACCESS_TOKEN_EXPIRES'])
            },
            app.config['JWT_SECRET_KEY'],
            algorithm='HS256'
        )


def auth_header(token):
    return {'Authorization': f'Bearer {token}'}


# ── /register ─────────────────────────────────────────────────────────────────

class TestRegister:
    def test_register_success(self, client, app):
        res = client.post('/api/auth/register', json={
            'username': 'alice',
            'password': 'password123',
            'email': 'alice@example.com'
        })
        assert res.status_code == 201
        data = res.get_json()
        assert 'token' in data
        assert data['user']['username'] == 'alice'
        assert data['user']['email'] == 'alice@example.com'

    def test_register_without_email(self, client):
        res = client.post('/api/auth/register', json={
            'username': 'bob',
            'password': 'password123',
        })
        assert res.status_code == 201
        data = res.get_json()
        assert data['user']['email'] == ''

    def test_register_missing_username(self, client):
        res = client.post('/api/auth/register', json={
            'password': 'password123',
        })
        assert res.status_code == 400
        assert '用户名' in res.get_json()['error']

    def test_register_short_username(self, client):
        res = client.post('/api/auth/register', json={
            'username': 'ab',
            'password': 'password123',
        })
        assert res.status_code == 400
        assert '3个字符' in res.get_json()['error']

    def test_register_short_password(self, client):
        res = client.post('/api/auth/register', json={
            'username': 'alice',
            'password': '12345',
        })
        assert res.status_code == 400
        assert '6个字符' in res.get_json()['error']

    def test_register_duplicate_username(self, client):
        client.post('/api/auth/register', json={'username': 'alice', 'password': 'password123'})
        res = client.post('/api/auth/register', json={'username': 'alice', 'password': 'password456'})
        assert res.status_code == 400
        assert '已被使用' in res.get_json()['error']

    def test_register_duplicate_email(self, client):
        client.post('/api/auth/register', json={
            'username': 'alice', 'password': 'password123', 'email': 'alice@example.com'
        })
        res = client.post('/api/auth/register', json={
            'username': 'alice2', 'password': 'password123', 'email': 'alice@example.com'
        })
        assert res.status_code == 400
        assert '已被注册' in res.get_json()['error']

    def test_register_invalid_email_format(self, client):
        res = client.post('/api/auth/register', json={
            'username': 'alice', 'password': 'password123', 'email': 'not-an-email'
        })
        assert res.status_code == 400
        assert '邮箱' in res.get_json()['error']


# ── /login ─────────────────────────────────────────────────────────────────────

class TestLogin:
    def test_login_by_email(self, client, app):
        client.post('/api/auth/register', json={
            'username': 'alice', 'password': 'password123', 'email': 'alice@example.com'
        })
        res = client.post('/api/auth/login', json={
            'email': 'alice@example.com',
            'password': 'password123'
        })
        assert res.status_code == 200
        data = res.get_json()
        assert 'token' in data
        assert data['user']['username'] == 'alice'

    def test_login_by_username(self, client):
        client.post('/api/auth/register', json={
            'username': 'alice', 'password': 'password123', 'email': 'alice@example.com'
        })
        res = client.post('/api/auth/login', json={
            'email': 'alice',
            'password': 'password123'
        })
        assert res.status_code == 200

    def test_login_wrong_password(self, client):
        client.post('/api/auth/register', json={
            'username': 'alice', 'password': 'password123'
        })
        res = client.post('/api/auth/login', json={
            'email': 'alice',
            'password': 'wrongpassword'
        })
        assert res.status_code == 401
        assert '错误' in res.get_json()['error']

    def test_login_nonexistent_user(self, client):
        res = client.post('/api/auth/login', json={
            'email': 'nobody@example.com',
            'password': 'password123'
        })
        assert res.status_code == 401

    def test_login_missing_credentials(self, client):
        res = client.post('/api/auth/login', json={})
        assert res.status_code == 400


# ── /logout ────────────────────────────────────────────────────────────────────

class TestLogout:
    def test_logout_success(self, client, app):
        reg = client.post('/api/auth/register', json={
            'username': 'alice', 'password': 'password123'
        })
        token = reg.get_json()['token']
        res = client.post('/api/auth/logout', headers=auth_header(token))
        assert res.status_code == 200

    def test_logout_no_token(self, client):
        res = client.post('/api/auth/logout')
        assert res.status_code == 401

    def test_logout_expired_token(self, client, app):
        token = jwt.encode(
            {'user_id': 999, 'exp': datetime.utcnow() - timedelta(seconds=10)},
            app.config['JWT_SECRET_KEY'], algorithm='HS256'
        )
        res = client.post('/api/auth/logout', headers=auth_header(token))
        assert res.status_code == 401


# ── /me ────────────────────────────────────────────────────────────────────────

class TestMe:
    def test_get_me_authenticated(self, client, app):
        reg = client.post('/api/auth/register', json={
            'username': 'alice', 'password': 'password123'
        })
        token = reg.get_json()['token']
        res = client.get('/api/auth/me', headers=auth_header(token))
        assert res.status_code == 200
        assert res.get_json()['user']['username'] == 'alice'

    def test_get_me_no_token(self, client):
        res = client.get('/api/auth/me')
        assert res.status_code == 401


# ── /send-code (requires auth) ─────────────────────────────────────────────────

class TestSendCode:
    def test_send_code_unauthenticated(self, client):
        res = client.post('/api/auth/send-code', json={'email': 'a@b.com'})
        assert res.status_code == 401

    def test_send_code_invalid_email(self, client, app):
        reg = client.post('/api/auth/register', json={
            'username': 'alice', 'password': 'password123'
        })
        token = reg.get_json()['token']
        res = client.post('/api/auth/send-code', headers=auth_header(token), json={'email': 'not-email'})
        assert res.status_code == 400

    def test_send_code_success(self, client, app, db):
        reg = client.post('/api/auth/register', json={
            'username': 'alice', 'password': 'password123'
        })
        token = reg.get_json()['token']
        res = client.post('/api/auth/send-code', headers=auth_header(token), json={
            'email': 'newemail@example.com'
        })
        assert res.status_code == 200
        # dev_code should be returned (mock email)
        assert 'dev_code' in res.get_json()


# ── /bind-email ────────────────────────────────────────────────────────────────

class TestBindEmail:
    def test_bind_email_unauthenticated(self, client):
        res = client.post('/api/auth/bind-email', json={'email': 'a@b.com', 'code': '123456'})
        assert res.status_code == 401

    def test_bind_email_missing_fields(self, client, app):
        reg = client.post('/api/auth/register', json={
            'username': 'alice', 'password': 'password123'
        })
        token = reg.get_json()['token']
        res = client.post('/api/auth/bind-email', headers=auth_header(token), json={})
        assert res.status_code == 400

    def test_bind_email_wrong_code(self, client, app, db):
        reg = client.post('/api/auth/register', json={
            'username': 'alice', 'password': 'password123'
        })
        token = reg.get_json()['token']
        user_id = reg.get_json()['user']['id']
        # Manually create a valid code
        from models import EmailVerificationCode
        with app.app_context():
            EmailVerificationCode.create_for('test@b.com', 'bind_email', user_id=user_id)
            code = EmailVerificationCode.query.first().code
        # Try with wrong code
        res = client.post('/api/auth/bind-email', headers=auth_header(token), json={
            'email': 'test@b.com', 'code': '000000'
        })
        assert res.status_code == 400
        assert '错误' in res.get_json()['error']


# ── /forgot-password ───────────────────────────────────────────────────────────

class TestForgotPassword:
    def test_forgot_password_unknown_email(self, client):
        """Should always return 200 to prevent email enumeration."""
        res = client.post('/api/auth/forgot-password', json={'email': 'nobody@example.com'})
        assert res.status_code == 200

    def test_forgot_password_invalid_email(self, client):
        res = client.post('/api/auth/forgot-password', json={'email': 'not-email'})
        assert res.status_code == 400

    def test_forgot_password_known_user(self, client):
        client.post('/api/auth/register', json={
            'username': 'alice', 'password': 'password123', 'email': 'alice@example.com'
        })
        res = client.post('/api/auth/forgot-password', json={'email': 'alice@example.com'})
        assert res.status_code == 200
        assert 'dev_code' in res.get_json()


# ── /reset-password ────────────────────────────────────────────────────────────

class TestResetPassword:
    def test_reset_password_wrong_code(self, client, app):
        """Register, request reset, then try with wrong code."""
        client.post('/api/auth/register', json={
            'username': 'alice', 'password': 'password123', 'email': 'alice@example.com'
        })
        res = client.post('/api/auth/forgot-password', json={'email': 'alice@example.com'})
        # Try reset with wrong code
        res = client.post('/api/auth/reset-password', json={
            'email': 'alice@example.com', 'code': '000000', 'password': 'newpassword123'
        })
        assert res.status_code == 400
        assert '错误' in res.get_json()['error']

    def test_reset_password_short_password(self, client, app):
        client.post('/api/auth/register', json={
            'username': 'alice', 'password': 'password123', 'email': 'alice@example.com'
        })
        res = client.post('/api/auth/forgot-password', json={'email': 'alice@example.com'})
        res = client.post('/api/auth/reset-password', json={
            'email': 'alice@example.com', 'code': '000000', 'password': '123'
        })
        assert res.status_code == 400
