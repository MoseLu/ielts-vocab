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
    assert 'upload-frontend-assets-to-oss.py' in build_script
    assert 'dist_payload=index-only' in build_script
    assert 'frontend_assets_uploaded_to_oss=true' in build_script
    assert '! -name index.html -exec rm -rf {} +' in build_script
    assert 'frontend_assets_uploaded_to_oss' in deploy_script
    assert 'Skipping frontend OSS upload; artifact already uploaded assets' in deploy_script
    assert 'rsync --partial --progress' in workflow
    assert "cat > '${remote_tmp}/ielts-vocab-release.tgz'" not in workflow
    assert 'artifact_upload_started=' in workflow
    assert 'FRONTEND_ASSET_OSS_PUBLIC_BASE_URL' in workflow
    assert 'FRONTEND_ASSET_OSS_PREFIX' in workflow
    assert 'FRONTEND_ASSET_OSS_CONNECT_TIMEOUT_SECONDS' in workflow
    assert 'FRONTEND_ASSET_OSS_UPLOAD_RETRY_ATTEMPTS' in workflow
    assert 'AXI_ALIYUN_OSS_ACCESS_KEY_ID' in workflow
    assert 'AXI_ALIYUN_OSS_PUBLIC_BUCKET' in workflow


def test_frontend_asset_public_header_verification_rejects_download_headers(monkeypatch):
    upload_module = _load_upload_module()
    seen_urls = []

    class FakeHeaders:
        def get(self, key, default=None):
            values = {
                'Content-Disposition': 'attachment',
                'x-oss-force-download': 'true',
            }
            return values.get(key, default)

    class FakeResponse:
        headers = FakeHeaders()

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return False

    def fake_urlopen(request, timeout):
        seen_urls.append(request.full_url)
        return FakeResponse()

    monkeypatch.setenv('FRONTEND_ASSET_BASE_URL', 'https://static.example.com/base')
    monkeypatch.setattr(upload_module.request, 'urlopen', fake_urlopen)

    try:
        upload_module.verify_public_delivery_headers([
            ('assets/index.js', 'projects/ielts-vocab/frontend-assets/assets/index.js'),
        ])
    except SystemExit as exc:
        assert 'download-style response headers' in str(exc)
    else:
        raise AssertionError('expected public header verification to fail')

    assert seen_urls == ['https://static.example.com/base/assets/index.js']


def test_frontend_asset_upload_retries_transient_put_failures(tmp_path, monkeypatch):
    upload_module = _load_upload_module()
    fake_bucket = _FakeBucket()
    attempts = {'count': 0}
    assets_dir = tmp_path / 'dist' / 'assets'
    assets_dir.mkdir(parents=True)
    (assets_dir / 'index.js').write_bytes(b'const ok = true;')
    original_put = fake_bucket.put_object

    def flaky_put(key, body, headers=None):
        attempts['count'] += 1
        if attempts['count'] == 1:
            raise RuntimeError('transient upload failure')
        return original_put(key, body, headers=headers)

    fake_bucket.put_object = flaky_put
    monkeypatch.setattr(upload_module.time, 'sleep', lambda delay: None)
    monkeypatch.setenv('FRONTEND_ASSET_OSS_ENABLED', 'true')
    monkeypatch.setenv('FRONTEND_ASSET_OSS_BUCKET_ENV', 'FRONTEND_ASSET_OSS_BUCKET')
    monkeypatch.setenv('FRONTEND_ASSET_OSS_BUCKET', 'fake-bucket')
    monkeypatch.setattr(upload_module, 'bucket_is_configured', lambda **kwargs: True)
    monkeypatch.setattr(upload_module, 'get_bucket', lambda **kwargs: fake_bucket)

    uploaded = upload_module.upload_frontend_assets(tmp_path)

    assert uploaded == 1
    assert attempts['count'] == 2


def test_frontend_asset_upload_passes_configurable_timeout_to_bucket(tmp_path, monkeypatch):
    upload_module = _load_upload_module()
    fake_bucket = _FakeBucket()
    assets_dir = tmp_path / 'dist' / 'assets'
    assets_dir.mkdir(parents=True)
    (assets_dir / 'index.js').write_bytes(b'const ok = true;')
    captured = {}

    def fake_get_bucket(**kwargs):
        captured.update(kwargs)
        return fake_bucket

    monkeypatch.setenv('FRONTEND_ASSET_OSS_ENABLED', 'true')
    monkeypatch.setenv('FRONTEND_ASSET_OSS_BUCKET_ENV', 'FRONTEND_ASSET_OSS_BUCKET')
    monkeypatch.setenv('FRONTEND_ASSET_OSS_BUCKET', 'fake-bucket')
    monkeypatch.setenv('FRONTEND_ASSET_OSS_CONNECT_TIMEOUT_SECONDS', '45')
    monkeypatch.setattr(upload_module, 'bucket_is_configured', lambda **kwargs: True)
    monkeypatch.setattr(upload_module, 'get_bucket', fake_get_bucket)

    upload_module.upload_frontend_assets(tmp_path)

    assert captured['connect_timeout'] == 45


def test_frontend_asset_upload_failure_reports_error_details(monkeypatch):
    upload_module = _load_upload_module()

    class RequestLikeError(Exception):
        status = -2
        details = 'Read timed out. (read timeout=10)'

    def always_fail(*args, **kwargs):
        raise RequestLikeError('timeout')

    monkeypatch.setattr(upload_module.time, 'sleep', lambda delay: None)
    monkeypatch.setenv('FRONTEND_ASSET_OSS_UPLOAD_RETRY_ATTEMPTS', '1')

    try:
        upload_module._put_object_with_retries(
            type('Bucket', (), {'put_object': always_fail})(),
            'assets/index.js',
            b'body',
            {},
            'assets/index.js',
        )
    except SystemExit as exc:
        message = str(exc)
    else:
        raise AssertionError('expected upload failure to raise SystemExit')

    assert 'Failed to upload frontend asset: assets/index.js' in message
    assert 'RequestLikeError' in message
    assert 'status=-2' in message
    assert 'Read timed out' in message


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
