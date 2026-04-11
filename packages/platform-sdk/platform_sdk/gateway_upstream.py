from __future__ import annotations

import time
from dataclasses import dataclass

import httpx


_SAFE_RETRY_METHODS = frozenset({'GET', 'HEAD', 'OPTIONS'})
_RETRYABLE_STATUS_CODES = frozenset({502, 503, 504})
_CIRCUIT_BREAKER_STATES: dict[str, '_CircuitBreakerState'] = {}


@dataclass(frozen=True)
class GatewayUpstreamPolicy:
    service_name: str
    connect_timeout_seconds: float
    read_timeout_seconds: float
    retry_attempts: int
    circuit_breaker_failures: int
    circuit_breaker_reset_seconds: float
    write_timeout_seconds: float = 10.0
    pool_timeout_seconds: float = 5.0

    def build_timeout(self) -> httpx.Timeout:
        return httpx.Timeout(
            connect=self.connect_timeout_seconds,
            read=self.read_timeout_seconds,
            write=self.write_timeout_seconds,
            pool=self.pool_timeout_seconds,
        )


@dataclass
class _CircuitBreakerState:
    failures: int = 0
    opened_until_monotonic: float = 0.0


class GatewayCircuitOpenError(RuntimeError):
    def __init__(self, service_name: str, retry_after_seconds: float):
        super().__init__(f'{service_name} circuit is open')
        self.service_name = service_name
        self.retry_after_seconds = retry_after_seconds


def reset_gateway_upstream_state() -> None:
    _CIRCUIT_BREAKER_STATES.clear()


def resolve_gateway_upstream_policy(
    *,
    service_name: str,
    path: str,
) -> GatewayUpstreamPolicy:
    normalized_path = path.lower()

    if service_name == 'ai-execution-service':
        if normalized_path.endswith('/stream'):
            return GatewayUpstreamPolicy(
                service_name=service_name,
                connect_timeout_seconds=5.0,
                read_timeout_seconds=90.0,
                retry_attempts=0,
                circuit_breaker_failures=3,
                circuit_breaker_reset_seconds=30.0,
            )
        return GatewayUpstreamPolicy(
            service_name=service_name,
            connect_timeout_seconds=5.0,
            read_timeout_seconds=30.0,
            retry_attempts=1,
            circuit_breaker_failures=3,
            circuit_breaker_reset_seconds=30.0,
        )

    if service_name == 'tts-media-service':
        read_timeout = 30.0 if normalized_path.startswith('/v1/tts/generate') else 5.0
        if normalized_path.startswith('/v1/media/example-audio'):
            read_timeout = 30.0
        return GatewayUpstreamPolicy(
            service_name=service_name,
            connect_timeout_seconds=5.0,
            read_timeout_seconds=read_timeout,
            retry_attempts=1,
            circuit_breaker_failures=3,
            circuit_breaker_reset_seconds=30.0,
        )

    if service_name == 'asr-service':
        return GatewayUpstreamPolicy(
            service_name=service_name,
            connect_timeout_seconds=5.0,
            read_timeout_seconds=15.0,
            retry_attempts=1,
            circuit_breaker_failures=3,
            circuit_breaker_reset_seconds=30.0,
        )

    if service_name == 'catalog-content-service':
        read_timeout_seconds = 5.0
        if normalized_path == '/api/books/search':
            read_timeout_seconds = 15.0
        return GatewayUpstreamPolicy(
            service_name=service_name,
            connect_timeout_seconds=5.0,
            read_timeout_seconds=read_timeout_seconds,
            retry_attempts=1,
            circuit_breaker_failures=3,
            circuit_breaker_reset_seconds=30.0,
        )

    return GatewayUpstreamPolicy(
        service_name=service_name,
        connect_timeout_seconds=5.0,
        read_timeout_seconds=5.0,
        retry_attempts=1,
        circuit_breaker_failures=3,
        circuit_breaker_reset_seconds=30.0,
    )


def before_gateway_upstream_attempt(policy: GatewayUpstreamPolicy) -> None:
    state = _CIRCUIT_BREAKER_STATES.setdefault(policy.service_name, _CircuitBreakerState())
    now = time.monotonic()
    if state.opened_until_monotonic > now:
        raise GatewayCircuitOpenError(
            policy.service_name,
            retry_after_seconds=max(0.0, state.opened_until_monotonic - now),
        )
    if state.opened_until_monotonic:
        state.failures = 0
        state.opened_until_monotonic = 0.0


def record_gateway_upstream_success(policy: GatewayUpstreamPolicy) -> None:
    state = _CIRCUIT_BREAKER_STATES.setdefault(policy.service_name, _CircuitBreakerState())
    state.failures = 0
    state.opened_until_monotonic = 0.0


def record_gateway_upstream_failure(policy: GatewayUpstreamPolicy) -> None:
    state = _CIRCUIT_BREAKER_STATES.setdefault(policy.service_name, _CircuitBreakerState())
    state.failures += 1
    if state.failures < policy.circuit_breaker_failures:
        return
    state.failures = 0
    state.opened_until_monotonic = time.monotonic() + policy.circuit_breaker_reset_seconds


def should_retry_gateway_upstream(
    *,
    policy: GatewayUpstreamPolicy,
    method: str,
    attempt_index: int,
    request_headers: dict[str, str] | None = None,
    status_code: int | None = None,
    error: Exception | None = None,
    streaming_request: bool = False,
) -> bool:
    if streaming_request or attempt_index >= policy.retry_attempts:
        return False

    normalized_method = (method or '').upper()
    normalized_headers = {
        str(name).lower(): str(value)
        for name, value in (request_headers or {}).items()
        if value is not None
    }
    is_retryable_method = normalized_method in _SAFE_RETRY_METHODS or bool(
        normalized_headers.get('idempotency-key')
    )
    if not is_retryable_method:
        return False

    if status_code is not None:
        return status_code in _RETRYABLE_STATUS_CODES

    if error is None:
        return False

    return isinstance(
        error,
        (
            httpx.ConnectError,
            httpx.ConnectTimeout,
            httpx.ReadTimeout,
            httpx.RemoteProtocolError,
            httpx.WriteTimeout,
            httpx.PoolTimeout,
        ),
    )
