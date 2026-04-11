from __future__ import annotations

from datetime import datetime, timedelta
from types import SimpleNamespace

from platform_sdk.domain_event_publisher import publish_outbox_batch
from platform_sdk.learning_core_study_session_application import log_learning_core_session_response
from platform_sdk.notes_study_session_projection_application import (
    drain_notes_learning_session_logged_queue,
)

from models import (
    LearningCoreOutboxEvent,
    NotesInboxEvent,
    NotesProjectedStudySession,
    User,
    UserStudySession,
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
        return SimpleNamespace(delivery_tag=201), self.message['properties'], self.message['body']

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


def test_learning_session_outbox_publish_and_notes_projection_consume_flow(app):
    with app.app_context():
        user = _create_user(username='wave5-notes-session-projection-user')
        payload, status = log_learning_core_session_response(user.id, {
            'mode': 'quickmemory',
            'bookId': 'ielts_reading_premium',
            'chapterId': '4',
            'wordsStudied': 11,
            'correctCount': 8,
            'wrongCount': 3,
            'durationSeconds': 540,
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
        processed = drain_notes_learning_session_logged_queue(
            connection=FakeConnection(consumer_channel),
        )

        projected_session = NotesProjectedStudySession.query.session.get(
            NotesProjectedStudySession,
            payload['id'],
        )
        inbox_record = NotesInboxEvent.query.filter_by(
            event_id=message['properties'].message_id
        ).first()

        assert processed == 1
        assert projected_session is not None
        assert projected_session.user_id == user.id
        assert projected_session.mode == 'quickmemory'
        assert projected_session.duration_seconds == 540
        assert inbox_record is not None
        assert inbox_record.status == 'processed'
        assert consumer_channel.acks == [201]
        assert consumer_channel.nacks == []


def test_notes_summary_context_prefers_projected_sessions_when_projection_is_complete(app):
    with app.app_context():
        user = _create_user(username='notes-projected-context-user')
        now = datetime.utcnow()
        db.session.add(UserStudySession(
            id=901,
            user_id=user.id,
            mode='listening',
            book_id='legacy-book',
            chapter_id='1',
            words_studied=5,
            correct_count=3,
            wrong_count=2,
            duration_seconds=300,
            started_at=now - timedelta(hours=2),
            ended_at=now - timedelta(hours=2) + timedelta(minutes=5),
        ))
        db.session.add(NotesProjectedStudySession(
            id=901,
            user_id=user.id,
            mode='meaning',
            book_id='projected-book',
            chapter_id='2',
            words_studied=9,
            correct_count=7,
            wrong_count=2,
            duration_seconds=420,
            started_at=now - timedelta(hours=2),
            ended_at=now - timedelta(hours=2) + timedelta(minutes=7),
        ))
        db.session.commit()

        in_window = notes_summary_context_repository.list_study_sessions_in_window(
            user.id,
            start_at=now - timedelta(days=1),
            end_before=now + timedelta(days=1),
        )
        before_rows = notes_summary_context_repository.list_study_sessions_before(
            user.id,
            end_before=now + timedelta(days=1),
            descending=True,
            require_words_studied=True,
        )

        assert len(in_window) == 1
        assert in_window[0].__class__.__name__ == 'NotesProjectedStudySession'
        assert in_window[0].book_id == 'projected-book'
        assert before_rows[0].__class__.__name__ == 'NotesProjectedStudySession'
        assert before_rows[0].mode == 'meaning'
