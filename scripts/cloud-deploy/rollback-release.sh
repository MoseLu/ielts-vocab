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

log "Rolling back current release to ${target_release}"
set_current_release "${target_release}"
switch_frontend_to_release "${target_release}"
write_nginx_gateway_upstream_for_port "8000"
nginx -t >/dev/null
systemctl reload nginx
record_single_release_activation "${target_release}" "${target_release}"
restart_service_units
stop_all_http_slot_services

"${script_dir}/smoke-check.sh"
log "Rollback completed successfully: ${target_release}"
