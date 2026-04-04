import json
from datetime import datetime, timedelta

from models import User, UserLearningEvent, UserLearningNote, UserQuickMemoryRecord, UserSmartWordStat, UserStudySession, UserWrongWord, db


def register_and_login(client, username='profile-user', password='password123'):
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


def test_learner_profile_endpoint_returns_focus_words_dimensions_and_topics(client, app):
    register_and_login(client, username='profile-user')

    with app.app_context():
        user = User.query.filter_by(username='profile-user').first()
        assert user is not None

        db.session.add_all([
            UserStudySession(
                user_id=user.id,
                mode='listening',
                words_studied=20,
                correct_count=8,
                wrong_count=12,
                duration_seconds=900,
                started_at=datetime(2026, 3, 30, 9, 0, 0),
            ),
            UserStudySession(
                user_id=user.id,
                mode='meaning',
                words_studied=18,
                correct_count=15,
                wrong_count=3,
                duration_seconds=600,
                started_at=datetime(2026, 3, 30, 14, 0, 0),
            ),
            UserStudySession(
                user_id=user.id,
                mode='dictation',
                words_studied=10,
                correct_count=7,
                wrong_count=3,
                duration_seconds=480,
                started_at=datetime(2026, 3, 29, 10, 0, 0),
            ),
            UserWrongWord(
                user_id=user.id,
                word='kind',
                phonetic='/kaɪnd/',
                pos='n.',
                definition='type',
                wrong_count=5,
                listening_wrong=1,
                meaning_wrong=4,
            ),
            UserWrongWord(
                user_id=user.id,
                word='effect',
                phonetic='/ɪˈfekt/',
                pos='n.',
                definition='result',
                wrong_count=4,
                listening_wrong=2,
                meaning_wrong=2,
            ),
            UserSmartWordStat(
                user_id=user.id,
                word='kind',
                listening_correct=2,
                listening_wrong=3,
                meaning_correct=1,
                meaning_wrong=6,
                dictation_correct=3,
                dictation_wrong=1,
            ),
            UserSmartWordStat(
                user_id=user.id,
                word='effect',
                listening_correct=1,
                listening_wrong=4,
                meaning_correct=2,
                meaning_wrong=3,
                dictation_correct=2,
                dictation_wrong=1,
            ),
            UserQuickMemoryRecord(
                user_id=user.id,
                word='kind',
                status='unknown',
                first_seen=int(datetime(2026, 3, 29, 9, 0, 0).timestamp() * 1000),
                last_seen=int(datetime(2026, 3, 30, 12, 0, 0).timestamp() * 1000),
                known_count=0,
                unknown_count=2,
                next_review=int((datetime.utcnow() - timedelta(hours=1)).timestamp() * 1000),
            ),
            UserLearningNote(
                user_id=user.id,
                question='What is the difference between kind of and a kind of?',
                answer='One is a hedge and the other points to a category.',
                word_context='kind',
                created_at=datetime(2026, 3, 30, 11, 0, 0),
            ),
            UserLearningNote(
                user_id=user.id,
                question='Please explain kind of and a kind of again.',
                answer='The first softens tone, the second names a type.',
                word_context='kind',
                created_at=datetime(2026, 3, 30, 12, 0, 0),
            ),
        ])
        db.session.commit()

    response = client.get('/api/ai/learner-profile?date=2026-03-30')

    assert response.status_code == 200
    data = response.get_json()
    assert data['summary']['weakest_mode'] == 'listening'
    assert data['summary']['streak_days'] >= 2
    assert data['dimensions'][0]['dimension'] == 'meaning'
    assert data['focus_words'][0]['word'] == 'kind'
    assert data['memory_system']['priority_dimension'] == 'recognition'
    assert data['memory_system']['priority_dimension_label'] == '认读'
    assert any(item['key'] == 'speaking' and item['status'] == 'needs_setup' for item in data['memory_system']['dimensions'])
    assert data['repeated_topics'][0]['word_context'] == 'kind'
    assert any('复习' in item for item in data['next_actions'])


def test_learner_profile_includes_recent_live_pending_session_duration(client, app):
    register_and_login(client, username='live-duration-profile-user')

    now = datetime.utcnow().replace(microsecond=0)
    completed_duration = 180
    live_duration_floor = 30 * 60

    with app.app_context():
        user = User.query.filter_by(username='live-duration-profile-user').first()
        assert user is not None

        db.session.add_all([
            UserStudySession(
                user_id=user.id,
                mode='quickmemory',
                words_studied=12,
                correct_count=9,
                wrong_count=3,
                duration_seconds=completed_duration,
                started_at=now - timedelta(hours=1),
                ended_at=now - timedelta(minutes=57),
            ),
            UserStudySession(
                user_id=user.id,
                mode='quickmemory',
                started_at=now - timedelta(minutes=30),
            ),
        ])
        db.session.commit()

    response = client.get(f"/api/ai/learner-profile?date={now.strftime('%Y-%m-%d')}")

    assert response.status_code == 200
    data = response.get_json()
    expected_floor = completed_duration + live_duration_floor
    assert data['summary']['today_sessions'] == 1
    assert data['summary']['today_duration_seconds'] >= expected_floor
    assert data['summary']['today_duration_seconds'] < expected_floor + 20


def test_learner_profile_speaking_dimension_uses_persistent_events(client, app):
    register_and_login(client, username='speaking-profile-user')

    now = datetime.utcnow().replace(microsecond=0)

    with app.app_context():
        user = User.query.filter_by(username='speaking-profile-user').first()
        assert user is not None

        db.session.add_all([
            UserLearningEvent(
                user_id=user.id,
                event_type='pronunciation_check',
                source='assistant',
                mode='speaking',
                word='dynamic',
                item_count=1,
                correct_count=1,
                wrong_count=0,
                payload=json.dumps({
                    'score': 85,
                    'passed': True,
                    'sentence': 'Dynamic pricing can confuse users.',
                }, ensure_ascii=False),
                occurred_at=now - timedelta(days=3),
            ),
            UserLearningEvent(
                user_id=user.id,
                event_type='speaking_simulation',
                source='assistant',
                mode='speaking',
                item_count=1,
                correct_count=1,
                wrong_count=0,
                payload=json.dumps({
                    'part': 2,
                    'topic': 'education',
                    'target_words': ['dynamic'],
                    'response_text': 'Dynamic vocabulary helped me explain the chart.',
                }, ensure_ascii=False),
                occurred_at=now - timedelta(days=2),
            ),
        ])
        db.session.commit()

    response = client.get(f"/api/ai/learner-profile?date={now.strftime('%Y-%m-%d')}")

    assert response.status_code == 200
    data = response.get_json()
    speaking = next(item for item in data['memory_system']['dimensions'] if item['key'] == 'speaking')

    assert speaking['tracked'] is True
    assert speaking['status'] == 'due'
    assert speaking['tracked_words'] == 1
    assert speaking['due_words'] == 1
    assert 'dynamic' in speaking['focus_words']


def test_learner_profile_listening_and_writing_dimensions_use_timed_events(client, app):
    register_and_login(client, username='timed-dimension-user')

    now = datetime.utcnow().replace(microsecond=0)

    with app.app_context():
        user = User.query.filter_by(username='timed-dimension-user').first()
        assert user is not None

        db.session.add_all([
            UserLearningEvent(
                user_id=user.id,
                event_type='listening_review',
                source='practice',
                mode='listening',
                word='dynamic',
                item_count=1,
                correct_count=1,
                wrong_count=0,
                payload=json.dumps({
                    'passed': True,
                    'source_mode': 'smart',
                }, ensure_ascii=False),
                occurred_at=now - timedelta(days=3),
            ),
            UserLearningEvent(
                user_id=user.id,
                event_type='writing_review',
                source='practice',
                mode='dictation',
                word='coherent',
                item_count=1,
                correct_count=1,
                wrong_count=0,
                payload=json.dumps({
                    'passed': True,
                    'source_mode': 'dictation',
                }, ensure_ascii=False),
                occurred_at=now - timedelta(days=3),
            ),
        ])
        db.session.commit()

    response = client.get(f"/api/ai/learner-profile?date={now.strftime('%Y-%m-%d')}")

    assert response.status_code == 200
    data = response.get_json()
    listening = next(item for item in data['memory_system']['dimensions'] if item['key'] == 'listening')
    writing = next(item for item in data['memory_system']['dimensions'] if item['key'] == 'writing')

    assert listening['tracking_level'] == 'full'
    assert listening['tracked'] is True
    assert listening['status'] == 'due'
    assert listening['due_words'] == 1
    assert 'dynamic' in listening['focus_words']

    assert writing['tracking_level'] == 'full'
    assert writing['tracked'] is True
    assert writing['status'] == 'due'
    assert writing['due_words'] == 1
    assert 'coherent' in writing['focus_words']


def test_learner_profile_uses_local_calendar_day_for_sessions_and_activity(client, app):
    register_and_login(client, username='local-day-profile-user')

    with app.app_context():
        user = User.query.filter_by(username='local-day-profile-user').first()
        assert user is not None

        db.session.add(
            UserStudySession(
                user_id=user.id,
                mode='quickmemory',
                words_studied=4,
                correct_count=3,
                wrong_count=1,
                duration_seconds=300,
                started_at=datetime(2026, 4, 2, 23, 30, 0),
                ended_at=datetime(2026, 4, 2, 23, 35, 0),
            )
        )
        db.session.add(
            UserLearningEvent(
                user_id=user.id,
                event_type='quick_memory_review',
                source='quickmemory',
                mode='quickmemory',
                word='section',
                item_count=1,
                correct_count=0,
                wrong_count=1,
                occurred_at=datetime(2026, 4, 2, 23, 40, 0),
            )
        )
        db.session.commit()

    response = client.get('/api/ai/learner-profile?date=2026-04-03')

    assert response.status_code == 200
    data = response.get_json()
    assert data['summary']['today_sessions'] == 1
    assert data['summary']['today_duration_seconds'] == 300
    assert data['activity_summary']['total_events'] == 1
    assert data['recent_activity'][0]['word'] == 'section'
