from __future__ import annotations

import os

import requests
from flask import current_app

from platform_sdk.internal_service_auth import (
    create_internal_auth_headers_for_user,
)


DEFAULT_CATALOG_CONTENT_SERVICE_URL = 'http://127.0.0.1:8103'
DEFAULT_TIMEOUT_SECONDS = 5.0
AI_EXECUTION_SERVICE_NAME = 'ai-execution-service'


def catalog_content_service_url() -> str:
    return (os.environ.get('CATALOG_CONTENT_SERVICE_URL') or DEFAULT_CATALOG_CONTENT_SERVICE_URL).rstrip('/')


def _internal_headers_for_user(user_id: int) -> dict[str, str]:
    app = current_app._get_current_object()
    return create_internal_auth_headers_for_user(
        source_service_name=AI_EXECUTION_SERVICE_NAME,
        user_id=user_id,
        env=app.config,
    )


def _request_json(
    method: str,
    path: str,
    *,
    user_id: int,
    params: dict | None = None,
    json_body: dict | None = None,
) -> tuple[dict, int]:
    response = requests.request(
        method,
        f'{catalog_content_service_url()}{path}',
        params=params,
        json=json_body,
        headers=_internal_headers_for_user(user_id),
        timeout=DEFAULT_TIMEOUT_SECONDS,
    )
    try:
        payload = response.json()
    except ValueError:
        payload = {'error': response.text or 'invalid upstream response'}
    return payload, response.status_code


def _is_boundary_error_status(status: int) -> bool:
    return status in {401, 403, 404} or status >= 500


def create_catalog_content_custom_book_internal_response(
    user_id: int,
    data: dict | None,
) -> tuple[dict, int]:
    payload, status = _request_json(
        'POST',
        '/internal/catalog/custom-books',
        user_id=user_id,
        json_body=data if isinstance(data, dict) else {},
    )
    if _is_boundary_error_status(status):
        raise RuntimeError(f'catalog-content custom-book create request failed: {status}')
    return payload, status


def list_catalog_content_custom_books_internal_response(user_id: int) -> tuple[dict, int]:
    payload, status = _request_json(
        'GET',
        '/internal/catalog/custom-books',
        user_id=user_id,
    )
    if _is_boundary_error_status(status):
        raise RuntimeError(f'catalog-content custom-book list request failed: {status}')
    return payload, status


def get_catalog_content_custom_book_internal_response(user_id: int, book_id: str) -> tuple[dict, int]:
    payload, status = _request_json(
        'GET',
        f'/internal/catalog/custom-books/{book_id}',
        user_id=user_id,
    )
    if _is_boundary_error_status(status):
        raise RuntimeError(f'catalog-content custom-book read request failed: {status}')
    return payload, status
