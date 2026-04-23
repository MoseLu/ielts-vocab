from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Callable

from starlette.applications import Starlette
from starlette.responses import JSONResponse as StarletteJSONResponse
from starlette.routing import Route

if TYPE_CHECKING:
    from fastapi import FastAPI
else:
    FastAPI = Any


ReadinessChecks = dict[str, Callable[[], bool]]


def create_service_app(
    *,
    service_name: str,
    version: str,
    readiness_checks: ReadinessChecks | None = None,
    extra_health: dict | None = None,
) -> FastAPI:
    from fastapi import FastAPI
    from fastapi.responses import JSONResponse

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


def create_service_shell_app(
    *,
    service_name: str,
    version: str,
    readiness_checks: ReadinessChecks | None = None,
    extra_health: dict | None = None,
) -> Starlette:
    checks = readiness_checks or {}
    health_payload = extra_health or {}

    async def health(_request) -> StarletteJSONResponse:
        return StarletteJSONResponse(
            {
                'status': 'ok',
                'service': service_name,
                'version': version,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                **health_payload,
            },
        )

    async def ready(request) -> StarletteJSONResponse:
        active_checks = getattr(request.app.state, 'readiness_checks', {})
        dependencies = {name: bool(check()) for name, check in active_checks.items()}
        is_ready = all(dependencies.values()) if dependencies else True
        payload = {
            'status': 'ready' if is_ready else 'not_ready',
            'service': service_name,
            'version': version,
            'dependencies': dependencies,
        }
        status_code = 200 if is_ready else 503
        return StarletteJSONResponse(payload, status_code=status_code)

    async def service_version(_request) -> StarletteJSONResponse:
        return StarletteJSONResponse(
            {
                'service': service_name,
                'version': version,
            },
        )

    app = Starlette(
        routes=[
            Route('/health', endpoint=health, methods=['GET']),
            Route('/ready', endpoint=ready, methods=['GET']),
            Route('/version', endpoint=service_version, methods=['GET']),
        ],
    )
    app.state.readiness_checks = checks
    return app
