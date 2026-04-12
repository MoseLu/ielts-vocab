from __future__ import annotations

import os
import sys
from pathlib import Path

from fastapi.middleware.wsgi import WSGIMiddleware


REPO_ROOT = Path(__file__).resolve().parents[2]
SDK_PATH = REPO_ROOT / 'packages' / 'platform-sdk'
if str(SDK_PATH) not in sys.path:
    sys.path.insert(0, str(SDK_PATH))

from platform_sdk.runtime_env import load_split_service_env

load_split_service_env(service_name='learning-core-service')

from platform_sdk.database_readiness import make_sqlalchemy_readiness_check
from platform_sdk.ai_vocab_catalog_application import get_quick_memory_vocab_lookup
from platform_sdk.learning_core_runtime import create_learning_core_flask_app
from platform_sdk.service_app import create_service_app

try:
    get_quick_memory_vocab_lookup()
except Exception:
    pass

learning_core_flask_app = create_learning_core_flask_app()

app = create_service_app(
    service_name='learning-core-service',
    version='0.1.0',
    readiness_checks={
        'database': make_sqlalchemy_readiness_check(learning_core_flask_app.config['SQLALCHEMY_DATABASE_URI']),
    },
    extra_health={'learning_progress_compatibility': True},
)
app.mount('/', WSGIMiddleware(learning_core_flask_app))


if __name__ == '__main__':
    import uvicorn

    uvicorn.run(app, host='0.0.0.0', port=int(os.environ.get('LEARNING_CORE_SERVICE_PORT', '8102')))
