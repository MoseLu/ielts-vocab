#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
root="${script_dir}"
skip_frontend_checks=false
skip_redis=false
skip_rabbit=false
runtime_prefix="${IELTS_MAC_RUNTIME_PREFIX:-$HOME/.local/share/micromamba/envs/ielts-mac-runtime}"

while (($#)); do
  case "$1" in
    --project-root)
      root="$(cd "$2" && pwd)"
      shift 2
      ;;
    --skip-frontend-checks)
      skip_frontend_checks=true
      shift
      ;;
    --skip-redis)
      skip_redis=true
      shift
      ;;
    --skip-rabbit)
      skip_rabbit=true
      shift
      ;;
    *)
      printf '[ERROR] Unknown argument: %s\n' "$1" >&2
      exit 64
      ;;
  esac
done

setup_script="${root}/scripts/setup-mac-runtime.sh"
backend_env="${root}/backend/.env"
microservices_env="${root}/backend/.env.microservices.local"
runtime_dir="${root}/logs/runtime/app-services-mac"
postgres_script="${root}/scripts/start-local-postgres-microservices.sh"
redis_script="${root}/scripts/start-local-redis-microservices.sh"
rabbit_script="${root}/scripts/start-local-rabbitmq-microservices.sh"

PATH="${runtime_prefix}/bin:${PATH}"
export PATH

port_base="${PORT:?workspace port lease is required}"
port_for() { printf '%s' "$((port_base + $1))"; }
gateway_port="$(port_for 0)"
identity_port="$(port_for 1)"
learning_port="$(port_for 2)"
catalog_port="$(port_for 3)"
ai_execution_port="$(port_for 4)"
tts_port="$(port_for 5)"
asr_http_port="$(port_for 6)"
notes_port="$(port_for 7)"
admin_port="$(port_for 8)"
asr_socketio_port="$(port_for 9)"
export GATEWAY_BFF_PORT="$gateway_port" IDENTITY_SERVICE_PORT="$identity_port" LEARNING_CORE_SERVICE_PORT="$learning_port"
export CATALOG_CONTENT_SERVICE_PORT="$catalog_port" AI_EXECUTION_SERVICE_PORT="$ai_execution_port" TTS_MEDIA_SERVICE_PORT="$tts_port"
export ASR_SERVICE_PORT="$asr_http_port" NOTES_SERVICE_PORT="$notes_port" ADMIN_OPS_SERVICE_PORT="$admin_port"
export SPEECH_SERVICE_PORT="$asr_socketio_port"

service_defs=(
  "gateway-bff|${gateway_port}|apps/gateway-bff|python -u ${root}/apps/gateway-bff/main.py|http://127.0.0.1:${gateway_port}/health"
  "identity-service|${identity_port}|services/identity-service|python -u ${root}/services/identity-service/main.py|http://127.0.0.1:${identity_port}/ready"
  "learning-core-service|${learning_port}|services/learning-core-service|python -u ${root}/services/learning-core-service/main.py|http://127.0.0.1:${learning_port}/ready"
  "catalog-content-service|${catalog_port}|services/catalog-content-service|python -u ${root}/services/catalog-content-service/main.py|http://127.0.0.1:${catalog_port}/ready"
  "ai-execution-service|${ai_execution_port}|services/ai-execution-service|python -u ${root}/services/ai-execution-service/main.py|http://127.0.0.1:${ai_execution_port}/ready"
  "tts-media-service|${tts_port}|services/tts-media-service|python -u ${root}/services/tts-media-service/main.py|http://127.0.0.1:${tts_port}/ready"
  "asr-service|${asr_http_port}|services/asr-service|python -u ${root}/services/asr-service/main.py|http://127.0.0.1:${asr_http_port}/ready"
  "notes-service|${notes_port}|services/notes-service|python -u ${root}/services/notes-service/main.py|http://127.0.0.1:${notes_port}/ready"
  "admin-ops-service|${admin_port}|services/admin-ops-service|python -u ${root}/services/admin-ops-service/main.py|http://127.0.0.1:${admin_port}/ready"
  "asr-socketio|${asr_socketio_port}|services/asr-service|python -u ${root}/services/asr-service/socketio_main.py|http://127.0.0.1:${asr_socketio_port}/ready"
)
worker_defs=(
  "core-eventing-worker|services/identity-service|python -u ${root}/services/identity-service/eventing_worker.py"
  "notes-domain-worker|services/notes-service|python -u ${root}/services/notes-service/domain_worker.py"
  "ai-execution-domain-worker|services/ai-execution-service|python -u ${root}/services/ai-execution-service/domain_worker.py"
  "admin-ops-domain-worker|services/admin-ops-service|python -u ${root}/services/admin-ops-service/domain_worker.py"
)
replaced_worker_names=(
  "identity-outbox-publisher"
  "learning-core-outbox-publisher"
  "tts-media-outbox-publisher"
  "ai-execution-outbox-publisher"
  "ai-wrong-word-projection-worker"
  "ai-daily-summary-projection-worker"
  "notes-outbox-publisher"
  "notes-study-session-projection-worker"
  "notes-wrong-word-projection-worker"
  "notes-prompt-run-projection-worker"
  "admin-user-projection-worker"
  "admin-study-session-projection-worker"
  "admin-daily-summary-projection-worker"
  "admin-prompt-run-projection-worker"
  "admin-tts-media-projection-worker"
  "admin-wrong-word-projection-worker"
)

log() {
  printf '[app-services-mac] %s\n' "$1"
}

require_command() {
  command -v "$1" >/dev/null 2>&1 || {
    printf '[ERROR] Required command not found: %s\n' "$1" >&2
    exit 1
  }
}

ensure_runtime() {
  if [[ ! -x "${runtime_prefix}/bin/python" ]]; then
    bash "${setup_script}"
  fi
  PATH="${runtime_prefix}/bin:${PATH}"
  export PATH
  require_command python
  require_command curl
  require_command lsof
}

wait_http_ready() {
  local label="$1"
  local url="$2"
  local deadline=$((SECONDS + 60))
  while (( SECONDS < deadline )); do
    if curl -fsS --max-time 5 "${url}" >/dev/null 2>&1; then
      log "Ready: ${label}"
      return 0
    fi
    sleep 1
  done
  printf '[ERROR] Timed out waiting for %s -> %s\n' "${label}" "${url}" >&2
  exit 1
}

stop_port_listener() {
  local port="$1"
  local pids=()
  while IFS= read -r pid; do
    [[ -n "${pid}" ]] && pids+=("${pid}")
  done < <(lsof -tiTCP:"${port}" -sTCP:LISTEN 2>/dev/null || true)
  if ((${#pids[@]} == 0)); then
    return 0
  fi
  kill "${pids[@]}" >/dev/null 2>&1 || true
  sleep 1
  kill -9 "${pids[@]}" >/dev/null 2>&1 || true
}

stop_pidfile_process() {
  local pidfile="$1"
  [[ -f "${pidfile}" ]] || return 0
  local pid
  pid="$(<"${pidfile}")"
  if [[ -n "${pid}" ]] && kill -0 "${pid}" >/dev/null 2>&1; then
    kill "${pid}" >/dev/null 2>&1 || true
    sleep 1
    kill -9 "${pid}" >/dev/null 2>&1 || true
  fi
  rm -f "${pidfile}"
}

start_logged_process() {
  local name="$1"
  local workdir="$2"
  local command_line="$3"
  local stdout_log="${runtime_dir}/${name}.out.log"
  local stderr_log="${runtime_dir}/${name}.err.log"
  local pidfile="${runtime_dir}/${name}.pid"

  # PRD-07 phase 2: rotate any prior logs over 50 MB before
  # truncating. Keeps the file size bounded so Promtail can
  # ingest the tail without paying the full history on every
  # restart.
  for log in "${stdout_log}" "${stderr_log}"; do
    if [[ -f "${log}" ]] && (( $(stat -f%z "${log}" 2>/dev/null || echo 0) > 52428800 )); then
      mv "${log}" "${log}.$(date +%Y%m%d-%H%M%S).rotated"
      gzip -f "${log}."*.rotated 2>/dev/null || true
    fi
  done

  : > "${stdout_log}"
  : > "${stderr_log}"
  (
    cd "${root}/${workdir}"
    export BACKEND_ENV_FILE="${backend_env}"
    export MICROSERVICES_ENV_FILE="${microservices_env}"
    export PYTHONPATH="${root}/backend:${root}/packages/platform-sdk${PYTHONPATH:+:${PYTHONPATH}}"
    nohup bash -c "${command_line}" >>"${stdout_log}" 2>>"${stderr_log}" &
    process_pid=$!
    echo "${process_pid}" > "${pidfile}"
    disown "${process_pid}" >/dev/null 2>&1 || true
  )
}

ensure_runtime
mkdir -p "${runtime_dir}"
[[ -f "${backend_env}" ]] || { printf '[ERROR] Missing backend env file: %s\n' "${backend_env}" >&2; exit 1; }
[[ -f "${microservices_env}" ]] || { printf '[ERROR] Missing microservices env file: %s\n' "${microservices_env}" >&2; exit 1; }

bash "${postgres_script}" "${root}"
if [[ "${skip_redis}" != "true" ]]; then
  bash "${redis_script}" "${root}"
fi
if [[ "${skip_rabbit}" != "true" ]]; then
  bash "${rabbit_script}" "${root}"
fi

python "${root}/scripts/run-service-schema-migrations.py" --env-file "${microservices_env}"

for worker_name in "${replaced_worker_names[@]}"; do
  stop_pidfile_process "${runtime_dir}/${worker_name}.pid"
done

for definition in "${service_defs[@]}"; do
  IFS='|' read -r name port workdir command_line health <<<"${definition}"
  stop_port_listener "${port}"
  stop_pidfile_process "${runtime_dir}/${name}.pid"
  start_logged_process "${name}" "${workdir}" "${command_line}"
  wait_http_ready "${name}" "${health}"
done

for definition in "${worker_defs[@]}"; do
  IFS='|' read -r name workdir command_line <<<"${definition}"
  stop_pidfile_process "${runtime_dir}/${name}.pid"
  start_logged_process "${name}" "${workdir}" "${command_line}"
  sleep 2
  if ! kill -0 "$(<"${runtime_dir}/${name}.pid")" >/dev/null 2>&1; then
    printf '[ERROR] %s exited during startup. Check %s/%s.out.log and .err.log\n' "${name}" "${runtime_dir}" "${name}" >&2
    exit 1
  fi
done

if [[ "${skip_frontend_checks}" != "true" ]]; then
  log "Gateway ready at http://127.0.0.1:${gateway_port}"
fi
log 'Microservice backend started successfully.'
printf '       Gateway:           http://127.0.0.1:%s\n' "${gateway_port}"
printf '       Identity:          http://127.0.0.1:%s\n' "${identity_port}"
printf '       Learning core:     http://127.0.0.1:%s\n' "${learning_port}"
printf '       Catalog content:   http://127.0.0.1:%s\n' "${catalog_port}"
printf '       AI execution:      http://127.0.0.1:%s\n' "${ai_execution_port}"
printf '       TTS media:         http://127.0.0.1:%s\n' "${tts_port}"
printf '       ASR HTTP:          http://127.0.0.1:%s\n' "${asr_http_port}"
printf '       Notes:             http://127.0.0.1:%s\n' "${notes_port}"
printf '       Admin ops:         http://127.0.0.1:%s\n' "${admin_port}"
printf '       ASR Socket.IO:     http://127.0.0.1:%s\n' "${asr_socketio_port}"
printf '       Core worker:       core-eventing-worker\n'
printf '       Notes worker:      notes-domain-worker\n'
printf '       AI worker:         ai-execution-domain-worker\n'
printf '       Admin worker:      admin-ops-domain-worker\n'
printf '       Runtime logs:      %s\n' "${runtime_dir}"
