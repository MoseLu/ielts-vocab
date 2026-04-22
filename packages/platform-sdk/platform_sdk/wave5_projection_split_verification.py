from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote_plus

import sqlalchemy as sa
from dotenv import load_dotenv

from platform_sdk.admin_study_session_projection_application import (
    STUDY_SESSION_ANALYTICS_PROJECTION,
)
from platform_sdk.admin_user_projection_application import USER_DIRECTORY_PROJECTION
from platform_sdk.admin_wrong_word_projection_application import (
    WRONG_WORD_DIRECTORY_PROJECTION,
)
from platform_sdk.ai_daily_summary_projection_application import (
    AI_DAILY_SUMMARY_CONTEXT_PROJECTION,
)
from platform_sdk.ai_wrong_word_projection_application import (
    AI_WRONG_WORD_CONTEXT_PROJECTION,
)
from platform_sdk.notes_study_session_projection_application import (
    NOTES_STUDY_SESSION_CONTEXT_PROJECTION,
)
from platform_sdk.notes_wrong_word_projection_application import (
    NOTES_WRONG_WORD_CONTEXT_PROJECTION,
)
from platform_sdk.runtime_env import load_split_service_env
from services.storage_boundary_guard import validate_split_service_storage_boundary


BOOTSTRAP_TOPIC = '__bootstrap__'
REPO_ROOT = Path(__file__).resolve().parents[3]
BACKEND_PATH = REPO_ROOT / 'backend'
REQUIRED_SERVICES = (
    'admin-ops-service',
    'notes-service',
    'ai-execution-service',
)


@dataclass(frozen=True)
class TableCountSpec:
    service_name: str
    table_name: str


@dataclass(frozen=True)
class ProjectionStatusSpec:
    projection_name: str
    source: TableCountSpec
    projected: TableCountSpec
    cursor: TableCountSpec


GROUP_SPECS: dict[str, dict[str, ProjectionStatusSpec]] = {
    'admin': {
        'user_directory': ProjectionStatusSpec(
            projection_name=USER_DIRECTORY_PROJECTION,
            source=TableCountSpec('admin-ops-service', 'users'),
            projected=TableCountSpec('admin-ops-service', 'admin_projected_users'),
            cursor=TableCountSpec('admin-ops-service', 'admin_projection_cursors'),
        ),
        'study_sessions': ProjectionStatusSpec(
            projection_name=STUDY_SESSION_ANALYTICS_PROJECTION,
            source=TableCountSpec('admin-ops-service', 'user_study_sessions'),
            projected=TableCountSpec('admin-ops-service', 'admin_projected_study_sessions'),
            cursor=TableCountSpec('admin-ops-service', 'admin_projection_cursors'),
        ),
        'wrong_words': ProjectionStatusSpec(
            projection_name=WRONG_WORD_DIRECTORY_PROJECTION,
            source=TableCountSpec('admin-ops-service', 'user_wrong_words'),
            projected=TableCountSpec('admin-ops-service', 'admin_projected_wrong_words'),
            cursor=TableCountSpec('admin-ops-service', 'admin_projection_cursors'),
        ),
    },
    'notes': {
        'study_sessions': ProjectionStatusSpec(
            projection_name=NOTES_STUDY_SESSION_CONTEXT_PROJECTION,
            source=TableCountSpec('notes-service', 'user_study_sessions'),
            projected=TableCountSpec('notes-service', 'notes_projected_study_sessions'),
            cursor=TableCountSpec('notes-service', 'notes_projection_cursors'),
        ),
        'wrong_words': ProjectionStatusSpec(
            projection_name=NOTES_WRONG_WORD_CONTEXT_PROJECTION,
            source=TableCountSpec('notes-service', 'user_wrong_words'),
            projected=TableCountSpec('notes-service', 'notes_projected_wrong_words'),
            cursor=TableCountSpec('notes-service', 'notes_projection_cursors'),
        ),
    },
    'ai': {
        'wrong_words': ProjectionStatusSpec(
            projection_name=AI_WRONG_WORD_CONTEXT_PROJECTION,
            source=TableCountSpec('ai-execution-service', 'user_wrong_words'),
            projected=TableCountSpec('ai-execution-service', 'ai_projected_wrong_words'),
            cursor=TableCountSpec('ai-execution-service', 'ai_projection_cursors'),
        ),
        'daily_summaries': ProjectionStatusSpec(
            projection_name=AI_DAILY_SUMMARY_CONTEXT_PROJECTION,
            source=TableCountSpec('ai-execution-service', 'user_daily_summaries'),
            projected=TableCountSpec('ai-execution-service', 'ai_projected_daily_summaries'),
            cursor=TableCountSpec('ai-execution-service', 'ai_projection_cursors'),
        ),
    },
}


def _service_env_prefix(service_name: str) -> str:
    return ''.join(char if char.isalnum() else '_' for char in service_name).strip('_').upper()


def _getenv(name: str, *, service_name: str, default: str = '') -> str:
    service_prefix = _service_env_prefix(service_name)
    if service_prefix:
        service_value = (os.environ.get(f'{service_prefix}_{name}') or '').strip()
        if service_value:
            return service_value
    return (os.environ.get(name) or default).strip()


def _normalize_database_uri(uri: str) -> str:
    if uri.startswith('postgres://'):
        return 'postgresql://' + uri[len('postgres://'):]
    return uri


def _resolve_sqlite_db_path(*, service_name: str) -> str:
    configured = _getenv('SQLITE_DB_PATH', service_name=service_name)
    if configured:
        return os.path.abspath(configured)
    return str((BACKEND_PATH / 'database.sqlite').resolve())


def _build_postgres_database_uri(*, service_name: str) -> str:
    host = _getenv('POSTGRES_HOST', service_name=service_name)
    database = _getenv('POSTGRES_DB', service_name=service_name) or _getenv(
        'POSTGRES_DATABASE',
        service_name=service_name,
    )
    user = _getenv('POSTGRES_USER', service_name=service_name)
    password = _getenv('POSTGRES_PASSWORD', service_name=service_name)
    if not (host and database and user and password):
        return ''

    port = _getenv('POSTGRES_PORT', service_name=service_name, default='5432') or '5432'
    sslmode = _getenv('POSTGRES_SSLMODE', service_name=service_name)
    auth = f'{quote_plus(user)}:{quote_plus(password)}'
    query = f'?sslmode={quote_plus(sslmode)}' if sslmode else ''
    return f'postgresql://{auth}@{host}:{port}/{database}{query}'


def _prepare_env(*, service_name: str, env_file: Path | None) -> None:
    env_path: Path | None = None
    if env_file is not None:
        env_path = env_file.resolve()
        if not env_path.exists():
            raise FileNotFoundError(f'Microservices env file not found: {env_path}')
        os.environ['MICROSERVICES_ENV_FILE'] = str(env_path)

    load_split_service_env(service_name=service_name)
    if env_path is not None:
        load_dotenv(env_path, override=True)
    os.environ['CURRENT_SERVICE_NAME'] = service_name


def resolve_split_service_database_uri(*, service_name: str, env_file: Path | None = None) -> str:
    _prepare_env(service_name=service_name, env_file=env_file)
    explicit_uri = _getenv('SQLALCHEMY_DATABASE_URI', service_name=service_name) or _getenv(
        'DATABASE_URL',
        service_name=service_name,
    )
    if explicit_uri:
        database_uri = _normalize_database_uri(explicit_uri)
    else:
        postgres_uri = _build_postgres_database_uri(service_name=service_name)
        if postgres_uri:
            database_uri = postgres_uri
        else:
            database_uri = 'sqlite:///' + _resolve_sqlite_db_path(service_name=service_name)

    validate_split_service_storage_boundary(
        service_name=service_name,
        database_uri=database_uri,
        base_dir=BACKEND_PATH,
    )
    return database_uri


def can_verify_split_runtime(*, env_file: Path | None = None) -> bool:
    try:
        for service_name in REQUIRED_SERVICES:
            resolve_split_service_database_uri(service_name=service_name, env_file=env_file)
    except Exception:
        return False
    return True


def _projection_status(
    *,
    projection_name: str,
    source_count: int,
    projected_count: int,
    ready: bool,
) -> dict[str, object]:
    counts_match = projected_count == source_count
    return {
        'projection_name': projection_name,
        'source_count': source_count,
        'projected_count': projected_count,
        'counts_match': counts_match,
        'ready': ready,
        'ok': bool(ready and counts_match),
    }


def _table_count(connection: sa.engine.Connection, table_name: str) -> int:
    return int(connection.execute(sa.text(f'SELECT COUNT(*) FROM {table_name}')).scalar_one())


def _projection_ready(
    connection: sa.engine.Connection,
    *,
    cursor_table: str,
    projection_name: str,
) -> bool:
    marker_name = f'{projection_name}.bootstrap'
    ready_count = connection.execute(
        sa.text(
            f'''
            SELECT COUNT(*)
            FROM {cursor_table}
            WHERE projection_name = :projection_name
              AND last_topic = :last_topic
              AND last_processed_at IS NOT NULL
            '''
        ),
        {
            'projection_name': marker_name,
            'last_topic': BOOTSTRAP_TOPIC,
        },
    ).scalar_one()
    return bool(int(ready_count or 0) > 0)


def collect_split_runtime_status(*, env_file: Path | None = None) -> dict[str, object]:
    database_uris = {
        service_name: resolve_split_service_database_uri(
            service_name=service_name,
            env_file=env_file,
        )
        for service_name in REQUIRED_SERVICES
    }
    engines = {
        service_name: sa.create_engine(uri)
        for service_name, uri in database_uris.items()
    }
    connections = {
        service_name: engine.connect()
        for service_name, engine in engines.items()
    }

    try:
        status: dict[str, object] = {
            'runtime': 'split',
            'bootstrap_ran': False,
            'bootstrap': None,
            'database_targets': {
                service_name: engine.url.render_as_string(hide_password=True)
                for service_name, engine in engines.items()
            },
        }
        for group_name, specs in GROUP_SPECS.items():
            group_status: dict[str, object] = {}
            for key, spec in specs.items():
                source_count = _table_count(
                    connections[spec.source.service_name],
                    spec.source.table_name,
                )
                projected_count = _table_count(
                    connections[spec.projected.service_name],
                    spec.projected.table_name,
                )
                ready = _projection_ready(
                    connections[spec.cursor.service_name],
                    cursor_table=spec.cursor.table_name,
                    projection_name=spec.projection_name,
                )
                group_status[key] = _projection_status(
                    projection_name=spec.projection_name,
                    source_count=source_count,
                    projected_count=projected_count,
                    ready=ready,
                )
            status[group_name] = group_status
        status['ok'] = all(
            item['ok']
            for group_name in ('admin', 'notes', 'ai')
            for item in status[group_name].values()
        )
        return status
    finally:
        for connection in connections.values():
            connection.close()
        for engine in engines.values():
            engine.dispose()
