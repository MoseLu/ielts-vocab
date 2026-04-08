from datetime import datetime, timedelta

from models import User, UserBookProgress, UserStudySession, db


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


def test_admin_overview_returns_platform_stats(client, app):
    register_user(client, 'admin-overview-admin')
    register_user(client, 'admin-overview-learner')

    with app.app_context():
        admin = User.query.filter_by(username='admin-overview-admin').first()
        learner = User.query.filter_by(username='admin-overview-learner').first()
        assert admin is not None and learner is not None
        admin.is_admin = True

        now = datetime.utcnow()
        db.session.add(UserStudySession(
            user_id=learner.id,
            mode='listening',
            book_id='ielts_listening_premium',
            chapter_id='2',
            words_studied=10,
            correct_count=7,
            wrong_count=3,
            duration_seconds=600,
            started_at=now - timedelta(hours=1),
            ended_at=now,
        ))
        db.session.commit()

    login_user(client, 'admin-overview-admin')
    response = client.get('/api/admin/overview')

    assert response.status_code == 200
    payload = response.get_json()
    assert payload['total_users'] == 3
    assert payload['active_users_today'] == 1
    assert payload['active_users_7d'] == 1
    assert payload['total_sessions'] == 1
    assert payload['total_study_seconds'] == 600
    assert payload['total_words_studied'] == 10
    assert payload['avg_accuracy'] == 70
    assert payload['mode_stats'][0]['mode'] == 'listening'
    assert payload['top_books'][0]['book_id'] == 'ielts_listening_premium'


def test_admin_users_supports_stat_sorting(client, app):
    register_user(client, 'admin-users-admin')
    register_user(client, 'admin-users-fast')
    register_user(client, 'admin-users-accurate')

    with app.app_context():
        admin = User.query.filter_by(username='admin-users-admin').first()
        fast = User.query.filter_by(username='admin-users-fast').first()
        accurate = User.query.filter_by(username='admin-users-accurate').first()
        assert admin is not None and fast is not None and accurate is not None
        admin.is_admin = True

        now = datetime.utcnow()
        db.session.add_all([
            UserStudySession(
                user_id=fast.id,
                mode='quickmemory',
                book_id='ielts_reading_premium',
                chapter_id='1',
                words_studied=20,
                correct_count=10,
                wrong_count=10,
                duration_seconds=1200,
                started_at=now - timedelta(days=1),
                ended_at=now - timedelta(days=1) + timedelta(minutes=20),
            ),
            UserStudySession(
                user_id=accurate.id,
                mode='meaning',
                book_id='ielts_listening_premium',
                chapter_id='2',
                words_studied=8,
                correct_count=8,
                wrong_count=0,
                duration_seconds=300,
                started_at=now - timedelta(hours=2),
                ended_at=now - timedelta(hours=2) + timedelta(minutes=5),
            ),
            UserBookProgress(
                user_id=fast.id,
                book_id='ielts_reading_premium',
                current_index=10,
                correct_count=6,
                wrong_count=4,
                is_completed=False,
            ),
            UserBookProgress(
                user_id=accurate.id,
                book_id='ielts_listening_premium',
                current_index=8,
                correct_count=8,
                wrong_count=0,
                is_completed=False,
            ),
        ])
        db.session.commit()

    login_user(client, 'admin-users-admin')

    study_time_res = client.get('/api/admin/users?sort=study_time&order=desc')
    assert study_time_res.status_code == 200
    study_time_users = study_time_res.get_json()['users']
    assert [user['username'] for user in study_time_users[:2]] == [
        'admin-users-fast',
        'admin-users-accurate',
    ]

    accuracy_res = client.get('/api/admin/users?sort=accuracy&order=desc')
    assert accuracy_res.status_code == 200
    accuracy_users = accuracy_res.get_json()['users']
    assert [user['username'] for user in accuracy_users[:2]] == [
        'admin-users-accurate',
        'admin-users-fast',
    ]
    assert accuracy_users[0]['stats']['accuracy'] == 100
