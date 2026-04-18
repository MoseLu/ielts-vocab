from __future__ import annotations

import os
import sys
from pathlib import Path

import httpx
from fastapi import HTTPException, Response
from fastapi.responses import JSONResponse

from platform_sdk.gateway_upstream import (
    GatewayCircuitOpenError,
    before_gateway_upstream_attempt,
    record_gateway_upstream_failure,
    record_gateway_upstream_success,
    resolve_gateway_upstream_policy,
    should_retry_gateway_upstream,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_PATH = REPO_ROOT / 'backend'
if str(BACKEND_PATH) not in sys.path:
    sys.path.insert(0, str(BACKEND_PATH))

from platform_sdk.word_tts_runtime_adapter import (
    default_word_tts_identity,
    normalize_word_key,
    word_tts_cache_path,
)


DEFAULT_TTS_MEDIA_SERVICE_URL = 'http://127.0.0.1:8105'
DEFAULT_ASR_SERVICE_URL = 'http://127.0.0.1:8106'
_AUDIO_BYTES_HEADER = 'X-Audio-Bytes'
_AUDIO_CACHE_KEY_HEADER = 'X-Audio-Cache-Key'
_AUDIO_OSS_URL_HEADER = 'X-Audio-Oss-Url'
_AUDIO_SOURCE_HEADER = 'X-Audio-Source'
_MEDIA_ID_HEADER = 'X-Media-Id'
_RYAN_WORD_AUDIO_VOICE = 'en-GB-RyanNeural'
_RYAN_WORD_AUDIO_OVERRIDES = frozenset({
    'brag',
    'branch',
    'brash',
    'brass',
    'brave',
    'breach',
    'bread',
    'breadth',
    'breed',
    'breeding',
    'brew',
    'brewery',
    'brick',
    'bridle',
    'brim',
    'brochure',
    'broker',
    'broom',
    'brought',
    'brute',
})


def tts_media_service_url() -> str:
    return (os.environ.get('TTS_MEDIA_SERVICE_URL') or DEFAULT_TTS_MEDIA_SERVICE_URL).rstrip('/')


def asr_service_url() -> str:
    return (os.environ.get('ASR_SERVICE_URL') or DEFAULT_ASR_SERVICE_URL).rstrip('/')


def validate_sentence(sentence: str) -> str:
    resolved = (sentence or '').strip()
    if not resolved:
        raise HTTPException(status_code=400, detail='sentence is required')
    return resolved


def resolve_word_audio_request(word: str) -> dict[str, str]:
    raw = (word or '').strip()
    if not raw or len(raw) > 160:
        raise HTTPException(status_code=400, detail='invalid w')
    normalized = normalize_word_key(raw)
    provider, model, voice = default_word_tts_identity()
    if provider == 'azure' and normalized in _RYAN_WORD_AUDIO_OVERRIDES:
        voice = _RYAN_WORD_AUDIO_VOICE
    file_name = word_tts_cache_path(Path('word_tts_cache'), normalized, model, voice).name
    return {
        'word': raw,
        'normalized_word': normalized,
        'provider': provider,
        'model': model,
        'voice': voice,
        'file_name': file_name,
    }


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
            with httpx.Client(timeout=policy.build_timeout(), follow_redirects=False) as client:
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
