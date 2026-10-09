"""Backward-compatible public surface for the gateway media proxy helpers.

Historically this file was a single 500+ line module. It is now a thin
wrapper that re-exports the public API while the actual implementation
lives in three smaller submodules:

* ``_helpers`` — small URL / validation / canonical-identity helpers
* ``_resolution`` — word audio request and candidate resolution
* ``_proxy`` — HTTP upstream proxy core, fetch wrappers, response builders

The split keeps ``from platform_sdk.gateway_media_proxy import X``
working for every public name and preserves test monkeypatching on
this module for ``azure_default_model``, ``azure_word_voice``,
``word_tts_cache_path``, ``resolve_normal_word_audio_identity``,
``phonetic_identity``, and ``httpx``: the wrapper owns those names and
the implementation submodules read them dynamically through the
wrapper at call time.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import httpx

from platform_sdk import word_audio_phonetic_identity as phonetic_identity
from platform_sdk.word_tts_runtime_adapter import (
    normalize_word_key as _normalize_word_key,
    word_tts_cache_path,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_PATH = REPO_ROOT / 'backend'
if str(BACKEND_PATH) not in sys.path:
    sys.path.insert(0, str(BACKEND_PATH))

from services.word_tts import azure_default_model, azure_word_voice  # noqa: E402

# Implementation submodules. They read monkeypatchable names
# (``azure_default_model`` / ``azure_word_voice`` / ``word_tts_cache_path``
# / ``resolve_normal_word_audio_identity`` / ``phonetic_identity`` /
# ``httpx``) from this module at call time via
# ``platform_sdk._wrapper_registry.get_wrapper()`` so the patch
# propagates regardless of how this module was loaded.
from platform_sdk._helpers import (  # noqa: E402,F401
    DEFAULT_ASR_SERVICE_URL,
    DEFAULT_TTS_MEDIA_SERVICE_URL,
    asr_service_url,
    normalize_word_audio_pronunciation_mode,
    resolve_normal_word_audio_identity,
    tts_media_service_url,
    validate_sentence,
)
from platform_sdk._resolution import (  # noqa: E402,F401
    resolve_word_audio_request,
    resolve_word_audio_request_candidates,
)
from platform_sdk._proxy import (  # noqa: E402,F401
    apply_audio_headers,
    audio_content_response,
    audio_payload_from_response,
    call_media_upstream,
    fetch_example_audio_content,
    fetch_example_audio_metadata,
    fetch_follow_read_chunked_audio,
    fetch_follow_read_word,
    fetch_tts_voices,
    fetch_word_audio_content,
    fetch_word_audio_metadata,
    generate_tts_audio,
    metadata_only_response,
    proxy_generic_tts_response,
    proxy_json_response,
    transcribe_speech_upload,
)
from platform_sdk._wrapper_registry import set_wrapper  # noqa: E402

# Register this module so the implementation submodules can look it up.
# Must run last so all re-exported names are already bound.
# Use ``globals()`` so the binding works regardless of how the module
# was loaded (production ``sys.modules[name]`` or legacy
# ``importlib.util.spec_from_file_location`` without registration).
set_wrapper(globals())

__all__ = [
    'DEFAULT_ASR_SERVICE_URL',
    'DEFAULT_TTS_MEDIA_SERVICE_URL',
    'apply_audio_headers',
    'asr_service_url',
    'audio_content_response',
    'audio_payload_from_response',
    'azure_default_model',
    'azure_word_voice',
    'call_media_upstream',
    'fetch_example_audio_content',
    'fetch_example_audio_metadata',
    'fetch_follow_read_chunked_audio',
    'fetch_follow_read_word',
    'fetch_tts_voices',
    'fetch_word_audio_content',
    'fetch_word_audio_metadata',
    'generate_tts_audio',
    'httpx',
    'metadata_only_response',
    'normalize_word_audio_pronunciation_mode',
    'phonetic_identity',
    'proxy_generic_tts_response',
    'proxy_json_response',
    'resolve_normal_word_audio_identity',
    'resolve_word_audio_request',
    'resolve_word_audio_request_candidates',
    'transcribe_speech_upload',
    'tts_media_service_url',
    'validate_sentence',
    'word_tts_cache_path',
]