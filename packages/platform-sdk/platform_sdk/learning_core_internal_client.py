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


DEFAULT_LEARNING_CORE_SERVICE_URL = 'http://127.0.0.1:8102'
DEFAULT_TIMEOUT_SECONDS = 5.0
AI_EXECUTION_SERVICE_NAME = 'ai-execution-service'


def learning_core_service_url() -> str:
    return (os.environ.get('LEARNING_CORE_SERVICE_URL') or DEFAULT_LEARNING_CORE_SERVICE_URL).rstrip('/')


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
        f'{learning_core_service_url()}{path}',
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


def fetch_learning_core_context_payload(user_id: int) -> dict:
    payload, status = _request_json('GET', '/internal/learning/context', user_id=user_id)
    if status != 200:
        raise RuntimeError(f'learning-core context request failed: {status}')
    return payload


def fetch_learning_core_learning_stats_response(
    user_id: int,
    *,
    days: int,
    book_id_filter: str | None,
    mode_filter_raw: str | None,
) -> tuple[dict, int]:
    params = {'days': days}
    if book_id_filter:
        params['book_id'] = book_id_filter
    if mode_filter_raw:
        params['mode'] = mode_filter_raw
    return _request_json('GET', '/internal/learning/stats', user_id=user_id, params=params)


def record_learning_core_event(
    user_id: int,
    *,
    event_type: str,
    source: str,
    mode: str | None = None,
    book_id: str | None = None,
    chapter_id: str | None = None,
    word: str | None = None,
    item_count: int = 0,
    correct_count: int = 0,
    wrong_count: int = 0,
    duration_seconds: int = 0,
    payload: dict | None = None,
    occurred_at: str | None = None,
) -> dict:
    response_payload, status = _request_json(
        'POST',
        '/internal/learning/events',
        user_id=user_id,
        json_body={
            'event_type': event_type,
            'source': source,
            'mode': mode,
            'book_id': book_id,
            'chapter_id': chapter_id,
            'word': word,
            'item_count': item_count,
            'correct_count': correct_count,
            'wrong_count': wrong_count,
            'duration_seconds': duration_seconds,
            'payload': payload,
            'occurred_at': occurred_at,
        },
    )
    if status != 201:
        raise RuntimeError(f'learning-core event request failed: {status}')
    return response_payload.get('event') if isinstance(response_payload.get('event'), dict) else response_payload
