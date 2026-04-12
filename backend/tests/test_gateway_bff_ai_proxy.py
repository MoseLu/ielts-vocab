from __future__ import annotations

import importlib.util
from pathlib import Path

from fastapi.testclient import TestClient

import platform_sdk.gateway_browser_routes as browser_routes
from platform_sdk.http_proxy import build_forward_headers


GATEWAY_PATH = Path(__file__).resolve().parents[2] / 'apps' / 'gateway-bff' / 'main.py'


def _load_gateway_module():
    spec = importlib.util.spec_from_file_location('gateway_bff_ai_main', GATEWAY_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_gateway_ai_context_proxy_routes_to_ai_execution_service(monkeypatch):
    module = _load_gateway_module()
    client = TestClient(module.app, base_url='https://axiomaticworld.com')
    captured: dict[str, object] = {}

    async def fake_proxy_browser_request(**kwargs):
        captured.update(kwargs)
        return browser_routes.Response(
            b'{"totalLearned":0,"books":[]}',
            status_code=200,
            media_type='application/json',
        )

    monkeypatch.setattr(browser_routes, 'proxy_browser_request', fake_proxy_browser_request)

    response = client.get('/api/ai/context', headers={'Authorization': 'Bearer ai-token'})

    assert response.status_code == 200
    assert response.json()['books'] == []
    assert captured['service_name'] == 'ai-execution-service'
    assert captured['base_url'] == browser_routes.ai_execution_service_url()
    assert captured['path'] == '/api/ai/context'
    forwarded = build_forward_headers(captured['request'], target_service_name=captured['service_name'])
    assert 'authorization' not in forwarded


def test_gateway_ai_stream_proxy_routes_to_ai_execution_service(monkeypatch):
    module = _load_gateway_module()
    client = TestClient(module.app, base_url='https://axiomaticworld.com')
    captured: dict[str, object] = {}

    async def fake_proxy_browser_request(**kwargs):
        captured.update(kwargs)
        return browser_routes.Response(
            b'data: {"type": "done"}\n\n',
            status_code=200,
            media_type='text/event-stream',
        )

    monkeypatch.setattr(browser_routes, 'proxy_browser_request', fake_proxy_browser_request)

    response = client.post(
        '/api/ai/ask/stream',
        json={'message': 'hello'},
        headers={'Cookie': 'access_token=abc'},
    )

    assert response.status_code == 200
    assert response.headers['content-type'].startswith('text/event-stream')
    assert 'data: {"type": "done"}' in response.text
    assert captured['service_name'] == 'ai-execution-service'
    assert captured['path'] == '/api/ai/ask/stream'
    forwarded = build_forward_headers(captured['request'], target_service_name=captured['service_name'])
    assert 'cookie' not in forwarded
