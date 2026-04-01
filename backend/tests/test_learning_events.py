from datetime import datetime

from models import UserLearningEvent, db
from routes import ai as ai_routes


def register_and_login(client, username='event-user', password='password123'):
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


def test_learner_profile_activity_summary_merges_events_from_multiple_sources(client, app, monkeypatch):
    register_and_login(client)

    start_res = client.post('/api/ai/start-session', json={
        'mode': 'listening',
        'bookId': 'ielts_reading_premium',
        'chapterId': '3',
    })
    assert start_res.status_code == 201
    session_id = start_res.get_json()['sessionId']

    log_res = client.post('/api/ai/log-session', json={
        'sessionId': session_id,
        'mode': 'listening',
        'bookId': 'ielts_reading_premium',
        'chapterId': '3',
        'wordsStudied': 12,
        'correctCount': 9,
        'wrongCount': 3,
        'durationSeconds': 180,
        'startedAt': int(datetime.utcnow().timestamp() * 1000),
    })
    assert log_res.status_code == 200

    qm_res = client.post('/api/ai/quick-memory/sync', json={
        'source': 'quickmemory',
        'records': [{
            'word': 'kind',
            'bookId': 'ielts_reading_premium',
            'chapterId': '3',
            'status': 'known',
            'firstSeen': 1,
            'lastSeen': 2,
            'knownCount': 1,
            'unknownCount': 0,
            'nextReview': 3,
            'fuzzyCount': 0,
        }],
    })
    assert qm_res.status_code == 200

    wrong_res = client.post('/api/ai/wrong-words/sync', json={
        'sourceMode': 'listening',
        'bookId': 'ielts_reading_premium',
        'chapterId': '3',
        'words': [{
            'word': 'effect',
            'definition': 'result',
            'wrongCount': 1,
            'listeningWrong': 1,
        }],
    })
    assert wrong_res.status_code == 200

    monkeypatch.setattr(ai_routes, '_chat_with_tools', lambda *args, **kwargs: {'text': '已回答'})
    ask_res = client.post('/api/ai/ask', json={
        'message': 'kind 和 effect 有什么区别？',
        'context': {
            'currentWord': 'kind',
            'practiceMode': 'listening',
        },
    })
    assert ask_res.status_code == 200

    today = datetime.utcnow().strftime('%Y-%m-%d')
    profile_res = client.get(f'/api/ai/learner-profile?date={today}')
    assert profile_res.status_code == 200
    data = profile_res.get_json()

    assert data['activity_summary']['total_events'] >= 4
    assert data['activity_summary']['study_sessions'] >= 1
    assert data['activity_summary']['quick_memory_reviews'] >= 1
    assert data['activity_summary']['wrong_word_records'] >= 1
    assert data['activity_summary']['assistant_questions'] >= 1
    assert any(item['source'] == 'quickmemory' for item in data['activity_source_breakdown'])
    assert any('向助手提问' in item['title'] for item in data['recent_activity'])

    with app.app_context():
        assert UserLearningEvent.query.count() >= 4

