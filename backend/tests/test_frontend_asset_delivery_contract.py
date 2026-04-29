from __future__ import annotations

import gzip
import importlib.util
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def _read(relative_path: str) -> str:
    return (REPO_ROOT / relative_path).read_text(encoding='utf-8')


def _load_upload_module():
    module_path = REPO_ROOT / 'scripts/upload-frontend-assets-to-oss.py'
    spec = importlib.util.spec_from_file_location('upload_frontend_assets_to_oss', module_path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class _FakeBucket:
    def __init__(self):
        self.objects = {}

    def put_object(self, key, body, headers=None):
        self.objects[key] = {'body': body, 'headers': headers or {}}

    def get_object_meta(self, key):
        return self.objects[key]


def test_frontend_asset_upload_gzips_text_assets(tmp_path, monkeypatch):
    upload_module = _load_upload_module()
    fake_bucket = _FakeBucket()
    assets_dir = tmp_path / 'dist' / 'assets'
    assets_dir.mkdir(parents=True)
    js_body = b'const message = "hello";\n' * 80
    css_body = b'.app { color: #123456; }\n' * 80
    (assets_dir / 'index.js').write_bytes(js_body)
    (assets_dir / 'index.css').write_bytes(css_body)

    monkeypatch.setenv('FRONTEND_ASSET_OSS_ENABLED', 'true')
    monkeypatch.setenv('FRONTEND_ASSET_OSS_BUCKET_ENV', 'FRONTEND_ASSET_OSS_BUCKET')
    monkeypatch.setenv('FRONTEND_ASSET_OSS_BUCKET', 'fake-bucket')
    monkeypatch.setattr(upload_module, 'bucket_is_configured', lambda **kwargs: True)
    monkeypatch.setattr(upload_module, 'get_bucket', lambda **kwargs: fake_bucket)

    uploaded = upload_module.upload_frontend_assets(tmp_path)

    assert uploaded == 2
    js_object = fake_bucket.objects['projects/ielts-vocab/frontend-assets/assets/index.js']
    css_object = fake_bucket.objects['projects/ielts-vocab/frontend-assets/assets/index.css']
    assert js_object['headers']['Content-Encoding'] == 'gzip'
    assert css_object['headers']['Content-Encoding'] == 'gzip'
    assert js_object['headers']['Content-Disposition'] == 'inline; filename="index.js"'
    assert css_object['headers']['Content-Disposition'] == 'inline; filename="index.css"'
    assert gzip.decompress(js_object['body']) == js_body
    assert gzip.decompress(css_object['body']) == css_body


def test_frontend_asset_upload_includes_prd_ui_templates(tmp_path, monkeypatch):
    upload_module = _load_upload_module()
    fake_bucket = _FakeBucket()
    template_dir = tmp_path / 'dist' / 'ui' / 'templates'
    template_dir.mkdir(parents=True)
    template_body = b'fake-png-body'
    (template_dir / 'word-chain-map-text-safe.png').write_bytes(template_body)
    (tmp_path / 'dist' / 'index.html').write_text('<html></html>', encoding='utf-8')

    monkeypatch.setenv('FRONTEND_ASSET_OSS_ENABLED', 'true')
    monkeypatch.setenv('FRONTEND_ASSET_OSS_BUCKET_ENV', 'FRONTEND_ASSET_OSS_BUCKET')
    monkeypatch.setenv('FRONTEND_ASSET_OSS_BUCKET', 'fake-bucket')
    monkeypatch.setattr(upload_module, 'bucket_is_configured', lambda **kwargs: True)
    monkeypatch.setattr(upload_module, 'get_bucket', lambda **kwargs: fake_bucket)

    uploaded = upload_module.upload_frontend_assets(tmp_path)

    assert uploaded == 1
    assert 'projects/ielts-vocab/frontend-assets/index.html' not in fake_bucket.objects
    ui_object = fake_bucket.objects[
        'projects/ielts-vocab/frontend-assets/ui/templates/word-chain-map-text-safe.png'
    ]
    assert ui_object['body'] == template_body
    assert ui_object['headers']['x-oss-object-acl'] == 'public-read'
    assert ui_object['headers']['Content-Disposition'] == (
        'inline; filename="word-chain-map-text-safe.png"'
    )


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


def test_release_artifact_path_builds_with_and_uploads_oss_assets():
    build_script = _read('scripts/cloud-deploy/build-release-artifact.sh')
    deploy_script = _read('scripts/cloud-deploy/deploy-release-artifact.sh')
    workflow = _read('.github/workflows/deploy-production.yml')

    assert 'resolve_frontend_asset_base' in build_script
    assert 'FRONTEND_ASSET_BASE_URL="${asset_base}"' in build_script
    assert 'VITE_ASSET_BASE_URL="${asset_base}"' in build_script
    assert 'frontend_asset_base_url=${asset_base}' in build_script
    assert 'rm -rf "${stage_dir}/.git" "${stage_dir}/node_modules" "${stage_dir}/frontend"' in build_script
    assert 'upload_frontend_assets_to_oss "${release_dir}"' in deploy_script
    assert 'FRONTEND_ASSET_OSS_PUBLIC_BASE_URL' in workflow
    assert 'FRONTEND_ASSET_OSS_PREFIX' in workflow


def test_frontend_asset_upload_marks_objects_public_read():
    script = _read('scripts/upload-frontend-assets-to-oss.py')

    assert 'FRONTEND_ASSET_OSS_OBJECT_ACL' in script
    assert "'public-read'" in script
    assert "'x-oss-object-acl'" in script
    assert 'bucket.put_object' in script


def test_nginx_template_compresses_and_caches_static_assets():
    config = _read('scripts/cloud-deploy/ielts-vocab.nginx.conf')

    assert 'gzip on;' in config
    assert 'gzip_types' in config
    assert 'location /assets/' in config
    assert 'expires 1y;' in config
    assert 'Cache-Control "public, immutable"' in config
