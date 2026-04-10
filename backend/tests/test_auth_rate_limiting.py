# ── Tests for backend/routes/auth.py rate limiting ───────────────────────────

from datetime import datetime, timedelta

from models import RateLimitBucket, db


class TestLoginRateLimiting:
    """Rate limiting must work across all login attempts, not just per-process."""

    def test_rate_limit_blocks_after_10_failures(self, client, app):
        client.post('/api/auth/register', json={
            'username': 'alice', 'password': 'correctpassword', 'email': 'alice@example.com',
        })

        for index in range(10):
            res = client.post('/api/auth/login', json={
                'email': 'alice@example.com',
                'password': 'wrongpassword',
            })
            assert res.status_code == 401, f"Attempt {index + 1} should be 401, got {res.status_code}"

        res = client.post('/api/auth/login', json={
            'email': 'alice@example.com',
            'password': 'wrongpassword',
        })
        assert res.status_code == 429, f"11th attempt should be rate-limited (429), got {res.status_code}"
        data = res.get_json()
        assert 'retry_after' in data

    def test_rate_limit_allows_after_window_resets(self, client, app):
        client.post('/api/auth/register', json={
            'username': 'alice', 'password': 'correctpassword', 'email': 'alice@example.com',
        })

        for _ in range(10):
            client.post('/api/auth/login', json={
                'email': 'alice@example.com',
                'password': 'wrongpassword',
            })

        res = client.post('/api/auth/login', json={
            'email': 'alice@example.com',
            'password': 'wrongpassword',
        })
        assert res.status_code == 429

        with app.app_context():
            bucket = RateLimitBucket.query.filter_by(purpose='login').first()
            if bucket:
                bucket.reset_at = datetime.utcnow() - timedelta(minutes=1)
                db.session.commit()

        res = client.post('/api/auth/login', json={
            'email': 'alice@example.com',
            'password': 'correctpassword',
        })
        assert res.status_code == 200

    def test_rate_limit_is_scoped_by_login_identifier(self, client, app):
        client.post('/api/auth/register', json={
            'username': 'alice', 'password': 'password123', 'email': 'alice@example.com',
        })
        client.post('/api/auth/register', json={
            'username': 'bob', 'password': 'password123', 'email': 'bob@example.com',
        })

        common_headers = {'X-Forwarded-For': '198.51.100.10, 10.0.0.1'}
        common_environ = {'REMOTE_ADDR': '127.0.0.1'}

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
            'username': 'alice', 'password': 'password123', 'email': 'alice@example.com',
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
            'username': 'alice', 'password': 'correctpassword', 'email': 'alice@example.com',
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
