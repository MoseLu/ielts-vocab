from __future__ import annotations

import os
import re
from urllib.parse import quote

try:
    from redis import Redis
except ImportError:  # pragma: no cover - exercised through dependency install in runtime.
    Redis = None


DEFAULT_REDIS_HOST = '127.0.0.1'
DEFAULT_REDIS_PORT = '56379'
DEFAULT_REDIS_DB = '0'


def _service_env_prefix(service_name: str | None = None) -> str:
    raw_name = (service_name or os.environ.get('CURRENT_SERVICE_NAME') or '').strip()
    if not raw_name:
        return ''
    return re.sub(r'[^A-Za-z0-9]+', '_', raw_name).strip('_').upper()


def _getenv(name: str, default: str = '', *, service_name: str | None = None) -> str:
    service_prefix = _service_env_prefix(service_name)
    if service_prefix:
        service_value = (os.environ.get(f'{service_prefix}_{name}') or '').strip()
        if service_value:
            return service_value
    return (os.environ.get(name) or default).strip()


def resolve_redis_url(*, service_name: str | None = None) -> str:
    explicit_url = _getenv('REDIS_URL', service_name=service_name)
    if explicit_url:
        return explicit_url

    host = _getenv('REDIS_HOST', DEFAULT_REDIS_HOST, service_name=service_name)
    if not host:
        return ''

    port = _getenv('REDIS_PORT', DEFAULT_REDIS_PORT, service_name=service_name) or DEFAULT_REDIS_PORT
    database = _getenv('REDIS_DB', DEFAULT_REDIS_DB, service_name=service_name) or DEFAULT_REDIS_DB
    password = _getenv('REDIS_PASSWORD', service_name=service_name)
    ssl_enabled = _getenv('REDIS_SSL', 'false', service_name=service_name).lower() in {
        '1',
        'true',
        'yes',
        'on',
    }
    scheme = 'rediss' if ssl_enabled else 'redis'
    auth = f':{quote(password, safe="")}@' if password else ''
    return f'{scheme}://{auth}{host}:{port}/{database}'


def resolve_redis_key_prefix(*, service_name: str | None = None) -> str:
    configured = _getenv('REDIS_KEY_PREFIX', service_name=service_name)
    if configured:
        return configured.rstrip(':')

    prefix = _service_env_prefix(service_name)
    if not prefix:
        return 'ielts-vocab'
    return prefix.lower().replace('_', '-')


def redis_is_configured(*, service_name: str | None = None) -> bool:
    return bool(resolve_redis_url(service_name=service_name))


def build_redis_client(*, service_name: str | None = None, redis_url: str | None = None):
    if Redis is None:
        raise RuntimeError('redis package is not installed')

    resolved_url = (redis_url or resolve_redis_url(service_name=service_name)).strip()
    if not resolved_url:
        raise ValueError('Redis URL is not configured')

    return Redis.from_url(
        resolved_url,
        socket_connect_timeout=1.5,
        socket_timeout=1.5,
    )


def make_redis_readiness_check(*, service_name: str | None = None, redis_url: str | None = None):
    def check() -> bool:
        try:
            client = build_redis_client(service_name=service_name, redis_url=redis_url)
        except Exception:
            return False

        try:
            return bool(client.ping())
        except Exception:
            return False

    return check
