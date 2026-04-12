from __future__ import annotations

import importlib.util
from pathlib import Path

from fastapi.testclient import TestClient

import platform_sdk.gateway_browser_routes as browser_routes
from platform_sdk.http_proxy import build_forward_headers
from platform_sdk.internal_service_auth import (
    INTERNAL_SERVICE_AUTH_HEADER,
    REQUEST_ID_HEADER,
    SERVICE_NAME_HEADER,
)
import jwt


GATEWAY_PATH = Path(__file__).resolve().parents[2] / 'apps' / 'gateway-bff' / 'main.py'


def _load_gateway_module():
    spec = importlib.util.spec_from_file_location('gateway_bff_learning_core_main', GATEWAY_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_gateway_progress_proxy_uses_learning_core_service(monkeypatch):
    module = _load_gateway_module()
    client = TestClient(module.app, base_url='https://axiomaticworld.com')
    captured: dict[str, object] = {}

    async def fake_proxy_browser_request(**kwargs):
        captured.update(kwargs)
        return browser_routes.Response(
            b'{"message":"Progress saved","progress":{"day":3,"current_index":18}}',
            status_code=200,
            media_type='application/json',
        )

    monkeypatch.setattr(browser_routes, 'proxy_browser_request', fake_proxy_browser_request)

    response = client.post(
        '/api/progress',
        json={'day': 3, 'current_index': 18},
        headers={'Authorization': 'Bearer learning-token'},
    )

    assert response.status_code == 200
    assert response.json()['progress']['day'] == 3
    assert captured['base_url'] == browser_routes.learning_core_service_url()
    assert captured['path'] == '/api/progress'
    forwarded = build_forward_headers(captured['request'], target_service_name=captured['service_name'])
    assert 'authorization' not in forwarded


def test_gateway_my_books_delete_proxy_routes_to_learning_core(monkeypatch):
    module = _load_gateway_module()
    client = TestClient(module.app, base_url='https://axiomaticworld.com')
    captured: dict[str, object] = {}

    async def fake_proxy_browser_request(**kwargs):
        captured.update(kwargs)
        return browser_routes.Response(
            b'{"message":"\\u5df2\\u79fb\\u9664"}',
            status_code=200,
            media_type='application/json',
        )

    monkeypatch.setattr(browser_routes, 'proxy_browser_request', fake_proxy_browser_request)

    response = client.delete(
        '/api/books/my/ielts_reading_premium',
        headers={'Cookie': 'access_token=abc'},
    )

    assert response.status_code == 200
    assert response.json() == {'message': '已移除'}
    assert captured['path'] == '/api/books/my/ielts_reading_premium'
    forwarded = build_forward_headers(captured['request'], target_service_name=captured['service_name'])
    assert 'cookie' not in forwarded


def test_gateway_favorites_proxy_routes_to_learning_core(monkeypatch):
    module = _load_gateway_module()
    client = TestClient(module.app, base_url='https://axiomaticworld.com')
    captured: dict[str, object] = {}

    async def fake_proxy_browser_request(**kwargs):
        captured.update(kwargs)
        return browser_routes.Response(
            b'{"words":["abandon"],"book_id":"favorites"}',
            status_code=200,
            media_type='application/json',
        )

    monkeypatch.setattr(browser_routes, 'proxy_browser_request', fake_proxy_browser_request)

    response = client.post(
        '/api/books/favorites/status',
        json={'words': ['abandon']},
        headers={'Authorization': 'Bearer favorite-token'},
    )

    assert response.status_code == 200
    assert response.json()['book_id'] == 'favorites'
    assert captured['path'] == '/api/books/favorites/status'
    forwarded = build_forward_headers(captured['request'], target_service_name=captured['service_name'])
    assert 'authorization' not in forwarded


def test_gateway_builds_internal_auth_headers_for_valid_browser_access_token(monkeypatch):
    monkeypatch.setenv('JWT_SECRET_KEY', 'gateway-test-secret')
    monkeypatch.setenv('INTERNAL_SERVICE_JWT_SECRET_KEY', 'gateway-test-secret')
    module = _load_gateway_module()
    client = TestClient(module.app, base_url='https://axiomaticworld.com')
    captured: dict[str, object] = {}

    access_token = jwt.encode(
        {
            'user_id': 12,
            'type': 'access',
            'is_admin': False,
            'username': 'gateway-user',
            'email': 'gateway@example.com',
            'scopes': ['user'],
        },
        'gateway-test-secret',
        algorithm='HS256',
    )

    async def fake_proxy_browser_request(**kwargs):
        captured.update(kwargs)
        return browser_routes.Response(
            b'{"progress":[]}',
            status_code=200,
            media_type='application/json',
        )

    monkeypatch.setattr(browser_routes, 'proxy_browser_request', fake_proxy_browser_request)

    response = client.get(
        '/api/books/progress',
        headers={'Authorization': f'Bearer {access_token}'},
    )

    forwarded = build_forward_headers(captured['request'], target_service_name=captured['service_name'])

    assert response.status_code == 200
    assert 'authorization' not in forwarded
    assert forwarded[SERVICE_NAME_HEADER] == 'gateway-bff'
    assert forwarded[REQUEST_ID_HEADER]
    assert INTERNAL_SERVICE_AUTH_HEADER in forwarded
