from __future__ import annotations

import importlib
import os
from contextlib import nullcontext
from functools import lru_cache


_SERVICE_APP_FACTORIES = {
    'admin-ops-service': 'platform_sdk.admin_ops_runtime:create_admin_ops_flask_app',
    'ai-execution-service': 'platform_sdk.ai_runtime:create_ai_flask_app',
    'catalog-content-service': 'platform_sdk.catalog_content_runtime:create_catalog_content_flask_app',
    'identity-service': 'platform_sdk.identity_runtime:create_identity_flask_app',
    'learning-core-service': 'platform_sdk.learning_core_runtime:create_learning_core_flask_app',
    'notes-service': 'platform_sdk.notes_runtime:create_notes_flask_app',
    'tts-media-service': 'platform_sdk.tts_media_runtime:create_tts_media_flask_app',
}


@lru_cache(maxsize=None)
def _create_worker_flask_app(service_name: str):
    factory_ref = _SERVICE_APP_FACTORIES.get(service_name)
    if not factory_ref:
        return None

    module_name, factory_name = factory_ref.split(':', 1)
    module = importlib.import_module(module_name)
    return getattr(module, factory_name)()


def worker_app_context():
    try:
        from flask import has_app_context
    except ImportError:
        return nullcontext()

    if has_app_context():
        return nullcontext()

    service_name = (os.environ.get('CURRENT_SERVICE_NAME') or '').strip()
    app = _create_worker_flask_app(service_name)
    if app is None:
        return nullcontext()
    return app.app_context()
