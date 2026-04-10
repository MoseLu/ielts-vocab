from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote_plus

from dotenv import dotenv_values
from sqlalchemy import create_engine, func, inspect, select


REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_PATH = REPO_ROOT / 'backend'
SDK_PATH = REPO_ROOT / 'packages' / 'platform-sdk'
if str(BACKEND_PATH) not in sys.path:
    sys.path.insert(0, str(BACKEND_PATH))
if str(SDK_PATH) not in sys.path:
    sys.path.insert(0, str(SDK_PATH))

from models import db
from platform_sdk.service_migration_plan import iter_service_migration_service_names
from platform_sdk.service_schema import resolve_service_tables
from platform_sdk.service_table_plan import (
    get_service_bootstrap_table_names,
    get_service_owned_table_names,
)


DEFAULT_SOURCE_SQLITE = BACKEND_PATH / 'database.sqlite'
DEFAULT_ENV_FILE = BACKEND_PATH / '.env.microservices.local'


@dataclass(frozen=True)
class TableParityResult:
    table_name: str
    source_rows: int
    target_rows: int
    source_min_pk: int | None
    target_min_pk: int | None
    source_max_pk: int | None
    target_max_pk: int | None

    @property
    def matches(self) -> bool:
        return (
            self.source_rows == self.target_rows
            and self.source_min_pk == self.target_min_pk
            and self.source_max_pk == self.target_max_pk
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description='Validate row-count parity between legacy SQLite and microservice-owned databases.',
    )
    parser.add_argument(
        '--service',
        action='append',
        dest='services',
        help='Service name to validate. Repeat for multiple services. Defaults to all write-owning services.',
    )
    parser.add_argument(
        '--scope',
        choices=('owned', 'bootstrap'),
        default='owned',
        help='Validate owned tables only, or the full bootstrap set including shadow tables.',
    )
    parser.add_argument(
        '--source-sqlite',
        default=str(DEFAULT_SOURCE_SQLITE),
        help='Path to the legacy SQLite database.',
    )
    parser.add_argument(
        '--env-file',
        default=str(DEFAULT_ENV_FILE),
        help='Env file that contains per-service target database URLs.',
    )
    return parser.parse_args()


def service_env_prefix(service_name: str) -> str:
    return service_name.replace('-', '_').upper()


def _env_value(env_values: dict[str, str], service_name: str, name: str) -> str:
    prefix = service_env_prefix(service_name)
    return (
        (env_values.get(f'{prefix}_{name}') or '').strip()
        or (env_values.get(name) or '').strip()
    )


def _build_postgres_database_url(env_values: dict[str, str], service_name: str) -> str:
    host = _env_value(env_values, service_name, 'POSTGRES_HOST')
    database = (
        _env_value(env_values, service_name, 'POSTGRES_DB')
        or _env_value(env_values, service_name, 'POSTGRES_DATABASE')
    )
    user = _env_value(env_values, service_name, 'POSTGRES_USER')
    password = _env_value(env_values, service_name, 'POSTGRES_PASSWORD')
    if not (host and database and user and password):
        return ''

    port = _env_value(env_values, service_name, 'POSTGRES_PORT') or '5432'
    sslmode = _env_value(env_values, service_name, 'POSTGRES_SSLMODE')
    auth = f'{quote_plus(user)}:{quote_plus(password)}'
    query = f'?sslmode={quote_plus(sslmode)}' if sslmode else ''
    return f'postgresql://{auth}@{host}:{port}/{database}{query}'


def load_target_database_url(service_name: str, env_file: Path) -> str:
    env_values: dict[str, str] = {}
    if BACKEND_PATH.joinpath('.env').exists():
        env_values.update(dotenv_values(BACKEND_PATH / '.env'))
    env_values.update(dotenv_values(env_file))

    for key in (
        f'{service_env_prefix(service_name)}_SQLALCHEMY_DATABASE_URI',
        f'{service_env_prefix(service_name)}_DATABASE_URL',
        'SQLALCHEMY_DATABASE_URI',
        'DATABASE_URL',
    ):
        value = env_values.get(key)
        if value:
            return value.strip()

    postgres_url = _build_postgres_database_url(env_values, service_name)
    if postgres_url:
        return postgres_url
    raise RuntimeError(f'Missing target database URL for {service_name} in {env_file}')


def resolve_service_names(raw_services: list[str] | None, *, scope: str) -> list[str]:
    if raw_services:
        return raw_services
    if scope == 'owned':
        return iter_service_migration_service_names()
    return iter_service_migration_service_names()


def resolve_table_names(service_name: str, scope: str) -> frozenset[str]:
    if scope == 'bootstrap':
        return get_service_bootstrap_table_names(service_name)
    return get_service_owned_table_names(service_name)


def resolve_tables(service_name: str, scope: str) -> list:
    table_names = resolve_table_names(service_name, scope)
    return [
        table
        for table in resolve_service_tables(service_name, metadata=db.metadata)
        if table.name in table_names
    ]


def _pk_column(table):
    columns = list(table.primary_key.columns)
    if len(columns) != 1:
        return None
    return columns[0]


def _table_summary(connection, table) -> tuple[int, int | None, int | None]:
    if table.name not in set(inspect(connection).get_table_names()):
        return 0, None, None

    pk_column = _pk_column(table)
    if pk_column is None:
        row = connection.execute(
            select(func.count()).select_from(table)
        ).one()
        return int(row[0]), None, None

    row = connection.execute(
        select(
            func.count(),
            func.min(pk_column),
            func.max(pk_column),
        ).select_from(table)
    ).one()
    return int(row[0]), row[1], row[2]


def validate_service_parity(
    service_name: str,
    *,
    scope: str,
    source_engine,
    target_engine,
) -> list[TableParityResult]:
    tables = resolve_tables(service_name, scope)
    results: list[TableParityResult] = []

    with source_engine.connect() as source_connection, target_engine.connect() as target_connection:
        for table in tables:
            source_rows, source_min_pk, source_max_pk = _table_summary(source_connection, table)
            target_rows, target_min_pk, target_max_pk = _table_summary(target_connection, table)
            results.append(
                TableParityResult(
                    table_name=table.name,
                    source_rows=source_rows,
                    target_rows=target_rows,
                    source_min_pk=source_min_pk,
                    target_min_pk=target_min_pk,
                    source_max_pk=source_max_pk,
                    target_max_pk=target_max_pk,
                )
            )

    return results


def print_service_report(service_name: str, target_url: str, results: list[TableParityResult]) -> None:
    print(f'[{service_name}] target={target_url}')
    if not results:
        print('  no tables selected')
        return

    for result in results:
        status = 'OK' if result.matches else 'MISMATCH'
        pk_summary = ''
        if result.source_min_pk is not None or result.target_min_pk is not None:
            pk_summary = (
                f' pk={result.source_min_pk}..{result.source_max_pk}'
                f' -> {result.target_min_pk}..{result.target_max_pk}'
            )
        print(
            f'  {status} {result.table_name}: '
            f'rows={result.source_rows} -> {result.target_rows}{pk_summary}'
        )


def main() -> int:
    args = parse_args()
    source_sqlite = Path(args.source_sqlite).resolve()
    env_file = Path(args.env_file).resolve()
    service_names = resolve_service_names(args.services, scope=args.scope)

    if not source_sqlite.exists():
        raise FileNotFoundError(f'SQLite source not found: {source_sqlite}')
    if not env_file.exists():
        raise FileNotFoundError(f'Env file not found: {env_file}')

    source_engine = create_engine(f'sqlite:///{source_sqlite.as_posix()}')
    any_mismatch = False

    for service_name in service_names:
        target_url = load_target_database_url(service_name, env_file)
        target_engine = create_engine(target_url)
        results = validate_service_parity(
            service_name,
            scope=args.scope,
            source_engine=source_engine,
            target_engine=target_engine,
        )
        print_service_report(
            service_name,
            target_engine.url.render_as_string(hide_password=True),
            results,
        )
        any_mismatch = any_mismatch or any(not result.matches for result in results)

    return 1 if any_mismatch else 0


if __name__ == '__main__':
    raise SystemExit(main())
