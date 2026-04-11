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
    AdminProjectedUser,
    AdminProjectionCursor,
)


ADMIN_OPS_SERVICE_NAME = 'admin-ops-service'
IDENTITY_USER_REGISTERED_TOPIC = 'identity.user.registered'
USER_DIRECTORY_PROJECTION = 'admin.user-directory'
USER_REGISTERED_QUEUE = f'{ADMIN_OPS_SERVICE_NAME}.{IDENTITY_USER_REGISTERED_TOPIC}'


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


def _parse_created_at(value) -> datetime:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str) and value.strip():
        return datetime.fromisoformat(value.replace('Z', '+00:00')).replace(tzinfo=None)
    return datetime.utcnow()


def _projection_cursor(session):
    cursor = AdminProjectionCursor.query.filter_by(projection_name=USER_DIRECTORY_PROJECTION).first()
    if cursor is None:
        cursor = AdminProjectionCursor(projection_name=USER_DIRECTORY_PROJECTION)
        session.add(cursor)
    return cursor


def upsert_projected_user(payload: dict, *, session=None) -> AdminProjectedUser:
    session = session or _query_session(AdminProjectedUser)
    user_id = int(payload.get('user_id') or 0)
    username = (payload.get('username') or '').strip()
    if user_id <= 0:
        raise ValueError('identity.user.registered payload must include user_id')
    if not username:
        raise ValueError('identity.user.registered payload must include username')

    record = session.get(AdminProjectedUser, user_id)
    if record is None:
        record = AdminProjectedUser(id=user_id, created_at=_parse_created_at(payload.get('created_at')))

    record.email = (payload.get('email') or '').strip() or None
    record.username = username
    record.avatar_url = payload.get('avatar_url')
    record.is_admin = bool(payload.get('is_admin', False))
    record.created_at = _parse_created_at(payload.get('created_at'))
    record.projected_at = datetime.utcnow()
    session.add(record)
    return record


def consume_identity_user_registered_event(
    *,
    event_id: str,
    producer_service: str,
    payload: dict,
    headers: dict | None = None,
    session=None,
) -> tuple[AdminProjectedUser, bool]:
    session = session or _query_session(AdminProjectedUser)
    inbox_record, created = register_inbox_event(
        AdminOpsInboxEvent,
        consumer_service=ADMIN_OPS_SERVICE_NAME,
        event_id=event_id,
        topic=IDENTITY_USER_REGISTERED_TOPIC,
        producer_service=producer_service,
        payload=payload,
        headers=headers,
        session=session,
    )
    if inbox_record.status == 'processed':
        existing = session.get(AdminProjectedUser, int(payload.get('user_id') or 0))
        if existing is None:
            raise RuntimeError('processed inbox event is missing projected user state')
        return existing, False

    begin_inbox_processing(inbox_record)
    try:
        projected_user = upsert_projected_user(payload, session=session)
        cursor = _projection_cursor(session)
        cursor.last_event_id = event_id
        cursor.last_topic = IDENTITY_USER_REGISTERED_TOPIC
        cursor.last_processed_at = datetime.utcnow()
        mark_inbox_event_processed(inbox_record)
        session.commit()
        return projected_user, created
    except Exception as exc:
        mark_inbox_event_failed(inbox_record, error_message=str(exc))
        session.commit()
        raise


def drain_identity_user_registered_queue(*, limit: int = 50, connection=None) -> int:
    close_connection = connection is None
    connection = connection or build_blocking_connection(service_name=ADMIN_OPS_SERVICE_NAME)
    channel = connection.channel()
    exchange_name = resolve_domain_exchange_name(service_name=ADMIN_OPS_SERVICE_NAME)
    channel.exchange_declare(exchange=exchange_name, exchange_type='topic', durable=True)
    channel.queue_declare(queue=USER_REGISTERED_QUEUE, durable=True)
    channel.queue_bind(
        exchange=exchange_name,
        queue=USER_REGISTERED_QUEUE,
        routing_key=IDENTITY_USER_REGISTERED_TOPIC,
    )

    processed = 0
    try:
        while processed < max(1, limit):
            method_frame, properties, body = channel.basic_get(queue=USER_REGISTERED_QUEUE, auto_ack=False)
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

                consume_identity_user_registered_event(
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
