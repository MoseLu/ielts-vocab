from __future__ import annotations

import importlib.util
from pathlib import Path

from fastapi.testclient import TestClient

import platform_sdk.gateway_browser_routes as browser_routes


GATEWAY_PATH = Path(__file__).resolve().parents[2] / 'apps' / 'gateway-bff' / 'main.py'


def _load_gateway_module():
    spec = importlib.util.spec_from_file_location('gateway_bff_exam_main', GATEWAY_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_gateway_exam_library_proxy_routes_to_admin_ops_service(monkeypatch):
    module = _load_gateway_module()
    client = TestClient(module.app, base_url='https://axiomaticworld.com')
    captured: dict[str, object] = {}

    async def fake_proxy_browser_request(**kwargs):
        captured.update(kwargs)
        return browser_routes.Response(
            b'{"items":[{"id":20,"title":"Test 1"}]}',
            status_code=200,
            media_type='application/json',
        )

    monkeypatch.setattr(browser_routes, 'proxy_browser_request', fake_proxy_browser_request)

    response = client.get('/api/exams', headers={'Authorization': 'Bearer learner-token'})

    assert response.status_code == 200
    assert response.json()['items'][0]['id'] == 20
    assert captured['base_url'] == browser_routes.admin_ops_service_url()
    assert captured['path'] == '/api/exams'


def test_gateway_exam_attempt_proxy_routes_to_admin_ops_service(monkeypatch):
    module = _load_gateway_module()
    client = TestClient(module.app, base_url='https://axiomaticworld.com')
    captured: dict[str, object] = {}

    async def fake_proxy_browser_request(**kwargs):
        captured.update(kwargs)
        return browser_routes.Response(
            b'{"attempt":{"id":11,"status":"in_progress"}}',
            status_code=201,
            media_type='application/json',
        )

    monkeypatch.setattr(browser_routes, 'proxy_browser_request', fake_proxy_browser_request)

    response = client.post('/api/exams/20/attempts', headers={'Authorization': 'Bearer learner-token'})

    assert response.status_code == 201
    assert response.json()['attempt']['id'] == 11
    assert captured['base_url'] == browser_routes.admin_ops_service_url()
    assert captured['path'] == '/api/exams/20/attempts'


def test_gateway_exam_response_proxy_routes_to_admin_ops_service(monkeypatch):
    module = _load_gateway_module()
    client = TestClient(module.app, base_url='https://axiomaticworld.com')
    captured: dict[str, object] = {}

    async def fake_proxy_browser_request(**kwargs):
        captured.update(kwargs)
        return browser_routes.Response(
            b'{"attempt":{"id":11,"status":"submitted"}}',
            status_code=200,
            media_type='application/json',
        )

    monkeypatch.setattr(browser_routes, 'proxy_browser_request', fake_proxy_browser_request)

    response = client.patch(
        '/api/exam-attempts/11/responses',
        headers={'Authorization': 'Bearer learner-token'},
        json={'responses': [{'questionId': 1, 'responseText': '9 am'}]},
    )

    assert response.status_code == 200
    assert response.json()['attempt']['status'] == 'submitted'
    assert captured['base_url'] == browser_routes.admin_ops_service_url()
    assert captured['path'] == '/api/exam-attempts/11/responses'


def test_gateway_admin_exam_publish_uses_admin_proxy(monkeypatch):
    module = _load_gateway_module()
    client = TestClient(module.app, base_url='https://axiomaticworld.com')
    captured: dict[str, object] = {}

    async def fake_proxy_browser_request(**kwargs):
        captured.update(kwargs)
        return browser_routes.Response(
            b'{"paperId":20,"publishStatus":"published_internal"}',
            status_code=200,
            media_type='application/json',
        )

    monkeypatch.setattr(browser_routes, 'proxy_browser_request', fake_proxy_browser_request)

    response = client.post(
        '/api/admin/exam-papers/20/publish',
        headers={'Authorization': 'Bearer admin-token'},
    )

    assert response.status_code == 200
    assert response.json()['publishStatus'] == 'published_internal'
    assert captured['base_url'] == browser_routes.admin_ops_service_url()
    assert captured['path'] == '/api/admin/exam-papers/20/publish'
