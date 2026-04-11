from __future__ import annotations

import json
from datetime import datetime, timedelta

from models import (
    AdminProjectedStudySession,
    AdminProjectedUser,
    AdminProjectedWrongWord,
    AdminProjectionCursor,
    User,
    UserStudySession,
    UserWrongWord,
    db,
)
from platform_sdk.admin_projection_bootstrap import (
    BOOTSTRAP_TOPIC,
    bootstrap_admin_projection_snapshots,
    bootstrap_projection_marker_name,
)
from platform_sdk.admin_study_session_projection_application import (
    STUDY_SESSION_ANALYTICS_PROJECTION,
)
from platform_sdk.admin_user_projection_application import USER_DIRECTORY_PROJECTION
from platform_sdk.admin_wrong_word_projection_application import (
    WRONG_WORD_DIRECTORY_PROJECTION,
)


def _create_user(*, username: str) -> User:
    user = User(username=username, email=f'{username}@example.com')
    user.set_password('password123')
    db.session.add(user)
    db.session.commit()
    return user


def _dimension_states(*, wrong_count: int, last_wrong_at: str) -> dict:
    return {
        'recognition': {
            'history_wrong': wrong_count,
            'pass_streak': 0,
            'last_wrong_at': last_wrong_at,
            'last_pass_at': None,
        },
        'meaning': {'history_wrong': 0, 'pass_streak': 0, 'last_wrong_at': None, 'last_pass_at': None},
        'listening': {'history_wrong': 0, 'pass_streak': 0, 'last_wrong_at': None, 'last_pass_at': None},
        'dictation': {'history_wrong': 0, 'pass_streak': 0, 'last_wrong_at': None, 'last_pass_at': None},
    }


def test_bootstrap_admin_projection_snapshots_backfills_state_and_cursors(app):
    with app.app_context():
        user = _create_user(username='bootstrap-admin-user')
        now = datetime.utcnow()
        db.session.add(UserStudySession(
            id=431,
            user_id=user.id,
            mode='meaning',
            book_id='ielts_reading_premium',
            chapter_id='2',
            words_studied=8,
            correct_count=6,
            wrong_count=2,
            duration_seconds=480,
            started_at=now - timedelta(hours=1),
            ended_at=now - timedelta(hours=1) + timedelta(minutes=8),
        ))
        db.session.add(UserWrongWord(
            user_id=user.id,
            word='compile',
            phonetic='/kəmˈpaɪl/',
            pos='v.',
            definition='collect information',
            wrong_count=3,
            meaning_wrong=2,
            dimension_state=json.dumps(_dimension_states(
                wrong_count=3,
                last_wrong_at='2026-04-11T11:00:00+00:00',
            ), ensure_ascii=False),
            updated_at=now,
        ))
        db.session.commit()

        expected_counts = {
            'users': User.query.count(),
            'study_sessions': UserStudySession.query.count(),
            'wrong_words': UserWrongWord.query.count(),
        }

        summary = bootstrap_admin_projection_snapshots()

        projected_user = db.session.get(AdminProjectedUser, user.id)
        projected_session = db.session.get(AdminProjectedStudySession, 431)
        projected_wrong_word = AdminProjectedWrongWord.query.filter_by(
            user_id=user.id,
            word='compile',
        ).first()

        assert summary == expected_counts
        assert AdminProjectedUser.query.count() == expected_counts['users']
        assert AdminProjectedStudySession.query.count() == expected_counts['study_sessions']
        assert AdminProjectedWrongWord.query.count() == expected_counts['wrong_words']
        assert projected_user is not None
        assert projected_user.username == 'bootstrap-admin-user'
        assert projected_session is not None
        assert projected_session.mode == 'meaning'
        assert projected_session.duration_seconds == 480
        assert projected_wrong_word is not None
        assert projected_wrong_word.definition == 'collect information'
        assert json.loads(projected_wrong_word.dimension_state)['recognition']['history_wrong'] == 3

        cursors = {
            cursor.projection_name: cursor
            for cursor in AdminProjectionCursor.query.all()
        }
        assert cursors[USER_DIRECTORY_PROJECTION].last_topic == BOOTSTRAP_TOPIC
        assert cursors[STUDY_SESSION_ANALYTICS_PROJECTION].last_topic == BOOTSTRAP_TOPIC
        assert cursors[WRONG_WORD_DIRECTORY_PROJECTION].last_topic == BOOTSTRAP_TOPIC
        assert cursors[bootstrap_projection_marker_name(USER_DIRECTORY_PROJECTION)].last_topic == BOOTSTRAP_TOPIC
        assert cursors[bootstrap_projection_marker_name(STUDY_SESSION_ANALYTICS_PROJECTION)].last_topic == BOOTSTRAP_TOPIC
        assert cursors[bootstrap_projection_marker_name(WRONG_WORD_DIRECTORY_PROJECTION)].last_topic == BOOTSTRAP_TOPIC
        assert cursors[USER_DIRECTORY_PROJECTION].last_event_id.startswith('bootstrap:')


def test_bootstrap_admin_projection_snapshots_is_idempotent_and_refreshes_rows(app):
    with app.app_context():
        user = _create_user(username='bootstrap-admin-refresh-user')
        now = datetime.utcnow()
        db.session.add(UserStudySession(
            id=532,
            user_id=user.id,
            mode='listening',
            book_id='legacy-book',
            chapter_id='1',
            words_studied=5,
            correct_count=3,
            wrong_count=2,
            duration_seconds=300,
            started_at=now - timedelta(hours=3),
            ended_at=now - timedelta(hours=3) + timedelta(minutes=5),
        ))
        db.session.add(UserWrongWord(
            user_id=user.id,
            word='legacy',
            definition='old definition',
            wrong_count=1,
            dimension_state=json.dumps(_dimension_states(
                wrong_count=1,
                last_wrong_at='2026-04-10T11:00:00+00:00',
            ), ensure_ascii=False),
            updated_at=now - timedelta(hours=2),
        ))
        db.session.commit()

        first_summary = bootstrap_admin_projection_snapshots()

        user.avatar_url = 'https://example.com/avatar.png'
        study_session = db.session.get(UserStudySession, 532)
        wrong_word = UserWrongWord.query.filter_by(user_id=user.id, word='legacy').first()
        assert study_session is not None and wrong_word is not None
        study_session.mode = 'quickmemory'
        study_session.duration_seconds = 720
        wrong_word.definition = 'fresh definition'
        wrong_word.wrong_count = 4
        wrong_word.dimension_state = json.dumps(_dimension_states(
            wrong_count=4,
            last_wrong_at='2026-04-11T12:00:00+00:00',
        ), ensure_ascii=False)
        db.session.commit()

        second_summary = bootstrap_admin_projection_snapshots()

        projected_user = db.session.get(AdminProjectedUser, user.id)
        projected_session = db.session.get(AdminProjectedStudySession, 532)
        projected_wrong_word = AdminProjectedWrongWord.query.filter_by(
            user_id=user.id,
            word='legacy',
        ).first()

        assert first_summary == second_summary
        assert AdminProjectedUser.query.count() == User.query.count()
        assert AdminProjectedStudySession.query.count() == UserStudySession.query.count()
        assert AdminProjectedWrongWord.query.count() == UserWrongWord.query.count()
        assert projected_user is not None
        assert projected_user.avatar_url == 'https://example.com/avatar.png'
        assert projected_session is not None
        assert projected_session.mode == 'quickmemory'
        assert projected_session.duration_seconds == 720
        assert projected_wrong_word is not None
        assert projected_wrong_word.definition == 'fresh definition'
        assert projected_wrong_word.wrong_count == 4
