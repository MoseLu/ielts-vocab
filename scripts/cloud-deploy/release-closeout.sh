#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${script_dir}/release-common.sh"

CLOSEOUT_TIMESTAMP="${CLOSEOUT_TIMESTAMP:-$(date -u +%Y%m%dT%H%M%SZ)}"
CLOSEOUT_HOST="${CLOSEOUT_HOST:-119.29.182.134}"
CLOSEOUT_LOG_DIR="${CLOSEOUT_LOG_DIR:-/var/log/ielts-vocab/release-closeout/${CLOSEOUT_TIMESTAMP}}"
CLOSEOUT_SMOKE_HOST="${SMOKE_HOST:-axiomaticworld.com}"
CLOSEOUT_NOTES_USER_ID="${CLOSEOUT_NOTES_USER_ID:-1}"
CLOSEOUT_BOUNDED_BOOK_ID="${CLOSEOUT_BOUNDED_BOOK_ID:-ielts_reading_premium}"
CLOSEOUT_BOUNDED_LIMIT="${CLOSEOUT_BOUNDED_LIMIT:-200}"

require_file "${BACKEND_ENV_FILE}"
require_file "${MICROSERVICES_ENV_FILE}"
require_command bash
require_command tee
require_command mkdir

mkdir -p "${CLOSEOUT_LOG_DIR}"

log "Release closeout starting"
log "Host: ${CLOSEOUT_HOST}"
log "Current release: $(current_target_path)"
log "Log directory: ${CLOSEOUT_LOG_DIR}"

{
  log "Running post-switch smoke"
  SMOKE_HOST="${CLOSEOUT_SMOKE_HOST}" "${script_dir}/smoke-check.sh"
} 2>&1 | tee "${CLOSEOUT_LOG_DIR}/smoke.log"

{
  log "Running bounded storage drill"
  DRILL_RUN_STORAGE_PARITY="${CLOSEOUT_RUN_STORAGE_PARITY:-false}" \
  DRILL_NOTES_USER_ID="${CLOSEOUT_NOTES_USER_ID}" \
  DRILL_SOURCE_SQLITE="${CLOSEOUT_SOURCE_SQLITE:-${DRILL_SOURCE_SQLITE:-}}" \
  DRILL_EXAMPLE_AUDIO_BOOK_ID="${CLOSEOUT_BOUNDED_BOOK_ID}" \
  DRILL_EXAMPLE_AUDIO_LIMIT="${CLOSEOUT_BOUNDED_LIMIT}" \
  DRILL_WORD_AUDIO_BOOK_ID="${CLOSEOUT_BOUNDED_BOOK_ID}" \
  DRILL_WORD_AUDIO_LIMIT="${CLOSEOUT_BOUNDED_LIMIT}" \
  SMOKE_HOST="${CLOSEOUT_SMOKE_HOST}" \
    "${script_dir}/wave4-storage-drill.sh"
} 2>&1 | tee "${CLOSEOUT_LOG_DIR}/storage-drill.log"

{
  log "Running projection verify"
  PYTHONPATH="${CURRENT_LINK}/backend:${CURRENT_LINK}/packages/platform-sdk:${PYTHONPATH:-}" \
    "${VENV_DIR}/bin/python" "${CURRENT_LINK}/scripts/run-wave5-projection-cutover.py" --verify-only
} 2>&1 | tee "${CLOSEOUT_LOG_DIR}/projection-verify.log"

log "Release closeout completed successfully"
log "Evidence directory: ${CLOSEOUT_LOG_DIR}"
