from datetime import datetime

import services.learner_profile as learner_profile_service
from models import User, UserStudySession, db


def register_and_login(client, username='time-audit-profile-user', password='password123'):
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


def test_learner_profile_dedupes_overlapping_session_duration(client, app, monkeypatch):
    register_and_login(client, username='overlap-profile-user')
    fixed_now = datetime(2026, 4, 13, 12, 0, 0)

    with app.app_context():
        user = User.query.filter_by(username='overlap-profile-user').first()
        assert user is not None
        db.session.add_all([
            UserStudySession(
                user_id=user.id,
                mode='listening',
                words_studied=10,
                correct_count=7,
                wrong_count=3,
                duration_seconds=900,
                started_at=datetime(2026, 4, 13, 1, 0, 0),
                ended_at=datetime(2026, 4, 13, 1, 15, 0),
            ),
            UserStudySession(
                user_id=user.id,
                mode='meaning',
                words_studied=8,
                correct_count=6,
                wrong_count=2,
                duration_seconds=600,
                started_at=datetime(2026, 4, 13, 1, 10, 0),
                ended_at=datetime(2026, 4, 13, 1, 20, 0),
            ),
        ])
        db.session.commit()

    monkeypatch.setattr(learner_profile_service, 'utc_now_naive', lambda: fixed_now)
    response = client.get('/api/ai/learner-profile?date=2026-04-13')

    assert response.status_code == 200
    data = response.get_json()
    assert data['summary']['today_sessions'] == 2
    assert data['summary']['today_duration_seconds'] == 20 * 60
