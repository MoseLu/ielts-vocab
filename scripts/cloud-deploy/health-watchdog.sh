#!/usr/bin/env bash
set -euo pipefail

APP_HOME="${APP_HOME:-/opt/ielts-vocab}"
CURRENT_LINK="${CURRENT_LINK:-${APP_HOME}/current}"
SCRIPT_ROOT="${CURRENT_LINK}/scripts/cloud-deploy"
source "${SCRIPT_ROOT}/release-common.sh"

WATCHDOG_STATE_DIR="${WATCHDOG_STATE_DIR:-${DEPLOY_RUNTIME_DIR}/watchdog}"
WATCHDOG_FAILURE_FILE="${WATCHDOG_FAILURE_FILE:-${WATCHDOG_STATE_DIR}/consecutive-failures}"
WATCHDOG_LAST_RESTART_FILE="${WATCHDOG_LAST_RESTART_FILE:-${WATCHDOG_STATE_DIR}/last-restart-at}"
WATCHDOG_FAILURE_THRESHOLD="${WATCHDOG_FAILURE_THRESHOLD:-3}"
WATCHDOG_RESTART_COOLDOWN_SECONDS="${WATCHDOG_RESTART_COOLDOWN_SECONDS:-300}"
WATCHDOG_DEPLOY_LOCK_MAX_SECONDS="${WATCHDOG_DEPLOY_LOCK_MAX_SECONDS:-5400}"
WATCHDOG_CURL_MAX_TIME_SECONDS="${WATCHDOG_CURL_MAX_TIME_SECONDS:-5}"

mkdir -p "${WATCHDOG_STATE_DIR}"

read_state_value() {
  local path="${1:?path is required}"
  local default_value="${2:-0}"
  if [[ -f "${path}" ]]; then
    tr -d '[:space:]' < "${path}"
    return 0
  fi
  printf '%s\n' "${default_value}"
}

write_state_value() {
  local path="${1:?path is required}"
  local value="${2:?value is required}"
  printf '%s\n' "${value}" > "${path}"
}

deploy_in_progress() {
  local lock_pid=""
  local lock_started=""
  local lock_age=0
  local now

  [[ -f "${DEPLOY_LOCK_FILE}" ]] || return 1

  lock_pid="$(awk -F= '/^pid=/{print $2}' "${DEPLOY_LOCK_FILE}" | tail -n1)"
  lock_started="$(awk -F= '/^started_at=/{print $2}' "${DEPLOY_LOCK_FILE}" | tail -n1)"
  now="$(date +%s)"
  if [[ -n "${lock_started}" ]]; then
    lock_age=$(( now - lock_started ))
  fi

  if [[ -n "${lock_pid}" ]] && kill -0 "${lock_pid}" 2>/dev/null; then
    if [[ -z "${lock_started}" || "${lock_age}" -lt "${WATCHDOG_DEPLOY_LOCK_MAX_SECONDS}" ]]; then
      log "Health watchdog: deploy is still running, skipping checks"
      return 0
    fi
  fi

  log "Health watchdog: removing stale deploy lock"
  rm -f "${DEPLOY_LOCK_FILE}"
  return 1
}

runtime_healthy() {
  systemctl is-active --quiet nginx || return 1
  systemctl is-active --quiet "ielts-service@gateway-bff" || return 1
  curl -fsS --max-time "${WATCHDOG_CURL_MAX_TIME_SECONDS}" "http://127.0.0.1:8000/ready" >/dev/null || return 1
  curl -fsS --max-time "${WATCHDOG_CURL_MAX_TIME_SECONDS}" -H "Host: ${SMOKE_HOST}" "http://127.0.0.1/api/books" >/dev/null || return 1
}

restart_cooldown_active() {
  local last_restart
  local now

  last_restart="$(read_state_value "${WATCHDOG_LAST_RESTART_FILE}" 0)"
  now="$(date +%s)"
  (( now - last_restart < WATCHDOG_RESTART_COOLDOWN_SECONDS ))
}

attempt_recovery() {
  log "Health watchdog: restarting nginx and single-instance services"
  write_state_value "${WATCHDOG_LAST_RESTART_FILE}" "$(date +%s)"
  systemctl restart nginx
  restart_service_units
  stop_all_http_slot_services || true
}

if deploy_in_progress; then
  exit 0
fi

if runtime_healthy; then
  write_state_value "${WATCHDOG_FAILURE_FILE}" 0
  log "Health watchdog: runtime healthy"
  exit 0
fi

failure_count="$(( $(read_state_value "${WATCHDOG_FAILURE_FILE}" 0) + 1 ))"
write_state_value "${WATCHDOG_FAILURE_FILE}" "${failure_count}"
log "Health watchdog: runtime probe failed (${failure_count}/${WATCHDOG_FAILURE_THRESHOLD})"

if (( failure_count < WATCHDOG_FAILURE_THRESHOLD )); then
  exit 0
fi

if restart_cooldown_active; then
  log "Health watchdog: restart cooldown active, skipping recovery"
  exit 0
fi

attempt_recovery
sleep 5

if runtime_healthy; then
  write_state_value "${WATCHDOG_FAILURE_FILE}" 0
  log "Health watchdog: recovery succeeded"
  exit 0
fi

log "Health watchdog: recovery attempted but runtime is still unhealthy"
