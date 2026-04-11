#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${script_dir}/release-common.sh"

GATEWAY_BFF_PORT="${GATEWAY_BFF_PORT:-8000}"
IDENTITY_SERVICE_PORT="${IDENTITY_SERVICE_PORT:-8101}"
LEARNING_CORE_SERVICE_PORT="${LEARNING_CORE_SERVICE_PORT:-8102}"
CATALOG_CONTENT_SERVICE_PORT="${CATALOG_CONTENT_SERVICE_PORT:-8103}"
AI_EXECUTION_SERVICE_PORT="${AI_EXECUTION_SERVICE_PORT:-8104}"
TTS_MEDIA_SERVICE_PORT="${TTS_MEDIA_SERVICE_PORT:-8105}"
ASR_SERVICE_PORT="${ASR_SERVICE_PORT:-8106}"
NOTES_SERVICE_PORT="${NOTES_SERVICE_PORT:-8107}"
ADMIN_OPS_SERVICE_PORT="${ADMIN_OPS_SERVICE_PORT:-8108}"
SPEECH_SERVICE_PORT="${SPEECH_SERVICE_PORT:-5001}"
SMOKE_MAX_WAIT_SECONDS="${SMOKE_MAX_WAIT_SECONDS:-90}"
SMOKE_RETRY_DELAY_SECONDS="${SMOKE_RETRY_DELAY_SECONDS:-2}"
CURL_MAX_TIME_SECONDS="${CURL_MAX_TIME_SECONDS:-5}"
VALIDATE_BROKER_SCRIPT="${VALIDATE_BROKER_SCRIPT:-${CURRENT_LINK}/scripts/cloud-deploy/validate-broker-runtime.sh}"

wait_for_curl() {
  local label="${1:?label is required}"
  shift

  local deadline
  local attempt=1
  deadline=$(( $(date +%s) + SMOKE_MAX_WAIT_SECONDS ))

  while true; do
    if curl -fsS --max-time "${CURL_MAX_TIME_SECONDS}" "$@" >/dev/null 2>&1; then
      log "Smoke check passed: ${label} (attempt ${attempt})"
      return 0
    fi
    if (( $(date +%s) >= deadline )); then
      log "Smoke check timed out after ${attempt} attempts: ${label}"
      curl -fsS --max-time "${CURL_MAX_TIME_SECONDS}" "$@" >/dev/null
    fi
    attempt=$((attempt + 1))
    sleep "${SMOKE_RETRY_DELAY_SECONDS}"
  done
}

wait_for_systemd_unit() {
  local unit_name="${1:?unit name is required}"
  local label="${2:?label is required}"

  local deadline
  local attempt=1
  deadline=$(( $(date +%s) + SMOKE_MAX_WAIT_SECONDS ))

  while true; do
    if systemctl is-active --quiet "${unit_name}"; then
      log "Smoke check passed: ${label} (attempt ${attempt})"
      return 0
    fi
    if (( $(date +%s) >= deadline )); then
      log "Smoke check timed out after ${attempt} attempts: ${label}"
      systemctl status "${unit_name}" --no-pager
    fi
    attempt=$((attempt + 1))
    sleep "${SMOKE_RETRY_DELAY_SECONDS}"
  done
}

check_url() {
  local url="${1:?url is required}"
  local label="${2:?label is required}"
  log "Smoke check: ${label}"
  wait_for_curl "${label}" "${url}"
}

check_host_url() {
  local path="${1:?path is required}"
  local label="${2:?label is required}"
  log "Smoke check: ${label}"
  wait_for_curl "${label}" -H "Host: ${SMOKE_HOST}" "http://127.0.0.1${path}"
}

require_command curl
require_command systemctl
require_file "${VALIDATE_BROKER_SCRIPT}"

log "Smoke check: wave5 broker runtime"
"${VALIDATE_BROKER_SCRIPT}"

check_url "http://127.0.0.1:${GATEWAY_BFF_PORT}/ready" "gateway-bff ready"
check_url "http://127.0.0.1:${IDENTITY_SERVICE_PORT}/ready" "identity-service ready"
check_url "http://127.0.0.1:${LEARNING_CORE_SERVICE_PORT}/ready" "learning-core-service ready"
check_url "http://127.0.0.1:${CATALOG_CONTENT_SERVICE_PORT}/ready" "catalog-content-service ready"
check_url "http://127.0.0.1:${AI_EXECUTION_SERVICE_PORT}/ready" "ai-execution-service ready"
check_url "http://127.0.0.1:${TTS_MEDIA_SERVICE_PORT}/ready" "tts-media-service ready"
check_url "http://127.0.0.1:${ASR_SERVICE_PORT}/ready" "asr-service ready"
check_url "http://127.0.0.1:${NOTES_SERVICE_PORT}/ready" "notes-service ready"
check_url "http://127.0.0.1:${ADMIN_OPS_SERVICE_PORT}/ready" "admin-ops-service ready"
check_url "http://127.0.0.1:${SPEECH_SERVICE_PORT}/ready" "asr-socketio ready"
check_host_url "/" "nginx frontend"
check_host_url "/api/books" "nginx api proxy"

current_release="$(current_target_path)"
if [[ -n "${current_release}" && -d "${current_release}" ]] && release_supports_wave5_workers "${current_release}"; then
  for worker in "${WAVE5_WORKER_UNITS[@]}"; do
    log "Smoke check: ${worker} active"
    wait_for_systemd_unit "ielts-service@${worker}" "${worker} active"
  done
else
  log "Skipping Wave 5 worker unit smoke because current release does not support worker units"
fi

log "Smoke checks passed"
