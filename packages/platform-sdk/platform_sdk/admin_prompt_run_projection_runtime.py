from __future__ import annotations

from collections.abc import Sequence

from platform_sdk.admin_prompt_run_projection_application import drain_ai_prompt_run_completed_queue
from platform_sdk.domain_worker_runtime import run_polling_worker
from platform_sdk.rabbitmq_runtime import rabbitmq_is_configured


ADMIN_PROMPT_RUN_PROJECTION_WORKER = 'admin-ops-service.prompt-run-projection-worker'


def drain_admin_prompt_run_projection_once(*, limit: int = 50) -> int:
    if not rabbitmq_is_configured(service_name='admin-ops-service'):
        return 0
    return drain_ai_prompt_run_completed_queue(limit=limit)


def run_admin_prompt_run_projection_worker(argv: Sequence[str] | None = None) -> int:
    return run_polling_worker(
        worker_name=ADMIN_PROMPT_RUN_PROJECTION_WORKER,
        step=lambda batch_limit: drain_admin_prompt_run_projection_once(limit=batch_limit),
        argv=argv,
    )
