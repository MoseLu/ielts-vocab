from models import UserLearningEvent, UserStudySession


def register_and_login(client, username='session-mode-user', password='password123'):
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


def test_start_session_normalizes_registered_mode_alias(client, app):
    register_and_login(client)

    response = client.post('/api/ai/start-session', json={
        'mode': 'quick_memory',
        'bookId': 'ielts_reading_premium',
        'chapterId': '1',
    })

    assert response.status_code == 201
    with app.app_context():
        session = UserStudySession.query.get(response.get_json()['sessionId'])
        assert session is not None
        assert session.mode == 'quickmemory'


def test_log_session_normalizes_mode_alias_for_session_and_event(client, app):
    register_and_login(client, username='session-mode-log-user')

    start_response = client.post('/api/ai/start-session', json={'mode': 'smart'})
    session_id = start_response.get_json()['sessionId']
    response = client.post('/api/ai/log-session', json={
        'sessionId': session_id,
        'mode': 'five-dimension-game',
        'wordsStudied': 2,
        'correctCount': 1,
        'wrongCount': 1,
        'durationSeconds': 12,
        'startedAt': 0,
    })

    assert response.status_code == 200
    with app.app_context():
        session = UserStudySession.query.get(session_id)
        event = UserLearningEvent.query.filter_by(event_type='study_session').one()
        assert session is not None
        assert session.mode == 'game'
        assert event.mode == 'game'


def test_start_session_preserves_custom_mode_fallback(client, app):
    register_and_login(client, username='session-mode-custom-user')

    custom_mode = 'Custom Mode Value That Is Longer Than Thirty Characters'
    response = client.post('/api/ai/start-session', json={
        'mode': custom_mode,
    })

    assert response.status_code == 201
    with app.app_context():
        session = UserStudySession.query.get(response.get_json()['sessionId'])
        assert session is not None
        assert session.mode == custom_mode[:30]
