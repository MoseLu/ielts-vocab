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
        assert 'access_expires_in' in data
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
        client.post('/api/auth/register', json={
            'username': 'alice', 'password': 'password123'
        })
        res = client.post('/api/auth/logout')
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
        client.post('/api/auth/register', json={
            'username': 'alice', 'password': 'password123'
        })
        res = client.get('/api/auth/me')
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
        client.post('/api/auth/register', json={
            'username': 'alice', 'password': 'password123'
        })
        res = client.post('/api/auth/send-code', json={'email': 'not-email'})
        assert res.status_code == 400

    def test_send_code_success(self, client, app, db):
        client.post('/api/auth/register', json={
            'username': 'alice', 'password': 'password123'
        })
        res = client.post('/api/auth/send-code', json={
            'email': 'newemail@example.com'
        })
        assert res.status_code == 200
        assert 'dev_code' not in res.get_json()


# ── /bind-email ────────────────────────────────────────────────────────────────

class TestBindEmail:
    def test_bind_email_unauthenticated(self, client):
        res = client.post('/api/auth/bind-email', json={'email': 'a@b.com', 'code': '123456'})
        assert res.status_code == 401

    def test_bind_email_missing_fields(self, client, app):
        client.post('/api/auth/register', json={
            'username': 'alice', 'password': 'password123'
        })
        res = client.post('/api/auth/bind-email', json={})
        assert res.status_code == 400

    def test_bind_email_wrong_code(self, client, app, db):
        reg = client.post('/api/auth/register', json={
            'username': 'alice', 'password': 'password123'
        })
        user_id = reg.get_json()['user']['id']
        # Manually create a valid code
        from models import EmailVerificationCode
        with app.app_context():
            EmailVerificationCode.create_for('test@b.com', 'bind_email', user_id=user_id)
            code = EmailVerificationCode.query.first().code
        # Try with wrong code
        res = client.post('/api/auth/bind-email', json={
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
        assert 'dev_code' not in res.get_json()


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


# ── /login Rate Limiting ───────────────────────────────────────────────────────

class TestLoginRateLimiting:
    """Rate limiting must work across all login attempts, not just per-process."""

    def test_rate_limit_blocks_after_10_failures(self, client, app):
        """After 10 failed logins, the 11th attempt should be rate-limited (429)."""
        # Register a real user so we're hitting real auth logic
        client.post('/api/auth/register', json={
            'username': 'alice', 'password': 'correctpassword', 'email': 'alice@example.com'
        })

        # Make 10 failed login attempts (wrong password)
        for i in range(10):
            res = client.post('/api/auth/login', json={
                'email': 'alice@example.com',
                'password': 'wrongpassword'
            })
            # First 10 should all get 401, not rate limited
            assert res.status_code == 401, f"Attempt {i+1} should be 401, got {res.status_code}"

        # The 11th attempt should be blocked by rate limiting
        res = client.post('/api/auth/login', json={
            'email': 'alice@example.com',
            'password': 'wrongpassword'
        })
        assert res.status_code == 429, f"11th attempt should be rate-limited (429), got {res.status_code}"
        data = res.get_json()
        assert 'retry_after' in data, "Should include retry_after seconds"

    def test_rate_limit_allows_after_window_resets(self, client, app):
        """After lockout window expires, login should be allowed again."""
        from datetime import datetime, timedelta
        from models import RateLimitBucket

        # Register a real user
        client.post('/api/auth/register', json={
            'username': 'alice', 'password': 'correctpassword', 'email': 'alice@example.com'
        })

        # Exhaust rate limit
        for _ in range(10):
            client.post('/api/auth/login', json={
                'email': 'alice@example.com', 'password': 'wrongpassword'
            })

        # Verify blocked
        res = client.post('/api/auth/login', json={
            'email': 'alice@example.com', 'password': 'wrongpassword'
        })
        assert res.status_code == 429

        # Manually expire the bucket in DB (simulate time passing)
        # This tests that the bucket resets correctly
        with app.app_context():
            bucket = RateLimitBucket.query.filter_by(purpose='login').first()
            if bucket:
                bucket.reset_at = datetime.utcnow() - timedelta(minutes=1)
                from models import db
                db.session.commit()

        # Now should be allowed again
        res = client.post('/api/auth/login', json={
            'email': 'alice@example.com', 'password': 'correctpassword'
        })
        assert res.status_code == 200, "Should allow login after window expires"

    def test_rate_limit_is_scoped_by_login_identifier(self, client, app):
        """One account's failures should not lock other accounts behind the same proxy IP."""
        # Register two users
        client.post('/api/auth/register', json={
            'username': 'alice', 'password': 'password123', 'email': 'alice@example.com'
        })
        client.post('/api/auth/register', json={
            'username': 'bob', 'password': 'password123', 'email': 'bob@example.com'
        })

        common_headers = {'X-Forwarded-For': '198.51.100.10, 10.0.0.1'}
        common_environ = {'REMOTE_ADDR': '127.0.0.1'}

        # Exhaust rate limit for alice using the same proxy chain/IP.
        for _ in range(10):
            res = client.post(
                '/api/auth/login',
                json={'email': 'alice@example.com', 'password': 'wrongpassword'},
                headers=common_headers,
                environ_overrides=common_environ,
            )
            assert res.status_code == 401

        blocked = client.post(
            '/api/auth/login',
            json={'email': 'alice@example.com', 'password': 'wrongpassword'},
            headers=common_headers,
            environ_overrides=common_environ,
        )
        assert blocked.status_code == 429

        bob_wrong = client.post(
            '/api/auth/login',
            json={'email': 'bob@example.com', 'password': 'wrongpassword'},
            headers=common_headers,
            environ_overrides=common_environ,
        )
        assert bob_wrong.status_code == 401

        bob_success = client.post(
            '/api/auth/login',
            json={'email': 'bob@example.com', 'password': 'password123'},
            headers=common_headers,
            environ_overrides=common_environ,
        )
        assert bob_success.status_code == 200

    def test_rate_limit_shares_bucket_between_email_and_username_for_same_account(self, client):
        client.post('/api/auth/register', json={
            'username': 'alice', 'password': 'password123', 'email': 'alice@example.com'
        })

        common_headers = {'X-Forwarded-For': '198.51.100.10, 10.0.0.1'}
        common_environ = {'REMOTE_ADDR': '127.0.0.1'}

        for _ in range(5):
            res = client.post(
                '/api/auth/login',
                json={'email': 'alice@example.com', 'password': 'wrongpassword'},
                headers=common_headers,
                environ_overrides=common_environ,
            )
            assert res.status_code == 401

        for _ in range(5):
            res = client.post(
                '/api/auth/login',
                json={'email': 'alice', 'password': 'wrongpassword'},
                headers=common_headers,
                environ_overrides=common_environ,
            )
            assert res.status_code == 401

        blocked = client.post(
            '/api/auth/login',
            json={'email': 'alice', 'password': 'wrongpassword'},
            headers=common_headers,
            environ_overrides=common_environ,
        )
        assert blocked.status_code == 429

    def test_rate_limit_uses_forwarded_client_ip_in_proxy_mode(self, client):
        client.post('/api/auth/register', json={
            'username': 'alice', 'password': 'correctpassword', 'email': 'alice@example.com'
        })

        def failed_login(forwarded_for: str):
            return client.post(
                '/api/auth/login',
                json={'email': 'alice@example.com', 'password': 'wrongpassword'},
                headers={'X-Forwarded-For': forwarded_for},
                environ_overrides={'REMOTE_ADDR': '127.0.0.1'},
            )

        for _ in range(10):
            res = failed_login('198.51.100.10, 10.0.0.1')
            assert res.status_code == 401

        blocked = failed_login('198.51.100.10, 10.0.0.1')
        assert blocked.status_code == 429

        other_ip = failed_login('198.51.100.11, 10.0.0.1')
        assert other_ip.status_code == 401
