from __future__ import annotations

import json
from datetime import datetime

from sqlalchemy.exc import SQLAlchemyError

from platform_sdk.admin_study_session_projection_application import (
    STUDY_SESSION_ANALYTICS_PROJECTION,
    upsert_projected_study_session,
)
from platform_sdk.admin_user_projection_application import (
    USER_DIRECTORY_PROJECTION,
    upsert_projected_user,
)
from platform_sdk.admin_wrong_word_projection_application import (
    WRONG_WORD_DIRECTORY_PROJECTION,
    upsert_projected_wrong_word,
)
from service_models.admin_ops_models import User, UserStudySession, UserWrongWord
from service_models.eventing_models import AdminProjectionCursor


BOOTSTRAP_TOPIC = '__bootstrap__'


def _query_session(model):
    return model.query.session


def bootstrap_projection_marker_name(projection_name: str) -> str:
    return f'{projection_name}.bootstrap'


def projection_bootstrap_ready(projection_name: str) -> bool:
    marker = AdminProjectionCursor.query.filter_by(
        projection_name=bootstrap_projection_marker_name(projection_name)
    ).first()
    return bool(
        marker is not None
        and marker.last_topic == BOOTSTRAP_TOPIC
        and marker.last_processed_at is not None
    )


def _user_payload(user) -> dict:
    return {
        'user_id': user.id,
        'username': user.username,
        'email': user.email,
        'avatar_url': user.avatar_url,
        'is_admin': user.is_admin,
        'created_at': user.created_at.isoformat() if user.created_at else None,
    }


def sync_admin_projected_user_snapshot(user, *, session=None) -> bool:
    if user is None:
        return False
    try:
        if not projection_bootstrap_ready(USER_DIRECTORY_PROJECTION):
            return False
    except SQLAlchemyError:
        return False
    upsert_projected_user(_user_payload(user), session=session)
    return True


def _parse_dimension_states(value):
    if isinstance(value, dict):
        return value
    if isinstance(value, (bytes, bytearray)):
        value = value.decode('utf-8')
    if isinstance(value, str) and value.strip():
        return json.loads(value)
    return {}


def _touch_projection_cursor(projection_name: str, *, session, bootstrap_started_at: datetime) -> None:
    event_id = f'bootstrap:{projection_name}:{bootstrap_started_at.strftime("%Y%m%d%H%M%S")}'
    for cursor_name in (
        projection_name,
        bootstrap_projection_marker_name(projection_name),
    ):
        cursor = AdminProjectionCursor.query.filter_by(projection_name=cursor_name).first()
        if cursor is None:
            cursor = AdminProjectionCursor(projection_name=cursor_name)
            session.add(cursor)
        cursor.last_event_id = event_id
        cursor.last_topic = BOOTSTRAP_TOPIC
        cursor.last_processed_at = datetime.utcnow()


def bootstrap_admin_projection_snapshots(*, session=None) -> dict[str, int]:
    session = session or _query_session(AdminProjectionCursor)
    bootstrap_started_at = datetime.utcnow()
    counts = {
        'users': 0,
        'study_sessions': 0,
        'wrong_words': 0,
    }

    for user in User.query.order_by(User.id.asc()).all():
        upsert_projected_user(_user_payload(user), session=session)
        counts['users'] += 1
    _touch_projection_cursor(
        USER_DIRECTORY_PROJECTION,
        session=session,
        bootstrap_started_at=bootstrap_started_at,
    )

    for study_session in UserStudySession.query.order_by(UserStudySession.id.asc()).all():
        upsert_projected_study_session({
            'session_id': study_session.id,
            'user_id': study_session.user_id,
            'mode': study_session.mode,
            'book_id': study_session.book_id,
            'chapter_id': study_session.chapter_id,
            'words_studied': study_session.words_studied,
            'correct_count': study_session.correct_count,
            'wrong_count': study_session.wrong_count,
            'duration_seconds': study_session.duration_seconds,
            'started_at': study_session.started_at.isoformat() if study_session.started_at else None,
            'ended_at': study_session.ended_at.isoformat() if study_session.ended_at else None,
        }, session=session)
        counts['study_sessions'] += 1
    _touch_projection_cursor(
        STUDY_SESSION_ANALYTICS_PROJECTION,
        session=session,
        bootstrap_started_at=bootstrap_started_at,
    )

    for wrong_word in UserWrongWord.query.order_by(UserWrongWord.id.asc()).all():
        upsert_projected_wrong_word({
            'user_id': wrong_word.user_id,
            'word': wrong_word.word,
            'phonetic': wrong_word.phonetic,
            'pos': wrong_word.pos,
            'definition': wrong_word.definition,
            'wrong_count': wrong_word.wrong_count,
            'listening_correct': wrong_word.listening_correct,
            'listening_wrong': wrong_word.listening_wrong,
            'meaning_correct': wrong_word.meaning_correct,
            'meaning_wrong': wrong_word.meaning_wrong,
            'dictation_correct': wrong_word.dictation_correct,
            'dictation_wrong': wrong_word.dictation_wrong,
            'dimension_states': _parse_dimension_states(wrong_word.dimension_state),
            'updated_at': wrong_word.updated_at.isoformat() if wrong_word.updated_at else None,
        }, session=session)
        counts['wrong_words'] += 1
    _touch_projection_cursor(
        WRONG_WORD_DIRECTORY_PROJECTION,
        session=session,
        bootstrap_started_at=bootstrap_started_at,
    )

    session.commit()
    return counts
