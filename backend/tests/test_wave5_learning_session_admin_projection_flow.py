from __future__ import annotations

import json
from datetime import datetime, timedelta
from types import SimpleNamespace

from platform_sdk.admin_study_session_projection_application import (
    STUDY_SESSION_ANALYTICS_PROJECTION,
    drain_learning_session_logged_queue,
)
from platform_sdk.admin_projection_bootstrap import bootstrap_projection_marker_name
from platform_sdk.domain_event_publisher import publish_outbox_batch
from platform_sdk.learning_core_study_session_application import log_learning_core_session_response

from models import (
    AdminOpsInboxEvent,
    AdminProjectedStudySession,
    AdminProjectionCursor,
    LearningCoreOutboxEvent,
    User,
    UserStudySession,
    db,
)
from services import admin_overview_repository, admin_user_session_repository


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
        return SimpleNamespace(delivery_tag=101), self.message['properties'], self.message['body']

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


def test_log_learning_session_queues_learning_outbox_event(app):
    with app.app_context():
        user = _create_user(username='wave5-session-outbox-user')

        payload, status = log_learning_core_session_response(user.id, {
            'mode': 'listening',
            'bookId': 'ielts_listening_premium',
            'chapterId': '2',
            'wordsStudied': 12,
            'correctCount': 9,
            'wrongCount': 3,
            'durationSeconds': 600,
        })

        event = LearningCoreOutboxEvent.query.order_by(LearningCoreOutboxEvent.id.desc()).first()

        assert status == 201
        assert payload['id'] > 0
        assert event is not None
        assert event.topic == 'learning.session.logged'
        assert event.aggregate_id == str(payload['id'])
        assert json.loads(event.payload_json) == {
            'session_id': payload['id'],
            'user_id': user.id,
            'mode': 'listening',
            'book_id': 'ielts_listening_premium',
            'chapter_id': '2',
            'words_studied': 12,
            'correct_count': 9,
            'wrong_count': 3,
            'duration_seconds': 600,
            'started_at': json.loads(event.payload_json)['started_at'],
            'ended_at': json.loads(event.payload_json)['ended_at'],
        }


def test_log_learning_session_honors_activity_capped_duration_for_started_session(app):
    with app.app_context():
        user = _create_user(username='wave5-session-activity-cap-user')
        ended_at = datetime.utcnow().replace(microsecond=0)
        started_at = ended_at - timedelta(hours=7, minutes=10, seconds=46)
        session = UserStudySession(
            user_id=user.id,
            mode='quickmemory',
            book_id='ielts_listening_premium',
            chapter_id='55',
            started_at=started_at,
        )
        db.session.add(session)
        db.session.commit()

        payload, status = log_learning_core_session_response(user.id, {
            'sessionId': session.id,
            'mode': 'quickmemory',
            'bookId': 'ielts_listening_premium',
            'chapterId': '55',
            'wordsStudied': 1,
            'wrongCount': 1,
            'durationSeconds': 20 * 60 + 8,
            'durationCappedByActivity': True,
            'endedAt': int(ended_at.timestamp() * 1000),
        })

        db.session.refresh(session)
        assert status == 200
        assert payload['id'] == session.id
        assert session.duration_seconds == 20 * 60 + 8


def test_learning_session_outbox_publish_and_admin_projection_consume_flow(app):
    with app.app_context():
        user = _create_user(username='wave5-session-projection-user')
        payload, status = log_learning_core_session_response(user.id, {
            'mode': 'meaning',
            'bookId': 'ielts_reading_premium',
            'chapterId': '3',
            'wordsStudied': 8,
            'correctCount': 6,
            'wrongCount': 2,
            'durationSeconds': 420,
        })
        assert status == 201

        publisher_channel = FakePublisherChannel()
        publish_outbox_batch(
            LearningCoreOutboxEvent,
            service_name='learning-core-service',
            connection=FakeConnection(publisher_channel),
        )
        assert len(publisher_channel.published) == 1
        message = publisher_channel.published[0]
        assert message['routing_key'] == 'learning.session.logged'

        consumer_channel = FakeConsumerChannel(message)
        processed = drain_learning_session_logged_queue(
            connection=FakeConnection(consumer_channel),
        )

        projected_session = AdminProjectedStudySession.query.session.get(AdminProjectedStudySession, payload['id'])
        inbox_record = AdminOpsInboxEvent.query.filter_by(
            event_id=message['properties'].message_id
        ).first()
        cursor = AdminProjectionCursor.query.filter_by(
            projection_name=STUDY_SESSION_ANALYTICS_PROJECTION
        ).first()

        assert processed == 1
        assert projected_session is not None
        assert projected_session.user_id == user.id
        assert projected_session.mode == 'meaning'
        assert projected_session.duration_seconds == 420
        assert inbox_record is not None
        assert inbox_record.status == 'processed'
        assert cursor is not None
        assert cursor.last_event_id == message['properties'].message_id
        assert consumer_channel.acks == [101]
        assert consumer_channel.nacks == []


def test_admin_session_stats_prefer_projected_sessions_when_projection_is_complete(app):
    with app.app_context():
        now = datetime.utcnow()
        db.session.add_all([
            UserStudySession(
                id=700,
                user_id=10,
                mode='listening',
                book_id='shared-only-book',
                chapter_id='0',
                words_studied=6,
                correct_count=4,
                wrong_count=2,
                duration_seconds=240,
                started_at=now - timedelta(hours=4),
                ended_at=now - timedelta(hours=4) + timedelta(minutes=4),
            ),
            AdminProjectedStudySession(
                id=701,
                user_id=11,
                mode='quickmemory',
                book_id='ielts_reading_premium',
                chapter_id='1',
                words_studied=20,
                correct_count=15,
                wrong_count=5,
                duration_seconds=900,
                started_at=now - timedelta(hours=2),
                ended_at=now - timedelta(hours=2) + timedelta(minutes=15),
            ),
            AdminProjectedStudySession(
                id=702,
                user_id=12,
                mode='meaning',
                book_id='ielts_listening_premium',
                chapter_id='2',
                words_studied=10,
                correct_count=8,
                wrong_count=2,
                duration_seconds=600,
                started_at=now - timedelta(hours=1),
                ended_at=now - timedelta(hours=1) + timedelta(minutes=10),
            ),
            AdminProjectionCursor(
                projection_name=bootstrap_projection_marker_name(STUDY_SESSION_ANALYTICS_PROJECTION),
                last_event_id='bootstrap:admin.study-session-analytics:test',
                last_topic='__bootstrap__',
                last_processed_at=now,
            ),
        ])
        db.session.commit()

        sessions = admin_user_session_repository.list_user_analytics_sessions(11)

        assert admin_overview_repository.count_total_analytics_sessions() == 2
        assert admin_overview_repository.get_analytics_totals()['study_seconds'] == 1500
        assert len(sessions) == 1
        assert sessions[0].id == 701
