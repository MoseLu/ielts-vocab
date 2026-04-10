from __future__ import annotations

import importlib.util
from pathlib import Path

from fastapi.testclient import TestClient

import platform_sdk.gateway_browser_routes as browser_routes
from platform_sdk.http_proxy import build_forward_headers


GATEWAY_PATH = Path(__file__).resolve().parents[2] / 'apps' / 'gateway-bff' / 'main.py'


def _load_gateway_module():
    spec = importlib.util.spec_from_file_location('gateway_bff_catalog_main', GATEWAY_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_gateway_books_categories_proxy_routes_to_catalog_content_service(monkeypatch):
    module = _load_gateway_module()
    client = TestClient(module.app, base_url='https://axiomaticworld.com')
    captured: dict[str, object] = {}

    async def fake_proxy_browser_request(**kwargs):
        captured.update(kwargs)
        return browser_routes.Response(
            b'{"categories":[{"id":"reading","name":"\\u9605\\u8bfb\\u8bcd\\u6c47"}]}',
            status_code=200,
            media_type='application/json',
        )

    monkeypatch.setattr(browser_routes, 'proxy_browser_request', fake_proxy_browser_request)

    response = client.get('/api/books/categories')

    assert response.status_code == 200
    assert response.json()['categories'][0]['id'] == 'reading'
    assert captured['base_url'] == browser_routes.catalog_content_service_url()
    assert captured['path'] == '/api/books/categories'


def test_gateway_confusable_custom_chapter_proxy_routes_to_catalog_content_service(monkeypatch):
    module = _load_gateway_module()
    client = TestClient(module.app, base_url='https://axiomaticworld.com')
    captured: dict[str, object] = {}

    async def fake_proxy_browser_request(**kwargs):
        captured.update(kwargs)
        return browser_routes.Response(
            b'{"created_count":1,"created_chapters":[{"id":1001}]}',
            status_code=201,
            media_type='application/json',
        )

    monkeypatch.setattr(browser_routes, 'proxy_browser_request', fake_proxy_browser_request)

    response = client.post(
        '/api/books/ielts_confusable_match/custom-chapters',
        json={'groups': [['whether', 'weather']]},
        headers={'Authorization': 'Bearer catalog-token'},
    )

    assert response.status_code == 201
    assert response.json()['created_chapters'][0]['id'] == 1001
    assert captured['path'] == '/api/books/ielts_confusable_match/custom-chapters'
    assert build_forward_headers(captured['request'])['authorization'] == 'Bearer catalog-token'
