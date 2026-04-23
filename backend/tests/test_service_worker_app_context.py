from __future__ import annotations

from flask import current_app, has_app_context
from sqlalchemy.pool import NullPool

from platform_sdk import service_worker_app_context


def test_worker_app_context_builds_lightweight_service_app(tmp_path, monkeypatch):
    sqlite_path = tmp_path / 'identity-worker.sqlite'
    monkeypatch.setenv('CURRENT_SERVICE_NAME', 'identity-service')
    monkeypatch.setenv('SECRET_KEY', 'test-secret')
    monkeypatch.setenv('JWT_SECRET_KEY', 'test-jwt-secret')
    monkeypatch.setenv(
        'IDENTITY_SERVICE_SQLALCHEMY_DATABASE_URI',
        f'sqlite:///{sqlite_path}',
    )
    service_worker_app_context._create_worker_flask_app.cache_clear()

    with service_worker_app_context.worker_app_context():
        assert has_app_context() is True
        assert current_app.name == 'identity-service.worker'
        assert current_app.config['SQLALCHEMY_DATABASE_URI'] == f'sqlite:///{sqlite_path}'

    service_worker_app_context._create_worker_flask_app.cache_clear()


def test_worker_app_context_falls_back_to_noop_for_unknown_service(monkeypatch):
    monkeypatch.setenv('CURRENT_SERVICE_NAME', 'gateway-bff')
    service_worker_app_context._create_worker_flask_app.cache_clear()

    with service_worker_app_context.worker_app_context():
        assert has_app_context() is False

    service_worker_app_context._create_worker_flask_app.cache_clear()


def test_worker_app_context_accepts_explicit_service_name_and_uses_nullpool_for_postgres(monkeypatch):
    monkeypatch.delenv('CURRENT_SERVICE_NAME', raising=False)
    monkeypatch.setenv('SECRET_KEY', 'test-secret')
    monkeypatch.setenv('JWT_SECRET_KEY', 'test-jwt-secret')
    monkeypatch.setenv(
        'IDENTITY_SERVICE_SQLALCHEMY_DATABASE_URI',
        'postgresql://identity:secret@127.0.0.1:5432/identity_db',
    )
    service_worker_app_context._create_worker_flask_app.cache_clear()

    with service_worker_app_context.worker_app_context(service_name='identity-service'):
        assert has_app_context() is True
        assert current_app.name == 'identity-service.worker'
        engine_options = current_app.config['SQLALCHEMY_ENGINE_OPTIONS']
        assert engine_options['poolclass'] is NullPool
        assert 'pool_size' not in engine_options
        assert 'max_overflow' not in engine_options
        assert 'pool_timeout' not in engine_options
        assert 'pool_use_lifo' not in engine_options

    service_worker_app_context._create_worker_flask_app.cache_clear()
