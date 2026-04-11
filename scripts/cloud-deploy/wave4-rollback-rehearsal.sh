#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
source "${script_dir}/release-common.sh"

REHEARSAL_TARGET_RELEASE="${REHEARSAL_TARGET_RELEASE:-${1:-}}"
REHEARSAL_RESTORE_RELEASE="${REHEARSAL_RESTORE_RELEASE:-}"
REHEARSAL_EXECUTE="${REHEARSAL_EXECUTE:-false}"
REHEARSAL_RUN_STORAGE_DRILL="${REHEARSAL_RUN_STORAGE_DRILL:-true}"
REHEARSAL_RECORD_PATH="${REHEARSAL_RECORD_PATH:-}"
REHEARSAL_RECORD_ACTIVE="${REHEARSAL_RECORD_ACTIVE:-false}"

restored="false"
restore_release=""


bool_is_true() {
  local raw="${1:-false}"
  [[ "${raw,,}" == "true" ]]
}


enable_recording_if_requested() {
  if [[ -z "${REHEARSAL_RECORD_PATH}" ]] || bool_is_true "${REHEARSAL_RECORD_ACTIVE}"; then
    return 0
  fi
  mkdir -p "$(dirname "${REHEARSAL_RECORD_PATH}")"
  export REHEARSAL_RECORD_ACTIVE="true"
  exec > >(tee -a "${REHEARSAL_RECORD_PATH}") 2>&1
  log "Recording Wave 4 rollback rehearsal output to ${REHEARSAL_RECORD_PATH}"
}


resolve_release_path() {
  local target="${1:?target release is required}"
  readlink -f "${target}"
}


validate_release_path() {
  local label="${1:?label is required}"
  local target="${2:?target release is required}"
  [[ -d "${target}" ]] || fail "${label} does not exist: ${target}"
}


is_rollback_capable_release() {
  local target="${1:?target release is required}"
  [[ -d "${target}" ]] || return 1
  [[ -d "${target}/dist" ]]
}


validate_rollback_capable_release() {
  local label="${1:?label is required}"
  local target="${2:?target release is required}"
  validate_release_path "${label}" "${target}"
  is_rollback_capable_release "${target}" || fail "${label} is missing frontend build output: ${target}/dist"
}


select_target_release() {
  local current_release="${1:?current release is required}"
  if [[ -n "${REHEARSAL_TARGET_RELEASE}" ]]; then
    resolve_release_path "${REHEARSAL_TARGET_RELEASE}"
    return 0
  fi

  local candidate=""
  while IFS= read -r candidate; do
    [[ -n "${candidate}" ]] || continue
    candidate="$(resolve_release_path "${candidate}")"
    if ! is_rollback_capable_release "${candidate}"; then
      continue
    fi
    if [[ "${candidate}" != "${current_release}" ]]; then
      printf '%s\n' "${candidate}"
      return 0
    fi
  done < <(list_release_dirs)

  fail "Could not resolve a rollback rehearsal target distinct from ${current_release}"
}


print_plan() {
  local current_release="${1:?current release is required}"
  local target_release="${2:?target release is required}"
  local restore_release_path="${3:?restore release is required}"

  log "Wave 4 rollback rehearsal"
  log "Current release: ${current_release}"
  log "Target release: ${target_release}"
  log "Restore release: ${restore_release_path}"
  log "Execute mode: ${REHEARSAL_EXECUTE}"
  log "Storage drill after restore: ${REHEARSAL_RUN_STORAGE_DRILL}"
}


run_storage_drill_after_restore() {
  if ! bool_is_true "${REHEARSAL_RUN_STORAGE_DRILL}"; then
    return 0
  fi

  local drill_script="${script_dir}/wave4-storage-drill.sh"
  require_file "${drill_script}"
  log "Running Wave 4 storage drill after restore"
  "${drill_script}"
}


attempt_best_effort_restore() {
  if [[ -z "${restore_release}" ]]; then
    return 0
  fi
  log "Rehearsal did not finish cleanly; attempting best-effort restore to ${restore_release}"
  if "${script_dir}/rollback-release.sh" "${restore_release}"; then
    log "Best-effort restore succeeded"
    return 0
  fi
  log "Best-effort restore failed; manual rollback required: ${script_dir}/rollback-release.sh ${restore_release}"
  return 1
}


cleanup() {
  if bool_is_true "${REHEARSAL_EXECUTE}" && [[ "${restored}" != "true" ]]; then
    attempt_best_effort_restore || true
  fi
}


main() {
  trap cleanup EXIT
  enable_recording_if_requested

  require_command readlink
  require_command bash
  require_file "${BACKEND_ENV_FILE}"
  require_file "${MICROSERVICES_ENV_FILE}"

  local current_release
  current_release="$(current_target_path)"
  [[ -n "${current_release}" ]] || fail "Could not resolve current release"
  current_release="$(resolve_release_path "${current_release}")"
  validate_rollback_capable_release "Current release" "${current_release}"

  local target_release
  target_release="$(select_target_release "${current_release}")"
  validate_rollback_capable_release "Rollback rehearsal target" "${target_release}"
  [[ "${target_release}" != "${current_release}" ]] || fail "Rollback rehearsal target matches current release"

  if [[ -n "${REHEARSAL_RESTORE_RELEASE}" ]]; then
    restore_release="$(resolve_release_path "${REHEARSAL_RESTORE_RELEASE}")"
  else
    restore_release="${current_release}"
  fi
  validate_rollback_capable_release "Rollback rehearsal restore release" "${restore_release}"
  [[ "${restore_release}" != "${target_release}" ]] || fail "Restore release matches rollback target"

  print_plan "${current_release}" "${target_release}" "${restore_release}"

  if ! bool_is_true "${REHEARSAL_EXECUTE}"; then
    log "Dry-run only; set REHEARSAL_EXECUTE=true to run the real rollback rehearsal"
    log "Rollback command: ${script_dir}/rollback-release.sh ${target_release}"
    log "Restore command: ${script_dir}/rollback-release.sh ${restore_release}"
    return 0
  fi

  log "Executing rollback rehearsal to ${target_release}"
  "${script_dir}/rollback-release.sh" "${target_release}"

  log "Restoring original release ${restore_release}"
  "${script_dir}/rollback-release.sh" "${restore_release}"
  restored="true"

  run_storage_drill_after_restore
  log "Wave 4 rollback rehearsal completed successfully"
}


main "$@"
