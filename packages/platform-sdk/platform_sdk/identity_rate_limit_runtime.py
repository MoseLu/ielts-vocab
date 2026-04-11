from __future__ import annotations

from platform_sdk.redis_runtime import build_redis_client, resolve_redis_key_prefix


_RATE_LIMIT_SERVICE_NAME = 'identity-service'
_RATE_LIMIT_NAMESPACE = 'rate-limit'


def _window_seconds(window_minutes: int) -> int:
    return max(int(window_minutes) * 60, 1)


def _redis_rate_limit_key(ip_address: str, purpose: str) -> str:
    prefix = resolve_redis_key_prefix(service_name=_RATE_LIMIT_SERVICE_NAME)
    normalized_ip = (ip_address or '0.0.0.0').strip() or '0.0.0.0'
    normalized_purpose = (purpose or 'login').strip() or 'login'
    return f'{prefix}:{_RATE_LIMIT_NAMESPACE}:{normalized_purpose}:{normalized_ip}'


def check_rate_limit_with_redis(
    *,
    ip_address: str,
    purpose: str,
    max_attempts: int,
    window_minutes: int,
) -> tuple[bool, int] | None:
    try:
        client = build_redis_client(service_name=_RATE_LIMIT_SERVICE_NAME)
    except Exception:
        return None

    key = _redis_rate_limit_key(ip_address, purpose)
    window_seconds = _window_seconds(window_minutes)

    try:
        current_count = int(client.incr(key))
        if current_count == 1:
            client.expire(key, window_seconds)

        if current_count > max_attempts:
            ttl = int(client.ttl(key))
            if ttl <= 0:
                client.expire(key, window_seconds)
                ttl = window_seconds
            return False, ttl

        ttl = int(client.ttl(key))
        if ttl <= 0:
            client.expire(key, window_seconds)
        return True, 0
    except Exception:
        return None


def reset_rate_limit_with_redis(*, ip_address: str, purpose: str) -> bool:
    try:
        client = build_redis_client(service_name=_RATE_LIMIT_SERVICE_NAME)
    except Exception:
        return False

    key = _redis_rate_limit_key(ip_address, purpose)
    try:
        client.delete(key)
        return True
    except Exception:
        return False
