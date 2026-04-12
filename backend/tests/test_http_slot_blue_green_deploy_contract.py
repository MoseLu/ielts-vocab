from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
CLOUD_DIR = REPO_ROOT / 'scripts' / 'cloud-deploy'


def _read(relative_path: str) -> str:
    return (REPO_ROOT / relative_path).read_text(encoding='utf-8')


def test_http_slot_common_defines_blue_green_ports_and_state_files():
    script = _read('scripts/cloud-deploy/http-slot-common.sh')

    assert 'ACTIVE_HTTP_SLOT_FILE=' in script
    assert 'LAST_GOOD_RELEASE_FILE=' in script
    assert 'blue|green' in script
    assert "blue) printf '1'" in script
    assert "green) printf '2'" in script
    assert "gateway-bff) printf '%s8000" in script
    assert "identity-service) printf '%s8101" in script
    assert "admin-ops-service) printf '%s8108" in script
    assert 'LEARNING_CORE_SERVICE_URL' in script
    assert 'AI_EXECUTION_SERVICE_URL' in script
    assert "printf '%s=http://127.0.0.1:%s" in script
    assert 'nginx_uses_http_slot_upstream' in script
    assert 'proxy_pass[[:space:]]+http://ielts_gateway_bff' in script
    assert 'last_good_mode="${5:-previous}"' in script
    assert 'current)' in script
    assert 'record_legacy_http_activation' in script


def test_http_slot_systemd_template_uses_slot_instance_wrapper():
    unit = (CLOUD_DIR / 'ielts-http-slot@.service').read_text(encoding='utf-8')
    wrapper = (CLOUD_DIR / 'run-http-slot-service.sh').read_text(encoding='utf-8')

    assert 'ExecStart=/opt/ielts-vocab/bin/run-http-slot-service.sh %i' in unit
    assert 'instance="${1:?slot.service instance is required}"' in wrapper
    assert 'slot="${instance%%.*}"' in wrapper
    assert 'service_name="${instance#*.}"' in wrapper
    assert 'Unknown HTTP slot service' in wrapper
    assert 'IELTS_APP_ROOT="${app_root}"' in wrapper
    assert 'IELTS_HTTP_SLOT_ENV_FILE="${slot_env}"' in wrapper
    assert 'exec "${app_root}/scripts/cloud-deploy/run-service.sh" "${service_name}"' in wrapper


def test_deploy_release_starts_inactive_slot_before_switching_nginx():
    script = _read('scripts/cloud-deploy/deploy-release.sh')

    start_index = script.index('start_http_slot_services "${target_slot}"')
    smoke_index = script.index('SMOKE_HTTP_SLOT="${target_slot}"')
    switch_index = script.index('activate_http_slot_release "${target_slot}"')
    current_index = script.index('set_current_release "${release_dir}"')

    assert start_index < smoke_index < switch_index < current_index
    assert 'install_http_slot_systemd_template "${release_dir}"' in script
    assert 'stop_legacy_http_units' in script
    assert 'restart_single_instance_units' in script
    assert 'SMOKE_SKIP_NGINX=true' in script
    assert 'SMOKE_SKIP_WORKERS=true' in script
    assert 'record_legacy_http_activation "${previous_current}"' in script


def test_rollback_release_defaults_to_last_good_release_and_uses_slot_smoke():
    script = _read('scripts/cloud-deploy/rollback-release.sh')

    assert 'resolve_rollback_target "${1:-}"' in script
    assert 'LAST_GOOD_RELEASE_FILE' in script
    assert 'target_slot="$(inactive_http_slot "${previous_slot}")"' in script
    assert 'start_http_slot_services "${target_slot}"' in script
    assert 'SMOKE_SKIP_NGINX=true' in script
    assert 'activate_http_slot_release "${target_slot}" "${target_release}" "${previous_slot}" "${previous_release}" "current"' in script


def test_http_slot_installer_uses_stable_wrapper_path_for_old_release_rollback():
    script = _read('scripts/cloud-deploy/release-common.sh')

    assert 'fallback_wrapper=' in script
    assert 'mkdir -p "${APP_HOME}/bin"' in script
    assert 'cp "${wrapper_path}" "${APP_HOME}/bin/run-http-slot-service.sh"' in script


def test_smoke_check_supports_pre_switch_slot_validation_and_ai_probe():
    script = _read('scripts/cloud-deploy/smoke-check.sh')

    assert 'SMOKE_HTTP_SLOT=' in script
    assert 'load_smoke_slot_env "${SMOKE_HTTP_SLOT}"' in script
    assert 'slot gateway books proxy' in script
    assert '/internal/ops/ai-dependencies?user_id=${SMOKE_AI_PROBE_USER_ID}' in script
    assert 'Skipping Wave 5 worker unit smoke for pre-switch HTTP slot validation' in script


def test_nginx_config_uses_generated_gateway_upstream_and_current_dist_link():
    nginx = _read('scripts/cloud-deploy/ielts-vocab.nginx.conf')

    assert 'include /etc/nginx/conf.d/ielts-vocab-upstream.inc;' in nginx
    assert 'root /var/www/ielts-vocab/current;' in nginx
    assert 'proxy_pass http://ielts_gateway_bff;' in nginx


def test_ai_execution_service_exposes_internal_dependency_probe():
    main = _read('services/ai-execution-service/main.py')

    assert "@app.get('/internal/ops/ai-dependencies')" in main
    assert 'fetch_learning_core_learning_stats_response' in main
    assert 'fetch_learning_core_context_payload' in main
    assert 'build_quick_memory_review_queue_response' in main
    assert "'quick_memory_review_queue'" in main
    assert 'build_local_learner_profile_response' in main
