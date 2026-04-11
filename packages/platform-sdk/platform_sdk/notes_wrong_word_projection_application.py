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
from service_models.notes_models import NotesProjectedWrongWord


NOTES_SERVICE_NAME = 'notes-service'
LEARNING_WRONG_WORD_UPDATED_TOPIC = 'learning.wrong_word.updated'
NOTES_WRONG_WORD_QUEUE = f'{NOTES_SERVICE_NAME}.{LEARNING_WRONG_WORD_UPDATED_TOPIC}'


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


def _json_dumps(value) -> str | None:
    if not value:
        return None
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False)


def _parse_dt(value) -> datetime:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str) and value.strip():
        return datetime.fromisoformat(value.replace('Z', '+00:00')).replace(tzinfo=None)
    return datetime.utcnow()


def _get_projected_wrong_word(session, *, user_id: int, word: str) -> NotesProjectedWrongWord | None:
    return session.query(NotesProjectedWrongWord).filter_by(user_id=user_id, word=word).first()


def upsert_notes_projected_wrong_word(payload: dict, *, session=None) -> NotesProjectedWrongWord:
    session = session or _query_session(NotesProjectedWrongWord)
    user_id = int(payload.get('user_id') or 0)
    word = str(payload.get('word') or '').strip()
    if user_id <= 0:
        raise ValueError('learning.wrong_word.updated payload must include user_id')
    if not word:
        raise ValueError('learning.wrong_word.updated payload must include word')

    record = _get_projected_wrong_word(session, user_id=user_id, word=word)
    if record is None:
        record = NotesProjectedWrongWord(
            user_id=user_id,
            word=word,
            updated_at=_parse_dt(payload.get('updated_at')),
        )

    record.user_id = user_id
    record.word = word
    record.phonetic = str(payload.get('phonetic') or '').strip() or None
    record.pos = str(payload.get('pos') or '').strip() or None
    record.definition = str(payload.get('definition') or '').strip() or None
    record.wrong_count = int(payload.get('wrong_count') or 0)
    record.listening_correct = int(payload.get('listening_correct') or 0)
    record.listening_wrong = int(payload.get('listening_wrong') or 0)
    record.meaning_correct = int(payload.get('meaning_correct') or 0)
    record.meaning_wrong = int(payload.get('meaning_wrong') or 0)
    record.dictation_correct = int(payload.get('dictation_correct') or 0)
    record.dictation_wrong = int(payload.get('dictation_wrong') or 0)
    record.dimension_state = _json_dumps(payload.get('dimension_states'))
    record.updated_at = _parse_dt(payload.get('updated_at'))
    record.projected_at = datetime.utcnow()
    session.add(record)
    return record


def consume_notes_learning_wrong_word_updated_event(
    *,
    event_id: str,
    producer_service: str,
    payload: dict,
    headers: dict | None = None,
    session=None,
) -> tuple[NotesProjectedWrongWord, bool]:
    session = session or _query_session(NotesProjectedWrongWord)
    inbox_record, created = register_inbox_event(
        NotesInboxEvent,
        consumer_service=NOTES_SERVICE_NAME,
        event_id=event_id,
        topic=LEARNING_WRONG_WORD_UPDATED_TOPIC,
        producer_service=producer_service,
        payload=payload,
        headers=headers,
        session=session,
    )
    if inbox_record.status == 'processed':
        existing = _get_projected_wrong_word(
            session,
            user_id=int(payload.get('user_id') or 0),
            word=str(payload.get('word') or '').strip(),
        )
        if existing is None:
            raise RuntimeError('processed inbox event is missing notes projected wrong-word state')
        return existing, False

    begin_inbox_processing(inbox_record)
    try:
        projected_wrong_word = upsert_notes_projected_wrong_word(payload, session=session)
        mark_inbox_event_processed(inbox_record)
        session.commit()
        return projected_wrong_word, created
    except Exception as exc:
        mark_inbox_event_failed(inbox_record, error_message=str(exc))
        session.commit()
        raise


def drain_notes_learning_wrong_word_updated_queue(*, limit: int = 50, connection=None) -> int:
    close_connection = connection is None
    connection = connection or build_blocking_connection(service_name=NOTES_SERVICE_NAME)
    channel = connection.channel()
    exchange_name = resolve_domain_exchange_name(service_name=NOTES_SERVICE_NAME)
    channel.exchange_declare(exchange=exchange_name, exchange_type='topic', durable=True)
    channel.queue_declare(queue=NOTES_WRONG_WORD_QUEUE, durable=True)
    channel.queue_bind(
        exchange=exchange_name,
        queue=NOTES_WRONG_WORD_QUEUE,
        routing_key=LEARNING_WRONG_WORD_UPDATED_TOPIC,
    )

    processed = 0
    try:
        while processed < max(1, limit):
            method_frame, properties, body = channel.basic_get(queue=NOTES_WRONG_WORD_QUEUE, auto_ack=False)
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

                consume_notes_learning_wrong_word_updated_event(
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
