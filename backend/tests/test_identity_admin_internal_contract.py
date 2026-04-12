from __future__ import annotations

import importlib.util
from pathlib import Path

from fastapi.testclient import TestClient

from models import User, db
from platform_sdk.admin_user_management_application import set_admin_response
from platform_sdk.internal_service_auth import create_internal_auth_headers_for_user


IDENTITY_SERVICE_PATH = (
    Path(__file__).resolve().parents[2]
    / 'services'
    / 'identity-service'
    / 'main.py'
)


def _load_identity_service_module(module_name: str):
    spec = importlib.util.spec_from_file_location(module_name, IDENTITY_SERVICE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _configure_identity_env(monkeypatch, tmp_path: Path) -> None:
    database_path = tmp_path / 'identity-service.sqlite'
    database_uri = f'sqlite:///{database_path.as_posix()}'
    monkeypatch.setenv('SECRET_KEY', 'test-secret')
    monkeypatch.setenv('JWT_SECRET_KEY', 'test-jwt-secret')
    monkeypatch.setenv('INTERNAL_SERVICE_JWT_SECRET_KEY', 'test-jwt-secret')
    monkeypatch.setenv('COOKIE_SECURE', 'false')
    monkeypatch.setenv('EMAIL_CODE_DELIVERY_MODE', 'mock')
    monkeypatch.setenv('SQLITE_DB_PATH', str(database_path))
    monkeypatch.setenv('SQLALCHEMY_DATABASE_URI', database_uri)
    monkeypatch.setenv('IDENTITY_SERVICE_SQLITE_DB_PATH', str(database_path))
    monkeypatch.setenv('IDENTITY_SERVICE_SQLALCHEMY_DATABASE_URI', database_uri)
    monkeypatch.setenv('DB_BACKUP_ENABLED', 'false')
    monkeypatch.setenv('CURRENT_SERVICE_NAME', 'identity-service')


def _internal_admin_headers(admin_user_id: int) -> dict[str, str]:
    return create_internal_auth_headers_for_user(
        user_id=admin_user_id,
        source_service_name='admin-ops-service',
        is_admin=True,
        scopes=('admin', 'user'),
        env={'INTERNAL_SERVICE_JWT_SECRET_KEY': 'test-jwt-secret'},
    )


def test_identity_internal_admin_set_admin_updates_user(monkeypatch, tmp_path):
    _configure_identity_env(monkeypatch, tmp_path)
    module = _load_identity_service_module('identity_service_internal_admin')
    client = TestClient(module.app)

    with module.identity_flask_app.app_context():
        admin = User(username='identity-admin', email='identity-admin@example.com', is_admin=True)
        admin.set_password('password123')
        target = User(username='identity-target', email='identity-target@example.com')
        target.set_password('password123')
        db.session.add_all([admin, target])
        db.session.commit()
        admin_id = admin.id
        target_id = target.id

    response = client.post(
        f'/internal/identity/admin/users/{target_id}/set-admin',
        headers=_internal_admin_headers(admin_id),
        json={'is_admin': True},
    )

    assert response.status_code == 200
    assert response.json()['user']['is_admin'] is True
    with module.identity_flask_app.app_context():
        assert db.session.get(User, target_id).is_admin is True


def test_admin_set_admin_uses_identity_internal_contract(monkeypatch):
    calls = []

    def fake_set_identity_user_admin(*, admin_user_id: int, target_user_id: int, is_admin: bool):
        calls.append((admin_user_id, target_user_id, is_admin))
        return {'message': '已更新', 'user': {'id': target_user_id, 'is_admin': is_admin}}, 200

    monkeypatch.setenv('CURRENT_SERVICE_NAME', 'admin-ops-service')
    monkeypatch.setenv('ALLOW_LEGACY_CROSS_SERVICE_FALLBACK', 'false')
    monkeypatch.setattr(
        'platform_sdk.admin_user_management_application.set_identity_user_admin',
        fake_set_identity_user_admin,
    )

    payload, status = set_admin_response(1, 2, {'is_admin': True})

    assert status == 200
    assert payload['user']['is_admin'] is True
    assert calls == [(1, 2, True)]


def test_admin_set_admin_returns_strict_boundary_when_identity_unavailable(monkeypatch):
    def fail_identity_user_admin(**kwargs):
        del kwargs
        raise RuntimeError('identity down')

    monkeypatch.setenv('CURRENT_SERVICE_NAME', 'admin-ops-service')
    monkeypatch.setenv('ALLOW_LEGACY_CROSS_SERVICE_FALLBACK', 'false')
    monkeypatch.setattr(
        'platform_sdk.admin_user_management_application.set_identity_user_admin',
        fail_identity_user_admin,
    )

    payload, status = set_admin_response(1, 2, {'is_admin': True})

    assert status == 503
    assert payload['boundary'] == 'strict-internal-contract'
    assert payload['upstream'] == 'identity-service'
