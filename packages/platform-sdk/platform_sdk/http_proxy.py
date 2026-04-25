from __future__ import annotations

import httpx
from fastapi import HTTPException, Request, Response
from fastapi.responses import StreamingResponse

from platform_sdk.gateway_upstream import (
    GatewayCircuitOpenError,
    before_gateway_upstream_attempt,
    record_gateway_upstream_failure,
    record_gateway_upstream_success,
    resolve_gateway_upstream_policy,
    should_retry_gateway_upstream,
)
from platform_sdk.internal_service_auth import (
    DEFAULT_SOURCE_SERVICE_NAME,
    try_build_internal_auth_headers,
)


_HOP_BY_HOP_HEADERS = {'connection', 'content-length', 'host', 'transfer-encoding'}
_SERVICE_FORWARD_HEADERS = {
    'accept',
    'content-type',
    'idempotency-key',
    'origin',
    'referer',
    'user-agent',
    'x-forwarded-for',
    'x-forwarded-proto',
    'x-real-ip',
}
_IDENTITY_BROWSER_CONTEXT_HEADERS = {'authorization', 'cookie'}


def build_forward_headers(request: Request, *, target_service_name: str | None = None) -> dict[str, str]:
    headers: dict[str, str] = {}
    forward_header_names = set(_SERVICE_FORWARD_HEADERS)
    if target_service_name == 'identity-service':
        forward_header_names.update(_IDENTITY_BROWSER_CONTEXT_HEADERS)

    for name in forward_header_names:
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


def _is_streaming_request(request: Request, path: str) -> bool:
    accept = request.headers.get('accept', '').lower()
    normalized_path = path.lower()
    return 'text/event-stream' in accept or normalized_path.endswith('/stream')


async def proxy_browser_request(
    *,
    request: Request,
    service_name: str,
    base_url: str,
    path: str,
    unavailable_detail: str,
) -> Response:
    request_headers = build_forward_headers(request, target_service_name=service_name)
    request_body = await request.body()
    streaming_request = _is_streaming_request(request, path)
    policy = resolve_gateway_upstream_policy(
        service_name=service_name,
        path=path,
    )

    attempt_index = 0
    while True:
        try:
            before_gateway_upstream_attempt(policy)
        except GatewayCircuitOpenError as exc:
            raise HTTPException(status_code=503, detail=f'{service_name} circuit open') from exc

        client = httpx.AsyncClient(
            timeout=policy.build_timeout(),
            follow_redirects=False,
            trust_env=False,
        )
        stream_context = None
        try:
            stream_context = client.stream(
                request.method,
                f'{base_url}{path}',
                params=request.query_params,
                content=request_body,
                headers=request_headers,
            )
            response = await stream_context.__aenter__()
        except httpx.TimeoutException as exc:
            await client.aclose()
            record_gateway_upstream_failure(policy)
            if should_retry_gateway_upstream(
                policy=policy,
                method=request.method,
                attempt_index=attempt_index,
                request_headers=request_headers,
                error=exc,
                streaming_request=streaming_request,
            ):
                attempt_index += 1
                continue
            raise HTTPException(status_code=504, detail=f'{service_name} timed out') from exc
        except httpx.HTTPError as exc:
            await client.aclose()
            record_gateway_upstream_failure(policy)
            if should_retry_gateway_upstream(
                policy=policy,
                method=request.method,
                attempt_index=attempt_index,
                request_headers=request_headers,
                error=exc,
                streaming_request=streaming_request,
            ):
                attempt_index += 1
                continue
            raise HTTPException(status_code=502, detail=unavailable_detail) from exc

        if not _is_event_stream_response(response):
            should_retry = False
            try:
                await response.aread()
                if response.status_code >= 500:
                    should_retry = should_retry_gateway_upstream(
                        policy=policy,
                        method=request.method,
                        attempt_index=attempt_index,
                        request_headers=request_headers,
                        status_code=response.status_code,
                        streaming_request=streaming_request,
                    )
                    if should_retry:
                        record_gateway_upstream_failure(policy)
                    else:
                        record_gateway_upstream_failure(policy)
                else:
                    record_gateway_upstream_success(policy)
                proxy = passthrough_response(response)
            finally:
                if stream_context is not None:
                    await stream_context.__aexit__(None, None, None)
                await client.aclose()
            if should_retry:
                attempt_index += 1
                continue
            return proxy

        record_gateway_upstream_success(policy)

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
