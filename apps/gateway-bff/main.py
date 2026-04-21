from __future__ import annotations

import os
import sys
from pathlib import Path

from fastapi import Body, File, Header, HTTPException, Query, Request, UploadFile
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
from platform_sdk.gateway_media_proxy import (
    asr_service_url as _asr_service_url,
    audio_content_response as _audio_content_response,
    fetch_example_audio_content,
    fetch_example_audio_metadata,
    fetch_follow_read_chunked_audio,
    fetch_follow_read_word,
    fetch_tts_voices,
    fetch_word_audio_content,
    fetch_word_audio_metadata,
    generate_tts_audio,
    metadata_only_response as _metadata_only_response,
    proxy_generic_tts_response as _proxy_generic_tts_response,
    proxy_json_response as _proxy_json_response,
    resolve_word_audio_request_candidates as _resolve_word_audio_request_candidates,
    resolve_word_audio_request as _resolve_word_audio_request,
    transcribe_speech_upload,
    tts_media_service_url as _tts_media_service_url,
    validate_sentence as _validate_sentence,
)
from platform_sdk.http_proxy import build_forward_headers
from platform_sdk.http_readiness import make_http_readiness_check
from platform_sdk.service_app import create_service_app

load_split_service_env(service_name='gateway-bff')


DEFAULT_UPSTREAM_TIMEOUT_SECONDS = 10.0
TRANSIENT_WORD_AUDIO_CACHE_ERROR_STATUSES = frozenset({502, 503, 504})


def _upstream_timeout_seconds() -> float:
    raw = (os.environ.get('GATEWAY_UPSTREAM_TIMEOUT_SECONDS') or '').strip()
    if not raw:
        return DEFAULT_UPSTREAM_TIMEOUT_SECONDS
    try:
        return max(0.1, float(raw))
    except ValueError:
        return DEFAULT_UPSTREAM_TIMEOUT_SECONDS


def _is_transient_word_audio_cache_error(exc: HTTPException) -> bool:
    return exc.status_code in TRANSIENT_WORD_AUDIO_CACHE_ERROR_STATUSES


def _fetch_word_audio_metadata_with_cache_fallback(
    *,
    file_name: str,
    model: str,
    voice: str,
    request: Request,
):
    try:
        return fetch_word_audio_metadata(
            file_name=file_name,
            model=model,
            voice=voice,
            headers=build_forward_headers(request, target_service_name='tts-media-service'),
        )
    except HTTPException as exc:
        if _is_transient_word_audio_cache_error(exc):
            return None
        raise


def _fetch_word_audio_content_with_cache_fallback(
    *,
    file_name: str,
    model: str,
    voice: str,
    request: Request,
):
    try:
        return fetch_word_audio_content(
            file_name=file_name,
            model=model,
            voice=voice,
            headers=build_forward_headers(request, target_service_name='tts-media-service'),
        )
    except HTTPException as exc:
        if _is_transient_word_audio_cache_error(exc):
            return None
        raise


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
def get_tts_voices_proxy(request: Request, provider: str | None = Query(default=None)):
    return fetch_tts_voices(provider=provider, headers=build_forward_headers(request, target_service_name='tts-media-service'))


@app.post('/api/tts/generate')
def post_tts_generate_proxy(request: Request, payload: dict = Body(...)):
    return _proxy_generic_tts_response(
        generate_tts_audio(payload, headers=build_forward_headers(request, target_service_name='tts-media-service'))
    )


@app.post('/api/speech/transcribe')
def post_speech_transcribe_proxy(request: Request, audio: UploadFile | None = File(default=None)):
    if audio is None:
        return JSONResponse(status_code=400, content={'error': '未收到音频文件'})
    audio.file.seek(0)
    return _proxy_json_response(
        transcribe_speech_upload(
            filename=audio.filename or 'speech-input.webm',
            content=audio.file.read(),
            content_type=audio.content_type,
            headers=build_forward_headers(request, target_service_name='asr-service'),
        )
    )


@app.get('/api/tts/word-audio/metadata')
def get_word_audio_metadata_proxy(
    request: Request,
    w: str = Query(..., min_length=1, max_length=160),
    pronunciation_mode: str | None = Query(default=None),
):
    metadata = None
    # Public word-audio is always the normal word track. Segmented/follow-read
    # playback must go through the dedicated follow-read endpoints.
    for request_info in _resolve_word_audio_request_candidates(w):
        metadata = _fetch_word_audio_metadata_with_cache_fallback(
            file_name=request_info['file_name'],
            model=request_info['model'],
            voice=request_info['voice'],
            request=request,
        )
        if metadata is not None:
            break
    if metadata is None:
        return JSONResponse(status_code=404, content={'error': 'word audio cache miss'})
    return metadata


@app.head('/api/tts/word-audio')
def head_word_audio_proxy(
    request: Request,
    w: str = Query(..., min_length=1, max_length=160),
    pronunciation_mode: str | None = Query(default=None),
):
    metadata = None
    for request_info in _resolve_word_audio_request_candidates(w):
        metadata = _fetch_word_audio_metadata_with_cache_fallback(
            file_name=request_info['file_name'],
            model=request_info['model'],
            voice=request_info['voice'],
            request=request,
        )
        if metadata is not None:
            break
    return _metadata_only_response(metadata or {'cache_hit': False}, source='oss')


@app.get('/api/tts/word-audio')
def get_word_audio_proxy(
    request: Request,
    w: str = Query(..., min_length=1, max_length=160),
    cache_only: str | None = Query(default=None),
    pronunciation_mode: str | None = Query(default=None),
    phonetic: str | None = Query(default=None),
):
    _ = pronunciation_mode, phonetic
    request_candidates = _resolve_word_audio_request_candidates(w)
    request_info = request_candidates[0]
    for candidate in request_candidates:
        payload = _fetch_word_audio_content_with_cache_fallback(
            file_name=candidate['file_name'],
            model=candidate['model'],
            voice=candidate['voice'],
            request=request,
        )
        if payload is not None:
            return _audio_content_response(payload, source='oss')
    if cache_only == '1':
        return JSONResponse(status_code=404, content={'error': 'word audio cache miss'})
    return _proxy_generic_tts_response(
        generate_tts_audio(
            {
                'text': request_info['word'],
                'provider': request_info['provider'],
                'model': request_info['model'].split('@', 1)[0],
                'voice_id': request_info['voice'],
                'content_mode': 'word',
            },
            headers=build_forward_headers(request, target_service_name='tts-media-service'),
        )
    )


@app.get('/api/tts/follow-read-word')
def get_follow_read_word_proxy(
    request: Request,
    w: str = Query(..., min_length=1, max_length=160),
    phonetic: str | None = Query(default=None),
    definition: str | None = Query(default=None),
    pos: str | None = Query(default=None),
):
    return fetch_follow_read_word(
        word=w,
        phonetic=phonetic,
        definition=definition,
        pos=pos,
        headers=build_forward_headers(request, target_service_name='tts-media-service'),
    )


@app.get('/api/tts/follow-read-chunked-audio')
def get_follow_read_chunked_audio_proxy(
    request: Request,
    w: str = Query(..., min_length=1, max_length=160),
    phonetic: str | None = Query(default=None),
):
    payload = fetch_follow_read_chunked_audio(
        word=w,
        phonetic=phonetic,
        headers=build_forward_headers(request, target_service_name='tts-media-service'),
    )
    return _audio_content_response(payload, source='local')


@app.head('/api/tts/example-audio')
def head_example_audio_proxy(
    request: Request,
    sentence: str = Query(..., min_length=1),
    word: str | None = Query(default=None),
):
    metadata = fetch_example_audio_metadata(
        sentence=_validate_sentence(sentence),
        word=word,
        headers=build_forward_headers(request, target_service_name='tts-media-service'),
    )
    return _metadata_only_response(metadata, source='local')


@app.get('/api/tts/example-audio')
def get_example_audio_proxy(
    request: Request,
    sentence: str = Query(..., min_length=1),
    word: str | None = Query(default=None),
):
    payload = fetch_example_audio_content(
        sentence=_validate_sentence(sentence),
        word=word,
        headers=build_forward_headers(request, target_service_name='tts-media-service'),
    )
    return _audio_content_response(payload, source='local')


@app.post('/api/tts/example-audio')
def post_example_audio_proxy(
    request: Request,
    payload: dict | None = Body(default=None),
    x_audio_metadata_only: str | None = Header(default=None, alias='X-Audio-Metadata-Only'),
):
    sentence = _validate_sentence(str((payload or {}).get('sentence') or ''))
    word = (payload or {}).get('word')
    if x_audio_metadata_only == '1':
        metadata = fetch_example_audio_metadata(
            sentence=sentence,
            word=word,
            headers=build_forward_headers(request, target_service_name='tts-media-service'),
        )
        return _metadata_only_response(metadata, source='local')
    return _audio_content_response(
        fetch_example_audio_content(
            sentence=sentence,
            word=word,
            headers=build_forward_headers(request, target_service_name='tts-media-service'),
        ),
        source='local',
    )


if __name__ == '__main__':
    import uvicorn

    uvicorn.run(app, host='0.0.0.0', port=int(os.environ.get('GATEWAY_BFF_PORT', '8000')))
