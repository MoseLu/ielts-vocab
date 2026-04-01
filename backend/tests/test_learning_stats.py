from datetime import datetime

from models import User, UserStudySession, db


def register_and_login(client, username='stats-user', password='password123'):
    client.post('/api/auth/register', json={
        'username': username,
        'password': password,
        'email': f'{username}@example.com',
    })
    res = client.post('/api/auth/login', json={
        'email': username,
        'password': password,
    })
    assert res.status_code == 200


def test_learning_stats_ignores_empty_started_sessions(client, app):
    register_and_login(client)

    with app.app_context():
        user = User.query.filter_by(username='stats-user').first()
        assert user is not None

        db.session.add_all([
            UserStudySession(
                user_id=user.id,
                mode='listening',
                book_id='ielts_listening_premium',
                chapter_id='1',
                started_at=datetime(2026, 3, 30, 9, 0, 0),
            ),
            UserStudySession(
                user_id=user.id,
                mode='listening',
                book_id='ielts_listening_premium',
                chapter_id='1',
                words_studied=20,
                correct_count=18,
                wrong_count=2,
                duration_seconds=120,
                started_at=datetime(2026, 3, 30, 9, 1, 0),
                ended_at=datetime(2026, 3, 30, 9, 3, 0),
            ),
        ])
        db.session.commit()

    response = client.get('/api/ai/learning-stats?days=7')

    assert response.status_code == 200
    data = response.get_json()
    assert data['summary']['total_sessions'] == 1
    listening = next(item for item in data['mode_breakdown'] if item['mode'] == 'listening')
    assert listening['sessions'] == 1
    assert listening['words_studied'] == 20
    assert listening['duration_seconds'] == 120


def test_learner_profile_ignores_empty_started_sessions(client, app):
    register_and_login(client, username='profile-stats-user')

    with app.app_context():
        user = User.query.filter_by(username='profile-stats-user').first()
        assert user is not None

        db.session.add_all([
            UserStudySession(
                user_id=user.id,
                mode='listening',
                started_at=datetime(2026, 3, 30, 8, 0, 0),
            ),
            UserStudySession(
                user_id=user.id,
                mode='listening',
                words_studied=15,
                correct_count=12,
                wrong_count=3,
                duration_seconds=180,
                started_at=datetime(2026, 3, 30, 9, 0, 0),
                ended_at=datetime(2026, 3, 30, 9, 3, 0),
            ),
        ])
        db.session.commit()

    response = client.get('/api/ai/learner-profile?date=2026-03-30')

    assert response.status_code == 200
    data = response.get_json()
    assert data['summary']['today_sessions'] == 1
    listening = next(item for item in data['mode_breakdown'] if item['mode'] == 'listening')
    assert listening['sessions'] == 1
    assert listening['words'] == 15


def test_learning_stats_skips_implausible_legacy_short_sessions(client, app):
    register_and_login(client, username='legacy-stats-user')

    with app.app_context():
        user = User.query.filter_by(username='legacy-stats-user').first()
        assert user is not None

        db.session.add_all([
            UserStudySession(
                user_id=user.id,
                mode='listening',
                words_studied=80,
                correct_count=70,
                wrong_count=10,
                duration_seconds=2,
                started_at=datetime(2026, 3, 30, 8, 0, 0),
            ),
            UserStudySession(
                user_id=user.id,
                mode='listening',
                words_studied=7,
                correct_count=6,
                wrong_count=1,
                duration_seconds=82,
                started_at=datetime(2026, 3, 30, 9, 0, 0),
                ended_at=datetime(2026, 3, 30, 9, 1, 22),
            ),
        ])
        db.session.commit()

    response = client.get('/api/ai/learning-stats?days=7')

    assert response.status_code == 200
    data = response.get_json()
    listening = next(item for item in data['mode_breakdown'] if item['mode'] == 'listening')
    assert listening['words_studied'] == 7
    assert listening['duration_seconds'] == 82
    assert listening['sessions'] == 1


def test_learning_stats_uses_review_sessions_for_accuracy_when_no_chapter_progress_exists(client, app):
    register_and_login(client, username='review-only-stats-user')

    now = datetime.utcnow().replace(microsecond=0)

    with app.app_context():
        user = User.query.filter_by(username='review-only-stats-user').first()
        assert user is not None

        db.session.add_all([
            UserStudySession(
                user_id=user.id,
                mode='errors',
                words_studied=4,
                correct_count=3,
                wrong_count=1,
                duration_seconds=120,
                started_at=now,
                ended_at=now,
            ),
            UserStudySession(
                user_id=user.id,
                mode='quickmemory',
                words_studied=5,
                correct_count=4,
                wrong_count=1,
                duration_seconds=150,
                started_at=now,
                ended_at=now,
            ),
        ])
        db.session.commit()

    response = client.get('/api/ai/learning-stats?days=7')

    assert response.status_code == 200
    data = response.get_json()
    assert data['alltime']['today_accuracy'] == 78
    assert data['alltime']['accuracy'] == 78
