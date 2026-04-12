from __future__ import annotations

import os

import requests
from flask import current_app

from platform_sdk.internal_service_auth import create_internal_auth_headers_for_user


DEFAULT_IDENTITY_SERVICE_URL = 'http://127.0.0.1:8101'
DEFAULT_TIMEOUT_SECONDS = 5.0
ADMIN_OPS_SERVICE_NAME = 'admin-ops-service'


def identity_service_url() -> str:
    return (os.environ.get('IDENTITY_SERVICE_URL') or DEFAULT_IDENTITY_SERVICE_URL).rstrip('/')


def _internal_admin_headers(admin_user_id: int) -> dict[str, str]:
    app = current_app._get_current_object()
    return create_internal_auth_headers_for_user(
        source_service_name=ADMIN_OPS_SERVICE_NAME,
        user_id=admin_user_id,
        is_admin=True,
        scopes=('admin', 'user'),
        env=app.config,
    )


def set_identity_user_admin(
    *,
    admin_user_id: int,
    target_user_id: int,
    is_admin: bool,
) -> tuple[dict, int]:
    response = requests.post(
        f'{identity_service_url()}/internal/identity/admin/users/{target_user_id}/set-admin',
        headers=_internal_admin_headers(admin_user_id),
        json={'is_admin': bool(is_admin)},
        timeout=DEFAULT_TIMEOUT_SECONDS,
    )
    try:
        payload = response.json()
    except ValueError:
        payload = {'error': response.text or 'invalid upstream response'}
    if response.status_code == 404 and payload.get('error') != '用户不存在':
        raise RuntimeError('identity admin set-admin route unavailable: 404')
    if response.status_code in {401, 403} or response.status_code >= 500:
        raise RuntimeError(f'identity admin set-admin request failed: {response.status_code}')
    return payload, response.status_code
