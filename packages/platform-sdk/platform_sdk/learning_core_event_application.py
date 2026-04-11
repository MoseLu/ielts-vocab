from __future__ import annotations

from platform_sdk.outbox_runtime import queue_outbox_event
from service_models.eventing_models import LearningCoreOutboxEvent


LEARNING_CORE_SERVICE_NAME = 'learning-core-service'
LEARNING_SESSION_LOGGED_TOPIC = 'learning.session.logged'


def build_study_session_logged_payload(session) -> dict:
    return {
        'session_id': session.id,
        'user_id': session.user_id,
        'mode': session.mode,
        'book_id': session.book_id,
        'chapter_id': session.chapter_id,
        'words_studied': int(session.words_studied or 0),
        'correct_count': int(session.correct_count or 0),
        'wrong_count': int(session.wrong_count or 0),
        'duration_seconds': int(session.duration_seconds or 0),
        'started_at': session.started_at.isoformat() if session.started_at else None,
        'ended_at': session.ended_at.isoformat() if session.ended_at else None,
    }


def queue_study_session_logged_event(session, *, session_db=None, event_id: str | None = None):
    return queue_outbox_event(
        LearningCoreOutboxEvent,
        producer_service=LEARNING_CORE_SERVICE_NAME,
        topic=LEARNING_SESSION_LOGGED_TOPIC,
        aggregate_id=str(session.id),
        payload=build_study_session_logged_payload(session),
        event_id=event_id,
        session=session_db,
    )
