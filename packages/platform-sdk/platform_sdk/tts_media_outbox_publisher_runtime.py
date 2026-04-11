from __future__ import annotations

from collections.abc import Sequence

from platform_sdk.domain_event_publisher import publish_outbox_batch
from platform_sdk.domain_worker_runtime import run_polling_worker
from platform_sdk.rabbitmq_runtime import rabbitmq_is_configured
from service_models.eventing_models import TTSMediaOutboxEvent


TTS_MEDIA_PUBLISHER_WORKER = 'tts-media-service.outbox-publisher'


def publish_tts_media_outbox_once(*, limit: int = 50) -> int:
    if not rabbitmq_is_configured(service_name='tts-media-service'):
        return 0
    return len(
        publish_outbox_batch(
            TTSMediaOutboxEvent,
            service_name='tts-media-service',
            worker_name=TTS_MEDIA_PUBLISHER_WORKER,
            limit=limit,
        )
    )


def run_tts_media_outbox_publisher(argv: Sequence[str] | None = None) -> int:
    return run_polling_worker(
        worker_name=TTS_MEDIA_PUBLISHER_WORKER,
        step=lambda batch_limit: publish_tts_media_outbox_once(limit=batch_limit),
        argv=argv,
    )
