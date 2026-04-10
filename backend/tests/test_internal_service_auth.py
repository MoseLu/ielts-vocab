from __future__ import annotations

import importlib.util
from pathlib import Path

from fastapi.testclient import TestClient
from models import User, UserLearningEvent, UserLearningNote, db

from platform_sdk.internal_service_auth import (
    INTERNAL_SERVICE_AUTH_HEADER,
    SERVICE_NAME_HEADER,
    create_internal_service_token,
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
