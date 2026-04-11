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
from service_models.notes_models import NotesProjectedStudySession, NotesProjectionCursor


NOTES_SERVICE_NAME = 'notes-service'
LEARNING_SESSION_LOGGED_TOPIC = 'learning.session.logged'
NOTES_STUDY_SESSION_QUEUE = f'{NOTES_SERVICE_NAME}.{LEARNING_SESSION_LOGGED_TOPIC}'
NOTES_STUDY_SESSION_CONTEXT_PROJECTION = 'notes.study-session-context'


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


def _projection_cursor(session) -> NotesProjectionCursor:
    cursor = session.query(NotesProjectionCursor).filter_by(
        projection_name=NOTES_STUDY_SESSION_CONTEXT_PROJECTION
    ).first()
    if cursor is None:
        cursor = NotesProjectionCursor(projection_name=NOTES_STUDY_SESSION_CONTEXT_PROJECTION)
        session.add(cursor)
    return cursor


def upsert_notes_projected_study_session(payload: dict, *, session=None) -> NotesProjectedStudySession:
    session = session or _query_session(NotesProjectedStudySession)
    session_id = int(payload.get('session_id') or 0)
    user_id = int(payload.get('user_id') or 0)
    if session_id <= 0:
        raise ValueError('learning.session.logged payload must include session_id')
    if user_id <= 0:
        raise ValueError('learning.session.logged payload must include user_id')

    record = session.get(NotesProjectedStudySession, session_id)
    if record is None:
        record = NotesProjectedStudySession(
            id=session_id,
            user_id=user_id,
            started_at=_parse_dt(payload.get('started_at')),
        )

    record.user_id = user_id
    record.mode = payload.get('mode') or None
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


def consume_notes_learning_session_logged_event(
    *,
    event_id: str,
    producer_service: str,
    payload: dict,
    headers: dict | None = None,
    session=None,
) -> tuple[NotesProjectedStudySession, bool]:
    session = session or _query_session(NotesProjectedStudySession)
    inbox_record, created = register_inbox_event(
        NotesInboxEvent,
        consumer_service=NOTES_SERVICE_NAME,
        event_id=event_id,
        topic=LEARNING_SESSION_LOGGED_TOPIC,
        producer_service=producer_service,
        payload=payload,
        headers=headers,
        session=session,
    )
    if inbox_record.status == 'processed':
        existing = session.get(NotesProjectedStudySession, int(payload.get('session_id') or 0))
        if existing is None:
            raise RuntimeError('processed inbox event is missing notes projected study session state')
        return existing, False

    begin_inbox_processing(inbox_record)
    try:
        projected_session = upsert_notes_projected_study_session(payload, session=session)
        mark_inbox_event_processed(inbox_record)
        cursor = _projection_cursor(session)
        cursor.last_event_id = event_id
        cursor.last_topic = LEARNING_SESSION_LOGGED_TOPIC
        cursor.last_processed_at = datetime.utcnow()
        session.commit()
        return projected_session, created
    except Exception as exc:
        mark_inbox_event_failed(inbox_record, error_message=str(exc))
        session.commit()
        raise


def drain_notes_learning_session_logged_queue(*, limit: int = 50, connection=None) -> int:
    close_connection = connection is None
    connection = connection or build_blocking_connection(service_name=NOTES_SERVICE_NAME)
    channel = connection.channel()
    exchange_name = resolve_domain_exchange_name(service_name=NOTES_SERVICE_NAME)
    channel.exchange_declare(exchange=exchange_name, exchange_type='topic', durable=True)
    channel.queue_declare(queue=NOTES_STUDY_SESSION_QUEUE, durable=True)
    channel.queue_bind(
        exchange=exchange_name,
        queue=NOTES_STUDY_SESSION_QUEUE,
        routing_key=LEARNING_SESSION_LOGGED_TOPIC,
    )

    processed = 0
    try:
        while processed < max(1, limit):
            method_frame, properties, body = channel.basic_get(
                queue=NOTES_STUDY_SESSION_QUEUE,
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

                consume_notes_learning_session_logged_event(
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
