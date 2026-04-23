from __future__ import annotations

from collections.abc import Sequence

from platform_sdk.domain_worker_runtime import run_multi_step_polling_worker
from platform_sdk.notes_outbox_publisher_runtime import publish_notes_outbox_once
from platform_sdk.notes_prompt_run_projection_runtime import (
    drain_notes_prompt_run_projection_once,
)
from platform_sdk.notes_study_session_projection_runtime import (
    drain_notes_study_session_projection_once,
)
from platform_sdk.notes_wrong_word_projection_runtime import (
    drain_notes_wrong_word_projection_once,
)


NOTES_DOMAIN_WORKER = 'notes-service.domain-worker'


def run_notes_domain_worker(argv: Sequence[str] | None = None) -> int:
    return run_multi_step_polling_worker(
        worker_name=NOTES_DOMAIN_WORKER,
        steps=(
            ('notes-outbox-publisher', lambda batch_limit: publish_notes_outbox_once(limit=batch_limit)),
            (
                'notes-study-session-projection-worker',
                lambda batch_limit: drain_notes_study_session_projection_once(limit=batch_limit),
            ),
            (
                'notes-wrong-word-projection-worker',
                lambda batch_limit: drain_notes_wrong_word_projection_once(limit=batch_limit),
            ),
            (
                'notes-prompt-run-projection-worker',
                lambda batch_limit: drain_notes_prompt_run_projection_once(limit=batch_limit),
            ),
        ),
        argv=argv,
    )
