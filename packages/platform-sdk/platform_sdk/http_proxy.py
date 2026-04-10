from __future__ import annotations

import httpx
from fastapi import HTTPException, Request, Response
from fastapi.responses import StreamingResponse

from platform_sdk.internal_service_auth import (
    DEFAULT_SOURCE_SERVICE_NAME,
    try_build_internal_auth_headers,
)


_HOP_BY_HOP_HEADERS = {'connection', 'content-length', 'host', 'transfer-encoding'}
_SERVICE_FORWARD_HEADERS = {
    'authorization',
    'content-type',
    'cookie',
    'origin',
    'referer',
    'user-agent',
    'x-forwarded-for',
    'x-forwarded-proto',
    'x-real-ip',
}


def build_forward_headers(request: Request) -> dict[str, str]:
    headers: dict[str, str] = {}
    for name in _SERVICE_FORWARD_HEADERS:
        value = request.headers.get(name)
        if value:
            headers[name] = value

    if 'x-forwarded-proto' not in headers:
        headers['x-forwarded-proto'] = request.url.scheme
    if 'x-forwarded-for' not in headers and request.client is not None:
        headers['x-forwarded-for'] = request.client.host

    host = request.headers.get('host')
    if host:
        headers['x-forwarded-host'] = host
    headers.update(
        try_build_internal_auth_headers(
            request,
            source_service_name=DEFAULT_SOURCE_SERVICE_NAME,
        )
    )
    return headers


def passthrough_response(response: httpx.Response) -> Response:
    proxy = Response(response.content, status_code=response.status_code)
    _apply_upstream_headers(proxy, response.headers)
    return proxy


def _apply_upstream_headers(proxy: Response, headers) -> None:
    for name, value in headers.multi_items():
        normalized_name = name.lower()
        if normalized_name in _HOP_BY_HOP_HEADERS:
            continue
        if normalized_name == 'set-cookie':
            proxy.headers.append(name, value)
            continue
        proxy.headers[name] = value


def _is_event_stream_response(response: httpx.Response) -> bool:
    content_type = response.headers.get('content-type', '').lower()
    return content_type.startswith('text/event-stream')


async def proxy_browser_request(
    *,
    request: Request,
    base_url: str,
    path: str,
    timeout_seconds: float,
    unavailable_detail: str,
) -> Response:
    client = httpx.AsyncClient(
        timeout=timeout_seconds,
        follow_redirects=False,
    )
    stream_context = None
    try:
        stream_context = client.stream(
            request.method,
            f'{base_url}{path}',
            params=request.query_params,
            content=await request.body(),
            headers=build_forward_headers(request),
        )
        response = await stream_context.__aenter__()
    except httpx.HTTPError as exc:
        await client.aclose()
        raise HTTPException(status_code=502, detail=unavailable_detail) from exc

    if not _is_event_stream_response(response):
        try:
            await response.aread()
            proxy = passthrough_response(response)
        finally:
            if stream_context is not None:
                await stream_context.__aexit__(None, None, None)
            await client.aclose()
        return proxy

    async def iterate_stream():
        try:
            async for chunk in response.aiter_bytes():
                yield chunk
        finally:
            if stream_context is not None:
                await stream_context.__aexit__(None, None, None)
            await client.aclose()

    proxy = StreamingResponse(
        iterate_stream(),
        status_code=response.status_code,
    )
    _apply_upstream_headers(proxy, response.headers)
    return proxy
