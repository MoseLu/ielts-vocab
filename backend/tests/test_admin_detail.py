from datetime import datetime, timedelta

from models import User, UserLearningEvent, UserStudySession, db


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
