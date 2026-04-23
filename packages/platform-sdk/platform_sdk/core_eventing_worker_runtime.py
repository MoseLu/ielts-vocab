from __future__ import annotations

from collections.abc import Sequence

from platform_sdk.domain_worker_runtime import run_multi_step_polling_worker
from platform_sdk.identity_outbox_publisher_runtime import publish_identity_outbox_once
from platform_sdk.learning_core_outbox_publisher_runtime import (
    publish_learning_core_outbox_once,
)
from platform_sdk.tts_media_outbox_publisher_runtime import publish_tts_media_outbox_once


CORE_EVENTING_WORKER = 'core-eventing-worker'


def run_core_eventing_worker(argv: Sequence[str] | None = None) -> int:
    return run_multi_step_polling_worker(
        worker_name=CORE_EVENTING_WORKER,
        steps=(
            (
                'identity-outbox-publisher',
                'identity-service',
                lambda batch_limit: publish_identity_outbox_once(limit=batch_limit),
            ),
            (
                'learning-core-outbox-publisher',
                'learning-core-service',
                lambda batch_limit: publish_learning_core_outbox_once(limit=batch_limit),
            ),
            (
                'tts-media-outbox-publisher',
                'tts-media-service',
                lambda batch_limit: publish_tts_media_outbox_once(limit=batch_limit),
            ),
        ),
        argv=argv,
    )
