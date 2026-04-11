#!/usr/bin/env bash
set -euo pipefail

env_file="${1:-/etc/ielts-vocab/microservices.env}"
python_bin="${PYTHON_BIN:-python3}"
dnf_bin="${DNF_BIN:-dnf}"
systemctl_bin="${SYSTEMCTL_BIN:-systemctl}"
redis_cli_bin="${REDIS_CLI_BIN:-redis-cli}"
rabbitmqctl_bin="${RABBITMQCTL_BIN:-rabbitmqctl}"
rabbitmq_diagnostics_bin="${RABBITMQ_DIAGNOSTICS_BIN:-rabbitmq-diagnostics}"

require_command() {
  command -v "$1" >/dev/null 2>&1 || {
    printf '[ERROR] Missing required command: %s\n' "$1" >&2
    exit 1
  }
}

require_file() {
  [[ -f "$1" ]] || {
    printf '[ERROR] Missing required file: %s\n' "$1" >&2
    exit 1
  }
}

require_command "${dnf_bin}"
require_command "${systemctl_bin}"
require_command "${python_bin}"
require_file "${env_file}"

eval "$(
"${python_bin}" - "${env_file}" <<'PY'
from __future__ import annotations

import sys
from pathlib import Path

env_file = Path(sys.argv[1])
env_values: dict[str, str] = {}
for raw_line in env_file.read_text(encoding='utf-8').splitlines():
    line = raw_line.strip()
    if not line or line.startswith('#') or '=' not in line:
        continue
    key, value = line.split('=', 1)
    key = key.strip()
    value = value.strip()
    if key:
        env_values[key] = value

redis_host = (env_values.get('REDIS_HOST') or '127.0.0.1').strip() or '127.0.0.1'
redis_port = (env_values.get('REDIS_PORT') or '6379').strip() or '6379'
rabbitmq_host = (env_values.get('RABBITMQ_HOST') or '127.0.0.1').strip() or '127.0.0.1'
rabbitmq_port = (env_values.get('RABBITMQ_PORT') or '5672').strip() or '5672'
rabbitmq_user = (env_values.get('RABBITMQ_USER') or 'guest').strip() or 'guest'
rabbitmq_password = (env_values.get('RABBITMQ_PASSWORD') or 'guest').strip() or 'guest'
rabbitmq_vhost = (env_values.get('RABBITMQ_VHOST') or '/').strip() or '/'

for key, value in (
    ('REDIS_HOST', redis_host),
    ('REDIS_PORT', redis_port),
    ('RABBITMQ_HOST', rabbitmq_host),
    ('RABBITMQ_PORT', rabbitmq_port),
    ('RABBITMQ_USER', rabbitmq_user),
    ('RABBITMQ_PASSWORD', rabbitmq_password),
    ('RABBITMQ_VHOST', rabbitmq_vhost),
):
    escaped = value.replace('\\', '\\\\').replace('"', '\\"')
    print(f'{key}="{escaped}"')
PY
)"

if [[ "${REDIS_HOST}" != "127.0.0.1" && "${REDIS_HOST}" != "localhost" ]]; then
  printf '[ERROR] This script only provisions a local Redis baseline, got REDIS_HOST=%s\n' "${REDIS_HOST}" >&2
  exit 1
fi
if [[ "${RABBITMQ_HOST}" != "127.0.0.1" && "${RABBITMQ_HOST}" != "localhost" ]]; then
  printf '[ERROR] This script only provisions a local RabbitMQ baseline, got RABBITMQ_HOST=%s\n' "${RABBITMQ_HOST}" >&2
  exit 1
fi
if [[ "${REDIS_PORT}" != "6379" ]]; then
  printf '[ERROR] This script expects REDIS_PORT=6379, got %s\n' "${REDIS_PORT}" >&2
  exit 1
fi
if [[ "${RABBITMQ_PORT}" != "5672" ]]; then
  printf '[ERROR] This script expects RABBITMQ_PORT=5672, got %s\n' "${RABBITMQ_PORT}" >&2
  exit 1
fi

printf '[INFO] Installing Redis and RabbitMQ packages\n'
"${dnf_bin}" install -y redis rabbitmq-server

printf '[INFO] Enabling Redis and RabbitMQ services\n'
"${systemctl_bin}" enable --now redis rabbitmq-server

require_command "${redis_cli_bin}"
require_command "${rabbitmqctl_bin}"
require_command "${rabbitmq_diagnostics_bin}"

if [[ "${RABBITMQ_VHOST}" != "/" ]]; then
  if ! "${rabbitmqctl_bin}" list_vhosts | tail -n +2 | awk '{print $1}' | grep -Fxq "${RABBITMQ_VHOST}"; then
    printf '[INFO] Creating RabbitMQ vhost %s\n' "${RABBITMQ_VHOST}"
    "${rabbitmqctl_bin}" add_vhost "${RABBITMQ_VHOST}"
  fi
fi

if [[ "${RABBITMQ_USER}" != "guest" || "${RABBITMQ_PASSWORD}" != "guest" ]]; then
  if "${rabbitmqctl_bin}" list_users | tail -n +2 | awk '{print $1}' | grep -Fxq "${RABBITMQ_USER}"; then
    printf '[INFO] Updating RabbitMQ user password for %s\n' "${RABBITMQ_USER}"
    "${rabbitmqctl_bin}" change_password "${RABBITMQ_USER}" "${RABBITMQ_PASSWORD}"
  else
    printf '[INFO] Creating RabbitMQ user %s\n' "${RABBITMQ_USER}"
    "${rabbitmqctl_bin}" add_user "${RABBITMQ_USER}" "${RABBITMQ_PASSWORD}"
  fi
fi

printf '[INFO] Granting RabbitMQ permissions on %s to %s\n' "${RABBITMQ_VHOST}" "${RABBITMQ_USER}"
"${rabbitmqctl_bin}" set_permissions -p "${RABBITMQ_VHOST}" "${RABBITMQ_USER}" '.*' '.*' '.*'

printf '[INFO] Validating Redis readiness\n'
"${redis_cli_bin}" -h "${REDIS_HOST}" -p "${REDIS_PORT}" PING

printf '[INFO] Validating RabbitMQ readiness\n'
"${rabbitmq_diagnostics_bin}" -q ping

printf '[DONE] Wave 5 broker runtime provisioned for %s and %s\n' "${REDIS_HOST}:${REDIS_PORT}" "${RABBITMQ_HOST}:${RABBITMQ_PORT}"
