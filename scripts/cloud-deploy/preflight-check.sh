#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${script_dir}/release-common.sh"

git_ref="${1:-main}"
speaking_validator_path="${SPEAKING_BAND_VALIDATOR_PATH:-}"

if [[ -z "${speaking_validator_path}" ]]; then
  if [[ -f "${script_dir}/validate_speaking_band_thresholds.py" ]]; then
    speaking_validator_path="${script_dir}/validate_speaking_band_thresholds.py"
  elif [[ -f "${script_dir}/../validate_speaking_band_thresholds.py" ]]; then
    speaking_validator_path="${script_dir}/../validate_speaking_band_thresholds.py"
  else
    speaking_validator_path="${CURRENT_LINK}/scripts/validate_speaking_band_thresholds.py"
  fi
fi

require_command git
require_command systemctl
require_command curl
require_command python3
require_command node
require_command corepack
require_command nginx
require_file "${BACKEND_ENV_FILE}"
require_file "${MICROSERVICES_ENV_FILE}"
require_file "${speaking_validator_path}"

ensure_release_directories
prepare_repository_root

probe_repo="${REPOSITORY_ROOT}"
if [[ ! -d "${probe_repo}/.git" && -d "${CURRENT_LINK}/.git" ]]; then
  probe_repo="${CURRENT_LINK}"
fi

[[ -f /etc/systemd/system/ielts-service@.service ]] || fail "Missing systemd template: /etc/systemd/system/ielts-service@.service"
if [[ ! -f /etc/systemd/system/ielts-http-slot@.service ]]; then
  log "HTTP slot systemd template will be installed by the next deploy"
fi

log "Checking git access for ${git_ref}"
git -C "${probe_repo}" ls-remote --exit-code origin HEAD >/dev/null

log "Checking broker env baseline"
grep -q '^REDIS_HOST=' "${MICROSERVICES_ENV_FILE}" || fail "Missing REDIS_HOST in ${MICROSERVICES_ENV_FILE}"
grep -q '^RABBITMQ_HOST=' "${MICROSERVICES_ENV_FILE}" || fail "Missing RABBITMQ_HOST in ${MICROSERVICES_ENV_FILE}"
grep -q '^RABBITMQ_USER=' "${MICROSERVICES_ENV_FILE}" || fail "Missing RABBITMQ_USER in ${MICROSERVICES_ENV_FILE}"
grep -q '^RABBITMQ_VHOST=' "${MICROSERVICES_ENV_FILE}" || fail "Missing RABBITMQ_VHOST in ${MICROSERVICES_ENV_FILE}"

log "Checking speaking calibration config"
python3 "${speaking_validator_path}" --env-file "${MICROSERVICES_ENV_FILE}" >/dev/null

log "Checking broker systemd units"
systemctl is-active --quiet redis
systemctl is-active --quiet rabbitmq-server

log "Checking nginx configuration"
nginx -t >/dev/null

log "Checking active frontend directory"
mkdir -p "${WEB_ROOT}"

log "Preflight passed"
