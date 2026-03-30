from datetime import datetime, timedelta

from models import User, UserLearningNote, UserQuickMemoryRecord, UserSmartWordStat, UserStudySession, UserWrongWord, db


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
    assert data['repeated_topics'][0]['word_context'] == 'kind'
    assert any('复习' in item for item in data['next_actions'])
