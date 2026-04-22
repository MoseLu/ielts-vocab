from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import sys

import pytest
from sqlalchemy import create_engine

from models import db


SCRIPT_PATH = (
    Path(__file__).resolve().parents[2]
    / 'scripts'
    / 'validate_microservice_storage_parity.py'
)


def _load_script_module():
    spec = importlib.util.spec_from_file_location('validate_microservice_storage_parity', SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _insert_identity_rows(engine, *, user_count: int) -> None:
    users = db.metadata.tables['users']
    revoked_tokens = db.metadata.tables['revoked_tokens']
    rate_limit_buckets = db.metadata.tables['rate_limit_buckets']
    email_codes = db.metadata.tables['email_verification_codes']
    tables = [users, revoked_tokens, rate_limit_buckets, email_codes]
    db.metadata.create_all(bind=engine, tables=tables, checkfirst=True)

    with engine.begin() as connection:
        payload = [
            {
                'id': index,
                'username': f'user-{index}',
                'password_hash': 'hashed',
                'is_admin': False,
            }
            for index in range(1, user_count + 1)
        ]
        if payload:
            connection.execute(users.insert(), payload)


def test_validate_service_parity_matches_when_counts_align(tmp_path):
    module = _load_script_module()
    source_engine = create_engine(f"sqlite:///{(tmp_path / 'source.sqlite').as_posix()}")
    target_engine = create_engine(f"sqlite:///{(tmp_path / 'target.sqlite').as_posix()}")

    _insert_identity_rows(source_engine, user_count=2)
    _insert_identity_rows(target_engine, user_count=2)

    results = module.validate_service_parity(
        'identity-service',
        scope='owned',
        source_engine=source_engine,
        target_engine=target_engine,
    )

    by_name = {result.table_name: result for result in results}
    assert by_name['users'].matches is True
    assert by_name['users'].source_rows == 2
    assert by_name['users'].target_rows == 2
    assert all(result.matches for result in results)


def test_validate_service_parity_flags_row_count_mismatch(tmp_path):
    module = _load_script_module()
    source_engine = create_engine(f"sqlite:///{(tmp_path / 'source.sqlite').as_posix()}")
    target_engine = create_engine(f"sqlite:///{(tmp_path / 'target.sqlite').as_posix()}")

    _insert_identity_rows(source_engine, user_count=2)
    _insert_identity_rows(target_engine, user_count=1)

    results = module.validate_service_parity(
        'identity-service',
        scope='owned',
        source_engine=source_engine,
        target_engine=target_engine,
    )

    by_name = {result.table_name: result for result in results}
    assert by_name['users'].matches is False
    assert by_name['users'].source_rows == 2
    assert by_name['users'].target_rows == 1


def test_load_target_database_url_builds_postgres_uri_from_env_parts(tmp_path):
    module = _load_script_module()
    env_file = tmp_path / 'microservices.env'
    env_file.write_text(
        '\n'.join([
            'IDENTITY_SERVICE_POSTGRES_HOST=127.0.0.1',
            'IDENTITY_SERVICE_POSTGRES_PORT=5432',
            'IDENTITY_SERVICE_POSTGRES_DB=ielts_identity_service',
            'IDENTITY_SERVICE_POSTGRES_USER=identity',
            'IDENTITY_SERVICE_POSTGRES_PASSWORD=p@ss word',
            'IDENTITY_SERVICE_POSTGRES_SSLMODE=disable',
        ]),
        encoding='utf-8',
    )

    target_url = module.load_target_database_url('identity-service', env_file)

    assert target_url == (
        'postgresql://identity:p%40ss+word@127.0.0.1:5432/'
        'ielts_identity_service?sslmode=disable'
    )


def test_resolve_source_sqlite_path_falls_back_to_latest_app_home_snapshot(
    tmp_path,
    monkeypatch,
):
    module = _load_script_module()
    app_home = tmp_path / 'app-home'
    source_dir = app_home / 'source'
    source_dir.mkdir(parents=True)
    older_snapshot = source_dir / '20260410.sqlite'
    newer_snapshot = source_dir / '20260411.sqlite'
    older_snapshot.write_text('', encoding='utf-8')
    newer_snapshot.write_text('', encoding='utf-8')
    os.utime(older_snapshot, (1, 1))
    os.utime(newer_snapshot, (2, 2))

    monkeypatch.setenv('APP_HOME', app_home.as_posix())
    monkeypatch.delenv('SOURCE_SQLITE_PATH', raising=False)
    monkeypatch.delenv('SQLITE_DB_PATH', raising=False)
    monkeypatch.delenv('BACKEND_ENV_FILE', raising=False)
    monkeypatch.setattr(module, 'DEFAULT_SOURCE_SQLITE', tmp_path / 'missing.sqlite')

    resolved = module.resolve_source_sqlite_path(None, env_file=tmp_path / 'missing.env')

    assert resolved == newer_snapshot.resolve()


def test_resolve_source_sqlite_path_raises_for_missing_explicit_override(tmp_path):
    module = _load_script_module()

    with pytest.raises(FileNotFoundError, match='SQLite source not found:'):
        module.resolve_source_sqlite_path(
            str(tmp_path / 'missing.sqlite'),
            env_file=tmp_path / 'missing.env',
        )
