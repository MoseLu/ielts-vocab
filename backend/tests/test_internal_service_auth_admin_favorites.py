from __future__ import annotations

import importlib.util
from pathlib import Path

from datetime import datetime

from fastapi.testclient import TestClient
from models import User, UserBookProgress, UserChapterProgress, UserFavoriteWord, UserLearningEvent, db

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
        request_id='req-internal-favorites',
        trace_id='trace-internal-favorites',
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


def test_learning_core_internal_admin_favorite_words_route_accepts_internal_service_user(
    monkeypatch,
    tmp_path,
):
    _configure_env(monkeypatch, tmp_path, 'learning-core-internal-admin-favorites')
    module = _load_module('learning_core_service_internal_admin_favorites', LEARNING_CORE_SERVICE_PATH)
    user_id = _create_user(module.learning_core_flask_app, 'learning-core-internal-admin-favorites-user')
    client = TestClient(module.app)

    with module.learning_core_flask_app.app_context():
        db.session.add(UserFavoriteWord(
            user_id=user_id,
            word='delta',
            normalized_word='delta',
            phonetic='/d/',
            pos='n.',
            definition='delta definition',
            source_book_id='ielts_reading_premium',
            source_book_title='IELTS Reading',
            source_chapter_id='5',
            source_chapter_title='Chapter 5',
        ))
        db.session.commit()

    response = client.get(
        '/internal/learning/admin/favorite-words',
        headers=_internal_headers(user_id=user_id),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload['favorite_words'][0]['word'] == 'delta'
    assert payload['favorite_words'][0]['source_book_id'] == 'ielts_reading_premium'


def test_learning_core_internal_admin_detail_routes_accept_internal_service_user(monkeypatch, tmp_path):
    _configure_env(monkeypatch, tmp_path, 'learning-core-internal-admin-detail')
    module = _load_module('learning_core_service_internal_admin_detail', LEARNING_CORE_SERVICE_PATH)
    user_id = _create_user(module.learning_core_flask_app, 'learning-core-internal-admin-detail-user')
    client = TestClient(module.app)

    with module.learning_core_flask_app.app_context():
        db.session.add(UserBookProgress(
            user_id=user_id,
            book_id='ielts_reading_premium',
            current_index=20,
            correct_count=14,
            wrong_count=6,
        ))
        db.session.add(UserChapterProgress(
            user_id=user_id,
            book_id='ielts_reading_premium',
            chapter_id='2',
            words_learned=20,
            correct_count=14,
            wrong_count=6,
        ))
        db.session.add(UserLearningEvent(
            user_id=user_id,
            event_type='quick_memory_review',
            source='quickmemory',
            word='alpha',
            occurred_at=datetime(2026, 4, 11, 20, 0, 0),
        ))
        db.session.commit()

    headers = _internal_headers(user_id=user_id)
    book_progress_response = client.get('/internal/learning/admin/book-progress', headers=headers)
    chapter_progress_response = client.get(
        '/internal/learning/admin/chapter-progress?book_id=ielts_reading_premium&limit=5',
        headers=headers,
    )
    event_response = client.get(
        '/internal/learning/admin/session-word-events?start_at=2026-04-11T19:59:00&end_at=2026-04-11T20:01:00',
        headers=headers,
    )

    assert book_progress_response.status_code == 200
    assert book_progress_response.json()['progress'][0]['book_id'] == 'ielts_reading_premium'
    assert chapter_progress_response.status_code == 200
    assert chapter_progress_response.json()['chapter_progress'][0]['chapter_id'] == 2
    assert event_response.status_code == 200
    assert event_response.json()['events'][0]['word'] == 'alpha'
