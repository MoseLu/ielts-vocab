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


def resolve_microservices_env_file() -> Path:
    configured = (os.environ.get('MICROSERVICES_ENV_FILE') or '').strip()
    if configured:
        return Path(configured).resolve()
    return DEFAULT_MICROSERVICES_ENV_FILE


def _should_load_microservices_env_file() -> bool:
    if os.environ.get('PYTEST_RUNNING') != '1':
        return True
    return bool((os.environ.get('MICROSERVICES_ENV_FILE') or '').strip())


def load_split_service_env(*, service_name: str | None = None) -> dict[str, str]:
    if service_name:
        os.environ['CURRENT_SERVICE_NAME'] = service_name

    loaded: dict[str, str] = {}
    if BACKEND_ENV_FILE.exists():
        load_dotenv(BACKEND_ENV_FILE, override=False)
        loaded['backend_env'] = str(BACKEND_ENV_FILE)

    microservices_env = resolve_microservices_env_file()
    if (
        _should_load_microservices_env_file()
        and microservices_env.exists()
        and not _has_explicit_database_env(service_name)
    ):
        load_dotenv(microservices_env, override=True)
        loaded['microservices_env'] = str(microservices_env)

    return loaded
