from __future__ import annotations

import argparse
import sys
from pathlib import Path

from dotenv import dotenv_values
from sqlalchemy import BigInteger, Integer, create_engine, inspect, select, text


REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_PATH = REPO_ROOT / 'backend'
SDK_PATH = REPO_ROOT / 'packages' / 'platform-sdk'
if str(BACKEND_PATH) not in sys.path:
    sys.path.insert(0, str(BACKEND_PATH))
if str(SDK_PATH) not in sys.path:
    sys.path.insert(0, str(SDK_PATH))

from models import db
from platform_sdk.service_schema import resolve_service_tables
from platform_sdk.service_table_plan import (
    get_service_bootstrap_table_names,
    get_service_owned_table_names,
    iter_stateful_service_names,
)


DEFAULT_SOURCE_SQLITE = BACKEND_PATH / 'database.sqlite'
DEFAULT_ENV_FILE = BACKEND_PATH / '.env.microservices.local'


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description='Bootstrap and migrate SQLite data into service-specific PostgreSQL databases.',
    )
    parser.add_argument(
        '--service',
        action='append',
        dest='services',
        help='Service name to migrate. Repeat for multiple services. Defaults to all stateful services.',
    )
    parser.add_argument(
        '--scope',
        choices=('bootstrap', 'owned'),
        default='bootstrap',
        help='Copy service-owned tables only, or the full bootstrap set including transitional shadow tables.',
    )
    parser.add_argument(
        '--source-sqlite',
        default=str(DEFAULT_SOURCE_SQLITE),
        help='Path to the monolith SQLite database.',
    )
    parser.add_argument(
        '--env-file',
        default=str(DEFAULT_ENV_FILE),
        help='Env file that contains per-service PostgreSQL URLs.',
    )
    parser.add_argument(
        '--replace',
        action='store_true',
        help='Delete existing rows from the selected target tables before copying.',
    )
    parser.add_argument(
        '--bootstrap-only',
        action='store_true',
        help='Create the service schema without copying data.',
    )
    parser.add_argument(
        '--plan',
        action='store_true',
        help='Print the selected service/table plan and exit.',
    )
    return parser.parse_args()


def service_env_prefix(service_name: str) -> str:
    return service_name.replace('-', '_').upper()


def load_target_database_url(service_name: str, env_file: Path) -> str:
    env_values = {}
    if BACKEND_PATH.joinpath('.env').exists():
        env_values.update(dotenv_values(BACKEND_PATH / '.env'))
    env_values.update(dotenv_values(env_file))

    prefix = service_env_prefix(service_name)
    for key in (f'{prefix}_SQLALCHEMY_DATABASE_URI', f'{prefix}_DATABASE_URL'):
        value = env_values.get(key)
        if value:
            return value
    raise RuntimeError(f'Missing target database URL for {service_name} in {env_file}')


def resolve_service_names(raw_services: list[str] | None) -> list[str]:
    if raw_services:
        return raw_services
    return iter_stateful_service_names()


def resolve_table_names(service_name: str, scope: str) -> frozenset[str]:
    if scope == 'owned':
        return get_service_owned_table_names(service_name)
    return get_service_bootstrap_table_names(service_name)


def resolve_tables(service_name: str, scope: str) -> list:
    table_names = resolve_table_names(service_name, scope)
    return [
        table
        for table in resolve_service_tables(service_name, metadata=db.metadata)
        if table.name in table_names
    ]


def create_selected_tables(target_engine, tables: list) -> None:
    if tables:
        db.metadata.create_all(bind=target_engine, tables=tables, checkfirst=True)


def clear_selected_tables(target_connection, tables: list) -> None:
    for table in reversed(tables):
        target_connection.execute(table.delete())


def copy_table_rows(source_connection, target_connection, table, *, batch_size: int = 500) -> int:
    row_count = 0
    result = source_connection.execute(select(table))
    while True:
        batch = result.mappings().fetchmany(batch_size)
        if not batch:
            break
        payload = [dict(row) for row in batch]
        target_connection.execute(table.insert(), payload)
        row_count += len(payload)
    return row_count


def reset_postgres_sequence(target_connection, table) -> None:
    primary_key_columns = list(table.primary_key.columns)
    if len(primary_key_columns) != 1:
        return

    pk_column = primary_key_columns[0]
    if not isinstance(pk_column.type, (Integer, BigInteger)):
        return

    target_connection.execute(text(
        f"""
        SELECT setval(
            pg_get_serial_sequence('{table.name}', '{pk_column.name}'),
            COALESCE(MAX({pk_column.name}), 1),
            MAX({pk_column.name}) IS NOT NULL
        )
        FROM {table.name}
        """
    ))


def print_plan(service_names: list[str], scope: str) -> None:
    for service_name in service_names:
        table_names = sorted(resolve_table_names(service_name, scope))
        print(f'[{service_name}]')
        if not table_names:
            print('  (no SQLAlchemy tables)')
            continue
        for table_name in table_names:
            print(f'  - {table_name}')


def migrate_service(
    service_name: str,
    *,
    scope: str,
    source_engine,
    target_engine,
    replace: bool,
    bootstrap_only: bool,
) -> dict[str, int]:
    tables = resolve_tables(service_name, scope)
    create_selected_tables(target_engine, tables)
    if bootstrap_only or not tables:
        return {}

    source_table_names = set(inspect(source_engine).get_table_names())
    copied_counts: dict[str, int] = {}

    with source_engine.connect() as source_connection, target_engine.begin() as target_connection:
        if replace:
            clear_selected_tables(target_connection, tables)

        for table in tables:
            if table.name not in source_table_names:
                copied_counts[table.name] = 0
                continue
            copied_counts[table.name] = copy_table_rows(source_connection, target_connection, table)

        if target_engine.dialect.name == 'postgresql':
            for table in tables:
                reset_postgres_sequence(target_connection, table)

    return copied_counts


def main() -> int:
    args = parse_args()
    source_sqlite = Path(args.source_sqlite).resolve()
    env_file = Path(args.env_file).resolve()
    service_names = resolve_service_names(args.services)

    if args.plan:
        print_plan(service_names, args.scope)
        return 0

    if not source_sqlite.exists():
        raise FileNotFoundError(f'SQLite source not found: {source_sqlite}')
    if not env_file.exists():
        raise FileNotFoundError(f'Env file not found: {env_file}')

    source_engine = create_engine(f'sqlite:///{source_sqlite.as_posix()}')

    for service_name in service_names:
        target_url = load_target_database_url(service_name, env_file)
        target_engine = create_engine(target_url)
        copied_counts = migrate_service(
            service_name,
            scope=args.scope,
            source_engine=source_engine,
            target_engine=target_engine,
            replace=args.replace,
            bootstrap_only=args.bootstrap_only,
        )
        selected_tables = sorted(resolve_table_names(service_name, args.scope))
        print(f'[{service_name}] target={target_engine.url.render_as_string(hide_password=True)}')
        if not selected_tables:
            print('  no SQLAlchemy tables selected')
            continue
        if args.bootstrap_only:
            print(f'  bootstrapped {len(selected_tables)} tables')
            continue
        for table_name in selected_tables:
            print(f'  {table_name}: {copied_counts.get(table_name, 0)} rows')

    return 0


if __name__ == '__main__':
    raise SystemExit(main())
