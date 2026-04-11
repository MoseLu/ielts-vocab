#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${script_dir}/release-common.sh"

PYTHON_BIN="${PYTHON_BIN:-${VENV_DIR}/bin/python}"
SYSTEMCTL_BIN="${SYSTEMCTL_BIN:-systemctl}"
CURL_BIN="${CURL_BIN:-curl}"
READY_TIMEOUT_SECONDS="${READY_TIMEOUT_SECONDS:-45}"
SHARED_SQLITE_OVERRIDE_RECORD_PATH="${SHARED_SQLITE_OVERRIDE_RECORD_PATH:-}"
SHARED_SQLITE_OVERRIDE_RECORD_ACTIVE="${SHARED_SQLITE_OVERRIDE_RECORD_ACTIVE:-false}"

override_set="false"


bool_is_true() {
  local raw="${1:-false}"
  [[ "${raw,,}" == "true" ]]
}


enable_recording_if_requested() {
  if [[ -z "${SHARED_SQLITE_OVERRIDE_RECORD_PATH}" ]] || bool_is_true "${SHARED_SQLITE_OVERRIDE_RECORD_ACTIVE}"; then
    return 0
  fi
  mkdir -p "$(dirname "${SHARED_SQLITE_OVERRIDE_RECORD_PATH}")"
  export SHARED_SQLITE_OVERRIDE_RECORD_ACTIVE="true"
  exec > >(tee -a "${SHARED_SQLITE_OVERRIDE_RECORD_PATH}") 2>&1
  log "Recording Wave 4 shared SQLite override restart output to ${SHARED_SQLITE_OVERRIDE_RECORD_PATH}"
}


require_executable_file() {
  [[ -x "$1" ]] || fail "Missing executable file: $1"
}


validate_guarded_service() {
  local service_name="${1:?service name is required}"
  if PYTHONPATH="${CURRENT_LINK}/packages/platform-sdk:${PYTHONPATH:-}" \
    "${PYTHON_BIN}" - "${service_name}" <<'PY'
import sys

from platform_sdk.service_storage_boundary_plan import get_service_storage_boundary_plan

get_service_storage_boundary_plan(sys.argv[1])
PY
  then
    return 0
  fi

  fail "Unknown guarded split service: ${service_name}"
}


service_ready_url() {
  local service_name="${1:?service name is required}"
  case "${service_name}" in
    identity-service) printf '%s\n' 'http://127.0.0.1:8101/ready' ;;
    learning-core-service) printf '%s\n' 'http://127.0.0.1:8102/ready' ;;
    catalog-content-service) printf '%s\n' 'http://127.0.0.1:8103/ready' ;;
    ai-execution-service) printf '%s\n' 'http://127.0.0.1:8104/ready' ;;
    tts-media-service) printf '%s\n' 'http://127.0.0.1:8105/ready' ;;
    asr-service) printf '%s\n' 'http://127.0.0.1:8106/ready' ;;
    notes-service) printf '%s\n' 'http://127.0.0.1:8107/ready' ;;
    admin-ops-service) printf '%s\n' 'http://127.0.0.1:8108/ready' ;;
    *) fail "No remote ready URL mapped for guarded service: ${service_name}" ;;
  esac
}


wait_http_ready() {
  local url="${1:?url is required}"
  local attempts=$(( READY_TIMEOUT_SECONDS * 2 ))
  local attempt=0

  log "Waiting for ready URL: ${url}"
  while (( attempt < attempts )); do
    if "${CURL_BIN}" -fsS "${url}" >/dev/null; then
      log "Ready URL responded: ${url}"
      return 0
    fi
    attempt=$((attempt + 1))
    sleep 0.5
  done

  fail "Service did not become ready within ${READY_TIMEOUT_SECONDS} seconds: ${url}"
}


cleanup() {
  if [[ "${override_set}" == "true" ]]; then
    "${SYSTEMCTL_BIN}" unset-environment ALLOW_SHARED_SPLIT_SERVICE_SQLITE_SERVICES || true
  fi
}


main() {
  trap cleanup EXIT

  enable_recording_if_requested
  (( $# > 0 )) || fail "At least one guarded split service name is required"
  require_command "${SYSTEMCTL_BIN}"
  require_command "${CURL_BIN}"
  require_file "${BACKEND_ENV_FILE}"
  require_file "${MICROSERVICES_ENV_FILE}"
  require_executable_file "${PYTHON_BIN}"

  local normalized_services=()
  local service_name=""
  local seen=" "
  for service_name in "$@"; do
    [[ -n "${service_name}" ]] || continue
    validate_guarded_service "${service_name}"
    if [[ "${seen}" == *" ${service_name} "* ]]; then
      continue
    fi
    normalized_services+=("${service_name}")
    seen="${seen}${service_name} "
  done
  (( ${#normalized_services[@]} > 0 )) || fail "No guarded split service names were provided"

  local override_csv=""
  override_csv="$(IFS=,; printf '%s' "${normalized_services[*]}")"

  log "Wave 4 shared SQLite override restart"
  if [[ -n "$(current_target_path)" ]]; then
    log "Current release: $(current_target_path)"
  fi
  log "Target services: ${override_csv}"
  log "Ready timeout seconds: ${READY_TIMEOUT_SECONDS}"
  log "Applying scoped shared SQLite override for: ${override_csv}"
  "${SYSTEMCTL_BIN}" set-environment ALLOW_SHARED_SPLIT_SERVICE_SQLITE_SERVICES="${override_csv}"
  override_set="true"

  for service_name in "${normalized_services[@]}"; do
    log "Restarting ielts-service@${service_name}"
    "${SYSTEMCTL_BIN}" restart "ielts-service@${service_name}"
    wait_http_ready "$(service_ready_url "${service_name}")"
  done

  log "Wave 4 shared SQLite override restart completed for: ${override_csv}"
}


main "$@"
