from __future__ import annotations

from collections.abc import Sequence

from platform_sdk.ai_word_image_application import drain_game_word_image_generation_queue
from platform_sdk.domain_worker_runtime import run_polling_worker


AI_WORD_IMAGE_GENERATION_WORKER = 'ai-execution-service.word-image-generation-worker'


def drain_ai_word_image_generation_once(*, limit: int = 10) -> int:
    return drain_game_word_image_generation_queue(limit=limit)


def run_ai_word_image_generation_worker(argv: Sequence[str] | None = None) -> int:
    return run_polling_worker(
        worker_name=AI_WORD_IMAGE_GENERATION_WORKER,
        step=lambda batch_limit: drain_ai_word_image_generation_once(limit=batch_limit),
        argv=argv,
        default_limit=10,
        default_idle_sleep_seconds=1.0,
        default_error_sleep_seconds=5.0,
    )
