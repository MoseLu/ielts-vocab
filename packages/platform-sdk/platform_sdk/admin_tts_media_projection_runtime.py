from __future__ import annotations

from collections.abc import Sequence

from platform_sdk.admin_tts_media_projection_application import drain_tts_media_generated_queue
from platform_sdk.domain_worker_runtime import run_polling_worker
from platform_sdk.rabbitmq_runtime import rabbitmq_is_configured


ADMIN_TTS_MEDIA_PROJECTION_WORKER = 'admin-ops-service.tts-media-projection-worker'


def drain_admin_tts_media_projection_once(*, limit: int = 50) -> int:
    if not rabbitmq_is_configured(service_name='admin-ops-service'):
        return 0
    return drain_tts_media_generated_queue(limit=limit)


def run_admin_tts_media_projection_worker(argv: Sequence[str] | None = None) -> int:
    return run_polling_worker(
        worker_name=ADMIN_TTS_MEDIA_PROJECTION_WORKER,
        step=lambda batch_limit: drain_admin_tts_media_projection_once(limit=batch_limit),
        argv=argv,
    )
