from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace

from platform_sdk.admin_prompt_run_projection_application import (
    PROMPT_RUN_PROJECTION,
    drain_ai_prompt_run_completed_queue,
)
from platform_sdk.ai_prompt_run_event_application import record_ai_prompt_run_completion
from platform_sdk.domain_event_publisher import publish_outbox_batch

from models import (
    AIExecutionOutboxEvent,
    AdminOpsInboxEvent,
    AdminProjectedPromptRun,
    AdminProjectionCursor,
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


def test_ai_prompt_run_completion_queues_outbox_event(app):
    with app.app_context():
        user = _create_user(username='wave5-ai-prompt-outbox-user')
        prompt_run = record_ai_prompt_run_completion(
            user_id=user.id,
            run_kind='assistant.ask',
            provider='minimax',
            model='MiniMax-M2.7-highspeed',
            prompt_excerpt='今天怎么复习？',
            response_excerpt='先复习今天到期的错词。',
            completed_at=datetime.utcnow(),
        )
        event = AIExecutionOutboxEvent.query.order_by(AIExecutionOutboxEvent.id.desc()).first()

        assert prompt_run.id > 0
        assert event is not None
        assert event.topic == 'ai.prompt_run.completed'
        assert event.aggregate_id == str(prompt_run.id)
        assert event.payload_json


def test_ai_prompt_outbox_publish_and_admin_projection_consume_flow(app):
    with app.app_context():
        user = _create_user(username='wave5-ai-prompt-projection-user')
        prompt_run = record_ai_prompt_run_completion(
            user_id=user.id,
            run_kind='custom-book.generate',
            provider='minimax',
            model='MiniMax-M2.7-highspeed',
            prompt_excerpt='请生成一份学术高频词书。',
            response_excerpt='{"title":"学术高频词"}',
            result_ref='custom-book-88',
            completed_at=datetime.utcnow(),
        )

        publisher_channel = FakePublisherChannel()
        publish_outbox_batch(
            AIExecutionOutboxEvent,
            service_name='ai-execution-service',
            connection=FakeConnection(publisher_channel),
        )
        assert len(publisher_channel.published) == 1
        message = publisher_channel.published[0]
        assert message['routing_key'] == 'ai.prompt_run.completed'

        consumer_channel = FakeConsumerChannel(message)
        processed = drain_ai_prompt_run_completed_queue(
            connection=FakeConnection(consumer_channel),
        )

        projected_prompt_run = AdminProjectedPromptRun.query.session.get(
            AdminProjectedPromptRun,
            prompt_run.id,
        )
        inbox_record = AdminOpsInboxEvent.query.filter_by(
            event_id=message['properties'].message_id
        ).first()
        cursor = AdminProjectionCursor.query.filter_by(
            projection_name=PROMPT_RUN_PROJECTION
        ).first()

        assert processed == 1
        assert projected_prompt_run is not None
        assert projected_prompt_run.user_id == user.id
        assert projected_prompt_run.run_kind == 'custom-book.generate'
        assert projected_prompt_run.result_ref == 'custom-book-88'
        assert inbox_record is not None
        assert inbox_record.status == 'processed'
        assert cursor is not None
        assert cursor.last_event_id == message['properties'].message_id
        assert consumer_channel.acks == [707]
        assert consumer_channel.nacks == []
