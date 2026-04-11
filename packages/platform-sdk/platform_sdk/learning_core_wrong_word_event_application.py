from __future__ import annotations

import json
from datetime import datetime

from platform_sdk.outbox_runtime import queue_outbox_event
from service_models.eventing_models import LearningCoreOutboxEvent


LEARNING_CORE_SERVICE_NAME = 'learning-core-service'
LEARNING_WRONG_WORD_UPDATED_TOPIC = 'learning.wrong_word.updated'


def _json_loads(value) -> dict:
    if isinstance(value, dict):
        return value
    if not value:
        return {}
    try:
        return json.loads(value)
    except Exception:
        return {}


def build_wrong_word_updated_payload(record, *, updated_at: datetime | None = None) -> dict:
    effective_updated_at = updated_at or getattr(record, 'updated_at', None) or datetime.utcnow()
    return {
        'user_id': int(record.user_id or 0),
        'word': (record.word or '').strip(),
        'phonetic': record.phonetic or None,
        'pos': record.pos or None,
        'definition': record.definition or None,
        'wrong_count': int(record.wrong_count or 0),
        'listening_correct': int(record.listening_correct or 0),
        'listening_wrong': int(record.listening_wrong or 0),
        'meaning_correct': int(record.meaning_correct or 0),
        'meaning_wrong': int(record.meaning_wrong or 0),
        'dictation_correct': int(record.dictation_correct or 0),
        'dictation_wrong': int(record.dictation_wrong or 0),
        'dimension_states': _json_loads(getattr(record, 'dimension_state', None)),
        'updated_at': effective_updated_at.isoformat(),
    }


def queue_wrong_word_updated_event(
    record,
    *,
    session_db=None,
    event_id: str | None = None,
    updated_at: datetime | None = None,
):
    normalized_word = (record.word or '').strip().lower()
    aggregate_id = f'{int(record.user_id or 0)}:{normalized_word}'
    return queue_outbox_event(
        LearningCoreOutboxEvent,
        producer_service=LEARNING_CORE_SERVICE_NAME,
        topic=LEARNING_WRONG_WORD_UPDATED_TOPIC,
        aggregate_id=aggregate_id,
        payload=build_wrong_word_updated_payload(record, updated_at=updated_at),
        event_id=event_id,
        session=session_db,
    )
