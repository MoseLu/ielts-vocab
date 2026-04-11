from __future__ import annotations

from collections.abc import Sequence

from platform_sdk.domain_worker_runtime import run_polling_worker
from platform_sdk.notes_prompt_run_projection_application import (
    drain_notes_ai_prompt_run_completed_queue,
)
from platform_sdk.rabbitmq_runtime import rabbitmq_is_configured


NOTES_PROMPT_RUN_PROJECTION_WORKER = 'notes-service.prompt-run-projection-worker'


def drain_notes_prompt_run_projection_once(*, limit: int = 50) -> int:
    if not rabbitmq_is_configured(service_name='notes-service'):
        return 0
    return drain_notes_ai_prompt_run_completed_queue(limit=limit)


def run_notes_prompt_run_projection_worker(argv: Sequence[str] | None = None) -> int:
    return run_polling_worker(
        worker_name=NOTES_PROMPT_RUN_PROJECTION_WORKER,
        step=lambda batch_limit: drain_notes_prompt_run_projection_once(limit=batch_limit),
        argv=argv,
    )
