from __future__ import annotations

from datetime import datetime

from platform_sdk.outbox_runtime import queue_outbox_event
from service_models.ai_execution_models import AIPromptRun
from service_models.eventing_models import AIExecutionOutboxEvent


AI_EXECUTION_SERVICE_NAME = 'ai-execution-service'
AI_PROMPT_RUN_COMPLETED_TOPIC = 'ai.prompt_run.completed'
_PROMPT_EXCERPT_LIMIT = 500


def _query_session(model):
    return model.query.session


def _normalize_text(value, *, limit: int = _PROMPT_EXCERPT_LIMIT):
    text = str(value or '').strip()
    if not text:
        return None
    return text[:limit]


def _normalize_value(value):
    text = str(value or '').strip()
    return text or None


def _normalize_dt(value):
    if isinstance(value, datetime):
        return value
    if isinstance(value, str) and value.strip():
        return datetime.fromisoformat(value.replace('Z', '+00:00')).replace(tzinfo=None)
    return datetime.utcnow()


def _normalize_user_id(value):
    if value in (None, ''):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def build_ai_prompt_run_completed_payload(prompt_run: AIPromptRun) -> dict:
    payload = {
        'prompt_run_id': prompt_run.id,
        'user_id': prompt_run.user_id,
        'run_kind': prompt_run.run_kind,
        'provider': prompt_run.provider,
        'model': prompt_run.model,
        'prompt_excerpt': prompt_run.prompt_excerpt,
        'response_excerpt': prompt_run.response_excerpt,
        'result_ref': prompt_run.result_ref,
        'completed_at': prompt_run.completed_at.isoformat() if prompt_run.completed_at else None,
    }
    metadata = prompt_run.metadata_dict()
    if metadata:
        payload['metadata'] = metadata
    return payload


def record_ai_prompt_run_completion(
    *,
    user_id: int | str | None,
    run_kind: str,
    prompt_excerpt: str | None = None,
    response_excerpt: str | None = None,
    result_ref: str | None = None,
    provider: str | None = None,
    model: str | None = None,
    metadata: dict | None = None,
    completed_at: datetime | str | None = None,
    headers: dict | None = None,
    event_id: str | None = None,
    session=None,
) -> AIPromptRun:
    session = session or _query_session(AIPromptRun)
    resolved_run_kind = _normalize_value(run_kind)
    if not resolved_run_kind:
        raise ValueError('ai prompt run completion must include run_kind')

    prompt_run = AIPromptRun(
        user_id=_normalize_user_id(user_id),
        run_kind=resolved_run_kind,
        provider=_normalize_value(provider),
        model=_normalize_value(model),
        prompt_excerpt=_normalize_text(prompt_excerpt),
        response_excerpt=_normalize_text(response_excerpt),
        result_ref=_normalize_value(result_ref),
        completed_at=_normalize_dt(completed_at),
    )
    prompt_run.set_metadata(metadata)
    session.add(prompt_run)
    session.flush()

    queue_outbox_event(
        AIExecutionOutboxEvent,
        producer_service=AI_EXECUTION_SERVICE_NAME,
        topic=AI_PROMPT_RUN_COMPLETED_TOPIC,
        aggregate_id=str(prompt_run.id),
        payload=build_ai_prompt_run_completed_payload(prompt_run),
        headers=headers,
        event_id=event_id,
        session=session,
    )
    session.commit()
    return prompt_run
