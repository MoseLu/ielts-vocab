from __future__ import annotations

import json
from datetime import datetime
from types import SimpleNamespace

from platform_sdk.admin_wrong_word_projection_application import (
    WRONG_WORD_DIRECTORY_PROJECTION,
    drain_learning_wrong_word_updated_queue,
)
from platform_sdk.admin_projection_bootstrap import bootstrap_projection_marker_name
from platform_sdk.domain_event_publisher import publish_outbox_batch
from platform_sdk.learning_core_wrong_words_application import sync_learning_core_wrong_words_response

from models import (
    AdminOpsInboxEvent,
    AdminProjectedWrongWord,
    AdminProjectionCursor,
    LearningCoreOutboxEvent,
    User,
    UserWrongWord,
    db,
)
from services import admin_user_detail_repository


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
        return SimpleNamespace(delivery_tag=202), self.message['properties'], self.message['body']

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
        'meaning': {
            'history_wrong': 0,
            'pass_streak': 0,
            'last_wrong_at': None,
            'last_pass_at': None,
        },
        'listening': {
            'history_wrong': 0,
            'pass_streak': 0,
            'last_wrong_at': None,
            'last_pass_at': None,
        },
        'dictation': {
            'history_wrong': 0,
            'pass_streak': 0,
            'last_wrong_at': None,
            'last_pass_at': None,
        },
    }


def test_sync_wrong_words_queues_learning_outbox_event(app):
    with app.app_context():
        user = _create_user(username='wave5-wrong-word-outbox-user')

        payload, status = sync_learning_core_wrong_words_response(user.id, {
            'sourceMode': 'listening',
            'bookId': 'ielts_listening_premium',
            'chapterId': '4',
            'words': [{
                'word': 'abandon',
                'phonetic': '/əˈbændən/',
                'pos': 'v.',
                'definition': 'leave behind',
                'wrongCount': 2,
                'dimensionStates': _dimension_states(
                    wrong_count=2,
                    last_wrong_at='2026-04-09T10:00:00+00:00',
                ),
            }],
        })

        event = LearningCoreOutboxEvent.query.order_by(LearningCoreOutboxEvent.id.desc()).first()

        assert status == 200
        assert payload == {'updated': 1}
        assert event is not None
        assert event.topic == 'learning.wrong_word.updated'
        assert event.aggregate_id == f'{user.id}:abandon'
        assert json.loads(event.payload_json) == {
            'user_id': user.id,
            'word': 'abandon',
            'phonetic': '/əˈbændən/',
            'pos': 'v.',
            'definition': 'leave behind',
            'wrong_count': 2,
            'listening_correct': 0,
            'listening_wrong': 0,
            'meaning_correct': 0,
            'meaning_wrong': 0,
            'dictation_correct': 0,
            'dictation_wrong': 0,
            'dimension_states': _dimension_states(
                wrong_count=2,
                last_wrong_at='2026-04-09T10:00:00+00:00',
            ),
            'updated_at': json.loads(event.payload_json)['updated_at'],
        }


def test_learning_wrong_word_outbox_publish_and_admin_projection_consume_flow(app):
    with app.app_context():
        user = _create_user(username='wave5-wrong-word-projection-user')
        payload, status = sync_learning_core_wrong_words_response(user.id, {
            'sourceMode': 'meaning',
            'bookId': 'ielts_reading_premium',
            'chapterId': '7',
            'words': [{
                'word': 'compile',
                'phonetic': '/kəmˈpaɪl/',
                'pos': 'v.',
                'definition': 'collect information',
                'wrongCount': 3,
                'dimensionStates': _dimension_states(
                    wrong_count=3,
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

        projected_wrong_word = AdminProjectedWrongWord.query.filter_by(
            user_id=user.id,
            word='compile',
        ).first()
        inbox_record = AdminOpsInboxEvent.query.filter_by(
            event_id=message['properties'].message_id
        ).first()
        cursor = AdminProjectionCursor.query.filter_by(
            projection_name=WRONG_WORD_DIRECTORY_PROJECTION
        ).first()

        assert processed == 1
        assert projected_wrong_word is not None
        assert projected_wrong_word.definition == 'collect information'
        assert projected_wrong_word.wrong_count == 3
        assert json.loads(projected_wrong_word.dimension_state)['recognition']['history_wrong'] == 3
        assert inbox_record is not None
        assert inbox_record.status == 'processed'
        assert cursor is not None
        assert cursor.last_event_id == message['properties'].message_id
        assert consumer_channel.acks == [202]
        assert consumer_channel.nacks == []


def test_admin_user_detail_wrong_words_prefer_projection_when_projection_is_complete(app):
    with app.app_context():
        user = _create_user(username='wave5-wrong-word-detail-user')
        shared_row = UserWrongWord(
            user_id=user.id,
            word='shared-word',
            phonetic='/old/',
            pos='n.',
            definition='shared definition',
            wrong_count=1,
            dimension_state=json.dumps(_dimension_states(
                wrong_count=1,
                last_wrong_at='2026-04-01T08:00:00+00:00',
            ), ensure_ascii=False),
            updated_at=datetime(2026, 4, 1, 8, 0, 0),
        )
        shared_only_row = UserWrongWord(
            user_id=user.id,
            word='shared-only-word',
            phonetic='/only/',
            pos='adj.',
            definition='shared only definition',
            wrong_count=2,
            dimension_state=json.dumps(_dimension_states(
                wrong_count=2,
                last_wrong_at='2026-04-02T08:00:00+00:00',
            ), ensure_ascii=False),
            updated_at=datetime(2026, 4, 2, 8, 0, 0),
        )
        projected_row = AdminProjectedWrongWord(
            user_id=user.id,
            word='projected-word',
            phonetic='/new/',
            pos='v.',
            definition='projected definition',
            wrong_count=5,
            dimension_state=json.dumps(_dimension_states(
                wrong_count=5,
                last_wrong_at='2026-04-10T08:00:00+00:00',
            ), ensure_ascii=False),
            updated_at=datetime(2026, 4, 10, 8, 0, 0),
        )
        marker = AdminProjectionCursor(
            projection_name=bootstrap_projection_marker_name(WRONG_WORD_DIRECTORY_PROJECTION),
            last_event_id='bootstrap:admin.wrong-word-directory:test',
            last_topic='__bootstrap__',
            last_processed_at=datetime(2026, 4, 10, 8, 0, 0),
        )
        db.session.add_all([shared_row, shared_only_row, projected_row, marker])
        db.session.commit()

        rows = admin_user_detail_repository.list_user_wrong_word_rows(user.id)

        assert admin_user_detail_repository.count_user_wrong_words(user.id) == 1
        assert len(rows) == 1
        assert rows[0].__class__.__name__ == 'AdminProjectedWrongWord'
        assert rows[0].word == 'projected-word'
        assert rows[0].to_dict()['wrong_count'] == 5
