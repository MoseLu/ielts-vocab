from __future__ import annotations

import logging
from datetime import datetime

from platform_sdk.cross_service_boundary import (
    current_service_name,
    legacy_cross_service_fallback_enabled,
)
from platform_sdk.learning_core_notes_context_internal_client import (
    fetch_learning_core_notes_study_sessions,
    fetch_learning_core_notes_wrong_words,
)
from platform_sdk.notes_projection_bootstrap import notes_projection_bootstrap_ready
from platform_sdk.notes_study_session_projection_application import (
    NOTES_STUDY_SESSION_CONTEXT_PROJECTION,
)
from platform_sdk.notes_wrong_word_projection_application import (
    NOTES_WRONG_WORD_CONTEXT_PROJECTION,
)
from service_models.learning_core_models import UserStudySession, UserWrongWord
from service_models.notes_models import NotesProjectedPromptRun, NotesProjectedStudySession, NotesProjectedWrongWord


LEARNING_CORE_SERVICE_NAME = 'learning-core-service'


class LearningCoreNotesContextUnavailable(RuntimeError):
    def __init__(self, *, action: str):
        super().__init__(f'{LEARNING_CORE_SERVICE_NAME} unavailable for {action}')
        self.action = action


def _handle_learning_core_context_read_failure(*, action: str, error: Exception) -> None:
    if legacy_cross_service_fallback_enabled():
        logging.warning(
            '[Boundary] using legacy local fallback: current_service=%s upstream=%s action=%s error=%s',
            current_service_name() or '<unset>',
            LEARNING_CORE_SERVICE_NAME,
            action,
            error,
        )
        return

    logging.warning(
        '[Boundary] strict internal contract blocked local fallback: current_service=%s upstream=%s action=%s error=%s',
        current_service_name() or '<unset>',
        LEARNING_CORE_SERVICE_NAME,
        action,
        error,
    )
    raise LearningCoreNotesContextUnavailable(action=action) from error


def _use_projected_study_sessions() -> bool:
    return notes_projection_bootstrap_ready(NOTES_STUDY_SESSION_CONTEXT_PROJECTION)


def _use_projected_wrong_words() -> bool:
    return notes_projection_bootstrap_ready(NOTES_WRONG_WORD_CONTEXT_PROJECTION)


def _prefer_learning_core_internal_reads() -> bool:
    return current_service_name() == 'notes-service'


def _list_shared_study_sessions_in_window(
    user_id: int,
    *,
    start_at: datetime,
    end_before: datetime,
    descending: bool = False,
):
    order_clause = UserStudySession.started_at.desc() if descending else UserStudySession.started_at.asc()
    return (
        UserStudySession.query
        .filter_by(user_id=user_id)
        .filter(UserStudySession.started_at >= start_at, UserStudySession.started_at < end_before)
        .order_by(order_clause)
        .all()
    )


def _list_projected_study_sessions_in_window(
    user_id: int,
    *,
    start_at: datetime,
    end_before: datetime,
    descending: bool = False,
):
    order_clause = (
        NotesProjectedStudySession.started_at.desc()
        if descending
        else NotesProjectedStudySession.started_at.asc()
    )
    return (
        NotesProjectedStudySession.query
        .filter_by(user_id=user_id)
        .filter(
            NotesProjectedStudySession.started_at >= start_at,
            NotesProjectedStudySession.started_at < end_before,
        )
        .order_by(order_clause)
        .all()
    )


def _list_shared_study_sessions_before(
    user_id: int,
    *,
    end_before: datetime,
    descending: bool = False,
    require_words_studied: bool = False,
):
    query = (
        UserStudySession.query
        .filter_by(user_id=user_id)
        .filter(UserStudySession.started_at < end_before)
    )
    if require_words_studied:
        query = query.filter(UserStudySession.words_studied > 0)
    order_clause = UserStudySession.started_at.desc() if descending else UserStudySession.started_at.asc()
    return query.order_by(order_clause).all()


def _list_projected_study_sessions_before(
    user_id: int,
    *,
    end_before: datetime,
    descending: bool = False,
    require_words_studied: bool = False,
):
    query = (
        NotesProjectedStudySession.query
        .filter_by(user_id=user_id)
        .filter(NotesProjectedStudySession.started_at < end_before)
    )
    if require_words_studied:
        query = query.filter(NotesProjectedStudySession.words_studied > 0)
    order_clause = (
        NotesProjectedStudySession.started_at.desc()
        if descending
        else NotesProjectedStudySession.started_at.asc()
    )
    return query.order_by(order_clause).all()


def _list_shared_wrong_words(user_id: int, *, limit: int | None = None):
    query = UserWrongWord.query.filter_by(user_id=user_id)
    if limit is not None:
        query = query.limit(limit)
    return query.all()


def _list_projected_wrong_words(user_id: int, *, limit: int | None = None):
    query = NotesProjectedWrongWord.query.filter_by(user_id=user_id)
    if limit is not None:
        query = query.limit(limit)
    return query.all()


def list_study_sessions_in_window(
    user_id: int,
    *,
    start_at: datetime,
    end_before: datetime,
    descending: bool = False,
):
    if _use_projected_study_sessions():
        return _list_projected_study_sessions_in_window(
            user_id,
            start_at=start_at,
            end_before=end_before,
            descending=descending,
        )
    if _prefer_learning_core_internal_reads():
        try:
            return fetch_learning_core_notes_study_sessions(
                user_id,
                start_at=start_at,
                end_before=end_before,
                descending=descending,
            )
        except Exception as exc:
            _handle_learning_core_context_read_failure(
                action='notes-summary-study-sessions-read',
                error=exc,
            )
    return _list_shared_study_sessions_in_window(
        user_id,
        start_at=start_at,
        end_before=end_before,
        descending=descending,
    )


def list_study_sessions_before(
    user_id: int,
    *,
    end_before: datetime,
    descending: bool = False,
    require_words_studied: bool = False,
):
    if _use_projected_study_sessions():
        return _list_projected_study_sessions_before(
            user_id,
            end_before=end_before,
            descending=descending,
            require_words_studied=require_words_studied,
        )
    if _prefer_learning_core_internal_reads():
        try:
            return fetch_learning_core_notes_study_sessions(
                user_id,
                end_before=end_before,
                descending=descending,
                require_words_studied=require_words_studied,
            )
        except Exception as exc:
            _handle_learning_core_context_read_failure(
                action='notes-summary-study-sessions-read',
                error=exc,
            )
    return _list_shared_study_sessions_before(
        user_id,
        end_before=end_before,
        descending=descending,
        require_words_studied=require_words_studied,
    )


def list_wrong_words(user_id: int, *, limit: int | None = None):
    if _use_projected_wrong_words():
        return _list_projected_wrong_words(user_id, limit=limit)
    if _prefer_learning_core_internal_reads():
        try:
            return fetch_learning_core_notes_wrong_words(user_id, limit=limit)
        except Exception as exc:
            _handle_learning_core_context_read_failure(
                action='notes-summary-wrong-words-read',
                error=exc,
            )
    return _list_shared_wrong_words(user_id, limit=limit)


def list_prompt_runs_in_window(
    user_id: int,
    *,
    start_at: datetime,
    end_before: datetime,
    descending: bool = False,
):
    order_clause = (
        NotesProjectedPromptRun.completed_at.desc()
        if descending
        else NotesProjectedPromptRun.completed_at.asc()
    )
    return (
        NotesProjectedPromptRun.query
        .filter_by(user_id=user_id)
        .filter(NotesProjectedPromptRun.completed_at >= start_at, NotesProjectedPromptRun.completed_at < end_before)
        .order_by(order_clause)
        .all()
    )
