from __future__ import annotations

from datetime import datetime, timezone
from typing import Callable

from fastapi import FastAPI
from fastapi.responses import JSONResponse


ReadinessChecks = dict[str, Callable[[], bool]]


def create_service_app(
    *,
    service_name: str,
    version: str,
    readiness_checks: ReadinessChecks | None = None,
    extra_health: dict | None = None,
) -> FastAPI:
    app = FastAPI(title=service_name, version=version)
    checks = readiness_checks or {}
    health_payload = extra_health or {}
    app.state.readiness_checks = checks

    @app.get('/health')
    def health() -> dict:
        return {
            'status': 'ok',
            'service': service_name,
            'version': version,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            **health_payload,
        }

    @app.get('/ready')
    def ready():
        readiness_checks = getattr(app.state, 'readiness_checks', {})
        dependencies = {name: bool(check()) for name, check in readiness_checks.items()}
        is_ready = all(dependencies.values()) if dependencies else True
        payload = {
            'status': 'ready' if is_ready else 'not_ready',
            'service': service_name,
            'version': version,
            'dependencies': dependencies,
        }
        if is_ready:
            return payload
        return JSONResponse(status_code=503, content=payload)

    @app.get('/version')
    def service_version() -> dict:
        return {
            'service': service_name,
            'version': version,
        }

    return app
