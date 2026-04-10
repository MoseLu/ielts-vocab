from __future__ import annotations

import importlib.util
from pathlib import Path

from fastapi.testclient import TestClient

from platform_sdk.internal_service_auth import (
    INTERNAL_SERVICE_AUTH_HEADER,
    SERVICE_NAME_HEADER,
    create_internal_service_token,
)


LEARNING_CORE_SERVICE_PATH = (
    Path(__file__).resolve().parents[2]
    / 'services'
    / 'learning-core-service'
    / 'main.py'
)
ADMIN_OPS_SERVICE_PATH = (
    Path(__file__).resolve().parents[2]
    / 'services'
    / 'admin-ops-service'
    / 'main.py'
)


def _load_module(module_name: str, path: Path):
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _configure_env(monkeypatch, tmp_path: Path, service_name: str) -> None:
    monkeypatch.setenv('SECRET_KEY', 'test-secret')
    monkeypatch.setenv('JWT_SECRET_KEY', 'test-jwt-secret')
    monkeypatch.setenv('INTERNAL_SERVICE_JWT_SECRET_KEY', 'test-jwt-secret')
    monkeypatch.setenv('COOKIE_SECURE', 'false')
    monkeypatch.setenv('EMAIL_CODE_DELIVERY_MODE', 'mock')
    monkeypatch.setenv('SQLITE_DB_PATH', str(tmp_path / f'{service_name}.sqlite'))
    monkeypatch.setenv('DB_BACKUP_ENABLED', 'false')


def _internal_headers(*, user_id: int, is_admin: bool = False) -> dict[str, str]:
    token = create_internal_service_token(
        secret='test-jwt-secret',
        source_service_name='gateway-bff',
        user_id=user_id,
        is_admin=is_admin,
        scopes=('admin', 'user') if is_admin else ('user',),
        request_id='req-internal',
        trace_id='trace-internal',
    )
    return {
        INTERNAL_SERVICE_AUTH_HEADER: token,
        SERVICE_NAME_HEADER: 'gateway-bff',
    }


def test_learning_core_accepts_internal_service_user_without_local_user_row(monkeypatch, tmp_path):
    _configure_env(monkeypatch, tmp_path, 'learning-core-internal')
    module = _load_module('learning_core_service_internal_auth', LEARNING_CORE_SERVICE_PATH)
    client = TestClient(module.app)

    response = client.get(
        '/api/books/progress',
        headers=_internal_headers(user_id=90210),
    )

    assert response.status_code == 200
    assert response.json() == {'progress': {}}


def test_admin_ops_accepts_internal_admin_user_without_local_user_row(monkeypatch, tmp_path):
    _configure_env(monkeypatch, tmp_path, 'admin-ops-internal')
    module = _load_module('admin_ops_service_internal_auth', ADMIN_OPS_SERVICE_PATH)
    client = TestClient(module.app)

    response = client.get(
        '/api/admin/overview',
        headers=_internal_headers(user_id=7, is_admin=True),
    )

    assert response.status_code == 200
    assert 'total_users' in response.json()
