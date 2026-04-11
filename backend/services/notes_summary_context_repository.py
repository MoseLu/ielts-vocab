from __future__ import annotations

from datetime import datetime

from service_models.learning_core_models import UserStudySession, UserWrongWord
from service_models.notes_models import NotesProjectedPromptRun, NotesProjectedStudySession, NotesProjectedWrongWord


def _use_projected_study_sessions() -> bool:
    projected_total = NotesProjectedStudySession.query.count()
    if projected_total <= 0:
        return False
    shared_total = UserStudySession.query.filter(UserStudySession.meaningful_clause()).count()
    return projected_total >= shared_total


def _study_session_model():
    return NotesProjectedStudySession if _use_projected_study_sessions() else UserStudySession


def _use_projected_wrong_words(user_id: int) -> bool:
    projected_total = NotesProjectedWrongWord.query.filter_by(user_id=user_id).count()
    if projected_total <= 0:
        return False
    shared_total = UserWrongWord.query.filter_by(user_id=user_id).count()
    return projected_total >= shared_total


def _wrong_word_model(user_id: int):
    return NotesProjectedWrongWord if _use_projected_wrong_words(user_id) else UserWrongWord


def list_study_sessions_in_window(
    user_id: int,
    *,
    start_at: datetime,
    end_before: datetime,
    descending: bool = False,
):
    study_session_model = _study_session_model()
    order_clause = (
        study_session_model.started_at.desc()
        if descending
        else study_session_model.started_at.asc()
    )
    return (
        study_session_model.query
        .filter_by(user_id=user_id)
        .filter(study_session_model.started_at >= start_at, study_session_model.started_at < end_before)
        .order_by(order_clause)
        .all()
    )


def list_study_sessions_before(
    user_id: int,
    *,
    end_before: datetime,
    descending: bool = False,
    require_words_studied: bool = False,
):
    study_session_model = _study_session_model()
    query = (
        study_session_model.query
        .filter_by(user_id=user_id)
        .filter(study_session_model.started_at < end_before)
    )
    if require_words_studied:
        query = query.filter(study_session_model.words_studied > 0)
    order_clause = (
        study_session_model.started_at.desc()
        if descending
        else study_session_model.started_at.asc()
    )
    return query.order_by(order_clause).all()


def list_wrong_words(user_id: int, *, limit: int | None = None):
    wrong_word_model = _wrong_word_model(user_id)
    query = wrong_word_model.query.filter_by(user_id=user_id)
    if limit is not None:
        query = query.limit(limit)
    return query.all()


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
