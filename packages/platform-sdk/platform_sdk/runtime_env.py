from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv


REPO_ROOT = Path(__file__).resolve().parents[3]
BACKEND_ENV_FILE = REPO_ROOT / 'backend' / '.env'
DEFAULT_MICROSERVICES_ENV_FILE = REPO_ROOT / 'backend' / '.env.microservices.local'


def _service_env_prefix(service_name: str | None) -> str:
    if not service_name:
        return ''
    return ''.join(char if char.isalnum() else '_' for char in service_name).strip('_').upper()


def _has_explicit_database_env(service_name: str | None) -> bool:
    prefix = _service_env_prefix(service_name)
    names = [
        'SQLALCHEMY_DATABASE_URI',
        'DATABASE_URL',
        'SQLITE_DB_PATH',
        'POSTGRES_HOST',
        'POSTGRES_DB',
        'POSTGRES_DATABASE',
        'POSTGRES_USER',
        'POSTGRES_PASSWORD',
    ]
    if prefix:
        names = [*(f'{prefix}_{name}' for name in names), *names]
    return any((os.environ.get(name) or '').strip() for name in names)


def resolve_backend_env_file() -> Path:
    configured = (os.environ.get('BACKEND_ENV_FILE') or '').strip()
    if configured:
        return Path(configured).resolve()
    return BACKEND_ENV_FILE


def resolve_microservices_env_file() -> Path:
    configured = (os.environ.get('MICROSERVICES_ENV_FILE') or '').strip()
    if configured:
        return Path(configured).resolve()
    return DEFAULT_MICROSERVICES_ENV_FILE


def resolve_http_slot_env_file() -> Path | None:
    configured = (os.environ.get('IELTS_HTTP_SLOT_ENV_FILE') or '').strip()
    if not configured:
        return None
    return Path(configured).resolve()


def _should_load_microservices_env_file() -> bool:
    if os.environ.get('PYTEST_RUNNING') != '1':
        return True
    return bool((os.environ.get('MICROSERVICES_ENV_FILE') or '').strip())


def load_split_service_env(*, service_name: str | None = None) -> dict[str, str]:
    if service_name:
        os.environ['CURRENT_SERVICE_NAME'] = service_name

    loaded: dict[str, str] = {}
    backend_env = resolve_backend_env_file()
    if backend_env.exists():
        load_dotenv(backend_env, override=False)
        loaded['backend_env'] = str(backend_env)

    microservices_env = resolve_microservices_env_file()
    if (
        _should_load_microservices_env_file()
        and microservices_env.exists()
        and not _has_explicit_database_env(service_name)
    ):
        load_dotenv(microservices_env, override=True)
        loaded['microservices_env'] = str(microservices_env)

    slot_env = resolve_http_slot_env_file()
    if slot_env and slot_env.exists():
        load_dotenv(slot_env, override=True)
        loaded['http_slot_env'] = str(slot_env)

    return loaded
