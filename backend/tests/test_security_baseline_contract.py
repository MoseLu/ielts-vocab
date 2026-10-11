from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SECURITY_HEADERS = (
    'add_header Content-Security-Policy ',
    'add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;',
    'add_header X-Frame-Options "DENY" always;',
    'add_header X-Content-Type-Options "nosniff" always;',
    'add_header Referrer-Policy "strict-origin-when-cross-origin" always;',
    'add_header Permissions-Policy ',
    'add_header Cross-Origin-Opener-Policy "same-origin" always;',
)


def _read(relative_path: str) -> str:
    return (REPO_ROOT / relative_path).read_text(encoding='utf-8')


def _location_block(config: str, marker: str) -> str:
    start = config.index(marker)
    next_location = config.find('\n    location ', start + len(marker))
    if next_location == -1:
        return config[start:]
    return config[start:next_location]


def test_cloud_nginx_template_sets_browser_security_headers():
    config = _read('scripts/cloud-deploy/ielts-vocab.nginx.conf')

    assert 'server_tokens off;' in config
    for header in SECURITY_HEADERS:
        assert header in config
    assert "default-src 'self'" in config
    assert "object-src 'none'" in config
    assert "frame-ancestors 'none'" in config
    assert "script-src 'self'" in config
    assert "connect-src 'self' https: wss:" in config
    assert 'upgrade-insecure-requests' in config


def test_cloud_nginx_repeats_security_headers_in_cache_header_locations():
    config = _read('scripts/cloud-deploy/ielts-vocab.nginx.conf')

    for marker in ('location /assets/ {', 'location = /index.html {', 'location / {'):
        block = _location_block(config, marker)
        assert 'add_header Cache-Control ' in block
        for header in SECURITY_HEADERS:
            assert header in block


def test_local_nginx_example_keeps_dev_socket_support_with_same_security_baseline():
    config = _read('nginx.conf.example')

    assert 'server_tokens off;' in config
    for header in SECURITY_HEADERS:
        assert header in config
    assert "connect-src 'self' http: https: ws: wss:" in config
    assert 'proxy_pass         http://127.0.0.1:8000;' in config
    assert 'proxy_pass         http://127.0.0.1:5001/socket.io/;' in config
