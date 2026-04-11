from __future__ import annotations

import os
from pathlib import Path

from runtime_paths import ensure_shared_package_paths


ensure_shared_package_paths()

from platform_sdk.service_storage_boundary_plan import (
    ALLOW_SHARED_SPLIT_SERVICE_SQLITE_ENV,
    ALLOW_SHARED_SPLIT_SERVICE_SQLITE_SERVICES_ENV,
    shared_sqlite_fallback_locked_for_service,
)


def current_service_name() -> str:
    return (os.environ.get('CURRENT_SERVICE_NAME') or '').strip()


def is_write_owning_split_service(service_name: str | None) -> bool:
    return shared_sqlite_fallback_locked_for_service(service_name)


def resolve_sqlite_uri_path(database_uri: str | None) -> Path | None:
    if not database_uri or not database_uri.startswith('sqlite:///'):
        return None
    raw_path = database_uri[len('sqlite:///'):].split('?', 1)[0].strip()
    if not raw_path or raw_path == ':memory:':
        return None
    return Path(raw_path).resolve()


def resolve_shared_sqlite_fallback_path(base_dir: str | Path) -> Path:
    return (Path(base_dir).resolve() / 'database.sqlite').resolve()


def uses_shared_sqlite_fallback(
    *,
    service_name: str | None,
    database_uri: str | None,
    base_dir: str | Path,
) -> bool:
    if not is_write_owning_split_service(service_name):
        return False
    sqlite_path = resolve_sqlite_uri_path(database_uri)
    if sqlite_path is None:
        return False
    return sqlite_path == resolve_shared_sqlite_fallback_path(base_dir)


def _configured_shared_sqlite_override_services() -> set[str]:
    raw_value = os.environ.get(ALLOW_SHARED_SPLIT_SERVICE_SQLITE_SERVICES_ENV, '')
    return {
        item.strip()
        for item in raw_value.split(',')
        if item.strip()
    }


def shared_sqlite_override_enabled(service_name: str | None) -> bool:
    if os.environ.get(ALLOW_SHARED_SPLIT_SERVICE_SQLITE_ENV, 'false').strip().lower() == 'true':
        return True
    if not service_name:
        return False
    return service_name in _configured_shared_sqlite_override_services()


def validate_split_service_storage_boundary(
    *,
    service_name: str | None,
    database_uri: str | None,
    base_dir: str | Path,
) -> None:
    if shared_sqlite_override_enabled(service_name):
        return
    if not uses_shared_sqlite_fallback(
        service_name=service_name,
        database_uri=database_uri,
        base_dir=base_dir,
    ):
        return

    shared_path = resolve_shared_sqlite_fallback_path(base_dir)
    raise ValueError(
        f'{service_name} resolved to the shared SQLite fallback at {shared_path}. '
        'Write-owning split services must use service-owned PostgreSQL or an explicit '
        'service-local SQLite path. Set '
        f'{ALLOW_SHARED_SPLIT_SERVICE_SQLITE_SERVICES_ENV}={service_name} for a service-scoped '
        'rollback or repair drill, or use '
        f'{ALLOW_SHARED_SPLIT_SERVICE_SQLITE_ENV}=true only for an emergency global override.'
    )
