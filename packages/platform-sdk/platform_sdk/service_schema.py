from __future__ import annotations

import sys
from pathlib import Path

from platform_sdk.service_table_plan import get_service_bootstrap_table_names


REPO_ROOT = Path(__file__).resolve().parents[3]
BACKEND_PATH = REPO_ROOT / 'backend'
if str(BACKEND_PATH) not in sys.path:
    sys.path.insert(0, str(BACKEND_PATH))

from models import db


def resolve_service_tables(service_name: str, metadata=None) -> list:
    metadata = metadata or db.metadata
    selected_names = get_service_bootstrap_table_names(service_name)
    missing = selected_names - set(metadata.tables)
    if missing:
        raise RuntimeError(
            f'{service_name} references tables missing from SQLAlchemy metadata: {sorted(missing)}'
        )
    return [
        table
        for table in metadata.sorted_tables
        if table.name in selected_names
    ]


def bootstrap_service_schema(service_name: str, bind=None, metadata=None) -> list[str]:
    metadata = metadata or db.metadata
    bind = bind or db.engine
    tables = resolve_service_tables(service_name, metadata=metadata)
    if tables:
        metadata.create_all(bind=bind, tables=tables, checkfirst=True)
    return [table.name for table in tables]
