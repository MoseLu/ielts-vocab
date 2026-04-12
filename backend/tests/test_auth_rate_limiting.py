# ── Tests for backend/routes/auth.py rate limiting ───────────────────────────

from datetime import datetime, timedelta

import pytest
from sqlalchemy.exc import IntegrityError

from models import RateLimitBucket, db
from platform_sdk import identity_rate_limit_runtime
from services import auth_repository


class FakeRedisRateLimitClient:
    def __init__(self):
        self._values: dict[str, int] = {}
        self._expires_at: dict[str, int] = {}
        self._now = 0

    def _prune(self, key: str) -> None:
        expires_at = self._expires_at.get(key)
        if expires_at is None:
            return
        if self._now < expires_at:
            return
        self._values.pop(key, None)
        self._expires_at.pop(key, None)

    def incr(self, key: str) -> int:
        self._prune(key)
        value = int(self._values.get(key, 0)) + 1
        self._values[key] = value
        return value

    def expire(self, key: str, seconds: int) -> bool:
        self._prune(key)
        if key not in self._values:
            return False
        self._expires_at[key] = self._now + int(seconds)
        return True

    def ttl(self, key: str) -> int:
        self._prune(key)
        if key not in self._values:
            return -2
        expires_at = self._expires_at.get(key)
        if expires_at is None:
            return -1
        return max(expires_at - self._now, 0)

    def delete(self, key: str) -> int:
        existed = key in self._values
        self._values.pop(key, None)
        self._expires_at.pop(key, None)
        return 1 if existed else 0

    def advance(self, seconds: int) -> None:
        self._now += int(seconds)


@pytest.fixture(autouse=True)
def disable_redis_rate_limit(monkeypatch):
    def _raise_unavailable(*args, **kwargs):
        raise RuntimeError('redis unavailable in this test')

    monkeypatch.setattr(identity_rate_limit_runtime, 'build_redis_client', _raise_unavailable)


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

    def test_rate_limit_falls_back_to_database_when_redis_is_unavailable(self, client, app):
        client.post('/api/auth/register', json={
            'username': 'alice', 'password': 'correctpassword', 'email': 'alice@example.com',
        })

        for _ in range(10):
            res = client.post('/api/auth/login', json={
                'email': 'alice@example.com',
                'password': 'wrongpassword',
            })
            assert res.status_code == 401

        blocked = client.post('/api/auth/login', json={
            'email': 'alice@example.com',
            'password': 'wrongpassword',
        })
        assert blocked.status_code == 429

        with app.app_context():
            assert RateLimitBucket.query.filter_by(purpose='login').count() == 1

    def test_rate_limit_retries_database_bucket_insert_after_unique_conflict(self, monkeypatch):
        attempts = {'count': 0}
        rollback_calls: list[str] = []

        def fake_check_and_increment(**kwargs):
            attempts['count'] += 1
            if attempts['count'] == 1:
                raise IntegrityError('INSERT', {}, Exception('unique_ip_purpose'))
            return True, 0

        monkeypatch.setattr(auth_repository, 'check_rate_limit_with_redis', lambda **kwargs: None)
        monkeypatch.setattr(auth_repository.RateLimitBucket, 'check_and_increment', fake_check_and_increment)
        monkeypatch.setattr(auth_repository.db.session, 'rollback', lambda: rollback_calls.append('rollback'))

        allowed, wait = auth_repository.check_rate_limit(
            ip_address='203.0.113.10',
            purpose='login',
            max_attempts=10,
            window_minutes=15,
        )

        assert (allowed, wait) == (True, 0)
        assert attempts['count'] == 2
        assert rollback_calls == ['rollback']

    def test_rate_limit_uses_redis_when_available(self, client, app, monkeypatch):
        fake_redis = FakeRedisRateLimitClient()
        monkeypatch.setattr(
            identity_rate_limit_runtime,
            'build_redis_client',
            lambda service_name=None: fake_redis,
        )

        client.post('/api/auth/register', json={
            'username': 'alice', 'password': 'correctpassword', 'email': 'alice@example.com',
        })

        for _ in range(10):
            res = client.post('/api/auth/login', json={
                'email': 'alice@example.com',
                'password': 'wrongpassword',
            })
            assert res.status_code == 401

        blocked = client.post('/api/auth/login', json={
            'email': 'alice@example.com',
            'password': 'wrongpassword',
        })
        assert blocked.status_code == 429

        with app.app_context():
            assert RateLimitBucket.query.filter_by(purpose='login').count() == 0

    def test_successful_login_resets_redis_bucket(self, client, monkeypatch, app):
        fake_redis = FakeRedisRateLimitClient()
        monkeypatch.setattr(
            identity_rate_limit_runtime,
            'build_redis_client',
            lambda service_name=None: fake_redis,
        )
        app.config['LOGIN_MAX_ATTEMPTS'] = 2

        client.post('/api/auth/register', json={
            'username': 'alice', 'password': 'correctpassword', 'email': 'alice@example.com',
        })

        wrong_once = client.post('/api/auth/login', json={
            'email': 'alice@example.com',
            'password': 'wrongpassword',
        })
        assert wrong_once.status_code == 401
        assert fake_redis._values

        success = client.post('/api/auth/login', json={
            'email': 'alice@example.com',
            'password': 'correctpassword',
        })
        assert success.status_code == 200
        assert fake_redis._values == {}

        next_wrong = client.post('/api/auth/login', json={
            'email': 'alice@example.com',
            'password': 'wrongpassword',
        })
        assert next_wrong.status_code == 401

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
