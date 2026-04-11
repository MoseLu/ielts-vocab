from __future__ import annotations

import json
from datetime import datetime
from types import SimpleNamespace

from platform_sdk.domain_event_publisher import publish_outbox_batch
from platform_sdk.learning_core_wrong_words_application import sync_learning_core_wrong_words_response
from platform_sdk.notes_wrong_word_projection_application import (
    drain_notes_learning_wrong_word_updated_queue,
)

from models import (
    LearningCoreOutboxEvent,
    NotesInboxEvent,
    NotesProjectedWrongWord,
    User,
    UserWrongWord,
    db,
)
from services import notes_summary_context_repository


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
        return SimpleNamespace(delivery_tag=505), self.message['properties'], self.message['body']

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


def _dimension_states(*, wrong_count: int, last_wrong_at: str) -> dict:
    return {
        'recognition': {
            'history_wrong': wrong_count,
            'pass_streak': 0,
            'last_wrong_at': last_wrong_at,
            'last_pass_at': None,
        },
        'meaning': {'history_wrong': 0, 'pass_streak': 0, 'last_wrong_at': None, 'last_pass_at': None},
        'listening': {'history_wrong': 0, 'pass_streak': 0, 'last_wrong_at': None, 'last_pass_at': None},
        'dictation': {'history_wrong': 0, 'pass_streak': 0, 'last_wrong_at': None, 'last_pass_at': None},
    }


def test_learning_wrong_word_outbox_publish_and_notes_projection_consume_flow(app):
    with app.app_context():
        user = _create_user(username='wave5-notes-wrong-word-projection-user')
        payload, status = sync_learning_core_wrong_words_response(user.id, {
            'sourceMode': 'listening',
            'words': [{
                'word': 'compile',
                'phonetic': '/kəmˈpaɪl/',
                'pos': 'v.',
                'definition': 'collect information',
                'wrongCount': 3,
                'dimensionStates': _dimension_states(
                    wrong_count=3,
                    last_wrong_at='2026-04-11T09:30:00+00:00',
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
        processed = drain_notes_learning_wrong_word_updated_queue(
            connection=FakeConnection(consumer_channel),
        )

        projected_wrong_word = NotesProjectedWrongWord.query.filter_by(
            user_id=user.id,
            word='compile',
        ).first()
        inbox_record = NotesInboxEvent.query.filter_by(
            event_id=message['properties'].message_id
        ).first()

        assert processed == 1
        assert projected_wrong_word is not None
        assert projected_wrong_word.definition == 'collect information'
        assert projected_wrong_word.wrong_count == 3
        assert json.loads(projected_wrong_word.dimension_state)['recognition']['history_wrong'] == 3
        assert inbox_record is not None
        assert inbox_record.status == 'processed'
        assert consumer_channel.acks == [505]
        assert consumer_channel.nacks == []


def test_notes_summary_context_prefers_projected_wrong_words_when_projection_is_complete(app):
    with app.app_context():
        user = _create_user(username='notes-projected-wrong-word-context-user')
        db.session.add(UserWrongWord(
            user_id=user.id,
            word='legacy',
            phonetic='/legacy/',
            pos='n.',
            definition='legacy value',
            wrong_count=1,
            updated_at=datetime(2026, 4, 11, 8, 0, 0),
        ))
        db.session.add(NotesProjectedWrongWord(
            user_id=user.id,
            word='legacy',
            phonetic='/projected/',
            pos='adj.',
            definition='projected value',
            wrong_count=4,
            dimension_state=json.dumps(_dimension_states(
                wrong_count=4,
                last_wrong_at='2026-04-11T09:00:00+00:00',
            ), ensure_ascii=False),
            updated_at=datetime(2026, 4, 11, 9, 0, 0),
        ))
        db.session.commit()

        wrong_words = notes_summary_context_repository.list_wrong_words(user.id, limit=10)

        assert len(wrong_words) == 1
        assert wrong_words[0].__class__.__name__ == 'NotesProjectedWrongWord'
        assert wrong_words[0].definition == 'projected value'
        assert wrong_words[0].wrong_count == 4
