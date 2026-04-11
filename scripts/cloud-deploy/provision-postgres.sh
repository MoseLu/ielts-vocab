#!/usr/bin/env bash
set -euo pipefail

env_file="${1:-/etc/ielts-vocab/microservices.env}"
db_host="${POSTGRES_HOST:-127.0.0.1}"
db_port="${POSTGRES_PORT:-5432}"
sslmode="${POSTGRES_SSLMODE:-disable}"
redis_host="${REDIS_HOST:-127.0.0.1}"
redis_port="${REDIS_PORT:-6379}"
redis_key_prefix="${REDIS_KEY_PREFIX:-ielts-vocab}"
rabbitmq_host="${RABBITMQ_HOST:-127.0.0.1}"
rabbitmq_port="${RABBITMQ_PORT:-5672}"
rabbitmq_user="${RABBITMQ_USER:-ielts_vocab}"
rabbitmq_password="${RABBITMQ_PASSWORD:-$(openssl rand -hex 24)}"
rabbitmq_vhost="${RABBITMQ_VHOST:-/ielts-vocab}"
rabbitmq_domain_exchange="${RABBITMQ_DOMAIN_EXCHANGE:-ielts-vocab.domain}"

services=(
  "IDENTITY_SERVICE:ielts_identity_service"
  "LEARNING_CORE_SERVICE:ielts_learning_core_service"
  "CATALOG_CONTENT_SERVICE:ielts_catalog_content_service"
  "AI_EXECUTION_SERVICE:ielts_ai_execution_service"
  "NOTES_SERVICE:ielts_notes_service"
  "TTS_MEDIA_SERVICE:ielts_tts_media_service"
  "ASR_SERVICE:ielts_asr_service"
  "ADMIN_OPS_SERVICE:ielts_admin_ops_service"
)
redis_db_assignments=(
  "GATEWAY_BFF_REDIS_DB=0"
  "IDENTITY_SERVICE_REDIS_DB=1"
  "LEARNING_CORE_SERVICE_REDIS_DB=2"
  "CATALOG_CONTENT_SERVICE_REDIS_DB=3"
  "AI_EXECUTION_SERVICE_REDIS_DB=4"
  "NOTES_SERVICE_REDIS_DB=5"
  "TTS_MEDIA_SERVICE_REDIS_DB=6"
  "ASR_SERVICE_REDIS_DB=7"
  "ADMIN_OPS_SERVICE_REDIS_DB=8"
)

psql_as_postgres() {
  su - postgres -c "psql -v ON_ERROR_STOP=1 -p ${db_port} -d postgres -Atc \"$1\""
}

sql_literal() {
  local value="${1//\'/\'\'}"
  printf "'%s'" "${value}"
}

mkdir -p "$(dirname "${env_file}")"
chmod 700 "$(dirname "${env_file}")"
{
  echo "POSTGRES_HOST=${db_host}"
  echo "POSTGRES_PORT=${db_port}"
  echo "POSTGRES_SSLMODE=${sslmode}"
  echo "DB_BACKUP_ENABLED=false"
  echo "REDIS_HOST=${redis_host}"
  echo "REDIS_PORT=${redis_port}"
  echo "REDIS_KEY_PREFIX=${redis_key_prefix}"
  for assignment in "${redis_db_assignments[@]}"; do
    echo "${assignment}"
  done
  echo "RABBITMQ_HOST=${rabbitmq_host}"
  echo "RABBITMQ_PORT=${rabbitmq_port}"
  echo "RABBITMQ_USER=${rabbitmq_user}"
  echo "RABBITMQ_PASSWORD=${rabbitmq_password}"
  echo "RABBITMQ_VHOST=${rabbitmq_vhost}"
  echo "RABBITMQ_DOMAIN_EXCHANGE=${rabbitmq_domain_exchange}"
  echo
} > "${env_file}"

for item in "${services[@]}"; do
  prefix="${item%%:*}"
  database="${item#*:}"
  role="${database}"
  password="$(openssl rand -hex 24)"

  if [[ "$(psql_as_postgres "SELECT 1 FROM pg_roles WHERE rolname = $(sql_literal "${role}")")" == "1" ]]; then
    psql_as_postgres "ALTER ROLE ${role} WITH LOGIN PASSWORD $(sql_literal "${password}")" >/dev/null
  else
    psql_as_postgres "CREATE ROLE ${role} LOGIN PASSWORD $(sql_literal "${password}")" >/dev/null
  fi

  if [[ "$(psql_as_postgres "SELECT 1 FROM pg_database WHERE datname = $(sql_literal "${database}")")" != "1" ]]; then
    psql_as_postgres "CREATE DATABASE ${database} OWNER ${role}" >/dev/null
  fi
  psql_as_postgres "ALTER DATABASE ${database} OWNER TO ${role}" >/dev/null
  psql_as_postgres "GRANT ALL PRIVILEGES ON DATABASE ${database} TO ${role}" >/dev/null

  echo "${prefix}_DATABASE_URL=postgresql://${role}:${password}@${db_host}:${db_port}/${database}?sslmode=${sslmode}" >> "${env_file}"
done

chmod 600 "${env_file}"
echo "Wrote ${env_file}"
