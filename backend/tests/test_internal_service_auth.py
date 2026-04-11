from __future__ import annotations

import importlib.util
from pathlib import Path

from fastapi.testclient import TestClient
from models import (
    User,
    UserChapterProgress,
    UserLearningEvent,
    UserLearningNote,
    UserQuickMemoryRecord,
    UserWrongWord,
    db,
)

from platform_sdk.internal_service_auth import (
    INTERNAL_SERVICE_AUTH_HEADER,
    SERVICE_NAME_HEADER,
    create_internal_service_token,
    internal_service_secret,
    internal_service_token_ttl_seconds,
)


LEARNING_CORE_SERVICE_PATH = (
    Path(__file__).resolve().parents[2]
    / 'services'
    / 'learning-core-service'
    / 'main.py'
)
ADMIN_OPS_SERVICE_PATH = (
    Path(__file__).resolve().parents[2]
    / 'services'
    / 'admin-ops-service'
    / 'main.py'
)
NOTES_SERVICE_PATH = (
    Path(__file__).resolve().parents[2]
    / 'services'
    / 'notes-service'
    / 'main.py'
)
CATALOG_CONTENT_SERVICE_PATH = (
    Path(__file__).resolve().parents[2]
    / 'services'
    / 'catalog-content-service'
    / 'main.py'
)
IDENTITY_SERVICE_PATH = (
    Path(__file__).resolve().parents[2]
    / 'services'
    / 'identity-service'
    / 'main.py'
)


def _load_module(module_name: str, path: Path):
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _configure_env(monkeypatch, tmp_path: Path, service_name: str) -> None:
    monkeypatch.setenv('SECRET_KEY', 'test-secret')
    monkeypatch.setenv('JWT_SECRET_KEY', 'test-jwt-secret')
    monkeypatch.setenv('INTERNAL_SERVICE_JWT_SECRET_KEY', 'test-jwt-secret')
    monkeypatch.setenv('COOKIE_SECURE', 'false')
    monkeypatch.setenv('EMAIL_CODE_DELIVERY_MODE', 'mock')
    monkeypatch.setenv('SQLITE_DB_PATH', str(tmp_path / f'{service_name}.sqlite'))
    monkeypatch.setenv('DB_BACKUP_ENABLED', 'false')


def _internal_headers(*, user_id: int, is_admin: bool = False) -> dict[str, str]:
    token = create_internal_service_token(
        secret='test-jwt-secret',
        source_service_name='gateway-bff',
        user_id=user_id,
        is_admin=is_admin,
        scopes=('admin', 'user') if is_admin else ('user',),
        request_id='req-internal',
        trace_id='trace-internal',
    )
    return {
        INTERNAL_SERVICE_AUTH_HEADER: token,
        SERVICE_NAME_HEADER: 'gateway-bff',
    }


def _create_user(flask_app, username: str) -> int:
    with flask_app.app_context():
        user = User(username=username, email=f'{username}@example.com')
        user.set_password('password123')
        db.session.add(user)
        db.session.commit()
        return user.id


def test_learning_core_accepts_internal_service_user_without_local_user_row(monkeypatch, tmp_path):
    _configure_env(monkeypatch, tmp_path, 'learning-core-internal')
    module = _load_module('learning_core_service_internal_auth', LEARNING_CORE_SERVICE_PATH)
    client = TestClient(module.app)

    response = client.get(
        '/api/books/progress',
        headers=_internal_headers(user_id=90210),
    )

    assert response.status_code == 200
    assert response.json() == {'progress': {}}


def test_identity_service_prefers_cookie_user_over_gateway_internal_snapshot(monkeypatch, tmp_path):
    _configure_env(monkeypatch, tmp_path, 'identity-cookie-priority')
    module = _load_module('identity_service_cookie_priority', IDENTITY_SERVICE_PATH)
    _create_user(module.identity_flask_app, 'identity-cookie-priority-user')
    client = TestClient(module.app)

    login_response = client.post('/api/auth/login', json={
        'email': 'identity-cookie-priority-user',
        'password': 'password123',
    })
    assert login_response.status_code == 200

    response = client.get(
        '/api/auth/me',
        headers=_internal_headers(user_id=90210),
    )

    assert response.status_code == 200
    payload = response.json()['user']
    assert payload['username'] == 'identity-cookie-priority-user'
    assert payload['created_at']


def test_learning_core_internal_read_routes_accept_internal_service_user(monkeypatch, tmp_path):
    _configure_env(monkeypatch, tmp_path, 'learning-core-internal-reads')
    module = _load_module('learning_core_service_internal_reads', LEARNING_CORE_SERVICE_PATH)
    client = TestClient(module.app)
    headers = _internal_headers(user_id=90210)

    context_response = client.get('/internal/learning/context', headers=headers)
    stats_response = client.get('/internal/learning/stats?days=7', headers=headers)

    assert context_response.status_code == 200
    assert 'memory' not in context_response.json()
    assert 'learnerProfile' not in context_response.json()
    assert context_response.json()['totalSessions'] == 0
    assert stats_response.status_code == 200
    assert stats_response.json()['summary']['total_words'] == 0


def test_learning_core_internal_event_route_accepts_internal_service_user(monkeypatch, tmp_path):
    _configure_env(monkeypatch, tmp_path, 'learning-core-internal-event')
    module = _load_module('learning_core_service_internal_event', LEARNING_CORE_SERVICE_PATH)
    user_id = _create_user(module.learning_core_flask_app, 'learning-core-internal-event-user')
    client = TestClient(module.app)

    response = client.post(
        '/internal/learning/events',
        headers=_internal_headers(user_id=user_id),
        json={
            'event_type': 'assistant_question',
            'source': 'assistant',
            'mode': 'smart',
            'word': 'abandon',
            'payload': {'question': 'How do I use abandon?'},
        },
    )

    assert response.status_code == 201
    assert response.json()['event']['event_type'] == 'assistant_question'
    with module.learning_core_flask_app.app_context():
        assert UserLearningEvent.query.filter_by(user_id=user_id, word='abandon').count() == 1


def test_learning_core_internal_ai_tool_routes_accept_internal_service_user(monkeypatch, tmp_path):
    _configure_env(monkeypatch, tmp_path, 'learning-core-internal-ai-tool')
    module = _load_module('learning_core_service_internal_ai_tool', LEARNING_CORE_SERVICE_PATH)
    user_id = _create_user(module.learning_core_flask_app, 'learning-core-internal-ai-tool-user')
    client = TestClient(module.app)

    with module.learning_core_flask_app.app_context():
        db.session.add(UserWrongWord(user_id=user_id, word='alpha', wrong_count=2))
        db.session.add(UserQuickMemoryRecord(
            user_id=user_id,
            word='alpha',
            status='known',
            first_seen=1000,
            last_seen=2000,
            known_count=2,
            unknown_count=0,
            next_review=3000,
        ))
        db.session.add(UserChapterProgress(
            user_id=user_id,
            book_id='ielts_reading_premium',
            chapter_id=2,
            correct_count=7,
            wrong_count=3,
            is_completed=True,
        ))
        db.session.commit()

    headers = _internal_headers(user_id=user_id)
    wrong_words_response = client.get(
        '/internal/learning/ai-tool/wrong-words?limit=5&query=alp',
        headers=headers,
    )
    chapter_progress_response = client.get(
        '/internal/learning/ai-tool/chapter-progress?book_id=ielts_reading_premium',
        headers=headers,
    )
    count_response = client.get(
        '/internal/learning/ai-tool/wrong-word-count',
        headers=headers,
    )
    quick_memory_response = client.get(
        '/internal/learning/quick-memory',
        headers=headers,
    )
    review_queue_response = client.get(
        '/internal/learning/quick-memory/review-queue?limit=5',
        headers=headers,
    )

    assert wrong_words_response.status_code == 200
    assert wrong_words_response.json()['words'][0]['word'] == 'alpha'
    assert chapter_progress_response.status_code == 200
    assert chapter_progress_response.json()['progress'][0]['chapter_id'] == 2
    assert chapter_progress_response.json()['progress'][0]['accuracy'] == 70
    assert count_response.status_code == 200
    assert count_response.json()['count'] == 1
    assert quick_memory_response.status_code == 200
    assert quick_memory_response.json()['records'][0]['word'] == 'alpha'
    assert review_queue_response.status_code == 200
    assert 'summary' in review_queue_response.json()


def test_learning_core_internal_sync_routes_accept_internal_service_user(monkeypatch, tmp_path):
    _configure_env(monkeypatch, tmp_path, 'learning-core-internal-sync')
    module = _load_module('learning_core_service_internal_sync', LEARNING_CORE_SERVICE_PATH)
    user_id = _create_user(module.learning_core_flask_app, 'learning-core-internal-sync-user')
    client = TestClient(module.app)
    headers = _internal_headers(user_id=user_id)

    quick_memory_response = client.post(
        '/internal/learning/quick-memory/sync',
        headers=headers,
        json={
            'source': 'internal-sync',
            'records': [{
                'word': 'kind',
                'status': 'known',
                'firstSeen': 1000,
                'lastSeen': 2000,
                'knownCount': 2,
                'unknownCount': 0,
                'nextReview': 3000,
            }],
        },
    )
    smart_stats_response = client.post(
        '/internal/learning/smart-stats/sync',
        headers=headers,
        json={
            'context': {'bookId': 'ielts_listening_premium', 'chapterId': '4', 'mode': 'smart'},
            'stats': [{
                'word': 'kind',
                'listening': {'correct': 2, 'wrong': 1},
                'meaning': {'correct': 0, 'wrong': 0},
                'dictation': {'correct': 1, 'wrong': 0},
            }],
        },
    )
    wrong_words_sync_response = client.post(
        '/internal/learning/wrong-words/sync',
        headers=headers,
        json={
            'sourceMode': 'smart',
            'words': [{
                'word': 'abandon',
                'definition': 'leave behind',
                'wrongCount': 1,
                'recognitionWrong': 1,
            }],
        },
    )
    wrong_words_list_response = client.get(
        '/internal/learning/wrong-words?details=compact',
        headers=headers,
    )
    wrong_words_clear_response = client.post(
        '/internal/learning/wrong-words/clear',
        headers=headers,
        json={'word': 'abandon'},
    )

    assert quick_memory_response.status_code == 200
    assert quick_memory_response.json()['ok'] is True
    assert smart_stats_response.status_code == 200
    assert smart_stats_response.json()['ok'] is True
    assert wrong_words_sync_response.status_code == 200
    assert wrong_words_sync_response.json()['updated'] == 1
    assert wrong_words_list_response.status_code == 200
    assert wrong_words_list_response.json()['words'][0]['word'] == 'abandon'
    assert wrong_words_clear_response.status_code == 200
    assert wrong_words_clear_response.json()['message']


def test_learning_core_internal_study_session_routes_accept_internal_service_user(monkeypatch, tmp_path):
    _configure_env(monkeypatch, tmp_path, 'learning-core-internal-study-sessions')
    module = _load_module('learning_core_service_internal_study_sessions', LEARNING_CORE_SERVICE_PATH)
    user_id = _create_user(module.learning_core_flask_app, 'learning-core-internal-study-user')
    client = TestClient(module.app)
    headers = _internal_headers(user_id=user_id)

    start_response = client.post(
        '/internal/learning/study-sessions/start',
        headers=headers,
        json={'mode': 'smart', 'bookId': 'ielts_reading_premium', 'chapterId': '3'},
    )
    session_id = start_response.json()['sessionId']
    log_response = client.post(
        '/internal/learning/study-sessions/log',
        headers=headers,
        json={
            'sessionId': session_id,
            'mode': 'smart',
            'bookId': 'ielts_reading_premium',
            'chapterId': '3',
            'wordsStudied': 5,
            'correctCount': 4,
            'wrongCount': 1,
            'durationSeconds': 60,
        },
    )
    cancel_response = client.post(
        '/internal/learning/study-sessions/cancel',
        headers=headers,
        json={'sessionId': session_id},
    )

    assert start_response.status_code == 201
    assert log_response.status_code == 200
    assert log_response.json()['id'] == session_id
    assert cancel_response.status_code == 409


def test_notes_internal_learning_note_routes_accept_internal_service_user(monkeypatch, tmp_path):
    _configure_env(monkeypatch, tmp_path, 'notes-internal-routes')
    module = _load_module('notes_service_internal_routes', NOTES_SERVICE_PATH)
    user_id = _create_user(module.notes_flask_app, 'notes-internal-routes-user')
    client = TestClient(module.app)

    with module.notes_flask_app.app_context():
        db.session.add(UserLearningNote(
            user_id=user_id,
            question='What is vivid?',
            answer='Bright or clear.',
            word_context='vivid',
        ))
        db.session.commit()

    list_response = client.get(
        '/internal/notes/learning-notes?limit=5',
        headers=_internal_headers(user_id=user_id),
    )
    create_response = client.post(
        '/internal/notes/learning-notes',
        headers=_internal_headers(user_id=user_id),
        json={
            'question': 'What is abandon?',
            'answer': 'To leave behind.',
            'word_context': 'abandon',
        },
    )

    assert list_response.status_code == 200
    assert list_response.json()['notes'][0]['word_context'] == 'vivid'
    assert create_response.status_code == 201
    assert create_response.json()['note']['word_context'] == 'abandon'
    with module.notes_flask_app.app_context():
        assert UserLearningNote.query.filter_by(user_id=user_id).count() == 2


def test_catalog_content_internal_custom_book_routes_accept_internal_service_user(monkeypatch, tmp_path):
    _configure_env(monkeypatch, tmp_path, 'catalog-content-internal-routes')
    module = _load_module('catalog_content_service_internal_routes', CATALOG_CONTENT_SERVICE_PATH)
    user_id = _create_user(module.catalog_content_flask_app, 'catalog-content-internal-user')
    client = TestClient(module.app)
    headers = _internal_headers(user_id=user_id)

    create_response = client.post(
        '/internal/catalog/custom-books',
        headers=headers,
        json={
            'title': 'Band 7',
            'description': 'desc',
            'education_stage': 'abroad',
            'exam_type': 'ielts',
            'ielts_skill': 'listening',
            'share_enabled': True,
            'chapter_word_target': 30,
            'chapters': [{'id': 'ch1', 'title': 'One', 'wordCount': 1}],
            'words': [{
                'chapterId': 'ch1',
                'word': 'abandon',
                'phonetic': '/əˈbændən/',
                'pos': 'v.',
                'definition': '放弃',
            }],
        },
    )
    created_book_id = create_response.json()['bookId']
    list_response = client.get('/internal/catalog/custom-books', headers=headers)
    get_response = client.get(f'/internal/catalog/custom-books/{created_book_id}', headers=headers)
    public_get_response = client.get(f'/api/books/custom-books/{created_book_id}', headers=headers)
    books_response = client.get('/api/books', headers=headers)
    chapters_response = client.get(f'/api/books/{created_book_id}/chapters', headers=headers)

    assert create_response.status_code == 201
    assert create_response.json()['title'] == 'Band 7'
    assert create_response.json()['book']['education_stage'] == 'abroad'
    assert create_response.json()['book']['exam_type'] == 'ielts'
    assert create_response.json()['book']['ielts_skill'] == 'listening'
    assert create_response.json()['book']['share_enabled'] is True
    assert create_response.json()['book']['chapter_word_target'] == 30
    assert list_response.status_code == 200
    assert list_response.json()['books'][0]['id'] == created_book_id
    assert get_response.status_code == 200
    assert get_response.json()['id'] == created_book_id
    assert public_get_response.status_code == 200
    assert public_get_response.json()['id'] == created_book_id
    assert books_response.status_code == 200
    assert books_response.json()['books'][0]['id'] == created_book_id
    assert chapters_response.status_code == 200
    created_chapter_id = chapters_response.json()['chapters'][0]['id']
    assert created_chapter_id.startswith(f'{created_book_id}_')
    chapter_words_response = client.get(
        f'/api/books/{created_book_id}/chapters/{created_chapter_id}',
        headers=headers,
    )
    assert chapter_words_response.status_code == 200
    assert chapter_words_response.json()['words'][0]['word'] == 'abandon'


def test_admin_ops_accepts_internal_admin_user_without_local_user_row(monkeypatch, tmp_path):
    _configure_env(monkeypatch, tmp_path, 'admin-ops-internal')
    module = _load_module('admin_ops_service_internal_auth', ADMIN_OPS_SERVICE_PATH)
    client = TestClient(module.app)

    response = client.get(
        '/api/admin/overview',
        headers=_internal_headers(user_id=7, is_admin=True),
    )

    assert response.status_code == 200
    assert 'total_users' in response.json()


def test_internal_service_secret_accepts_config_mapping_values():
    assert internal_service_secret(env={'JWT_SECRET_KEY': ' test-jwt '}) == 'test-jwt'
    assert internal_service_secret(env={'JWT_SECRET_KEY': 123456}) == '123456'


def test_internal_service_token_ttl_seconds_accepts_integer_config_values():
    assert internal_service_token_ttl_seconds(env={'INTERNAL_SERVICE_TOKEN_TTL_SECONDS': 120}) == 120
    assert internal_service_token_ttl_seconds(env={'INTERNAL_SERVICE_TOKEN_TTL_SECONDS': 5}) == 10
