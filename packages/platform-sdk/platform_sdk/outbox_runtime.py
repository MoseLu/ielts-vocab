from __future__ import annotations

import json
import uuid
from datetime import datetime

from platform_sdk.domain_event_contracts import get_domain_event_contract
from platform_sdk.rabbitmq_runtime import resolve_domain_exchange_name


def _query_session(model):
    return model.query.session


def _json_dumps(value) -> str:
    return json.dumps(value or {}, ensure_ascii=False, sort_keys=True)


def next_event_id() -> str:
    return uuid.uuid4().hex


def queue_outbox_event(
    outbox_model,
    *,
    producer_service: str,
    topic: str,
    payload: dict,
    aggregate_type: str | None = None,
    aggregate_id: str | None = None,
    headers: dict | None = None,
    available_at: datetime | None = None,
    event_id: str | None = None,
    session=None,
):
    contract = get_domain_event_contract(topic)
    if contract.publisher_service != producer_service:
        raise ValueError(f'{topic} must be published by {contract.publisher_service}, not {producer_service}')

    session = session or _query_session(outbox_model)
    record = outbox_model(
        event_id=event_id or next_event_id(),
        topic=topic,
        producer_service=producer_service,
        exchange_name=resolve_domain_exchange_name(service_name=producer_service),
        routing_key=contract.routing_key,
        aggregate_type=aggregate_type or contract.aggregate_type,
        aggregate_id=aggregate_id,
        payload_json=_json_dumps(payload),
        headers_json=_json_dumps(headers),
        available_at=available_at or datetime.utcnow(),
    )
    session.add(record)
    return record


def claim_outbox_events(outbox_model, *, worker_name: str, limit: int = 50, now: datetime | None = None, session=None):
    session = session or _query_session(outbox_model)
    now = now or datetime.utcnow()
    records = (
        outbox_model.query
        .filter(outbox_model.published_at.is_(None))
        .filter(outbox_model.claimed_at.is_(None))
        .filter(outbox_model.available_at <= now)
        .order_by(outbox_model.available_at.asc(), outbox_model.id.asc())
        .limit(max(1, limit))
        .all()
    )
    for record in records:
        record.claimed_at = now
        record.claimed_by = worker_name
        record.attempt_count = int(record.attempt_count or 0) + 1
        record.last_error = None
    return records


def mark_outbox_event_published(record, *, published_at: datetime | None = None) -> None:
    record.published_at = published_at or datetime.utcnow()
    record.last_error = None


def mark_outbox_event_failed(record, *, error_message: str) -> None:
    record.claimed_at = None
    record.claimed_by = None
    record.last_error = error_message.strip() or 'unknown error'


def register_inbox_event(
    inbox_model,
    *,
    consumer_service: str,
    event_id: str,
    topic: str,
    producer_service: str,
    payload: dict | None = None,
    headers: dict | None = None,
    session=None,
):
    contract = get_domain_event_contract(topic)
    if contract.publisher_service != producer_service:
        raise ValueError(f'{topic} must come from {contract.publisher_service}, not {producer_service}')
    if consumer_service not in contract.consumer_services:
        raise ValueError(f'{topic} is not declared for consumer {consumer_service}')

    existing = inbox_model.query.filter_by(event_id=event_id).first()
    if existing is not None:
        return existing, False

    session = session or _query_session(inbox_model)
    record = inbox_model(
        event_id=event_id,
        topic=topic,
        producer_service=producer_service,
        payload_json=_json_dumps(payload),
        headers_json=_json_dumps(headers),
    )
    session.add(record)
    return record, True


def begin_inbox_processing(record) -> None:
    record.status = 'processing'
    record.attempt_count = int(record.attempt_count or 0) + 1
    record.last_error = None


def mark_inbox_event_processed(record, *, processed_at: datetime | None = None) -> None:
    record.status = 'processed'
    record.processed_at = processed_at or datetime.utcnow()
    record.last_error = None


def mark_inbox_event_failed(record, *, error_message: str) -> None:
    record.status = 'failed'
    record.last_error = error_message.strip() or 'unknown error'
