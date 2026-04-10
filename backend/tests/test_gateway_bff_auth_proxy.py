from __future__ import annotations

import importlib.util
import json
from pathlib import Path

from fastapi.testclient import TestClient

import platform_sdk.gateway_browser_routes as browser_routes
from platform_sdk.http_proxy import build_forward_headers


GATEWAY_PATH = Path(__file__).resolve().parents[2] / 'apps' / 'gateway-bff' / 'main.py'


def _load_gateway_module():
    spec = importlib.util.spec_from_file_location('gateway_bff_auth_main', GATEWAY_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_gateway_auth_proxy_preserves_json_and_set_cookie_headers(monkeypatch):
    module = _load_gateway_module()
    client = TestClient(module.app, base_url='https://axiomaticworld.com')

    async def fake_proxy_browser_request(**kwargs):
        assert kwargs['path'] == '/api/auth/login'
        return browser_routes.Response(
            json.dumps({'message': '登录成功', 'user': {'username': 'alice'}}).encode('utf-8'),
            status_code=200,
            media_type='application/json',
        )

    monkeypatch.setattr(browser_routes, 'proxy_browser_request', fake_proxy_browser_request)

    response = client.post('/api/auth/login', json={'email': 'alice', 'password': 'password123'})

    assert response.status_code == 200
    assert response.json() == {'message': '登录成功', 'user': {'username': 'alice'}}


def test_gateway_auth_proxy_forwards_browser_context_headers(monkeypatch):
    module = _load_gateway_module()
    client = TestClient(module.app, base_url='https://axiomaticworld.com')
    captured: dict[str, object] = {}

    async def fake_proxy_browser_request(**kwargs):
        captured.update(kwargs)
        return browser_routes.Response(
            b'{"user": null, "authenticated": false}',
            status_code=200,
            media_type='application/json',
        )

    monkeypatch.setattr(browser_routes, 'proxy_browser_request', fake_proxy_browser_request)

    response = client.get(
        '/api/auth/me',
        headers={
            'Authorization': 'Bearer test-token',
            'Cookie': 'access_token=abc; refresh_token=def',
            'Origin': 'https://axiomaticworld.com',
            'Referer': 'https://axiomaticworld.com/login',
            'User-Agent': 'pytest-agent/1.0',
        },
    )

    assert response.status_code == 200
    assert response.json() == {'user': None, 'authenticated': False}
    assert captured['path'] == '/api/auth/me'
    forwarded = build_forward_headers(captured['request'])
    assert captured['request'].method == 'GET'
    assert forwarded['authorization'] == 'Bearer test-token'
    assert forwarded['cookie'] == 'access_token=abc; refresh_token=def'
    assert forwarded['x-forwarded-proto'] == 'https'
    assert forwarded['origin'] == 'https://axiomaticworld.com'
