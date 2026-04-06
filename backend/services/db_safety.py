from __future__ import annotations

import os
from pathlib import Path

from flask import current_app, has_app_context


DESTRUCTIVE_DB_UNLOCK_ENV_VAR = 'ALLOW_DESTRUCTIVE_DB_OPERATIONS'
_TRUTHY_VALUES = {'1', 'true', 'yes', 'on'}


def resolve_sqlite_database_path(uri: str | None) -> Path | None:
    if not uri:
        return None

    if not uri.startswith('sqlite:///'):
        return None

    raw_path = uri[len('sqlite:///'):].split('?', 1)[0]
    if raw_path == ':memory:':
        return None
    if raw_path.startswith('/') and len(raw_path) >= 3 and raw_path[2] == ':':
        raw_path = raw_path[1:]
    if not raw_path:
        return None
    return Path(raw_path).resolve()


def primary_sqlite_database_path() -> Path:
    return (Path(__file__).resolve().parents[1] / 'database.sqlite').resolve()


def destructive_db_operations_unlocked() -> bool:
    env_value = os.environ.get(DESTRUCTIVE_DB_UNLOCK_ENV_VAR, '').strip().lower()
    if env_value in _TRUTHY_VALUES:
        return True

    if has_app_context():
        return bool(current_app.config.get('ALLOW_DESTRUCTIVE_DB_OPERATIONS', False))

    return False


def ensure_sqlite_drop_all_allowed(uri: str | None, *, testing: bool = False) -> None:
    db_path = resolve_sqlite_database_path(uri)
    if db_path is None or testing:
        return

    if destructive_db_operations_unlocked():
        return

    raise RuntimeError(
        f'Refusing to run db.drop_all() against file-backed SQLite database {db_path}. '
        f'Set {DESTRUCTIVE_DB_UNLOCK_ENV_VAR}=true to allow this intentionally.'
    )


def ensure_sqlite_restore_allowed(target_db: Path | str) -> None:
    resolved_target = Path(target_db).resolve()
    if resolved_target != primary_sqlite_database_path():
        return

    if destructive_db_operations_unlocked():
        return

    raise RuntimeError(
        f'Refusing to overwrite the primary SQLite database {resolved_target}. '
        f'Set {DESTRUCTIVE_DB_UNLOCK_ENV_VAR}=true to allow this intentionally.'
    )
