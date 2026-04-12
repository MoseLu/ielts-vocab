from __future__ import annotations

import os

from platform_sdk.runtime_env import load_split_service_env


def test_load_split_service_env_uses_configured_backend_env_file(tmp_path, monkeypatch):
    backend_env = tmp_path / 'backend.env'
    microservices_env = tmp_path / 'microservices.env'
    backend_env.write_text('SECRET_KEY=from-backend-env\n', encoding='utf-8')
    microservices_env.write_text(
        'IDENTITY_SERVICE_SQLALCHEMY_DATABASE_URI=sqlite:///identity.sqlite\n',
        encoding='utf-8',
    )

    monkeypatch.setenv('PYTEST_RUNNING', '1')
    monkeypatch.setenv('BACKEND_ENV_FILE', str(backend_env))
    monkeypatch.setenv('MICROSERVICES_ENV_FILE', str(microservices_env))
    monkeypatch.delenv('SECRET_KEY', raising=False)
    monkeypatch.delenv('IDENTITY_SERVICE_SQLALCHEMY_DATABASE_URI', raising=False)

    loaded = load_split_service_env(service_name='identity-service')

    assert loaded['backend_env'] == str(backend_env.resolve())
    assert loaded['microservices_env'] == str(microservices_env.resolve())
    assert os.environ['CURRENT_SERVICE_NAME'] == 'identity-service'
    assert os.environ['SECRET_KEY'] == 'from-backend-env'
    assert os.environ['IDENTITY_SERVICE_SQLALCHEMY_DATABASE_URI'] == 'sqlite:///identity.sqlite'
    assert loaded['backend_env']
    assert loaded['microservices_env']


def test_load_split_service_env_applies_http_slot_env_after_microservices_env(tmp_path, monkeypatch):
    backend_env = tmp_path / 'backend.env'
    microservices_env = tmp_path / 'microservices.env'
    slot_env = tmp_path / 'blue.env'
    backend_env.write_text('SECRET_KEY=from-backend-env\n', encoding='utf-8')
    microservices_env.write_text(
        'LEARNING_CORE_SERVICE_PORT=8102\n'
        'LEARNING_CORE_SERVICE_URL=http://127.0.0.1:8102\n',
        encoding='utf-8',
    )
    slot_env.write_text(
        'LEARNING_CORE_SERVICE_PORT=18102\n'
        'LEARNING_CORE_SERVICE_URL=http://127.0.0.1:18102\n',
        encoding='utf-8',
    )

    monkeypatch.setenv('PYTEST_RUNNING', '1')
    monkeypatch.setenv('BACKEND_ENV_FILE', str(backend_env))
    monkeypatch.setenv('MICROSERVICES_ENV_FILE', str(microservices_env))
    monkeypatch.setenv('IELTS_HTTP_SLOT_ENV_FILE', str(slot_env))
    monkeypatch.delenv('LEARNING_CORE_SERVICE_PORT', raising=False)
    monkeypatch.delenv('LEARNING_CORE_SERVICE_URL', raising=False)

    loaded = load_split_service_env(service_name='learning-core-service')

    assert loaded['microservices_env'] == str(microservices_env.resolve())
    assert loaded['http_slot_env'] == str(slot_env.resolve())
    assert os.environ['LEARNING_CORE_SERVICE_PORT'] == '18102'
    assert os.environ['LEARNING_CORE_SERVICE_URL'] == 'http://127.0.0.1:18102'
