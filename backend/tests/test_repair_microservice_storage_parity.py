from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

from sqlalchemy import create_engine, func, select

from models import db


SCRIPT_PATH = (
    Path(__file__).resolve().parents[2]
    / 'scripts'
    / 'repair_microservice_storage_parity.py'
)


def _load_script_module():
    spec = importlib.util.spec_from_file_location('repair_microservice_storage_parity', SCRIPT_PATH)
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


def _count_users(engine) -> int:
    users = db.metadata.tables['users']
    with engine.connect() as connection:
        row = connection.execute(select(func.count()).select_from(users)).one()
    return int(row[0])


def test_repair_service_parity_repairs_row_count_mismatch(tmp_path):
    module = _load_script_module()
    source_engine = create_engine(f"sqlite:///{(tmp_path / 'source.sqlite').as_posix()}")
    target_engine = create_engine(f"sqlite:///{(tmp_path / 'target.sqlite').as_posix()}")

    _insert_identity_rows(source_engine, user_count=2)
    _insert_identity_rows(target_engine, user_count=1)

    report = module.repair_service_parity(
        'identity-service',
        scope='owned',
        source_engine=source_engine,
        target_engine=target_engine,
        target_url='sqlite:///target.sqlite',
        dry_run=False,
    )

    assert report.mismatched_tables_before == ('users',)
    assert report.mismatched_tables_after == ()
    assert report.repair_attempted is True
    assert report.repaired is True
    assert report.copied_counts['users'] == 2
    assert _count_users(target_engine) == 2


def test_repair_service_parity_dry_run_leaves_target_unchanged(tmp_path):
    module = _load_script_module()
    source_engine = create_engine(f"sqlite:///{(tmp_path / 'source.sqlite').as_posix()}")
    target_engine = create_engine(f"sqlite:///{(tmp_path / 'target.sqlite').as_posix()}")

    _insert_identity_rows(source_engine, user_count=2)
    _insert_identity_rows(target_engine, user_count=1)

    report = module.repair_service_parity(
        'identity-service',
        scope='owned',
        source_engine=source_engine,
        target_engine=target_engine,
        target_url='sqlite:///target.sqlite',
        dry_run=True,
    )

    assert report.mismatched_tables_before == ('users',)
    assert report.mismatched_tables_after == ('users',)
    assert report.repair_attempted is False
    assert report.repaired is False
    assert _count_users(target_engine) == 1


def test_repair_service_parity_noops_when_service_is_clean(tmp_path):
    module = _load_script_module()
    source_engine = create_engine(f"sqlite:///{(tmp_path / 'source.sqlite').as_posix()}")
    target_engine = create_engine(f"sqlite:///{(tmp_path / 'target.sqlite').as_posix()}")

    _insert_identity_rows(source_engine, user_count=2)
    _insert_identity_rows(target_engine, user_count=2)

    report = module.repair_service_parity(
        'identity-service',
        scope='owned',
        source_engine=source_engine,
        target_engine=target_engine,
        target_url='sqlite:///target.sqlite',
        dry_run=False,
    )

    assert report.mismatched_tables_before == ()
    assert report.mismatched_tables_after == ()
    assert report.repair_attempted is False
    assert report.clean is True
