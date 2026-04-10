from __future__ import annotations

import platform_sdk.redis_runtime as redis_runtime


def _clear_redis_env(monkeypatch):
    for name in (
        'CURRENT_SERVICE_NAME',
        'REDIS_URL',
        'REDIS_HOST',
        'REDIS_PORT',
        'REDIS_DB',
        'REDIS_PASSWORD',
        'REDIS_SSL',
        'REDIS_KEY_PREFIX',
        'GATEWAY_BFF_REDIS_URL',
        'GATEWAY_BFF_REDIS_HOST',
        'GATEWAY_BFF_REDIS_PORT',
        'GATEWAY_BFF_REDIS_DB',
        'GATEWAY_BFF_REDIS_PASSWORD',
        'GATEWAY_BFF_REDIS_SSL',
        'GATEWAY_BFF_REDIS_KEY_PREFIX',
    ):
        monkeypatch.delenv(name, raising=False)


def test_resolve_redis_url_prefers_service_specific_url(monkeypatch):
    _clear_redis_env(monkeypatch)
    monkeypatch.setenv('CURRENT_SERVICE_NAME', 'gateway-bff')
    monkeypatch.setenv('REDIS_URL', 'redis://127.0.0.1:6379/0')
    monkeypatch.setenv('GATEWAY_BFF_REDIS_URL', 'redis://127.0.0.1:56379/7')

    assert redis_runtime.resolve_redis_url() == 'redis://127.0.0.1:56379/7'


def test_resolve_redis_url_builds_service_specific_url_from_parts(monkeypatch):
    _clear_redis_env(monkeypatch)
    monkeypatch.setenv('CURRENT_SERVICE_NAME', 'gateway-bff')
    monkeypatch.setenv('REDIS_HOST', '127.0.0.1')
    monkeypatch.setenv('REDIS_PORT', '56379')
    monkeypatch.setenv('GATEWAY_BFF_REDIS_DB', '3')
    monkeypatch.setenv('GATEWAY_BFF_REDIS_PASSWORD', 'p@ss word')
    monkeypatch.setenv('GATEWAY_BFF_REDIS_SSL', 'true')

    assert redis_runtime.resolve_redis_url() == 'rediss://:p%40ss%20word@127.0.0.1:56379/3'


def test_resolve_redis_key_prefix_uses_explicit_value(monkeypatch):
    _clear_redis_env(monkeypatch)
    monkeypatch.setenv('CURRENT_SERVICE_NAME', 'gateway-bff')
    monkeypatch.setenv('REDIS_KEY_PREFIX', 'ielts-vocab-local:')

    assert redis_runtime.resolve_redis_key_prefix() == 'ielts-vocab-local'


def test_resolve_redis_key_prefix_defaults_to_service_name(monkeypatch):
    _clear_redis_env(monkeypatch)
    monkeypatch.setenv('CURRENT_SERVICE_NAME', 'gateway-bff')

    assert redis_runtime.resolve_redis_key_prefix() == 'gateway-bff'


def test_make_redis_readiness_check_uses_client_ping(monkeypatch):
    captured: dict[str, str] = {}

    class FakeClient:
        def ping(self):
            return True

    class FakeRedis:
        @staticmethod
        def from_url(url, **kwargs):
            captured['url'] = url
            return FakeClient()

    monkeypatch.setattr(redis_runtime, 'Redis', FakeRedis)

    check = redis_runtime.make_redis_readiness_check(redis_url='redis://127.0.0.1:56379/0')

    assert check() is True
    assert captured['url'] == 'redis://127.0.0.1:56379/0'
