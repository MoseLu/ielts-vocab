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
    assert 'record_single_release_activation' in script


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


def test_deploy_release_uses_single_release_switch_and_stops_http_slots():
    script = _read('scripts/cloud-deploy/deploy-release.sh')

    current_index = script.index('set_current_release "${release_dir}"')
    upstream_index = script.index('write_nginx_gateway_upstream_for_port "8000"', current_index)
    record_index = script.index(
        'record_single_release_activation "${release_dir}" "${previous_current}"',
        current_index,
    )
    restart_index = script.index('restart_service_units', current_index)
    stop_slots_index = script.index('stop_all_http_slot_services', current_index)
    smoke_index = script.index('"${release_dir}/scripts/cloud-deploy/smoke-check.sh"', current_index)

    assert current_index < upstream_index < record_index < restart_index < stop_slots_index < smoke_index
    assert 'Activating single-release deployment' in script
    assert 'Attempting rollback to previous single-release deployment' in script
    assert 'record_single_release_activation "${previous_current}"' in script
    assert 'start_http_slot_services "${target_slot}"' not in script
    assert 'activate_http_slot_release "${target_slot}"' not in script
    assert 'SMOKE_SKIP_NGINX=true' not in script
    assert 'SMOKE_SKIP_WORKERS=true' not in script


def test_preflight_checks_speaking_calibration_before_nginx_and_remote_deploy():
    script = _read('scripts/cloud-deploy/preflight-check.sh')
    workflow = _read('.github/workflows/deploy-production.yml')

    speaking_index = script.index('Checking speaking calibration config')
    nginx_index = script.index('Checking nginx configuration')

    assert 'SPEAKING_BAND_VALIDATOR_PATH' in script
    assert 'validate_speaking_band_thresholds.py' in script
    assert 'python3 "${speaking_validator_path}" --env-file "${MICROSERVICES_ENV_FILE}" >/dev/null' in script
    assert speaking_index < nginx_index
    assert 'scripts/validate_speaking_band_thresholds.py \\' in workflow


def test_rollback_release_defaults_to_last_good_release_and_restarts_single_release():
    script = _read('scripts/cloud-deploy/rollback-release.sh')

    assert 'resolve_rollback_target "${1:-}"' in script
    assert 'LAST_GOOD_RELEASE_FILE' in script
    assert 'set_current_release "${target_release}"' in script
    assert 'write_nginx_gateway_upstream_for_port "8000"' in script
    assert 'record_single_release_activation "${target_release}" "${target_release}"' in script
    assert 'restart_service_units' in script
    assert 'stop_all_http_slot_services' in script
    assert 'start_http_slot_services "${target_slot}"' not in script
    assert 'activate_http_slot_release "${target_slot}"' not in script


def test_http_slot_installer_uses_stable_wrapper_path_for_old_release_rollback():
    script = _read('scripts/cloud-deploy/release-common.sh')

    assert 'fallback_wrapper=' in script
    assert 'mkdir -p "${APP_HOME}/bin"' in script
    assert 'cp "${wrapper_path}" "${APP_HOME}/bin/run-http-slot-service.sh"' in script


def test_smoke_check_defaults_to_current_release_and_keeps_optional_slot_support():
    script = _read('scripts/cloud-deploy/smoke-check.sh')

    assert 'SMOKE_HTTP_SLOT=' in script
    assert 'if [[ -z "${SMOKE_HTTP_SLOT}" ]]; then' in script
    assert 'SMOKE_HTTP_SLOT="$(active_http_slot)"' in script
    assert 'load_smoke_slot_env "${SMOKE_HTTP_SLOT}"' in script
    assert 'smoke_release="$(current_target_path)"' in script
    assert 'if [[ -n "${SMOKE_HTTP_SLOT}" ]]; then' in script
    assert 'slot gateway books proxy' in script
    assert '/internal/ops/ai-dependencies?user_id=${SMOKE_AI_PROBE_USER_ID}' in script
    assert 'Skipping canonical worker unit smoke for pre-switch HTTP slot validation' in script


def test_nginx_config_uses_generated_gateway_upstream_and_current_dist_link():
    nginx = _read('scripts/cloud-deploy/ielts-vocab.nginx.conf')

    assert 'include /etc/nginx/conf.d/ielts-vocab-upstream.inc;' in nginx
    assert 'root /var/www/ielts-vocab/current;' in nginx
    assert 'proxy_pass http://ielts_gateway_bff;' in nginx


def test_ai_execution_service_exposes_internal_dependency_probe():
    main = _read('services/ai-execution-service/main.py')

    assert "app.add_route('/internal/ops/ai-dependencies'" in main
    assert main.index("app.add_route('/internal/ops/ai-dependencies'") < main.index(
        "app.mount('/', WSGIMiddleware(ai_flask_app))"
    )
    assert 'def _load_ai_dependency_probe_support()' in main
    assert 'fetch_learning_core_learning_stats_response' in main
    assert 'fetch_learning_core_context_payload' in main
    assert 'build_quick_memory_review_queue_response' in main
    assert "'quick_memory_review_queue'" in main
    assert 'build_local_learner_profile_response' in main


def test_release_common_falls_back_to_local_backup_script_when_current_release_lacks_cloud_deploy():
    source = _read('scripts/cloud-deploy/release-common.sh')

    assert 'if [[ -f "${CURRENT_LINK}/scripts/cloud-deploy/backup-postgres.sh" ]]; then' in source
    assert 'elif [[ -f "${REPOSITORY_ROOT}/scripts/cloud-deploy/backup-postgres.sh" ]]; then' in source
    assert 'elif [[ -n "${script_dir:-}" && -f "${script_dir}/backup-postgres.sh" ]]; then' in source
    assert 'backup_script="${script_dir}/backup-postgres.sh"' in source
    assert 'bash "${backup_script}" "${MICROSERVICES_ENV_FILE}"' in source


def test_artifact_deploy_keeps_release_dir_after_move():
    script = _read('scripts/cloud-deploy/deploy-release-artifact.sh')

    assert 'mv "${extract_dir}" "${release_dir}"' in script
    assert 'extract_dir="${release_dir}"' not in script
