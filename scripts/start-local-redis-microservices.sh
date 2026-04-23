#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
root="${1:-$(cd "${script_dir}/.." && pwd)}"
bind_host="${IELTS_REDIS_BIND_HOST:-127.0.0.1}"
port="${IELTS_REDIS_PORT:-56379}"
runtime_prefix="${IELTS_MAC_RUNTIME_PREFIX:-$HOME/.local/share/micromamba/envs/ielts-mac-runtime}"
runtime_dir="${root}/logs/runtime/redis-microservices-mac"
data_dir="${runtime_dir}/data"
log_path="${runtime_dir}/redis.log"
config_path="${runtime_dir}/redis.local.conf"
pid_path="${runtime_dir}/redis.pid"

PATH="${runtime_prefix}/bin:${PATH}"
export PATH

log() {
  printf '[redis-local] %s\n' "$1"
}

require_command() {
  command -v "$1" >/dev/null 2>&1 || {
    printf '[ERROR] Required command not found: %s\n' "$1" >&2
    exit 1
  }
}

wait_ready() {
  local deadline=$((SECONDS + 30))
  while (( SECONDS < deadline )); do
    if redis-cli -h "${bind_host}" -p "${port}" ping 2>/dev/null | grep -q '^PONG'; then
      return 0
    fi
    sleep 1
  done
  printf '[ERROR] Redis did not become ready on %s:%s\n' "${bind_host}" "${port}" >&2
  exit 1
}

mkdir -p "${runtime_dir}" "${data_dir}"
require_command redis-server
require_command redis-cli

if redis-cli -h "${bind_host}" -p "${port}" ping 2>/dev/null | grep -q '^PONG'; then
  log "Redis already ready on redis://${bind_host}:${port}/0"
  exit 0
fi

cat > "${config_path}" <<EOF
bind ${bind_host}
port ${port}
dir ${data_dir}
dbfilename dump.rdb
save ""
appendonly no
daemonize yes
pidfile ${pid_path}
logfile ${log_path}
EOF

redis-server "${config_path}" >/dev/null
wait_ready
log "Redis ready on redis://${bind_host}:${port}/0"
log "Runtime dir: ${runtime_dir}"
