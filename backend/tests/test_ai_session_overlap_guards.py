from datetime import datetime, timedelta

from models import User, UserStudySession, db


def register_and_login(client, username='overlap-guard-user', password='password123'):
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


def test_start_session_closes_older_open_placeholder_before_creating_new_one(client, app):
    register_and_login(client, username='overlap-close-user')

    first = client.post('/api/ai/start-session', json={
        'mode': 'listening',
        'bookId': 'ielts_listening_premium',
        'chapterId': '1',
    })
    assert first.status_code == 201
    first_session_id = first.get_json()['sessionId']

    with app.app_context():
        session = UserStudySession.query.get(first_session_id)
        assert session is not None
        session.started_at = datetime.utcnow() - timedelta(minutes=8)
        db.session.commit()

    second = client.post('/api/ai/start-session', json={
        'mode': 'quickmemory',
        'bookId': 'ielts_reading_premium',
        'chapterId': '2',
    })
    assert second.status_code == 201
    second_session_id = second.get_json()['sessionId']
    assert second_session_id != first_session_id

    with app.app_context():
        first_session = UserStudySession.query.get(first_session_id)
        second_session = UserStudySession.query.get(second_session_id)
        assert first_session is not None
        assert second_session is not None
        assert first_session.ended_at is not None
        assert first_session.duration_seconds == 0
        assert second_session.ended_at is None


def test_log_session_discards_zero_count_duration_without_server_activity(client, app):
    register_and_login(client, username='duration-filter-user')

    start_res = client.post('/api/ai/start-session', json={
        'mode': 'dictation',
        'bookId': 'ielts_listening_premium',
        'chapterId': '7',
    })
    assert start_res.status_code == 201
    session_id = start_res.get_json()['sessionId']

    with app.app_context():
        session = UserStudySession.query.get(session_id)
        assert session is not None
        session.started_at = datetime.utcnow() - timedelta(minutes=12)
        db.session.commit()

    response = client.post('/api/ai/log-session', json={
        'sessionId': session_id,
        'mode': 'dictation',
        'bookId': 'ielts_listening_premium',
        'chapterId': '7',
        'wordsStudied': 0,
        'correctCount': 0,
        'wrongCount': 0,
    })

    assert response.status_code == 200

    with app.app_context():
        session = UserStudySession.query.get(session_id)
        assert session is not None
        assert session.ended_at is not None
        assert session.duration_seconds == 0


def test_start_session_force_new_session_skips_recent_pending_placeholder_reuse(client, app):
    register_and_login(client, username='force-new-session-user')

    first = client.post('/api/ai/start-session', json={
        'mode': 'quickmemory',
        'bookId': 'ielts_reading_premium',
        'chapterId': '9',
    })
    assert first.status_code == 201
    first_session_id = first.get_json()['sessionId']

    second = client.post('/api/ai/start-session', json={
        'mode': 'quickmemory',
        'bookId': 'ielts_reading_premium',
        'chapterId': '9',
        'forceNewSession': True,
    })
    assert second.status_code == 201
    second_session_id = second.get_json()['sessionId']
    assert second_session_id != first_session_id

    with app.app_context():
        first_session = UserStudySession.query.get(first_session_id)
        second_session = UserStudySession.query.get(second_session_id)
        assert first_session is not None
        assert second_session is not None
        assert first_session.ended_at is not None
        assert first_session.duration_seconds == 0
        assert second_session.ended_at is None
