from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import Body, HTTPException, Query, Request
from fastapi.responses import Response


REPO_ROOT = Path(__file__).resolve().parents[2]
SERVICE_DIR = Path(__file__).resolve().parent
SDK_PATH = REPO_ROOT / 'packages' / 'platform-sdk'
BACKEND_PATH = REPO_ROOT / 'backend'
for candidate in (SERVICE_DIR, SDK_PATH, BACKEND_PATH):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from platform_sdk.runtime_env import load_split_service_env

load_split_service_env(service_name='tts-media-service')

from platform_sdk.database_readiness import make_sqlalchemy_readiness_check
from platform_sdk.internal_service_auth import (
    REQUEST_ID_HEADER,
    SERVICE_NAME_HEADER,
    TRACE_ID_HEADER,
    USER_ID_HEADER,
)
from platform_sdk.service_app import create_service_app
from platform_sdk.storage import (
    DEFAULT_METADATA_CACHE_TTL_SECONDS,
    DEFAULT_SIGNED_URL_EXPIRES_SECONDS,
    SAFE_OSS_SEGMENT_RE,
    bucket_is_configured,
    env_int,
    fetch_object_payload,
    join_object_key,
    resolve_object_metadata,
)
from platform_sdk.tts_media_event_application import record_tts_media_materialization
from platform_sdk.tts_media_runtime import create_tts_media_flask_app
import runtime_helpers as runtime

DEFAULT_WORD_TTS_OSS_PREFIX = 'projects/ielts-vocab/word-tts-cache'
_AUDIO_BYTES_HEADER = 'X-Audio-Bytes'
_AUDIO_CACHE_KEY_HEADER = 'X-Audio-Cache-Key'
_AUDIO_OSS_URL_HEADER = 'X-Audio-Oss-Url'
_MEDIA_ID_HEADER = 'X-Media-Id'
_SEGMENTED_WORD_CACHE_TAG = 'azure-word-segmented-v1'
tts_media_flask_app = create_tts_media_flask_app()


def _event_headers(request: Request) -> dict[str, str]:
    headers: dict[str, str] = {}
    for name in (REQUEST_ID_HEADER, TRACE_ID_HEADER, SERVICE_NAME_HEADER):
        value = (request.headers.get(name) or request.headers.get(name.title()) or '').strip()
        if value:
            headers[name] = value
    return headers


def _request_user_id(request: Request) -> int | None:
    raw_value = (request.headers.get(USER_ID_HEADER) or request.headers.get(USER_ID_HEADER.title()) or '').strip()
    if not raw_value:
        return None
    try:
        return int(raw_value)
    except ValueError:
        return None


def _record_tts_media_materialization(request: Request, **payload) -> None:
    with tts_media_flask_app.app_context():
        record_tts_media_materialization(
            user_id=_request_user_id(request),
            headers=_event_headers(request),
            **payload,
        )


def _materialization_callback(request: Request):
    return lambda **payload: _record_tts_media_materialization(request, **payload)


def _word_tts_oss_prefix() -> str:
    return (
        os.environ.get('WORD_TTS_OSS_PREFIX', DEFAULT_WORD_TTS_OSS_PREFIX).strip('/')
        or DEFAULT_WORD_TTS_OSS_PREFIX
    )


def _signed_url_expires_seconds() -> int:
    return env_int(
        'WORD_TTS_OSS_SIGNED_URL_EXPIRES_SECONDS',
        DEFAULT_SIGNED_URL_EXPIRES_SECONDS,
    )


def _metadata_cache_ttl_seconds() -> int:
    return env_int(
        'WORD_TTS_OSS_METADATA_CACHE_TTL_SECONDS',
        DEFAULT_METADATA_CACHE_TTL_SECONDS,
    )


def _word_audio_object_key(*, file_name: str, model: str, voice: str) -> str:
    identity = f'{model}--{voice}'
    identity_segment = SAFE_OSS_SEGMENT_RE.sub('-', identity.lower()).strip('-') or 'default'
    segments: list[str] = []
    if f'@{_SEGMENTED_WORD_CACHE_TAG}' in (model or ''):
        segments.append('segmented')
    segments.append(identity_segment)
    return join_object_key(
        prefix=_word_tts_oss_prefix(),
        segments=segments,
        file_name=file_name,
    )


def _resolve_word_audio_metadata(*, file_name: str, model: str, voice: str):
    return resolve_object_metadata(
        object_key=_word_audio_object_key(file_name=file_name, model=model, voice=voice),
        file_name=file_name,
        signed_url_expires_seconds=_signed_url_expires_seconds(),
        metadata_cache_ttl_seconds=_metadata_cache_ttl_seconds(),
    )


app = create_service_app(
    service_name='tts-media-service',
    version='0.1.0',
    readiness_checks={
        'database': make_sqlalchemy_readiness_check(tts_media_flask_app.config['SQLALCHEMY_DATABASE_URI']),
        'aliyun_oss': bucket_is_configured,
    },
    extra_health={'object_storage': 'aliyun-oss'},
)


@app.get('/v1/tts/voices')
def get_tts_voices(provider: str | None = Query(default=None)) -> dict:
    resolved_provider = runtime.normalize_tts_provider(provider)
    return runtime.list_voices_payload(
        runtime.current_english_voices(resolved_provider),
        runtime.current_recommended_voices(resolved_provider),
    )


@app.post('/v1/tts/generate')
def generate_tts_audio(request: Request, payload: dict = Body(...)):
    provider = runtime.requested_tts_provider(payload)
    if provider != 'minimax':
        return runtime.generate_non_minimax_speech(
            payload,
            provider_override=provider,
            on_materialized=_materialization_callback(request),
        )
    return runtime.generate_minimax_speech(
        payload,
        on_materialized=_materialization_callback(request),
    )


@app.get('/v1/media/word-audio')
def get_word_audio_metadata(
    file_name: str = Query(..., min_length=1, max_length=255),
    model: str = Query(..., min_length=1, max_length=255),
    voice: str = Query(..., min_length=1, max_length=255),
) -> dict:
    expires_seconds = _signed_url_expires_seconds()
    metadata = _resolve_word_audio_metadata(file_name=file_name, model=model, voice=voice)
    if metadata is None:
        raise HTTPException(status_code=404, detail='word audio object not found')
    return {
        'media_id': metadata.object_key,
        'cache_hit': True,
        'provider': metadata.provider,
        'bucket_name': metadata.bucket_name,
        'object_key': metadata.object_key,
        'content_type': metadata.content_type,
        'byte_length': metadata.byte_length,
        'cache_key': metadata.cache_key,
        'signed_url': metadata.signed_url,
        'signed_url_expires_at': (
            datetime.now(timezone.utc) + timedelta(seconds=expires_seconds)
        ).isoformat(),
    }


@app.get('/v1/media/word-audio/content')
def get_word_audio_content(
    file_name: str = Query(..., min_length=1, max_length=255),
    model: str = Query(..., min_length=1, max_length=255),
    voice: str = Query(..., min_length=1, max_length=255),
):
    object_key = _word_audio_object_key(file_name=file_name, model=model, voice=voice)
    payload = fetch_object_payload(
        object_key=object_key,
        file_name=file_name,
        signed_url_expires_seconds=_signed_url_expires_seconds(),
        metadata_cache_ttl_seconds=_metadata_cache_ttl_seconds(),
    )
    if payload is None:
        raise HTTPException(status_code=404, detail='word audio payload not found')
    response = Response(payload.body, media_type=payload.content_type or 'application/octet-stream')
    response.headers[_AUDIO_BYTES_HEADER] = str(payload.byte_length)
    if payload.cache_key:
        response.headers[_AUDIO_CACHE_KEY_HEADER] = payload.cache_key
    response.headers[_AUDIO_OSS_URL_HEADER] = payload.signed_url
    response.headers[_MEDIA_ID_HEADER] = payload.object_key
    return response


@app.post('/v1/media/example-audio/metadata')
def get_example_audio_metadata(payload: dict = Body(...)) -> dict:
    sentence = str((payload or {}).get('sentence') or '').strip()
    if not sentence:
        raise HTTPException(status_code=400, detail='sentence is required')
    return runtime.example_audio_metadata(sentence)


@app.post('/v1/media/example-audio/content')
def get_example_audio_content(request: Request, payload: dict = Body(...)):
    sentence = str((payload or {}).get('sentence') or '').strip()
    if not sentence:
        raise HTTPException(status_code=400, detail='sentence is required')
    try:
        audio_payload = runtime.example_audio_content_payload(
            sentence,
            on_materialized=_materialization_callback(request),
        )
    except Exception as exc:
        status_code = getattr(exc, 'status_code', 502)
        if not isinstance(status_code, int) or status_code < 400 or status_code >= 600:
            status_code = 502
        raise HTTPException(status_code=status_code, detail='example audio generation failed') from exc
    response = Response(
        audio_payload['body'],
        media_type=audio_payload.get('content_type') or runtime.DEFAULT_EXAMPLE_AUDIO_CONTENT_TYPE,
    )
    response.headers[_AUDIO_BYTES_HEADER] = str(audio_payload['byte_length'])
    if audio_payload.get('cache_key'):
        response.headers[_AUDIO_CACHE_KEY_HEADER] = str(audio_payload['cache_key'])
    if audio_payload.get('signed_url'):
        response.headers[_AUDIO_OSS_URL_HEADER] = str(audio_payload['signed_url'])
    if audio_payload.get('media_id'):
        response.headers[_MEDIA_ID_HEADER] = str(audio_payload['media_id'])
    return response


if __name__ == '__main__':
    import uvicorn

    uvicorn.run(app, host='0.0.0.0', port=int(os.environ.get('TTS_MEDIA_SERVICE_PORT', '8105')))
