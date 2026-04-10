#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${script_dir}/release-common.sh"

git_ref="${1:-main}"

require_command git
require_command systemctl
require_command curl
require_command python3
require_command node
require_command corepack
require_file "${BACKEND_ENV_FILE}"
require_file "${MICROSERVICES_ENV_FILE}"

ensure_release_directories
prepare_repository_root

probe_repo="${REPOSITORY_ROOT}"
if [[ ! -d "${probe_repo}/.git" && -d "${CURRENT_LINK}/.git" ]]; then
  probe_repo="${CURRENT_LINK}"
fi

[[ -f /etc/systemd/system/ielts-service@.service ]] || fail "Missing systemd template: /etc/systemd/system/ielts-service@.service"

log "Checking git access for ${git_ref}"
git -C "${probe_repo}" ls-remote --exit-code origin HEAD >/dev/null

log "Checking nginx configuration"
nginx -t >/dev/null

log "Checking active frontend directory"
mkdir -p "${WEB_ROOT}"

log "Preflight passed"
