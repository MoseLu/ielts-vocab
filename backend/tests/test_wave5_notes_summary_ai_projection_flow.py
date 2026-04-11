from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace

from platform_sdk import ai_context_application
from platform_sdk.ai_projection_bootstrap import ai_bootstrap_marker_name
from platform_sdk.ai_daily_summary_projection_application import (
    AI_DAILY_SUMMARY_CONTEXT_PROJECTION,
    drain_notes_summary_generated_queue,
)
from platform_sdk.domain_event_publisher import publish_outbox_batch
from platform_sdk.notes_summary_jobs_application import generate_summary_response

from models import (
    AIExecutionInboxEvent,
    AIProjectionCursor,
    AIProjectedDailySummary,
    NotesOutboxEvent,
    User,
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
        return SimpleNamespace(delivery_tag=707), self.message['properties'], self.message['body']

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


def test_notes_summary_outbox_publish_and_ai_projection_consume_flow(app, monkeypatch):
    with app.app_context():
        monkeypatch.setenv('ALLOW_LEGACY_CROSS_SERVICE_FALLBACK', 'true')
        user = _create_user(username='wave5-notes-summary-ai-projection-user')
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
            lambda *args, **kwargs: {'text': '# 2026-04-11 学习总结\n\n今天完成了 AI 复盘。'},
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

        projected_summary = AIProjectedDailySummary.query.session.get(
            AIProjectedDailySummary,
            summary_id,
        )
        inbox_record = AIExecutionInboxEvent.query.filter_by(
            event_id=message['properties'].message_id
        ).first()
        cursor = AIProjectionCursor.query.filter_by(
            projection_name=AI_DAILY_SUMMARY_CONTEXT_PROJECTION
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
        assert cursor.last_topic == 'notes.summary.generated'
        assert consumer_channel.acks == [707]
        assert consumer_channel.nacks == []


def test_ai_context_uses_projected_summaries_when_notes_service_is_unavailable(app, monkeypatch):
    with app.app_context():
        user = _create_user(username='wave5-ai-context-summary-user')
        db.session.add(AIProjectedDailySummary(
            user_id=user.id,
            date='2026-04-11',
            content='# 2026-04-11 学习总结 今天优先复盘了错词和 AI 问答。',
            generated_at=datetime(2026, 4, 11, 9, 0, 0),
        ))
        db.session.add(AIProjectionCursor(
            projection_name=ai_bootstrap_marker_name(AI_DAILY_SUMMARY_CONTEXT_PROJECTION),
            last_event_id='bootstrap:ai.daily-summary-context:test',
            last_topic='__bootstrap__',
            last_processed_at=datetime.utcnow(),
        ))
        db.session.commit()

        monkeypatch.setattr(
            ai_context_application,
            'fetch_learning_core_context_payload',
            lambda user_id: {'books': [], 'wrongWords': [], 'recentSessions': []},
        )
        monkeypatch.setattr(
            ai_context_application,
            'build_local_learner_profile_response',
            lambda user_id, *, target_date, view: ({'activity_summary': {'today_words': 2}}, 200),
        )
        monkeypatch.setattr(
            ai_context_application,
            'load_memory',
            lambda user_id: {'goals': ['7.0']},
        )
        monkeypatch.setattr(
            ai_context_application,
            'list_recent_daily_summaries',
            lambda user_id, limit=7: (_ for _ in ()).throw(RuntimeError('notes unavailable')),
        )

        payload = ai_context_application.build_context_payload(user.id)

        assert payload['recentSummaries'][0]['date'] == '2026-04-11'
        assert 'AI 问答' in payload['recentSummaries'][0]['content']
