from __future__ import annotations

from platform_sdk.admin_projection_bootstrap import (
    projection_bootstrap_ready,
)
from platform_sdk.admin_study_session_projection_application import (
    STUDY_SESSION_ANALYTICS_PROJECTION,
)
from platform_sdk.admin_user_projection_application import USER_DIRECTORY_PROJECTION
from platform_sdk.admin_wrong_word_projection_application import (
    WRONG_WORD_DIRECTORY_PROJECTION,
)
from platform_sdk.cross_service_boundary import legacy_cross_service_fallback_enabled
from service_models.admin_ops_models import User, UserStudySession, UserWrongWord
from service_models.eventing_models import (
    AdminProjectedStudySession,
    AdminProjectedUser,
    AdminProjectedWrongWord,
)


class AdminProjectionUnavailable(RuntimeError):
    def __init__(self, action: str, projection_name: str):
        super().__init__(f'{projection_name} projection is not bootstrapped for {action}')
        self.action = action
        self.projection_name = projection_name


def _projection_model_or_legacy(projection_name: str, projected_model, legacy_model, *, action: str):
    if projection_bootstrap_ready(projection_name):
        return projected_model
    if legacy_cross_service_fallback_enabled():
        return legacy_model
    raise AdminProjectionUnavailable(action, projection_name)


def user_directory_projection_ready() -> bool:
    return projection_bootstrap_ready(USER_DIRECTORY_PROJECTION)


def user_directory_model():
    return _projection_model_or_legacy(
        USER_DIRECTORY_PROJECTION,
        AdminProjectedUser,
        User,
        action='admin-user-directory',
    )


def _use_projected_user_counts() -> bool:
    return user_directory_projection_ready()


def user_count_model():
    return user_directory_model()


def _use_projected_study_sessions() -> bool:
    return projection_bootstrap_ready(STUDY_SESSION_ANALYTICS_PROJECTION)


def study_session_model():
    return _projection_model_or_legacy(
        STUDY_SESSION_ANALYTICS_PROJECTION,
        AdminProjectedStudySession,
        UserStudySession,
        action='admin-study-session-analytics',
    )


def _use_projected_wrong_words() -> bool:
    return projection_bootstrap_ready(WRONG_WORD_DIRECTORY_PROJECTION)


def wrong_word_model():
    return _projection_model_or_legacy(
        WRONG_WORD_DIRECTORY_PROJECTION,
        AdminProjectedWrongWord,
        UserWrongWord,
        action='admin-wrong-word-directory',
    )
