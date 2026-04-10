#!/usr/bin/env bash
set -euo pipefail

APP_HOME="${APP_HOME:-/opt/ielts-vocab}"
CURRENT_LINK="${CURRENT_LINK:-${APP_HOME}/current}"
REPOSITORY_ROOT="${REPOSITORY_ROOT:-${APP_HOME}/repository}"
RELEASES_ROOT="${RELEASES_ROOT:-${APP_HOME}/releases}"
VENV_DIR="${VENV_DIR:-${APP_HOME}/venv}"
WEB_ROOT="${WEB_ROOT:-/var/www/ielts-vocab}"
BACKEND_ENV_FILE="${BACKEND_ENV_FILE:-/etc/ielts-vocab/backend.env}"
MICROSERVICES_ENV_FILE="${MICROSERVICES_ENV_FILE:-/etc/ielts-vocab/microservices.env}"
SMOKE_HOST="${SMOKE_HOST:-axiomaticworld.com}"
RELEASE_RETENTION_COUNT="${RELEASE_RETENTION_COUNT:-5}"

SERVICE_UNITS=(
  "gateway-bff"
  "identity-service"
  "learning-core-service"
  "catalog-content-service"
  "ai-execution-service"
  "tts-media-service"
  "asr-service"
  "notes-service"
  "admin-ops-service"
  "asr-socketio"
)

log() {
  printf '[%s] %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*"
}

fail() {
  log "ERROR: $*"
  exit 1
}

require_command() {
  command -v "$1" >/dev/null 2>&1 || fail "Missing required command: $1"
}

require_file() {
  [[ -f "$1" ]] || fail "Missing required file: $1"
}

ensure_release_directories() {
  mkdir -p "${APP_HOME}" "${RELEASES_ROOT}" "${WEB_ROOT}"
}

sync_repository_origin() {
  local source_origin=""
  if [[ -d "${CURRENT_LINK}/.git" ]]; then
    source_origin="$(git -C "${CURRENT_LINK}" remote get-url origin 2>/dev/null || true)"
  fi
  if [[ -z "${source_origin}" ]]; then
    return 0
  fi
  if git -C "${REPOSITORY_ROOT}" remote get-url origin >/dev/null 2>&1; then
    git -C "${REPOSITORY_ROOT}" remote set-url origin "${source_origin}"
  else
    git -C "${REPOSITORY_ROOT}" remote add origin "${source_origin}"
  fi
}

prepare_repository_root() {
  if [[ -d "${REPOSITORY_ROOT}/.git" ]]; then
    sync_repository_origin
    return 0
  fi
  if [[ -d "${CURRENT_LINK}/.git" ]]; then
    log "Bootstrapping repository cache from ${CURRENT_LINK}"
    git clone --no-hardlinks "${CURRENT_LINK}" "${REPOSITORY_ROOT}"
    sync_repository_origin
    return 0
  fi
  fail "Repository cache missing and ${CURRENT_LINK} is not a git checkout"
}

fetch_git_commit() {
  local git_ref="${1:?git ref is required}"
  if [[ "${git_ref}" =~ ^[0-9a-f]{7,40}$ ]]; then
    git -C "${REPOSITORY_ROOT}" fetch --tags origin "${git_ref}" >/dev/null 2>&1
    git -C "${REPOSITORY_ROOT}" rev-parse --verify "FETCH_HEAD^{commit}"
    return 0
  fi
  git -C "${REPOSITORY_ROOT}" fetch --tags origin "refs/heads/${git_ref}:refs/remotes/origin/${git_ref}" >/dev/null 2>&1
  git -C "${REPOSITORY_ROOT}" rev-parse --verify "refs/remotes/origin/${git_ref}^{commit}"
}

ensure_python_runtime() {
  if [[ ! -x "${VENV_DIR}/bin/python" ]]; then
    python3 -m venv "${VENV_DIR}"
  fi
  "${VENV_DIR}/bin/pip" install --upgrade pip wheel
}

ensure_node_runtime() {
  require_command node
  require_command corepack
  corepack enable
  corepack prepare pnpm@9.0.0 --activate
}

install_release_dependencies() {
  local release_dir="${1:?release dir is required}"
  ensure_python_runtime
  ensure_node_runtime
  "${VENV_DIR}/bin/pip" install \
    -r "${release_dir}/backend/requirements.txt" \
    -r "${release_dir}/services/requirements.txt"
  "${VENV_DIR}/bin/pip" install -e "${release_dir}/packages/platform-sdk"
  pnpm --dir "${release_dir}" install --frozen-lockfile
  pnpm --dir "${release_dir}" build
}

hydrate_release_git_index() {
  local release_dir="${1:?release dir is required}"
  git -C "${release_dir}" init -q
  git -C "${release_dir}" add -A
}

copy_frontend_dist() {
  local release_dir="${1:?release dir is required}"
  [[ -d "${release_dir}/dist" ]] || fail "Missing frontend build output in ${release_dir}/dist"
  mkdir -p "${WEB_ROOT}"
  find "${WEB_ROOT}" -mindepth 1 -maxdepth 1 -exec rm -rf {} +
  cp -a "${release_dir}/dist/." "${WEB_ROOT}/"
}

current_target_path() {
  if [[ -L "${CURRENT_LINK}" ]]; then
    readlink -f "${CURRENT_LINK}"
    return 0
  fi
  if [[ -d "${CURRENT_LINK}" ]]; then
    printf '%s\n' "${CURRENT_LINK}"
    return 0
  fi
  printf '\n'
}

stage_current_directory_as_legacy_release() {
  local suffix="${1:?suffix is required}"
  local legacy_dir="${RELEASES_ROOT}/legacy-${suffix}"
  if [[ ! -e "${CURRENT_LINK}" || -L "${CURRENT_LINK}" ]]; then
    return 1
  fi
  mv "${CURRENT_LINK}" "${legacy_dir}"
  printf '%s\n' "${legacy_dir}"
}

set_current_release() {
  local target_dir="${1:?target dir is required}"
  local temp_link="${CURRENT_LINK}.tmp"
  ln -sfn "${target_dir}" "${temp_link}"
  mv -Tf "${temp_link}" "${CURRENT_LINK}"
}

run_backup_script() {
  local backup_script=""
  if [[ -x "${CURRENT_LINK}/scripts/cloud-deploy/backup-postgres.sh" ]]; then
    backup_script="${CURRENT_LINK}/scripts/cloud-deploy/backup-postgres.sh"
  elif [[ -x "${REPOSITORY_ROOT}/scripts/cloud-deploy/backup-postgres.sh" ]]; then
    backup_script="${REPOSITORY_ROOT}/scripts/cloud-deploy/backup-postgres.sh"
  fi
  [[ -n "${backup_script}" ]] || fail "Could not find backup-postgres.sh"
  "${backup_script}" "${MICROSERVICES_ENV_FILE}"
}

restart_service_units() {
  systemctl daemon-reload
  for service in "${SERVICE_UNITS[@]}"; do
    systemctl restart "ielts-service@${service}"
  done
}

cleanup_old_releases() {
  local keep_primary="${1:-}"
  local keep_secondary="${2:-}"
  local retained=0
  mapfile -t release_dirs < <(list_release_dirs)
  for dir in "${release_dirs[@]}"; do
    if [[ -n "${keep_primary}" && "${dir}" == "${keep_primary}" ]]; then
      continue
    fi
    if [[ -n "${keep_secondary}" && "${dir}" == "${keep_secondary}" ]]; then
      continue
    fi
    retained=$((retained + 1))
    if (( retained > RELEASE_RETENTION_COUNT )); then
      rm -rf "${dir}"
    fi
  done
}

list_release_dirs() {
  find "${RELEASES_ROOT}" -mindepth 1 -maxdepth 1 -type d | sort -r
}
