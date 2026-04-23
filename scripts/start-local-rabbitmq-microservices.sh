#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
root="${1:-$(cd "${script_dir}/.." && pwd)}"
bind_host="${IELTS_RABBITMQ_BIND_HOST:-127.0.0.1}"
port="${IELTS_RABBITMQ_PORT:-5679}"
runtime_prefix="${IELTS_MAC_RUNTIME_PREFIX:-$HOME/.local/share/micromamba/envs/ielts-mac-runtime}"
runtime_dir="${root}/logs/runtime/rabbitmq-microservices-mac"
config_base="${runtime_dir}/rabbitmq"
config_path="${config_base}.conf"
node_name="${IELTS_RABBITMQ_NODE_NAME:-ielts_vocab_local}"
dist_port="${IELTS_RABBITMQ_DIST_PORT:-25679}"
log_base="${runtime_dir}/log"
db_base="${runtime_dir}/db"

PATH="${runtime_prefix}/bin:${PATH}"
export PATH

log() {
  printf '[rabbitmq-local] %s\n' "$1"
}

require_command() {
  command -v "$1" >/dev/null 2>&1 || {
    printf '[ERROR] Required command not found: %s\n' "$1" >&2
    exit 1
  }
}

wait_ready() {
  local deadline=$((SECONDS + 60))
  while (( SECONDS < deadline )); do
    if RABBITMQ_NODE_PORT="${port}" \
      RABBITMQ_DIST_PORT="${dist_port}" \
      RABBITMQ_NODENAME="${node_name}" \
      RABBITMQ_CONFIG_FILE="${config_base}" \
      RABBITMQ_LOG_BASE="${log_base}" \
      RABBITMQ_MNESIA_BASE="${db_base}" \
      rabbitmq-diagnostics -q ping >/dev/null 2>&1; then
      return 0
    fi
    sleep 1
  done
  printf '[ERROR] RabbitMQ did not become ready on %s:%s\n' "${bind_host}" "${port}" >&2
  exit 1
}

mkdir -p "${runtime_dir}" "${log_base}" "${db_base}"
require_command rabbitmq-server
require_command rabbitmq-diagnostics

cat > "${config_path}" <<EOF
listeners.tcp.default = ${port}
loopback_users.guest = false
management.tcp.port = 15679
EOF

export RABBITMQ_NODE_PORT="${port}"
export RABBITMQ_DIST_PORT="${dist_port}"
export RABBITMQ_NODENAME="${node_name}"
export RABBITMQ_CONFIG_FILE="${config_base}"
export RABBITMQ_LOG_BASE="${log_base}"
export RABBITMQ_MNESIA_BASE="${db_base}"

if rabbitmq-diagnostics -q ping >/dev/null 2>&1; then
  log "RabbitMQ already ready on amqp://guest:guest@${bind_host}:${port}/%2F"
  exit 0
fi

rabbitmq-server -detached >/dev/null 2>&1
wait_ready
log "RabbitMQ ready on amqp://guest:guest@${bind_host}:${port}/%2F"
log "Runtime dir: ${runtime_dir}"
