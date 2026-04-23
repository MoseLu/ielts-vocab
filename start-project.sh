#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
root="${script_dir}"
allow_dirty_compatibility_drill=false
use_monolith_compatibility=false
skip_redis=false
skip_rabbit=false
skip_frontend_build=false
monolith_compat_route_groups=""
monolith_compat_surface="all"
monolith_compat_backend_port=5000
frontend_port=3002
gateway_port=8000
speech_port=5001
runtime_prefix="${IELTS_MAC_RUNTIME_PREFIX:-$HOME/.local/share/micromamba/envs/ielts-mac-runtime}"

while (($#)); do
  case "$1" in
    --project-root)
      root="$(cd "$2" && pwd)"
      shift 2
      ;;
    --allow-dirty-compatibility-drill)
      allow_dirty_compatibility_drill=true
      shift
      ;;
    --use-monolith-compatibility)
      use_monolith_compatibility=true
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
    --skip-frontend-build)
      skip_frontend_build=true
      shift
      ;;
    --monolith-compat-route-groups)
      monolith_compat_route_groups="$2"
      shift 2
      ;;
    --monolith-compat-surface)
      monolith_compat_surface="$2"
      shift 2
      ;;
    --monolith-compat-backend-port)
      monolith_compat_backend_port="$2"
      shift 2
      ;;
    *)
      printf '[ERROR] Unknown argument: %s\n' "$1" >&2
      exit 64
      ;;
  esac
done

setup_script="${root}/scripts/setup-mac-runtime.sh"
microservices_script="${root}/start-microservices.sh"
log_dir="${root}/logs/runtime"
frontend_out="${log_dir}/frontend-preview.out.log"
frontend_err="${log_dir}/frontend-preview.err.log"
backend_out="${log_dir}/backend-compat.out.log"
backend_err="${log_dir}/backend-compat.err.log"
speech_out="${log_dir}/speech-compat.out.log"
speech_err="${log_dir}/speech-compat.err.log"

PATH="${runtime_prefix}/bin:${PATH}"
export PATH

log() {
  printf '[start-project] %s\n' "$1"
}

require_command() {
  command -v "$1" >/dev/null 2>&1 || {
    printf '[ERROR] Required command not found: %s\n' "$1" >&2
    exit 1
  }
}

ensure_runtime() {
  if [[ ! -x "${runtime_prefix}/bin/python" ]]; then
    "${setup_script}"
  fi
  PATH="${runtime_prefix}/bin:${PATH}"
  export PATH
  require_command python
  require_command pnpm
  require_command curl
  require_command lsof
}

wait_http_ready() {
  local label="$1"
  local url="$2"
  local deadline=$((SECONDS + 60))
  while (( SECONDS < deadline )); do
    local status=0
    status="$(curl -s -o /dev/null -w '%{http_code}' "${url}" || true)"
    if [[ "${status}" =~ ^[234][0-9][0-9]$ ]]; then
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

start_background() {
  local label="$1"
  local stdout_log="$2"
  local stderr_log="$3"
  shift 3
  local command_line
  printf -v command_line '%q ' "$@"
  : > "${stdout_log}"
  : > "${stderr_log}"
  nohup bash -lc "${command_line}" >>"${stdout_log}" 2>>"${stderr_log}" < /dev/null &
  log "Started ${label}"
}

resolve_monolith_probe_path() {
  if [[ -n "${monolith_compat_route_groups}" && "${monolith_compat_surface}" != "all" ]]; then
    printf '[ERROR] Use either --monolith-compat-route-groups or --monolith-compat-surface, not both.\n' >&2
    exit 64
  fi

  local raw_json
  if [[ -n "${monolith_compat_route_groups}" ]]; then
    raw_json="$(python "${root}/scripts/resolve-monolith-compat-route-groups.py" --surface "${monolith_compat_surface}" --route-groups "${monolith_compat_route_groups}" --json)"
  else
    raw_json="$(python "${root}/scripts/resolve-monolith-compat-route-groups.py" --surface "${monolith_compat_surface}" --json)"
  fi

  printf '%s' "${raw_json}" | python - <<'PY'
import json
import sys
payload = json.load(sys.stdin)
print(payload["probe_path"])
PY
}

ensure_runtime
mkdir -p "${log_dir}"

if [[ "${allow_dirty_compatibility_drill}" == "true" ]]; then
  log 'Dirty compatibility drill override enabled.'
fi

stop_port_listener "${frontend_port}"

if [[ "${use_monolith_compatibility}" == "true" ]]; then
  local_probe_path="$(resolve_monolith_probe_path)"
  stop_port_listener "${monolith_compat_backend_port}"
  stop_port_listener "${speech_port}"
  export ALLOW_MONOLITH_COMPAT_RUNTIME=1
  if [[ -n "${monolith_compat_route_groups}" ]]; then
    export MONOLITH_COMPAT_ROUTE_GROUPS="${monolith_compat_route_groups}"
  elif [[ "${monolith_compat_surface}" != "all" ]]; then
    export MONOLITH_COMPAT_ROUTE_GROUPS="$(python "${root}/scripts/resolve-monolith-compat-route-groups.py" --surface "${monolith_compat_surface}")"
  fi
  export BACKEND_PORT="${monolith_compat_backend_port}"
  export VITE_API_PROXY_TARGET="http://127.0.0.1:${monolith_compat_backend_port}"
  start_background 'backend-compat' "${backend_out}" "${backend_err}" python "${root}/backend/app.py"
  start_background 'speech-compat' "${speech_out}" "${speech_err}" python "${root}/backend/speech_service.py"
  wait_http_ready 'compat backend probe' "http://127.0.0.1:${monolith_compat_backend_port}${local_probe_path}"
  wait_http_ready 'compat speech ready' "http://127.0.0.1:${speech_port}/ready"
  log "Legacy backend/app.py on port ${monolith_compat_backend_port} is compatibility-only."
else
  microservices_args=(--project-root "${root}" --skip-frontend-checks)
  if [[ "${skip_redis}" == "true" ]]; then
    microservices_args+=(--skip-redis)
  fi
  if [[ "${skip_rabbit}" == "true" ]]; then
    microservices_args+=(--skip-rabbit)
  fi
  "${microservices_script}" "${microservices_args[@]}"
  export BACKEND_PORT="${gateway_port}"
  export VITE_API_PROXY_TARGET="http://127.0.0.1:${gateway_port}"
  wait_http_ready 'gateway ready' "http://127.0.0.1:${gateway_port}/health"
fi

if [[ "${skip_frontend_build}" != "true" ]]; then
  pnpm --dir "${root}/frontend" build
else
  log 'Skipping frontend build and reusing existing dist.'
fi
start_background 'frontend-preview' "${frontend_out}" "${frontend_err}" env CI=1 node "${root}/frontend/node_modules/vite/bin/vite.js" preview --host 127.0.0.1 --port "${frontend_port}"
wait_http_ready 'preview login' "http://127.0.0.1:${frontend_port}/login"
wait_http_ready 'preview api proxy' "http://127.0.0.1:${frontend_port}/api/books/stats"

log 'Local production-style startup completed.'
printf '       Frontend:           http://127.0.0.1:%s/login\n' "${frontend_port}"
printf '       Gateway API:        http://127.0.0.1:%s\n' "${gateway_port}"
printf '       Compatibility path: ./start-monolith-compat.sh\n'
