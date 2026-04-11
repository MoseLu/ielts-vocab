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
from service_models.admin_ops_models import User, UserStudySession, UserWrongWord
from service_models.eventing_models import (
    AdminProjectedStudySession,
    AdminProjectedUser,
    AdminProjectedWrongWord,
)


def user_directory_projection_ready() -> bool:
    return projection_bootstrap_ready(USER_DIRECTORY_PROJECTION)


def user_directory_model():
    return AdminProjectedUser if user_directory_projection_ready() else User


def _use_projected_user_counts() -> bool:
    return user_directory_projection_ready()


def user_count_model():
    return user_directory_model()


def _use_projected_study_sessions() -> bool:
    return projection_bootstrap_ready(STUDY_SESSION_ANALYTICS_PROJECTION)


def study_session_model():
    return AdminProjectedStudySession if _use_projected_study_sessions() else UserStudySession


def _use_projected_wrong_words() -> bool:
    return projection_bootstrap_ready(WRONG_WORD_DIRECTORY_PROJECTION)


def wrong_word_model():
    return AdminProjectedWrongWord if _use_projected_wrong_words() else UserWrongWord
