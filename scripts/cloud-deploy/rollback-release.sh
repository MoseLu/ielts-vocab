#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")" && pwd)"
source "${script_dir}/release-common.sh"

resolve_rollback_target() {
  local requested="${1:-}"
  if [[ -z "${requested}" || "${requested}" == "--last-good" ]]; then
    require_file "${LAST_GOOD_RELEASE_FILE}"
    requested="$(tr -d '[:space:]' < "${LAST_GOOD_RELEASE_FILE}")"
  fi
  [[ -n "${requested}" ]] || fail "Rollback target is empty"
  readlink -f "${requested}"
}

require_command systemctl
require_command curl
require_command nginx

target_release="$(resolve_rollback_target "${1:-}")"
[[ -d "${target_release}" ]] || fail "Rollback target does not exist: ${target_release}"

previous_slot="$(active_http_slot)"
previous_release=""
if [[ -n "${previous_slot}" ]]; then
  previous_release="$(http_slot_release_path "${previous_slot}")"
fi
target_slot="$(inactive_http_slot "${previous_slot}")"

log "Preparing rollback of HTTP traffic to ${target_release} through ${target_slot} slot"
install_http_slot_systemd_template "${target_release}"
set_http_slot_release "${target_slot}" "${target_release}"
write_http_slot_env "${target_slot}"
start_http_slot_services "${target_slot}"

SMOKE_HTTP_SLOT="${target_slot}" \
SMOKE_SKIP_NGINX=true \
SMOKE_SKIP_WORKERS=true \
VALIDATE_BROKER_SCRIPT="${target_release}/scripts/cloud-deploy/validate-broker-runtime.sh" \
  "${script_dir}/smoke-check.sh"

activate_http_slot_release "${target_slot}" "${target_release}" "${previous_slot}" "${previous_release}" "current"
set_current_release "${target_release}"
restart_single_instance_units
if [[ -n "${previous_slot}" && "${previous_slot}" != "${target_slot}" ]]; then
  stop_http_slot_services "${previous_slot}"
fi
stop_legacy_http_units

"${script_dir}/smoke-check.sh"
log "Rollback completed successfully: ${target_release}"
