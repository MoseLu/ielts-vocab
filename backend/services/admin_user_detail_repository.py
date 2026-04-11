from __future__ import annotations

import logging
from datetime import datetime, timedelta

from platform_sdk.cross_service_boundary import (
    current_service_name,
    legacy_cross_service_fallback_enabled,
)
from platform_sdk.learning_core_admin_detail_internal_client import (
    fetch_learning_core_admin_book_progress_rows,
    fetch_learning_core_admin_chapter_progress_rows,
    fetch_learning_core_admin_favorite_words,
    fetch_learning_core_admin_session_word_events,
)
from service_models.learning_core_models import UserFavoriteWord
from service_models.admin_ops_models import (
    UserBookProgress,
    UserChapterProgress,
    UserLearningEvent,
)
from service_models.eventing_models import AdminProjectedDailySummary
from services.admin_projection_repository_support import wrong_word_model


LEARNING_CORE_SERVICE_NAME = 'learning-core-service'


class LearningCoreAdminDetailUnavailable(RuntimeError):
    def __init__(self, *, action: str):
        super().__init__(f'{LEARNING_CORE_SERVICE_NAME} unavailable for {action}')
        self.action = action


def _handle_learning_core_read_failure(*, action: str, error: Exception) -> None:
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
    raise LearningCoreAdminDetailUnavailable(action=action) from error


def list_user_book_progress_rows(user_id: int):
    try:
        return fetch_learning_core_admin_book_progress_rows(user_id)
    except Exception as exc:
        _handle_learning_core_read_failure(
            action='admin-detail-book-progress-read',
            error=exc,
        )
        return UserBookProgress.query.filter_by(user_id=user_id).all()


def list_user_chapter_progress_rows(
    user_id: int,
    *,
    book_id: str | None = None,
    limit: int | None = None,
):
    try:
        return fetch_learning_core_admin_chapter_progress_rows(
            user_id,
            book_id=book_id,
            limit=limit,
        )
    except Exception as exc:
        _handle_learning_core_read_failure(
            action='admin-detail-chapter-progress-read',
            error=exc,
        )
        query = UserChapterProgress.query.filter_by(user_id=user_id)
        if book_id:
            query = query.filter_by(book_id=book_id)
        query = query.order_by(UserChapterProgress.updated_at.desc())
        if limit is not None:
            query = query.limit(limit)
        return query.all()


def list_user_wrong_word_rows(user_id: int):
    model = wrong_word_model()
    return model.query.filter_by(user_id=user_id).all()


def list_user_favorite_word_rows(user_id: int):
    try:
        return fetch_learning_core_admin_favorite_words(user_id)
    except Exception as exc:
        _handle_learning_core_read_failure(
            action='admin-detail-favorite-words-read',
            error=exc,
        )
        return UserFavoriteWord.query.filter_by(user_id=user_id).order_by(
            UserFavoriteWord.updated_at.desc(),
            UserFavoriteWord.created_at.desc(),
        ).all()


def count_user_wrong_words(user_id: int) -> int:
    model = wrong_word_model()
    return model.query.filter_by(user_id=user_id).count()


def list_user_recent_summary_rows(user_id: int, *, limit: int = 5):
    return (
        AdminProjectedDailySummary.query
        .filter_by(user_id=user_id)
        .order_by(AdminProjectedDailySummary.generated_at.desc(), AdminProjectedDailySummary.id.desc())
        .limit(limit)
        .all()
    )


def list_learning_events_for_sessions(
    user_id: int,
    *,
    lower_bound: datetime,
    upper_bound: datetime,
):
    try:
        return fetch_learning_core_admin_session_word_events(
            user_id,
            start_at=lower_bound - timedelta(seconds=5),
            end_at=upper_bound + timedelta(seconds=5),
        )
    except Exception as exc:
        _handle_learning_core_read_failure(
            action='admin-detail-session-word-events-read',
            error=exc,
        )
        return (
            UserLearningEvent.query
            .filter(
                UserLearningEvent.user_id == user_id,
                UserLearningEvent.word.isnot(None),
                UserLearningEvent.event_type.in_(('quick_memory_review', 'wrong_word_recorded')),
                UserLearningEvent.occurred_at >= lower_bound - timedelta(seconds=5),
                UserLearningEvent.occurred_at <= upper_bound + timedelta(seconds=5),
            )
            .order_by(UserLearningEvent.occurred_at.asc(), UserLearningEvent.id.asc())
            .all()
        )
