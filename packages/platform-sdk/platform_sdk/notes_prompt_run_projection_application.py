from __future__ import annotations

import json
from datetime import datetime

from platform_sdk.outbox_runtime import (
    begin_inbox_processing,
    mark_inbox_event_failed,
    mark_inbox_event_processed,
    register_inbox_event,
)
from platform_sdk.rabbitmq_runtime import (
    build_blocking_connection,
    resolve_domain_exchange_name,
)
from service_models.eventing_models import NotesInboxEvent
from service_models.notes_models import NotesProjectedPromptRun


NOTES_SERVICE_NAME = 'notes-service'
AI_PROMPT_RUN_COMPLETED_TOPIC = 'ai.prompt_run.completed'
NOTES_PROMPT_RUN_QUEUE = f'{NOTES_SERVICE_NAME}.{AI_PROMPT_RUN_COMPLETED_TOPIC}'


def _query_session(model):
    return model.query.session


def _json_loads(value):
    if not value:
        return {}
    if isinstance(value, (bytes, bytearray)):
        value = value.decode('utf-8')
    if isinstance(value, (dict, list)):
        return value
    return json.loads(value)


def _parse_dt(value) -> datetime:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str) and value.strip():
        return datetime.fromisoformat(value.replace('Z', '+00:00')).replace(tzinfo=None)
    return datetime.utcnow()


def upsert_notes_projected_prompt_run(
    payload: dict,
    *,
    event_id: str,
    session=None,
) -> NotesProjectedPromptRun:
    session = session or _query_session(NotesProjectedPromptRun)
    prompt_run_id = int(payload.get('prompt_run_id') or 0)
    if prompt_run_id <= 0:
        raise ValueError('ai.prompt_run.completed payload must include prompt_run_id')

    record = session.get(NotesProjectedPromptRun, prompt_run_id)
    if record is None:
        record = NotesProjectedPromptRun(
            id=prompt_run_id,
            event_id=event_id,
            completed_at=_parse_dt(payload.get('completed_at')),
            run_kind=str(payload.get('run_kind') or '').strip(),
        )

    record.event_id = event_id
    record.user_id = int(payload.get('user_id') or 0) or None
    record.run_kind = str(payload.get('run_kind') or '').strip()
    record.provider = str(payload.get('provider') or '').strip() or None
    record.model = str(payload.get('model') or '').strip() or None
    record.prompt_excerpt = str(payload.get('prompt_excerpt') or '').strip() or None
    record.response_excerpt = str(payload.get('response_excerpt') or '').strip() or None
    record.result_ref = str(payload.get('result_ref') or '').strip() or None
    record.completed_at = _parse_dt(payload.get('completed_at'))
    record.projected_at = datetime.utcnow()
    session.add(record)
    return record


def consume_notes_ai_prompt_run_completed_event(
    *,
    event_id: str,
    producer_service: str,
    payload: dict,
    headers: dict | None = None,
    session=None,
) -> tuple[NotesProjectedPromptRun, bool]:
    session = session or _query_session(NotesProjectedPromptRun)
    inbox_record, created = register_inbox_event(
        NotesInboxEvent,
        consumer_service=NOTES_SERVICE_NAME,
        event_id=event_id,
        topic=AI_PROMPT_RUN_COMPLETED_TOPIC,
        producer_service=producer_service,
        payload=payload,
        headers=headers,
        session=session,
    )
    if inbox_record.status == 'processed':
        existing = session.get(NotesProjectedPromptRun, int(payload.get('prompt_run_id') or 0))
        if existing is None:
            raise RuntimeError('processed inbox event is missing notes projected prompt run state')
        return existing, False

    begin_inbox_processing(inbox_record)
    try:
        projected_prompt_run = upsert_notes_projected_prompt_run(
            payload,
            event_id=event_id,
            session=session,
        )
        mark_inbox_event_processed(inbox_record)
        session.commit()
        return projected_prompt_run, created
    except Exception as exc:
        mark_inbox_event_failed(inbox_record, error_message=str(exc))
        session.commit()
        raise


def drain_notes_ai_prompt_run_completed_queue(*, limit: int = 50, connection=None) -> int:
    close_connection = connection is None
    connection = connection or build_blocking_connection(service_name=NOTES_SERVICE_NAME)
    channel = connection.channel()
    exchange_name = resolve_domain_exchange_name(service_name=NOTES_SERVICE_NAME)
    channel.exchange_declare(exchange=exchange_name, exchange_type='topic', durable=True)
    channel.queue_declare(queue=NOTES_PROMPT_RUN_QUEUE, durable=True)
    channel.queue_bind(
        exchange=exchange_name,
        queue=NOTES_PROMPT_RUN_QUEUE,
        routing_key=AI_PROMPT_RUN_COMPLETED_TOPIC,
    )

    processed = 0
    try:
        while processed < max(1, limit):
            method_frame, properties, body = channel.basic_get(
                queue=NOTES_PROMPT_RUN_QUEUE,
                auto_ack=False,
            )
            if method_frame is None:
                break

            try:
                headers = dict(getattr(properties, 'headers', None) or {})
                event_id = getattr(properties, 'message_id', None) or headers.get('event_id') or ''
                producer_service = headers.get('producer_service') or ''
                if not event_id:
                    raise ValueError('domain event message is missing event_id')
                if not producer_service:
                    raise ValueError('domain event message is missing producer_service')

                consume_notes_ai_prompt_run_completed_event(
                    event_id=event_id,
                    producer_service=producer_service,
                    payload=_json_loads(body),
                    headers=headers,
                )
            except Exception:
                channel.basic_nack(method_frame.delivery_tag, requeue=True)
                raise
            else:
                channel.basic_ack(method_frame.delivery_tag)
                processed += 1

        return processed
    finally:
        if close_connection:
            connection.close()
