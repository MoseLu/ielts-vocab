from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def _read(relative_path: str) -> str:
    return (REPO_ROOT / relative_path).read_text(encoding='utf-8')


def test_vite_supports_configurable_frontend_asset_base_url():
    config = _read('frontend/vite.config.ts')

    assert 'FRONTEND_ASSET_BASE_URL' in config
    assert 'VITE_ASSET_BASE_URL' in config
    assert 'base: resolveAssetBaseUrl()' in config


def test_release_common_uploads_frontend_assets_to_oss_after_build():
    script = _read('scripts/cloud-deploy/release-common.sh')

    assert 'upload-frontend-assets-to-oss.py' in script
    assert 'FRONTEND_ASSET_OSS_ENABLED' in script
    assert 'FRONTEND_ASSET_BASE_URL=' in script
    assert 'upload_frontend_assets_to_oss "${release_dir}"' in script


def test_nginx_template_compresses_and_caches_static_assets():
    config = _read('scripts/cloud-deploy/ielts-vocab.nginx.conf')

    assert 'gzip on;' in config
    assert 'gzip_types' in config
    assert 'location /assets/' in config
    assert 'expires 1y;' in config
    assert 'Cache-Control "public, immutable"' in config
