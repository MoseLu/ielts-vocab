from __future__ import annotations

import importlib
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
BACKEND_PATH = REPO_ROOT / 'backend'
if str(BACKEND_PATH) not in sys.path:
    sys.path.insert(0, str(BACKEND_PATH))

DEFAULT_DB_MODEL_MODULE = 'service_models.identity_models'
EVENTING_MODEL_MODULE = 'service_models.eventing_models'

SERVICE_MODEL_MODULES: dict[str, tuple[str, ...]] = {
    'gateway-bff': (DEFAULT_DB_MODEL_MODULE,),
    'identity-service': ('service_models.identity_models', EVENTING_MODEL_MODULE),
    'learning-core-service': (
        'service_models.learning_core_models',
        EVENTING_MODEL_MODULE,
        'service_models.identity_models',
        'service_models.catalog_content_models',
    ),
    'catalog-content-service': (
        'service_models.catalog_content_models',
        EVENTING_MODEL_MODULE,
        'service_models.identity_models',
        'service_models.notes_models',
    ),
    'notes-service': (
        'service_models.notes_models',
        EVENTING_MODEL_MODULE,
        'service_models.identity_models',
        'service_models.learning_core_models',
        'service_models.catalog_content_models',
    ),
    'ai-execution-service': (
        'service_models.ai_execution_models',
        EVENTING_MODEL_MODULE,
        'service_models.identity_models',
        'service_models.learning_core_models',
        'service_models.notes_models',
        'service_models.catalog_content_models',
    ),
    'admin-ops-service': (
        'service_models.admin_ops_models',
        EVENTING_MODEL_MODULE,
        'service_models.identity_models',
        'service_models.learning_core_models',
        'service_models.catalog_content_models',
    ),
    'tts-media-service': (EVENTING_MODEL_MODULE, DEFAULT_DB_MODEL_MODULE),
    'asr-service': (EVENTING_MODEL_MODULE, DEFAULT_DB_MODEL_MODULE),
}


def get_service_model_module_names(service_name: str) -> tuple[str, ...]:
    try:
        return SERVICE_MODEL_MODULES[service_name]
    except KeyError as exc:
        raise KeyError(f'Unknown microservice model registry: {service_name}') from exc



def load_service_model_modules(service_name: str) -> tuple[object, ...]:
    return tuple(
        importlib.import_module(module_name)
        for module_name in get_service_model_module_names(service_name)
    )



def resolve_service_db(service_name: str):
    for module in load_service_model_modules(service_name):
        db = getattr(module, 'db', None)
        if db is not None:
            return db
    raise RuntimeError(f'{service_name} does not expose a SQLAlchemy db binding')
