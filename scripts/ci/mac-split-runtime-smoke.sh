#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
root="${1:-$(cd "${script_dir}/../.." && pwd)}"
ports_to_cleanup=(5001 8000 8101 8102 8103 8104 8105 8106 8107 8108)
backend_env="${root}/backend/.env"
backend_env_example="${root}/backend/.env.example"
microservices_env="${root}/backend/.env.microservices.local"
microservices_env_example="${root}/backend/.env.microservices.local.example"
start_script="${root}/start-microservices.sh"
startup_pid=''

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

wait_http_ready() {
  local url="$1"
  local deadline=$((SECONDS + 240))
  while (( SECONDS < deadline )); do
    local status
    status="$(curl -s -o /dev/null -w '%{http_code}' "${url}" || true)"
    if [[ "${status}" =~ ^[234][0-9][0-9]$ ]]; then
      return 0
    fi
    sleep 2
  done
  printf '[ERROR] Timed out waiting for %s\n' "${url}" >&2
  exit 1
}

ensure_backend_env() {
  if [[ -f "${backend_env}" ]]; then
    return 0
  fi
  if [[ -f "${backend_env_example}" ]]; then
    cp "${backend_env_example}" "${backend_env}"
    return 0
  fi
  cat > "${backend_env}" <<'EOF'
SECRET_KEY=ci-secret-key
JWT_SECRET_KEY=ci-jwt-secret-key
COOKIE_SECURE=false
EMAIL_CODE_DELIVERY_MODE=mock
ADMIN_INITIAL_PASSWORD=admin123
EOF
}

ensure_microservices_env() {
  if [[ -f "${microservices_env}" ]]; then
    return 0
  fi
  if [[ ! -f "${microservices_env_example}" ]]; then
    printf '[ERROR] Missing microservices env example: %s\n' "${microservices_env_example}" >&2
    exit 1
  fi
  cp "${microservices_env_example}" "${microservices_env}"
}

cleanup() {
  if [[ -n "${startup_pid}" ]] && kill -0 "${startup_pid}" >/dev/null 2>&1; then
    kill "${startup_pid}" >/dev/null 2>&1 || true
    sleep 1
    kill -9 "${startup_pid}" >/dev/null 2>&1 || true
  fi
  for port in "${ports_to_cleanup[@]}"; do
    stop_port_listener "${port}"
  done
}

trap cleanup EXIT

ensure_backend_env
ensure_microservices_env

for port in "${ports_to_cleanup[@]}"; do
  stop_port_listener "${port}"
done

"${start_script}" --project-root "${root}" --skip-frontend-checks &
startup_pid=$!

wait_http_ready 'http://127.0.0.1:8000/health'
cd "${root}"
pnpm --dir frontend exec playwright test tests/e2e/smoke.spec.ts --project=chromium
