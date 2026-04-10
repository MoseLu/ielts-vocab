from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import Body, HTTPException, Query
from fastapi.responses import Response


REPO_ROOT = Path(__file__).resolve().parents[2]
SERVICE_DIR = Path(__file__).resolve().parent
SDK_PATH = REPO_ROOT / 'packages' / 'platform-sdk'
BACKEND_PATH = REPO_ROOT / 'backend'
for candidate in (SERVICE_DIR, SDK_PATH, BACKEND_PATH):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from platform_sdk.runtime_env import load_split_service_env
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
import runtime_helpers as runtime

load_split_service_env(service_name='tts-media-service')

DEFAULT_WORD_TTS_OSS_PREFIX = 'projects/ielts-vocab/word-tts-cache'
_AUDIO_BYTES_HEADER = 'X-Audio-Bytes'
_AUDIO_CACHE_KEY_HEADER = 'X-Audio-Cache-Key'
_AUDIO_OSS_URL_HEADER = 'X-Audio-Oss-Url'
_MEDIA_ID_HEADER = 'X-Media-Id'


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
    return join_object_key(
        prefix=_word_tts_oss_prefix(),
        segments=[identity_segment],
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
    readiness_checks={'aliyun_oss': bucket_is_configured},
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
def generate_tts_audio(payload: dict = Body(...)):
    provider = runtime.requested_tts_provider(payload)
    if provider != 'minimax':
        return runtime.generate_non_minimax_speech(payload, provider_override=provider)
    return runtime.generate_minimax_speech(payload)


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
def get_example_audio_content(payload: dict = Body(...)):
    sentence = str((payload or {}).get('sentence') or '').strip()
    if not sentence:
        raise HTTPException(status_code=400, detail='sentence is required')
    model, voice = runtime.example_tts_identity(sentence)
    cache_file = runtime.example_cache_file(sentence, model, voice)
    if not (cache_file.exists() and runtime.is_probably_valid_mp3_file(cache_file)):
        runtime.remove_invalid_cached_audio(cache_file)
        try:
            audio_bytes = runtime.synthesize_example_audio(sentence, model, voice)
            runtime.write_bytes_atomically(cache_file, audio_bytes)
        except Exception as exc:
            status_code = getattr(exc, 'status_code', 502)
            if not isinstance(status_code, int) or status_code < 400 or status_code >= 600:
                status_code = 502
            raise HTTPException(status_code=status_code, detail='example audio generation failed') from exc
    response = Response(cache_file.read_bytes(), media_type=runtime.DEFAULT_EXAMPLE_AUDIO_CONTENT_TYPE)
    response.headers[_AUDIO_BYTES_HEADER] = str(cache_file.stat().st_size)
    response.headers[_AUDIO_CACHE_KEY_HEADER] = runtime.local_cache_key(cache_file)
    response.headers[_MEDIA_ID_HEADER] = cache_file.name
    return response


if __name__ == '__main__':
    import uvicorn

    uvicorn.run(app, host='0.0.0.0', port=int(os.environ.get('TTS_MEDIA_SERVICE_PORT', '8105')))
