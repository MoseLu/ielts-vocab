from __future__ import annotations

import os
import sys
from pathlib import Path

from fastapi import Query
from fastapi.middleware.wsgi import WSGIMiddleware
from fastapi.responses import JSONResponse


REPO_ROOT = Path(__file__).resolve().parents[2]
SDK_PATH = REPO_ROOT / 'packages' / 'platform-sdk'
if str(SDK_PATH) not in sys.path:
    sys.path.insert(0, str(SDK_PATH))

from platform_sdk.runtime_env import load_split_service_env

load_split_service_env(service_name='ai-execution-service')

from platform_sdk.ai_runtime import create_ai_flask_app
from platform_sdk.database_readiness import make_sqlalchemy_readiness_check
from platform_sdk.learner_profile_application_support import (
    build_learner_profile_response as build_local_learner_profile_response,
)
from platform_sdk.learning_core_internal_client import (
    fetch_learning_core_context_payload,
    fetch_learning_core_learning_stats_response,
)
from platform_sdk.service_app import create_service_app

ai_flask_app = create_ai_flask_app()

app = create_service_app(
    service_name='ai-execution-service',
    version='0.1.0',
    readiness_checks={
        'database': make_sqlalchemy_readiness_check(ai_flask_app.config['SQLALCHEMY_DATABASE_URI']),
    },
    extra_health={'ai_compatibility': True},
)


@app.get('/internal/ops/ai-dependencies')
def get_ai_dependency_probe(user_id: int = Query(default=1, ge=1)):
    checks: dict[str, bool] = {}
    errors: dict[str, str] = {}
    with ai_flask_app.app_context():
        try:
            _payload, status = fetch_learning_core_learning_stats_response(
                user_id,
                days=7,
                book_id_filter=None,
                mode_filter_raw=None,
            )
            checks['learning_stats'] = status == 200
        except Exception as exc:
            checks['learning_stats'] = False
            errors['learning_stats'] = str(exc)
        try:
            fetch_learning_core_context_payload(user_id)
            checks['learner_profile_context'] = True
        except Exception as exc:
            checks['learner_profile_context'] = False
            errors['learner_profile_context'] = str(exc)
        try:
            profile_payload, profile_status = build_local_learner_profile_response(
                user_id,
                target_date=None,
                view='stats',
            )
            checks['learner_profile_stats'] = profile_status == 200 and isinstance(profile_payload, dict)
        except Exception as exc:
            checks['learner_profile_stats'] = False
            errors['learner_profile_stats'] = str(exc)
    status_code = 200 if all(checks.values()) else 503
    return JSONResponse(
        status_code=status_code,
        content={
            'status': 'ready' if status_code == 200 else 'not_ready',
            'service': 'ai-execution-service',
            'dependencies': checks,
            'errors': errors,
        },
    )


app.mount('/', WSGIMiddleware(ai_flask_app))


if __name__ == '__main__':
    import uvicorn

    uvicorn.run(app, host='0.0.0.0', port=int(os.environ.get('AI_EXECUTION_SERVICE_PORT', '8104')))
