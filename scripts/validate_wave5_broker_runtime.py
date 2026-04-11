from __future__ import annotations

import argparse
import contextlib
import json
import os
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

from dotenv import dotenv_values


REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_PATH = REPO_ROOT / 'backend'
SDK_PATH = REPO_ROOT / 'packages' / 'platform-sdk'
if str(BACKEND_PATH) not in sys.path:
    sys.path.insert(0, str(BACKEND_PATH))
if str(SDK_PATH) not in sys.path:
    sys.path.insert(0, str(SDK_PATH))

from platform_sdk.rabbitmq_runtime import (
    build_blocking_connection,
    resolve_rabbitmq_url,
)
from platform_sdk.redis_runtime import (
    build_redis_client,
    resolve_redis_url,
)


DEFAULT_ENV_FILE = BACKEND_PATH / '.env.microservices.local'
DEFAULT_SERVICES = (
    'gateway-bff',
    'identity-service',
    'learning-core-service',
    'catalog-content-service',
    'ai-execution-service',
    'tts-media-service',
    'asr-service',
    'notes-service',
    'admin-ops-service',
)


@dataclass(frozen=True)
class BrokerRuntimeResult:
    broker_kind: str
    service_name: str
    resolved_url: str
    ready: bool
    error: str = ''


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description='Validate Wave 5 Redis/RabbitMQ runtime configuration and connectivity.',
    )
    parser.add_argument(
        '--env-file',
        default=str(DEFAULT_ENV_FILE),
        help='Env file that contains Redis/RabbitMQ settings.',
    )
    parser.add_argument(
        '--service',
        action='append',
        dest='services',
        help='Service name to validate. Repeat for multiple services. Defaults to the split-service broker baseline.',
    )
    parser.add_argument(
        '--format',
        choices=('text', 'json'),
        default='text',
        help='Output format.',
    )
    return parser.parse_args()


def load_env_values(env_file: Path) -> dict[str, str]:
    env_values: dict[str, str] = {}
    if BACKEND_PATH.joinpath('.env').exists():
        env_values.update(dotenv_values(BACKEND_PATH / '.env'))
    env_values.update(dotenv_values(env_file))
    return {
        str(key): str(value)
        for key, value in env_values.items()
        if key and value is not None
    }


@contextlib.contextmanager
def patched_environ(values: dict[str, str]):
    original = os.environ.copy()
    try:
        os.environ.update(values)
        yield
    finally:
        os.environ.clear()
        os.environ.update(original)


def resolve_service_names(raw_services: list[str] | None) -> list[str]:
    if raw_services:
        return raw_services
    return list(DEFAULT_SERVICES)


def _service_env_prefix(service_name: str) -> str:
    return re.sub(r'[^A-Za-z0-9]+', '_', service_name).strip('_').upper()


def _is_broker_explicitly_configured(
    env_values: dict[str, str],
    *,
    broker_prefix: str,
    service_name: str,
) -> bool:
    service_prefix = _service_env_prefix(service_name)
    candidate_names = [
        f'{broker_prefix}_URL',
        f'{broker_prefix}_HOST',
    ]
    if service_prefix:
        candidate_names[:0] = [
            f'{service_prefix}_{broker_prefix}_URL',
            f'{service_prefix}_{broker_prefix}_HOST',
        ]
    return any((env_values.get(name) or '').strip() for name in candidate_names)


def validate_redis_runtime(service_names: list[str], env_values: dict[str, str]) -> list[BrokerRuntimeResult]:
    results: list[BrokerRuntimeResult] = []
    with patched_environ(env_values):
        for service_name in service_names:
            if not _is_broker_explicitly_configured(
                env_values,
                broker_prefix='REDIS',
                service_name=service_name,
            ):
                results.append(BrokerRuntimeResult('redis', service_name, '', False, 'redis url is not configured'))
                continue

            resolved_url = resolve_redis_url(service_name=service_name)
            if not resolved_url:
                results.append(BrokerRuntimeResult('redis', service_name, '', False, 'redis url is not configured'))
                continue

            try:
                client = build_redis_client(service_name=service_name)
                ready = bool(client.ping())
            except Exception as exc:
                results.append(BrokerRuntimeResult('redis', service_name, resolved_url, False, str(exc)))
            else:
                results.append(BrokerRuntimeResult('redis', service_name, resolved_url, ready, '' if ready else 'redis ping failed'))
    return results


def validate_rabbitmq_runtime(service_names: list[str], env_values: dict[str, str]) -> list[BrokerRuntimeResult]:
    results: list[BrokerRuntimeResult] = []
    with patched_environ(env_values):
        for service_name in service_names:
            if not _is_broker_explicitly_configured(
                env_values,
                broker_prefix='RABBITMQ',
                service_name=service_name,
            ):
                results.append(BrokerRuntimeResult('rabbitmq', service_name, '', False, 'rabbitmq url is not configured'))
                continue

            resolved_url = resolve_rabbitmq_url(service_name=service_name)
            if not resolved_url:
                results.append(BrokerRuntimeResult('rabbitmq', service_name, '', False, 'rabbitmq url is not configured'))
                continue

            try:
                connection = build_blocking_connection(service_name=service_name)
            except Exception as exc:
                results.append(BrokerRuntimeResult('rabbitmq', service_name, resolved_url, False, str(exc)))
                continue

            try:
                connection.close()
                results.append(BrokerRuntimeResult('rabbitmq', service_name, resolved_url, True))
            except Exception as exc:
                results.append(BrokerRuntimeResult('rabbitmq', service_name, resolved_url, False, str(exc)))
    return results


def print_text_report(results: list[BrokerRuntimeResult]) -> None:
    for result in results:
        status = 'OK' if result.ready else 'FAIL'
        suffix = f' error={result.error}' if result.error else ''
        print(f'[{status}] {result.broker_kind} {result.service_name} -> {result.resolved_url or "<unset>"}{suffix}')


def main() -> int:
    args = parse_args()
    env_file = Path(args.env_file).resolve()
    if not env_file.exists():
        raise FileNotFoundError(f'Env file not found: {env_file}')

    service_names = resolve_service_names(args.services)
    env_values = load_env_values(env_file)
    results = [
        *validate_redis_runtime(service_names, env_values),
        *validate_rabbitmq_runtime(service_names, env_values),
    ]

    if args.format == 'json':
        print(json.dumps([asdict(result) for result in results], ensure_ascii=False, indent=2))
    else:
        print_text_report(results)

    return 1 if any(not result.ready for result in results) else 0


if __name__ == '__main__':
    raise SystemExit(main())
