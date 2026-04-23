from __future__ import annotations

import os
import sys
from pathlib import Path

from a2wsgi import WSGIMiddleware


REPO_ROOT = Path(__file__).resolve().parents[2]
SDK_PATH = REPO_ROOT / 'packages' / 'platform-sdk'
if str(SDK_PATH) not in sys.path:
    sys.path.insert(0, str(SDK_PATH))

from platform_sdk.runtime_env import load_split_service_env

load_split_service_env(service_name='catalog-content-service')

from platform_sdk.catalog_content_runtime import create_catalog_content_flask_app
from platform_sdk.database_readiness import make_sqlalchemy_readiness_check
from platform_sdk.service_app import create_service_shell_app

catalog_content_flask_app = create_catalog_content_flask_app()

app = create_service_shell_app(
    service_name='catalog-content-service',
    version='0.1.0',
    readiness_checks={
        'database': make_sqlalchemy_readiness_check(catalog_content_flask_app.config['SQLALCHEMY_DATABASE_URI']),
    },
    extra_health={'catalog_compatibility': True},
)
app.mount('/', WSGIMiddleware(catalog_content_flask_app))


if __name__ == '__main__':
    import uvicorn

    uvicorn.run(app, host='0.0.0.0', port=int(os.environ.get('CATALOG_CONTENT_SERVICE_PORT', '8103')))
