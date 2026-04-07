from __future__ import annotations

import os
import re
import threading
import time
from dataclasses import dataclass

import oss2
from oss2 import exceptions as oss_exceptions


SAFE_OSS_SEGMENT_RE = re.compile(r'[^a-z0-9]+')
DEFAULT_WORD_TTS_OSS_PREFIX = 'projects/ielts-vocab/word-tts-cache'
DEFAULT_SIGNED_URL_EXPIRES_SECONDS = 3600
DEFAULT_METADATA_CACHE_TTL_SECONDS = 300


@dataclass(frozen=True)
class WordAudioOssMetadata:
    byte_length: int | None
    cache_key: str | None
    signed_url: str


@dataclass(frozen=True)
class WordAudioOssPayload:
    audio_bytes: bytes
    byte_length: int
    cache_key: str | None
    signed_url: str
    content_type: str


_CLIENT_LOCK = threading.Lock()
_METADATA_CACHE_LOCK = threading.Lock()
_OSS_BUCKET: oss2.Bucket | None = None
_OSS_BUCKET_SIGNATURE: tuple[str, str, str, str, str] | None = None
_WORD_AUDIO_METADATA_CACHE: dict[str, tuple[float, WordAudioOssMetadata | None]] = {}


def _env_int(name: str, default: int) -> int:
    raw = (os.environ.get(name) or '').strip()
    if not raw:
        return default
    try:
        return max(1, int(raw))
    except ValueError:
        return default


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
    access_key_id = (os.environ.get('AXI_ALIYUN_OSS_ACCESS_KEY_ID') or '').strip()
    access_key_secret = (os.environ.get('AXI_ALIYUN_OSS_ACCESS_KEY_SECRET') or '').strip()
    bucket_name = (os.environ.get('AXI_ALIYUN_OSS_PRIVATE_BUCKET') or '').strip()
    region = (os.environ.get('AXI_ALIYUN_OSS_REGION') or '').strip()
    endpoint = (os.environ.get('AXI_ALIYUN_OSS_ENDPOINT') or '').strip()
    if not access_key_id or not access_key_secret or not bucket_name or not region:
        return None
    return access_key_id, access_key_secret, bucket_name, region, endpoint


def _build_endpoint(region: str, endpoint: str) -> str:
    resolved = endpoint.strip()
    if resolved:
        if resolved.startswith(('http://', 'https://')):
            return resolved
        return f'https://{resolved}'
    return f'https://{region}.aliyuncs.com'


def _normalize_bucket_region(region: str) -> str:
    resolved = region.strip()
    return resolved[4:] if resolved.startswith('oss-') else resolved


def _build_bucket() -> oss2.Bucket | None:
    signature = _bucket_signature()
    if signature is None:
        return None

    access_key_id, access_key_secret, bucket_name, region, endpoint = signature
    bucket_region = _normalize_bucket_region(region)
    security_token = (os.environ.get('AXI_ALIYUN_OSS_STS_TOKEN') or '').strip()
    auth = (
        oss2.StsAuth(access_key_id, access_key_secret, security_token, auth_version='v4')
        if security_token
        else oss2.AuthV4(access_key_id, access_key_secret)
    )
    return oss2.Bucket(
        auth,
        _build_endpoint(region, endpoint),
        bucket_name,
        region=bucket_region,
        connect_timeout=10,
    )


def _oss_bucket() -> oss2.Bucket | None:
    global _OSS_BUCKET, _OSS_BUCKET_SIGNATURE

    signature = _bucket_signature()
    if signature is None:
        return None

    with _CLIENT_LOCK:
        if _OSS_BUCKET is not None and _OSS_BUCKET_SIGNATURE == signature:
            return _OSS_BUCKET
        _OSS_BUCKET = _build_bucket()
        _OSS_BUCKET_SIGNATURE = signature
        return _OSS_BUCKET


def word_audio_oss_object_key(*, file_name: str, model: str, voice: str) -> str:
    identity = f'{model}--{voice}'
    identity_segment = SAFE_OSS_SEGMENT_RE.sub('-', identity.lower()).strip('-') or 'default'
    prefix = _word_tts_oss_prefix()
    if prefix:
        return f'{prefix}/{identity_segment}/{file_name}'
    return f'{identity_segment}/{file_name}'


def _cache_key_for_object(
    file_name: str,
    byte_length: int | None,
    etag: str | None,
    last_modified: str | None,
) -> str:
    fingerprint = etag or last_modified or 'unknown'
    size = byte_length if isinstance(byte_length, int) and byte_length > 0 else 0
    return f'oss:{file_name}:{size}:{fingerprint}'


def _read_object_metadata(
    bucket: oss2.Bucket,
    object_key: str,
    *,
    file_name: str,
) -> WordAudioOssMetadata | None:
    try:
        meta = bucket.get_object_meta(object_key)
    except (oss_exceptions.NoSuchKey, oss_exceptions.NotFound):
        return None
    except Exception:
        return None

    headers = getattr(meta, 'headers', {}) or {}
    raw_length = headers.get('Content-Length') or headers.get('content-length')
    try:
        byte_length = int(raw_length) if raw_length else None
    except (TypeError, ValueError):
        byte_length = None
    etag = (headers.get('ETag') or headers.get('etag') or '').strip('"') or None
    last_modified = headers.get('Last-Modified') or headers.get('last-modified')
    signed_url = bucket.sign_url(
        'GET',
        object_key,
        _signed_url_expires_seconds(),
        slash_safe=True,
    )
    return WordAudioOssMetadata(
        byte_length=byte_length,
        cache_key=_cache_key_for_object(file_name, byte_length, etag, last_modified),
        signed_url=signed_url,
    )


def _signed_url_for_object(bucket: oss2.Bucket, object_key: str) -> str:
    return bucket.sign_url(
        'GET',
        object_key,
        _signed_url_expires_seconds(),
        slash_safe=True,
    )


def _cache_metadata(
    *,
    object_key: str,
    metadata: WordAudioOssMetadata | None,
) -> None:
    expires_at = time.time() + _metadata_cache_ttl_seconds()
    cache_key = f'{object_key}|{_signed_url_expires_seconds()}'
    with _METADATA_CACHE_LOCK:
        _WORD_AUDIO_METADATA_CACHE[cache_key] = (expires_at, metadata)


def _payload_from_object(
    bucket: oss2.Bucket,
    object_key: str,
    *,
    file_name: str,
) -> WordAudioOssPayload | None:
    try:
        obj = bucket.get_object(object_key)
    except (oss_exceptions.NoSuchKey, oss_exceptions.NotFound):
        _cache_metadata(object_key=object_key, metadata=None)
        return None
    except Exception:
        return None

    try:
        audio_bytes = obj.read()
    except Exception:
        return None
    if not audio_bytes:
        return None

    headers = getattr(obj, 'headers', {}) or {}
    raw_length = headers.get('Content-Length') or headers.get('content-length')
    try:
        byte_length = int(raw_length) if raw_length else len(audio_bytes)
    except (TypeError, ValueError):
        byte_length = len(audio_bytes)
    byte_length = byte_length if byte_length > 0 else len(audio_bytes)
    etag = (headers.get('ETag') or headers.get('etag') or '').strip('"') or None
    last_modified = headers.get('Last-Modified') or headers.get('last-modified')
    content_type = (headers.get('Content-Type') or headers.get('content-type') or 'audio/mpeg').strip() or 'audio/mpeg'
    signed_url = _signed_url_for_object(bucket, object_key)
    metadata = WordAudioOssMetadata(
        byte_length=byte_length,
        cache_key=_cache_key_for_object(file_name, byte_length, etag, last_modified),
        signed_url=signed_url,
    )
    _cache_metadata(object_key=object_key, metadata=metadata)
    return WordAudioOssPayload(
        audio_bytes=audio_bytes,
        byte_length=len(audio_bytes),
        cache_key=metadata.cache_key,
        signed_url=signed_url,
        content_type=content_type,
    )


def resolve_word_audio_oss_metadata(
    *,
    file_name: str,
    model: str,
    voice: str,
) -> WordAudioOssMetadata | None:
    bucket = _oss_bucket()
    if bucket is None:
        return None

    object_key = word_audio_oss_object_key(file_name=file_name, model=model, voice=voice)
    cache_key = f'{object_key}|{_signed_url_expires_seconds()}'
    now = time.time()

    with _METADATA_CACHE_LOCK:
        cached = _WORD_AUDIO_METADATA_CACHE.get(cache_key)
        if cached and cached[0] > now:
            return cached[1]

    metadata = _read_object_metadata(bucket, object_key, file_name=file_name)
    expires_at = now + _metadata_cache_ttl_seconds()
    with _METADATA_CACHE_LOCK:
        _WORD_AUDIO_METADATA_CACHE[cache_key] = (expires_at, metadata)
    return metadata


def fetch_word_audio_oss_payload(
    *,
    file_name: str,
    model: str,
    voice: str,
) -> WordAudioOssPayload | None:
    bucket = _oss_bucket()
    if bucket is None:
        return None

    object_key = word_audio_oss_object_key(file_name=file_name, model=model, voice=voice)
    return _payload_from_object(bucket, object_key, file_name=file_name)
