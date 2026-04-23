from __future__ import annotations

import importlib
import os
from contextlib import contextmanager, nullcontext
from functools import lru_cache

from flask import Flask
from sqlalchemy.pool import NullPool

_WORKER_DB_MODULES = {
    'admin-ops-service': 'service_models.admin_ops_models:db',
    'ai-execution-service': 'service_models.ai_execution_models:db',
    'catalog-content-service': 'service_models.catalog_content_models:db',
    'identity-service': 'service_models.identity_models:db',
    'learning-core-service': 'service_models.learning_core_models:db',
    'notes-service': 'service_models.notes_models:db',
    'tts-media-service': 'service_models.eventing_models:db',
}

_NULLPOOL_INCOMPATIBLE_ENGINE_OPTIONS = {
    'pool_size',
    'max_overflow',
    'pool_timeout',
    'pool_use_lifo',
}


@contextmanager
def _service_name_env(service_name: str):
    previous_value = os.environ.get('CURRENT_SERVICE_NAME')
    os.environ['CURRENT_SERVICE_NAME'] = service_name
    try:
        yield
    finally:
        if previous_value is None:
            os.environ.pop('CURRENT_SERVICE_NAME', None)
        else:
            os.environ['CURRENT_SERVICE_NAME'] = previous_value


def _worker_engine_options(database_uri: str) -> dict[str, object]:
    if not database_uri.startswith('postgresql://'):
        return {}
    return {
        'poolclass': NullPool,
        'pool_pre_ping': True,
    }


def _resolve_worker_engine_options(
    *,
    database_uri: str,
    existing_engine_options: dict[str, object],
) -> dict[str, object]:
    worker_engine_options = _worker_engine_options(database_uri)
    if not worker_engine_options:
        return existing_engine_options
    sanitized_engine_options = {
        key: value
        for key, value in existing_engine_options.items()
        if key not in _NULLPOOL_INCOMPATIBLE_ENGINE_OPTIONS
    }
    return {
        **sanitized_engine_options,
        **worker_engine_options,
    }


@lru_cache(maxsize=None)
def _create_worker_flask_app(service_name: str):
    db_ref = _WORKER_DB_MODULES.get(service_name)
    if not db_ref:
        return None

    with _service_name_env(service_name):
        config_module = importlib.import_module('config')
        config_class = importlib.reload(config_module).Config
        module_name, db_name = db_ref.split(':', 1)
        module = importlib.import_module(module_name)
        db = getattr(module, db_name)

        app = Flask(f'{service_name}.worker')
        app.config.from_object(config_class)
        existing_engine_options = app.config.get('SQLALCHEMY_ENGINE_OPTIONS') or {}
        app.config['SQLALCHEMY_ENGINE_OPTIONS'] = _resolve_worker_engine_options(
            database_uri=app.config.get('SQLALCHEMY_DATABASE_URI', ''),
            existing_engine_options=existing_engine_options,
        )
        db.init_app(app)
        return app


def worker_app_context(*, service_name: str | None = None):
    try:
        from flask import has_app_context
    except ImportError:
        return nullcontext()

    if has_app_context():
        return nullcontext()

    resolved_service_name = (service_name or os.environ.get('CURRENT_SERVICE_NAME') or '').strip()
    app = _create_worker_flask_app(resolved_service_name)
    if app is None:
        return nullcontext()

    @contextmanager
    def _context():
        with _service_name_env(resolved_service_name):
            with app.app_context():
                yield

    return _context()
