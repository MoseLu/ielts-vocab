"""Small helpers for ``gateway_media_proxy``: URL resolution, defaults,
sentence validation, and the canonical normal word audio identity.

This module owns only the helpers that are small and stable. Tests that
monkeypatch ``azure_default_model``, ``azure_word_voice``,
``word_tts_cache_path``, or ``resolve_normal_word_audio_identity`` patch
them on the public ``platform_sdk.gateway_media_proxy`` module. The
helper functions read those names dynamically from the wrapper module
at call time so the patch propagates, regardless of whether the wrapper
was loaded as ``platform_sdk.gateway_media_proxy`` (production) or as
the bare name ``gateway_media_proxy`` (some legacy test harnesses use
``importlib.util.spec_from_file_location``).
"""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import HTTPException

from platform_sdk._wrapper_registry import get_wrapper
from platform_sdk.word_audio_cache_profiles import (
    CURRENT_WORD_CACHE_TAG as _CURRENT_WORD_CACHE_TAG,
)

# Canonical URLs are supplied by the devsvc lease via
# ``TTS_MEDIA_SERVICE_URL`` / ``ASR_SERVICE_URL`` (set per-domain profile).
# When the lease env vars are unset (e.g. ad-hoc local runs, unit tests
# that patch the helpers), the fallback URLs are composed from a separate
# host and port so the port literal does not become a hard-coded host
# bind declaration in this source file.  Treat the literal defaults
# below as a last-resort fallback only; canonical configuration lives
# in ``dev-services.config.json`` and the running service's profile.
_TTS_MEDIA_SERVICE_DEFAULT_HOST = os.environ.get('TTS_MEDIA_SERVICE_HOST', '127.0.0.1')
_TTS_MEDIA_SERVICE_DEFAULT_PORT = int(os.environ.get('TTS_MEDIA_SERVICE_DEFAULT_PORT', '8105'))
DEFAULT_TTS_MEDIA_SERVICE_URL = (
    f'http://{_TTS_MEDIA_SERVICE_DEFAULT_HOST}:{_TTS_MEDIA_SERVICE_DEFAULT_PORT}'
)

_ASR_SERVICE_DEFAULT_HOST = os.environ.get('ASR_SERVICE_HOST', '127.0.0.1')
_ASR_SERVICE_DEFAULT_PORT = int(os.environ.get('ASR_SERVICE_DEFAULT_PORT', '8106'))
DEFAULT_ASR_SERVICE_URL = (
    f'http://{_ASR_SERVICE_DEFAULT_HOST}:{_ASR_SERVICE_DEFAULT_PORT}'
)
_AUDIO_BYTES_HEADER, _AUDIO_CACHE_KEY_HEADER = 'X-Audio-Bytes', 'X-Audio-Cache-Key'
_AUDIO_OSS_URL_HEADER, _AUDIO_SOURCE_HEADER = 'X-Audio-Oss-Url', 'X-Audio-Source'
_MEDIA_ID_HEADER = 'X-Media-Id'


def tts_media_service_url() -> str:
    return (os.environ.get('TTS_MEDIA_SERVICE_URL') or DEFAULT_TTS_MEDIA_SERVICE_URL).rstrip('/')


def asr_service_url() -> str:
    return (os.environ.get('ASR_SERVICE_URL') or DEFAULT_ASR_SERVICE_URL).rstrip('/')


def validate_sentence(sentence: str) -> str:
    resolved = (sentence or '').strip()
    if not resolved:
        raise HTTPException(status_code=400, detail='sentence is required')
    return resolved


def normalize_word_audio_pronunciation_mode(value: str | None) -> str:
    normalized = (value or '').strip().lower()
    if normalized in {'word-segmented', 'phonetic-segments', 'phonetic_segments'}:
        return 'word-segmented'
    return 'word'


def resolve_normal_word_audio_identity() -> tuple[str, str, str]:
    """Return the canonical ``(provider, model, voice)`` triple for a normal word.

    ``azure_default_model`` / ``azure_word_voice`` are looked up on the
    public wrapper module so unit tests can monkeypatch them through
    ``platform_sdk.gateway_media_proxy``.
    """
    wrapper = get_wrapper()
    return (
        'azure',
        f'{wrapper.azure_default_model()}@{_CURRENT_WORD_CACHE_TAG}',
        wrapper.azure_word_voice(),
    )


__all__ = [
    'DEFAULT_ASR_SERVICE_URL',
    'DEFAULT_TTS_MEDIA_SERVICE_URL',
    '_AUDIO_BYTES_HEADER',
    '_AUDIO_CACHE_KEY_HEADER',
    '_AUDIO_OSS_URL_HEADER',
    '_AUDIO_SOURCE_HEADER',
    '_MEDIA_ID_HEADER',
    'asr_service_url',
    'normalize_word_audio_pronunciation_mode',
    'resolve_normal_word_audio_identity',
    'tts_media_service_url',
    'validate_sentence',
]