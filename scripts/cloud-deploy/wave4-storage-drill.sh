#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${script_dir}/release-common.sh"

PYTHON_BIN="${PYTHON_BIN:-${VENV_DIR}/bin/python}"
DRILL_RECORD_PATH="${DRILL_RECORD_PATH:-}"
DRILL_RECORD_ACTIVE="${DRILL_RECORD_ACTIVE:-false}"
DRILL_SCOPE="${DRILL_SCOPE:-owned}"
DRILL_RUN_REPAIR="${DRILL_RUN_REPAIR:-false}"
DRILL_RUN_STORAGE_PARITY="${DRILL_RUN_STORAGE_PARITY:-true}"
DRILL_SOURCE_SQLITE="${DRILL_SOURCE_SQLITE:-}"
DRILL_RUN_SMOKE="${DRILL_RUN_SMOKE:-true}"
DRILL_RUN_NOTES_EXPORT_VALIDATION="${DRILL_RUN_NOTES_EXPORT_VALIDATION:-true}"
DRILL_RUN_NOTES_EXPORT_REPAIR="${DRILL_RUN_NOTES_EXPORT_REPAIR:-false}"
DRILL_RUN_EXAMPLE_AUDIO_VALIDATION="${DRILL_RUN_EXAMPLE_AUDIO_VALIDATION:-true}"
DRILL_RUN_EXAMPLE_AUDIO_REPAIR="${DRILL_RUN_EXAMPLE_AUDIO_REPAIR:-false}"
DRILL_RUN_WORD_AUDIO_VALIDATION="${DRILL_RUN_WORD_AUDIO_VALIDATION:-true}"
DRILL_RUN_WORD_AUDIO_REPAIR="${DRILL_RUN_WORD_AUDIO_REPAIR:-false}"
DRILL_NOTES_USER_ID="${DRILL_NOTES_USER_ID:-1}"
DRILL_NOTES_START_DATE="${DRILL_NOTES_START_DATE:-}"
DRILL_NOTES_END_DATE="${DRILL_NOTES_END_DATE:-}"
DRILL_NOTES_FORMAT="${DRILL_NOTES_FORMAT:-md}"
DRILL_NOTES_TYPE="${DRILL_NOTES_TYPE:-all}"
DRILL_EXAMPLE_AUDIO_BOOK_ID="${DRILL_EXAMPLE_AUDIO_BOOK_ID:-}"
DRILL_EXAMPLE_AUDIO_LIMIT="${DRILL_EXAMPLE_AUDIO_LIMIT:-0}"
DRILL_EXAMPLE_AUDIO_VERBOSE="${DRILL_EXAMPLE_AUDIO_VERBOSE:-false}"
DRILL_WORD_AUDIO_BOOK_ID="${DRILL_WORD_AUDIO_BOOK_ID:-}"
DRILL_WORD_AUDIO_LIMIT="${DRILL_WORD_AUDIO_LIMIT:-0}"
DRILL_WORD_AUDIO_VERBOSE="${DRILL_WORD_AUDIO_VERBOSE:-false}"
DRILL_ROLLBACK_TARGET="${DRILL_ROLLBACK_TARGET:-}"
DRILL_EXECUTE_ROLLBACK="${DRILL_EXECUTE_ROLLBACK:-false}"


bool_is_true() {
  local raw="${1:-false}"
  [[ "${raw,,}" == "true" ]]
}


enable_recording_if_requested() {
  if [[ -z "${DRILL_RECORD_PATH}" ]] || bool_is_true "${DRILL_RECORD_ACTIVE}"; then
    return 0
  fi
  mkdir -p "$(dirname "${DRILL_RECORD_PATH}")"
  export DRILL_RECORD_ACTIVE="true"
  exec > >(tee -a "${DRILL_RECORD_PATH}") 2>&1
  log "Recording Wave 4 storage drill output to ${DRILL_RECORD_PATH}"
}


require_executable_file() {
  [[ -x "$1" ]] || fail "Missing executable file: $1"
}


source_runtime_env_files() {
  set -a
  # shellcheck source=/dev/null
  source "${BACKEND_ENV_FILE}"
  # shellcheck source=/dev/null
  source "${MICROSERVICES_ENV_FILE}"
  set +a
}


script_path() {
  local relative="${1:?relative path is required}"
  printf '%s\n' "${CURRENT_LINK}/${relative}"
}


run_python_script() {
  local relative="${1:?relative path is required}"
  shift
  local target
  target="$(script_path "${relative}")"
  require_file "${target}"
  log "Running ${relative} $*"
  "${PYTHON_BIN}" "${target}" "$@"
}


oss_configured() {
  [[ -n "${AXI_ALIYUN_OSS_ACCESS_KEY_ID:-}" ]] \
    && [[ -n "${AXI_ALIYUN_OSS_ACCESS_KEY_SECRET:-}" ]] \
    && [[ -n "${AXI_ALIYUN_OSS_PRIVATE_BUCKET:-}" ]] \
    && [[ -n "${AXI_ALIYUN_OSS_REGION:-}" ]]
}


validate_rollback_target() {
  local target="${1:-}"
  if [[ -z "${target}" ]]; then
    return 0
  fi
  local resolved
  resolved="$(readlink -f "${target}")"
  [[ -d "${resolved}" ]] || fail "Rollback target does not exist: ${resolved}"
  log "Rollback target validated: ${resolved}"
}


run_notes_export_validation() {
  local args=(
    "--user-id" "${DRILL_NOTES_USER_ID}"
    "--format" "${DRILL_NOTES_FORMAT}"
    "--type" "${DRILL_NOTES_TYPE}"
  )
  if [[ -n "${DRILL_NOTES_START_DATE}" ]]; then
    args+=("--start-date" "${DRILL_NOTES_START_DATE}")
  fi
  if [[ -n "${DRILL_NOTES_END_DATE}" ]]; then
    args+=("--end-date" "${DRILL_NOTES_END_DATE}")
  fi
  run_python_script "scripts/validate_notes_export_oss_reference.py" "${args[@]}"
}


run_notes_export_repair() {
  local args=(
    "--user-id" "${DRILL_NOTES_USER_ID}"
    "--format" "${DRILL_NOTES_FORMAT}"
    "--type" "${DRILL_NOTES_TYPE}"
  )
  if [[ -n "${DRILL_NOTES_START_DATE}" ]]; then
    args+=("--start-date" "${DRILL_NOTES_START_DATE}")
  fi
  if [[ -n "${DRILL_NOTES_END_DATE}" ]]; then
    args+=("--end-date" "${DRILL_NOTES_END_DATE}")
  fi
  run_python_script "scripts/repair_notes_export_oss_reference.py" "${args[@]}"
}


run_example_audio_validation() {
  local args=()
  if [[ -n "${DRILL_EXAMPLE_AUDIO_BOOK_ID}" ]]; then
    args+=("--book-id" "${DRILL_EXAMPLE_AUDIO_BOOK_ID}")
  fi
  if [[ "${DRILL_EXAMPLE_AUDIO_LIMIT}" != "0" ]]; then
    args+=("--limit" "${DRILL_EXAMPLE_AUDIO_LIMIT}")
  fi
  if bool_is_true "${DRILL_EXAMPLE_AUDIO_VERBOSE}"; then
    args+=("--verbose")
  fi
  run_python_script "scripts/validate_example_audio_oss_parity.py" "${args[@]}"
}


run_example_audio_repair() {
  local args=("--generate-missing" "--repair-size-mismatch" "--repair-content-type-mismatch")
  if [[ -n "${DRILL_EXAMPLE_AUDIO_BOOK_ID}" ]]; then
    args+=("--book-id" "${DRILL_EXAMPLE_AUDIO_BOOK_ID}")
  fi
  if [[ "${DRILL_EXAMPLE_AUDIO_LIMIT}" != "0" ]]; then
    args+=("--limit" "${DRILL_EXAMPLE_AUDIO_LIMIT}")
  fi
  run_python_script "scripts/backfill_example_audio_to_oss.py" "${args[@]}"
  run_example_audio_validation
}


run_word_audio_validation() {
  local args=()
  if [[ -n "${DRILL_WORD_AUDIO_BOOK_ID}" ]]; then
    args+=("--book-id" "${DRILL_WORD_AUDIO_BOOK_ID}")
  fi
  if [[ "${DRILL_WORD_AUDIO_LIMIT}" != "0" ]]; then
    args+=("--limit" "${DRILL_WORD_AUDIO_LIMIT}")
  fi
  if bool_is_true "${DRILL_WORD_AUDIO_VERBOSE}"; then
    args+=("--verbose")
  fi
  run_python_script "scripts/validate_word_audio_oss_parity.py" "${args[@]}"
}


run_word_audio_repair() {
  local args=("--repair-size-mismatch" "--repair-content-type-mismatch")
  if [[ -n "${DRILL_WORD_AUDIO_BOOK_ID}" ]]; then
    args+=("--book-id" "${DRILL_WORD_AUDIO_BOOK_ID}")
  fi
  if [[ "${DRILL_WORD_AUDIO_LIMIT}" != "0" ]]; then
    args+=("--limit" "${DRILL_WORD_AUDIO_LIMIT}")
  fi
  run_python_script "scripts/backfill_word_audio_to_oss.py" "${args[@]}"
  run_word_audio_validation
}


run_storage_parity_check() {
  local args=(
    "--scope" "${DRILL_SCOPE}"
    "--env-file" "${MICROSERVICES_ENV_FILE}"
  )
  if [[ -n "${DRILL_SOURCE_SQLITE}" ]]; then
    args+=("--source-sqlite" "${DRILL_SOURCE_SQLITE}")
  fi

  if bool_is_true "${DRILL_RUN_REPAIR}"; then
    if run_python_script "scripts/validate_microservice_storage_parity.py" "${args[@]}"; then
      log "Initial storage parity validation matched; continuing into repair verification"
    else
      log "Initial storage parity validation reported drift; continuing into repair because DRILL_RUN_REPAIR=true"
    fi
    run_python_script "scripts/repair_microservice_storage_parity.py" "${args[@]}"
    return 0
  fi

  run_python_script "scripts/validate_microservice_storage_parity.py" "${args[@]}"
}


main() {
  enable_recording_if_requested
  require_command bash
  require_command curl
  require_command readlink
  require_file "${BACKEND_ENV_FILE}"
  require_file "${MICROSERVICES_ENV_FILE}"
  require_executable_file "${PYTHON_BIN}"
  require_file "$(script_path "scripts/validate_microservice_storage_parity.py")"
  require_file "$(script_path "scripts/repair_microservice_storage_parity.py")"
  require_file "$(script_path "scripts/validate_notes_export_oss_reference.py")"
  require_file "$(script_path "scripts/repair_notes_export_oss_reference.py")"
  require_file "$(script_path "scripts/validate_example_audio_oss_parity.py")"
  require_file "$(script_path "scripts/backfill_example_audio_to_oss.py")"
  require_file "$(script_path "scripts/validate_word_audio_oss_parity.py")"
  require_file "$(script_path "scripts/backfill_word_audio_to_oss.py")"

  source_runtime_env_files

  log "Wave 4 remote storage drill starting"
  log "Current release: $(current_target_path)"
  validate_rollback_target "${DRILL_ROLLBACK_TARGET}"
  if bool_is_true "${DRILL_RUN_STORAGE_PARITY}"; then
    run_storage_parity_check
  else
    log "Skipping SQLite parity validation because DRILL_RUN_STORAGE_PARITY=false"
  fi

  if oss_configured; then
    if bool_is_true "${DRILL_RUN_NOTES_EXPORT_REPAIR}"; then
      run_notes_export_repair
    elif bool_is_true "${DRILL_RUN_NOTES_EXPORT_VALIDATION}"; then
      run_notes_export_validation
    fi
    if bool_is_true "${DRILL_RUN_EXAMPLE_AUDIO_REPAIR}"; then
      run_example_audio_repair
    elif bool_is_true "${DRILL_RUN_EXAMPLE_AUDIO_VALIDATION}"; then
      run_example_audio_validation
    fi
    if bool_is_true "${DRILL_RUN_WORD_AUDIO_REPAIR}"; then
      run_word_audio_repair
    elif bool_is_true "${DRILL_RUN_WORD_AUDIO_VALIDATION}"; then
      run_word_audio_validation
    fi
  else
    log "Aliyun OSS env is not configured; skipping object-reference validation"
  fi

  if bool_is_true "${DRILL_RUN_SMOKE}"; then
    "${script_dir}/smoke-check.sh"
  fi

  if [[ -n "${DRILL_ROLLBACK_TARGET}" ]]; then
    log "Rollback rehearsal target: $(readlink -f "${DRILL_ROLLBACK_TARGET}")"
    if bool_is_true "${DRILL_EXECUTE_ROLLBACK}"; then
      log "Executing real rollback as requested"
      "${script_dir}/rollback-release.sh" "${DRILL_ROLLBACK_TARGET}"
    else
      log "Rollback execution skipped; set DRILL_EXECUTE_ROLLBACK=true to run it"
    fi
  fi

  log "Wave 4 remote storage drill completed"
}


main "$@"
