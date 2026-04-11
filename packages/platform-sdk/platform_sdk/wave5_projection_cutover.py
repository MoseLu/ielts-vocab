from __future__ import annotations

from platform_sdk.admin_projection_bootstrap import (
    bootstrap_admin_projection_snapshots,
    projection_bootstrap_ready,
)
from platform_sdk.admin_study_session_projection_application import (
    STUDY_SESSION_ANALYTICS_PROJECTION,
)
from platform_sdk.admin_user_projection_application import USER_DIRECTORY_PROJECTION
from platform_sdk.admin_wrong_word_projection_application import (
    WRONG_WORD_DIRECTORY_PROJECTION,
)
from platform_sdk.ai_daily_summary_projection_application import (
    AI_DAILY_SUMMARY_CONTEXT_PROJECTION,
)
from platform_sdk.ai_projection_bootstrap import (
    ai_projection_bootstrap_ready,
    bootstrap_ai_projection_snapshots,
)
from platform_sdk.ai_wrong_word_projection_application import (
    AI_WRONG_WORD_CONTEXT_PROJECTION,
)
from platform_sdk.notes_projection_bootstrap import (
    bootstrap_notes_projection_snapshots,
    notes_projection_bootstrap_ready,
)
from platform_sdk.notes_study_session_projection_application import (
    NOTES_STUDY_SESSION_CONTEXT_PROJECTION,
)
from platform_sdk.notes_wrong_word_projection_application import (
    NOTES_WRONG_WORD_CONTEXT_PROJECTION,
)
from service_models.admin_ops_models import User
from service_models.ai_execution_models import AIProjectedDailySummary, AIProjectedWrongWord
from service_models.eventing_models import (
    AdminProjectedStudySession,
    AdminProjectedUser,
    AdminProjectedWrongWord,
)
from service_models.learning_core_models import UserStudySession, UserWrongWord
from service_models.notes_models import (
    NotesProjectedStudySession,
    NotesProjectedWrongWord,
    UserDailySummary,
)


def _projection_status(
    *,
    projection_name: str,
    source_count: int,
    projected_count: int,
    ready: bool,
) -> dict[str, object]:
    counts_match = projected_count == source_count
    return {
        'projection_name': projection_name,
        'source_count': source_count,
        'projected_count': projected_count,
        'counts_match': counts_match,
        'ready': ready,
        'ok': bool(ready and counts_match),
    }


def collect_wave5_projection_cutover_status() -> dict[str, object]:
    admin = {
        'user_directory': _projection_status(
            projection_name=USER_DIRECTORY_PROJECTION,
            source_count=User.query.count(),
            projected_count=AdminProjectedUser.query.count(),
            ready=projection_bootstrap_ready(USER_DIRECTORY_PROJECTION),
        ),
        'study_sessions': _projection_status(
            projection_name=STUDY_SESSION_ANALYTICS_PROJECTION,
            source_count=UserStudySession.query.count(),
            projected_count=AdminProjectedStudySession.query.count(),
            ready=projection_bootstrap_ready(STUDY_SESSION_ANALYTICS_PROJECTION),
        ),
        'wrong_words': _projection_status(
            projection_name=WRONG_WORD_DIRECTORY_PROJECTION,
            source_count=UserWrongWord.query.count(),
            projected_count=AdminProjectedWrongWord.query.count(),
            ready=projection_bootstrap_ready(WRONG_WORD_DIRECTORY_PROJECTION),
        ),
    }
    notes = {
        'study_sessions': _projection_status(
            projection_name=NOTES_STUDY_SESSION_CONTEXT_PROJECTION,
            source_count=UserStudySession.query.count(),
            projected_count=NotesProjectedStudySession.query.count(),
            ready=notes_projection_bootstrap_ready(NOTES_STUDY_SESSION_CONTEXT_PROJECTION),
        ),
        'wrong_words': _projection_status(
            projection_name=NOTES_WRONG_WORD_CONTEXT_PROJECTION,
            source_count=UserWrongWord.query.count(),
            projected_count=NotesProjectedWrongWord.query.count(),
            ready=notes_projection_bootstrap_ready(NOTES_WRONG_WORD_CONTEXT_PROJECTION),
        ),
    }
    ai = {
        'wrong_words': _projection_status(
            projection_name=AI_WRONG_WORD_CONTEXT_PROJECTION,
            source_count=UserWrongWord.query.count(),
            projected_count=AIProjectedWrongWord.query.count(),
            ready=ai_projection_bootstrap_ready(AI_WRONG_WORD_CONTEXT_PROJECTION),
        ),
        'daily_summaries': _projection_status(
            projection_name=AI_DAILY_SUMMARY_CONTEXT_PROJECTION,
            source_count=UserDailySummary.query.count(),
            projected_count=AIProjectedDailySummary.query.count(),
            ready=ai_projection_bootstrap_ready(AI_DAILY_SUMMARY_CONTEXT_PROJECTION),
        ),
    }
    return {
        'admin': admin,
        'notes': notes,
        'ai': ai,
        'ok': all(
            item['ok']
            for group in (admin, notes, ai)
            for item in group.values()
        ),
    }


def run_wave5_projection_cutover(*, bootstrap: bool = True) -> dict[str, object]:
    bootstrap_summary = None
    if bootstrap:
        bootstrap_summary = {
            'admin': bootstrap_admin_projection_snapshots(),
            'notes': bootstrap_notes_projection_snapshots(),
            'ai': bootstrap_ai_projection_snapshots(),
        }
    status = collect_wave5_projection_cutover_status()
    status['bootstrap_ran'] = bool(bootstrap)
    status['bootstrap'] = bootstrap_summary
    return status
