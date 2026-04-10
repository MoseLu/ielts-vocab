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


def start_learning_core_study_session_response(user_id: int, data: dict | None) -> tuple[dict, int]:
    return _request_json(
        'POST',
        '/internal/learning/study-sessions/start',
        user_id=user_id,
        json_body=data if isinstance(data, dict) else {},
    )


def log_learning_core_study_session_response(user_id: int, data: dict | None) -> tuple[dict, int]:
    return _request_json(
        'POST',
        '/internal/learning/study-sessions/log',
        user_id=user_id,
        json_body=data if isinstance(data, dict) else {},
    )


def cancel_learning_core_study_session_response(user_id: int, session_id) -> tuple[dict, int]:
    return _request_json(
        'POST',
        '/internal/learning/study-sessions/cancel',
        user_id=user_id,
        json_body={'sessionId': session_id},
    )


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


def fetch_learning_core_wrong_words_for_ai(
    user_id: int,
    *,
    limit: int,
    query: str,
    recent_first: bool,
) -> list[dict]:
    payload, status = _request_json(
        'GET',
        '/internal/learning/ai-tool/wrong-words',
        user_id=user_id,
        params={
            'limit': max(1, min(300, int(limit or 12))),
            'query': query,
            'recent_first': 'true' if recent_first else 'false',
        },
    )
    if status != 200:
        raise RuntimeError(f'learning-core wrong-words request failed: {status}')
    return [item for item in (payload.get('words') or []) if isinstance(item, dict)]


def fetch_learning_core_chapter_progress_for_ai(user_id: int, *, book_id: str) -> list[dict]:
    payload, status = _request_json(
        'GET',
        '/internal/learning/ai-tool/chapter-progress',
        user_id=user_id,
        params={'book_id': book_id},
    )
    if status != 200:
        raise RuntimeError(f'learning-core chapter-progress request failed: {status}')
    return [item for item in (payload.get('progress') or []) if isinstance(item, dict)]


def fetch_learning_core_wrong_word_count(user_id: int) -> int:
    payload, status = _request_json(
        'GET',
        '/internal/learning/ai-tool/wrong-word-count',
        user_id=user_id,
    )
    if status != 200:
        raise RuntimeError(f'learning-core wrong-word-count request failed: {status}')
    return int(payload.get('count') or 0)


def fetch_learning_core_quick_memory_records_response(user_id: int) -> dict:
    payload, status = _request_json(
        'GET',
        '/internal/learning/quick-memory',
        user_id=user_id,
    )
    if status != 200:
        raise RuntimeError(f'learning-core quick-memory request failed: {status}')
    return payload


def fetch_learning_core_quick_memory_review_queue_response(user_id: int, args) -> dict:
    payload, status = _request_json(
        'GET',
        '/internal/learning/quick-memory/review-queue',
        user_id=user_id,
        params={
            'limit': args.get('limit'),
            'offset': args.get('offset'),
            'within_days': args.get('within_days'),
            'scope': args.get('scope'),
            'book_id': args.get('book_id'),
            'chapter_id': args.get('chapter_id'),
        },
    )
    if status != 200:
        raise RuntimeError(f'learning-core quick-memory review queue request failed: {status}')
    return payload


def sync_learning_core_quick_memory(user_id: int, data: dict | None) -> dict:
    payload, status = _request_json(
        'POST',
        '/internal/learning/quick-memory/sync',
        user_id=user_id,
        json_body=data if isinstance(data, dict) else {},
    )
    if status != 200:
        raise RuntimeError(f'learning-core quick-memory sync request failed: {status}')
    return payload


def fetch_learning_core_smart_stats_response(user_id: int) -> dict:
    payload, status = _request_json(
        'GET',
        '/internal/learning/smart-stats',
        user_id=user_id,
    )
    if status != 200:
        raise RuntimeError(f'learning-core smart-stats request failed: {status}')
    return payload


def sync_learning_core_smart_stats(user_id: int, data: dict | None) -> dict:
    payload, status = _request_json(
        'POST',
        '/internal/learning/smart-stats/sync',
        user_id=user_id,
        json_body=data if isinstance(data, dict) else {},
    )
    if status != 200:
        raise RuntimeError(f'learning-core smart-stats sync request failed: {status}')
    return payload


def fetch_learning_core_wrong_words_response(
    user_id: int,
    *,
    search_value=None,
    detail_mode=None,
) -> dict:
    payload, status = _request_json(
        'GET',
        '/internal/learning/wrong-words',
        user_id=user_id,
        params={
            'search': search_value,
            'details': detail_mode,
        },
    )
    if status != 200:
        raise RuntimeError(f'learning-core wrong-words request failed: {status}')
    return payload


def sync_learning_core_wrong_words(user_id: int, data: dict | None) -> dict:
    payload, status = _request_json(
        'POST',
        '/internal/learning/wrong-words/sync',
        user_id=user_id,
        json_body=data if isinstance(data, dict) else {},
    )
    if status != 200:
        raise RuntimeError(f'learning-core wrong-words sync request failed: {status}')
    return payload


def clear_learning_core_wrong_words(user_id: int, *, word: str | None = None) -> dict:
    payload, status = _request_json(
        'POST',
        '/internal/learning/wrong-words/clear',
        user_id=user_id,
        json_body={'word': word} if word else {},
    )
    if status != 200:
        raise RuntimeError(f'learning-core wrong-words clear request failed: {status}')
    return payload
