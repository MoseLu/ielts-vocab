#!/usr/bin/env bash
set -euo pipefail

instance="${1:?slot.service instance is required}"
slot="${instance%%.*}"
service_name="${instance#*.}"

case "${slot}" in
  blue|green) ;;
  *)
    echo "Unknown HTTP slot: ${slot}" >&2
    exit 64
    ;;
esac

if [[ -z "${service_name}" || "${service_name}" == "${instance}" ]]; then
  echo "Expected instance format <slot>.<service>, got: ${instance}" >&2
  exit 64
fi

case "${service_name}" in
  gateway-bff|identity-service|learning-core-service|catalog-content-service|ai-execution-service|tts-media-service|asr-service|notes-service|admin-ops-service) ;;
  *)
    echo "Unknown HTTP slot service: ${service_name}" >&2
    exit 64
    ;;
esac

app_home="${APP_HOME:-/opt/ielts-vocab}"
slot_root="${HTTP_SLOTS_ROOT:-${app_home}/http-slots}/${slot}"
app_root="${slot_root}/current"
slot_env="${HTTP_SLOT_ENV_DIR:-/etc/ielts-vocab/http-slots}/${slot}.env"
backend_env="${BACKEND_ENV_FILE:-/etc/ielts-vocab/backend.env}"
microservices_env="${MICROSERVICES_ENV_FILE:-/etc/ielts-vocab/microservices.env}"

[[ -d "${app_root}" ]] || { echo "Missing HTTP slot release: ${app_root}" >&2; exit 66; }
[[ -f "${slot_env}" ]] || { echo "Missing HTTP slot env: ${slot_env}" >&2; exit 66; }
[[ -f "${app_root}/scripts/cloud-deploy/run-service.sh" ]] || {
  echo "Missing release run-service.sh under ${app_root}" >&2
  exit 66
}

set -a
[[ -f "${backend_env}" ]] && source "${backend_env}"
[[ -f "${microservices_env}" ]] && source "${microservices_env}"
source "${slot_env}"
set +a

export APP_HOME="${app_home}"
export IELTS_APP_ROOT="${app_root}"
export IELTS_VENV="${IELTS_VENV:-/opt/ielts-vocab/venv}"
export IELTS_SERVICE_HOST="${IELTS_SERVICE_HOST:-127.0.0.1}"
export MICROSERVICES_ENV_FILE="${microservices_env}"
export IELTS_HTTP_SLOT="${slot}"
export IELTS_HTTP_SLOT_ENV_FILE="${slot_env}"

exec "${app_root}/scripts/cloud-deploy/run-service.sh" "${service_name}"
