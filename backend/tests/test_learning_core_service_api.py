from __future__ import annotations

import importlib.util
import uuid
from datetime import datetime, timedelta
from pathlib import Path

import jwt
from fastapi.testclient import TestClient

from services.books_favorites_service import FAVORITES_BOOK_ID
from models import User, db


SERVICE_PATH = (
    Path(__file__).resolve().parents[2]
    / 'services'
    / 'learning-core-service'
    / 'main.py'
)


def _load_learning_core_service_module(module_name: str):
    spec = importlib.util.spec_from_file_location(module_name, SERVICE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _configure_learning_core_env(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv('SECRET_KEY', 'test-secret')
    monkeypatch.setenv('JWT_SECRET_KEY', 'test-jwt-secret')
    monkeypatch.setenv('COOKIE_SECURE', 'false')
    monkeypatch.setenv('EMAIL_CODE_DELIVERY_MODE', 'mock')
    monkeypatch.setenv('SQLITE_DB_PATH', str(tmp_path / 'learning-core-service.sqlite'))
    monkeypatch.setenv('DB_BACKUP_ENABLED', 'false')


def _create_user_and_token(flask_app, username='learning-core-user') -> str:
    with flask_app.app_context():
        user = User(username=username)
        user.set_password('password123')
        db.session.add(user)
        db.session.commit()
        token = jwt.encode(
            {
                'user_id': user.id,
                'type': 'access',
                'jti': str(uuid.uuid4()),
                'exp': datetime.utcnow() + timedelta(seconds=flask_app.config['JWT_ACCESS_TOKEN_EXPIRES']),
                'iat': datetime.utcnow(),
            },
            flask_app.config['JWT_SECRET_KEY'],
            algorithm='HS256',
        )
    return token


def _auth_headers(token: str) -> dict[str, str]:
    return {'Authorization': f'Bearer {token}'}


def test_learning_core_service_health_endpoint(monkeypatch, tmp_path):
    _configure_learning_core_env(monkeypatch, tmp_path)
    module = _load_learning_core_service_module('learning_core_service_health')
    client = TestClient(module.app)

    response = client.get('/health')

    assert response.status_code == 200
    assert response.json()['service'] == 'learning-core-service'
    assert response.json()['learning_progress_compatibility'] is True


def test_learning_core_service_legacy_progress_round_trip(monkeypatch, tmp_path):
    _configure_learning_core_env(monkeypatch, tmp_path)
    module = _load_learning_core_service_module('learning_core_service_progress')
    client = TestClient(module.app)
    token = _create_user_and_token(module.learning_core_flask_app, username='legacy-core-user')

    save_response = client.post(
        '/api/progress',
        json={'day': 4, 'current_index': 18, 'correct_count': 15, 'wrong_count': 3},
        headers=_auth_headers(token),
    )
    day_response = client.get('/api/progress/4', headers=_auth_headers(token))

    assert save_response.status_code == 200
    assert save_response.json()['progress']['day'] == 4
    assert day_response.status_code == 200
    assert day_response.json()['progress']['current_index'] == 18


def test_learning_core_service_book_progress_and_mode_round_trip(monkeypatch, tmp_path):
    _configure_learning_core_env(monkeypatch, tmp_path)
    module = _load_learning_core_service_module('learning_core_service_book_progress')
    client = TestClient(module.app)
    token = _create_user_and_token(module.learning_core_flask_app, username='book-core-user')

    save_book = client.post(
        '/api/books/progress',
        json={'book_id': 'ielts_reading_premium', 'current_index': 50, 'correct_count': 40, 'wrong_count': 10},
        headers=_auth_headers(token),
    )
    save_chapter = client.post(
        '/api/books/ielts_reading_premium/chapters/2/progress',
        json={'words_learned': 30, 'correct_count': 22, 'wrong_count': 8, 'is_completed': False},
        headers=_auth_headers(token),
    )
    save_mode = client.post(
        '/api/books/ielts_reading_premium/chapters/2/mode-progress',
        json={'mode': 'meaning', 'correct_count': 6, 'wrong_count': 2, 'is_completed': True},
        headers=_auth_headers(token),
    )
    get_book = client.get('/api/books/progress/ielts_reading_premium', headers=_auth_headers(token))
    get_chapter = client.get('/api/books/ielts_reading_premium/chapters/progress', headers=_auth_headers(token))

    assert save_book.status_code == 200
    assert save_book.json()['progress']['current_index'] == 50
    assert save_chapter.status_code == 200
    assert save_chapter.json()['progress']['words_learned'] == 30
    assert save_mode.status_code == 200
    assert save_mode.json()['mode_progress']['accuracy'] == 75
    assert get_book.status_code == 200
    assert get_book.json()['progress']['current_index'] == 30
    assert get_chapter.status_code == 200
    assert get_chapter.json()['chapter_progress']['2']['modes']['meaning']['accuracy'] == 75


def test_learning_core_service_my_books_round_trip(monkeypatch, tmp_path):
    _configure_learning_core_env(monkeypatch, tmp_path)
    module = _load_learning_core_service_module('learning_core_service_my_books')
    client = TestClient(module.app)
    token = _create_user_and_token(module.learning_core_flask_app, username='library-core-user')

    add_response = client.post(
        '/api/books/my',
        json={'book_id': 'ielts_reading_premium'},
        headers=_auth_headers(token),
    )
    list_response = client.get('/api/books/my', headers=_auth_headers(token))
    remove_response = client.delete('/api/books/my/ielts_reading_premium', headers=_auth_headers(token))

    assert add_response.status_code == 201
    assert add_response.json()['book_id'] == 'ielts_reading_premium'
    assert list_response.status_code == 200
    assert list_response.json()['book_ids'] == ['ielts_reading_premium']
    assert remove_response.status_code == 200
    assert remove_response.json()['message'] == '已移除'


def test_learning_core_service_favorites_and_familiar_round_trip(monkeypatch, tmp_path):
    _configure_learning_core_env(monkeypatch, tmp_path)
    module = _load_learning_core_service_module('learning_core_service_personal_words')
    client = TestClient(module.app)
    token = _create_user_and_token(module.learning_core_flask_app, username='learning-core-words-user')

    favorite_add = client.post(
        '/api/books/favorites',
        json={'word': 'Abandon', 'phonetic': '/əˈbændən/', 'pos': 'v.', 'definition': '放弃'},
        headers=_auth_headers(token),
    )
    favorite_status = client.post(
        '/api/books/favorites/status',
        json={'words': ['abandon', 'beta']},
        headers=_auth_headers(token),
    )
    familiar_add = client.post(
        '/api/books/familiar',
        json={'word': 'Abandon', 'phonetic': '/əˈbændən/', 'pos': 'v.', 'definition': '放弃'},
        headers=_auth_headers(token),
    )
    familiar_status = client.post(
        '/api/books/familiar/status',
        json={'words': ['abandon', 'beta']},
        headers=_auth_headers(token),
    )

    assert favorite_add.status_code == 200
    assert favorite_add.json()['book']['id'] == FAVORITES_BOOK_ID
    assert favorite_status.status_code == 200
    assert favorite_status.json()['words'] == ['abandon']
    assert favorite_status.json()['book_id'] == FAVORITES_BOOK_ID
    assert familiar_add.status_code == 200
    assert familiar_add.json()['created'] is True
    assert familiar_status.status_code == 200
    assert familiar_status.json()['words'] == ['abandon']
