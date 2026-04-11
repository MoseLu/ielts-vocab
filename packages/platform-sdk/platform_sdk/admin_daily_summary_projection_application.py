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
from service_models.eventing_models import (
    AdminOpsInboxEvent,
    AdminProjectedDailySummary,
    AdminProjectionCursor,
)


ADMIN_OPS_SERVICE_NAME = 'admin-ops-service'
NOTES_SUMMARY_GENERATED_TOPIC = 'notes.summary.generated'
DAILY_SUMMARY_PROJECTION = 'admin.daily-summary-directory'
DAILY_SUMMARY_QUEUE = f'{ADMIN_OPS_SERVICE_NAME}.{NOTES_SUMMARY_GENERATED_TOPIC}'


def _query_session(model):
    return model.query.session


def _json_loads(value):
    if not value:
        return {}
    if isinstance(value, (bytes, bytearray)):
        value = value.decode('utf-8')
    if isinstance(value, dict):
        return value
    return json.loads(value)


def _parse_dt(value) -> datetime:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str) and value.strip():
        return datetime.fromisoformat(value.replace('Z', '+00:00')).replace(tzinfo=None)
    return datetime.utcnow()


def _projection_cursor(session):
    cursor = AdminProjectionCursor.query.filter_by(
        projection_name=DAILY_SUMMARY_PROJECTION
    ).first()
    if cursor is None:
        cursor = AdminProjectionCursor(projection_name=DAILY_SUMMARY_PROJECTION)
        session.add(cursor)
    return cursor


def upsert_projected_daily_summary(payload: dict, *, session=None) -> AdminProjectedDailySummary:
    session = session or _query_session(AdminProjectedDailySummary)
    summary_id = int(payload.get('summary_id') or 0)
    user_id = int(payload.get('user_id') or 0)
    target_date = (payload.get('date') or '').strip()
    if summary_id <= 0:
        raise ValueError('notes.summary.generated payload must include summary_id')
    if user_id <= 0:
        raise ValueError('notes.summary.generated payload must include user_id')
    if not target_date:
        raise ValueError('notes.summary.generated payload must include date')

    record = session.get(AdminProjectedDailySummary, summary_id)
    if record is None:
        record = AdminProjectedDailySummary(
            id=summary_id,
            user_id=user_id,
            date=target_date,
            generated_at=_parse_dt(payload.get('generated_at')),
        )

    record.user_id = user_id
    record.date = target_date
    record.content = payload.get('content') or ''
    record.generated_at = _parse_dt(payload.get('generated_at'))
    record.projected_at = datetime.utcnow()
    session.add(record)
    return record


def consume_notes_summary_generated_event(
    *,
    event_id: str,
    producer_service: str,
    payload: dict,
    headers: dict | None = None,
    session=None,
) -> tuple[AdminProjectedDailySummary, bool]:
    session = session or _query_session(AdminProjectedDailySummary)
    inbox_record, created = register_inbox_event(
        AdminOpsInboxEvent,
        consumer_service=ADMIN_OPS_SERVICE_NAME,
        event_id=event_id,
        topic=NOTES_SUMMARY_GENERATED_TOPIC,
        producer_service=producer_service,
        payload=payload,
        headers=headers,
        session=session,
    )
    if inbox_record.status == 'processed':
        existing = session.get(AdminProjectedDailySummary, int(payload.get('summary_id') or 0))
        if existing is None:
            raise RuntimeError('processed inbox event is missing projected daily summary state')
        return existing, False

    begin_inbox_processing(inbox_record)
    try:
        projected_summary = upsert_projected_daily_summary(payload, session=session)
        cursor = _projection_cursor(session)
        cursor.last_event_id = event_id
        cursor.last_topic = NOTES_SUMMARY_GENERATED_TOPIC
        cursor.last_processed_at = datetime.utcnow()
        mark_inbox_event_processed(inbox_record)
        session.commit()
        return projected_summary, created
    except Exception as exc:
        mark_inbox_event_failed(inbox_record, error_message=str(exc))
        session.commit()
        raise


def drain_notes_summary_generated_queue(*, limit: int = 50, connection=None) -> int:
    close_connection = connection is None
    connection = connection or build_blocking_connection(service_name=ADMIN_OPS_SERVICE_NAME)
    channel = connection.channel()
    exchange_name = resolve_domain_exchange_name(service_name=ADMIN_OPS_SERVICE_NAME)
    channel.exchange_declare(exchange=exchange_name, exchange_type='topic', durable=True)
    channel.queue_declare(queue=DAILY_SUMMARY_QUEUE, durable=True)
    channel.queue_bind(
        exchange=exchange_name,
        queue=DAILY_SUMMARY_QUEUE,
        routing_key=NOTES_SUMMARY_GENERATED_TOPIC,
    )

    processed = 0
    try:
        while processed < max(1, limit):
            method_frame, properties, body = channel.basic_get(queue=DAILY_SUMMARY_QUEUE, auto_ack=False)
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

                consume_notes_summary_generated_event(
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
