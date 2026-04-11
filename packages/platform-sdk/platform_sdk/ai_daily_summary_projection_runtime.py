from __future__ import annotations

from collections.abc import Sequence

from platform_sdk.ai_daily_summary_projection_application import (
    drain_notes_summary_generated_queue,
)
from platform_sdk.domain_worker_runtime import run_polling_worker
from platform_sdk.rabbitmq_runtime import rabbitmq_is_configured


AI_DAILY_SUMMARY_PROJECTION_WORKER = 'ai-execution-service.daily-summary-projection-worker'


def drain_ai_daily_summary_projection_once(*, limit: int = 50) -> int:
    if not rabbitmq_is_configured(service_name='ai-execution-service'):
        return 0
    return drain_notes_summary_generated_queue(limit=limit)


def run_ai_daily_summary_projection_worker(argv: Sequence[str] | None = None) -> int:
    return run_polling_worker(
        worker_name=AI_DAILY_SUMMARY_PROJECTION_WORKER,
        step=lambda batch_limit: drain_ai_daily_summary_projection_once(limit=batch_limit),
        argv=argv,
    )
