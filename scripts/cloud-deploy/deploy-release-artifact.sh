#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")" && pwd)"
source "${script_dir}/release-common.sh"

artifact_path="${1:?artifact path is required}"
release_label="${2:-}"
timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
switched=false
previous_current=""
release_dir=""
extract_dir=""

bootstrap_admin_projections() {
  local release_path="${1:?release path is required}"
  local bootstrap_script="${release_path}/scripts/bootstrap-admin-projections.py"

  require_file "${bootstrap_script}"
  log "Bootstrapping admin projections"
  BACKEND_ENV_FILE="${BACKEND_ENV_FILE}" \
  CURRENT_SERVICE_NAME="admin-ops-service" \
  MICROSERVICES_ENV_FILE="${MICROSERVICES_ENV_FILE}" \
  PYTHONPATH="${release_path}/backend:${release_path}/packages/platform-sdk:${PYTHONPATH:-}" \
    "${VENV_DIR}/bin/python" "${bootstrap_script}" \
      --service-name "admin-ops-service" \
      --env-file "${MICROSERVICES_ENV_FILE}" \
      --format text
}

should_bootstrap_admin_projections() {
  case "${DEPLOY_BOOTSTRAP_ADMIN_PROJECTIONS:-false}" in
    1|true|TRUE|yes|YES) return 0 ;;
    ''|0|false|FALSE|no|NO) return 1 ;;
    *) fail "Invalid DEPLOY_BOOTSTRAP_ADMIN_PROJECTIONS value: ${DEPLOY_BOOTSTRAP_ADMIN_PROJECTIONS}" ;;
  esac
}

rollback_after_failure() {
  if [[ "${switched}" != "true" ]]; then
    return 0
  fi
  if [[ -n "${previous_current}" && -d "${previous_current}" ]]; then
    log "Attempting rollback to previous single-release deployment"
    set_current_release "${previous_current}"
    switch_frontend_to_release "${previous_current}"
    write_nginx_gateway_upstream_for_port "8000"
    nginx -t >/dev/null && systemctl reload nginx
    record_single_release_activation "${previous_current}"
    restart_service_units || true
    stop_all_http_slot_services || true
  fi
}

cleanup() {
  rm -rf "${extract_dir}"
  clear_deploy_lock
}

trap 'status=$?; if (( status != 0 )); then rollback_after_failure; fi; cleanup' EXIT

require_command tar
require_command systemctl
require_command curl
require_command python3
require_command nginx
require_file "${artifact_path}"
require_file "${BACKEND_ENV_FILE}"
require_file "${MICROSERVICES_ENV_FILE}"
ensure_release_directories
extract_dir="$(mktemp -d "${RELEASES_ROOT}/artifact-${timestamp}-XXXXXX")"
write_deploy_lock "${release_label:-artifact}"

tar -xzf "${artifact_path}" -C "${extract_dir}"
install_runtime_systemd_units "${extract_dir}"
install_release_python_dependencies "${extract_dir}"

if ! release_has_prebuilt_frontend "${extract_dir}"; then
  fail "Artifact is missing a prebuilt frontend dist payload"
fi

if [[ -z "${release_label}" ]]; then
  release_label="$(read_release_artifact_value "${extract_dir}" "commit_sha")"
fi
if [[ -z "${release_label}" ]]; then
  release_label="artifact"
fi

release_dir="${RELEASES_ROOT}/${timestamp}-$(printf '%s' "${release_label}" | cut -c1-12)"
previous_current="$(current_target_path)"
schema_migration_script="${extract_dir}/scripts/run-service-schema-migrations.py"

require_file "${schema_migration_script}"
mv "${extract_dir}" "${release_dir}"
extract_dir="${release_dir}"

run_backup_script
log "Applying split-service schema migrations"
"${VENV_DIR}/bin/python" "${schema_migration_script}" --env-file "${MICROSERVICES_ENV_FILE}"
if should_bootstrap_admin_projections; then
  bootstrap_admin_projections "${release_dir}"
else
  log "Skipping admin projection bootstrap during deploy"
fi
if [[ -e "${CURRENT_LINK}" && ! -L "${CURRENT_LINK}" ]]; then
  previous_current="$(stage_current_directory_as_legacy_release "${timestamp}")"
fi

log "Activating single-release deployment from artifact"
set_current_release "${release_dir}"
switch_frontend_to_release "${release_dir}"
write_nginx_gateway_upstream_for_port "8000"
nginx -t >/dev/null
systemctl reload nginx
record_single_release_activation "${release_dir}" "${previous_current}"
switched=true
enable_runtime_watchdog_timer
restart_service_units
stop_all_http_slot_services

log "Running post-switch smoke checks"
"${release_dir}/scripts/cloud-deploy/smoke-check.sh"

cleanup_old_releases "${release_dir}" "${previous_current}"
log "Artifact deployment completed successfully: ${release_dir}"
trap - EXIT
cleanup
