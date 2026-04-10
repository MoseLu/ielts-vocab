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

check_url() {
  local url="${1:?url is required}"
  local label="${2:?label is required}"
  log "Smoke check: ${label}"
  curl -fsS "${url}" >/dev/null
}

check_host_url() {
  local path="${1:?path is required}"
  local label="${2:?label is required}"
  log "Smoke check: ${label}"
  curl -fsS -H "Host: ${SMOKE_HOST}" "http://127.0.0.1${path}" >/dev/null
}

require_command curl

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

log "Smoke checks passed"
