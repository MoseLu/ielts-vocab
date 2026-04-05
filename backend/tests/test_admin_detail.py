import json
from datetime import datetime, timedelta

from models import User, UserLearningEvent, UserStudySession, UserWrongWord, db


def register_user(client, username, password='password123'):
    response = client.post('/api/auth/register', json={
        'username': username,
        'password': password,
        'email': f'{username}@example.com',
    })
    assert response.status_code == 201


def login_user(client, username, password='password123'):
    response = client.post('/api/auth/login', json={
        'email': username,
        'password': password,
    })
    assert response.status_code == 200


def test_admin_user_detail_includes_session_end_and_word_samples(client, app):
    register_user(client, 'admin-detail-admin')
    register_user(client, 'admin-detail-learner')

    with app.app_context():
        admin = User.query.filter_by(username='admin-detail-admin').first()
        learner = User.query.filter_by(username='admin-detail-learner').first()
        admin.is_admin = True

        session_start = datetime(2026, 4, 1, 9, 0, 0)
        session_end = session_start + timedelta(minutes=15)

        db.session.add(UserStudySession(
            user_id=learner.id,
            mode='quickmemory',
            book_id='ielts_listening_premium',
            chapter_id='44',
            words_studied=12,
            correct_count=9,
            wrong_count=3,
            duration_seconds=900,
            started_at=session_start,
            ended_at=session_end,
        ))
        db.session.flush()

        db.session.add_all([
            UserLearningEvent(
                user_id=learner.id,
                event_type='quick_memory_review',
                source='quickmemory',
                mode='quickmemory',
                book_id='ielts_listening_premium',
                chapter_id='44',
                word='campaign',
                occurred_at=session_start + timedelta(minutes=2),
            ),
            UserLearningEvent(
                user_id=learner.id,
                event_type='wrong_word_recorded',
                source='wrong_words',
                mode='quickmemory',
                book_id='ielts_listening_premium',
                chapter_id='44',
                word='engine',
                occurred_at=session_start + timedelta(minutes=6),
            ),
            UserLearningEvent(
                user_id=learner.id,
                event_type='quick_memory_review',
                source='quickmemory',
                mode='quickmemory',
                book_id='ielts_listening_premium',
                chapter_id='44',
                word='campaign',
                occurred_at=session_start + timedelta(minutes=8),
            ),
            UserLearningEvent(
                user_id=learner.id,
                event_type='quick_memory_review',
                source='quickmemory',
                mode='quickmemory',
                book_id='ielts_listening_premium',
                chapter_id='44',
                word='satellite',
                occurred_at=session_start + timedelta(minutes=10),
            ),
            UserLearningEvent(
                user_id=learner.id,
                event_type='quick_memory_review',
                source='quickmemory',
                mode='quickmemory',
                book_id='ielts_listening_premium',
                chapter_id='44',
                word='outside',
                occurred_at=session_end + timedelta(minutes=5),
            ),
        ])
        db.session.commit()
        learner_id = learner.id

    login_user(client, 'admin-detail-admin')
    response = client.get(f'/api/admin/users/{learner_id}')

    assert response.status_code == 200
    payload = response.get_json()
    assert len(payload['sessions']) == 1

    session = payload['sessions'][0]
    assert session['ended_at'] == '2026-04-01T09:15:00+00:00'
    assert session['studied_words'] == ['campaign', 'engine', 'satellite']
    assert session['studied_words_total'] == 3


def test_admin_user_detail_wrong_words_supports_last_error_and_wrong_count_sort(client, app):
    register_user(client, 'admin-detail-sort-admin')
    register_user(client, 'admin-detail-sort-learner')

    with app.app_context():
        admin = User.query.filter_by(username='admin-detail-sort-admin').first()
        learner = User.query.filter_by(username='admin-detail-sort-learner').first()
        admin.is_admin = True

        def build_dimension_state(history_wrong, last_wrong_at):
            return json.dumps({
                'recognition': {
                    'history_wrong': history_wrong,
                    'pass_streak': 0,
                    'last_wrong_at': last_wrong_at,
                    'last_pass_at': None,
                },
                'meaning': {
                    'history_wrong': 0,
                    'pass_streak': 0,
                    'last_wrong_at': None,
                    'last_pass_at': None,
                },
                'listening': {
                    'history_wrong': 0,
                    'pass_streak': 0,
                    'last_wrong_at': None,
                    'last_pass_at': None,
                },
                'dictation': {
                    'history_wrong': 0,
                    'pass_streak': 0,
                    'last_wrong_at': None,
                    'last_pass_at': None,
                },
            }, ensure_ascii=False)

        db.session.add_all([
            UserWrongWord(
                user_id=learner.id,
                word='alpha',
                phonetic='/a/',
                pos='n.',
                definition='alpha definition',
                wrong_count=9,
                dimension_state=build_dimension_state(9, '2026-04-01T08:00:00+00:00'),
                updated_at=datetime(2026, 4, 4, 8, 0, 0),
            ),
            UserWrongWord(
                user_id=learner.id,
                word='beta',
                phonetic='/b/',
                pos='n.',
                definition='beta definition',
                wrong_count=3,
                dimension_state=build_dimension_state(3, '2026-04-04T10:00:00+00:00'),
                updated_at=datetime(2026, 4, 4, 10, 0, 0),
            ),
            UserWrongWord(
                user_id=learner.id,
                word='gamma',
                phonetic='/g/',
                pos='n.',
                definition='gamma definition',
                wrong_count=9,
                dimension_state=build_dimension_state(9, '2026-04-03T09:00:00+00:00'),
                updated_at=datetime(2026, 4, 3, 9, 0, 0),
            ),
        ])
        db.session.commit()
        learner_id = learner.id

    login_user(client, 'admin-detail-sort-admin')

    default_response = client.get(f'/api/admin/users/{learner_id}')
    assert default_response.status_code == 200
    default_wrong_words = default_response.get_json()['wrong_words']
    assert [item['word'] for item in default_wrong_words[:3]] == ['beta', 'gamma', 'alpha']
    assert default_wrong_words[0]['last_wrong_at'] == '2026-04-04T10:00:00+00:00'

    count_response = client.get(f'/api/admin/users/{learner_id}?wrong_words_sort=wrong_count')
    assert count_response.status_code == 200
    count_wrong_words = count_response.get_json()['wrong_words']
    assert [item['word'] for item in count_wrong_words[:3]] == ['gamma', 'alpha', 'beta']
