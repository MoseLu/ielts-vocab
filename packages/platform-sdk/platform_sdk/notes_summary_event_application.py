from __future__ import annotations

from platform_sdk.outbox_runtime import queue_outbox_event
from service_models.eventing_models import NotesOutboxEvent


NOTES_SERVICE_NAME = 'notes-service'
NOTES_SUMMARY_GENERATED_TOPIC = 'notes.summary.generated'


def build_summary_generated_payload(summary) -> dict:
    return {
        'summary_id': int(summary.id or 0),
        'user_id': int(summary.user_id or 0),
        'date': summary.date,
        'content': summary.content,
        'generated_at': summary.generated_at.isoformat() if summary.generated_at else None,
    }


def queue_summary_generated_event(summary, *, session_db=None, event_id: str | None = None):
    return queue_outbox_event(
        NotesOutboxEvent,
        producer_service=NOTES_SERVICE_NAME,
        topic=NOTES_SUMMARY_GENERATED_TOPIC,
        aggregate_id=str(summary.id),
        payload=build_summary_generated_payload(summary),
        event_id=event_id,
        session=session_db,
    )
