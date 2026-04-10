#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${script_dir}/release-common.sh"

target_release="${1:?target release path is required}"

require_command systemctl
require_command curl

target_release="$(readlink -f "${target_release}")"
[[ -d "${target_release}" ]] || fail "Rollback target does not exist: ${target_release}"

log "Rolling back current release to ${target_release}"
set_current_release "${target_release}"
copy_frontend_dist "${target_release}"
restart_service_units
"${script_dir}/smoke-check.sh"
log "Rollback completed successfully"
