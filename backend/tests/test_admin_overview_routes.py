from datetime import datetime, timedelta

from models import AdminProjectedPromptRun, AdminProjectedTTSMedia, User, UserBookProgress, UserStudySession, db
from services import admin_user_detail_repository


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
    assert payload['prompt_run_events_today'] == 0
    assert payload['prompt_run_events_7d'] == 0
    assert payload['recent_prompt_runs'] == []
    assert payload['tts_media_events_today'] == 0
    assert payload['tts_media_events_7d'] == 0
    assert payload['recent_tts_media'] == []
    assert payload['mode_stats'][0]['mode'] == 'listening'
    assert payload['top_books'][0]['book_id'] == 'ielts_listening_premium'


def test_admin_overview_includes_recent_projected_tts_media(client, app):
    register_user(client, 'admin-overview-tts-admin')
    register_user(client, 'admin-overview-tts-learner')

    with app.app_context():
        admin = User.query.filter_by(username='admin-overview-tts-admin').first()
        learner = User.query.filter_by(username='admin-overview-tts-learner').first()
        assert admin is not None and learner is not None
        admin.is_admin = True

        now = datetime.utcnow()
        db.session.add_all([
            AdminProjectedTTSMedia(
                event_id='evt-tts-1',
                user_id=learner.id,
                media_kind='example-audio',
                media_id='example-1.mp3',
                tts_provider='minimax',
                storage_provider='local-cache',
                model='qwen-tts-2025-05-22',
                voice='Cherry',
                byte_length=803,
                generated_at=now - timedelta(hours=2),
            ),
            AdminProjectedTTSMedia(
                event_id='evt-tts-2',
                user_id=learner.id,
                media_kind='tts-generate',
                media_id='generate-2.mp3',
                tts_provider='azure',
                storage_provider='local-cache',
                model='azure-rest:audio-24khz-48kbitrate-mono-mp3',
                voice='en-US-AndrewMultilingualNeural',
                byte_length=912,
                generated_at=now - timedelta(minutes=30),
            ),
        ])
        db.session.commit()

    login_user(client, 'admin-overview-tts-admin')
    response = client.get('/api/admin/overview')

    assert response.status_code == 200
    payload = response.get_json()
    assert payload['tts_media_events_today'] == 2
    assert payload['tts_media_events_7d'] == 2
    assert [row['event_id'] for row in payload['recent_tts_media']] == ['evt-tts-2', 'evt-tts-1']
    assert payload['recent_tts_media'][0]['media_kind'] == 'tts-generate'
    assert payload['recent_tts_media'][0]['byte_length'] == 912


def test_admin_overview_includes_recent_projected_prompt_runs(client, app):
    register_user(client, 'admin-overview-prompt-admin')
    register_user(client, 'admin-overview-prompt-learner')

    with app.app_context():
        admin = User.query.filter_by(username='admin-overview-prompt-admin').first()
        learner = User.query.filter_by(username='admin-overview-prompt-learner').first()
        assert admin is not None and learner is not None
        admin.is_admin = True

        now = datetime.utcnow()
        db.session.add_all([
            AdminProjectedPromptRun(
                id=101,
                event_id='evt-prompt-1',
                user_id=learner.id,
                run_kind='assistant.ask',
                provider='minimax',
                model='MiniMax-M2.7-highspeed',
                prompt_excerpt='今天怎么复习？',
                response_excerpt='先复习今天到期的错词。',
                completed_at=now - timedelta(hours=1),
            ),
            AdminProjectedPromptRun(
                id=102,
                event_id='evt-prompt-2',
                user_id=learner.id,
                run_kind='custom-book.generate',
                provider='minimax',
                model='MiniMax-M2.7-highspeed',
                prompt_excerpt='请生成一份学术高频词书。',
                response_excerpt='{\"title\":\"学术高频词\"}',
                result_ref='custom_book_102',
                completed_at=now - timedelta(minutes=20),
            ),
        ])
        db.session.commit()

    login_user(client, 'admin-overview-prompt-admin')
    response = client.get('/api/admin/overview')

    assert response.status_code == 200
    payload = response.get_json()
    assert payload['prompt_run_events_today'] == 2
    assert payload['prompt_run_events_7d'] == 2
    assert [row['event_id'] for row in payload['recent_prompt_runs']] == ['evt-prompt-2', 'evt-prompt-1']
    assert payload['recent_prompt_runs'][0]['run_kind'] == 'custom-book.generate'
    assert payload['recent_prompt_runs'][0]['result_ref'] == 'custom_book_102'


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


def test_admin_users_return_strict_boundary_error_when_learning_core_fallback_is_disabled(
    client,
    app,
    monkeypatch,
):
    register_user(client, 'admin-users-boundary-admin')
    register_user(client, 'admin-users-boundary-learner')

    with app.app_context():
        admin = User.query.filter_by(username='admin-users-boundary-admin').first()
        learner = User.query.filter_by(username='admin-users-boundary-learner').first()
        assert admin is not None and learner is not None
        admin.is_admin = True
        db.session.add(UserBookProgress(
            user_id=learner.id,
            book_id='ielts_listening_premium',
            current_index=6,
            correct_count=4,
            wrong_count=2,
            is_completed=False,
        ))
        db.session.commit()

    monkeypatch.setenv('CURRENT_SERVICE_NAME', 'admin-ops-service')
    monkeypatch.setenv('ALLOW_LEGACY_CROSS_SERVICE_FALLBACK', 'false')

    def _raise(*args, **kwargs):
        raise RuntimeError('learning-core unavailable')

    monkeypatch.setattr(admin_user_detail_repository, 'fetch_learning_core_admin_book_progress_rows', _raise)

    login_user(client, 'admin-users-boundary-admin')
    response = client.get('/api/admin/users')

    assert response.status_code == 503
    assert response.get_json() == {
        'error': 'learning-core-service unavailable',
        'boundary': 'strict-internal-contract',
        'action': 'admin-detail-book-progress-read',
        'upstream': 'learning-core-service',
    }
