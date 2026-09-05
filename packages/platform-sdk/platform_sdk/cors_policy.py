from __future__ import annotations

import os
from collections.abc import Mapping


PUBLIC_WEB_ORIGINS = (
    'https://axiomaticworld.com',
    'https://www.axiomaticworld.com',
)
LOCAL_DEV_ORIGINS = (
    'http://axiomaticworld.com',
    'http://www.axiomaticworld.com',
    'http://localhost:5173',
    'http://127.0.0.1:5173',
    'http://localhost:3000',
    'http://127.0.0.1:3000',
    'http://localhost:3020',
    'http://127.0.0.1:3020',
    'http://localhost:3002',
    'http://127.0.0.1:3002',
    'http://localhost:4173',
    'http://127.0.0.1:4173',
)
PRODUCTION_ENV_NAMES = {'prod', 'production'}


def _split_csv(raw_value: str) -> list[str]:
    return [item.strip() for item in raw_value.split(',') if item.strip()]


def _env_flag(environ: Mapping[str, str], name: str) -> bool:
    return (environ.get(name) or '').strip().lower() in {'1', 'true', 'yes', 'on'}


def is_production_like_cors_runtime(environ: Mapping[str, str] | None = None) -> bool:
    active_env = os.environ if environ is None else environ
    app_env = (
        active_env.get('APP_ENV')
        or active_env.get('FLASK_ENV')
        or active_env.get('ENV')
        or ''
    ).strip().lower()
    return app_env in PRODUCTION_ENV_NAMES or _env_flag(active_env, 'COOKIE_SECURE')


def build_cors_origins(environ: Mapping[str, str] | None = None) -> list[str]:
    active_env = os.environ if environ is None else environ
    configured = _split_csv(active_env.get('CORS_ORIGINS', ''))
    production_like = is_production_like_cors_runtime(active_env)

    if '*' in configured:
        if production_like:
            raise ValueError('CORS_ORIGINS=* is not allowed when APP_ENV is production or COOKIE_SECURE=true')
        return ['*']

    configured_public = _split_csv(active_env.get('PUBLIC_WEB_ORIGINS', ''))
    defaults = configured_public or list(PUBLIC_WEB_ORIGINS)
    include_local_defaults = (
        not production_like
        or _env_flag(active_env, 'CORS_INCLUDE_LOCAL_DEV_ORIGINS')
    )
    if include_local_defaults:
        defaults.extend(LOCAL_DEV_ORIGINS)

    merged: list[str] = []
    for origin in [*configured, *defaults]:
        if origin and origin not in merged:
            merged.append(origin)
    return merged


def build_socketio_cors_allowed_origins(environ: Mapping[str, str] | None = None) -> list[str] | str:
    origins = build_cors_origins(environ)
    return '*' if origins == ['*'] else origins
