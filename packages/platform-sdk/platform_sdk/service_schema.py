from __future__ import annotations

import sys
from pathlib import Path

from platform_sdk.service_table_plan import (
    get_service_bootstrap_table_names,
    get_service_owned_table_names,
    iter_stateful_service_names,
)
from platform_sdk.service_model_registry import resolve_service_db


REPO_ROOT = Path(__file__).resolve().parents[3]
BACKEND_PATH = REPO_ROOT / 'backend'
if str(BACKEND_PATH) not in sys.path:
    sys.path.insert(0, str(BACKEND_PATH))


def resolve_named_tables(table_names, *, metadata, context_name: str) -> list:
    selected_names = set(table_names)
    missing = selected_names - set(metadata.tables)
    if missing:
        raise RuntimeError(
            f'{context_name} references tables missing from SQLAlchemy metadata: {sorted(missing)}'
        )
    return [
        table
        for table in metadata.sorted_tables
        if table.name in selected_names
    ]


def resolve_service_tables(service_name: str, metadata=None) -> list:
    if metadata is None:
        metadata = resolve_service_db(service_name).metadata
    return resolve_named_tables(
        get_service_bootstrap_table_names(service_name),
        metadata=metadata,
        context_name=service_name,
    )


def bootstrap_service_schema(service_name: str, bind=None, metadata=None) -> list[str]:
    service_db = resolve_service_db(service_name)
    metadata = metadata or service_db.metadata
    bind = bind or service_db.engine
    tables = resolve_service_tables(service_name, metadata=metadata)
    if tables:
        metadata.create_all(bind=bind, tables=tables, checkfirst=True)
    return [table.name for table in tables]


def resolve_monolith_tables(metadata=None) -> list:
    if metadata is None:
        metadata = resolve_service_db('identity-service').metadata
    selected_names = set()
    for service_name in iter_stateful_service_names(include_shadow_only=False):
        selected_names.update(get_service_owned_table_names(service_name))
    return resolve_named_tables(
        selected_names,
        metadata=metadata,
        context_name='backend-monolith',
    )


def bootstrap_monolith_schema(bind=None, metadata=None) -> list[str]:
    service_db = resolve_service_db('identity-service')
    metadata = metadata or service_db.metadata
    bind = bind or service_db.engine
    tables = resolve_monolith_tables(metadata=metadata)
    if tables:
        metadata.create_all(bind=bind, tables=tables, checkfirst=True)
    return [table.name for table in tables]
