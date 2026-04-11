from datetime import datetime

from models import User, UserStudySession, db
from platform_sdk.learning_stats_modes_support import normalize_stats_mode, stats_mode_candidates


def _register_and_login(client, username='mode-stats-user', password='password123'):
    client.post('/api/auth/register', json={
        'username': username,
        'password': password,
        'email': f'{username}@example.com',
    })
    response = client.post('/api/auth/login', json={
        'email': username,
        'password': password,
    })
    assert response.status_code == 200


def test_normalize_stats_mode_ignores_non_string_values():
    assert normalize_stats_mode(7) == ''
    assert normalize_stats_mode(None) == ''
    assert stats_mode_candidates(7) == []


def test_learning_stats_endpoint_ignores_non_string_session_modes(client, app):
    _register_and_login(client, username='non-string-mode-stats-user')
    now = datetime.utcnow().replace(microsecond=0)

    with app.app_context():
        user = User.query.filter_by(username='non-string-mode-stats-user').first()
        assert user is not None

        db.session.add_all([
            UserStudySession(
                user_id=user.id,
                mode=7,
                words_studied=5,
                correct_count=4,
                wrong_count=1,
                duration_seconds=60,
                started_at=now,
                ended_at=now,
            ),
            UserStudySession(
                user_id=user.id,
                mode='listening',
                words_studied=6,
                correct_count=5,
                wrong_count=1,
                duration_seconds=90,
                started_at=now,
                ended_at=now,
            ),
        ])
        db.session.commit()

    response = client.get('/api/ai/learning-stats?days=7')

    assert response.status_code == 200
    data = response.get_json()
    assert data['summary']['total_sessions'] == 2
    assert data['modes'] == ['listening']
    assert all(item['mode'] != 7 for item in data['mode_breakdown'])
