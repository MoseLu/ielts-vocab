from models import UserStudySession
from routes import ai as ai_routes


def register_and_login(client, username='session-user', password='password123'):
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


def test_cancel_session_deletes_empty_started_session(client, app):
    register_and_login(client)

    start_res = client.post('/api/ai/start-session', json={
        'mode': 'quickmemory',
        'bookId': 'ielts_reading_premium',
        'chapterId': '1',
    })
    assert start_res.status_code == 201
    session_id = start_res.get_json()['sessionId']

    cancel_res = client.post('/api/ai/cancel-session', json={'sessionId': session_id})
    assert cancel_res.status_code == 200
    assert cancel_res.get_json()['deleted'] is True

    with app.app_context():
        assert UserStudySession.query.get(session_id) is None


def test_cancel_session_rejects_session_with_learning_data(client, app):
    register_and_login(client, username='session-user-2')

    start_res = client.post('/api/ai/start-session', json={'mode': 'smart'})
    session_id = start_res.get_json()['sessionId']

    log_res = client.post('/api/ai/log-session', json={
        'sessionId': session_id,
        'mode': 'smart',
        'wordsStudied': 1,
        'correctCount': 1,
        'wrongCount': 0,
        'durationSeconds': 0,
        'startedAt': 0,
    })
    assert log_res.status_code == 200

    cancel_res = client.post('/api/ai/cancel-session', json={'sessionId': session_id})
    assert cancel_res.status_code == 409

    with app.app_context():
        session = UserStudySession.query.get(session_id)
        assert session is not None
        assert session.words_studied == 1


def test_greet_returns_fallback_when_ai_service_fails(client, monkeypatch):
    register_and_login(client, username='greet-user')

    def raise_ai_error(*args, **kwargs):
        raise RuntimeError('simulated ai failure')

    monkeypatch.setattr(ai_routes, '_chat_with_tools', raise_ai_error)

    res = client.post('/api/ai/greet', json={'context': {}})

    assert res.status_code == 200
    data = res.get_json()
    assert isinstance(data, dict)
    assert data.get('reply')
    assert '雅思小助手' in data['reply']
    assert data.get('options') == []
