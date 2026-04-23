#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
root="${1:-$(cd "${script_dir}/.." && pwd)}"
bind_host="${IELTS_POSTGRES_BIND_HOST:-127.0.0.1}"
port="${IELTS_POSTGRES_PORT:-55432}"
runtime_prefix="${IELTS_MAC_RUNTIME_PREFIX:-$HOME/.local/share/micromamba/envs/ielts-mac-runtime}"
env_file="${IELTS_MICROSERVICES_ENV_FILE:-${root}/backend/.env.microservices.local}"
runtime_dir="${root}/logs/runtime/postgres-microservices-mac"
data_dir="${runtime_dir}/data"
log_path="${runtime_dir}/postgres.log"
admin_user="${IELTS_POSTGRES_ADMIN_USER:-postgres}"
admin_password="${IELTS_POSTGRES_ADMIN_PASSWORD:-postgres}"

PATH="${runtime_prefix}/bin:${PATH}"
export PATH

log() {
  printf '[postgres-local] %s\n' "$1"
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
    if pg_isready -h "${bind_host}" -p "${port}" -U "${admin_user}" >/dev/null 2>&1; then
      return 0
    fi
    sleep 1
  done
  printf '[ERROR] PostgreSQL did not become ready on %s:%s\n' "${bind_host}" "${port}" >&2
  exit 1
}

create_cluster_if_needed() {
  if [[ -f "${data_dir}/PG_VERSION" ]]; then
    return 0
  fi

  mkdir -p "${runtime_dir}"
  local pwfile
  pwfile="$(mktemp)"
  printf '%s\n' "${admin_password}" > "${pwfile}"
  initdb -D "${data_dir}" -U "${admin_user}" --pwfile="${pwfile}" >/dev/null
  rm -f "${pwfile}"
}

ensure_started() {
  mkdir -p "${runtime_dir}"
  if pg_isready -h "${bind_host}" -p "${port}" -U "${admin_user}" >/dev/null 2>&1; then
    log "PostgreSQL already ready on postgresql://${admin_user}@${bind_host}:${port}/postgres"
    return 0
  fi

  pg_ctl -D "${data_dir}" -l "${log_path}" -o "-p ${port} -c autovacuum=off" start >/dev/null
  wait_ready
}

ensure_service_databases() {
  python - "${env_file}" "${bind_host}" "${port}" "${admin_user}" "${admin_password}" <<'PY'
from __future__ import annotations

import sys
from pathlib import Path
from urllib.parse import urlparse

import psycopg2
from psycopg2 import sql


env_path = Path(sys.argv[1])
host = sys.argv[2]
port = int(sys.argv[3])
admin_user = sys.argv[4]
admin_password = sys.argv[5]

specs: list[tuple[str, str, str]] = []
for raw_line in env_path.read_text(encoding='utf-8-sig').splitlines():
    line = raw_line.strip()
    if not line or line.startswith('#') or '_DATABASE_URL=' not in line:
        continue
    _, value = line.split('=', 1)
    parsed = urlparse(value.strip())
    if not parsed.username or not parsed.password:
        continue
    database = parsed.path.lstrip('/')
    if not database:
        continue
    specs.append((parsed.username, parsed.password, database))

seen: set[tuple[str, str]] = set()
unique_specs = []
for user, password, database in specs:
    key = (user, database)
    if key in seen:
        continue
    seen.add(key)
    unique_specs.append((user, password, database))

conn = psycopg2.connect(
    host=host,
    port=port,
    user=admin_user,
    password=admin_password,
    dbname='postgres',
)
try:
    conn.autocommit = True
    with conn.cursor() as cursor:
        for user, password, database in unique_specs:
            cursor.execute('SELECT 1 FROM pg_roles WHERE rolname = %s', (user,))
            if cursor.fetchone():
                cursor.execute(sql.SQL('ALTER ROLE {} WITH LOGIN PASSWORD %s').format(sql.Identifier(user)), (password,))
            else:
                cursor.execute(sql.SQL('CREATE ROLE {} LOGIN PASSWORD %s').format(sql.Identifier(user)), (password,))

            cursor.execute('SELECT 1 FROM pg_database WHERE datname = %s', (database,))
            if not cursor.fetchone():
                cursor.execute(
                    sql.SQL('CREATE DATABASE {} OWNER {}').format(
                        sql.Identifier(database),
                        sql.Identifier(user),
                    )
                )
            cursor.execute(
                sql.SQL('ALTER DATABASE {} OWNER TO {}').format(
                    sql.Identifier(database),
                    sql.Identifier(user),
                )
            )
            cursor.execute(
                sql.SQL('GRANT ALL PRIVILEGES ON DATABASE {} TO {}').format(
                    sql.Identifier(database),
                    sql.Identifier(user),
                )
            )
finally:
    conn.close()
PY
}

require_command python
require_command initdb
require_command pg_ctl
require_command pg_isready
create_cluster_if_needed
ensure_started
ensure_service_databases
log "PostgreSQL ready on postgresql://${admin_user}@${bind_host}:${port}/postgres"
log "Data dir: ${data_dir}"
