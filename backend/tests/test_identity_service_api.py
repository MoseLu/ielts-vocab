from __future__ import annotations

import importlib.util
from pathlib import Path

from fastapi.testclient import TestClient


SERVICE_PATH = (
    Path(__file__).resolve().parents[2]
    / 'services'
    / 'identity-service'
    / 'main.py'
)


def _load_identity_service_module(module_name: str):
    spec = importlib.util.spec_from_file_location(module_name, SERVICE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _configure_identity_env(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv('SECRET_KEY', 'test-secret')
    monkeypatch.setenv('JWT_SECRET_KEY', 'test-jwt-secret')
    monkeypatch.setenv('COOKIE_SECURE', 'false')
    monkeypatch.setenv('EMAIL_CODE_DELIVERY_MODE', 'mock')
    monkeypatch.setenv('SQLITE_DB_PATH', str(tmp_path / 'identity-service.sqlite'))
    monkeypatch.setenv('DB_BACKUP_ENABLED', 'false')


def test_identity_service_health_endpoint(monkeypatch, tmp_path):
    _configure_identity_env(monkeypatch, tmp_path)
    module = _load_identity_service_module('identity_service_health')
    client = TestClient(module.app)

    response = client.get('/health')

    assert response.status_code == 200
    assert response.json()['service'] == 'identity-service'
    assert response.json()['auth_compatibility'] is True


def test_identity_service_register_and_me_flow(monkeypatch, tmp_path):
    _configure_identity_env(monkeypatch, tmp_path)
    module = _load_identity_service_module('identity_service_register')
    client = TestClient(module.app)

    register_response = client.post(
        '/api/auth/register',
        json={
            'username': 'service-alice',
            'password': 'password123',
            'email': 'service-alice@example.com',
        },
    )

    assert register_response.status_code == 201
    assert register_response.json()['user']['username'] == 'service-alice'
    assert register_response.headers.get_list('set-cookie')

    me_response = client.get('/api/auth/me')

    assert me_response.status_code == 200
    assert me_response.json()['user']['username'] == 'service-alice'
    assert me_response.json()['access_expires_in'] > 0


def test_identity_service_forgot_password_returns_generic_payload(monkeypatch, tmp_path):
    _configure_identity_env(monkeypatch, tmp_path)
    module = _load_identity_service_module('identity_service_forgot')
    client = TestClient(module.app)

    response = client.post('/api/auth/forgot-password', json={'email': 'nobody@example.com'})

    assert response.status_code == 200
    assert response.json()['delivery_mode'] == 'mock'
    assert '验证码' in response.json()['message']
