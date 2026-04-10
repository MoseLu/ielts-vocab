from __future__ import annotations

import importlib.util
import uuid
from datetime import datetime, timedelta
from pathlib import Path

import jwt
from fastapi.testclient import TestClient

import services.books_catalog_service as books_catalog_service
import services.books_vocabulary_loader_service as books_vocabulary_loader_service
import services.phonetic_lookup_service as phonetic_lookup_service
from models import User, db


SERVICE_PATH = (
    Path(__file__).resolve().parents[2]
    / 'services'
    / 'catalog-content-service'
    / 'main.py'
)


def _load_catalog_content_service_module(module_name: str):
    spec = importlib.util.spec_from_file_location(module_name, SERVICE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _configure_catalog_env(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv('SECRET_KEY', 'test-secret')
    monkeypatch.setenv('JWT_SECRET_KEY', 'test-jwt-secret')
    monkeypatch.setenv('COOKIE_SECURE', 'false')
    monkeypatch.setenv('EMAIL_CODE_DELIVERY_MODE', 'mock')
    monkeypatch.setenv('SQLITE_DB_PATH', str(tmp_path / 'catalog-content-service.sqlite'))
    monkeypatch.setenv('DB_BACKUP_ENABLED', 'false')


def _create_user_and_token(flask_app, username='catalog-user') -> str:
    with flask_app.app_context():
        user = User(username=username, email=f'{username}@example.com')
        user.set_password('password123')
        db.session.add(user)
        db.session.commit()
        token = jwt.encode(
            {
                'user_id': user.id,
                'type': 'access',
                'jti': str(uuid.uuid4()),
                'iat': int(datetime.utcnow().timestamp()),
                'exp': datetime.utcnow() + timedelta(seconds=flask_app.config['JWT_ACCESS_TOKEN_EXPIRES']),
            },
            flask_app.config['JWT_SECRET_KEY'],
            algorithm='HS256',
        )
    return token


def _auth_headers(token: str) -> dict[str, str]:
    return {'Authorization': f'Bearer {token}'}


def test_catalog_content_service_health_endpoint(monkeypatch, tmp_path):
    _configure_catalog_env(monkeypatch, tmp_path)
    module = _load_catalog_content_service_module('catalog_content_service_health')
    client = TestClient(module.app)

    response = client.get('/health')

    assert response.status_code == 200
    assert response.json()['service'] == 'catalog-content-service'
    assert response.json()['catalog_compatibility'] is True


def test_catalog_content_service_lists_books_and_vocabulary_stats(monkeypatch, tmp_path):
    _configure_catalog_env(monkeypatch, tmp_path)
    module = _load_catalog_content_service_module('catalog_content_service_books')
    client = TestClient(module.app)

    books_response = client.get('/api/books')
    vocabulary_response = client.get('/api/vocabulary/stats')

    assert books_response.status_code == 200
    assert len(books_response.json()['books']) > 0
    assert vocabulary_response.status_code == 200
    assert vocabulary_response.json()['days'] == 30


def test_catalog_content_service_word_details(monkeypatch, tmp_path):
    _configure_catalog_env(monkeypatch, tmp_path)
    module = _load_catalog_content_service_module('catalog_content_service_word_details')
    client = TestClient(module.app)

    monkeypatch.setattr(books_catalog_service, '_build_global_word_search_catalog', lambda: [{
        'word': 'quit',
        'phonetic': '/kwɪt/',
        'pos': 'v.',
        'definition': '停止；离开',
        'examples': [{'en': 'He decided to quit last year.', 'zh': '他决定去年辞职。'}],
        'book_id': 'book-a',
        'book_title': 'Book A',
    }])
    monkeypatch.setattr(
        books_vocabulary_loader_service,
        'resolve_unified_examples',
        lambda *_args, **_kwargs: [{'en': 'Quit before the deadline.', 'zh': '在截止前退出。'}],
    )
    monkeypatch.setattr(phonetic_lookup_service, 'lookup_local_phonetic', lambda _word: '/kwɪt/')
    monkeypatch.setattr(
        phonetic_lookup_service,
        'resolve_phonetic',
        lambda _word, allow_remote=True: '/kwɪt/',
    )

    response = client.get('/api/books/word-details?word=quit')

    assert response.status_code == 200
    payload = response.json()
    assert payload['word'] == 'quit'
    assert payload['phonetic'] == '/kwɪt/'
    assert payload['examples'][0]['en'] == 'Quit before the deadline.'
    assert payload['books'][0]['book_id'] == 'book-a'


def test_catalog_content_service_creates_confusable_custom_chapter(monkeypatch, tmp_path):
    _configure_catalog_env(monkeypatch, tmp_path)
    module = _load_catalog_content_service_module('catalog_content_service_confusable')
    client = TestClient(module.app)
    token = _create_user_and_token(module.catalog_content_flask_app, username='catalog-confusable-user')

    create_response = client.post(
        '/api/books/ielts_confusable_match/custom-chapters',
        json={'groups': [['whether', 'weather']]},
        headers=_auth_headers(token),
    )

    assert create_response.status_code == 201
    created = create_response.json()
    assert created['created_count'] == 1

    chapter_id = created['created_chapters'][0]['id']
    detail_response = client.get(
        f'/api/books/ielts_confusable_match/chapters/{chapter_id}',
        headers=_auth_headers(token),
    )

    assert detail_response.status_code == 200
    detail_payload = detail_response.json()
    assert detail_payload['chapter']['is_custom'] is True
    assert {word['word'] for word in detail_payload['words']} == {'whether', 'weather'}
