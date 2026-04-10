#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${script_dir}/release-common.sh"

git_ref="${1:?git ref is required}"
timestamp="$(date -u +%Y%m%dT%H%M%SZ)"

require_command git
require_command tar
require_command systemctl
require_command curl
require_command python3
require_command node
require_command corepack
require_file "${BACKEND_ENV_FILE}"
require_file "${MICROSERVICES_ENV_FILE}"
ensure_release_directories
prepare_repository_root

commit_sha="$(fetch_git_commit "${git_ref}")"
release_dir="${RELEASES_ROOT}/${timestamp}-$(printf '%s' "${commit_sha}" | cut -c1-12)"
previous_release="$(current_target_path)"

log "Preparing release ${release_dir} from ${commit_sha}"
mkdir -p "${release_dir}"
git -C "${REPOSITORY_ROOT}" archive "${commit_sha}" | tar -xf - -C "${release_dir}"
find "${release_dir}/scripts/cloud-deploy" -maxdepth 1 -type f -name '*.sh' -exec chmod +x {} +
install_release_dependencies "${release_dir}"

run_backup_script
if [[ -e "${CURRENT_LINK}" && ! -L "${CURRENT_LINK}" ]]; then
  previous_release="$(stage_current_directory_as_legacy_release "${timestamp}")"
fi

set_current_release "${release_dir}"
if ! {
  copy_frontend_dist "${release_dir}" &&
  restart_service_units &&
  "${script_dir}/smoke-check.sh"
}; then
  log "Deployment verification failed for ${release_dir}"
  if [[ -n "${previous_release}" && -d "${previous_release}" ]]; then
    log "Attempting rollback to ${previous_release}"
    "${script_dir}/rollback-release.sh" "${previous_release}"
  fi
  fail "Deployment failed after switching current release"
fi

cleanup_old_releases "${release_dir}" "${previous_release}"
log "Deployment completed successfully: ${release_dir}"
