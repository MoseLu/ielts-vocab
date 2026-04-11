from __future__ import annotations

import json
from dataclasses import dataclass
from types import SimpleNamespace

from platform_sdk.outbox_runtime import (
    claim_outbox_events,
    mark_outbox_event_failed,
    mark_outbox_event_published,
)
from platform_sdk.rabbitmq_runtime import (
    build_blocking_connection,
    pika,
    resolve_domain_exchange_name,
)


@dataclass(frozen=True)
class PublishedDomainEvent:
    event_id: str
    topic: str
    routing_key: str
    aggregate_id: str | None


def _query_session(model):
    return model.query.session


def _json_loads(value):
    if not value:
        return {}
    if isinstance(value, (dict, list)):
        return value
    return json.loads(value)


def _build_properties(record, headers: dict):
    values = {
        'content_type': 'application/json',
        'content_encoding': 'utf-8',
        'delivery_mode': 2,
        'message_id': record.event_id,
        'type': record.topic,
        'timestamp': int(record.created_at.timestamp()) if record.created_at else None,
        'headers': headers,
    }
    if pika is None:
        return SimpleNamespace(**values)
    return pika.BasicProperties(**values)


def publish_outbox_batch(
    outbox_model,
    *,
    service_name: str,
    worker_name: str | None = None,
    limit: int = 50,
    connection=None,
    session=None,
) -> list[PublishedDomainEvent]:
    session = session or _query_session(outbox_model)
    close_connection = connection is None
    connection = connection or build_blocking_connection(service_name=service_name)
    channel = connection.channel()
    exchange_name = resolve_domain_exchange_name(service_name=service_name)
    channel.exchange_declare(exchange=exchange_name, exchange_type='topic', durable=True)

    records = claim_outbox_events(
        outbox_model,
        worker_name=worker_name or f'{service_name}.outbox-publisher',
        limit=limit,
        session=session,
    )
    published: list[PublishedDomainEvent] = []

    try:
        for record in records:
            try:
                payload = _json_loads(record.payload_json)
                extra_headers = _json_loads(record.headers_json)
                message_headers = {
                    'event_id': record.event_id,
                    'producer_service': record.producer_service,
                    'topic': record.topic,
                    'aggregate_type': record.aggregate_type,
                    'aggregate_id': record.aggregate_id,
                }
                if isinstance(extra_headers, dict):
                    message_headers.update(extra_headers)

                channel.basic_publish(
                    exchange=record.exchange_name or exchange_name,
                    routing_key=record.routing_key or record.topic,
                    body=json.dumps(payload, ensure_ascii=False, sort_keys=True).encode('utf-8'),
                    properties=_build_properties(record, message_headers),
                )
                mark_outbox_event_published(record)
                published.append(
                    PublishedDomainEvent(
                        event_id=record.event_id,
                        topic=record.topic,
                        routing_key=record.routing_key,
                        aggregate_id=record.aggregate_id,
                    )
                )
            except Exception as exc:
                mark_outbox_event_failed(record, error_message=str(exc))

        session.commit()
        return published
    finally:
        if close_connection:
            connection.close()
