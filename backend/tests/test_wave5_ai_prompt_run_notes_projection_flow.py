from __future__ import annotations

from datetime import datetime, timedelta
from types import SimpleNamespace

import jwt

from platform_sdk.ai_prompt_run_event_application import record_ai_prompt_run_completion
from platform_sdk.domain_event_publisher import publish_outbox_batch
from platform_sdk.notes_prompt_run_projection_application import (
    drain_notes_ai_prompt_run_completed_queue,
)

from models import (
    AIExecutionOutboxEvent,
    NotesInboxEvent,
    NotesProjectedPromptRun,
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
        return SimpleNamespace(delivery_tag=808), self.message['properties'], self.message['body']

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


def _make_token(app, user_id: int, username: str) -> str:
    return jwt.encode(
        {
            'user_id': user_id,
            'type': 'access',
            'jti': f'jti-{username}',
            'iat': int(datetime.utcnow().timestamp()),
            'exp': datetime.utcnow() + timedelta(seconds=app.config['JWT_ACCESS_TOKEN_EXPIRES']),
        },
        app.config['JWT_SECRET_KEY'],
        algorithm='HS256',
    )


def test_ai_prompt_outbox_publish_and_notes_projection_consume_flow(app):
    with app.app_context():
        user = _create_user(username='wave5-notes-prompt-projection-user')
        prompt_run = record_ai_prompt_run_completion(
            user_id=user.id,
            run_kind='assistant.ask_stream',
            provider='minimax',
            model='MiniMax-M2.7-highspeed',
            prompt_excerpt='今天先复习什么？',
            response_excerpt='先看错词，再做听力和 quick memory。',
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
        processed = drain_notes_ai_prompt_run_completed_queue(
            connection=FakeConnection(consumer_channel),
        )

        projected_prompt_run = NotesProjectedPromptRun.query.session.get(
            NotesProjectedPromptRun,
            prompt_run.id,
        )
        inbox_record = NotesInboxEvent.query.filter_by(
            event_id=message['properties'].message_id
        ).first()

        assert processed == 1
        assert projected_prompt_run is not None
        assert projected_prompt_run.user_id == user.id
        assert projected_prompt_run.run_kind == 'assistant.ask_stream'
        assert projected_prompt_run.prompt_excerpt == '今天先复习什么？'
        assert inbox_record is not None
        assert inbox_record.status == 'processed'
        assert consumer_channel.acks == [808]
        assert consumer_channel.nacks == []


def test_notes_summary_prompt_includes_projected_prompt_runs(client, app, monkeypatch):
    with app.app_context():
        user = _create_user(username='notes-summary-prompt-run-user')
        db.session.add(NotesProjectedPromptRun(
            id=3201,
            event_id='evt-notes-prompt-run-3201',
            user_id=user.id,
            run_kind='assistant.ask',
            provider='minimax',
            model='MiniMax-M2.7-highspeed',
            prompt_excerpt='今天怎么安排复习？',
            response_excerpt='先复习错词，再完成一轮听力练习。',
            completed_at=datetime(2026, 3, 30, 10, 11, 0),
        ))
        db.session.commit()
        token = _make_token(app, user.id, user.username)

    captured = {}

    def fake_chat(messages, *args, **kwargs):
        captured['messages'] = messages
        return {'text': '# refreshed summary'}

    monkeypatch.setattr('services.notes_summary_job_service.chat', fake_chat)

    response = client.post(
        '/api/notes/summaries/generate',
        json={'date': '2026-03-30'},
        headers={'Authorization': f'Bearer {token}'},
    )

    assert response.status_code == 200
    prompt = captured['messages'][1]['content']
    assert '今日 AI 运行次数：1' in prompt
    assert '当天 AI 使用痕迹' in prompt
    assert '18:11 AI 助手问答' in prompt
    assert '今天怎么安排复习？' in prompt
