#!/usr/bin/env python3
from __future__ import annotations

import argparse
import gzip
import hashlib
import mimetypes
import os
import time
from pathlib import Path
from urllib import request
from urllib.error import URLError

from dotenv import load_dotenv
from oss2 import exceptions as oss_exceptions

from platform_sdk.storage import bucket_is_configured, env_int, get_bucket, join_object_key


DEFAULT_PREFIX = 'projects/ielts-vocab/frontend-assets'
GZIP_SUFFIXES = {'.css', '.js', '.json', '.svg'}
TRUTHY = {'1', 'true', 'yes', 'on'}
FALSY = {'', '0', 'false', 'no', 'off'}
PUBLIC_HEADER_VERIFY_LIMIT = 12
DEFAULT_UPLOAD_RETRY_ATTEMPTS = 4
DEFAULT_CONNECT_TIMEOUT_SECONDS = 60
CONTENT_SHA256_META_HEADER = 'x-oss-meta-sha256'
FRONTEND_ASSET_CACHE_CONTROL = 'public, max-age=31536000, immutable'


def _enabled() -> bool:
    raw = (os.environ.get('FRONTEND_ASSET_OSS_ENABLED') or '').strip().lower()
    if raw in TRUTHY:
        return True
    if raw in FALSY:
        return False
    raise SystemExit(f'Invalid FRONTEND_ASSET_OSS_ENABLED value: {raw}')


def _load_env(path: str | None, *, override: bool) -> None:
    if not path:
        return
    env_path = Path(path)
    if env_path.exists():
        load_dotenv(env_path, override=override)


def _content_type(path: Path) -> str:
    guessed, _ = mimetypes.guess_type(path.name)
    if guessed:
        return guessed
    if path.suffix == '.js':
        return 'application/javascript'
    if path.suffix == '.css':
        return 'text/css'
    return 'application/octet-stream'


def _prefix() -> str:
    return (os.environ.get('FRONTEND_ASSET_OSS_PREFIX') or DEFAULT_PREFIX).strip().strip('/')


def _bucket_env() -> str:
    return (os.environ.get('FRONTEND_ASSET_OSS_BUCKET_ENV') or 'AXI_ALIYUN_OSS_PUBLIC_BUCKET').strip()


def _object_acl() -> str:
    return (os.environ.get('FRONTEND_ASSET_OSS_OBJECT_ACL') or 'public-read').strip()


def _connect_timeout_seconds() -> int:
    return env_int('FRONTEND_ASSET_OSS_CONNECT_TIMEOUT_SECONDS', DEFAULT_CONNECT_TIMEOUT_SECONDS)


def _upload_retry_attempts() -> int:
    return env_int('FRONTEND_ASSET_OSS_UPLOAD_RETRY_ATTEMPTS', DEFAULT_UPLOAD_RETRY_ATTEMPTS)


def _public_base_url() -> str:
    configured_asset_base = (
        os.environ.get('FRONTEND_ASSET_BASE_URL')
        or os.environ.get('VITE_ASSET_BASE_URL')
        or ''
    ).strip()
    if configured_asset_base:
        return configured_asset_base.rstrip('/')
    public_bucket_base = (os.environ.get('FRONTEND_ASSET_OSS_PUBLIC_BASE_URL') or '').strip().rstrip('/')
    prefix = _prefix()
    if public_bucket_base and prefix:
        return f'{public_bucket_base}/{prefix}'
    return public_bucket_base


def _verify_public_headers_enabled() -> bool:
    raw = (os.environ.get('FRONTEND_ASSET_OSS_VERIFY_PUBLIC_HEADERS') or 'true').strip().lower()
    if raw in TRUTHY:
        return True
    if raw in FALSY:
        return False
    raise SystemExit(f'Invalid FRONTEND_ASSET_OSS_VERIFY_PUBLIC_HEADERS value: {raw}')


def _public_asset_url(relative_path: str) -> str:
    public_base = _public_base_url()
    return f'{public_base}/{relative_path.lstrip("/")}'


def _prepared_body_and_headers(path: Path, body: bytes) -> tuple[bytes, dict[str, str]]:
    headers = {
        'Content-Type': _content_type(path),
        'Content-Disposition': f'inline; filename="{path.name}"',
        'Cache-Control': FRONTEND_ASSET_CACHE_CONTROL,
    }
    if path.suffix.lower() in GZIP_SUFFIXES:
        headers['Content-Encoding'] = 'gzip'
        prepared_body = gzip.compress(body, compresslevel=9, mtime=0)
    else:
        prepared_body = body
    headers[CONTENT_SHA256_META_HEADER] = hashlib.sha256(prepared_body).hexdigest()
    return prepared_body, headers


def _retry_delay_seconds(attempt: int) -> float:
    return min(8.0, 1.5 * attempt)


def _exception_summary(exc: Exception | None) -> str:
    if exc is None:
        return 'type=<unknown>'
    parts = [f'type={type(exc).__name__}']
    for attr in ('status', 'code', 'request_id', 'details'):
        value = getattr(exc, attr, None)
        if value not in (None, ''):
            parts.append(f'{attr}={value}')
    message = str(exc).strip()
    if message:
        parts.append(f'message={message}')
    return ' '.join(parts)


def _metadata_headers(meta) -> dict:
    if isinstance(meta, dict):
        return dict(meta.get('headers') or {})
    return dict(getattr(meta, 'headers', {}) or {})


def _header_value(headers: dict, name: str) -> str:
    direct = headers.get(name)
    if direct is not None:
        return str(direct).strip()
    lowered = name.lower()
    for key, value in headers.items():
        if str(key).lower() == lowered:
            return str(value).strip()
    return ''


def _same_header_value(left: str, right: str) -> bool:
    return left.strip().lower() == right.strip().lower()


def _remote_body_matches(headers: dict, body: bytes) -> bool:
    raw_length = _header_value(headers, 'Content-Length')
    try:
        if raw_length and int(raw_length) != len(body):
            return False
    except ValueError:
        return False

    remote_sha256 = _header_value(headers, CONTENT_SHA256_META_HEADER)
    if remote_sha256:
        return remote_sha256.lower() == hashlib.sha256(body).hexdigest()

    remote_etag = _header_value(headers, 'ETag').strip('"').lower()
    if remote_etag:
        return remote_etag == hashlib.md5(body).hexdigest()
    return False


def _remote_headers_match(remote_headers: dict, desired_headers: dict[str, str]) -> bool:
    for header_name in ('Content-Type', 'Content-Disposition', 'Cache-Control', 'Content-Encoding'):
        desired_value = desired_headers.get(header_name, '')
        remote_value = _header_value(remote_headers, header_name)
        if desired_value:
            if not remote_value or not _same_header_value(remote_value, desired_value):
                return False
        elif remote_value:
            return False
    remote_sha256 = _header_value(remote_headers, CONTENT_SHA256_META_HEADER)
    desired_sha256 = desired_headers.get(CONTENT_SHA256_META_HEADER, '')
    return not remote_sha256 or _same_header_value(remote_sha256, desired_sha256)


def _get_existing_object_meta(bucket, object_key: str, relative_path: str):
    last_exc: Exception | None = None
    retry_attempts = _upload_retry_attempts()
    for attempt in range(1, retry_attempts + 1):
        try:
            return bucket.get_object_meta(object_key)
        except (KeyError, oss_exceptions.NoSuchKey, oss_exceptions.NotFound):
            return None
        except Exception as exc:
            last_exc = exc
            if attempt >= retry_attempts:
                break
            delay = _retry_delay_seconds(attempt)
            print(
                f'[frontend-assets] meta_lookup_retry path={relative_path} attempt={attempt} '
                f'delay={delay:.1f}s error={_exception_summary(exc)}',
                flush=True,
            )
            time.sleep(delay)
    print(
        f'[frontend-assets] meta_lookup_failed path={relative_path} '
        f'error={_exception_summary(last_exc)}; falling back to upload',
        flush=True,
    )
    return None


def _remote_object_matches(bucket, object_key: str, body: bytes, headers: dict[str, str], relative_path: str) -> bool:
    meta = _get_existing_object_meta(bucket, object_key, relative_path)
    if meta is None:
        return False
    remote_headers = _metadata_headers(meta)
    return _remote_body_matches(remote_headers, body) and _remote_headers_match(remote_headers, headers)


def _put_object_with_retries(bucket, object_key: str, body: bytes, headers: dict[str, str], relative_path: str) -> None:
    last_exc: Exception | None = None
    retry_attempts = _upload_retry_attempts()
    for attempt in range(1, retry_attempts + 1):
        try:
            bucket.put_object(object_key, body, headers=headers)
            return
        except Exception as exc:
            last_exc = exc
            if attempt >= retry_attempts:
                break
            delay = _retry_delay_seconds(attempt)
            print(
                f'[frontend-assets] upload_retry path={relative_path} attempt={attempt} '
                f'delay={delay:.1f}s error={_exception_summary(exc)}',
                flush=True,
            )
            time.sleep(delay)
    raise SystemExit(
        f'Failed to upload frontend asset: {relative_path}; {_exception_summary(last_exc)}'
    ) from last_exc


def _verify_object_meta_with_retries(bucket, object_key: str, relative_path: str) -> None:
    last_exc: Exception | None = None
    retry_attempts = _upload_retry_attempts()
    for attempt in range(1, retry_attempts + 1):
        try:
            bucket.get_object_meta(object_key)
            return
        except Exception as exc:
            last_exc = exc
            if attempt >= retry_attempts:
                break
            delay = _retry_delay_seconds(attempt)
            print(
                f'[frontend-assets] meta_retry path={relative_path} attempt={attempt} '
                f'delay={delay:.1f}s error={_exception_summary(exc)}',
                flush=True,
            )
            time.sleep(delay)
    raise SystemExit(
        'Failed to verify uploaded frontend asset metadata: '
        f'{relative_path}; {_exception_summary(last_exc)}'
    ) from last_exc


def _selected_header_check_assets(uploaded_assets: list[tuple[str, str]]) -> list[tuple[str, str]]:
    selected: list[tuple[str, str]] = []
    suffix_groups = (
        ('.js',),
        ('.css',),
        ('.png', '.jpg', '.jpeg', '.webp', '.svg'),
    )
    for suffixes in suffix_groups:
        match = next(
            (
                item
                for item in uploaded_assets
                if item[0].lower().endswith(suffixes)
            ),
            None,
        )
        if match is not None:
            selected.append(match)
    if not selected and uploaded_assets:
        selected.append(uploaded_assets[0])
    return selected[:PUBLIC_HEADER_VERIFY_LIMIT]


def verify_public_delivery_headers(uploaded_assets: list[tuple[str, str]]) -> None:
    public_base = _public_base_url()
    if not public_base:
        print('[frontend-assets] public header verification skipped: FRONTEND_ASSET_OSS_PUBLIC_BASE_URL is empty', flush=True)
        return
    if not _verify_public_headers_enabled():
        print('[frontend-assets] public header verification skipped: FRONTEND_ASSET_OSS_VERIFY_PUBLIC_HEADERS is off', flush=True)
        return

    checked = 0
    for relative_path, object_key in _selected_header_check_assets(uploaded_assets):
        url = _public_asset_url(relative_path)
        try:
            with request.urlopen(request.Request(url, method='HEAD'), timeout=10) as response:
                content_disposition = (response.headers.get('Content-Disposition') or '').lower()
                cache_control = (response.headers.get('Cache-Control') or '').lower()
                force_download = (response.headers.get('x-oss-force-download') or '').lower()
        except URLError as exc:
            raise SystemExit(f'Failed to verify frontend asset public headers: {relative_path}') from exc
        if 'attachment' in content_disposition or force_download == 'true':
            raise SystemExit(
                'Frontend OSS asset has download-style response headers: '
                f'relative_path={relative_path} object_key={object_key} '
                f'content_disposition={content_disposition or "<empty>"} '
                f'x_oss_force_download={force_download or "<empty>"}'
            )
        if 'max-age=' not in cache_control or 'immutable' not in cache_control:
            raise SystemExit(
                'Frontend OSS asset is missing long-lived immutable cache headers: '
                f'relative_path={relative_path} object_key={object_key} '
                f'cache_control={cache_control or "<empty>"}'
            )
        checked += 1
    print(f'[frontend-assets] public_header_checked={checked} public_base={public_base}', flush=True)


def upload_frontend_assets(release_dir: Path) -> int:
    if not _enabled():
        print('[frontend-assets] OSS upload skipped: FRONTEND_ASSET_OSS_ENABLED is off', flush=True)
        return 0
    bucket_env = _bucket_env()
    if not bucket_is_configured(bucket_env=bucket_env):
        raise SystemExit(f'Frontend asset OSS upload enabled but bucket env is incomplete: {bucket_env}')
    connect_timeout = _connect_timeout_seconds()
    bucket = get_bucket(bucket_env=bucket_env, connect_timeout=connect_timeout)
    if bucket is None:
        raise SystemExit(f'Failed to create frontend asset OSS bucket client: {bucket_env}')

    dist_dir = release_dir / 'dist'
    if not dist_dir.is_dir():
        raise SystemExit(f'Missing frontend dist directory: {dist_dir}')

    checked_assets: list[tuple[str, str]] = []
    files = sorted(
        path
        for path in dist_dir.rglob('*')
        if path.is_file() and path.name != 'index.html' and not path.name.startswith('.')
    )
    total = len(files)
    total_bytes = sum(path.stat().st_size for path in files)
    uploaded_bytes = 0
    skipped_bytes = 0
    skipped = 0
    print(
        f'[frontend-assets] upload_start files={total} bytes={total_bytes} '
        f'prefix={_prefix()} connect_timeout={connect_timeout} '
        f'retry_attempts={_upload_retry_attempts()}',
        flush=True,
    )
    for index, file_path in enumerate(files, start=1):
        relative_path = file_path.relative_to(dist_dir).as_posix()
        object_key = join_object_key(prefix=_prefix(), file_name=relative_path)
        body = file_path.read_bytes()
        body, headers = _prepared_body_and_headers(file_path, body)
        object_acl = _object_acl()
        if object_acl:
            headers['x-oss-object-acl'] = object_acl
        file_size = file_path.stat().st_size
        if _remote_object_matches(bucket, object_key, body, headers, relative_path):
            print(
                f'[frontend-assets] skip_file index={index}/{total} '
                f'size={file_size} path={relative_path}',
                flush=True,
            )
            skipped += 1
            skipped_bytes += file_size
            checked_assets.append((relative_path, object_key))
            continue
        print(
            f'[frontend-assets] upload_file index={index}/{total} '
            f'size={file_size} path={relative_path}',
            flush=True,
        )
        _put_object_with_retries(bucket, object_key, body, headers, relative_path)
        _verify_object_meta_with_retries(bucket, object_key, relative_path)
        uploaded_bytes += file_size
        checked_assets.append((relative_path, object_key))
    verify_public_delivery_headers(checked_assets)
    uploaded = len(checked_assets) - skipped
    print(
        f'[frontend-assets] uploaded={uploaded} bytes={uploaded_bytes} '
        f'skipped={skipped} skipped_bytes={skipped_bytes} '
        f'prefix={_prefix()} bucket_env={bucket_env} acl={_object_acl() or "default"}',
        flush=True,
    )
    return uploaded


def main() -> int:
    parser = argparse.ArgumentParser(description='Upload built frontend assets to Aliyun OSS.')
    parser.add_argument('release_dir', help='Release directory containing dist/assets')
    parser.add_argument('--backend-env-file', default=os.environ.get('BACKEND_ENV_FILE'))
    parser.add_argument('--env-file', default=os.environ.get('MICROSERVICES_ENV_FILE'))
    args = parser.parse_args()

    _load_env(args.backend_env_file, override=False)
    _load_env(args.env_file, override=True)
    upload_frontend_assets(Path(args.release_dir))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
