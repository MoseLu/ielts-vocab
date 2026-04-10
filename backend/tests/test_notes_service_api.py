from __future__ import annotations

import importlib.util
import uuid
from datetime import datetime, timedelta
from pathlib import Path

import jwt
from fastapi.testclient import TestClient

from models import User, UserDailySummary, UserLearningNote, db


SERVICE_PATH = (
    Path(__file__).resolve().parents[2]
    / 'services'
    / 'notes-service'
    / 'main.py'
)


def _load_notes_service_module(module_name: str):
    spec = importlib.util.spec_from_file_location(module_name, SERVICE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _configure_notes_env(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv('SECRET_KEY', 'test-secret')
    monkeypatch.setenv('JWT_SECRET_KEY', 'test-jwt-secret')
    monkeypatch.setenv('COOKIE_SECURE', 'false')
    monkeypatch.setenv('EMAIL_CODE_DELIVERY_MODE', 'mock')
    monkeypatch.setenv('SQLITE_DB_PATH', str(tmp_path / 'notes-service.sqlite'))
    monkeypatch.setenv('DB_BACKUP_ENABLED', 'false')


def _create_user_and_token(flask_app, username='notes-service-user') -> tuple[int, str]:
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
        return user.id, token


def _auth_headers(token: str) -> dict[str, str]:
    return {'Authorization': f'Bearer {token}'}


def test_notes_service_health_endpoint(monkeypatch, tmp_path):
    _configure_notes_env(monkeypatch, tmp_path)
    module = _load_notes_service_module('notes_service_health')
    client = TestClient(module.app)

    response = client.get('/health')

    assert response.status_code == 200
    assert response.json()['service'] == 'notes-service'
    assert response.json()['notes_compatibility'] is True


def test_notes_service_lists_notes(monkeypatch, tmp_path):
    _configure_notes_env(monkeypatch, tmp_path)
    module = _load_notes_service_module('notes_service_list')
    client = TestClient(module.app)
    user_id, token = _create_user_and_token(module.notes_flask_app, username='notes-list-user')

    with module.notes_flask_app.app_context():
        db.session.add(UserLearningNote(
            user_id=user_id,
            question='What is abandon?',
            answer='To leave behind.',
            word_context='abandon',
        ))
        db.session.commit()

    response = client.get('/api/notes', headers=_auth_headers(token))

    assert response.status_code == 200
    assert response.json()['total'] == 1
    assert response.json()['notes'][0]['word_context'] == 'abandon'


def test_notes_service_generates_summary(monkeypatch, tmp_path):
    _configure_notes_env(monkeypatch, tmp_path)
    module = _load_notes_service_module('notes_service_generate')
    client = TestClient(module.app)
    _user_id, token = _create_user_and_token(module.notes_flask_app, username='notes-generate-user')

    monkeypatch.setattr(
        'platform_sdk.notes_summary_jobs_application.chat',
        lambda *args, **kwargs: {'text': '# generated summary'},
    )

    response = client.post(
        '/api/notes/summaries/generate',
        json={'date': '2026-03-30'},
        headers=_auth_headers(token),
    )

    assert response.status_code == 200
    assert response.json()['summary']['content'] == '# generated summary'


def test_notes_service_exports_notes_and_summaries(monkeypatch, tmp_path):
    _configure_notes_env(monkeypatch, tmp_path)
    module = _load_notes_service_module('notes_service_export')
    client = TestClient(module.app)
    user_id, token = _create_user_and_token(module.notes_flask_app, username='notes-export-user')

    with module.notes_flask_app.app_context():
        db.session.add(UserDailySummary(
            user_id=user_id,
            date='2026-03-30',
            content='# summary body',
            generated_at=datetime.utcnow(),
        ))
        db.session.add(UserLearningNote(
            user_id=user_id,
            question='What is vivid?',
            answer='Bright or clear.',
            word_context='vivid',
            created_at=datetime(2026, 3, 30, 8, 0, 0),
        ))
        db.session.commit()

    response = client.get(
        '/api/notes/export?start_date=2026-03-30&end_date=2026-03-30',
        headers=_auth_headers(token),
    )

    assert response.status_code == 200
    assert response.json()['filename'] == 'ielts_notes_2026-03-30_2026-03-30.md'
    assert '# 每日学习总结' in response.json()['content']
    assert 'What is vivid?' in response.json()['content']


def test_notes_service_export_returns_oss_reference_when_configured(monkeypatch, tmp_path):
    _configure_notes_env(monkeypatch, tmp_path)
    module = _load_notes_service_module('notes_service_export_oss')
    client = TestClient(module.app)
    user_id, token = _create_user_and_token(module.notes_flask_app, username='notes-export-oss-user')

    with module.notes_flask_app.app_context():
        db.session.add(UserDailySummary(
            user_id=user_id,
            date='2026-03-30',
            content='# summary body',
            generated_at=datetime.utcnow(),
        ))
        db.session.commit()

    monkeypatch.setattr(
        'platform_sdk.notes_query_application.store_notes_export',
        lambda **kwargs: {
            'provider': 'aliyun-oss',
            'bucket_name': 'bucket',
            'object_key': 'exports/notes-service/user-1/ielts_notes_2026-03-30_2026-03-30.md',
            'byte_length': 123,
            'cache_key': 'oss:ielts_notes.md:123:etag-1',
            'signed_url': 'https://oss.example.com/notes-export.md?signature=1',
            'signed_url_expires_at': '2026-04-10T16:00:00+00:00',
        },
    )

    response = client.get(
        '/api/notes/export?start_date=2026-03-30&end_date=2026-03-30',
        headers=_auth_headers(token),
    )

    assert response.status_code == 200
    assert response.json()['provider'] == 'aliyun-oss'
    assert response.json()['bucket_name'] == 'bucket'
    assert response.json()['object_key'] == 'exports/notes-service/user-1/ielts_notes_2026-03-30_2026-03-30.md'
    assert response.json()['signed_url'] == 'https://oss.example.com/notes-export.md?signature=1'


def test_notes_service_saves_word_detail_note(monkeypatch, tmp_path):
    _configure_notes_env(monkeypatch, tmp_path)
    module = _load_notes_service_module('notes_service_word_note')
    client = TestClient(module.app)
    _user_id, token = _create_user_and_token(module.notes_flask_app, username='notes-word-note-user')

    response = client.put(
        '/api/books/word-details/note',
        json={'word': 'quit', 'content': '记住 quit 和 quiet 的区别'},
        headers=_auth_headers(token),
    )

    assert response.status_code == 200
    assert response.json()['note']['content'] == '记住 quit 和 quiet 的区别'
