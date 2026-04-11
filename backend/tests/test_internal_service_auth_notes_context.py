from __future__ import annotations

import importlib.util
from pathlib import Path

from fastapi.testclient import TestClient
from models import User, UserStudySession, UserWrongWord, db

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


def _internal_headers(*, user_id: int) -> dict[str, str]:
    token = create_internal_service_token(
        secret='test-jwt-secret',
        source_service_name='gateway-bff',
        user_id=user_id,
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


def test_learning_core_notes_context_internal_routes_accept_internal_service_user(monkeypatch, tmp_path):
    _configure_env(monkeypatch, tmp_path, 'learning-core-notes-context')
    module = _load_module('learning_core_service_notes_context_internal', LEARNING_CORE_SERVICE_PATH)
    user_id = _create_user(module.learning_core_flask_app, 'learning-core-notes-context-user')
    client = TestClient(module.app)

    with module.learning_core_flask_app.app_context():
        db.session.add(UserStudySession(
            user_id=user_id,
            mode='meaning',
            book_id='ielts_reading_premium',
            chapter_id='3',
            words_studied=9,
            correct_count=7,
            wrong_count=2,
        ))
        db.session.add(UserWrongWord(
            user_id=user_id,
            word='abandon',
            definition='leave behind',
            wrong_count=3,
        ))
        db.session.commit()

    headers = _internal_headers(user_id=user_id)
    sessions_response = client.get(
        '/internal/learning/notes-context/study-sessions?require_words_studied=true',
        headers=headers,
    )
    wrong_words_response = client.get(
        '/internal/learning/notes-context/wrong-words?limit=5',
        headers=headers,
    )

    assert sessions_response.status_code == 200
    assert sessions_response.json()['sessions'][0]['book_id'] == 'ielts_reading_premium'
    assert sessions_response.json()['sessions'][0]['words_studied'] == 9
    assert wrong_words_response.status_code == 200
    assert wrong_words_response.json()['wrong_words'][0]['word'] == 'abandon'
    assert wrong_words_response.json()['wrong_words'][0]['wrong_count'] == 3
