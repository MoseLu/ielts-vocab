from __future__ import annotations

import httpx

from platform_sdk.http_readiness import make_http_readiness_check


def test_readiness_check_ignores_env_proxy_settings(monkeypatch):
    captured_kwargs: dict[str, object] = {}

    class FakeResponse:
        status_code = 200

    def fake_get(url, **kwargs):
        captured_kwargs.update(kwargs)
        return FakeResponse()

    monkeypatch.setattr(httpx, 'get', fake_get)

    check = make_http_readiness_check(base_url='http://127.0.0.1:8105')

    assert check() is True
    assert captured_kwargs['trust_env'] is False
