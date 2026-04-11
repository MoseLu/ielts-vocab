from __future__ import annotations

import os
from dataclasses import dataclass

from runtime_paths import ensure_shared_package_paths

ensure_shared_package_paths()

from platform_sdk.storage import aliyun_oss as shared_oss


oss2 = shared_oss.oss2
oss_exceptions = shared_oss.oss_exceptions
SAFE_OSS_SEGMENT_RE = shared_oss.SAFE_OSS_SEGMENT_RE
DEFAULT_SIGNED_URL_EXPIRES_SECONDS = shared_oss.DEFAULT_SIGNED_URL_EXPIRES_SECONDS
DEFAULT_METADATA_CACHE_TTL_SECONDS = shared_oss.DEFAULT_METADATA_CACHE_TTL_SECONDS
DEFAULT_WORD_TTS_OSS_PREFIX = 'projects/ielts-vocab/word-tts-cache'
DEFAULT_WORD_AUDIO_CONTENT_TYPE = 'audio/mpeg'


@dataclass(frozen=True)
class WordAudioOssMetadata:
    provider: str
    bucket_name: str
    object_key: str
    byte_length: int | None
    content_type: str | None
    cache_key: str | None
    signed_url: str


@dataclass(frozen=True)
class WordAudioOssPayload:
    provider: str
    bucket_name: str
    object_key: str
    audio_bytes: bytes
    byte_length: int
    content_type: str
    cache_key: str | None
    signed_url: str

    @property
    def body(self) -> bytes:
        return self.audio_bytes


def _env_int(name: str, default: int) -> int:
    return shared_oss.env_int(name, default)


def _word_tts_oss_prefix() -> str:
    return (
        os.environ.get('WORD_TTS_OSS_PREFIX', DEFAULT_WORD_TTS_OSS_PREFIX).strip('/')
        or DEFAULT_WORD_TTS_OSS_PREFIX
    )


def _signed_url_expires_seconds() -> int:
    return _env_int(
        'WORD_TTS_OSS_SIGNED_URL_EXPIRES_SECONDS',
        DEFAULT_SIGNED_URL_EXPIRES_SECONDS,
    )


def _metadata_cache_ttl_seconds() -> int:
    return _env_int(
        'WORD_TTS_OSS_METADATA_CACHE_TTL_SECONDS',
        DEFAULT_METADATA_CACHE_TTL_SECONDS,
    )


def _bucket_signature() -> tuple[str, str, str, str, str] | None:
    return shared_oss.bucket_signature_from_env()


def _build_endpoint(region: str, endpoint: str) -> str:
    return shared_oss.build_endpoint(region, endpoint)


def _normalize_bucket_region(region: str) -> str:
    return shared_oss.normalize_bucket_region(region)


def _build_bucket():
    return shared_oss.build_bucket_from_env()


def _oss_bucket():
    return shared_oss.get_bucket()


def _metadata_from_shared(metadata: shared_oss.StoredObjectMetadata | None) -> WordAudioOssMetadata | None:
    if metadata is None:
        return None
    return WordAudioOssMetadata(
        provider=metadata.provider,
        bucket_name=metadata.bucket_name,
        object_key=metadata.object_key,
        byte_length=metadata.byte_length,
        content_type=metadata.content_type,
        cache_key=metadata.cache_key,
        signed_url=metadata.signed_url,
    )


def _payload_from_shared(payload: shared_oss.StoredObjectPayload | None) -> WordAudioOssPayload | None:
    if payload is None:
        return None
    return WordAudioOssPayload(
        provider=payload.provider,
        bucket_name=payload.bucket_name,
        object_key=payload.object_key,
        audio_bytes=payload.body,
        byte_length=payload.byte_length,
        content_type=payload.content_type,
        cache_key=payload.cache_key,
        signed_url=payload.signed_url,
    )


def word_audio_oss_object_key(*, file_name: str, model: str, voice: str) -> str:
    identity = f'{model}--{voice}'
    identity_segment = SAFE_OSS_SEGMENT_RE.sub('-', identity.lower()).strip('-') or 'default'
    return shared_oss.join_object_key(
        prefix=_word_tts_oss_prefix(),
        segments=[identity_segment],
        file_name=file_name,
    )


def _cache_key_for_object(
    file_name: str,
    byte_length: int | None,
    etag: str | None,
    last_modified: str | None,
) -> str:
    return shared_oss._cache_key_for_object(
        file_name=file_name,
        byte_length=byte_length,
        etag=etag,
        last_modified=last_modified,
    )


def resolve_word_audio_oss_metadata(
    *,
    file_name: str,
    model: str,
    voice: str,
) -> WordAudioOssMetadata | None:
    return _metadata_from_shared(
        shared_oss.resolve_object_metadata(
            object_key=word_audio_oss_object_key(file_name=file_name, model=model, voice=voice),
            file_name=file_name,
            bucket=_oss_bucket(),
            signed_url_expires_seconds=_signed_url_expires_seconds(),
            metadata_cache_ttl_seconds=_metadata_cache_ttl_seconds(),
        )
    )


def fetch_word_audio_oss_payload(
    *,
    file_name: str,
    model: str,
    voice: str,
) -> WordAudioOssPayload | None:
    return _payload_from_shared(
        shared_oss.fetch_object_payload(
            object_key=word_audio_oss_object_key(file_name=file_name, model=model, voice=voice),
            file_name=file_name,
            bucket=_oss_bucket(),
            signed_url_expires_seconds=_signed_url_expires_seconds(),
            metadata_cache_ttl_seconds=_metadata_cache_ttl_seconds(),
        )
    )


def put_word_audio_oss_bytes(
    *,
    file_name: str,
    model: str,
    voice: str,
    audio_bytes: bytes,
) -> WordAudioOssMetadata | None:
    return _metadata_from_shared(
        shared_oss.put_object_bytes(
            object_key=word_audio_oss_object_key(file_name=file_name, model=model, voice=voice),
            body=audio_bytes,
            content_type=DEFAULT_WORD_AUDIO_CONTENT_TYPE,
            bucket=_oss_bucket(),
            signed_url_expires_seconds=_signed_url_expires_seconds(),
            metadata_cache_ttl_seconds=_metadata_cache_ttl_seconds(),
        )
    )
