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
    AdminProjectedTTSMedia,
    AdminProjectionCursor,
)


ADMIN_OPS_SERVICE_NAME = 'admin-ops-service'
TTS_MEDIA_GENERATED_TOPIC = 'tts.media.generated'
TTS_MEDIA_PROJECTION = 'admin.tts-media-directory'
TTS_MEDIA_QUEUE = f'{ADMIN_OPS_SERVICE_NAME}.{TTS_MEDIA_GENERATED_TOPIC}'


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
        projection_name=TTS_MEDIA_PROJECTION
    ).first()
    if cursor is None:
        cursor = AdminProjectionCursor(projection_name=TTS_MEDIA_PROJECTION)
        session.add(cursor)
    return cursor


def upsert_projected_tts_media(
    *,
    event_id: str,
    payload: dict,
    session=None,
) -> AdminProjectedTTSMedia:
    session = session or _query_session(AdminProjectedTTSMedia)
    media_kind = str(payload.get('media_kind') or '').strip()
    media_id = str(payload.get('media_id') or '').strip()
    if not media_kind:
        raise ValueError('tts.media.generated payload must include media_kind')
    if not media_id:
        raise ValueError('tts.media.generated payload must include media_id')

    record = session.query(AdminProjectedTTSMedia).filter_by(event_id=event_id).first()
    if record is None:
        record = AdminProjectedTTSMedia(event_id=event_id, media_kind=media_kind, media_id=media_id)

    user_id = payload.get('user_id')
    record.event_id = event_id
    record.user_id = int(user_id) if user_id not in (None, '') else None
    record.media_kind = media_kind
    record.media_id = media_id
    record.tts_provider = (payload.get('tts_provider') or None) or None
    record.storage_provider = (payload.get('storage_provider') or None) or None
    record.model = (payload.get('model') or None) or None
    record.voice = (payload.get('voice') or None) or None
    record.byte_length = int(payload.get('byte_length') or 0)
    record.generated_at = _parse_dt(payload.get('generated_at'))
    record.projected_at = datetime.utcnow()
    session.add(record)
    return record


def consume_tts_media_generated_event(
    *,
    event_id: str,
    producer_service: str,
    payload: dict,
    headers: dict | None = None,
    session=None,
) -> tuple[AdminProjectedTTSMedia, bool]:
    session = session or _query_session(AdminProjectedTTSMedia)
    inbox_record, created = register_inbox_event(
        AdminOpsInboxEvent,
        consumer_service=ADMIN_OPS_SERVICE_NAME,
        event_id=event_id,
        topic=TTS_MEDIA_GENERATED_TOPIC,
        producer_service=producer_service,
        payload=payload,
        headers=headers,
        session=session,
    )
    if inbox_record.status == 'processed':
        existing = session.query(AdminProjectedTTSMedia).filter_by(event_id=event_id).first()
        if existing is None:
            raise RuntimeError('processed inbox event is missing projected tts media state')
        return existing, False

    begin_inbox_processing(inbox_record)
    try:
        projected_record = upsert_projected_tts_media(
            event_id=event_id,
            payload=payload,
            session=session,
        )
        cursor = _projection_cursor(session)
        cursor.last_event_id = event_id
        cursor.last_topic = TTS_MEDIA_GENERATED_TOPIC
        cursor.last_processed_at = datetime.utcnow()
        mark_inbox_event_processed(inbox_record)
        session.commit()
        return projected_record, created
    except Exception as exc:
        mark_inbox_event_failed(inbox_record, error_message=str(exc))
        session.commit()
        raise


def drain_tts_media_generated_queue(*, limit: int = 50, connection=None) -> int:
    close_connection = connection is None
    connection = connection or build_blocking_connection(service_name=ADMIN_OPS_SERVICE_NAME)
    channel = connection.channel()
    exchange_name = resolve_domain_exchange_name(service_name=ADMIN_OPS_SERVICE_NAME)
    channel.exchange_declare(exchange=exchange_name, exchange_type='topic', durable=True)
    channel.queue_declare(queue=TTS_MEDIA_QUEUE, durable=True)
    channel.queue_bind(
        exchange=exchange_name,
        queue=TTS_MEDIA_QUEUE,
        routing_key=TTS_MEDIA_GENERATED_TOPIC,
    )

    processed = 0
    try:
        while processed < max(1, limit):
            method_frame, properties, body = channel.basic_get(queue=TTS_MEDIA_QUEUE, auto_ack=False)
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

                consume_tts_media_generated_event(
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
