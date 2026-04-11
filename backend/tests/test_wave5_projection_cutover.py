from __future__ import annotations

import json
from datetime import datetime, timedelta

from models import (
    User,
    UserDailySummary,
    UserStudySession,
    UserWrongWord,
    db,
)
from platform_sdk.wave5_projection_cutover import run_wave5_projection_cutover


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


def test_run_wave5_projection_cutover_bootstraps_and_verifies_all_projection_groups(app):
    with app.app_context():
        user = _create_user(username='wave5-cutover-user')
        now = datetime.utcnow()
        db.session.add(UserStudySession(
            id=741,
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

        result = run_wave5_projection_cutover()

        assert result['bootstrap_ran'] is True
        assert result['ok'] is True
        assert result['bootstrap']['admin']['users'] == User.query.count()
        assert result['bootstrap']['admin']['study_sessions'] == UserStudySession.query.count()
        assert result['bootstrap']['admin']['wrong_words'] == UserWrongWord.query.count()
        assert result['bootstrap']['notes']['study_sessions'] == UserStudySession.query.count()
        assert result['bootstrap']['notes']['wrong_words'] == UserWrongWord.query.count()
        assert result['bootstrap']['ai']['wrong_words'] == UserWrongWord.query.count()
        assert result['bootstrap']['ai']['daily_summaries'] == UserDailySummary.query.count()
        for group_name in ('admin', 'notes', 'ai'):
            for item in result[group_name].values():
                assert item['ready'] is True
                assert item['counts_match'] is True
                assert item['ok'] is True


def test_run_wave5_projection_cutover_verify_only_reports_not_ready_before_bootstrap(app):
    with app.app_context():
        user = _create_user(username='wave5-cutover-verify-only-user')
        db.session.add(UserStudySession(user_id=user.id, mode='listening', words_studied=1))
        db.session.commit()

        result = run_wave5_projection_cutover(bootstrap=False)

        assert result['bootstrap_ran'] is False
        assert result['bootstrap'] is None
        assert result['ok'] is False
        assert result['admin']['user_directory']['ready'] is False
        assert result['notes']['study_sessions']['ready'] is False
        assert result['ai']['wrong_words']['ready'] is False
