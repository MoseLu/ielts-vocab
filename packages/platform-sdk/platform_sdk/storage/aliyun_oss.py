from __future__ import annotations

import hashlib
import os
import re
import threading
import time
from dataclasses import dataclass

import oss2
from oss2 import exceptions as oss_exceptions


SAFE_OSS_SEGMENT_RE = re.compile(r'[^a-z0-9]+')
DEFAULT_SIGNED_URL_EXPIRES_SECONDS = 3600
DEFAULT_METADATA_CACHE_TTL_SECONDS = 300
DEFAULT_CONNECT_TIMEOUT_SECONDS = 10

_CLIENT_LOCK = threading.Lock()
_METADATA_CACHE_LOCK = threading.Lock()
_OSS_BUCKETS: dict[tuple[str, str, str, str, str], oss2.Bucket] = {}
_OBJECT_METADATA_CACHE: dict[str, tuple[float, "StoredObjectMetadata | None"]] = {}


@dataclass(frozen=True)
class StoredObjectMetadata:
    provider: str
    bucket_name: str
    object_key: str
    byte_length: int | None
    content_type: str | None
    cache_key: str | None
    signed_url: str


@dataclass(frozen=True)
class StoredObjectPayload:
    provider: str
    bucket_name: str
    object_key: str
    body: bytes
    byte_length: int
    content_type: str
    cache_key: str | None
    signed_url: str


def env_int(name: str, default: int) -> int:
    raw = (os.environ.get(name) or '').strip()
    if not raw:
        return default
    try:
        return max(1, int(raw))
    except ValueError:
        return default


def sanitize_segment(value: str) -> str:
    cleaned = SAFE_OSS_SEGMENT_RE.sub('-', (value or '').strip().lower()).strip('-')
    return cleaned or 'default'


def join_object_key(*, prefix: str | None = None, segments: list[str] | tuple[str, ...] = (), file_name: str) -> str:
    path_parts = [part.strip('/') for part in ([prefix] if prefix else []) if part and part.strip('/')]
    path_parts.extend(part.strip('/') for part in segments if part and part.strip('/'))
    path_parts.append(file_name.lstrip('/'))
    return '/'.join(path_parts)


def build_service_object_key(
    *,
    service_name: str,
    file_name: str,
    segments: list[str] | tuple[str, ...] = (),
    prefix: str | None = None,
) -> str:
    normalized_segments = [sanitize_segment(service_name), *[sanitize_segment(part) for part in segments]]
    return join_object_key(prefix=prefix, segments=normalized_segments, file_name=file_name)


def build_endpoint(region: str, endpoint: str) -> str:
    resolved = endpoint.strip()
    if resolved:
        if resolved.startswith(('http://', 'https://')):
            return resolved
        return f'https://{resolved}'
    return f'https://{region}.aliyuncs.com'


def normalize_bucket_region(region: str) -> str:
    resolved = region.strip()
    return resolved[4:] if resolved.startswith('oss-') else resolved


def bucket_signature_from_env(
    *,
    access_key_id_env: str = 'AXI_ALIYUN_OSS_ACCESS_KEY_ID',
    access_key_secret_env: str = 'AXI_ALIYUN_OSS_ACCESS_KEY_SECRET',
    bucket_env: str = 'AXI_ALIYUN_OSS_PRIVATE_BUCKET',
    region_env: str = 'AXI_ALIYUN_OSS_REGION',
    endpoint_env: str = 'AXI_ALIYUN_OSS_ENDPOINT',
) -> tuple[str, str, str, str, str] | None:
    access_key_id = (os.environ.get(access_key_id_env) or '').strip()
    access_key_secret = (os.environ.get(access_key_secret_env) or '').strip()
    bucket_name = (os.environ.get(bucket_env) or '').strip()
    region = (os.environ.get(region_env) or '').strip()
    endpoint = (os.environ.get(endpoint_env) or '').strip()
    if not access_key_id or not access_key_secret or not bucket_name or not region:
        return None
    return access_key_id, access_key_secret, bucket_name, region, endpoint


def bucket_is_configured(**kwargs) -> bool:
    return bucket_signature_from_env(**kwargs) is not None


def build_bucket_from_env(
    *,
    access_key_id_env: str = 'AXI_ALIYUN_OSS_ACCESS_KEY_ID',
    access_key_secret_env: str = 'AXI_ALIYUN_OSS_ACCESS_KEY_SECRET',
    bucket_env: str = 'AXI_ALIYUN_OSS_PRIVATE_BUCKET',
    region_env: str = 'AXI_ALIYUN_OSS_REGION',
    endpoint_env: str = 'AXI_ALIYUN_OSS_ENDPOINT',
    sts_token_env: str = 'AXI_ALIYUN_OSS_STS_TOKEN',
    connect_timeout: int = DEFAULT_CONNECT_TIMEOUT_SECONDS,
) -> oss2.Bucket | None:
    signature = bucket_signature_from_env(
        access_key_id_env=access_key_id_env,
        access_key_secret_env=access_key_secret_env,
        bucket_env=bucket_env,
        region_env=region_env,
        endpoint_env=endpoint_env,
    )
    if signature is None:
        return None

    access_key_id, access_key_secret, bucket_name, region, endpoint = signature
    security_token = (os.environ.get(sts_token_env) or '').strip()
    auth = (
        oss2.StsAuth(access_key_id, access_key_secret, security_token, auth_version='v4')
        if security_token
        else oss2.AuthV4(access_key_id, access_key_secret)
    )
    return oss2.Bucket(
        auth,
        build_endpoint(region, endpoint),
        bucket_name,
        region=normalize_bucket_region(region),
        connect_timeout=connect_timeout,
    )


def get_bucket(
    *,
    access_key_id_env: str = 'AXI_ALIYUN_OSS_ACCESS_KEY_ID',
    access_key_secret_env: str = 'AXI_ALIYUN_OSS_ACCESS_KEY_SECRET',
    bucket_env: str = 'AXI_ALIYUN_OSS_PRIVATE_BUCKET',
    region_env: str = 'AXI_ALIYUN_OSS_REGION',
    endpoint_env: str = 'AXI_ALIYUN_OSS_ENDPOINT',
    sts_token_env: str = 'AXI_ALIYUN_OSS_STS_TOKEN',
    connect_timeout: int = DEFAULT_CONNECT_TIMEOUT_SECONDS,
) -> oss2.Bucket | None:
    signature = bucket_signature_from_env(
        access_key_id_env=access_key_id_env,
        access_key_secret_env=access_key_secret_env,
        bucket_env=bucket_env,
        region_env=region_env,
        endpoint_env=endpoint_env,
    )
    if signature is None:
        return None

    cache_key = (*signature, sts_token_env)
    with _CLIENT_LOCK:
        bucket = _OSS_BUCKETS.get(cache_key)
        if bucket is not None:
            return bucket
        bucket = build_bucket_from_env(
            access_key_id_env=access_key_id_env,
            access_key_secret_env=access_key_secret_env,
            bucket_env=bucket_env,
            region_env=region_env,
            endpoint_env=endpoint_env,
            sts_token_env=sts_token_env,
            connect_timeout=connect_timeout,
        )
        if bucket is not None:
            _OSS_BUCKETS[cache_key] = bucket
        return bucket


def _cache_key_for_object(
    *,
    file_name: str,
    byte_length: int | None,
    etag: str | None,
    last_modified: str | None,
) -> str:
    fingerprint = etag or last_modified or 'unknown'
    size = byte_length if isinstance(byte_length, int) and byte_length > 0 else 0
    return f'oss:{file_name}:{size}:{fingerprint}'


def _metadata_cache_key(object_key: str, signed_url_expires_seconds: int) -> str:
    return f'{object_key}|{signed_url_expires_seconds}'


def clear_cached_metadata(*, object_key: str | None = None) -> None:
    with _METADATA_CACHE_LOCK:
        if object_key is None:
            _OBJECT_METADATA_CACHE.clear()
            return
        for key in [candidate for candidate in _OBJECT_METADATA_CACHE if candidate.startswith(f'{object_key}|')]:
            _OBJECT_METADATA_CACHE.pop(key, None)


def _signed_url(bucket: oss2.Bucket, object_key: str, expires_seconds: int) -> str:
    return bucket.sign_url('GET', object_key, expires_seconds, slash_safe=True)


def _resolved_bucket_name(bucket: oss2.Bucket, bucket_env: str) -> str:
    bucket_name = getattr(bucket, 'bucket_name', None)
    if isinstance(bucket_name, str) and bucket_name.strip():
        return bucket_name
    return (os.environ.get(bucket_env) or '').strip()


def resolve_object_metadata(
    *,
    object_key: str,
    file_name: str | None = None,
    bucket: oss2.Bucket | None = None,
    bucket_env: str = 'AXI_ALIYUN_OSS_PRIVATE_BUCKET',
    signed_url_expires_seconds: int = DEFAULT_SIGNED_URL_EXPIRES_SECONDS,
    metadata_cache_ttl_seconds: int = DEFAULT_METADATA_CACHE_TTL_SECONDS,
) -> StoredObjectMetadata | None:
    bucket = bucket or get_bucket(bucket_env=bucket_env)
    if bucket is None:
        return None

    cache_key = _metadata_cache_key(object_key, signed_url_expires_seconds)
    now = time.time()
    with _METADATA_CACHE_LOCK:
        cached = _OBJECT_METADATA_CACHE.get(cache_key)
        if cached and cached[0] > now:
            return cached[1]

    try:
        meta = bucket.get_object_meta(object_key)
    except (oss_exceptions.NoSuchKey, oss_exceptions.NotFound):
        metadata = None
    except Exception:
        metadata = None
    else:
        headers = getattr(meta, 'headers', {}) or {}
        raw_length = headers.get('Content-Length') or headers.get('content-length')
        try:
            byte_length = int(raw_length) if raw_length else None
        except (TypeError, ValueError):
            byte_length = None
        content_type = (headers.get('Content-Type') or headers.get('content-type') or '').strip() or None
        etag = (headers.get('ETag') or headers.get('etag') or '').strip('"') or None
        last_modified = headers.get('Last-Modified') or headers.get('last-modified')
        object_missing = False
        if content_type is None:
            get_object_result = None
            try:
                get_object_result = bucket.get_object(object_key)
            except (oss_exceptions.NoSuchKey, oss_exceptions.NotFound):
                object_missing = True
            except Exception:
                get_object_result = None
            else:
                get_headers = getattr(get_object_result, 'headers', {}) or {}
                get_raw_length = get_headers.get('Content-Length') or get_headers.get('content-length')
                try:
                    byte_length = int(get_raw_length) if get_raw_length else byte_length
                except (TypeError, ValueError):
                    pass
                content_type = (get_headers.get('Content-Type') or get_headers.get('content-type') or '').strip() or None
                etag = etag or (get_headers.get('ETag') or get_headers.get('etag') or '').strip('"') or None
                last_modified = last_modified or get_headers.get('Last-Modified') or get_headers.get('last-modified')
            finally:
                close = getattr(get_object_result, 'close', None)
                if callable(close):
                    close()
        if object_missing:
            with _METADATA_CACHE_LOCK:
                _OBJECT_METADATA_CACHE[cache_key] = (now + metadata_cache_ttl_seconds, None)
            return None
        metadata = StoredObjectMetadata(
            provider='aliyun-oss',
            bucket_name=_resolved_bucket_name(bucket, bucket_env),
            object_key=object_key,
            byte_length=byte_length,
            content_type=content_type,
            cache_key=_cache_key_for_object(
                file_name=file_name or object_key.rsplit('/', 1)[-1],
                byte_length=byte_length,
                etag=etag,
                last_modified=last_modified,
            ),
            signed_url=_signed_url(bucket, object_key, signed_url_expires_seconds),
        )

    with _METADATA_CACHE_LOCK:
        _OBJECT_METADATA_CACHE[cache_key] = (now + metadata_cache_ttl_seconds, metadata)
    return metadata


def fetch_object_payload(
    *,
    object_key: str,
    file_name: str | None = None,
    bucket: oss2.Bucket | None = None,
    bucket_env: str = 'AXI_ALIYUN_OSS_PRIVATE_BUCKET',
    signed_url_expires_seconds: int = DEFAULT_SIGNED_URL_EXPIRES_SECONDS,
    metadata_cache_ttl_seconds: int = DEFAULT_METADATA_CACHE_TTL_SECONDS,
) -> StoredObjectPayload | None:
    bucket = bucket or get_bucket(bucket_env=bucket_env)
    if bucket is None:
        return None

    try:
        obj = bucket.get_object(object_key)
    except (oss_exceptions.NoSuchKey, oss_exceptions.NotFound):
        clear_cached_metadata(object_key=object_key)
        return None
    except Exception:
        return None

    try:
        body = obj.read()
    except Exception:
        return None
    if not body:
        return None

    headers = getattr(obj, 'headers', {}) or {}
    raw_length = headers.get('Content-Length') or headers.get('content-length')
    try:
        byte_length = int(raw_length) if raw_length else len(body)
    except (TypeError, ValueError):
        byte_length = len(body)
    content_type = (headers.get('Content-Type') or headers.get('content-type') or 'application/octet-stream').strip()
    etag = (headers.get('ETag') or headers.get('etag') or '').strip('"') or None
    last_modified = headers.get('Last-Modified') or headers.get('last-modified')
    payload = StoredObjectPayload(
        provider='aliyun-oss',
        bucket_name=_resolved_bucket_name(bucket, bucket_env),
        object_key=object_key,
        body=body,
        byte_length=byte_length,
        content_type=content_type,
        cache_key=_cache_key_for_object(
            file_name=file_name or object_key.rsplit('/', 1)[-1],
            byte_length=byte_length,
            etag=etag,
            last_modified=last_modified,
        ),
        signed_url=_signed_url(bucket, object_key, signed_url_expires_seconds),
    )
    with _METADATA_CACHE_LOCK:
        _OBJECT_METADATA_CACHE[_metadata_cache_key(object_key, signed_url_expires_seconds)] = (
            time.time() + metadata_cache_ttl_seconds,
            StoredObjectMetadata(
                provider=payload.provider,
                bucket_name=payload.bucket_name,
                object_key=payload.object_key,
                byte_length=payload.byte_length,
                content_type=payload.content_type,
                cache_key=payload.cache_key,
                signed_url=payload.signed_url,
            ),
        )
    return payload


def put_object_bytes(
    *,
    object_key: str,
    body: bytes,
    content_type: str,
    bucket: oss2.Bucket | None = None,
    bucket_env: str = 'AXI_ALIYUN_OSS_PRIVATE_BUCKET',
    signed_url_expires_seconds: int = DEFAULT_SIGNED_URL_EXPIRES_SECONDS,
    metadata_cache_ttl_seconds: int = DEFAULT_METADATA_CACHE_TTL_SECONDS,
) -> StoredObjectMetadata | None:
    bucket = bucket or get_bucket(bucket_env=bucket_env)
    if bucket is None:
        return None

    headers = {'Content-Type': content_type}
    try:
        result = bucket.put_object(object_key, body, headers=headers)
    except Exception:
        return None

    etag = getattr(result, 'etag', None) or getattr(result, 'crc', None)
    metadata = StoredObjectMetadata(
        provider='aliyun-oss',
        bucket_name=_resolved_bucket_name(bucket, bucket_env),
        object_key=object_key,
        byte_length=len(body),
        content_type=content_type,
        cache_key=_cache_key_for_object(
            file_name=object_key.rsplit('/', 1)[-1],
            byte_length=len(body),
            etag=str(etag) if etag else hashlib.md5(body).hexdigest(),
            last_modified=None,
        ),
        signed_url=_signed_url(bucket, object_key, signed_url_expires_seconds),
    )
    with _METADATA_CACHE_LOCK:
        _OBJECT_METADATA_CACHE[_metadata_cache_key(object_key, signed_url_expires_seconds)] = (
            time.time() + metadata_cache_ttl_seconds,
            metadata,
        )
    return metadata


def delete_object(
    *,
    object_key: str,
    bucket: oss2.Bucket | None = None,
    bucket_env: str = 'AXI_ALIYUN_OSS_PRIVATE_BUCKET',
    missing_ok: bool = True,
) -> bool:
    bucket = bucket or get_bucket(bucket_env=bucket_env)
    if bucket is None:
        return False

    try:
        bucket.delete_object(object_key)
    except (oss_exceptions.NoSuchKey, oss_exceptions.NotFound):
        if not missing_ok:
            return False
    except Exception:
        return False

    clear_cached_metadata(object_key=object_key)
    return True
