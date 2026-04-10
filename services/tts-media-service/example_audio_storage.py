from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

from platform_sdk.storage import (
    DEFAULT_METADATA_CACHE_TTL_SECONDS,
    DEFAULT_SIGNED_URL_EXPIRES_SECONDS,
    build_service_object_key,
    env_int,
    fetch_object_payload,
    put_object_bytes,
    resolve_object_metadata,
)


DEFAULT_EXAMPLE_AUDIO_OSS_SERVICE = 'tts-media-service'
DEFAULT_EXAMPLE_AUDIO_CONTENT_TYPE = 'audio/mpeg'


def example_audio_oss_prefix() -> str | None:
    raw = (os.environ.get('EXAMPLE_AUDIO_OSS_PREFIX') or '').strip().strip('/')
    return raw or None


def example_audio_signed_url_expires_seconds() -> int:
    return env_int(
        'EXAMPLE_AUDIO_OSS_SIGNED_URL_EXPIRES_SECONDS',
        DEFAULT_SIGNED_URL_EXPIRES_SECONDS,
    )


def example_audio_metadata_cache_ttl_seconds() -> int:
    return env_int(
        'EXAMPLE_AUDIO_OSS_METADATA_CACHE_TTL_SECONDS',
        DEFAULT_METADATA_CACHE_TTL_SECONDS,
    )


def example_audio_object_key(sentence: str, model: str, voice: str, *, example_cache_file) -> str:
    return build_service_object_key(
        service_name=DEFAULT_EXAMPLE_AUDIO_OSS_SERVICE,
        prefix=example_audio_oss_prefix(),
        segments=['example-audio', model, voice],
        file_name=example_cache_file(sentence, model, voice).name,
    )


def signed_url_expires_at(seconds: int) -> str:
    return (datetime.now(timezone.utc) + timedelta(seconds=seconds)).isoformat()


def resolve_example_audio_oss_metadata(sentence: str, model: str, voice: str, *, example_cache_file):
    return resolve_object_metadata(
        object_key=example_audio_object_key(
            sentence,
            model,
            voice,
            example_cache_file=example_cache_file,
        ),
        file_name=example_cache_file(sentence, model, voice).name,
        signed_url_expires_seconds=example_audio_signed_url_expires_seconds(),
        metadata_cache_ttl_seconds=example_audio_metadata_cache_ttl_seconds(),
    )


def fetch_example_audio_oss_payload(sentence: str, model: str, voice: str, *, example_cache_file):
    return fetch_object_payload(
        object_key=example_audio_object_key(
            sentence,
            model,
            voice,
            example_cache_file=example_cache_file,
        ),
        file_name=example_cache_file(sentence, model, voice).name,
        signed_url_expires_seconds=example_audio_signed_url_expires_seconds(),
        metadata_cache_ttl_seconds=example_audio_metadata_cache_ttl_seconds(),
    )


def put_example_audio_oss_bytes(
    sentence: str,
    model: str,
    voice: str,
    audio_bytes: bytes,
    *,
    example_cache_file,
):
    return put_object_bytes(
        object_key=example_audio_object_key(
            sentence,
            model,
            voice,
            example_cache_file=example_cache_file,
        ),
        body=audio_bytes,
        content_type=DEFAULT_EXAMPLE_AUDIO_CONTENT_TYPE,
        signed_url_expires_seconds=example_audio_signed_url_expires_seconds(),
        metadata_cache_ttl_seconds=example_audio_metadata_cache_ttl_seconds(),
    )
