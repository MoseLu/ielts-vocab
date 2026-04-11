#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${script_dir}/release-common.sh"

PYTHON_BIN="${PYTHON_BIN:-${VENV_DIR}/bin/python}"
SYSTEMCTL_BIN="${SYSTEMCTL_BIN:-systemctl}"
VALIDATOR_PATH="${VALIDATOR_PATH:-${CURRENT_LINK}/scripts/validate_wave5_broker_runtime.py}"

require_command "${SYSTEMCTL_BIN}"
require_command "${PYTHON_BIN}"
require_file "${BACKEND_ENV_FILE}"
require_file "${MICROSERVICES_ENV_FILE}"
require_file "${VALIDATOR_PATH}"

log "Validating remote broker systemd baseline"
"${SYSTEMCTL_BIN}" is-active --quiet redis
"${SYSTEMCTL_BIN}" is-active --quiet rabbitmq-server

log "Running Wave 5 broker runtime validation"
"${PYTHON_BIN}" "${VALIDATOR_PATH}" --env-file "${MICROSERVICES_ENV_FILE}"

log "Wave 5 broker runtime validation passed"
