import json
from datetime import datetime, timedelta

from models import (
    AdminProjectedDailySummary,
    User,
    UserBookProgress,
    UserChapterProgress,
    UserFavoriteWord,
    UserLearningEvent,
    UserStudySession,
    UserWrongWord,
    db,
)
from platform_sdk.admin_projection_bootstrap import bootstrap_admin_projection_snapshots
from platform_sdk.internal_service_auth import create_internal_auth_headers_for_user
from services import admin_user_detail_repository
from services.books_structure_service import get_book_chapter_count, get_book_word_count


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


def test_admin_user_detail_progress_hides_confusable_book_and_returns_real_progress(client, app):
    register_user(client, 'admin-detail-progress-admin')
    register_user(client, 'admin-detail-progress-learner')

    with app.app_context():
        admin = User.query.filter_by(username='admin-detail-progress-admin').first()
        learner = User.query.filter_by(username='admin-detail-progress-learner').first()
        admin.is_admin = True

        db.session.add_all([
            UserBookProgress(
                user_id=learner.id,
                book_id='ielts_listening_premium',
                current_index=12,
                correct_count=8,
                wrong_count=2,
                is_completed=False,
                updated_at=datetime(2026, 4, 5, 8, 0, 0),
            ),
            UserBookProgress(
                user_id=learner.id,
                book_id='ielts_confusable_match',
                current_index=99,
                correct_count=60,
                wrong_count=8,
                is_completed=False,
                updated_at=datetime(2026, 4, 5, 9, 0, 0),
            ),
            UserChapterProgress(
                user_id=learner.id,
                book_id='ielts_listening_premium',
                chapter_id=1,
                words_learned=30,
                correct_count=18,
                wrong_count=4,
                is_completed=True,
                updated_at=datetime(2026, 4, 6, 10, 0, 0),
            ),
        ])
        db.session.commit()
        learner_id = learner.id

        expected_total_words = get_book_word_count('ielts_listening_premium', user_id=learner.id)
        expected_total_chapters = get_book_chapter_count('ielts_listening_premium', user_id=learner.id)

    login_user(client, 'admin-detail-progress-admin')
    response = client.get(f'/api/admin/users/{learner_id}')

    assert response.status_code == 200
    payload = response.get_json()
    assert [row['book_id'] for row in payload['book_progress']] == ['ielts_listening_premium']

    progress = payload['book_progress'][0]
    assert progress['current_index'] == 30
    assert progress['correct_count'] == 18
    assert progress['wrong_count'] == 4
    assert progress['total_words'] == expected_total_words
    assert progress['total_chapters'] == expected_total_chapters
    assert progress['completed_chapters'] == 1
    assert progress['progress_percent'] == round(30 / expected_total_words * 100)


def test_admin_user_detail_includes_favorite_words(client, app):
    register_user(client, 'admin-detail-favorite-admin')
    register_user(client, 'admin-detail-favorite-learner')

    with app.app_context():
        admin = User.query.filter_by(username='admin-detail-favorite-admin').first()
        learner = User.query.filter_by(username='admin-detail-favorite-learner').first()
        admin.is_admin = True

        db.session.add_all([
            UserFavoriteWord(
                user_id=learner.id,
                word='abandon',
                normalized_word='abandon',
                phonetic='/əˈbændən/',
                pos='v.',
                definition='to leave behind',
                source_book_id='ielts_listening_premium',
                source_book_title='雅思听力精讲',
                source_chapter_id='12',
                source_chapter_title='第12章',
                created_at=datetime(2026, 4, 6, 8, 0, 0),
                updated_at=datetime(2026, 4, 6, 8, 0, 0),
            ),
            UserFavoriteWord(
                user_id=learner.id,
                word='compile',
                normalized_word='compile',
                phonetic='/kəmˈpaɪl/',
                pos='v.',
                definition='to collect information',
                source_book_id='ielts_reading_premium',
                source_book_title='雅思阅读精讲',
                source_chapter_id='3',
                source_chapter_title='第3章',
                created_at=datetime(2026, 4, 7, 8, 0, 0),
                updated_at=datetime(2026, 4, 7, 8, 0, 0),
            ),
        ])
        db.session.commit()
        learner_id = learner.id

    login_user(client, 'admin-detail-favorite-admin')
    response = client.get(f'/api/admin/users/{learner_id}')

    assert response.status_code == 200
    payload = response.get_json()
    assert [item['word'] for item in payload['favorite_words']] == ['compile', 'abandon']
    assert payload['favorite_words'][0]['source_book_title'] == '雅思阅读精讲'
    assert payload['favorite_words'][1]['source_chapter_title'] == '第12章'


def test_admin_user_detail_includes_projected_recent_summaries(client, app):
    register_user(client, 'admin-detail-summary-admin')
    register_user(client, 'admin-detail-summary-learner')

    with app.app_context():
        admin = User.query.filter_by(username='admin-detail-summary-admin').first()
        learner = User.query.filter_by(username='admin-detail-summary-learner').first()
        admin.is_admin = True

        db.session.add_all([
            AdminProjectedDailySummary(
                id=801,
                user_id=learner.id,
                date='2026-04-10',
                content='# 2026-04-10 学习总结\n\n今天完成了阅读复盘。',
                generated_at=datetime(2026, 4, 10, 20, 0, 0),
            ),
            AdminProjectedDailySummary(
                id=802,
                user_id=learner.id,
                date='2026-04-11',
                content='# 2026-04-11 学习总结\n\n今天完成了错词复盘。',
                generated_at=datetime(2026, 4, 11, 20, 0, 0),
            ),
        ])
        db.session.commit()
        learner_id = learner.id

    login_user(client, 'admin-detail-summary-admin')
    response = client.get(f'/api/admin/users/{learner_id}')

    assert response.status_code == 200
    payload = response.get_json()
    assert [item['date'] for item in payload['recent_summaries']] == ['2026-04-11', '2026-04-10']
    assert payload['recent_summaries'][0]['content'].startswith('# 2026-04-11 学习总结')


def test_admin_user_detail_returns_strict_boundary_error_when_learning_core_fallback_is_disabled(
    client,
    app,
    monkeypatch,
):
    register_user(client, 'admin-detail-boundary-admin')
    register_user(client, 'admin-detail-boundary-learner')

    with app.app_context():
        admin = User.query.filter_by(username='admin-detail-boundary-admin').first()
        learner = User.query.filter_by(username='admin-detail-boundary-learner').first()
        assert admin is not None and learner is not None
        admin.is_admin = True
        db.session.add(UserBookProgress(
            user_id=learner.id,
            book_id='ielts_listening_premium',
            current_index=7,
            correct_count=5,
            wrong_count=2,
            is_completed=False,
        ))
        db.session.commit()
        bootstrap_admin_projection_snapshots()
        admin_id = admin.id
        learner_id = learner.id

    monkeypatch.setenv('CURRENT_SERVICE_NAME', 'admin-ops-service')
    monkeypatch.setenv('ALLOW_LEGACY_CROSS_SERVICE_FALLBACK', 'false')

    def _raise(*args, **kwargs):
        raise RuntimeError('learning-core unavailable')

    monkeypatch.setattr(admin_user_detail_repository, 'fetch_learning_core_admin_book_progress_rows', _raise)

    headers = create_internal_auth_headers_for_user(
        user_id=admin_id,
        source_service_name='gateway-bff',
        is_admin=True,
        username='admin-detail-boundary-admin',
        email='admin-detail-boundary-admin@example.com',
        env=app.config,
    )
    response = client.get(f'/api/admin/users/{learner_id}', headers=headers)

    assert response.status_code == 503
    assert response.get_json() == {
        'error': 'learning-core-service unavailable',
        'boundary': 'strict-internal-contract',
        'action': 'admin-detail-book-progress-read',
        'upstream': 'learning-core-service',
    }
