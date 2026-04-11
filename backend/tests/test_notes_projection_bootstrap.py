from __future__ import annotations

import json
from datetime import datetime, timedelta

from models import (
    NotesProjectedStudySession,
    NotesProjectedWrongWord,
    NotesProjectionCursor,
    User,
    UserStudySession,
    UserWrongWord,
    db,
)
from platform_sdk.notes_projection_bootstrap import (
    BOOTSTRAP_TOPIC,
    bootstrap_notes_projection_snapshots,
    notes_bootstrap_marker_name,
)
from platform_sdk.notes_study_session_projection_application import (
    NOTES_STUDY_SESSION_CONTEXT_PROJECTION,
)
from platform_sdk.notes_wrong_word_projection_application import (
    NOTES_WRONG_WORD_CONTEXT_PROJECTION,
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


def test_bootstrap_notes_projection_snapshots_backfills_state_and_markers(app):
    with app.app_context():
        user = _create_user(username='bootstrap-notes-user')
        now = datetime.utcnow()
        db.session.add(UserStudySession(
            id=641,
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

        summary = bootstrap_notes_projection_snapshots()

        projected_session = db.session.get(NotesProjectedStudySession, 641)
        projected_wrong_word = NotesProjectedWrongWord.query.filter_by(
            user_id=user.id,
            word='compile',
        ).first()
        cursors = {
            cursor.projection_name: cursor
            for cursor in NotesProjectionCursor.query.all()
        }

        assert summary == {
            'study_sessions': UserStudySession.query.count(),
            'wrong_words': UserWrongWord.query.count(),
        }
        assert projected_session is not None
        assert projected_session.mode == 'meaning'
        assert projected_wrong_word is not None
        assert projected_wrong_word.definition == 'collect information'
        assert cursors[NOTES_STUDY_SESSION_CONTEXT_PROJECTION].last_topic == BOOTSTRAP_TOPIC
        assert cursors[NOTES_WRONG_WORD_CONTEXT_PROJECTION].last_topic == BOOTSTRAP_TOPIC
        assert cursors[notes_bootstrap_marker_name(NOTES_STUDY_SESSION_CONTEXT_PROJECTION)].last_topic == BOOTSTRAP_TOPIC
        assert cursors[notes_bootstrap_marker_name(NOTES_WRONG_WORD_CONTEXT_PROJECTION)].last_topic == BOOTSTRAP_TOPIC
