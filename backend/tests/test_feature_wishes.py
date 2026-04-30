from __future__ import annotations

import importlib.util
import base64
import uuid
from datetime import datetime, timedelta
from pathlib import Path

import jwt
from fastapi.testclient import TestClient

from models import User, db
from platform_sdk.internal_service_auth import create_internal_auth_headers_for_user


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
    database_path = tmp_path / 'feature-wishes.sqlite'
    database_uri = f'sqlite:///{database_path.as_posix()}'
    monkeypatch.setenv('SECRET_KEY', 'test-secret')
    monkeypatch.setenv('JWT_SECRET_KEY', 'test-jwt-secret')
    monkeypatch.setenv('COOKIE_SECURE', 'false')
    monkeypatch.setenv('EMAIL_CODE_DELIVERY_MODE', 'mock')
    monkeypatch.setenv('SQLITE_DB_PATH', str(database_path))
    monkeypatch.setenv('SQLALCHEMY_DATABASE_URI', database_uri)
    monkeypatch.setenv('ADMIN_OPS_SERVICE_SQLITE_DB_PATH', str(database_path))
    monkeypatch.setenv('ADMIN_OPS_SERVICE_SQLALCHEMY_DATABASE_URI', database_uri)
    monkeypatch.setenv('DB_BACKUP_ENABLED', 'false')
    monkeypatch.setenv('CURRENT_SERVICE_NAME', 'admin-ops-service')


def _seed_users(flask_app):
    with flask_app.app_context():
        db.create_all()
        admin = User(username='wish-admin', email='admin@example.com', is_admin=True)
        admin.set_password('password123')
        learner = User(username='wish-learner', email='learner@example.com')
        learner.set_password('password123')
        other = User(username='wish-other', email='other@example.com')
        other.set_password('password123')
        db.session.add_all([admin, learner, other])
        db.session.commit()
        return {
            'admin': admin.to_dict(),
            'learner': learner.to_dict(),
            'other': other.to_dict(),
        }


def _access_token(flask_app, user: dict) -> str:
    return jwt.encode(
        {
            'user_id': user['id'],
            'type': 'access',
            'is_admin': bool(user['is_admin']),
            'username': user['username'],
            'email': user['email'],
            'jti': str(uuid.uuid4()),
            'iat': int(datetime.utcnow().timestamp()),
            'exp': datetime.utcnow() + timedelta(seconds=flask_app.config['JWT_ACCESS_TOKEN_EXPIRES']),
        },
        flask_app.config['JWT_SECRET_KEY'],
        algorithm='HS256',
    )


def _auth_headers(token: str) -> dict[str, str]:
    payload = jwt.decode(token, options={'verify_signature': False})
    return create_internal_auth_headers_for_user(
        user_id=int(payload['user_id']),
        source_service_name='gateway-bff',
        is_admin=bool(payload.get('is_admin')),
        username=str(payload.get('username') or ''),
        email=str(payload.get('email') or ''),
        env={'INTERNAL_SERVICE_JWT_SECRET_KEY': 'test-jwt-secret'},
    )


def _png_bytes() -> bytes:
    return base64.b64decode(
        'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8'
        '/x8AAwMCAO+/p9sAAAAASUVORK5CYII='
    )


def test_feature_wish_visibility_search_and_owner_edit(monkeypatch, tmp_path):
    _configure_admin_env(monkeypatch, tmp_path)
    module = _load_admin_ops_service_module('admin_ops_service_feature_wishes')
    client = TestClient(module.app)
    users = _seed_users(module.admin_ops_flask_app)
    learner_headers = _auth_headers(_access_token(module.admin_ops_flask_app, users['learner']))
    other_headers = _auth_headers(_access_token(module.admin_ops_flask_app, users['other']))
    admin_headers = _auth_headers(_access_token(module.admin_ops_flask_app, users['admin']))

    learner_create = client.post(
        '/api/feature-wishes',
        headers=learner_headers,
        json={'title': '错题清单自动整理', 'content': '练习结束后生成错词复盘清单'},
    )
    other_create = client.post(
        '/api/feature-wishes',
        headers=other_headers,
        json={'title': '口语主题筛选', 'content': '按口语场景筛选词汇'},
    )

    assert learner_create.status_code == 201
    assert other_create.status_code == 201

    learner_list = client.get('/api/feature-wishes', headers=learner_headers)
    admin_list = client.get('/api/feature-wishes', headers=admin_headers)
    search_list = client.get('/api/feature-wishes?search=错题', headers=admin_headers)
    blocked_edit = client.put(
        f"/api/feature-wishes/{learner_create.json()['wish']['id']}",
        headers=admin_headers,
        json={'title': '管理员不能改别人的愿望', 'content': '即使是管理员也不行'},
    )
    owner_edit = client.put(
        f"/api/feature-wishes/{learner_create.json()['wish']['id']}",
        headers=learner_headers,
        json={'title': '错题清单自动整理增强版', 'content': '加入下一次复习建议'},
    )

    assert learner_list.status_code == 200
    assert [item['title'] for item in learner_list.json()['items']] == ['错题清单自动整理']
    assert admin_list.status_code == 200
    assert admin_list.json()['total'] == 2
    assert search_list.status_code == 200
    assert [item['title'] for item in search_list.json()['items']] == ['错题清单自动整理']
    assert blocked_edit.status_code == 403
    assert owner_edit.status_code == 200
    assert owner_edit.json()['wish']['title'] == '错题清单自动整理增强版'


def test_feature_wish_image_upload_creates_resized_oss_variants(monkeypatch, tmp_path):
    _configure_admin_env(monkeypatch, tmp_path)
    module = _load_admin_ops_service_module('admin_ops_service_feature_wish_images')
    client = TestClient(module.app)
    users = _seed_users(module.admin_ops_flask_app)
    learner_headers = _auth_headers(_access_token(module.admin_ops_flask_app, users['learner']))
    uploaded: list[tuple[str, str, int]] = []

    def fake_put_object_bytes(*, object_key, body, content_type, **kwargs):
        uploaded.append((object_key, content_type, len(body)))
        return type('Stored', (), {
            'provider': 'aliyun-oss',
            'bucket_name': 'test-bucket',
            'object_key': object_key,
            'byte_length': len(body),
            'content_type': content_type,
            'cache_key': f'oss:{object_key}',
            'signed_url': f'https://oss.example.com/{object_key}?signature=1',
        })()

    monkeypatch.setattr(
        'platform_sdk.feature_wish_image_storage.put_object_bytes',
        fake_put_object_bytes,
    )

    response = client.post(
        '/api/feature-wishes',
        headers=learner_headers,
        data={'title': '图片许愿', 'content': '上传三张以内参考图'},
        files=[
            ('images', ('wish.png', _png_bytes(), 'image/png')),
            ('images', ('wish-2.png', _png_bytes(), 'image/png')),
        ],
    )
    too_many = client.post(
        '/api/feature-wishes',
        headers=learner_headers,
        data={'title': '太多图片', 'content': '这条应该失败'},
        files=[('images', (f'wish-{idx}.png', _png_bytes(), 'image/png')) for idx in range(4)],
    )

    assert response.status_code == 201
    wish = response.json()['wish']
    assert len(wish['images']) == 2
    assert wish['images'][0]['thumbnail_url'].startswith('https://oss.example.com/')
    assert wish['images'][0]['full_url'].startswith('https://oss.example.com/')
    assert any('/thumb-' in item[0] for item in uploaded)
    assert any('/full-' in item[0] for item in uploaded)
    assert too_many.status_code == 400
