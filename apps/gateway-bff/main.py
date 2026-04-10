from __future__ import annotations

import os
import sys
from pathlib import Path

import httpx
from fastapi import Body, File, Header, HTTPException, Query, Response, UploadFile
from fastapi.responses import JSONResponse


REPO_ROOT = Path(__file__).resolve().parents[2]
SDK_PATH = REPO_ROOT / 'packages' / 'platform-sdk'
BACKEND_PATH = REPO_ROOT / 'backend'
for candidate in (SDK_PATH, BACKEND_PATH):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from platform_sdk.runtime_env import load_split_service_env
from platform_sdk.gateway_browser_routes import (
    admin_ops_service_url,
    ai_execution_service_url,
    browser_compat_router,
    catalog_content_service_url,
    identity_service_url,
    learning_core_service_url,
    notes_service_url,
)
from platform_sdk.http_readiness import make_http_readiness_check
from platform_sdk.service_app import create_service_app
from services.word_tts import default_word_tts_identity, normalize_word_key, word_tts_cache_path

load_split_service_env(service_name='gateway-bff')


DEFAULT_TTS_MEDIA_SERVICE_URL = 'http://127.0.0.1:8105'
DEFAULT_ASR_SERVICE_URL = 'http://127.0.0.1:8106'
DEFAULT_UPSTREAM_TIMEOUT_SECONDS = 10.0
_AUDIO_BYTES_HEADER = 'X-Audio-Bytes'
_AUDIO_CACHE_KEY_HEADER = 'X-Audio-Cache-Key'
_AUDIO_OSS_URL_HEADER = 'X-Audio-Oss-Url'
_AUDIO_SOURCE_HEADER = 'X-Audio-Source'
_MEDIA_ID_HEADER = 'X-Media-Id'


def _tts_media_service_url() -> str:
    return (os.environ.get('TTS_MEDIA_SERVICE_URL') or DEFAULT_TTS_MEDIA_SERVICE_URL).rstrip('/')


def _asr_service_url() -> str:
    return (os.environ.get('ASR_SERVICE_URL') or DEFAULT_ASR_SERVICE_URL).rstrip('/')


def _upstream_timeout_seconds() -> float:
    raw = (os.environ.get('GATEWAY_UPSTREAM_TIMEOUT_SECONDS') or '').strip()
    if not raw:
        return DEFAULT_UPSTREAM_TIMEOUT_SECONDS
    try:
        return max(0.1, float(raw))
    except ValueError:
        return DEFAULT_UPSTREAM_TIMEOUT_SECONDS


def _validate_sentence(sentence: str) -> str:
    resolved = (sentence or '').strip()
    if not resolved:
        raise HTTPException(status_code=400, detail='sentence is required')
    return resolved


def _resolve_word_audio_request(word: str) -> dict[str, str]:
    raw = (word or '').strip()
    if not raw or len(raw) > 160:
        raise HTTPException(status_code=400, detail='invalid w')
    normalized = normalize_word_key(raw)
    provider, model, voice = default_word_tts_identity()
    file_name = word_tts_cache_path(Path('word_tts_cache'), normalized, model, voice).name
    return {
        'word': raw,
        'normalized_word': normalized,
        'provider': provider,
        'model': model,
        'voice': voice,
        'file_name': file_name,
    }


def _call_upstream(
    *,
    method: str,
    base_url: str,
    path: str,
    params: dict | None = None,
    json: dict | None = None,
    files=None,
) -> httpx.Response:
    try:
        with httpx.Client(timeout=_upstream_timeout_seconds()) as client:
            response = client.request(
                method,
                f'{base_url}{path}',
                params=params,
                json=json,
                files=files,
            )
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail='tts media service unavailable') from exc
    return response


def _audio_payload_from_response(response: httpx.Response) -> dict:
    return {
        'body': response.content,
        'content_type': response.headers.get('content-type', 'application/octet-stream'),
        'byte_length': response.headers.get(_AUDIO_BYTES_HEADER, ''),
        'cache_key': response.headers.get(_AUDIO_CACHE_KEY_HEADER, ''),
        'signed_url': response.headers.get(_AUDIO_OSS_URL_HEADER, ''),
        'media_id': response.headers.get(_MEDIA_ID_HEADER, ''),
    }


def fetch_word_audio_metadata(*, file_name: str, model: str, voice: str) -> dict | None:
    response = _call_upstream(
        method='GET',
        base_url=_tts_media_service_url(),
        path='/v1/media/word-audio',
        params={'file_name': file_name, 'model': model, 'voice': voice},
    )
    if response.status_code == 404:
        return None
    if response.status_code >= 400:
        raise HTTPException(status_code=502, detail='tts media service error')
    return response.json()


def fetch_word_audio_content(*, file_name: str, model: str, voice: str) -> dict | None:
    response = _call_upstream(
        method='GET',
        base_url=_tts_media_service_url(),
        path='/v1/media/word-audio/content',
        params={'file_name': file_name, 'model': model, 'voice': voice},
    )
    if response.status_code == 404:
        return None
    if response.status_code >= 400:
        raise HTTPException(status_code=502, detail='tts media service error')
    return _audio_payload_from_response(response)


def fetch_example_audio_metadata(*, sentence: str, word: str | None = None) -> dict:
    response = _call_upstream(
        method='POST',
        base_url=_tts_media_service_url(),
        path='/v1/media/example-audio/metadata',
        json={'sentence': sentence, 'word': word},
    )
    if response.status_code == 400:
        raise HTTPException(status_code=400, detail='sentence is required')
    if response.status_code >= 400:
        raise HTTPException(status_code=502, detail='tts media service error')
    return response.json()


def fetch_example_audio_content(*, sentence: str, word: str | None = None) -> dict:
    response = _call_upstream(
        method='POST',
        base_url=_tts_media_service_url(),
        path='/v1/media/example-audio/content',
        json={'sentence': sentence, 'word': word},
    )
    if response.status_code == 400:
        raise HTTPException(status_code=400, detail='sentence is required')
    if response.status_code >= 400:
        raise HTTPException(status_code=502, detail='tts media service error')
    return _audio_payload_from_response(response)


def fetch_tts_voices(*, provider: str | None = None) -> dict:
    response = _call_upstream(
        method='GET',
        base_url=_tts_media_service_url(),
        path='/v1/tts/voices',
        params={'provider': provider} if provider else None,
    )
    if response.status_code >= 400:
        raise HTTPException(status_code=502, detail='tts media service error')
    return response.json()


def generate_tts_audio(payload: dict) -> httpx.Response:
    return _call_upstream(
        method='POST',
        base_url=_tts_media_service_url(),
        path='/v1/tts/generate',
        json=payload,
    )


def transcribe_speech_upload(*, filename: str, content: bytes, content_type: str | None) -> httpx.Response:
    return _call_upstream(
        method='POST',
        base_url=_asr_service_url(),
        path='/v1/speech/transcribe',
        files={'audio': (filename, content, content_type or 'application/octet-stream')},
    )


def _apply_audio_headers(response: Response, *, byte_length: str | int | None, cache_key: str | None) -> Response:
    if byte_length not in (None, ''):
        response.headers[_AUDIO_BYTES_HEADER] = str(byte_length)
    if cache_key:
        response.headers[_AUDIO_CACHE_KEY_HEADER] = cache_key
    response.headers['Cache-Control'] = 'no-store, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Accept-Ranges'] = 'none'
    return response


def _metadata_only_response(metadata: dict, *, source: str) -> Response:
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
    response = _apply_audio_headers(
        response,
        byte_length=metadata.get('byte_length'),
        cache_key=metadata.get('cache_key'),
    )
    if metadata.get('signed_url'):
        response.headers[_AUDIO_OSS_URL_HEADER] = str(metadata['signed_url'])
    if metadata.get('media_id'):
        response.headers[_MEDIA_ID_HEADER] = str(metadata['media_id'])
    response.headers[_AUDIO_SOURCE_HEADER] = source
    return response


def _audio_content_response(payload: dict, *, source: str) -> Response:
    response = Response(payload['body'], media_type=payload['content_type'])
    response = _apply_audio_headers(
        response,
        byte_length=payload.get('byte_length'),
        cache_key=payload.get('cache_key'),
    )
    if payload.get('signed_url'):
        response.headers[_AUDIO_OSS_URL_HEADER] = str(payload['signed_url'])
    if payload.get('media_id'):
        response.headers[_MEDIA_ID_HEADER] = str(payload['media_id'])
    response.headers[_AUDIO_SOURCE_HEADER] = source
    return response


def _proxy_generic_tts_response(response: httpx.Response):
    content_type = response.headers.get('content-type', '')
    if 'application/json' in content_type:
        return JSONResponse(status_code=response.status_code, content=response.json())
    proxy = Response(response.content, status_code=response.status_code, media_type=content_type or None)
    return _apply_audio_headers(
        proxy,
        byte_length=response.headers.get(_AUDIO_BYTES_HEADER, ''),
        cache_key=response.headers.get(_AUDIO_CACHE_KEY_HEADER, ''),
    )


def _proxy_json_response(response: httpx.Response):
    content_type = response.headers.get('content-type', '')
    if 'application/json' in content_type:
        return JSONResponse(status_code=response.status_code, content=response.json())
    return Response(response.content, status_code=response.status_code, media_type=content_type or None)


app = create_service_app(
    service_name='gateway-bff',
    version='0.1.0',
    readiness_checks={
        'identity-service': make_http_readiness_check(
            base_url=identity_service_url(),
            timeout_seconds=_upstream_timeout_seconds(),
        ),
        'learning-core-service': make_http_readiness_check(
            base_url=learning_core_service_url(),
            timeout_seconds=_upstream_timeout_seconds(),
        ),
        'catalog-content-service': make_http_readiness_check(
            base_url=catalog_content_service_url(),
            timeout_seconds=_upstream_timeout_seconds(),
        ),
        'ai-execution-service': make_http_readiness_check(
            base_url=ai_execution_service_url(),
            timeout_seconds=_upstream_timeout_seconds(),
        ),
        'notes-service': make_http_readiness_check(
            base_url=notes_service_url(),
            timeout_seconds=_upstream_timeout_seconds(),
        ),
        'admin-ops-service': make_http_readiness_check(
            base_url=admin_ops_service_url(),
            timeout_seconds=_upstream_timeout_seconds(),
        ),
        'tts-media-service': make_http_readiness_check(
            base_url=_tts_media_service_url(),
            timeout_seconds=_upstream_timeout_seconds(),
        ),
        'asr-service': make_http_readiness_check(
            base_url=_asr_service_url(),
            timeout_seconds=_upstream_timeout_seconds(),
        ),
    },
    extra_health={'edge_compatibility': True},
)
app.include_router(browser_compat_router)


@app.get('/api/tts/voices')
def get_tts_voices_proxy(provider: str | None = Query(default=None)):
    return fetch_tts_voices(provider=provider)


@app.post('/api/tts/generate')
def post_tts_generate_proxy(payload: dict = Body(...)):
    return _proxy_generic_tts_response(generate_tts_audio(payload))


@app.post('/api/speech/transcribe')
def post_speech_transcribe_proxy(audio: UploadFile | None = File(default=None)):
    if audio is None:
        return JSONResponse(status_code=400, content={'error': '未收到音频文件'})
    audio.file.seek(0)
    return _proxy_json_response(
        transcribe_speech_upload(
            filename=audio.filename or 'speech-input.webm',
            content=audio.file.read(),
            content_type=audio.content_type,
        )
    )


@app.get('/api/tts/word-audio/metadata')
def get_word_audio_metadata_proxy(w: str = Query(..., min_length=1, max_length=160)):
    request_info = _resolve_word_audio_request(w)
    metadata = fetch_word_audio_metadata(
        file_name=request_info['file_name'],
        model=request_info['model'],
        voice=request_info['voice'],
    )
    if metadata is None:
        return JSONResponse(status_code=404, content={'error': 'word audio cache miss'})
    return metadata


@app.head('/api/tts/word-audio')
def head_word_audio_proxy(w: str = Query(..., min_length=1, max_length=160)):
    request_info = _resolve_word_audio_request(w)
    metadata = fetch_word_audio_metadata(
        file_name=request_info['file_name'],
        model=request_info['model'],
        voice=request_info['voice'],
    )
    return _metadata_only_response(metadata or {'cache_hit': False}, source='oss')


@app.get('/api/tts/word-audio')
def get_word_audio_proxy(
    w: str = Query(..., min_length=1, max_length=160),
    cache_only: str | None = Query(default=None),
):
    if cache_only != '1':
        return JSONResponse(
            status_code=501,
            content={'error': 'word audio generation via gateway is not implemented yet'},
        )
    request_info = _resolve_word_audio_request(w)
    payload = fetch_word_audio_content(
        file_name=request_info['file_name'],
        model=request_info['model'],
        voice=request_info['voice'],
    )
    if payload is None:
        return JSONResponse(status_code=404, content={'error': 'word audio cache miss'})
    return _audio_content_response(payload, source='oss')


@app.head('/api/tts/example-audio')
def head_example_audio_proxy(
    sentence: str = Query(..., min_length=1),
    word: str | None = Query(default=None),
):
    metadata = fetch_example_audio_metadata(sentence=_validate_sentence(sentence), word=word)
    return _metadata_only_response(metadata, source='local')


@app.get('/api/tts/example-audio')
def get_example_audio_proxy(
    sentence: str = Query(..., min_length=1),
    word: str | None = Query(default=None),
):
    payload = fetch_example_audio_content(sentence=_validate_sentence(sentence), word=word)
    return _audio_content_response(payload, source='local')


@app.post('/api/tts/example-audio')
def post_example_audio_proxy(
    payload: dict | None = Body(default=None),
    x_audio_metadata_only: str | None = Header(default=None, alias='X-Audio-Metadata-Only'),
):
    sentence = _validate_sentence(str((payload or {}).get('sentence') or ''))
    word = (payload or {}).get('word')
    if x_audio_metadata_only == '1':
        metadata = fetch_example_audio_metadata(sentence=sentence, word=word)
        return _metadata_only_response(metadata, source='local')
    return _audio_content_response(
        fetch_example_audio_content(sentence=sentence, word=word),
        source='local',
    )


if __name__ == '__main__':
    import uvicorn

    uvicorn.run(app, host='0.0.0.0', port=int(os.environ.get('GATEWAY_BFF_PORT', '8000')))
