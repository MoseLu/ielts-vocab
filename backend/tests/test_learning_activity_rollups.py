from datetime import datetime

from models import (
    User,
    UserChapterModeProgress,
    UserChapterProgress,
    UserLearningBookRollup,
    UserLearningChapterRollup,
    UserLearningDailyLedger,
    UserLearningUserRollup,
    UserStudySession,
    db,
)
from services.learning_activity_backfill import backfill_learning_activity_rollups
from services.learning_activity_service import record_learning_activity


def _register_user(client, username='learning-rollup-user'):
    response = client.post('/api/auth/register', json={
        'username': username,
        'password': 'password123',
    })
    assert response.status_code == 201


def _user_id(app, username='learning-rollup-user'):
    with app.app_context():
        user = User.query.filter_by(username=username).one()
        return user.id


def test_chapter_progress_writes_five_level_rollups(client, app):
    _register_user(client)
    user_id = _user_id(app)

    response = client.post('/api/books/ielts_reading_premium/chapters/1/progress', json={
        'mode': 'dictation',
        'current_index': 3,
        'words_learned': 5,
        'correct_count': 4,
        'wrong_count': 1,
        'answered_words': ['alpha', 'beta'],
        'queue_words': ['alpha', 'beta', 'gamma'],
        'is_completed': False,
    })

    assert response.status_code == 200
    with app.app_context():
        ledger = UserLearningDailyLedger.query.filter_by(
            user_id=user_id,
            book_id='ielts_reading_premium',
            mode='dictation',
            chapter_id='1',
        ).one()
        assert ledger.words_learned == 5
        assert ledger.learning_date

        chapter_rollup = UserLearningChapterRollup.query.filter_by(
            user_id=user_id,
            book_id='ielts_reading_premium',
            mode='dictation',
            chapter_id='1',
        ).one()
        assert chapter_rollup.current_index == 3
        assert chapter_rollup.words_learned == 5
        assert chapter_rollup.correct_count == 4

        book_rollup = UserLearningBookRollup.query.filter_by(
            user_id=user_id,
            book_id='ielts_reading_premium',
        ).one()
        assert book_rollup.current_index == 5
        assert book_rollup.correct_count == 4

        user_rollup = UserLearningUserRollup.query.filter_by(user_id=user_id).one()
        assert user_rollup.book_count == 1
        assert user_rollup.words_learned == 5


def test_chapter_progress_requires_resolved_mode(client):
    _register_user(client, username='learning-rollup-mode-required')

    response = client.post('/api/books/ielts_reading_premium/chapters/1/progress', json={
        'current_index': 1,
        'words_learned': 1,
        'correct_count': 1,
        'wrong_count': 0,
    })

    assert response.status_code == 400
    assert 'mode' in response.get_json()['error']


def test_same_chapter_keeps_modes_separate_in_rollups(client, app):
    _register_user(client, username='learning-rollup-modes')
    user_id = _user_id(app, username='learning-rollup-modes')

    quickmemory = client.post('/api/books/ielts_reading_premium/chapters/2/progress', json={
        'mode': 'quickmemory',
        'current_index': 1,
        'words_learned': 1,
        'correct_count': 1,
        'wrong_count': 0,
        'is_completed': False,
    })
    meaning = client.post('/api/books/ielts_reading_premium/chapters/2/mode-progress', json={
        'mode': 'meaning',
        'correct_count': 0,
        'wrong_count': 2,
        'is_completed': False,
    })

    assert quickmemory.status_code == 200
    assert meaning.status_code == 200
    with app.app_context():
        rows = UserLearningChapterRollup.query.filter_by(
            user_id=user_id,
            book_id='ielts_reading_premium',
            chapter_id='2',
        ).all()
        assert {row.mode for row in rows} == {'quickmemory', 'meaning'}
        by_mode = {row.mode: row for row in rows}
        assert by_mode['quickmemory'].correct_count == 1
        assert by_mode['meaning'].wrong_count == 2

    progress = client.get('/api/books/ielts_reading_premium/chapters/progress')
    assert progress.status_code == 200
    modes = progress.get_json()['chapter_progress']['2']['modes']
    assert modes['quickmemory']['correct_count'] == 1
    assert modes['meaning']['wrong_count'] == 2


def test_learning_date_uses_local_day_boundaries(app):
    with app.app_context():
        user = User(username='learning-rollup-date')
        user.set_password('password123')
        from models import db

        db.session.add(user)
        db.session.commit()

        record_learning_activity(
            user_id=user.id,
            book_id='book-a',
            mode='listening',
            chapter_id='1',
            occurred_at=datetime(2026, 4, 21, 15, 59),
            correct_count=1,
        )
        record_learning_activity(
            user_id=user.id,
            book_id='book-a',
            mode='listening',
            chapter_id='1',
            occurred_at=datetime(2026, 4, 21, 16, 1),
            correct_count=2,
        )
        db.session.commit()

        dates = {
            row.learning_date
            for row in UserLearningDailyLedger.query.filter_by(user_id=user.id).all()
        }
        assert dates == {'2026-04-21', '2026-04-22'}


def test_backfill_learning_activity_rollups_is_idempotent(app):
    with app.app_context():
        user = User(username='learning-rollup-backfill')
        user.set_password('password123')
        db.session.add(user)
        db.session.flush()
        db.session.add(UserStudySession(
            user_id=user.id,
            mode='listening',
            book_id='book-backfill',
            chapter_id='1',
            words_studied=3,
            duration_seconds=60,
            started_at=datetime(2026, 4, 22, 1, 0),
        ))
        db.session.add(UserChapterModeProgress(
            user_id=user.id,
            book_id='book-backfill',
            chapter_id='1',
            mode='listening',
            correct_count=2,
            wrong_count=1,
            is_completed=False,
        ))
        db.session.add(UserChapterProgress(
            user_id=user.id,
            book_id='book-backfill',
            chapter_id='1',
            words_learned=3,
            correct_count=2,
            wrong_count=1,
        ))
        db.session.commit()

        first = backfill_learning_activity_rollups(user_ids=[user.id])
        second = backfill_learning_activity_rollups(user_ids=[user.id])

        assert first['ledger_writes'] == second['ledger_writes']
        assert UserLearningDailyLedger.query.filter_by(user_id=user.id).count() == 1
        rollup = UserLearningChapterRollup.query.filter_by(
            user_id=user.id,
            book_id='book-backfill',
            mode='listening',
            chapter_id='1',
        ).one()
        assert rollup.words_learned == 3
        assert rollup.correct_count == 2
        assert rollup.duration_seconds == 60
