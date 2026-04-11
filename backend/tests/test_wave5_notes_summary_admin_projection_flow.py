from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace

from platform_sdk.admin_daily_summary_projection_application import (
    DAILY_SUMMARY_PROJECTION,
    drain_notes_summary_generated_queue,
)
from platform_sdk.domain_event_publisher import publish_outbox_batch
from platform_sdk.notes_summary_jobs_application import generate_summary_response

from models import (
    AdminOpsInboxEvent,
    AdminProjectedDailySummary,
    AdminProjectionCursor,
    NotesOutboxEvent,
    User,
    UserDailySummary,
    db,
)


class FakePublisherChannel:
    def __init__(self):
        self.published: list[dict] = []

    def exchange_declare(self, **kwargs):
        pass

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
        self.acks: list[int] = []
        self.nacks: list[tuple[int, bool]] = []
        self._delivered = False

    def exchange_declare(self, **kwargs):
        pass

    def queue_declare(self, **kwargs):
        pass

    def queue_bind(self, **kwargs):
        pass

    def basic_get(self, *, queue, auto_ack=False):
        if self._delivered:
            return None, None, None
        self._delivered = True
        return SimpleNamespace(delivery_tag=303), self.message['properties'], self.message['body']

    def basic_ack(self, delivery_tag):
        self.acks.append(delivery_tag)

    def basic_nack(self, delivery_tag, requeue=True):
        self.nacks.append((delivery_tag, requeue))


class FakeConnection:
    def __init__(self, channel):
        self._channel = channel

    def channel(self):
        return self._channel

    def close(self):
        return None


def _create_user(*, username: str) -> User:
    user = User(username=username, email=f'{username}@example.com')
    user.set_password('password123')
    db.session.add(user)
    db.session.commit()
    return user


def test_generate_summary_queues_notes_outbox_event(app, monkeypatch):
    with app.app_context():
        monkeypatch.setenv('ALLOW_LEGACY_CROSS_SERVICE_FALLBACK', 'true')
        user = _create_user(username='wave5-notes-summary-outbox-user')
        monkeypatch.setattr(
            'platform_sdk.notes_summary_jobs_application.build_learner_profile_payload',
            lambda *args, **kwargs: {},
        )
        monkeypatch.setattr(
            'platform_sdk.notes_summary_jobs_application.build_memory_topics',
            lambda *args, **kwargs: [],
        )
        monkeypatch.setattr(
            'platform_sdk.notes_summary_jobs_application.chat',
            lambda *args, **kwargs: {'text': '# 2026-04-10 学习总结\n\n今天完成了一轮复盘。'},
        )

        response = generate_summary_response(user.id, {'date': '2026-04-10'})
        event = NotesOutboxEvent.query.order_by(NotesOutboxEvent.id.desc()).first()
        summary = UserDailySummary.query.filter_by(user_id=user.id, date='2026-04-10').first()

        assert response.get_json()['summary']['date'] == '2026-04-10'
        assert summary is not None
        assert event is not None
        assert event.topic == 'notes.summary.generated'
        assert event.aggregate_id == str(summary.id)
        assert event.payload_json
        payload = response.get_json()['summary']
        assert payload['id'] == summary.id


def test_notes_summary_outbox_publish_and_admin_projection_consume_flow(app, monkeypatch):
    with app.app_context():
        monkeypatch.setenv('ALLOW_LEGACY_CROSS_SERVICE_FALLBACK', 'true')
        user = _create_user(username='wave5-notes-summary-projection-user')
        monkeypatch.setattr(
            'platform_sdk.notes_summary_jobs_application.build_learner_profile_payload',
            lambda *args, **kwargs: {},
        )
        monkeypatch.setattr(
            'platform_sdk.notes_summary_jobs_application.build_memory_topics',
            lambda *args, **kwargs: [],
        )
        monkeypatch.setattr(
            'platform_sdk.notes_summary_jobs_application.chat',
            lambda *args, **kwargs: {'text': '# 2026-04-11 学习总结\n\n今天完成了错词整理。'},
        )

        response = generate_summary_response(user.id, {'date': '2026-04-11'})
        summary_id = response.get_json()['summary']['id']

        publisher_channel = FakePublisherChannel()
        publish_outbox_batch(
            NotesOutboxEvent,
            service_name='notes-service',
            connection=FakeConnection(publisher_channel),
        )
        assert len(publisher_channel.published) == 1
        message = publisher_channel.published[0]
        assert message['routing_key'] == 'notes.summary.generated'

        consumer_channel = FakeConsumerChannel(message)
        processed = drain_notes_summary_generated_queue(
            connection=FakeConnection(consumer_channel),
        )

        projected_summary = AdminProjectedDailySummary.query.session.get(
            AdminProjectedDailySummary,
            summary_id,
        )
        inbox_record = AdminOpsInboxEvent.query.filter_by(
            event_id=message['properties'].message_id
        ).first()
        cursor = AdminProjectionCursor.query.filter_by(
            projection_name=DAILY_SUMMARY_PROJECTION
        ).first()

        assert processed == 1
        assert projected_summary is not None
        assert projected_summary.user_id == user.id
        assert projected_summary.date == '2026-04-11'
        assert projected_summary.content.startswith('# 2026-04-11 学习总结')
        assert inbox_record is not None
        assert inbox_record.status == 'processed'
        assert cursor is not None
        assert cursor.last_event_id == message['properties'].message_id
        assert consumer_channel.acks == [303]
        assert consumer_channel.nacks == []
