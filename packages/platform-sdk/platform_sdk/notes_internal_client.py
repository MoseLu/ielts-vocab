from __future__ import annotations

import os
import uuid
from dataclasses import dataclass
from datetime import datetime

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


DEFAULT_NOTES_SERVICE_URL = 'http://127.0.0.1:8107'
DEFAULT_TIMEOUT_SECONDS = 5.0
AI_EXECUTION_SERVICE_NAME = 'ai-execution-service'


@dataclass(frozen=True)
class LearningNoteSnapshot:
    id: int
    question: str
    answer: str
    word_context: str | None
    created_at: datetime | None


@dataclass(frozen=True)
class DailySummarySnapshot:
    id: int
    date: str
    content: str
    generated_at: datetime | None


def notes_service_url() -> str:
    return (os.environ.get('NOTES_SERVICE_URL') or DEFAULT_NOTES_SERVICE_URL).rstrip('/')


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
        f'{notes_service_url()}{path}',
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


def _parse_optional_datetime(value) -> datetime | None:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str) and value:
        try:
            return datetime.fromisoformat(value.replace('Z', '+00:00'))
        except ValueError:
            return None
    return None


def _deserialize_learning_note(payload: dict) -> LearningNoteSnapshot:
    return LearningNoteSnapshot(
        id=int(payload.get('id') or 0),
        question=str(payload.get('question') or ''),
        answer=str(payload.get('answer') or ''),
        word_context=(str(payload.get('word_context') or '').strip() or None),
        created_at=_parse_optional_datetime(payload.get('created_at')),
    )


def _deserialize_daily_summary(payload: dict) -> DailySummarySnapshot:
    return DailySummarySnapshot(
        id=int(payload.get('id') or 0),
        date=str(payload.get('date') or ''),
        content=str(payload.get('content') or ''),
        generated_at=_parse_optional_datetime(payload.get('generated_at')),
    )


def list_recent_learning_notes(user_id: int, *, limit: int = 80) -> list[LearningNoteSnapshot]:
    payload, status = _request_json(
        'GET',
        '/internal/notes/learning-notes',
        user_id=user_id,
        params={'limit': max(1, min(200, int(limit or 80))), 'descending': 'true'},
    )
    if status != 200:
        raise RuntimeError(f'notes learning-notes request failed: {status}')
    return [
        _deserialize_learning_note(item)
        for item in (payload.get('notes') or [])
        if isinstance(item, dict)
    ]


def list_recent_daily_summaries(user_id: int, *, limit: int = 14) -> list[DailySummarySnapshot]:
    payload, status = _request_json(
        'GET',
        '/internal/notes/summaries',
        user_id=user_id,
        params={'limit': max(1, min(60, int(limit or 14))), 'descending': 'true'},
    )
    if status != 200:
        raise RuntimeError(f'notes summaries request failed: {status}')
    return [
        _deserialize_daily_summary(item)
        for item in (payload.get('summaries') or [])
        if isinstance(item, dict)
    ]


def create_learning_note(
    user_id: int,
    *,
    question: str,
    answer: str,
    word_context: str | None,
) -> dict:
    payload, status = _request_json(
        'POST',
        '/internal/notes/learning-notes',
        user_id=user_id,
        json_body={
            'question': question,
            'answer': answer,
            'word_context': word_context,
        },
    )
    if status != 201:
        raise RuntimeError(f'notes learning-note create failed: {status}')
    return payload.get('note') if isinstance(payload.get('note'), dict) else payload
