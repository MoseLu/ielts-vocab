from __future__ import annotations

from platform_sdk.outbox_runtime import queue_outbox_event
from service_models.eventing_models import IdentityOutboxEvent


IDENTITY_SERVICE_NAME = 'identity-service'
USER_REGISTERED_TOPIC = 'identity.user.registered'


def build_user_registered_payload(user) -> dict:
    return {
        'user_id': user.id,
        'username': user.username,
        'email': user.email or '',
        'avatar_url': user.avatar_url,
        'is_admin': bool(user.is_admin),
        'created_at': user.created_at.isoformat() if user.created_at else None,
    }


def queue_user_registered_event(user, *, session=None, event_id: str | None = None):
    return queue_outbox_event(
        IdentityOutboxEvent,
        producer_service=IDENTITY_SERVICE_NAME,
        topic=USER_REGISTERED_TOPIC,
        aggregate_id=str(user.id),
        payload=build_user_registered_payload(user),
        event_id=event_id,
        session=session,
    )
