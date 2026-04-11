from __future__ import annotations

import json
from datetime import datetime, timedelta
from types import SimpleNamespace

from platform_sdk.admin_user_projection_application import (
    USER_DIRECTORY_PROJECTION,
    drain_identity_user_registered_queue,
)
from platform_sdk.domain_event_publisher import publish_outbox_batch

from models import (
    AdminOpsInboxEvent,
    AdminProjectedUser,
    AdminProjectionCursor,
    IdentityOutboxEvent,
    User,
)
from services import admin_overview_repository, auth_repository


class FakePublisherChannel:
    def __init__(self):
        self.exchanges: list[dict] = []
        self.published: list[dict] = []

    def exchange_declare(self, **kwargs):
        self.exchanges.append(kwargs)

    def basic_publish(self, *, exchange, routing_key, body, properties):
        self.published.append({
            'exchange': exchange,
            'routing_key': routing_key,
            'body': body,
            'properties': properties,
        })


class FakeConsumerChannel:
    def __init__(self, message: dict):
        self.message = message
        self.exchanges: list[dict] = []
        self.queues: list[dict] = []
        self.bindings: list[dict] = []
        self.acks: list[int] = []
        self.nacks: list[tuple[int, bool]] = []
        self._delivered = False

    def exchange_declare(self, **kwargs):
        self.exchanges.append(kwargs)

    def queue_declare(self, **kwargs):
        self.queues.append(kwargs)

    def queue_bind(self, **kwargs):
        self.bindings.append(kwargs)

    def basic_get(self, *, queue, auto_ack=False):
        if self._delivered:
            return None, None, None
        self._delivered = True
        return SimpleNamespace(delivery_tag=99), self.message['properties'], self.message['body']

    def basic_ack(self, delivery_tag):
        self.acks.append(delivery_tag)

    def basic_nack(self, delivery_tag, requeue=True):
        self.nacks.append((delivery_tag, requeue))


class FakeConnection:
    def __init__(self, channel):
        self._channel = channel
        self.closed = False

    def channel(self):
        return self._channel

    def close(self):
        self.closed = True


def test_create_user_queues_identity_registered_outbox_event(app):
    with app.app_context():
        user = auth_repository.create_user(
            username='wave5-outbox-user',
            email='wave5-outbox@example.com',
            password='password123',
        )

        events = IdentityOutboxEvent.query.order_by(IdentityOutboxEvent.id.asc()).all()

        assert len(events) == 1
        assert events[0].topic == 'identity.user.registered'
        assert events[0].aggregate_id == str(user.id)
        assert json.loads(events[0].payload_json) == {
            'user_id': user.id,
            'username': 'wave5-outbox-user',
            'email': 'wave5-outbox@example.com',
            'avatar_url': None,
            'is_admin': False,
            'created_at': user.created_at.isoformat(),
        }


def test_identity_outbox_publish_and_admin_projection_consume_flow(app):
    with app.app_context():
        user = auth_repository.create_user(
            username='wave5-projection-user',
            email='wave5-projection@example.com',
            password='password123',
        )

        publisher_channel = FakePublisherChannel()
        publish_outbox_batch(
            IdentityOutboxEvent,
            service_name='identity-service',
            connection=FakeConnection(publisher_channel),
        )

        assert len(publisher_channel.published) == 1
        message = publisher_channel.published[0]
        assert message['routing_key'] == 'identity.user.registered'

        consumer_channel = FakeConsumerChannel(message)
        processed = drain_identity_user_registered_queue(
            connection=FakeConnection(consumer_channel),
        )

        projected_user = AdminProjectedUser.query.session.get(AdminProjectedUser, user.id)
        inbox_record = AdminOpsInboxEvent.query.filter_by(
            event_id=message['properties'].message_id
        ).first()
        cursor = AdminProjectionCursor.query.filter_by(
            projection_name=USER_DIRECTORY_PROJECTION
        ).first()

        assert processed == 1
        assert projected_user is not None
        assert projected_user.username == 'wave5-projection-user'
        assert projected_user.email == 'wave5-projection@example.com'
        assert inbox_record is not None
        assert inbox_record.status == 'processed'
        assert cursor is not None
        assert cursor.last_event_id == message['properties'].message_id
        assert consumer_channel.acks == [99]
        assert consumer_channel.nacks == []


def test_admin_overview_counts_prefer_projected_users_when_projection_is_complete(app):
    with app.app_context():
        admin = User.query.filter_by(username='admin').first()
        assert admin is not None

        now = datetime.utcnow()
        projected_admin = AdminProjectedUser(
            id=admin.id,
            username=admin.username,
            email=admin.email,
            avatar_url=admin.avatar_url,
            is_admin=admin.is_admin,
            created_at=now - timedelta(hours=2),
        )
        projected_learner = AdminProjectedUser(
            id=999,
            username='projected-learner',
            email='projected-learner@example.com',
            avatar_url=None,
            is_admin=False,
            created_at=now - timedelta(minutes=5),
        )
        db_session = AdminProjectedUser.query.session
        db_session.add_all([projected_admin, projected_learner])
        db_session.commit()

        assert admin_overview_repository.count_total_users() == 2
        assert admin_overview_repository.count_new_users_since(now - timedelta(days=1)) == 2
