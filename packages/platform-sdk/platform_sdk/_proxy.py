"""HTTP upstream proxy core for ``gateway_media_proxy``.

Hosts:

* the circuit-breaker aware upstream client (``call_media_upstream``)
* the per-endpoint ``fetch_*`` helpers that wrap media / ASR calls
* the FastAPI ``Response`` builders that apply audio headers and
  proxy JSON / binary payloads.

Test-side monkeypatching targets (``call_media_upstream``,
``fetch_word_audio_metadata``, ``fetch_word_audio_content``,
``generate_tts_audio``) stay in this module so the public wrapper
can re-export them with the same identity.
"""

from __future__ import annotations

import httpx
from fastapi import HTTPException, Response
from fastapi.responses import JSONResponse

from platform_sdk._helpers import (
    _AUDIO_BYTES_HEADER,
    _AUDIO_CACHE_KEY_HEADER,
    _AUDIO_OSS_URL_HEADER,
    _AUDIO_SOURCE_HEADER,
    _MEDIA_ID_HEADER,
    asr_service_url,
    tts_media_service_url,
)
from platform_sdk.gateway_upstream import (
    GatewayCircuitOpenError,
    before_gateway_upstream_attempt,
    record_gateway_upstream_failure,
    record_gateway_upstream_success,
    resolve_gateway_upstream_policy,
    should_retry_gateway_upstream,
)


def call_media_upstream(
    *,
    service_name: str,
    method: str,
    base_url: str,
    path: str,
    params: dict | None = None,
    json: dict | None = None,
    files=None,
    headers: dict[str, str] | None = None,
    unavailable_detail: str,
) -> httpx.Response:
    request_headers = dict(headers or {})
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

        try:
            with httpx.Client(timeout=policy.build_timeout(), follow_redirects=False, trust_env=False) as client:
                response = client.request(
                    method,
                    f'{base_url}{path}',
                    params=params,
                    json=json,
                    files=files,
                    headers=request_headers,
                )
        except httpx.TimeoutException as exc:
            record_gateway_upstream_failure(policy)
            if should_retry_gateway_upstream(
                policy=policy,
                method=method,
                attempt_index=attempt_index,
                request_headers=request_headers,
                error=exc,
            ):
                attempt_index += 1
                continue
            raise HTTPException(status_code=504, detail=f'{service_name} timed out') from exc
        except httpx.HTTPError as exc:
            record_gateway_upstream_failure(policy)
            if should_retry_gateway_upstream(
                policy=policy,
                method=method,
                attempt_index=attempt_index,
                request_headers=request_headers,
                error=exc,
            ):
                attempt_index += 1
                continue
            raise HTTPException(status_code=502, detail=unavailable_detail) from exc

        if response.status_code >= 500:
            should_retry = should_retry_gateway_upstream(
                policy=policy,
                method=method,
                attempt_index=attempt_index,
                request_headers=request_headers,
                status_code=response.status_code,
            )
            record_gateway_upstream_failure(policy)
            if should_retry:
                attempt_index += 1
                continue
            return response

        record_gateway_upstream_success(policy)
        return response


def audio_payload_from_response(response: httpx.Response) -> dict:
    return {
        'body': response.content,
        'content_type': response.headers.get('content-type', 'application/octet-stream'),
        'byte_length': response.headers.get(_AUDIO_BYTES_HEADER, ''),
        'cache_key': response.headers.get(_AUDIO_CACHE_KEY_HEADER, ''),
        'signed_url': response.headers.get(_AUDIO_OSS_URL_HEADER, ''),
        'media_id': response.headers.get(_MEDIA_ID_HEADER, ''),
    }


def fetch_word_audio_metadata(
    *,
    file_name: str,
    model: str,
    voice: str,
    headers: dict[str, str] | None = None,
) -> dict | None:
    response = call_media_upstream(
        service_name='tts-media-service',
        method='GET',
        base_url=tts_media_service_url(),
        path='/v1/media/word-audio',
        params={'file_name': file_name, 'model': model, 'voice': voice},
        headers=headers,
        unavailable_detail='tts media service unavailable',
    )
    if response.status_code == 404:
        return None
    if response.status_code >= 400:
        raise HTTPException(status_code=502, detail='tts media service error')
    return response.json()


def fetch_word_audio_content(
    *,
    file_name: str,
    model: str,
    voice: str,
    headers: dict[str, str] | None = None,
) -> dict | None:
    response = call_media_upstream(
        service_name='tts-media-service',
        method='GET',
        base_url=tts_media_service_url(),
        path='/v1/media/word-audio/content',
        params={'file_name': file_name, 'model': model, 'voice': voice},
        headers=headers,
        unavailable_detail='tts media service unavailable',
    )
    if response.status_code == 404:
        return None
    if response.status_code >= 400:
        raise HTTPException(status_code=502, detail='tts media service error')
    return audio_payload_from_response(response)


def fetch_follow_read_word(
    *,
    word: str,
    phonetic: str | None = None,
    definition: str | None = None,
    pos: str | None = None,
    headers: dict[str, str] | None = None,
) -> dict:
    params = {'w': word}
    if phonetic:
        params['phonetic'] = phonetic
    if definition:
        params['definition'] = definition
    if pos:
        params['pos'] = pos
    response = call_media_upstream(
        service_name='tts-media-service',
        method='GET',
        base_url=tts_media_service_url(),
        path='/v1/media/follow-read-word',
        params=params,
        headers=headers,
        unavailable_detail='tts media service unavailable',
    )
    if response.status_code == 400:
        raise HTTPException(status_code=400, detail='invalid w')
    if response.status_code >= 400:
        raise HTTPException(status_code=502, detail='tts media service error')
    return response.json()


def fetch_follow_read_chunked_audio(
    *,
    word: str,
    phonetic: str | None = None,
    headers: dict[str, str] | None = None,
) -> dict:
    params = {'w': word}
    if phonetic:
        params['phonetic'] = phonetic
    response = call_media_upstream(
        service_name='tts-media-service',
        method='GET',
        base_url=tts_media_service_url(),
        path='/v1/media/follow-read-chunked-audio',
        params=params,
        headers=headers,
        unavailable_detail='tts media service unavailable',
    )
    if response.status_code == 400:
        raise HTTPException(status_code=400, detail='invalid w')
    if response.status_code >= 400:
        raise HTTPException(status_code=502, detail='tts media service error')
    return audio_payload_from_response(response)


def fetch_example_audio_metadata(
    *,
    sentence: str,
    word: str | None = None,
    headers: dict[str, str] | None = None,
) -> dict:
    response = call_media_upstream(
        service_name='tts-media-service',
        method='POST',
        base_url=tts_media_service_url(),
        path='/v1/media/example-audio/metadata',
        json={'sentence': sentence, 'word': word},
        headers=headers,
        unavailable_detail='tts media service unavailable',
    )
    if response.status_code == 400:
        raise HTTPException(status_code=400, detail='sentence is required')
    if response.status_code >= 400:
        raise HTTPException(status_code=502, detail='tts media service error')
    return response.json()


def fetch_example_audio_content(
    *,
    sentence: str,
    word: str | None = None,
    headers: dict[str, str] | None = None,
) -> dict:
    response = call_media_upstream(
        service_name='tts-media-service',
        method='POST',
        base_url=tts_media_service_url(),
        path='/v1/media/example-audio/content',
        json={'sentence': sentence, 'word': word},
        headers=headers,
        unavailable_detail='tts media service unavailable',
    )
    if response.status_code == 400:
        raise HTTPException(status_code=400, detail='sentence is required')
    if response.status_code >= 400:
        raise HTTPException(status_code=502, detail='tts media service error')
    return audio_payload_from_response(response)


def fetch_tts_voices(*, provider: str | None = None, headers: dict[str, str] | None = None) -> dict:
    response = call_media_upstream(
        service_name='tts-media-service',
        method='GET',
        base_url=tts_media_service_url(),
        path='/v1/tts/voices',
        params={'provider': provider} if provider else None,
        headers=headers,
        unavailable_detail='tts media service unavailable',
    )
    if response.status_code >= 400:
        raise HTTPException(status_code=502, detail='tts media service error')
    return response.json()


def generate_tts_audio(payload: dict, *, headers: dict[str, str] | None = None) -> httpx.Response:
    return call_media_upstream(
        service_name='tts-media-service',
        method='POST',
        base_url=tts_media_service_url(),
        path='/v1/tts/generate',
        json=payload,
        headers=headers,
        unavailable_detail='tts media service unavailable',
    )


def transcribe_speech_upload(
    *,
    filename: str,
    content: bytes,
    content_type: str | None,
    headers: dict[str, str] | None = None,
) -> httpx.Response:
    return call_media_upstream(
        service_name='asr-service',
        method='POST',
        base_url=asr_service_url(),
        path='/v1/speech/transcribe',
        files={'audio': (filename, content, content_type or 'application/octet-stream')},
        headers=headers,
        unavailable_detail='asr service unavailable',
    )


def apply_audio_headers(response: Response, *, byte_length: str | int | None, cache_key: str | None) -> Response:
    if byte_length not in (None, ''):
        response.headers[_AUDIO_BYTES_HEADER] = str(byte_length)
    if cache_key:
        response.headers[_AUDIO_CACHE_KEY_HEADER] = cache_key
    response.headers['Cache-Control'] = 'no-store, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Accept-Ranges'] = 'none'
    return response


def metadata_only_response(metadata: dict, *, source: str) -> Response:
    response = Response(status_code=204)
    cache_hit = metadata.get('cache_hit')
    if cache_hit is None:
        cache_hit = any(
            metadata.get(field) not in (None, '')
            for field in ('byte_length', 'cache_key', 'signed_url', 'media_id')
        )
    if not cache_hit:
        response.headers[_AUDIO_SOURCE_HEADER] = 'missing'
        return response
    response = apply_audio_headers(
        response,
        byte_length=metadata.get('byte_length'),
        cache_key=metadata.get('cache_key'),
    )
    if metadata.get('signed_url'):
        response.headers[_AUDIO_OSS_URL_HEADER] = str(metadata['signed_url'])
    if metadata.get('media_id'):
        response.headers[_MEDIA_ID_HEADER] = str(metadata['media_id'])
    provider = str(metadata.get('provider') or '').strip().lower()
    response.headers[_AUDIO_SOURCE_HEADER] = (
        'oss' if provider == 'aliyun-oss' or metadata.get('signed_url') else source
    )
    return response


def audio_content_response(payload: dict, *, source: str) -> Response:
    response = Response(payload['body'], media_type=payload['content_type'])
    response = apply_audio_headers(
        response,
        byte_length=payload.get('byte_length'),
        cache_key=payload.get('cache_key'),
    )
    if payload.get('signed_url'):
        response.headers[_AUDIO_OSS_URL_HEADER] = str(payload['signed_url'])
    if payload.get('media_id'):
        response.headers[_MEDIA_ID_HEADER] = str(payload['media_id'])
    provider = str(payload.get('provider') or '').strip().lower()
    response.headers[_AUDIO_SOURCE_HEADER] = (
        'oss' if provider == 'aliyun-oss' or payload.get('signed_url') else source
    )
    return response


def proxy_generic_tts_response(response: httpx.Response):
    content_type = response.headers.get('content-type', '')
    if 'application/json' in content_type:
        return JSONResponse(status_code=response.status_code, content=response.json())
    proxy = Response(response.content, status_code=response.status_code, media_type=content_type or None)
    return apply_audio_headers(
        proxy,
        byte_length=response.headers.get(_AUDIO_BYTES_HEADER, ''),
        cache_key=response.headers.get(_AUDIO_CACHE_KEY_HEADER, ''),
    )


def proxy_json_response(response: httpx.Response):
    content_type = response.headers.get('content-type', '')
    if 'application/json' in content_type:
        return JSONResponse(status_code=response.status_code, content=response.json())
    return Response(response.content, status_code=response.status_code, media_type=content_type or None)


__all__ = [
    'apply_audio_headers',
    'audio_content_response',
    'audio_payload_from_response',
    'call_media_upstream',
    'fetch_example_audio_content',
    'fetch_example_audio_metadata',
    'fetch_follow_read_chunked_audio',
    'fetch_follow_read_word',
    'fetch_tts_voices',
    'fetch_word_audio_content',
    'fetch_word_audio_metadata',
    'generate_tts_audio',
    'metadata_only_response',
    'proxy_generic_tts_response',
    'proxy_json_response',
    'transcribe_speech_upload',
]