# ── Tests for backend/routes/auth.py email flows ─────────────────────────────

from models import EmailVerificationCode


class TestSendCode:
    def test_send_code_unauthenticated(self, client):
        res = client.post('/api/auth/send-code', json={'email': 'a@b.com'})
        assert res.status_code == 401

    def test_send_code_invalid_email(self, client, app):
        client.post('/api/auth/register', json={
            'username': 'alice', 'password': 'password123',
        })
        res = client.post('/api/auth/send-code', json={'email': 'not-email'})
        assert res.status_code == 400

    def test_send_code_success(self, client, app, db):
        client.post('/api/auth/register', json={
            'username': 'alice', 'password': 'password123',
        })
        res = client.post('/api/auth/send-code', json={
            'email': 'newemail@example.com',
        })
        assert res.status_code == 200
        assert 'dev_code' not in res.get_json()


class TestBindEmail:
    def test_bind_email_unauthenticated(self, client):
        res = client.post('/api/auth/bind-email', json={'email': 'a@b.com', 'code': '123456'})
        assert res.status_code == 401

    def test_bind_email_missing_fields(self, client, app):
        client.post('/api/auth/register', json={
            'username': 'alice', 'password': 'password123',
        })
        res = client.post('/api/auth/bind-email', json={})
        assert res.status_code == 400

    def test_bind_email_wrong_code(self, client, app, db):
        reg = client.post('/api/auth/register', json={
            'username': 'alice', 'password': 'password123',
        })
        user_id = reg.get_json()['user']['id']
        with app.app_context():
            EmailVerificationCode.create_for('test@b.com', 'bind_email', user_id=user_id)
        res = client.post('/api/auth/bind-email', json={
            'email': 'test@b.com', 'code': '000000',
        })
        assert res.status_code == 400
        assert '错误' in res.get_json()['error']


class TestForgotPassword:
    def test_forgot_password_unknown_email(self, client):
        res = client.post('/api/auth/forgot-password', json={'email': 'nobody@example.com'})
        assert res.status_code == 200

    def test_forgot_password_invalid_email(self, client):
        res = client.post('/api/auth/forgot-password', json={'email': 'not-email'})
        assert res.status_code == 400

    def test_forgot_password_known_user(self, client):
        client.post('/api/auth/register', json={
            'username': 'alice', 'password': 'password123', 'email': 'alice@example.com',
        })
        res = client.post('/api/auth/forgot-password', json={'email': 'alice@example.com'})
        assert res.status_code == 200
        assert 'dev_code' not in res.get_json()


class TestResetPassword:
    def test_reset_password_wrong_code(self, client, app):
        client.post('/api/auth/register', json={
            'username': 'alice', 'password': 'password123', 'email': 'alice@example.com',
        })
        client.post('/api/auth/forgot-password', json={'email': 'alice@example.com'})
        res = client.post('/api/auth/reset-password', json={
            'email': 'alice@example.com', 'code': '000000', 'password': 'newpassword123',
        })
        assert res.status_code == 400
        assert '错误' in res.get_json()['error']

    def test_reset_password_short_password(self, client, app):
        client.post('/api/auth/register', json={
            'username': 'alice', 'password': 'password123', 'email': 'alice@example.com',
        })
        client.post('/api/auth/forgot-password', json={'email': 'alice@example.com'})
        res = client.post('/api/auth/reset-password', json={
            'email': 'alice@example.com', 'code': '000000', 'password': '123',
        })
        assert res.status_code == 400
