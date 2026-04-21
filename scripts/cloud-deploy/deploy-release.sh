#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")" && pwd)"
source "${script_dir}/release-common.sh"

git_ref="${1:?git ref is required}"
timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
switched=false
target_slot=""
previous_slot=""
previous_release=""
previous_current=""
release_dir=""

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

rollback_after_switch() {
  if [[ "${switched}" != "true" ]]; then
    return 0
  fi
  log "Attempting rollback after failed post-switch step"
  if [[ -n "${previous_slot}" && -n "${previous_release}" ]]; then
    set_http_slot_release "${previous_slot}" "${previous_release}"
    write_http_slot_env "${previous_slot}"
    start_http_slot_services "${previous_slot}"
    activate_http_slot_release "${previous_slot}" "${previous_release}" "${target_slot}" "${release_dir}" "current"
  elif [[ -n "${previous_current}" && -d "${previous_current}" ]]; then
    switch_frontend_to_release "${previous_current}"
    write_nginx_gateway_upstream_for_port "8000"
    nginx -t >/dev/null && systemctl reload nginx
    record_legacy_http_activation "${previous_current}"
  fi
  if [[ -n "${previous_current}" && -d "${previous_current}" ]]; then
    set_current_release "${previous_current}"
    restart_single_instance_units || true
  fi
  if [[ -n "${target_slot}" ]]; then
    stop_http_slot_services "${target_slot}"
  fi
}

trap 'status=$?; if (( status != 0 )); then rollback_after_switch; fi' EXIT

require_command git
require_command tar
require_command systemctl
require_command curl
require_command python3
require_command node
require_command corepack
require_command nginx
require_file "${BACKEND_ENV_FILE}"
require_file "${MICROSERVICES_ENV_FILE}"
ensure_release_directories
prepare_repository_root

commit_sha="$(fetch_git_commit "${git_ref}")"
release_dir="${RELEASES_ROOT}/${timestamp}-$(printf '%s' "${commit_sha}" | cut -c1-12)"
previous_current="$(current_target_path)"
previous_slot="$(active_http_slot)"
if [[ -n "${previous_slot}" ]]; then
  previous_release="$(http_slot_release_path "${previous_slot}")"
fi
if [[ -z "${previous_release}" ]]; then
  previous_release="${previous_current}"
fi
target_slot="$(inactive_http_slot "${previous_slot}")"
schema_migration_script="${release_dir}/scripts/run-service-schema-migrations.py"

log "Preparing release ${release_dir} from ${commit_sha}"
mkdir -p "${release_dir}"
git -C "${REPOSITORY_ROOT}" archive "${commit_sha}" | tar -xf - -C "${release_dir}"
hydrate_release_git_index "${release_dir}"
find "${release_dir}/scripts/cloud-deploy" -maxdepth 1 -type f -name '*.sh' -exec chmod +x {} +
install_release_dependencies "${release_dir}"
require_file "${schema_migration_script}"

run_backup_script
log "Applying split-service schema migrations"
"${VENV_DIR}/bin/python" "${schema_migration_script}" --env-file "${MICROSERVICES_ENV_FILE}"
bootstrap_admin_projections "${release_dir}"
if [[ -e "${CURRENT_LINK}" && ! -L "${CURRENT_LINK}" ]]; then
  previous_current="$(stage_current_directory_as_legacy_release "${timestamp}")"
  if [[ -z "${previous_release}" ]]; then
    previous_release="${previous_current}"
  fi
fi

log "Preparing HTTP ${target_slot} slot"
install_http_slot_systemd_template "${release_dir}"
set_http_slot_release "${target_slot}" "${release_dir}"
write_http_slot_env "${target_slot}"
start_http_slot_services "${target_slot}"

log "Running pre-switch smoke checks for HTTP ${target_slot} slot"
SMOKE_HTTP_SLOT="${target_slot}" \
SMOKE_SKIP_NGINX=true \
SMOKE_SKIP_WORKERS=true \
VALIDATE_BROKER_SCRIPT="${release_dir}/scripts/cloud-deploy/validate-broker-runtime.sh" \
  "${release_dir}/scripts/cloud-deploy/smoke-check.sh"

log "Switching frontend and API traffic to HTTP ${target_slot} slot"
activate_http_slot_release "${target_slot}" "${release_dir}" "${previous_slot}" "${previous_release}"
switched=true
set_current_release "${release_dir}"
restart_single_instance_units
if [[ -n "${previous_slot}" && "${previous_slot}" != "${target_slot}" ]]; then
  stop_http_slot_services "${previous_slot}"
fi
stop_legacy_http_units

log "Running post-switch smoke checks"
"${release_dir}/scripts/cloud-deploy/smoke-check.sh"

cleanup_old_releases "${release_dir}" "${previous_release}"
log "Deployment completed successfully: ${release_dir}"
trap - EXIT
