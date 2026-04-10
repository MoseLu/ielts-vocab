from __future__ import annotations

import importlib.util
import json
import uuid
from datetime import datetime, timedelta
from pathlib import Path

import jwt
from fastapi.testclient import TestClient

from models import User, db
import platform_sdk.ai_assistant_application as ai_assistant_application
import platform_sdk.ai_custom_books_application as ai_custom_books_application
import platform_sdk.ai_similarity_application as ai_similarity_application


SERVICE_PATH = (
    Path(__file__).resolve().parents[2]
    / 'services'
    / 'ai-execution-service'
    / 'main.py'
)


def _load_ai_execution_service_module(module_name: str):
    spec = importlib.util.spec_from_file_location(module_name, SERVICE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _configure_ai_env(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv('SECRET_KEY', 'test-secret')
    monkeypatch.setenv('JWT_SECRET_KEY', 'test-jwt-secret')
    monkeypatch.setenv('COOKIE_SECURE', 'false')
    monkeypatch.setenv('EMAIL_CODE_DELIVERY_MODE', 'mock')
    monkeypatch.setenv('SQLITE_DB_PATH', str(tmp_path / 'ai-execution-service.sqlite'))
    monkeypatch.setenv('DB_BACKUP_ENABLED', 'false')


def _create_user_and_token(flask_app, username='ai-execution-user') -> str:
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


def test_ai_execution_service_health_endpoint(monkeypatch, tmp_path):
    _configure_ai_env(monkeypatch, tmp_path)
    module = _load_ai_execution_service_module('ai_execution_service_health')
    client = TestClient(module.app)

    response = client.get('/health')

    assert response.status_code == 200
    assert response.json()['service'] == 'ai-execution-service'
    assert response.json()['ai_compatibility'] is True


def test_ai_execution_service_context_route(monkeypatch, tmp_path):
    _configure_ai_env(monkeypatch, tmp_path)
    module = _load_ai_execution_service_module('ai_execution_service_context')
    client = TestClient(module.app)
    token = _create_user_and_token(module.ai_flask_app, username='ai-context-runtime-user')

    response = client.get('/api/ai/context', headers=_auth_headers(token))

    assert response.status_code == 200
    data = response.json()
    assert 'books' in data
    assert 'totalLearned' in data


def test_ai_execution_service_ask_route(monkeypatch, tmp_path):
    _configure_ai_env(monkeypatch, tmp_path)
    module = _load_ai_execution_service_module('ai_execution_service_ask')
    client = TestClient(module.app)
    token = _create_user_and_token(module.ai_flask_app, username='ai-ask-runtime-user')

    persisted = {}
    monkeypatch.setattr(
        ai_assistant_application,
        'build_ask_messages',
        lambda *args, **kwargs: [{'role': 'system', 'content': 'test'}],
    )
    monkeypatch.setattr(ai_assistant_application, 'build_ask_extra_handlers', lambda *args, **kwargs: {})
    monkeypatch.setattr(
        ai_assistant_application,
        'persist_ask_response',
        lambda current_user, user_message, frontend_context, clean_reply: persisted.update({
            'message': user_message,
            'reply': clean_reply,
        }),
    )
    monkeypatch.setattr(
        ai_assistant_application,
        'chat_with_tools',
        lambda *args, **kwargs: {'text': '先复习今天到期的错词。'},
    )

    response = client.post(
        '/api/ai/ask',
        json={'message': '今天怎么复习？', 'context': {'currentWord': 'kind'}},
        headers=_auth_headers(token),
    )

    assert response.status_code == 200
    assert response.json()['reply'] == '先复习今天到期的错词。'
    assert persisted == {
        'message': '今天怎么复习？',
        'reply': '先复习今天到期的错词。',
    }


def test_ai_execution_service_ask_stream_route(monkeypatch, tmp_path):
    _configure_ai_env(monkeypatch, tmp_path)
    module = _load_ai_execution_service_module('ai_execution_service_stream')
    client = TestClient(module.app)
    token = _create_user_and_token(module.ai_flask_app, username='ai-stream-runtime-user')

    monkeypatch.setattr(
        'platform_sdk.ai_assistant_application.build_ask_messages',
        lambda *args, **kwargs: [{'role': 'system', 'content': 'test'}],
    )
    monkeypatch.setattr(
        'platform_sdk.ai_assistant_application.build_ask_extra_handlers',
        lambda *args, **kwargs: {},
    )
    monkeypatch.setattr(
        'platform_sdk.ai_assistant_application.persist_ask_response',
        lambda *args, **kwargs: None,
    )

    def fake_stream(*args, **kwargs):
        yield {'type': 'text_delta', 'text': '先复习错词。'}

    monkeypatch.setattr('platform_sdk.ai_assistant_application.stream_chat_with_tools', fake_stream)

    response = client.post(
        '/api/ai/ask/stream',
        json={'message': '今天怎么复习？', 'context': {'currentWord': 'kind'}},
        headers=_auth_headers(token),
    )

    assert response.status_code == 200
    assert response.headers['content-type'].startswith('text/event-stream')
    assert '"type": "text"' in response.text
    assert '"type": "done"' in response.text


def test_ai_execution_service_generate_book_route(monkeypatch, tmp_path):
    _configure_ai_env(monkeypatch, tmp_path)
    module = _load_ai_execution_service_module('ai_execution_service_generate_book')
    client = TestClient(module.app)
    token = _create_user_and_token(module.ai_flask_app, username='ai-generate-book-runtime-user')

    payload = {
        'title': '学术高频词',
        'description': '聚焦常见学术场景',
        'chapters': [{'id': 'ch1', 'title': '校园', 'wordCount': 1}],
        'words': [{
            'chapterId': 'ch1',
            'word': 'lecture',
            'phonetic': '/ˈlektʃə/',
            'pos': 'n.',
            'definition': '讲座',
        }],
    }
    monkeypatch.setattr(
        ai_custom_books_application,
        'chat',
        lambda messages, max_tokens=8192: {'type': 'text', 'text': json.dumps(payload, ensure_ascii=False)},
    )

    response = client.post(
        '/api/ai/generate-book',
        json={'targetWords': 20, 'userLevel': 'intermediate', 'focusAreas': ['academic']},
        headers=_auth_headers(token),
    )

    assert response.status_code == 200
    data = response.json()
    assert data['title'] == '学术高频词'
    assert len(data['chapters']) == 1
    assert len(data['words']) == 1


def test_ai_execution_service_quick_memory_sync_round_trip(monkeypatch, tmp_path):
    _configure_ai_env(monkeypatch, tmp_path)
    module = _load_ai_execution_service_module('ai_execution_service_quick_memory')
    client = TestClient(module.app)
    token = _create_user_and_token(module.ai_flask_app, username='ai-quick-memory-runtime-user')

    sync_response = client.post(
        '/api/ai/quick-memory/sync',
        json={
            'source': 'split-test',
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
        headers=_auth_headers(token),
    )
    get_response = client.get('/api/ai/quick-memory', headers=_auth_headers(token))

    assert sync_response.status_code == 200
    assert sync_response.json()['ok'] is True
    assert get_response.status_code == 200
    assert get_response.json()['records'][0]['word'] == 'kind'


def test_ai_execution_service_wrong_words_sync_round_trip(monkeypatch, tmp_path):
    _configure_ai_env(monkeypatch, tmp_path)
    module = _load_ai_execution_service_module('ai_execution_service_wrong_words')
    client = TestClient(module.app)
    token = _create_user_and_token(module.ai_flask_app, username='ai-wrong-words-runtime-user')

    sync_response = client.post(
        '/api/ai/wrong-words/sync',
        json={
            'sourceMode': 'smart',
            'words': [{
                'word': 'abandon',
                'definition': '放弃',
                'wrongCount': 2,
                'recognitionWrong': 2,
            }],
        },
        headers=_auth_headers(token),
    )
    get_response = client.get(
        '/api/ai/wrong-words?details=compact',
        headers=_auth_headers(token),
    )

    assert sync_response.status_code == 200
    assert sync_response.json()['updated'] == 1
    assert get_response.status_code == 200
    assert get_response.json()['words'][0]['word'] == 'abandon'


def test_ai_execution_service_similar_words_route(monkeypatch, tmp_path):
    _configure_ai_env(monkeypatch, tmp_path)
    module = _load_ai_execution_service_module('ai_execution_service_similar_words')
    client = TestClient(module.app)
    token = _create_user_and_token(module.ai_flask_app, username='ai-similar-runtime-user')

    monkeypatch.setattr(ai_similarity_application, 'get_global_vocab_pool', lambda: [
        {
            'word': 'adapt',
            'phonetic': '/əˈdæpt/',
            'pos': 'v.',
            'definition': '适应',
            'group_key': 'adapt-group',
        },
        {
            'word': 'adopt',
            'phonetic': '/əˈdɒpt/',
            'pos': 'v.',
            'definition': '采用',
            'group_key': 'adopt-group',
        },
    ])
    monkeypatch.setattr(
        ai_similarity_application,
        'list_preset_listening_confusables',
        lambda _word, limit=20: [],
    )

    response = client.get(
        '/api/ai/similar-words',
        params={'word': 'adapt', 'phonetic': '/əˈdæpt/', 'pos': 'v.', 'n': 5},
        headers=_auth_headers(token),
    )

    assert response.status_code == 200
    assert response.json()['words'][0]['word'] == 'adopt'
