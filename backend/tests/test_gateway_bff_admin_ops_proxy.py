from __future__ import annotations

import importlib.util
from pathlib import Path

from fastapi.testclient import TestClient

import platform_sdk.gateway_browser_routes as browser_routes
from platform_sdk.http_proxy import build_forward_headers
from platform_sdk.internal_service_auth import INTERNAL_SERVICE_AUTH_HEADER
import jwt


GATEWAY_PATH = Path(__file__).resolve().parents[2] / 'apps' / 'gateway-bff' / 'main.py'


def _load_gateway_module():
    spec = importlib.util.spec_from_file_location('gateway_bff_admin_main', GATEWAY_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_gateway_admin_overview_proxy_routes_to_admin_ops_service(monkeypatch):
    module = _load_gateway_module()
    client = TestClient(module.app, base_url='https://axiomaticworld.com')
    captured: dict[str, object] = {}

    async def fake_proxy_browser_request(**kwargs):
        captured.update(kwargs)
        return browser_routes.Response(
            b'{"total_users":3,"total_sessions":1}',
            status_code=200,
            media_type='application/json',
        )

    monkeypatch.setattr(browser_routes, 'proxy_browser_request', fake_proxy_browser_request)

    response = client.get('/api/admin/overview', headers={'Authorization': 'Bearer admin-token'})

    assert response.status_code == 200
    assert response.json()['total_sessions'] == 1
    assert captured['base_url'] == browser_routes.admin_ops_service_url()
    assert captured['path'] == '/api/admin/overview'
    forwarded = build_forward_headers(captured['request'], target_service_name=captured['service_name'])
    assert 'authorization' not in forwarded


def test_gateway_builds_internal_admin_context_headers(monkeypatch):
    monkeypatch.setenv('JWT_SECRET_KEY', 'gateway-admin-secret')
    monkeypatch.setenv('INTERNAL_SERVICE_JWT_SECRET_KEY', 'gateway-admin-secret')
    module = _load_gateway_module()
    client = TestClient(module.app, base_url='https://axiomaticworld.com')
    captured: dict[str, object] = {}

    access_token = jwt.encode(
        {
            'user_id': 1,
            'type': 'access',
            'is_admin': True,
            'username': 'admin',
            'email': 'admin@example.com',
            'scopes': ['admin', 'user'],
        },
        'gateway-admin-secret',
        algorithm='HS256',
    )

    async def fake_proxy_browser_request(**kwargs):
        captured.update(kwargs)
        return browser_routes.Response(
            b'{"total_users":0,"total_sessions":0}',
            status_code=200,
            media_type='application/json',
        )

    monkeypatch.setattr(browser_routes, 'proxy_browser_request', fake_proxy_browser_request)

    response = client.get(
        '/api/admin/overview',
        headers={'Authorization': f'Bearer {access_token}'},
    )

    forwarded = build_forward_headers(captured['request'], target_service_name=captured['service_name'])

    assert response.status_code == 200
    assert INTERNAL_SERVICE_AUTH_HEADER in forwarded
    assert 'authorization' not in forwarded


def test_gateway_word_feedback_proxy_routes_to_admin_ops_service(monkeypatch):
    module = _load_gateway_module()
    client = TestClient(module.app, base_url='https://axiomaticworld.com')
    captured: dict[str, object] = {}

    async def fake_proxy_browser_request(**kwargs):
        captured.update(kwargs)
        return browser_routes.Response(
            b'{"message":"ok"}',
            status_code=201,
            media_type='application/json',
        )

    monkeypatch.setattr(browser_routes, 'proxy_browser_request', fake_proxy_browser_request)

    response = client.post(
        '/api/books/word-feedback',
        headers={'Authorization': 'Bearer learner-token'},
        json={'word': 'quit', 'feedback_types': ['translation']},
    )

    assert response.status_code == 201
    assert response.json()['message'] == 'ok'
    assert captured['base_url'] == browser_routes.admin_ops_service_url()
    assert captured['path'] == '/api/books/word-feedback'
    forwarded = build_forward_headers(captured['request'], target_service_name=captured['service_name'])
    assert 'authorization' not in forwarded
