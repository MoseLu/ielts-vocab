from __future__ import annotations

import importlib.util
from pathlib import Path

from fastapi.testclient import TestClient

import platform_sdk.gateway_browser_routes as browser_routes
from platform_sdk.http_proxy import build_forward_headers


GATEWAY_PATH = Path(__file__).resolve().parents[2] / 'apps' / 'gateway-bff' / 'main.py'


def _load_gateway_module():
    spec = importlib.util.spec_from_file_location('gateway_bff_notes_main', GATEWAY_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_gateway_notes_list_proxy_routes_to_notes_service(monkeypatch):
    module = _load_gateway_module()
    client = TestClient(module.app, base_url='https://axiomaticworld.com')
    captured: dict[str, object] = {}

    async def fake_proxy_browser_request(**kwargs):
        captured.update(kwargs)
        return browser_routes.Response(
            b'{"notes":[],"memory_topics":[],"total":0,"per_page":20,"next_cursor":null,"has_more":false}',
            status_code=200,
            media_type='application/json',
        )

    monkeypatch.setattr(browser_routes, 'proxy_browser_request', fake_proxy_browser_request)

    response = client.get('/api/notes?per_page=20', headers={'Authorization': 'Bearer notes-token'})

    assert response.status_code == 200
    assert response.json()['notes'] == []
    assert captured['base_url'] == browser_routes.notes_service_url()
    assert captured['path'] == '/api/notes'
    assert build_forward_headers(captured['request'])['authorization'] == 'Bearer notes-token'


def test_gateway_notes_job_proxy_routes_to_notes_service(monkeypatch):
    module = _load_gateway_module()
    client = TestClient(module.app, base_url='https://axiomaticworld.com')
    captured: dict[str, object] = {}

    async def fake_proxy_browser_request(**kwargs):
        captured.update(kwargs)
        return browser_routes.Response(
            b'{"job_id":"job-123","status":"completed","progress":100}',
            status_code=200,
            media_type='application/json',
        )

    monkeypatch.setattr(browser_routes, 'proxy_browser_request', fake_proxy_browser_request)

    response = client.get(
        '/api/notes/summaries/generate-jobs/job-123',
        headers={'Cookie': 'access_token=abc'},
    )

    assert response.status_code == 200
    assert response.json()['job_id'] == 'job-123'
    assert captured['path'] == '/api/notes/summaries/generate-jobs/job-123'
    assert build_forward_headers(captured['request'])['cookie'] == 'access_token=abc'


def test_gateway_word_detail_note_proxy_routes_to_notes_service(monkeypatch):
    module = _load_gateway_module()
    client = TestClient(module.app, base_url='https://axiomaticworld.com')
    captured: dict[str, object] = {}

    async def fake_proxy_browser_request(**kwargs):
        captured.update(kwargs)
        return browser_routes.Response(
            b'{"note":{"word":"quit","content":"remember"}}',
            status_code=200,
            media_type='application/json',
        )

    monkeypatch.setattr(browser_routes, 'proxy_browser_request', fake_proxy_browser_request)

    response = client.put(
        '/api/books/word-details/note',
        json={'word': 'quit', 'content': 'remember'},
        headers={'Authorization': 'Bearer note-token'},
    )

    assert response.status_code == 200
    assert response.json()['note']['word'] == 'quit'
    assert captured['path'] == '/api/books/word-details/note'
    assert build_forward_headers(captured['request'])['authorization'] == 'Bearer note-token'
