from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

from platform_sdk.storage import (
    DEFAULT_METADATA_CACHE_TTL_SECONDS,
    DEFAULT_SIGNED_URL_EXPIRES_SECONDS,
    bucket_is_configured,
    build_service_object_key,
    env_int,
    fetch_object_payload,
    put_object_bytes,
    resolve_object_metadata,
)


DEFAULT_NOTES_EXPORT_OSS_PREFIX = 'exports'
DEFAULT_NOTES_EXPORT_SERVICE = 'notes-service'


def notes_export_oss_prefix() -> str:
    return (
        os.environ.get('NOTES_EXPORT_OSS_PREFIX', DEFAULT_NOTES_EXPORT_OSS_PREFIX).strip('/')
        or DEFAULT_NOTES_EXPORT_OSS_PREFIX
    )


def notes_export_signed_url_expires_seconds() -> int:
    return env_int(
        'NOTES_EXPORT_OSS_SIGNED_URL_EXPIRES_SECONDS',
        DEFAULT_SIGNED_URL_EXPIRES_SECONDS,
    )


def notes_export_metadata_cache_ttl_seconds() -> int:
    return env_int(
        'NOTES_EXPORT_OSS_METADATA_CACHE_TTL_SECONDS',
        DEFAULT_METADATA_CACHE_TTL_SECONDS,
    )


def notes_export_object_key(*, user_id: int, filename: str) -> str:
    return build_service_object_key(
        service_name=DEFAULT_NOTES_EXPORT_SERVICE,
        prefix=notes_export_oss_prefix(),
        segments=[f'user-{user_id}'],
        file_name=filename,
    )


def notes_export_content_type(fmt: str) -> str:
    if fmt == 'txt':
        return 'text/plain; charset=utf-8'
    return 'text/markdown; charset=utf-8'


def _signed_url_expires_at(seconds: int) -> str:
    return (datetime.now(timezone.utc) + timedelta(seconds=seconds)).isoformat()


def resolve_notes_export_metadata(*, user_id: int, filename: str):
    return resolve_object_metadata(
        object_key=notes_export_object_key(user_id=user_id, filename=filename),
        file_name=filename,
        signed_url_expires_seconds=notes_export_signed_url_expires_seconds(),
        metadata_cache_ttl_seconds=notes_export_metadata_cache_ttl_seconds(),
    )


def fetch_notes_export_payload(*, user_id: int, filename: str):
    return fetch_object_payload(
        object_key=notes_export_object_key(user_id=user_id, filename=filename),
        file_name=filename,
        signed_url_expires_seconds=notes_export_signed_url_expires_seconds(),
        metadata_cache_ttl_seconds=notes_export_metadata_cache_ttl_seconds(),
    )


def store_notes_export(*, user_id: int, filename: str, fmt: str, content: str) -> dict:
    payload = {
        'provider': None,
        'bucket_name': None,
        'object_key': None,
        'byte_length': None,
        'cache_key': None,
        'signed_url': None,
        'signed_url_expires_at': None,
    }
    if not bucket_is_configured():
        return payload

    content_bytes = content.encode('utf-8')
    metadata = put_object_bytes(
        object_key=notes_export_object_key(user_id=user_id, filename=filename),
        body=content_bytes,
        content_type=notes_export_content_type(fmt),
        signed_url_expires_seconds=notes_export_signed_url_expires_seconds(),
        metadata_cache_ttl_seconds=notes_export_metadata_cache_ttl_seconds(),
    )
    if metadata is None:
        return payload

    return {
        'provider': metadata.provider,
        'bucket_name': metadata.bucket_name,
        'object_key': metadata.object_key,
        'byte_length': metadata.byte_length,
        'cache_key': metadata.cache_key,
        'signed_url': metadata.signed_url,
        'signed_url_expires_at': _signed_url_expires_at(
            notes_export_signed_url_expires_seconds()
        ),
    }
