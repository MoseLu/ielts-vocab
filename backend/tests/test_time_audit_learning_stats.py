from datetime import datetime, timedelta

import routes.ai as ai_routes
from models import User, UserLearningEvent, UserStudySession, db
from services import ai_route_support_service as route_support_service


def register_and_login(client, username='time-audit-stats-user', password='password123'):
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


def _load_user(username: str) -> User:
    user = User.query.filter_by(username=username).first()
    assert user is not None
    return user


def test_learning_stats_dedupes_overlapping_closed_sessions(client, app, monkeypatch):
    register_and_login(client, username='overlap-stats-user')
    fixed_now = datetime(2026, 4, 13, 12, 0, 0)

    with app.app_context():
        user = _load_user('overlap-stats-user')
        db.session.add_all([
            UserStudySession(
                user_id=user.id,
                mode='quickmemory',
                words_studied=12,
                correct_count=10,
                wrong_count=2,
                duration_seconds=900,
                started_at=datetime(2026, 4, 13, 1, 0, 0),
                ended_at=datetime(2026, 4, 13, 1, 15, 0),
            ),
            UserStudySession(
                user_id=user.id,
                mode='dictation',
                words_studied=8,
                correct_count=6,
                wrong_count=2,
                duration_seconds=600,
                started_at=datetime(2026, 4, 13, 1, 10, 0),
                ended_at=datetime(2026, 4, 13, 1, 20, 0),
            ),
        ])
        db.session.commit()

    monkeypatch.setattr(ai_routes, 'utc_now_naive', lambda: fixed_now)
    monkeypatch.setattr(route_support_service, 'utc_now_naive', lambda: fixed_now)
    response = client.get('/api/ai/learning-stats?days=7')

    assert response.status_code == 200
    data = response.get_json()
    today_row = next(item for item in data['daily'] if item['date'] == '2026-04-13')
    assert today_row['duration_seconds'] == 20 * 60
    assert data['summary']['total_duration_seconds'] == 20 * 60
    assert data['alltime']['duration_seconds'] == 20 * 60
    assert data['alltime']['today_duration_seconds'] == 20 * 60


def test_learning_stats_excludes_zero_count_duration_without_activity_evidence(client, app, monkeypatch):
    register_and_login(client, username='zero-duration-stats-user')
    fixed_now = datetime(2026, 4, 13, 12, 0, 0)

    with app.app_context():
        user = _load_user('zero-duration-stats-user')
        db.session.add_all([
            UserStudySession(
                user_id=user.id,
                mode='dictation',
                duration_seconds=900,
                started_at=datetime(2026, 4, 13, 2, 0, 0),
                ended_at=datetime(2026, 4, 13, 2, 15, 0),
            ),
            UserStudySession(
                user_id=user.id,
                mode='listening',
                words_studied=5,
                correct_count=4,
                wrong_count=1,
                duration_seconds=180,
                started_at=datetime(2026, 4, 13, 3, 0, 0),
                ended_at=datetime(2026, 4, 13, 3, 3, 0),
            ),
        ])
        db.session.commit()

    monkeypatch.setattr(ai_routes, 'utc_now_naive', lambda: fixed_now)
    monkeypatch.setattr(route_support_service, 'utc_now_naive', lambda: fixed_now)
    response = client.get('/api/ai/learning-stats?days=7')

    assert response.status_code == 200
    data = response.get_json()
    assert data['summary']['total_sessions'] == 1
    assert data['summary']['total_duration_seconds'] == 180
    assert data['alltime']['duration_seconds'] == 180


def test_learning_stats_keeps_zero_count_duration_when_events_back_it(client, app, monkeypatch):
    register_and_login(client, username='event-backed-stats-user')
    fixed_now = datetime(2026, 4, 13, 12, 0, 0)

    with app.app_context():
        user = _load_user('event-backed-stats-user')
        db.session.add(UserStudySession(
            user_id=user.id,
            mode='dictation',
            book_id='ielts_listening_premium',
            chapter_id='9',
            duration_seconds=600,
            started_at=datetime(2026, 4, 13, 4, 0, 0),
            ended_at=datetime(2026, 4, 13, 4, 10, 0),
        ))
        db.session.add(UserLearningEvent(
            user_id=user.id,
            event_type='chapter_mode_progress_updated',
            source='chapter_mode_progress',
            mode='dictation',
            book_id='ielts_listening_premium',
            chapter_id='9',
            occurred_at=datetime(2026, 4, 13, 4, 6, 0),
        ))
        db.session.commit()

    monkeypatch.setattr(ai_routes, 'utc_now_naive', lambda: fixed_now)
    monkeypatch.setattr(route_support_service, 'utc_now_naive', lambda: fixed_now)
    response = client.get('/api/ai/learning-stats?days=7')

    assert response.status_code == 200
    data = response.get_json()
    assert data['summary']['total_sessions'] == 1
    assert data['summary']['total_duration_seconds'] == 600
    assert data['alltime']['duration_seconds'] == 600


def test_learning_stats_dedupes_live_pending_against_closed_session_overlap(client, app, monkeypatch):
    register_and_login(client, username='live-overlap-stats-user')
    fixed_now = datetime(2026, 4, 13, 12, 0, 0)

    with app.app_context():
        user = _load_user('live-overlap-stats-user')
        db.session.add(UserStudySession(
            user_id=user.id,
            mode='quickmemory',
            words_studied=6,
            correct_count=5,
            wrong_count=1,
            duration_seconds=600,
            started_at=datetime(2026, 4, 13, 1, 0, 0),
            ended_at=datetime(2026, 4, 13, 1, 10, 0),
        ))
        db.session.add(UserStudySession(
            user_id=user.id,
            mode='quickmemory',
            book_id='ielts_reading_premium',
            chapter_id='12',
            started_at=datetime(2026, 4, 13, 1, 8, 0),
        ))
        db.session.add(UserLearningEvent(
            user_id=user.id,
            event_type='quick_memory_review',
            source='quickmemory',
            mode='quickmemory',
            book_id='ielts_reading_premium',
            chapter_id='12',
            occurred_at=datetime(2026, 4, 13, 1, 15, 0),
        ))
        db.session.commit()

    monkeypatch.setattr(ai_routes, 'utc_now_naive', lambda: fixed_now)
    monkeypatch.setattr(route_support_service, 'utc_now_naive', lambda: fixed_now)
    response = client.get('/api/ai/learning-stats?days=7')

    assert response.status_code == 200
    data = response.get_json()
    expected_union_seconds = 20 * 60
    assert data['summary']['total_duration_seconds'] == expected_union_seconds
    assert data['alltime']['today_duration_seconds'] == expected_union_seconds
