from datetime import datetime, timedelta, timezone

import routes.ai as ai_routes
from models import User, UserChapterProgress, UserQuickMemoryRecord, UserStudySession, db


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


def test_learning_stats_ignores_empty_started_sessions(client, app, monkeypatch):
    register_and_login(client)
    fixed_now = datetime(2026, 3, 30, 12, 0, 0)

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

    monkeypatch.setattr(ai_routes, 'utc_now_naive', lambda: fixed_now)
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


def test_learning_stats_skips_epoch_sized_broken_duration_rows(client, app):
    register_and_login(client, username='broken-duration-stats-user')

    with app.app_context():
        user = User.query.filter_by(username='broken-duration-stats-user').first()
        assert user is not None

        db.session.add_all([
            UserStudySession(
                user_id=user.id,
                mode='listening',
                words_studied=1,
                correct_count=1,
                wrong_count=0,
                duration_seconds=1_775_322_098,
                started_at=datetime(2026, 4, 4, 17, 1, 38, 477224),
                ended_at=datetime(2026, 4, 4, 17, 1, 38, 476222),
            ),
            UserStudySession(
                user_id=user.id,
                mode='listening',
                words_studied=7,
                correct_count=6,
                wrong_count=1,
                duration_seconds=82,
                started_at=datetime(2026, 4, 4, 9, 0, 0),
                ended_at=datetime(2026, 4, 4, 9, 1, 22),
            ),
        ])
        db.session.commit()

    response = client.get('/api/ai/learning-stats?days=7')

    assert response.status_code == 200
    data = response.get_json()
    listening = next(item for item in data['mode_breakdown'] if item['mode'] == 'listening')
    assert data['summary']['total_duration_seconds'] == 82
    assert data['alltime']['duration_seconds'] == 82
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


def test_learning_stats_prefers_today_sessions_for_today_accuracy_when_chapter_progress_is_perfect(client, app):
    register_and_login(client, username='mixed-today-accuracy-user')

    now = datetime.utcnow().replace(microsecond=0)

    with app.app_context():
        user = User.query.filter_by(username='mixed-today-accuracy-user').first()
        assert user is not None

        db.session.add(
            UserChapterProgress(
                user_id=user.id,
                book_id='ielts_reading_premium',
                chapter_id=1,
                words_learned=50,
                correct_count=50,
                wrong_count=0,
                is_completed=True,
                updated_at=now,
            )
        )
        db.session.add(
            UserStudySession(
                user_id=user.id,
                mode='quickmemory',
                book_id='ielts_reading_premium',
                chapter_id='1',
                words_studied=10,
                correct_count=8,
                wrong_count=2,
                duration_seconds=300,
                started_at=now,
                ended_at=now,
            )
        )
        db.session.commit()

    response = client.get('/api/ai/learning-stats?days=7')

    assert response.status_code == 200
    data = response.get_json()
    assert data['alltime']['today_accuracy'] == 80


def test_learning_stats_includes_recent_live_pending_session_duration(client, app, monkeypatch):
    register_and_login(client, username='live-duration-stats-user')

    now = datetime(2026, 4, 5, 6, 0, 0)
    completed_duration = 120
    live_duration_floor = 45 * 60

    with app.app_context():
        user = User.query.filter_by(username='live-duration-stats-user').first()
        assert user is not None

        db.session.add_all([
            UserStudySession(
                user_id=user.id,
                mode='quickmemory',
                book_id='ielts_reading_premium',
                chapter_id='8',
                started_at=now - timedelta(hours=2),
            ),
            UserStudySession(
                user_id=user.id,
                mode='quickmemory',
                book_id='ielts_reading_premium',
                chapter_id='9',
                words_studied=10,
                correct_count=8,
                wrong_count=2,
                duration_seconds=completed_duration,
                started_at=now - timedelta(hours=1, minutes=30),
                ended_at=now - timedelta(hours=1, minutes=28),
            ),
            UserStudySession(
                user_id=user.id,
                mode='quickmemory',
                book_id='ielts_reading_premium',
                chapter_id='10',
                started_at=now - timedelta(minutes=45),
            ),
        ])
        db.session.commit()

    monkeypatch.setattr(ai_routes, 'utc_now_naive', lambda: now)
    response = client.get('/api/ai/learning-stats?days=7')

    assert response.status_code == 200
    data = response.get_json()
    today_key = now.strftime('%Y-%m-%d')
    today_row = next(item for item in data['daily'] if item['date'] == today_key)
    expected_floor = completed_duration + live_duration_floor
    assert data['use_fallback'] is False
    assert today_row['duration_seconds'] >= expected_floor
    assert today_row['duration_seconds'] < expected_floor + 20
    assert data['alltime']['today_duration_seconds'] >= expected_floor
    assert data['alltime']['today_duration_seconds'] < expected_floor + 20
    quickmemory = next(item for item in data['mode_breakdown'] if item['mode'] == 'quickmemory')
    assert quickmemory['duration_seconds'] >= expected_floor
    assert quickmemory['duration_seconds'] < expected_floor + 20


def test_learning_stats_uses_local_calendar_day_for_today_counts(client, app, monkeypatch):
    register_and_login(client, username='local-day-stats-user')

    fixed_now = datetime(2026, 4, 3, 6, 8, 53)
    monkeypatch.setattr(ai_routes, 'utc_now_naive', lambda: fixed_now)

    with app.app_context():
        user = User.query.filter_by(username='local-day-stats-user').first()
        assert user is not None

        db.session.add(
            UserStudySession(
                user_id=user.id,
                mode='quickmemory',
                book_id='ielts_confusable_match',
                chapter_id='1',
                words_studied=3,
                correct_count=2,
                wrong_count=1,
                duration_seconds=600,
                started_at=datetime(2026, 4, 2, 23, 30, 0),
                ended_at=datetime(2026, 4, 2, 23, 40, 0),
            )
        )
        db.session.add(
            UserQuickMemoryRecord(
                user_id=user.id,
                word='section',
                status='unknown',
                first_seen=int(datetime(2026, 3, 25, 13, 14, 52, tzinfo=timezone.utc).timestamp() * 1000),
                last_seen=int(datetime(2026, 4, 2, 23, 30, 11, tzinfo=timezone.utc).timestamp() * 1000),
                known_count=0,
                unknown_count=2,
                next_review=int(datetime(2026, 4, 3, 23, 30, 11, tzinfo=timezone.utc).timestamp() * 1000),
            )
        )
        db.session.commit()

    response = client.get('/api/ai/learning-stats?days=7')

    assert response.status_code == 200
    data = response.get_json()
    today_row = next(item for item in data['daily'] if item['date'] == '2026-04-03')
    assert today_row['sessions'] == 1
    assert today_row['duration_seconds'] == 600
    assert data['alltime']['today_duration_seconds'] == 600
    assert data['alltime']['today_review_words'] == 1


def test_learning_stats_splits_cross_midnight_sessions_into_today(client, app, monkeypatch):
    register_and_login(client, username='cross-midnight-stats-user')

    fixed_now = datetime(2026, 4, 5, 0, 40, 0)
    monkeypatch.setattr(ai_routes, 'utc_now_naive', lambda: fixed_now)

    with app.app_context():
        user = User.query.filter_by(username='cross-midnight-stats-user').first()
        assert user is not None

        db.session.add(
            UserStudySession(
                user_id=user.id,
                mode='quickmemory',
                book_id='ielts_reading_premium',
                chapter_id='2',
                words_studied=20,
                correct_count=14,
                wrong_count=6,
                duration_seconds=1200,
                started_at=datetime(2026, 4, 4, 15, 50, 0),
                ended_at=datetime(2026, 4, 4, 16, 10, 0),
            )
        )
        db.session.commit()

    response = client.get('/api/ai/learning-stats?days=7')

    assert response.status_code == 200
    data = response.get_json()
    today_row = next(item for item in data['daily'] if item['date'] == '2026-04-05')
    assert today_row['sessions'] == 1
    assert today_row['words_studied'] == 10
    assert today_row['correct_count'] == 7
    assert today_row['wrong_count'] == 3
    assert today_row['duration_seconds'] == 600
    assert today_row['accuracy'] == 70
    assert data['alltime']['today_duration_seconds'] == 600
    assert data['alltime']['today_accuracy'] == 70
