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
    AdminProjectedStudySession,
    AdminProjectionCursor,
)


ADMIN_OPS_SERVICE_NAME = 'admin-ops-service'
LEARNING_SESSION_LOGGED_TOPIC = 'learning.session.logged'
STUDY_SESSION_ANALYTICS_PROJECTION = 'admin.study-session-analytics'
STUDY_SESSION_QUEUE = f'{ADMIN_OPS_SERVICE_NAME}.{LEARNING_SESSION_LOGGED_TOPIC}'


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


def _projection_cursor(session):
    cursor = AdminProjectionCursor.query.filter_by(
        projection_name=STUDY_SESSION_ANALYTICS_PROJECTION
    ).first()
    if cursor is None:
        cursor = AdminProjectionCursor(projection_name=STUDY_SESSION_ANALYTICS_PROJECTION)
        session.add(cursor)
    return cursor


def upsert_projected_study_session(payload: dict, *, session=None) -> AdminProjectedStudySession:
    session = session or _query_session(AdminProjectedStudySession)
    session_id = int(payload.get('session_id') or 0)
    user_id = int(payload.get('user_id') or 0)
    if session_id <= 0:
        raise ValueError('learning.session.logged payload must include session_id')
    if user_id <= 0:
        raise ValueError('learning.session.logged payload must include user_id')

    record = session.get(AdminProjectedStudySession, session_id)
    if record is None:
        record = AdminProjectedStudySession(id=session_id, user_id=user_id, started_at=_parse_dt(payload.get('started_at')))

    record.user_id = user_id
    record.mode = (payload.get('mode') or None)
    record.book_id = payload.get('book_id') or None
    record.chapter_id = payload.get('chapter_id') or None
    record.words_studied = int(payload.get('words_studied') or 0)
    record.correct_count = int(payload.get('correct_count') or 0)
    record.wrong_count = int(payload.get('wrong_count') or 0)
    record.duration_seconds = int(payload.get('duration_seconds') or 0)
    record.started_at = _parse_dt(payload.get('started_at'))
    record.ended_at = _parse_dt(payload.get('ended_at')) if payload.get('ended_at') else None
    record.projected_at = datetime.utcnow()
    session.add(record)
    return record


def consume_learning_session_logged_event(
    *,
    event_id: str,
    producer_service: str,
    payload: dict,
    headers: dict | None = None,
    session=None,
) -> tuple[AdminProjectedStudySession, bool]:
    session = session or _query_session(AdminProjectedStudySession)
    inbox_record, created = register_inbox_event(
        AdminOpsInboxEvent,
        consumer_service=ADMIN_OPS_SERVICE_NAME,
        event_id=event_id,
        topic=LEARNING_SESSION_LOGGED_TOPIC,
        producer_service=producer_service,
        payload=payload,
        headers=headers,
        session=session,
    )
    if inbox_record.status == 'processed':
        existing = session.get(AdminProjectedStudySession, int(payload.get('session_id') or 0))
        if existing is None:
            raise RuntimeError('processed inbox event is missing projected study session state')
        return existing, False

    begin_inbox_processing(inbox_record)
    try:
        projected_session = upsert_projected_study_session(payload, session=session)
        cursor = _projection_cursor(session)
        cursor.last_event_id = event_id
        cursor.last_topic = LEARNING_SESSION_LOGGED_TOPIC
        cursor.last_processed_at = datetime.utcnow()
        mark_inbox_event_processed(inbox_record)
        session.commit()
        return projected_session, created
    except Exception as exc:
        mark_inbox_event_failed(inbox_record, error_message=str(exc))
        session.commit()
        raise


def drain_learning_session_logged_queue(*, limit: int = 50, connection=None) -> int:
    close_connection = connection is None
    connection = connection or build_blocking_connection(service_name=ADMIN_OPS_SERVICE_NAME)
    channel = connection.channel()
    exchange_name = resolve_domain_exchange_name(service_name=ADMIN_OPS_SERVICE_NAME)
    channel.exchange_declare(exchange=exchange_name, exchange_type='topic', durable=True)
    channel.queue_declare(queue=STUDY_SESSION_QUEUE, durable=True)
    channel.queue_bind(
        exchange=exchange_name,
        queue=STUDY_SESSION_QUEUE,
        routing_key=LEARNING_SESSION_LOGGED_TOPIC,
    )

    processed = 0
    try:
        while processed < max(1, limit):
            method_frame, properties, body = channel.basic_get(queue=STUDY_SESSION_QUEUE, auto_ack=False)
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

                consume_learning_session_logged_event(
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
