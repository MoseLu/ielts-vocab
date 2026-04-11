from __future__ import annotations

from service_models.admin_ops_models import User, UserStudySession, UserWrongWord
from service_models.eventing_models import (
    AdminProjectedStudySession,
    AdminProjectedUser,
    AdminProjectedWrongWord,
)


def _use_projected_user_counts() -> bool:
    projected_total = AdminProjectedUser.query.count()
    if projected_total <= 0:
        return False
    return projected_total >= User.query.count()


def user_count_model():
    return AdminProjectedUser if _use_projected_user_counts() else User


def _use_projected_study_sessions() -> bool:
    projected_total = AdminProjectedStudySession.query.filter(
        AdminProjectedStudySession.analytics_clause()
    ).count()
    if projected_total <= 0:
        return False
    shared_total = UserStudySession.query.filter(UserStudySession.analytics_clause()).count()
    return projected_total >= shared_total


def study_session_model():
    return AdminProjectedStudySession if _use_projected_study_sessions() else UserStudySession


def _use_projected_wrong_words() -> bool:
    projected_total = AdminProjectedWrongWord.query.count()
    if projected_total <= 0:
        return False
    return projected_total >= UserWrongWord.query.count()


def wrong_word_model():
    return AdminProjectedWrongWord if _use_projected_wrong_words() else UserWrongWord
