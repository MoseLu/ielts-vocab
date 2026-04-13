from datetime import datetime, timedelta, timezone

from models import UserLearningEvent, UserStudySession, db
from platform_sdk.learning_core_study_session_application import (
    log_learning_core_session_response,
)


def register_and_login(client, username='duration-guard-user', password='password123'):
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


def add_learning_event(
    *,
    user_id: int,
    event_type: str,
    source: str,
    occurred_at: datetime,
    mode: str | None = None,
    book_id: str | None = None,
    chapter_id: str | None = None,
):
    event = UserLearningEvent(
        user_id=user_id,
        event_type=event_type,
        source=source,
        mode=mode,
        book_id=book_id,
        chapter_id=chapter_id,
        occurred_at=occurred_at,
    )
    db.session.add(event)
    db.session.commit()
    return event


def test_log_session_caps_to_recent_server_activity_when_client_cap_missing(client, app):
    register_and_login(client, username='session-user-server-cap')

    base_now_utc = datetime.now(timezone.utc).replace(microsecond=0)
    recovered_start_utc = base_now_utc - timedelta(hours=6, minutes=54, seconds=2)
    last_activity_utc = recovered_start_utc + timedelta(seconds=56)
    expected_duration_seconds = 5 * 60 + 56

    start_res = client.post('/api/ai/start-session', json={
        'mode': 'listening',
        'bookId': 'ielts_listening_premium',
        'chapterId': '53',
    })
    assert start_res.status_code == 201
    session_id = start_res.get_json()['sessionId']

    with app.app_context():
        session = UserStudySession.query.get(session_id)
        assert session is not None
        session.started_at = recovered_start_utc.replace(tzinfo=None)
        db.session.commit()
        add_learning_event(
            user_id=session.user_id,
            event_type='chapter_mode_progress_updated',
            source='chapter_mode_progress',
            mode='listening',
            book_id='ielts_listening_premium',
            chapter_id='53',
            occurred_at=last_activity_utc.replace(tzinfo=None),
        )

    log_res = client.post('/api/ai/log-session', json={
        'sessionId': session_id,
        'mode': 'listening',
        'bookId': 'ielts_listening_premium',
        'chapterId': '53',
        'wordsStudied': 1,
        'correctCount': 1,
        'wrongCount': 1,
        'durationSeconds': int((base_now_utc - recovered_start_utc).total_seconds()),
        'startedAt': int(recovered_start_utc.timestamp() * 1000),
        'endedAt': int(base_now_utc.timestamp() * 1000),
    })

    assert log_res.status_code == 200

    with app.app_context():
        session = UserStudySession.query.get(session_id)
        assert session is not None
        assert session.duration_seconds == expected_duration_seconds
        assert session.ended_at == (last_activity_utc + timedelta(minutes=5)).replace(tzinfo=None)


def test_learning_core_log_session_caps_to_recent_server_activity(client, app):
    register_and_login(client, username='split-session-user-server-cap')

    base_now_utc = datetime.now(timezone.utc).replace(microsecond=0)
    recovered_start_utc = base_now_utc - timedelta(hours=6, minutes=54, seconds=2)
    last_activity_utc = recovered_start_utc + timedelta(seconds=56)
    expected_duration_seconds = 5 * 60 + 56

    start_res = client.post('/api/ai/start-session', json={
        'mode': 'listening',
        'bookId': 'ielts_listening_premium',
        'chapterId': '17',
    })
    assert start_res.status_code == 201
    session_id = start_res.get_json()['sessionId']

    with app.app_context():
        session = UserStudySession.query.get(session_id)
        assert session is not None
        session.started_at = recovered_start_utc.replace(tzinfo=None)
        db.session.commit()
        add_learning_event(
            user_id=session.user_id,
            event_type='chapter_mode_progress_updated',
            source='chapter_mode_progress',
            mode='listening',
            book_id='ielts_listening_premium',
            chapter_id='17',
            occurred_at=last_activity_utc.replace(tzinfo=None),
        )

        payload, status = log_learning_core_session_response(session.user_id, {
            'sessionId': session_id,
            'mode': 'listening',
            'bookId': 'ielts_listening_premium',
            'chapterId': '17',
            'wordsStudied': 1,
            'correctCount': 1,
            'wrongCount': 1,
            'durationSeconds': int((base_now_utc - recovered_start_utc).total_seconds()),
            'startedAt': int(recovered_start_utc.timestamp() * 1000),
            'endedAt': int(base_now_utc.timestamp() * 1000),
        })

        assert status == 200
        assert payload['id'] == session_id

        db.session.expire_all()
        session = UserStudySession.query.get(session_id)
        assert session is not None
        assert session.duration_seconds == expected_duration_seconds
        assert session.ended_at == (last_activity_utc + timedelta(minutes=5)).replace(tzinfo=None)


def test_learning_stats_caps_live_pending_duration_by_recent_activity(client, app):
    register_and_login(client, username='session-user-live-pending-cap')

    base_now_utc = datetime.now(timezone.utc).replace(microsecond=0)
    recovered_start_utc = base_now_utc - timedelta(hours=2)
    last_activity_utc = recovered_start_utc + timedelta(seconds=42)
    expected_duration_seconds = 5 * 60 + 42

    start_res = client.post('/api/ai/start-session', json={
        'mode': 'listening',
        'bookId': 'ielts_listening_premium',
        'chapterId': '9',
    })
    assert start_res.status_code == 201
    session_id = start_res.get_json()['sessionId']

    with app.app_context():
        session = UserStudySession.query.get(session_id)
        assert session is not None
        session.started_at = recovered_start_utc.replace(tzinfo=None)
        db.session.commit()
        add_learning_event(
            user_id=session.user_id,
            event_type='chapter_mode_progress_updated',
            source='chapter_mode_progress',
            mode='listening',
            book_id='ielts_listening_premium',
            chapter_id='9',
            occurred_at=last_activity_utc.replace(tzinfo=None),
        )

    stats_res = client.get('/api/ai/learning-stats')
    assert stats_res.status_code == 200
    payload = stats_res.get_json()
    assert payload['summary']['total_duration_seconds'] == expected_duration_seconds
    assert payload['alltime']['duration_seconds'] == expected_duration_seconds
    assert payload['alltime']['today_duration_seconds'] == expected_duration_seconds
