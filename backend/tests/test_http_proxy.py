from __future__ import annotations

from collections.abc import Sequence

import httpx
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

import platform_sdk.http_proxy as http_proxy
from platform_sdk.gateway_upstream import GatewayUpstreamPolicy, reset_gateway_upstream_state


class FakeResponse:
    def __init__(
        self,
        *,
        status_code: int,
        headers: dict[str, str] | None = None,
        content: bytes = b'',
        stream_chunks: Sequence[bytes] | None = None,
    ):
        self.status_code = status_code
        self.headers = httpx.Headers(headers or {'content-type': 'application/json'})
        self.content = content
        self._stream_chunks = list(stream_chunks or [content])

    async def aread(self) -> bytes:
        return self.content

    async def aiter_bytes(self):
        for chunk in self._stream_chunks:
            yield chunk


class FakeStreamContext:
    def __init__(self, outcome):
        self._outcome = outcome

    async def __aenter__(self):
        if isinstance(self._outcome, Exception):
            raise self._outcome
        return self._outcome

    async def __aexit__(self, exc_type, exc, tb):
        return False


def _make_async_client(outcomes, captured_calls, captured_timeouts, captured_client_kwargs=None):
    class FakeAsyncClient:
        def __init__(self, *args, **kwargs):
            captured_timeouts.append(kwargs.get('timeout'))
            if captured_client_kwargs is not None:
                captured_client_kwargs.append(kwargs)

        def stream(self, method, url, params=None, content=None, headers=None):
            captured_calls.append(
                {
                    'method': method,
                    'url': url,
                    'params': params,
                    'content': content,
                    'headers': headers,
                }
            )
            return FakeStreamContext(outcomes.pop(0))

        async def aclose(self):
            return None

    return FakeAsyncClient


def _build_proxy_app(*, service_name: str, upstream_path: str):
    app = FastAPI()

    @app.api_route('/proxy', methods=['GET', 'POST'])
    async def proxy(request: Request):
        return await http_proxy.proxy_browser_request(
            request=request,
            service_name=service_name,
            base_url='http://upstream.test',
            path=upstream_path,
            unavailable_detail=f'{service_name} unavailable',
        )

    return app


def test_proxy_browser_request_retries_safe_get_timeout_then_succeeds(monkeypatch):
    reset_gateway_upstream_state()
    outcomes = [
        httpx.ReadTimeout('upstream timed out'),
        FakeResponse(
            status_code=200,
            headers={'content-type': 'application/json'},
            content=b'{"ok":true}',
        ),
    ]
    captured_calls: list[dict[str, object]] = []
    captured_timeouts: list[object] = []
    monkeypatch.setattr(
        http_proxy.httpx,
        'AsyncClient',
        _make_async_client(outcomes, captured_calls, captured_timeouts),
    )

    app = _build_proxy_app(service_name='catalog-content-service', upstream_path='/api/books')
    client = TestClient(app, base_url='https://axiomaticworld.com')

    response = client.get('/proxy')

    assert response.status_code == 200
    assert response.json() == {'ok': True}
    assert len(captured_calls) == 2
    assert captured_calls[1]['headers']['x-service-name'] == 'gateway-bff'
    assert captured_timeouts[0].read == 5.0


def test_proxy_browser_request_uses_extended_timeout_for_books_search(monkeypatch):
    reset_gateway_upstream_state()
    outcomes = [
        FakeResponse(
            status_code=200,
            headers={'content-type': 'application/json'},
            content=b'{"query":"test","results":[],"total":0}',
        ),
    ]
    captured_calls: list[dict[str, object]] = []
    captured_timeouts: list[object] = []
    monkeypatch.setattr(
        http_proxy.httpx,
        'AsyncClient',
        _make_async_client(outcomes, captured_calls, captured_timeouts),
    )

    app = _build_proxy_app(service_name='catalog-content-service', upstream_path='/api/books/search')
    client = TestClient(app, base_url='https://axiomaticworld.com')

    response = client.get('/proxy?q=test&limit=12')

    assert response.status_code == 200
    assert response.json() == {'query': 'test', 'results': [], 'total': 0}
    assert len(captured_calls) == 1
    assert captured_timeouts[0].read == 15.0


def test_proxy_browser_request_uses_extended_timeout_for_custom_books(monkeypatch):
    reset_gateway_upstream_state()
    outcomes = [
        FakeResponse(
            status_code=201,
            headers={'content-type': 'application/json'},
            content=b'{"bookId":"custom_1"}',
        ),
    ]
    captured_calls: list[dict[str, object]] = []
    captured_timeouts: list[object] = []
    monkeypatch.setattr(
        http_proxy.httpx,
        'AsyncClient',
        _make_async_client(outcomes, captured_calls, captured_timeouts),
    )

    app = _build_proxy_app(
        service_name='catalog-content-service',
        upstream_path='/api/books/custom-books/custom_1/chapters',
    )
    client = TestClient(app, base_url='https://axiomaticworld.com')

    response = client.post('/proxy', json={'chapters': [], 'words': []})

    assert response.status_code == 201
    assert response.json() == {'bookId': 'custom_1'}
    assert len(captured_calls) == 1
    assert captured_timeouts[0].read == 60.0


def test_proxy_browser_request_preserves_event_stream_headers(monkeypatch):
    reset_gateway_upstream_state()
    outcomes = [
        FakeResponse(
            status_code=200,
            headers={
                'content-type': 'text/event-stream; charset=utf-8',
                'x-request-id': 'req-stream-1',
                'x-trace-id': 'trace-stream-1',
            },
            stream_chunks=[
                b'data: {"type":"delta"}\n\n',
                b'data: {"type":"done"}\n\n',
            ],
        )
    ]
    captured_calls: list[dict[str, object]] = []
    captured_timeouts: list[object] = []
    monkeypatch.setattr(
        http_proxy.httpx,
        'AsyncClient',
        _make_async_client(outcomes, captured_calls, captured_timeouts),
    )

    app = _build_proxy_app(service_name='ai-execution-service', upstream_path='/api/ai/ask/stream')
    client = TestClient(app, base_url='https://axiomaticworld.com')

    response = client.post(
        '/proxy',
        json={'message': 'hello'},
        headers={'Accept': 'text/event-stream'},
    )

    assert response.status_code == 200
    assert response.headers['content-type'].startswith('text/event-stream')
    assert response.headers['x-request-id'] == 'req-stream-1'
    assert response.headers['x-trace-id'] == 'trace-stream-1'
    assert 'data: {"type":"done"}' in response.text
    assert len(captured_calls) == 1
    assert captured_timeouts[0].read == 90.0


def test_proxy_browser_request_does_not_retry_stream_timeout(monkeypatch):
    reset_gateway_upstream_state()
    outcomes = [httpx.ReadTimeout('stream timed out')]
    captured_calls: list[dict[str, object]] = []
    captured_timeouts: list[object] = []
    monkeypatch.setattr(
        http_proxy.httpx,
        'AsyncClient',
        _make_async_client(outcomes, captured_calls, captured_timeouts),
    )

    app = _build_proxy_app(service_name='ai-execution-service', upstream_path='/api/ai/ask/stream')
    client = TestClient(app, base_url='https://axiomaticworld.com')

    response = client.post(
        '/proxy',
        json={'message': 'hello'},
        headers={'Accept': 'text/event-stream'},
    )

    assert response.status_code == 504
    assert response.json() == {'detail': 'ai-execution-service timed out'}
    assert len(captured_calls) == 1


def test_proxy_browser_request_opens_circuit_after_repeated_failures(monkeypatch):
    reset_gateway_upstream_state()
    outcomes = [
        httpx.ConnectError('connect failure'),
        httpx.ConnectError('connect failure'),
    ]
    captured_calls: list[dict[str, object]] = []
    captured_timeouts: list[object] = []
    monkeypatch.setattr(
        http_proxy.httpx,
        'AsyncClient',
        _make_async_client(outcomes, captured_calls, captured_timeouts),
    )
    monkeypatch.setattr(
        http_proxy,
        'resolve_gateway_upstream_policy',
        lambda **kwargs: GatewayUpstreamPolicy(
            service_name=kwargs['service_name'],
            connect_timeout_seconds=1.0,
            read_timeout_seconds=1.0,
            retry_attempts=0,
            circuit_breaker_failures=2,
            circuit_breaker_reset_seconds=60.0,
        ),
    )

    app = _build_proxy_app(service_name='catalog-content-service', upstream_path='/api/books')
    client = TestClient(app, base_url='https://axiomaticworld.com')

    first = client.get('/proxy')
    second = client.get('/proxy')
    third = client.get('/proxy')

    assert first.status_code == 502
    assert second.status_code == 502
    assert third.status_code == 503
    assert third.json() == {'detail': 'catalog-content-service circuit open'}
    assert len(captured_calls) == 2


def test_proxy_browser_request_disables_env_proxy_resolution(monkeypatch):
    reset_gateway_upstream_state()
    outcomes = [
        FakeResponse(
            status_code=200,
            headers={'content-type': 'application/json'},
            content=b'{"ok":true}',
        ),
    ]
    captured_calls: list[dict[str, object]] = []
    captured_timeouts: list[object] = []
    captured_client_kwargs: list[dict[str, object]] = []
    monkeypatch.setattr(
        http_proxy.httpx,
        'AsyncClient',
        _make_async_client(
            outcomes,
            captured_calls,
            captured_timeouts,
            captured_client_kwargs,
        ),
    )

    app = _build_proxy_app(service_name='identity-service', upstream_path='/api/auth/me')
    client = TestClient(app, base_url='https://axiomaticworld.com')

    response = client.get('/proxy')

    assert response.status_code == 200
    assert response.json() == {'ok': True}
    assert len(captured_client_kwargs) == 1
    assert captured_client_kwargs[0]['trust_env'] is False
