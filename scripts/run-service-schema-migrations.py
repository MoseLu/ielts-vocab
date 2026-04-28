from __future__ import annotations

import argparse
import sys
from collections.abc import Callable
from dataclasses import dataclass
import os
from pathlib import Path
from urllib.parse import quote_plus

import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations
from dotenv import load_dotenv


REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_PATH = REPO_ROOT / 'backend'
SDK_PATH = REPO_ROOT / 'packages' / 'platform-sdk'
for path in (BACKEND_PATH, SDK_PATH):
    path_text = str(path)
    if path_text not in sys.path:
        sys.path.insert(0, path_text)

from platform_sdk.runtime_env import load_split_service_env
from platform_sdk.service_migration_plan import (
    get_service_migration_plan,
    iter_service_migration_service_names,
)
from platform_sdk.service_model_registry import resolve_service_db
from platform_sdk.service_schema import bootstrap_service_schema
from services.storage_boundary_guard import validate_split_service_storage_boundary


@dataclass(frozen=True)
class SchemaPatch:
    revision: str
    description: str
    apply: Callable[[sa.engine.Connection], list[str]]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description='Apply idempotent schema migrations to split-service databases.',
    )
    parser.add_argument(
        '--service',
        action='append',
        dest='services',
        help='Service name to migrate. Repeat for multiple services. Defaults to all migration-planned services.',
    )
    parser.add_argument(
        '--env-file',
        help='Optional microservices env file. Defaults to MICROSERVICES_ENV_FILE or backend/.env.microservices.local.',
    )
    parser.add_argument(
        '--plan',
        action='store_true',
        help='Print the selected migration plan and exit.',
    )
    return parser.parse_args()


def resolve_service_names(raw_services: list[str] | None) -> list[str]:
    if raw_services:
        return raw_services
    return iter_service_migration_service_names()


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
    return os.path.join(BACKEND_PATH, 'database.sqlite')


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


def resolve_database_uri(*, service_name: str, env_file: Path | None) -> str:
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


def _bool_server_default(connection: sa.engine.Connection):
    if connection.dialect.name == 'postgresql':
        return sa.text('false')
    return sa.text('0')


def _migration_ops(connection: sa.engine.Connection) -> Operations:
    return Operations(MigrationContext.configure(connection))


def _version_table(plan):
    metadata = sa.MetaData()
    return sa.Table(
        plan.version_table,
        metadata,
        sa.Column('version_num', sa.String(length=255), primary_key=True),
    )


def _ensure_version_table(connection: sa.engine.Connection, plan) -> sa.Table:
    table = _version_table(plan)
    table.metadata.create_all(bind=connection, tables=[table], checkfirst=True)
    return table


def _read_version(connection: sa.engine.Connection, plan) -> str | None:
    table = _ensure_version_table(connection, plan)
    return connection.execute(sa.select(table.c.version_num)).scalar_one_or_none()


def _write_version(connection: sa.engine.Connection, plan, revision: str) -> None:
    table = _ensure_version_table(connection, plan)
    connection.execute(table.delete())
    connection.execute(table.insert().values(version_num=revision))


def _apply_learning_core_chapter_id_patch(connection: sa.engine.Connection) -> list[str]:
    inspector = sa.inspect(connection)
    ops = _migration_ops(connection)
    changes: list[str] = []

    for table_name in ('user_chapter_progress', 'user_chapter_mode_progress'):
        columns = {column['name']: column for column in inspector.get_columns(table_name)}
        chapter_id = columns.get('chapter_id')
        if chapter_id is None or isinstance(chapter_id['type'], sa.String):
            continue

        with ops.batch_alter_table(table_name) as batch_op:
            batch_op.alter_column(
                'chapter_id',
                existing_type=chapter_id['type'],
                type_=sa.String(length=50),
                existing_nullable=bool(chapter_id.get('nullable')),
            )
        changes.append(f'{table_name}.chapter_id -> VARCHAR(50)')
        inspector = sa.inspect(connection)

    return changes


def _apply_custom_book_metadata_patch(connection: sa.engine.Connection) -> list[str]:
    inspector = sa.inspect(connection)
    ops = _migration_ops(connection)
    bool_default = _bool_server_default(connection)
    changes: list[str] = []

    custom_book_columns = {column['name'] for column in inspector.get_columns('custom_books')}
    if 'education_stage' not in custom_book_columns:
        ops.add_column('custom_books', sa.Column('education_stage', sa.String(length=50), nullable=True))
        changes.append('custom_books.education_stage')
    if 'exam_type' not in custom_book_columns:
        ops.add_column('custom_books', sa.Column('exam_type', sa.String(length=50), nullable=True))
        changes.append('custom_books.exam_type')
    if 'ielts_skill' not in custom_book_columns:
        ops.add_column('custom_books', sa.Column('ielts_skill', sa.String(length=50), nullable=True))
        changes.append('custom_books.ielts_skill')
    if 'share_enabled' not in custom_book_columns:
        ops.add_column(
            'custom_books',
            sa.Column('share_enabled', sa.Boolean(), nullable=False, server_default=bool_default),
        )
        changes.append('custom_books.share_enabled')
    if 'chapter_word_target' not in custom_book_columns:
        ops.add_column(
            'custom_books',
            sa.Column('chapter_word_target', sa.Integer(), nullable=False, server_default=sa.text('15')),
        )
        changes.append('custom_books.chapter_word_target')

    custom_book_word_columns = {column['name'] for column in inspector.get_columns('custom_book_words')}
    if 'is_incomplete' not in custom_book_word_columns:
        ops.add_column(
            'custom_book_words',
            sa.Column('is_incomplete', sa.Boolean(), nullable=False, server_default=bool_default),
        )
        changes.append('custom_book_words.is_incomplete')

    return changes


def _apply_learning_core_progress_resume_patch(connection: sa.engine.Connection) -> list[str]:
    inspector = sa.inspect(connection)
    if 'user_chapter_progress' not in inspector.get_table_names():
        return []

    ops = _migration_ops(connection)
    columns = {column['name'] for column in inspector.get_columns('user_chapter_progress')}
    changes: list[str] = []
    if 'session_current_index' not in columns:
        ops.add_column(
            'user_chapter_progress',
            sa.Column('session_current_index', sa.Integer(), nullable=False, server_default=sa.text('0')),
        )
        changes.append('user_chapter_progress.session_current_index')
    if 'session_answered_words' not in columns:
        ops.add_column('user_chapter_progress', sa.Column('session_answered_words', sa.Text(), nullable=True))
        changes.append('user_chapter_progress.session_answered_words')
    if 'session_queue_words' not in columns:
        ops.add_column('user_chapter_progress', sa.Column('session_queue_words', sa.Text(), nullable=True))
        changes.append('user_chapter_progress.session_queue_words')
    return changes


def _apply_ai_home_todo_plan_user_fk_patch(connection: sa.engine.Connection) -> list[str]:
    inspector = sa.inspect(connection)
    if 'user_home_todo_plans' not in inspector.get_table_names():
        return []

    matching_fks = [
        fk for fk in inspector.get_foreign_keys('user_home_todo_plans')
        if fk.get('referred_table') == 'users'
        and fk.get('constrained_columns') == ['user_id']
    ]
    if not matching_fks:
        return []

    ops = _migration_ops(connection)
    changes: list[str] = []
    for fk in matching_fks:
        fk_name = fk.get('name')
        if not fk_name:
            continue
        with ops.batch_alter_table('user_home_todo_plans') as batch_op:
            batch_op.drop_constraint(fk_name, type_='foreignkey')
        changes.append(f'user_home_todo_plans.{fk_name}')

    return changes


SERVICE_PATCHES: dict[str, tuple[SchemaPatch, ...]] = {
    'learning-core-service': (
        SchemaPatch(
            revision='learning_core_service_0002',
            description='Store chapter progress ids as strings.',
            apply=_apply_learning_core_chapter_id_patch,
        ),
        SchemaPatch(
            revision='learning_core_service_0003',
            description='Add shadow custom book metadata and incomplete-word flags.',
            apply=_apply_custom_book_metadata_patch,
        ),
        SchemaPatch(
            revision='learning_core_service_0004',
            description='Add resumable chapter-progress snapshot columns.',
            apply=_apply_learning_core_progress_resume_patch,
        ),
    ),
    'catalog-content-service': (
        SchemaPatch(
            revision='catalog_content_service_0002',
            description='Add custom book metadata and incomplete-word flags.',
            apply=_apply_custom_book_metadata_patch,
        ),
    ),
    'ai-execution-service': (
        SchemaPatch(
            revision='ai_execution_service_0002',
            description='Remove identity user FK from home todo plans.',
            apply=_apply_ai_home_todo_plan_user_fk_patch,
        ),
    ),
}


def latest_revision_for_service(service_name: str) -> str:
    patches = SERVICE_PATCHES.get(service_name, ())
    if patches:
        return patches[-1].revision
    return get_service_migration_plan(service_name).baseline_revision


def migrate_service_schema(service_name: str, *, env_file: Path | None = None) -> dict:
    database_uri = resolve_database_uri(service_name=service_name, env_file=env_file)
    engine = sa.create_engine(database_uri)
    service_db = resolve_service_db(service_name)
    latest_revision = latest_revision_for_service(service_name)
    version_before: str | None = None
    applied_patches: list[dict[str, object]] = []

    try:
        bootstrapped_tables = bootstrap_service_schema(
            service_name,
            bind=engine,
            metadata=service_db.metadata,
        )
        with engine.begin() as connection:
            plan = get_service_migration_plan(service_name)
            version_before = _read_version(connection, plan)
            for patch in SERVICE_PATCHES.get(service_name, ()):
                changes = patch.apply(connection)
                if changes:
                    applied_patches.append({
                        'revision': patch.revision,
                        'description': patch.description,
                        'changes': changes,
                    })
            _write_version(connection, plan, latest_revision)
        return {
            'service_name': service_name,
            'database_uri': engine.url.render_as_string(hide_password=True),
            'bootstrapped_tables': bootstrapped_tables,
            'version_before': version_before,
            'version_after': latest_revision,
            'applied_patches': applied_patches,
        }
    finally:
        engine.dispose()


def print_plan(service_names: list[str]) -> None:
    for service_name in service_names:
        plan = get_service_migration_plan(service_name)
        print(f'[{service_name}]')
        print(f'  version_table: {plan.version_table}')
        print(f'  baseline_revision: {plan.baseline_revision}')
        print(f'  latest_revision: {latest_revision_for_service(service_name)}')
        patches = SERVICE_PATCHES.get(service_name, ())
        if not patches:
            print('  patches: (none)')
            continue
        for patch in patches:
            print(f'  - {patch.revision}: {patch.description}')


def print_result(result: dict) -> None:
    print(f"[{result['service_name']}] target={result['database_uri']}")
    print(f"  version: {result['version_before'] or '<unset>'} -> {result['version_after']}")
    if result['applied_patches']:
        for patch in result['applied_patches']:
            print(f"  applied {patch['revision']}: {', '.join(patch['changes'])}")
    else:
        print('  applied patches: none')


def main() -> int:
    args = parse_args()
    env_file = Path(args.env_file).resolve() if args.env_file else None
    service_names = resolve_service_names(args.services)

    if args.plan:
        print_plan(service_names)
        return 0

    for service_name in service_names:
        print_result(migrate_service_schema(service_name, env_file=env_file))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
