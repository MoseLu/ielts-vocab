from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace

from platform_sdk.admin_tts_media_projection_application import (
    TTS_MEDIA_PROJECTION,
    drain_tts_media_generated_queue,
)
from platform_sdk.domain_event_publisher import publish_outbox_batch
from platform_sdk.tts_media_event_application import record_tts_media_materialization

from models import (
    AdminOpsInboxEvent,
    AdminProjectedTTSMedia,
    AdminProjectionCursor,
    TTSMediaAsset,
    TTSMediaOutboxEvent,
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
        return SimpleNamespace(delivery_tag=404), self.message['properties'], self.message['body']

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


def test_tts_media_materialization_queues_outbox_event(app):
    with app.app_context():
        user = _create_user(username='wave5-tts-media-user')

        asset, created = record_tts_media_materialization(
            media_kind='example-audio',
            media_id='example-asset.mp3',
            user_id=user.id,
            tts_provider='minimax',
            storage_provider='local-cache',
            model='qwen-tts-2025-05-22',
            voice='Cherry',
            byte_length=803,
            generated_at=datetime(2026, 4, 11, 10, 30, 0),
            headers={'request_id': 'req-tts-1', 'trace_id': 'trace-tts-1'},
        )
        event = TTSMediaOutboxEvent.query.order_by(TTSMediaOutboxEvent.id.desc()).first()

        assert created is True
        assert asset.media_kind == 'example-audio'
        assert asset.media_id == 'example-asset.mp3'
        assert event is not None
        assert event.topic == 'tts.media.generated'
        assert event.aggregate_id == 'example-audio:example-asset.mp3'


def test_tts_media_outbox_publish_and_admin_projection_consume_flow(app):
    with app.app_context():
        user = _create_user(username='wave5-tts-media-projection-user')
        asset, created = record_tts_media_materialization(
            media_kind='tts-generate',
            media_id='generate-asset.mp3',
            user_id=user.id,
            tts_provider='azure',
            storage_provider='local-cache',
            model='azure-rest:audio-24khz-48kbitrate-mono-mp3',
            voice='en-US-AndrewMultilingualNeural',
            byte_length=912,
            generated_at=datetime(2026, 4, 11, 11, 0, 0),
            headers={'request_id': 'req-tts-2', 'trace_id': 'trace-tts-2'},
        )
        assert created is True

        publisher_channel = FakePublisherChannel()
        publish_outbox_batch(
            TTSMediaOutboxEvent,
            service_name='tts-media-service',
            connection=FakeConnection(publisher_channel),
        )
        assert len(publisher_channel.published) == 1
        message = publisher_channel.published[0]
        assert message['routing_key'] == 'tts.media.generated'

        consumer_channel = FakeConsumerChannel(message)
        processed = drain_tts_media_generated_queue(
            connection=FakeConnection(consumer_channel),
        )

        projected = AdminProjectedTTSMedia.query.filter_by(
            event_id=message['properties'].message_id
        ).first()
        inbox_record = AdminOpsInboxEvent.query.filter_by(
            event_id=message['properties'].message_id
        ).first()
        cursor = AdminProjectionCursor.query.filter_by(
            projection_name=TTS_MEDIA_PROJECTION
        ).first()
        stored_asset = TTSMediaAsset.query.filter_by(
            media_kind='tts-generate',
            media_id='generate-asset.mp3',
        ).first()

        assert processed == 1
        assert stored_asset is not None
        assert stored_asset.user_id == user.id
        assert projected is not None
        assert projected.user_id == user.id
        assert projected.media_kind == 'tts-generate'
        assert projected.media_id == 'generate-asset.mp3'
        assert projected.tts_provider == 'azure'
        assert projected.storage_provider == 'local-cache'
        assert projected.byte_length == 912
        assert inbox_record is not None
        assert inbox_record.status == 'processed'
        assert cursor is not None
        assert cursor.last_event_id == message['properties'].message_id
        assert consumer_channel.acks == [404]
        assert consumer_channel.nacks == []
