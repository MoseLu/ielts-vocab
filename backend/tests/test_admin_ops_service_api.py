from __future__ import annotations

import importlib.util
import uuid
from datetime import datetime, timedelta
from pathlib import Path

import jwt
from fastapi.testclient import TestClient

from models import User, UserStudySession, db


SERVICE_PATH = (
    Path(__file__).resolve().parents[2]
    / 'services'
    / 'admin-ops-service'
    / 'main.py'
)


def _load_admin_ops_service_module(module_name: str):
    spec = importlib.util.spec_from_file_location(module_name, SERVICE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _configure_admin_env(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv('SECRET_KEY', 'test-secret')
    monkeypatch.setenv('JWT_SECRET_KEY', 'test-jwt-secret')
    monkeypatch.setenv('COOKIE_SECURE', 'false')
    monkeypatch.setenv('EMAIL_CODE_DELIVERY_MODE', 'mock')
    monkeypatch.setenv('SQLITE_DB_PATH', str(tmp_path / 'admin-ops-service.sqlite'))
    monkeypatch.setenv('DB_BACKUP_ENABLED', 'false')


def _create_admin_token(flask_app, username='admin-ops-admin') -> tuple[int, str]:
    with flask_app.app_context():
        admin = User(username=username, email=f'{username}@example.com', is_admin=True)
        admin.set_password('password123')
        learner = User(username='admin-ops-learner', email='learner@example.com')
        learner.set_password('password123')
        db.session.add_all([admin, learner])
        db.session.flush()
        learner_id = learner.id
        db.session.add(UserStudySession(
            user_id=learner_id,
            mode='listening',
            book_id='ielts_listening_premium',
            chapter_id='2',
            words_studied=10,
            correct_count=7,
            wrong_count=3,
            duration_seconds=600,
            started_at=datetime.utcnow() - timedelta(minutes=10),
            ended_at=datetime.utcnow(),
        ))
        db.session.commit()
        token = jwt.encode(
            {
                'user_id': admin.id,
                'type': 'access',
                'jti': str(uuid.uuid4()),
                'iat': int(datetime.utcnow().timestamp()),
                'exp': datetime.utcnow() + timedelta(seconds=flask_app.config['JWT_ACCESS_TOKEN_EXPIRES']),
            },
            flask_app.config['JWT_SECRET_KEY'],
            algorithm='HS256',
        )
    return learner_id, token


def _create_access_token(flask_app, *, user_id: int, is_admin: bool, username: str, email: str) -> str:
    return jwt.encode(
        {
            'user_id': user_id,
            'type': 'access',
            'is_admin': is_admin,
            'username': username,
            'email': email,
            'jti': str(uuid.uuid4()),
            'iat': int(datetime.utcnow().timestamp()),
            'exp': datetime.utcnow() + timedelta(seconds=flask_app.config['JWT_ACCESS_TOKEN_EXPIRES']),
        },
        flask_app.config['JWT_SECRET_KEY'],
        algorithm='HS256',
    )


def _auth_headers(token: str) -> dict[str, str]:
    return {'Authorization': f'Bearer {token}'}


def test_admin_ops_service_health_endpoint(monkeypatch, tmp_path):
    _configure_admin_env(monkeypatch, tmp_path)
    module = _load_admin_ops_service_module('admin_ops_service_health')
    client = TestClient(module.app)

    response = client.get('/health')

    assert response.status_code == 200
    assert response.json()['service'] == 'admin-ops-service'
    assert response.json()['admin_compatibility'] is True


def test_admin_ops_service_overview_and_detail(monkeypatch, tmp_path):
    _configure_admin_env(monkeypatch, tmp_path)
    monkeypatch.setenv('ALLOW_LEGACY_CROSS_SERVICE_FALLBACK', 'true')
    module = _load_admin_ops_service_module('admin_ops_service_routes')
    client = TestClient(module.app)
    learner_id, token = _create_admin_token(module.admin_ops_flask_app)

    overview_response = client.get('/api/admin/overview', headers=_auth_headers(token))
    detail_response = client.get(f'/api/admin/users/{learner_id}', headers=_auth_headers(token))

    assert overview_response.status_code == 200
    assert overview_response.json()['total_sessions'] == 1
    assert detail_response.status_code == 200
    assert detail_response.json()['user']['id'] == learner_id


def test_admin_ops_service_submits_and_lists_word_feedback(monkeypatch, tmp_path):
    _configure_admin_env(monkeypatch, tmp_path)
    module = _load_admin_ops_service_module('admin_ops_service_feedback_routes')
    client = TestClient(module.app)
    learner_id, admin_token = _create_admin_token(module.admin_ops_flask_app)
    learner_token = _create_access_token(
        module.admin_ops_flask_app,
        user_id=learner_id,
        is_admin=False,
        username='admin-ops-learner',
        email='learner@example.com',
    )

    submit_response = client.post(
        '/api/books/word-feedback',
        headers=_auth_headers(learner_token),
        json={
            'word': 'quit',
            'phonetic': '/kwɪt/',
            'pos': 'v.',
            'definition': '停止；离开',
            'book_id': 'ielts_listening_premium',
            'book_title': '雅思听力高频词汇',
            'chapter_id': '2',
            'chapter_title': '第2章',
            'example_en': 'He decided to quit last year.',
            'example_zh': '他去年决定辞职。',
            'feedback_types': ['translation', 'audio_pronunciation'],
            'source': 'global_search',
        },
    )
    list_response = client.get('/api/admin/word-feedback?limit=50', headers=_auth_headers(admin_token))

    assert submit_response.status_code == 201
    assert submit_response.json()['feedback']['word'] == 'quit'
    assert submit_response.json()['feedback']['feedback_types'] == ['translation', 'audio_pronunciation']
    assert list_response.status_code == 200
    assert list_response.json()['total'] == 1
    assert list_response.json()['items'][0]['username'] == 'admin-ops-learner'
    assert list_response.json()['items'][0]['feedback_type_labels'] == ['翻译不准', '音频发音问题']
