from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
ROLLBACK_ONLY_TTS_ADMIN_PATHS = (
    '/api/tts/admin/generate-words',
    '/api/tts/admin/word-audio-status',
    '/api/tts/books-summary',
    '/api/tts/generate/',
    '/api/tts/status/',
)


def _read(relative_path: str) -> str:
    return (REPO_ROOT / relative_path).read_text(encoding='utf-8')


def test_start_project_uses_split_runtime_as_default_backend_path():
    start_project = _read('start-project.ps1')
    start_monolith_compat = _read('start-monolith-compat.ps1')
    start_microservices = _read('start-microservices.ps1')

    assert 'start-microservices.ps1' in start_project
    assert 'AllowSharedSplitServiceSqliteServices' not in start_project
    assert 'UseMonolithCompatibility' in start_project
    assert 'MonolithCompatSurface' in start_project
    assert 'ALLOW_MONOLITH_COMPAT_RUNTIME=1' in start_project
    assert 'Gateway API:' in start_project
    assert 'start-monolith-compat.ps1' in start_project
    assert 'resolve-monolith-compat-route-groups.py' in start_project
    assert 'Compatibility surface:' in start_project
    assert 'Compatibility probe:' in start_project
    assert 'AllowDirtyCompatibilityDrill' in start_project
    assert 'MonolithCompatBackendPort = 5000' in start_project
    assert 'Write-CompatibilityDrillCodeState' in start_project
    assert 'Dirty drill override:' in start_project
    assert 'Use either -MonolithCompatRouteGroups or -MonolithCompatSurface, not both.' in start_project
    assert '$resolvedMonolithCompatProbePath = \'/api/books/stats\'' in start_project
    assert '$legacyMonolithPort = $MonolithCompatBackendPort' in start_project
    assert 'Wait-HttpReady -Url "http://127.0.0.1:$legacyMonolithPort$resolvedMonolithCompatProbePath"' in start_project
    assert 'set "BACKEND_PORT={0}"' in start_project
    assert 'set "VITE_API_PROXY_TARGET=http://127.0.0.1:{0}"' in start_project
    assert 'Legacy backend/app.py on port $legacyMonolithPort is compatibility-only.' in start_project
    assert '$gatewayPort = 8000' in start_project
    assert 'http://127.0.0.1:$gatewayPort' in start_project
    assert 'start-microservices.ps1 failed.' in start_project
    assert "'-AllowSharedSplitServiceSqliteServices'" not in start_project
    assert 'MonolithCompatSurface' in start_monolith_compat
    assert 'AllowDirtyCompatibilityDrill' in start_monolith_compat
    assert 'MonolithCompatBackendPort = 5000' in start_monolith_compat
    assert '-AllowDirtyCompatibilityDrill:$AllowDirtyCompatibilityDrill' in start_monolith_compat
    assert '-MonolithCompatBackendPort $MonolithCompatBackendPort' in start_monolith_compat
    assert 'ALLOW_SHARED_SPLIT_SERVICE_SQLITE_SERVICES' not in start_microservices
    assert 'Shared SQLite override services:' not in start_microservices
    assert 'function Stop-WorkerCommandTrees' in start_microservices
    assert "Get-CimInstance Win32_Process -Filter \"Name = 'cmd.exe'\"" in start_microservices
    assert 'Stop-WorkerCommandTrees -Definitions $workerDefinitions' in start_microservices


def test_monolith_app_archives_compatibility_runtime_outside_main_shell():
    app_source = _read('backend/app.py')
    speech_source = _read('backend/speech_service.py')
    guard_source = _read('backend/compat_runtime_guard.py')
    manifest_source = _read('backend/monolith_compat_manifest.py')
    compat_runtime = _read('backend/monolith_compat_runtime.py')

    assert 'from monolith_compat_runtime import configure_monolith_compat_runtime' in app_source
    assert 'from compat_runtime_guard import require_explicit_monolith_compat_runtime' in app_source
    assert 'from runtime_paths import ensure_shared_package_paths' in app_source
    assert 'ensure_shared_package_paths()' in app_source
    assert 'configure_monolith_compat_runtime(app, migrate=migrate)' in app_source
    assert "runtime_label='backend/app.py'" in app_source
    assert 'register_blueprint(' not in app_source
    assert 'bootstrap_monolith_schema(' not in app_source
    assert 'require_explicit_monolith_compat_runtime' in speech_source
    assert "runtime_label='backend/speech_service.py'" in speech_source
    assert "MONOLITH_COMPAT_RUNTIME_ENV = 'ALLOW_MONOLITH_COMPAT_RUNTIME'" in guard_source
    assert 'MONOLITH_COMPAT_ROUTE_GROUPS' in manifest_source
    assert 'resolve_enabled_monolith_compat_route_groups' in manifest_source
    assert 'describe_monolith_compat_route_groups' in manifest_source
    assert 'def register_monolith_compat_blueprints' in compat_runtime
    assert 'def configure_monolith_compat_runtime' in compat_runtime
    assert 'for group in resolve_enabled_monolith_compat_route_groups():' in compat_runtime


def test_vite_and_nginx_proxy_api_traffic_through_gateway_bff():
    vite_config = _read('frontend/vite.config.ts')
    nginx_config = _read('nginx.conf.example')

    assert "const API_PROXY_TARGET = process.env.VITE_API_PROXY_TARGET?.trim() || 'http://127.0.0.1:8000'" in vite_config
    assert 'const SPEECH_PROXY_TARGET =' in vite_config
    assert 'function buildProxyConfig()' in vite_config
    assert 'proxy: buildProxyConfig()' in vite_config
    assert 'http://localhost:5000' not in vite_config
    assert (
        'proxy_pass         http://127.0.0.1:8000;' in nginx_config
        or 'proxy_pass         http://ielts_gateway_bff;' in nginx_config
    )
    assert 'http://127.0.0.1:5000' not in nginx_config


def test_playwright_no_longer_boots_the_legacy_monolith_runtime():
    playwright_config = _read('frontend/playwright.config.ts')

    assert 'python app.py' not in playwright_config
    assert 'http://127.0.0.1:5000' not in playwright_config
    assert 'pnpm dev -- --host 127.0.0.1 --port 3020' in playwright_config


def test_rollback_only_tts_admin_surface_stays_out_of_browser_code_paths():
    gateway_source = _read('apps/gateway-bff/main.py')
    frontend_sources = '\n'.join(
        path.read_text(encoding='utf-8')
        for path in (REPO_ROOT / 'frontend' / 'src').rglob('*')
        if path.is_file() and path.suffix in {'.ts', '.tsx', '.js', '.jsx', '.scss', '.css'}
    )

    for raw_path in ROLLBACK_ONLY_TTS_ADMIN_PATHS:
        assert raw_path not in gateway_source
        assert raw_path not in frontend_sources
