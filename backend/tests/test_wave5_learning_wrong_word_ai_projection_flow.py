from __future__ import annotations

import json
from datetime import datetime
from types import SimpleNamespace

from platform_sdk import ai_assistant_tool_support, ai_wrong_words_application
from platform_sdk.ai_projection_bootstrap import ai_bootstrap_marker_name
from platform_sdk.ai_wrong_word_projection_application import (
    AI_WRONG_WORD_CONTEXT_PROJECTION,
    drain_learning_wrong_word_updated_queue,
)
from platform_sdk.domain_event_publisher import publish_outbox_batch
from platform_sdk.learning_core_wrong_words_application import sync_learning_core_wrong_words_response

from models import (
    AIExecutionInboxEvent,
    AIProjectionCursor,
    AIProjectedWrongWord,
    LearningCoreOutboxEvent,
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
        return SimpleNamespace(delivery_tag=909), self.message['properties'], self.message['body']

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


def _dimension_states(*, wrong_count: int, last_wrong_at: str, pass_streak: int = 0) -> dict:
    return {
        'recognition': {
            'history_wrong': wrong_count,
            'pass_streak': pass_streak,
            'last_wrong_at': last_wrong_at,
            'last_pass_at': None,
        },
        'meaning': {'history_wrong': 0, 'pass_streak': 0, 'last_wrong_at': None, 'last_pass_at': None},
        'listening': {'history_wrong': 0, 'pass_streak': 0, 'last_wrong_at': None, 'last_pass_at': None},
        'dictation': {'history_wrong': 0, 'pass_streak': 0, 'last_wrong_at': None, 'last_pass_at': None},
    }


def test_learning_wrong_word_outbox_publish_and_ai_projection_consume_flow(app):
    with app.app_context():
        user = _create_user(username='wave5-ai-wrong-word-projection-user')
        payload, status = sync_learning_core_wrong_words_response(user.id, {
            'sourceMode': 'meaning',
            'bookId': 'ielts_reading_premium',
            'chapterId': '7',
            'words': [{
                'word': 'compile',
                'phonetic': '/kəmˈpaɪl/',
                'pos': 'v.',
                'definition': 'collect information',
                'wrongCount': 4,
                'dimensionStates': _dimension_states(
                    wrong_count=4,
                    last_wrong_at='2026-04-10T09:30:00+00:00',
                ),
            }],
        })
        assert status == 200
        assert payload == {'updated': 1}

        publisher_channel = FakePublisherChannel()
        publish_outbox_batch(
            LearningCoreOutboxEvent,
            service_name='learning-core-service',
            connection=FakeConnection(publisher_channel),
        )
        assert len(publisher_channel.published) == 1
        message = publisher_channel.published[0]
        assert message['routing_key'] == 'learning.wrong_word.updated'

        consumer_channel = FakeConsumerChannel(message)
        processed = drain_learning_wrong_word_updated_queue(
            connection=FakeConnection(consumer_channel),
        )

        projected_wrong_word = AIProjectedWrongWord.query.filter_by(
            user_id=user.id,
            word='compile',
        ).first()
        inbox_record = AIExecutionInboxEvent.query.filter_by(
            event_id=message['properties'].message_id
        ).first()
        cursor = AIProjectionCursor.query.filter_by(
            projection_name=AI_WRONG_WORD_CONTEXT_PROJECTION
        ).first()

        assert processed == 1
        assert projected_wrong_word is not None
        assert projected_wrong_word.definition == 'collect information'
        assert projected_wrong_word.wrong_count == 4
        assert json.loads(projected_wrong_word.dimension_state)['recognition']['history_wrong'] == 4
        assert inbox_record is not None
        assert inbox_record.status == 'processed'
        assert cursor is not None
        assert cursor.last_event_id == message['properties'].message_id
        assert cursor.last_topic == 'learning.wrong_word.updated'
        assert consumer_channel.acks == [909]
        assert consumer_channel.nacks == []


def test_ai_wrong_words_read_uses_projection_when_learning_core_is_unavailable(app, monkeypatch):
    with app.app_context():
        user = _create_user(username='wave5-ai-wrong-word-read-user')
        db.session.add(AIProjectedWrongWord(
            user_id=user.id,
            word='compile',
            phonetic='/kəmˈpaɪl/',
            pos='v.',
            definition='collect information',
            wrong_count=4,
            dimension_state=json.dumps(_dimension_states(
                wrong_count=4,
                last_wrong_at='2026-04-10T09:30:00+00:00',
            ), ensure_ascii=False),
            updated_at=datetime(2026, 4, 10, 9, 30, 0),
        ))
        db.session.add(AIProjectionCursor(
            projection_name=ai_bootstrap_marker_name(AI_WRONG_WORD_CONTEXT_PROJECTION),
            last_event_id='bootstrap:ai.wrong-word-context:test',
            last_topic='__bootstrap__',
            last_processed_at=datetime.utcnow(),
        ))
        db.session.commit()

        monkeypatch.setattr(
            ai_wrong_words_application,
            'fetch_learning_core_wrong_words_response',
            lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError('learning-core unavailable')),
        )
        monkeypatch.setenv('CURRENT_SERVICE_NAME', 'ai-execution-service')
        monkeypatch.delenv('ALLOW_LEGACY_CROSS_SERVICE_FALLBACK', raising=False)

        response, status = ai_wrong_words_application.build_wrong_words_response(
            user.id,
            search_value='comp',
            detail_mode='compact',
        )

        assert status == 200
        assert response['words'][0]['word'] == 'compile'
        assert response['words'][0]['wrong_count'] == 4


def test_get_wrong_words_tool_uses_projection_when_learning_core_is_unavailable(app, monkeypatch):
    with app.app_context():
        user = _create_user(username='wave5-ai-wrong-word-tool-user')
        db.session.add(AIProjectedWrongWord(
            user_id=user.id,
            word='abandon',
            phonetic='/əˈbændən/',
            pos='v.',
            definition='leave behind',
            wrong_count=3,
            dimension_state=json.dumps(_dimension_states(
                wrong_count=3,
                last_wrong_at='2026-04-10T10:00:00+00:00',
            ), ensure_ascii=False),
            updated_at=datetime(2026, 4, 10, 10, 0, 0),
        ))
        db.session.add(AIProjectionCursor(
            projection_name=ai_bootstrap_marker_name(AI_WRONG_WORD_CONTEXT_PROJECTION),
            last_event_id='bootstrap:ai.wrong-word-context:test',
            last_topic='__bootstrap__',
            last_processed_at=datetime.utcnow(),
        ))
        db.session.commit()

        monkeypatch.setattr(
            ai_assistant_tool_support,
            'fetch_learning_core_wrong_words_for_ai',
            lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError('learning-core unavailable')),
        )

        result = ai_assistant_tool_support.make_get_wrong_words(user.id)(
            limit=8,
            query='aban',
            recent_first=True,
        )

        assert 'abandon' in result
        assert '错误3次' in result
