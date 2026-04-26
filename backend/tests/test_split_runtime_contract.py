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
    start_project = _read('start-project.sh')
    start_monolith_compat = _read('start-monolith-compat.sh')
    start_microservices = _read('start-microservices.sh')

    assert 'start-microservices.sh' in start_project
    assert 'ALLOW_SHARED_SPLIT_SERVICE_SQLITE_SERVICES' not in start_project
    assert '--use-monolith-compatibility' in start_project
    assert '--monolith-compat-surface' in start_project
    assert 'ALLOW_MONOLITH_COMPAT_RUNTIME=1' in start_project
    assert 'Gateway API:' in start_project
    assert 'start-monolith-compat.sh' in start_project
    assert 'resolve-monolith-compat-route-groups.py' in start_project
    assert '--allow-dirty-compatibility-drill' in start_project
    assert '--monolith-compat-backend-port' in start_project
    assert '--skip-frontend-build' in start_project
    assert 'Use either --monolith-compat-route-groups or --monolith-compat-surface, not both.' in start_project
    assert "python -c 'import json, sys; print(json.load(sys.stdin)[\"probe_path\"])'" in start_project
    assert "python - <<'PY'" not in start_project
    assert 'http://127.0.0.1:${monolith_compat_backend_port}' in start_project
    assert 'http://127.0.0.1:${gateway_port}' in start_project
    assert 'Legacy backend/app.py on port ${monolith_compat_backend_port} is compatibility-only.' in start_project
    assert 'pnpm --dir "${root}/frontend" build' in start_project
    assert 'node "${root}/frontend/node_modules/vite/bin/vite.js" preview' in start_project
    assert '--use-monolith-compatibility' in start_monolith_compat
    assert 'start-project.sh' in start_monolith_compat
    assert 'ALLOW_SHARED_SPLIT_SERVICE_SQLITE_SERVICES' not in start_microservices
    assert 'core-eventing-worker' in start_microservices
    assert 'notes-domain-worker' in start_microservices
    assert 'ai-execution-domain-worker' in start_microservices
    assert 'admin-ops-domain-worker' in start_microservices
    assert 'lsof -tiTCP:' in start_microservices
    assert 'scripts/start-local-postgres-microservices.sh' in start_microservices
    assert 'scripts/start-local-redis-microservices.sh' in start_microservices
    assert 'scripts/start-local-rabbitmq-microservices.sh' in start_microservices


def test_start_project_exposes_lowmem_consolidated_runtime_without_replacing_split_default():
    start_project = _read('start-project.sh')
    start_lowmem = _read('start-lowmem.sh') if (REPO_ROOT / 'start-lowmem.sh').exists() else ''

    assert '--use-lowmem-consolidated-runtime' in start_project
    assert 'use_lowmem_consolidated_runtime=true' in start_project
    assert 'LOWMEM_CONSOLIDATED_RUNTIME=1' in start_project
    assert 'IELTS_BACKEND_RUNTIME_PROFILE=lowmem-consolidated' in start_project
    assert 'Low-memory API:' in start_project
    assert 'http://127.0.0.1:${gateway_port}' in start_project
    assert 'Low-memory consolidated runtime cannot be combined with monolith compatibility.' in start_project
    assert 'lowmem_consolidated_route_surface="browser"' in start_project
    assert 'BACKEND_PORT="${gateway_port}"' in start_project
    assert 'start_background \'backend-lowmem\'' in start_project
    assert 'start_background \'speech-lowmem\'' in start_project
    assert '--use-lowmem-consolidated-runtime' in start_lowmem
    assert 'start-project.sh' in start_lowmem


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


def test_simple_wsgi_services_use_starlette_shells_instead_of_fastapi_shells():
    for relative_path in (
        'services/identity-service/main.py',
        'services/learning-core-service/main.py',
        'services/catalog-content-service/main.py',
        'services/notes-service/main.py',
        'services/admin-ops-service/main.py',
    ):
        source = _read(relative_path)
        assert 'from a2wsgi import WSGIMiddleware' in source
        assert 'create_service_shell_app(' in source


def test_ai_and_asr_services_use_starlette_shells_for_lightweight_runtime_contracts():
    ai_source = _read('services/ai-execution-service/main.py')
    asr_source = _read('services/asr-service/main.py')

    assert 'from a2wsgi import WSGIMiddleware' in ai_source
    assert 'from starlette.requests import Request' in ai_source
    assert 'create_service_shell_app(' in ai_source
    assert "app.add_route('/internal/ops/ai-dependencies'" in ai_source
    assert ai_source.index("app.add_route('/internal/ops/ai-dependencies'") < ai_source.index(
        "app.mount('/', WSGIMiddleware(ai_flask_app))"
    )

    assert 'from starlette.datastructures import UploadFile' in asr_source
    assert 'from starlette.requests import Request' in asr_source
    assert 'create_service_shell_app(' in asr_source
    assert "app.add_route('/v1/speech/transcribe'" in asr_source
