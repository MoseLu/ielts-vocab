from __future__ import annotations

from collections.abc import Sequence

from platform_sdk.admin_daily_summary_projection_runtime import (
    drain_admin_daily_summary_projection_once,
)
from platform_sdk.admin_prompt_run_projection_runtime import (
    drain_admin_prompt_run_projection_once,
)
from platform_sdk.admin_study_session_projection_runtime import (
    drain_admin_study_session_projection_once,
)
from platform_sdk.admin_tts_media_projection_runtime import (
    drain_admin_tts_media_projection_once,
)
from platform_sdk.admin_user_projection_runtime import (
    drain_admin_user_projection_once,
)
from platform_sdk.admin_wrong_word_projection_runtime import (
    drain_admin_wrong_word_projection_once,
)
from platform_sdk.domain_worker_runtime import run_multi_step_polling_worker


ADMIN_OPS_DOMAIN_WORKER = 'admin-ops-service.domain-worker'


def run_admin_ops_domain_worker(argv: Sequence[str] | None = None) -> int:
    return run_multi_step_polling_worker(
        worker_name=ADMIN_OPS_DOMAIN_WORKER,
        steps=(
            (
                'admin-user-projection-worker',
                lambda batch_limit: drain_admin_user_projection_once(limit=batch_limit),
            ),
            (
                'admin-study-session-projection-worker',
                lambda batch_limit: drain_admin_study_session_projection_once(limit=batch_limit),
            ),
            (
                'admin-daily-summary-projection-worker',
                lambda batch_limit: drain_admin_daily_summary_projection_once(limit=batch_limit),
            ),
            (
                'admin-prompt-run-projection-worker',
                lambda batch_limit: drain_admin_prompt_run_projection_once(limit=batch_limit),
            ),
            (
                'admin-tts-media-projection-worker',
                lambda batch_limit: drain_admin_tts_media_projection_once(limit=batch_limit),
            ),
            (
                'admin-wrong-word-projection-worker',
                lambda batch_limit: drain_admin_wrong_word_projection_once(limit=batch_limit),
            ),
        ),
        argv=argv,
    )
