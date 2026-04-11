from __future__ import annotations

import json
from datetime import datetime

from models import (
    AIProjectedDailySummary,
    AIProjectedWrongWord,
    AIProjectionCursor,
    User,
    UserDailySummary,
    UserWrongWord,
    db,
)
from platform_sdk.ai_daily_summary_projection_application import (
    AI_DAILY_SUMMARY_CONTEXT_PROJECTION,
)
from platform_sdk.ai_projection_bootstrap import (
    BOOTSTRAP_TOPIC,
    ai_bootstrap_marker_name,
    bootstrap_ai_projection_snapshots,
)
from platform_sdk.ai_wrong_word_projection_application import (
    AI_WRONG_WORD_CONTEXT_PROJECTION,
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


def test_bootstrap_ai_projection_snapshots_backfills_state_and_markers(app):
    with app.app_context():
        user = _create_user(username='bootstrap-ai-user')
        now = datetime.utcnow()
        db.session.add(UserWrongWord(
            user_id=user.id,
            word='compile',
            phonetic='/kəmˈpaɪl/',
            pos='v.',
            definition='collect information',
            wrong_count=4,
            meaning_wrong=2,
            dimension_state=json.dumps(_dimension_states(
                wrong_count=4,
                last_wrong_at='2026-04-11T11:00:00+00:00',
            ), ensure_ascii=False),
            updated_at=now,
        ))
        db.session.add(UserDailySummary(
            user_id=user.id,
            date='2026-04-11',
            content='# 2026-04-11 学习总结\n\n今天完成了 AI 复盘。',
            generated_at=now,
        ))
        db.session.commit()

        summary = bootstrap_ai_projection_snapshots()

        projected_wrong_word = AIProjectedWrongWord.query.filter_by(
            user_id=user.id,
            word='compile',
        ).first()
        projected_summary = AIProjectedDailySummary.query.filter_by(
            user_id=user.id,
            date='2026-04-11',
        ).first()
        cursors = {
            cursor.projection_name: cursor
            for cursor in AIProjectionCursor.query.all()
        }

        assert summary == {
            'wrong_words': UserWrongWord.query.count(),
            'daily_summaries': UserDailySummary.query.count(),
        }
        assert projected_wrong_word is not None
        assert projected_wrong_word.definition == 'collect information'
        assert projected_summary is not None
        assert projected_summary.content.startswith('# 2026-04-11 学习总结')
        assert cursors[AI_WRONG_WORD_CONTEXT_PROJECTION].last_topic == BOOTSTRAP_TOPIC
        assert cursors[AI_DAILY_SUMMARY_CONTEXT_PROJECTION].last_topic == BOOTSTRAP_TOPIC
        assert cursors[ai_bootstrap_marker_name(AI_WRONG_WORD_CONTEXT_PROJECTION)].last_topic == BOOTSTRAP_TOPIC
        assert cursors[ai_bootstrap_marker_name(AI_DAILY_SUMMARY_CONTEXT_PROJECTION)].last_topic == BOOTSTRAP_TOPIC
