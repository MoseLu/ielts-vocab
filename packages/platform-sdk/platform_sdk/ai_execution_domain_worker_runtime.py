from __future__ import annotations

from collections.abc import Sequence

from platform_sdk.ai_daily_summary_projection_runtime import (
    drain_ai_daily_summary_projection_once,
)
from platform_sdk.ai_execution_outbox_publisher_runtime import (
    publish_ai_execution_outbox_once,
)
from platform_sdk.ai_wrong_word_projection_runtime import (
    drain_ai_wrong_word_projection_once,
)
from platform_sdk.domain_worker_runtime import run_multi_step_polling_worker


AI_EXECUTION_DOMAIN_WORKER = 'ai-execution-service.domain-worker'


def run_ai_execution_domain_worker(argv: Sequence[str] | None = None) -> int:
    return run_multi_step_polling_worker(
        worker_name=AI_EXECUTION_DOMAIN_WORKER,
        steps=(
            (
                'ai-execution-outbox-publisher',
                lambda batch_limit: publish_ai_execution_outbox_once(limit=batch_limit),
            ),
            (
                'ai-wrong-word-projection-worker',
                lambda batch_limit: drain_ai_wrong_word_projection_once(limit=batch_limit),
            ),
            (
                'ai-daily-summary-projection-worker',
                lambda batch_limit: drain_ai_daily_summary_projection_once(limit=batch_limit),
            ),
        ),
        argv=argv,
    )
