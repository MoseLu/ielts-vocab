from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import sqlalchemy as sa

from service_models.ai_execution_models import UserHomeTodoPlan


SCRIPT_PATH = Path(__file__).resolve().parents[2] / 'scripts' / 'run-service-schema-migrations.py'


def _load_script_module():
    spec = importlib.util.spec_from_file_location('run_service_schema_migrations_ai_todo', SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _write_env_file(tmp_path: Path, database_path: Path) -> Path:
    env_path = tmp_path / 'ai-execution.env'
    env_path.write_text(
        '\n'.join([
            'SECRET_KEY=test-secret-key',
            'JWT_SECRET_KEY=test-jwt-secret-key',
            f'AI_EXECUTION_SERVICE_SQLALCHEMY_DATABASE_URI=sqlite:///{database_path.as_posix()}',
        ]),
        encoding='utf-8',
    )
    return env_path


def _create_home_todo_table_with_identity_fk(database_path: Path) -> None:
    engine = sa.create_engine(f'sqlite:///{database_path.as_posix()}')
    try:
        with engine.begin() as connection:
            connection.execute(sa.text(
                'CREATE TABLE users ('
                'id INTEGER PRIMARY KEY, '
                'username VARCHAR(100) NOT NULL UNIQUE, '
                'password_hash VARCHAR(255) NOT NULL'
                ')'
            ))
            connection.execute(sa.text(
                'CREATE TABLE user_home_todo_plans ('
                'id INTEGER PRIMARY KEY, '
                'user_id INTEGER NOT NULL, '
                'plan_date VARCHAR(10) NOT NULL, '
                'pending_count INTEGER NOT NULL DEFAULT 0, '
                'completed_count INTEGER NOT NULL DEFAULT 0, '
                'carry_over_count INTEGER NOT NULL DEFAULT 0, '
                'last_generated_at DATETIME NOT NULL, '
                'created_at DATETIME NOT NULL, '
                'updated_at DATETIME NOT NULL, '
                'CONSTRAINT user_home_todo_plans_user_id_fkey '
                'FOREIGN KEY(user_id) REFERENCES users(id), '
                'CONSTRAINT unique_user_home_todo_plan UNIQUE(user_id, plan_date)'
                ')'
            ))
    finally:
        engine.dispose()


def test_home_todo_plan_user_id_is_not_bound_to_identity_users_table():
    user_fks = [
        fk for fk in UserHomeTodoPlan.__table__.foreign_keys
        if fk.parent.name == 'user_id' and fk.column.table.name == 'users'
    ]

    assert user_fks == []


def test_ai_migration_runner_drops_home_todo_identity_user_fk(tmp_path, monkeypatch):
    module = _load_script_module()
    database_path = tmp_path / 'ai-execution.sqlite'
    env_path = _write_env_file(tmp_path, database_path)
    _create_home_todo_table_with_identity_fk(database_path)

    monkeypatch.setenv('PYTEST_RUNNING', '1')
    monkeypatch.setenv('MICROSERVICES_ENV_FILE', str(env_path))

    result = module.migrate_service_schema('ai-execution-service', env_file=env_path)

    assert result['version_after'] == 'ai_execution_service_0002'
    assert [patch['revision'] for patch in result['applied_patches']] == ['ai_execution_service_0002']

    engine = sa.create_engine(f'sqlite:///{database_path.as_posix()}')
    try:
        inspector = sa.inspect(engine)
        remaining_user_fks = [
            fk for fk in inspector.get_foreign_keys('user_home_todo_plans')
            if fk.get('referred_table') == 'users' and fk.get('constrained_columns') == ['user_id']
        ]
        assert remaining_user_fks == []
    finally:
        engine.dispose()
