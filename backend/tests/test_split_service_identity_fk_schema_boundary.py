from __future__ import annotations

from pathlib import Path

import pytest
import sqlalchemy as sa

from test_service_schema_migration_runner import _load_script_module, _write_env_file


@pytest.mark.parametrize(
    ('service_name', 'table_name', 'expected_revision'),
    [
        ('learning-core-service', 'user_added_books', 'learning_core_service_0006'),
        ('catalog-content-service', 'custom_books', 'catalog_content_service_0004'),
        ('notes-service', 'user_learning_notes', 'notes_service_0002'),
        ('ai-execution-service', 'ai_prompt_runs', 'ai_execution_service_0003'),
    ],
)
def test_non_identity_service_migrations_remove_identity_user_fks(
    tmp_path: Path,
    monkeypatch,
    service_name: str,
    table_name: str,
    expected_revision: str,
):
    module = _load_script_module()
    database_path = tmp_path / f'{service_name}.sqlite'
    env_path = _write_env_file(tmp_path, service_name=service_name, database_path=database_path)

    monkeypatch.setenv('PYTEST_RUNNING', '1')
    monkeypatch.setenv('MICROSERVICES_ENV_FILE', str(env_path))

    result = module.migrate_service_schema(service_name, env_file=env_path)

    assert result['version_after'] == expected_revision
    assert any(patch['revision'] == expected_revision for patch in result['applied_patches'])

    engine = sa.create_engine(f'sqlite:///{database_path.as_posix()}')
    try:
        remaining_user_fks = [
            fk for fk in sa.inspect(engine).get_foreign_keys(table_name)
            if fk.get('referred_table') == 'users'
        ]
        assert remaining_user_fks == []
    finally:
        engine.dispose()
