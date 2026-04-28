#!/usr/bin/env python3
from __future__ import annotations

import argparse
import mimetypes
import os
from pathlib import Path

from dotenv import load_dotenv

from platform_sdk.storage import bucket_is_configured, join_object_key, put_object_bytes


DEFAULT_PREFIX = 'projects/ielts-vocab/frontend-assets'
TRUTHY = {'1', 'true', 'yes', 'on'}
FALSY = {'', '0', 'false', 'no', 'off'}


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


def upload_frontend_assets(release_dir: Path) -> int:
    if not _enabled():
        print('[frontend-assets] OSS upload skipped: FRONTEND_ASSET_OSS_ENABLED is off')
        return 0
    bucket_env = _bucket_env()
    if not bucket_is_configured(bucket_env=bucket_env):
        raise SystemExit(f'Frontend asset OSS upload enabled but bucket env is incomplete: {bucket_env}')

    dist_dir = release_dir / 'dist'
    assets_dir = dist_dir / 'assets'
    if not assets_dir.is_dir():
        raise SystemExit(f'Missing frontend assets directory: {assets_dir}')

    uploaded = 0
    for file_path in sorted(path for path in assets_dir.rglob('*') if path.is_file()):
        relative_path = file_path.relative_to(dist_dir).as_posix()
        object_key = join_object_key(prefix=_prefix(), file_name=relative_path)
        body = file_path.read_bytes()
        metadata = put_object_bytes(
            object_key=object_key,
            body=body,
            content_type=_content_type(file_path),
            bucket_env=bucket_env,
        )
        if metadata is None:
            raise SystemExit(f'Failed to upload frontend asset: {relative_path}')
        uploaded += 1
    print(f'[frontend-assets] uploaded={uploaded} prefix={_prefix()} bucket_env={bucket_env}')
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
