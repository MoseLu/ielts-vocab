#!/usr/bin/env bash
set -euo pipefail

service_name="${1:?service name is required}"
app_root="${IELTS_APP_ROOT:-/opt/ielts-vocab/current}"
venv_dir="${IELTS_VENV:-/opt/ielts-vocab/venv}"
host="${IELTS_SERVICE_HOST:-127.0.0.1}"

export MICROSERVICES_ENV_FILE="${MICROSERVICES_ENV_FILE:-/etc/ielts-vocab/microservices.env}"
export PYTHONPATH="${app_root}/backend:${app_root}/packages/platform-sdk:${PYTHONPATH:-}"

run_uvicorn() {
  local workdir="$1"
  local port="$2"
  cd "${app_root}/${workdir}"
  exec "${venv_dir}/bin/uvicorn" main:app \
    --host "${host}" \
    --port "${port}" \
    --proxy-headers \
    --forwarded-allow-ips "127.0.0.1"
}

case "${service_name}" in
  gateway-bff)
    run_uvicorn "apps/gateway-bff" "${GATEWAY_BFF_PORT:-8000}"
    ;;
  identity-service)
    run_uvicorn "services/identity-service" "${IDENTITY_SERVICE_PORT:-8101}"
    ;;
  learning-core-service)
    run_uvicorn "services/learning-core-service" "${LEARNING_CORE_SERVICE_PORT:-8102}"
    ;;
  catalog-content-service)
    run_uvicorn "services/catalog-content-service" "${CATALOG_CONTENT_SERVICE_PORT:-8103}"
    ;;
  ai-execution-service)
    run_uvicorn "services/ai-execution-service" "${AI_EXECUTION_SERVICE_PORT:-8104}"
    ;;
  tts-media-service)
    run_uvicorn "services/tts-media-service" "${TTS_MEDIA_SERVICE_PORT:-8105}"
    ;;
  asr-service)
    run_uvicorn "services/asr-service" "${ASR_SERVICE_PORT:-8106}"
    ;;
  notes-service)
    run_uvicorn "services/notes-service" "${NOTES_SERVICE_PORT:-8107}"
    ;;
  admin-ops-service)
    run_uvicorn "services/admin-ops-service" "${ADMIN_OPS_SERVICE_PORT:-8108}"
    ;;
  asr-socketio)
    export SPEECH_SERVICE_HOST="${SPEECH_SERVICE_HOST:-${host}}"
    export SPEECH_SERVICE_PORT="${SPEECH_SERVICE_PORT:-5001}"
    cd "${app_root}/services/asr-service"
    exec "${venv_dir}/bin/python" -u socketio_main.py
    ;;
  *)
    echo "Unknown service: ${service_name}" >&2
    exit 64
    ;;
esac
