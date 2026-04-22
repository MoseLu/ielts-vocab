#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")" && pwd)"
source "${script_dir}/release-common.sh"

SMOKE_HTTP_SLOT="${SMOKE_HTTP_SLOT:-}"
SMOKE_SKIP_NGINX="${SMOKE_SKIP_NGINX:-false}"
SMOKE_SKIP_WORKERS="${SMOKE_SKIP_WORKERS:-false}"
SMOKE_AI_PROBE_USER_ID="${SMOKE_AI_PROBE_USER_ID:-1}"
SMOKE_ADMIN_PROBE_USER_ID="${SMOKE_ADMIN_PROBE_USER_ID:-1}"
SMOKE_MAX_WAIT_SECONDS="${SMOKE_MAX_WAIT_SECONDS:-90}"
SMOKE_RETRY_DELAY_SECONDS="${SMOKE_RETRY_DELAY_SECONDS:-2}"
CURL_MAX_TIME_SECONDS="${CURL_MAX_TIME_SECONDS:-5}"
VALIDATE_BROKER_SCRIPT="${VALIDATE_BROKER_SCRIPT:-${script_dir}/validate-broker-runtime.sh}"

load_smoke_slot_env() {
  local slot="${1:-}"
  local env_file
  [[ -n "${slot}" ]] || return 0
  require_http_slot "${slot}"
  env_file="$(http_slot_env_file "${slot}")"
  require_file "${env_file}"
  set -a
  source "${env_file}"
  set +a
}

release_supports_ai_dependency_probe() {
  local release_dir="${1:-}"
  [[ -n "${release_dir}" ]] || return 1
  grep -Fq "/internal/ops/ai-dependencies" "${release_dir}/services/ai-execution-service/main.py" 2>/dev/null
}

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

check_admin_overview_probe() {
  local release_dir="${1:?release dir is required}"
  log "Smoke check: admin overview projection"
  BACKEND_ENV_FILE="${BACKEND_ENV_FILE}" \
  MICROSERVICES_ENV_FILE="${MICROSERVICES_ENV_FILE}" \
  ADMIN_OPS_SERVICE_PORT="${ADMIN_OPS_SERVICE_PORT}" \
  SMOKE_ADMIN_PROBE_USER_ID="${SMOKE_ADMIN_PROBE_USER_ID}" \
  CURL_MAX_TIME_SECONDS="${CURL_MAX_TIME_SECONDS}" \
  PYTHONPATH="${release_dir}/backend:${release_dir}/packages/platform-sdk:${PYTHONPATH:-}" \
    "${VENV_DIR}/bin/python" - <<'PY'
import os
import sys

import requests
from dotenv import load_dotenv

from platform_sdk.internal_service_auth import create_internal_auth_headers_for_user

backend_env = os.environ.get('BACKEND_ENV_FILE') or ''
microservices_env = os.environ.get('MICROSERVICES_ENV_FILE') or ''
if backend_env:
    load_dotenv(backend_env, override=False)
if microservices_env:
    load_dotenv(microservices_env, override=True)

port = os.environ.get('ADMIN_OPS_SERVICE_PORT') or '8108'
user_id = int(os.environ.get('SMOKE_ADMIN_PROBE_USER_ID') or '1')
timeout = float(os.environ.get('CURL_MAX_TIME_SECONDS') or '5')
headers = create_internal_auth_headers_for_user(
    user_id=user_id,
    is_admin=True,
    username='smoke-admin',
)
response = requests.get(
    f'http://127.0.0.1:{port}/api/admin/overview',
    headers=headers,
    timeout=timeout,
)
if response.status_code != 200:
    print(
        f'admin overview probe failed: status={response.status_code} body={response.text[:300]}',
        file=sys.stderr,
    )
    raise SystemExit(1)
print('admin overview projection passed')

users_response = requests.get(
    f'http://127.0.0.1:{port}/api/admin/users?page=1&per_page=20',
    headers=headers,
    timeout=timeout,
)
if users_response.status_code != 200:
    print(
        f'admin users probe failed: status={users_response.status_code} '
        f'body={users_response.text[:300]}',
        file=sys.stderr,
    )
    raise SystemExit(1)

users = users_response.json().get('users') or []
if not users:
    print('admin detail projection skipped: no users returned')
    raise SystemExit(0)

target_user_id = int(users[0]['id'])
detail_response = requests.get(
    f'http://127.0.0.1:{port}/api/admin/users/{target_user_id}?wrong_words_sort=last_error',
    headers=headers,
    timeout=timeout,
)
if detail_response.status_code != 200:
    print(
        f'admin detail probe failed: status={detail_response.status_code} '
        f'user_id={target_user_id} body={detail_response.text[:300]}',
        file=sys.stderr,
    )
    raise SystemExit(1)
print('admin detail projection passed')
PY
}

require_command curl
require_command systemctl
require_file "${VALIDATE_BROKER_SCRIPT}"
require_file "${VENV_DIR}/bin/python"

if [[ -z "${SMOKE_HTTP_SLOT}" ]]; then
  SMOKE_HTTP_SLOT="$(active_http_slot)"
fi
load_smoke_slot_env "${SMOKE_HTTP_SLOT}"

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

smoke_release="$(current_target_path)"
if [[ -n "${SMOKE_HTTP_SLOT}" ]]; then
  smoke_release="$(http_slot_release_path "${SMOKE_HTTP_SLOT}")"
fi

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
check_admin_overview_probe "${smoke_release}"

if [[ "${SMOKE_SKIP_NGINX}" != "true" ]]; then
  check_url "http://127.0.0.1:${SPEECH_SERVICE_PORT}/ready" "asr-socketio ready"
  check_host_url "/" "nginx frontend"
  check_host_url "/api/books" "nginx api proxy"
else
  check_url "http://127.0.0.1:${GATEWAY_BFF_PORT}/api/books" "slot gateway books proxy"
fi

if release_supports_ai_dependency_probe "${smoke_release}"; then
  check_url "http://127.0.0.1:${AI_EXECUTION_SERVICE_PORT}/internal/ops/ai-dependencies?user_id=${SMOKE_AI_PROBE_USER_ID}" "ai dependency probe"
else
  log "Skipping AI dependency probe because target release does not support it"
fi

current_release="$(current_target_path)"
if [[ "${SMOKE_SKIP_WORKERS}" != "true" ]] && [[ -n "${current_release}" && -d "${current_release}" ]] && release_supports_wave5_workers "${current_release}"; then
  for worker in "${WAVE5_WORKER_UNITS[@]}"; do
    log "Smoke check: ${worker} active"
    wait_for_systemd_unit "ielts-service@${worker}" "${worker} active"
  done
elif [[ "${SMOKE_SKIP_WORKERS}" != "true" ]]; then
  log "Skipping Wave 5 worker unit smoke because current release does not support worker units"
else
  log "Skipping Wave 5 worker unit smoke for pre-switch HTTP slot validation"
fi

log "Smoke check: health watchdog timer active"
wait_for_systemd_unit "ielts-health-watchdog.timer" "health watchdog timer active"

log "Smoke checks passed"
