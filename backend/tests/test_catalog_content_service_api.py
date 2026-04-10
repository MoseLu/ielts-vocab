from __future__ import annotations

import importlib.util
import uuid
from datetime import datetime, timedelta
from pathlib import Path

import jwt
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

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


def _create_learning_core_favorites_db(db_url: str, user_id: int) -> None:
    engine = create_engine(db_url)
    with engine.begin() as connection:
        connection.execute(text("""
            CREATE TABLE user_favorite_words (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                word VARCHAR(160) NOT NULL,
                normalized_word VARCHAR(160) NOT NULL,
                phonetic VARCHAR(100),
                pos VARCHAR(50),
                definition TEXT,
                source_book_id VARCHAR(100),
                source_book_title VARCHAR(200),
                source_chapter_id VARCHAR(100),
                source_chapter_title VARCHAR(200),
                created_at DATETIME,
                updated_at DATETIME
            )
        """))
        connection.execute(text("""
            INSERT INTO user_favorite_words (
                user_id,
                word,
                normalized_word,
                phonetic,
                pos,
                definition,
                source_book_id,
                source_book_title,
                source_chapter_id,
                source_chapter_title,
                created_at,
                updated_at
            )
            VALUES (
                :user_id,
                'Abandon',
                'abandon',
                '/əˈbændən/',
                'v.',
                '放弃',
                'ielts_reading_premium',
                'IELTS Reading Premium',
                '1',
                'Chapter 1',
                '2026-04-10 10:00:00',
                '2026-04-10 10:00:00'
            )
        """), {'user_id': user_id})


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


def test_catalog_content_service_reads_favorites_from_learning_core_database(
    monkeypatch,
    tmp_path,
):
    learning_core_url = 'sqlite:///' + str(tmp_path / 'learning-core-service.sqlite')
    _configure_catalog_env(monkeypatch, tmp_path)
    monkeypatch.setenv('LEARNING_CORE_SERVICE_DATABASE_URL', learning_core_url)
    module = _load_catalog_content_service_module('catalog_content_service_favorites')
    client = TestClient(module.app)
    token = _create_user_and_token(module.catalog_content_flask_app, username='catalog-favorite-user')

    with module.catalog_content_flask_app.app_context():
        user_id = User.query.filter_by(username='catalog-favorite-user').first().id
    _create_learning_core_favorites_db(learning_core_url, user_id)

    books_response = client.get('/api/books', headers=_auth_headers(token))
    chapter_response = client.get(
        '/api/books/ielts_auto_favorites/chapters/1',
        headers=_auth_headers(token),
    )

    assert books_response.status_code == 200
    favorite_book = next(
        book
        for book in books_response.json()['books']
        if book['id'] == 'ielts_auto_favorites'
    )
    assert favorite_book['word_count'] == 1
    assert chapter_response.status_code == 200
    assert chapter_response.json()['words'][0]['word'] == 'Abandon'


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
