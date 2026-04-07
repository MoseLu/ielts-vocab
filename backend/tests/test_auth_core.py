# ── Tests for backend/routes/auth.py core auth flows ─────────────────────────

import jwt
from datetime import datetime, timedelta


def make_token(app, user_id):
    """Generate a valid JWT for the given user."""
    with app.app_context():
        return jwt.encode(
            {
                'user_id': user_id,
                'exp': datetime.utcnow() + timedelta(seconds=app.config['JWT_ACCESS_TOKEN_EXPIRES']),
            },
            app.config['JWT_SECRET_KEY'],
            algorithm='HS256',
        )


def auth_header(token):
    return {'Authorization': f'Bearer {token}'}


class TestRegister:
    def test_register_success(self, client, app):
        res = client.post('/api/auth/register', json={
            'username': 'alice',
            'password': 'password123',
            'email': 'alice@example.com',
        })
        assert res.status_code == 201
        data = res.get_json()
        assert 'access_expires_in' in data
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

    def test_register_logs_audit_context(self, client, caplog):
        caplog.set_level('INFO')
        res = client.post(
            '/api/auth/register',
            json={
                'username': 'audited-user',
                'password': 'password123',
                'email': 'audited-user@example.com',
            },
            headers={
                'X-Forwarded-For': '203.0.113.10, 10.0.0.1',
                'User-Agent': 'pytest-agent/1.0',
                'Origin': 'https://axiomaticworld.com',
            },
            environ_overrides={'REMOTE_ADDR': '127.0.0.1'},
        )
        assert res.status_code == 201
        assert 'Registration audit | outcome=created reason=ok' in caplog.text
        assert 'username=audited-user' in caplog.text
        assert 'email=audited-user@example.com' in caplog.text
        assert 'client_ip=203.0.113.10' in caplog.text
        assert 'forwarded_for=203.0.113.10, 10.0.0.1' in caplog.text

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
            'username': 'alice', 'password': 'password123', 'email': 'alice@example.com',
        })
        res = client.post('/api/auth/register', json={
            'username': 'alice2', 'password': 'password123', 'email': 'alice@example.com',
        })
        assert res.status_code == 400
        assert '已被注册' in res.get_json()['error']

    def test_register_invalid_email_format(self, client):
        res = client.post('/api/auth/register', json={
            'username': 'alice', 'password': 'password123', 'email': 'not-an-email',
        })
        assert res.status_code == 400
        assert '邮箱' in res.get_json()['error']


class TestLogin:
    def test_login_by_email(self, client, app):
        client.post('/api/auth/register', json={
            'username': 'alice', 'password': 'password123', 'email': 'alice@example.com',
        })
        res = client.post('/api/auth/login', json={
            'email': 'alice@example.com',
            'password': 'password123',
        })
        assert res.status_code == 200
        data = res.get_json()
        assert 'access_expires_in' in data
        assert data['user']['username'] == 'alice'

    def test_login_by_username(self, client):
        client.post('/api/auth/register', json={
            'username': 'alice', 'password': 'password123', 'email': 'alice@example.com',
        })
        res = client.post('/api/auth/login', json={
            'email': 'alice',
            'password': 'password123',
        })
        assert res.status_code == 200

    def test_login_wrong_password(self, client):
        client.post('/api/auth/register', json={
            'username': 'alice', 'password': 'password123',
        })
        res = client.post('/api/auth/login', json={
            'email': 'alice',
            'password': 'wrongpassword',
        })
        assert res.status_code == 401
        assert '错误' in res.get_json()['error']

    def test_login_nonexistent_user(self, client):
        res = client.post('/api/auth/login', json={
            'email': 'nobody@example.com',
            'password': 'password123',
        })
        assert res.status_code == 401

    def test_login_missing_credentials(self, client):
        res = client.post('/api/auth/login', json={})
        assert res.status_code == 400

    def test_login_local_http_origin_drops_secure_cookie(self, client, app):
        app.config['COOKIE_SECURE'] = True
        client.post('/api/auth/register', json={
            'username': 'alice', 'password': 'password123', 'email': 'alice@example.com',
        })
        res = client.post(
            '/api/auth/login',
            json={
                'email': 'alice@example.com',
                'password': 'password123',
            },
            base_url='http://127.0.0.1:5000',
            headers={
                'Origin': 'http://127.0.0.1:3002',
                'Referer': 'http://127.0.0.1:3002/login',
            },
        )
        assert res.status_code == 200
        cookies = res.headers.getlist('Set-Cookie')
        access_cookie = next(cookie for cookie in cookies if cookie.startswith('access_token='))
        refresh_cookie = next(cookie for cookie in cookies if cookie.startswith('refresh_token='))
        assert 'Secure' not in access_cookie
        assert 'Secure' not in refresh_cookie

    def test_login_https_origin_keeps_secure_cookie(self, client, app):
        app.config['COOKIE_SECURE'] = True
        client.post('/api/auth/register', json={
            'username': 'alice', 'password': 'password123', 'email': 'alice@example.com',
        })
        res = client.post(
            '/api/auth/login',
            json={
                'email': 'alice@example.com',
                'password': 'password123',
            },
            base_url='https://axiomaticworld.com',
            headers={'Origin': 'https://axiomaticworld.com'},
        )
        assert res.status_code == 200
        cookies = res.headers.getlist('Set-Cookie')
        access_cookie = next(cookie for cookie in cookies if cookie.startswith('access_token='))
        refresh_cookie = next(cookie for cookie in cookies if cookie.startswith('refresh_token='))
        assert 'Secure' in access_cookie
        assert 'Secure' in refresh_cookie

    def test_login_http_custom_domain_drops_secure_cookie(self, client, app):
        app.config['COOKIE_SECURE'] = True
        client.post('/api/auth/register', json={
            'username': 'alice', 'password': 'password123', 'email': 'alice@example.com',
        })
        res = client.post(
            '/api/auth/login',
            json={
                'email': 'alice@example.com',
                'password': 'password123',
            },
            base_url='http://axiomaticworld.com',
            headers={
                'Origin': 'http://axiomaticworld.com',
                'Referer': 'http://axiomaticworld.com/login',
                'Host': 'axiomaticworld.com',
            },
        )
        assert res.status_code == 200
        cookies = res.headers.getlist('Set-Cookie')
        access_cookie = next(cookie for cookie in cookies if cookie.startswith('access_token='))
        refresh_cookie = next(cookie for cookie in cookies if cookie.startswith('refresh_token='))
        assert 'Secure' not in access_cookie
        assert 'Secure' not in refresh_cookie


class TestLogout:
    def test_logout_success(self, client, app):
        client.post('/api/auth/register', json={
            'username': 'alice', 'password': 'password123',
        })
        res = client.post('/api/auth/logout')
        assert res.status_code == 200

    def test_logout_no_token(self, client):
        res = client.post('/api/auth/logout')
        assert res.status_code == 401

    def test_logout_expired_token(self, client, app):
        token = jwt.encode(
            {'user_id': 999, 'exp': datetime.utcnow() - timedelta(seconds=10)},
            app.config['JWT_SECRET_KEY'],
            algorithm='HS256',
        )
        res = client.post('/api/auth/logout', headers=auth_header(token))
        assert res.status_code == 401


class TestMe:
    def test_get_me_authenticated(self, client, app):
        client.post('/api/auth/register', json={
            'username': 'alice', 'password': 'password123',
        })
        res = client.get('/api/auth/me')
        assert res.status_code == 200
        assert res.get_json()['user']['username'] == 'alice'

    def test_get_me_no_token(self, client):
        res = client.get('/api/auth/me')
        assert res.status_code == 200
        assert res.get_json()['user'] is None
        assert res.get_json()['authenticated'] is False
