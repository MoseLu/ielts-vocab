#!/usr/bin/env bash
set -euo pipefail

env_file="${1:-/etc/ielts-vocab/microservices.env}"
backup_root="${2:-/var/backups/ielts-vocab/postgres}"
retention_days="${RETENTION_DAYS:-7}"
timestamp="$(date -u +%Y%m%dT%H%M%SZ)"

set -a
# shellcheck disable=SC1090
. "${env_file}"
set +a

mkdir -p "${backup_root}/${timestamp}"
chmod 700 "${backup_root}"

for var_name in \
  IDENTITY_SERVICE_DATABASE_URL \
  LEARNING_CORE_SERVICE_DATABASE_URL \
  CATALOG_CONTENT_SERVICE_DATABASE_URL \
  AI_EXECUTION_SERVICE_DATABASE_URL \
  NOTES_SERVICE_DATABASE_URL \
  TTS_MEDIA_SERVICE_DATABASE_URL \
  ASR_SERVICE_DATABASE_URL \
  ADMIN_OPS_SERVICE_DATABASE_URL
do
  url="${!var_name:-}"
  if [[ -z "${url}" ]]; then
    echo "Skipping ${var_name}: not configured" >&2
    continue
  fi
  pg_dump "${url}" --format=custom --no-owner --file "${backup_root}/${timestamp}/${var_name}.dump"
done

find "${backup_root}" -mindepth 1 -maxdepth 1 -type d -mtime "+${retention_days}" -exec rm -rf {} +
echo "PostgreSQL backups written to ${backup_root}/${timestamp}"
