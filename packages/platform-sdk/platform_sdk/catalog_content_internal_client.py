from __future__ import annotations

import os
import uuid

import requests
from flask import current_app

from platform_sdk.internal_service_auth import (
    INTERNAL_SERVICE_AUTH_HEADER,
    REQUEST_ID_HEADER,
    SERVICE_NAME_HEADER,
    TRACE_ID_HEADER,
    create_internal_service_token,
    internal_service_secret,
    internal_service_token_ttl_seconds,
)


DEFAULT_CATALOG_CONTENT_SERVICE_URL = 'http://127.0.0.1:8103'
DEFAULT_TIMEOUT_SECONDS = 5.0
AI_EXECUTION_SERVICE_NAME = 'ai-execution-service'


def catalog_content_service_url() -> str:
    return (os.environ.get('CATALOG_CONTENT_SERVICE_URL') or DEFAULT_CATALOG_CONTENT_SERVICE_URL).rstrip('/')


def _internal_headers_for_user(user_id: int) -> dict[str, str]:
    app = current_app._get_current_object()
    request_id = uuid.uuid4().hex
    trace_id = request_id
    secret = internal_service_secret(env=app.config)
    token = create_internal_service_token(
        secret=secret,
        source_service_name=AI_EXECUTION_SERVICE_NAME,
        user_id=user_id,
        request_id=request_id,
        trace_id=trace_id,
        ttl_seconds=internal_service_token_ttl_seconds(env=app.config),
    )
    return {
        INTERNAL_SERVICE_AUTH_HEADER: token,
        REQUEST_ID_HEADER: request_id,
        TRACE_ID_HEADER: trace_id,
        SERVICE_NAME_HEADER: AI_EXECUTION_SERVICE_NAME,
    }


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


def create_catalog_content_custom_book_internal_response(
    user_id: int,
    data: dict | None,
) -> tuple[dict, int]:
    return _request_json(
        'POST',
        '/internal/catalog/custom-books',
        user_id=user_id,
        json_body=data if isinstance(data, dict) else {},
    )


def list_catalog_content_custom_books_internal_response(user_id: int) -> tuple[dict, int]:
    return _request_json(
        'GET',
        '/internal/catalog/custom-books',
        user_id=user_id,
    )


def get_catalog_content_custom_book_internal_response(user_id: int, book_id: str) -> tuple[dict, int]:
    return _request_json(
        'GET',
        f'/internal/catalog/custom-books/{book_id}',
        user_id=user_id,
    )
