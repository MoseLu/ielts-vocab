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
DEPLOY_RUNTIME_DIR="${DEPLOY_RUNTIME_DIR:-/run/ielts-vocab}"
DEPLOY_LOCK_FILE="${DEPLOY_LOCK_FILE:-${DEPLOY_RUNTIME_DIR}/deploy.lock}"
DEPLOY_BUILD_CPU_QUOTA="${DEPLOY_BUILD_CPU_QUOTA:-50%}"
DEPLOY_BUILD_MEMORY_HIGH="${DEPLOY_BUILD_MEMORY_HIGH:-1280M}"
DEPLOY_BUILD_MEMORY_MAX="${DEPLOY_BUILD_MEMORY_MAX:-1536M}"
DEPLOY_BUILD_NICE="${DEPLOY_BUILD_NICE:-15}"
DEPLOY_BUILD_NODE_MAX_OLD_SPACE_MB="${DEPLOY_BUILD_NODE_MAX_OLD_SPACE_MB:-512}"
DEPLOY_BUILD_NPM_JOBS="${DEPLOY_BUILD_NPM_JOBS:-1}"
RELEASE_ARTIFACT_ENV_FILE="${RELEASE_ARTIFACT_ENV_FILE:-.release-artifact.env}"

HTTP_SERVICE_UNITS=(
  "gateway-bff"
  "identity-service"
  "learning-core-service"
  "catalog-content-service"
  "ai-execution-service"
  "tts-media-service"
  "asr-service"
  "notes-service"
  "admin-ops-service"
)
SINGLE_INSTANCE_CORE_UNITS=(
  "asr-socketio"
)
CORE_SERVICE_UNITS=("${HTTP_SERVICE_UNITS[@]}" "${SINGLE_INSTANCE_CORE_UNITS[@]}")
WAVE5_WORKER_UNITS=(
  "identity-outbox-publisher"
  "learning-core-outbox-publisher"
  "ai-execution-outbox-publisher"
  "ai-wrong-word-projection-worker"
  "ai-daily-summary-projection-worker"
  "notes-outbox-publisher"
  "notes-study-session-projection-worker"
  "notes-wrong-word-projection-worker"
  "notes-prompt-run-projection-worker"
  "tts-media-outbox-publisher"
  "admin-user-projection-worker"
  "admin-study-session-projection-worker"
  "admin-daily-summary-projection-worker"
  "admin-prompt-run-projection-worker"
  "admin-tts-media-projection-worker"
  "admin-wrong-word-projection-worker"
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

source "${BASH_SOURCE[0]%/*}/http-slot-common.sh"

ensure_release_directories() {
  mkdir -p "${APP_HOME}" "${RELEASES_ROOT}" "${WEB_ROOT}" "${DEPLOY_RUNTIME_DIR}"
  ensure_http_slot_directories
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
  local corepack_cmd=""
  require_command node
  if command -v corepack.cmd >/dev/null 2>&1; then
    corepack_cmd="corepack.cmd"
  elif command -v corepack >/dev/null 2>&1; then
    corepack_cmd="corepack"
  else
    fail "Missing required command: corepack"
  fi
  "${corepack_cmd}" enable
  "${corepack_cmd}" prepare pnpm@9.0.0 --activate
}

run_deploy_job() {
  local label="${1:?label is required}"
  shift

  if ! command -v systemd-run >/dev/null 2>&1; then
    "$@"
    return 0
  fi

  local unit_name="ielts-release-${label}-$(date +%s)-$$"
  systemd-run --quiet --wait --collect --pipe \
    --service-type=exec \
    --unit "${unit_name}" \
    -p CPUAccounting=yes \
    -p MemoryAccounting=yes \
    -p CPUQuota="${DEPLOY_BUILD_CPU_QUOTA}" \
    -p MemoryHigh="${DEPLOY_BUILD_MEMORY_HIGH}" \
    -p MemoryMax="${DEPLOY_BUILD_MEMORY_MAX}" \
    -p Nice="${DEPLOY_BUILD_NICE}" \
    -p IOSchedulingClass=best-effort \
    -p IOSchedulingPriority=7 \
    -p TasksMax=256 \
    "$@"
}

write_deploy_lock() {
  mkdir -p "${DEPLOY_RUNTIME_DIR}"
  cat > "${DEPLOY_LOCK_FILE}" <<EOF
pid=$$
started_at=$(date +%s)
release_ref=${1:-unknown}
EOF
}

clear_deploy_lock() {
  rm -f "${DEPLOY_LOCK_FILE}"
}

release_python_dependency_fingerprint() {
  local release_dir="${1:?release dir is required}"
  python3 - "${release_dir}" <<'PY'
import hashlib
import pathlib
import sys

release_dir = pathlib.Path(sys.argv[1])
manifest_paths = (
    'backend/requirements.txt',
    'services/requirements.txt',
    'packages/platform-sdk/pyproject.toml',
    'packages/platform-sdk/setup.py',
    'packages/platform-sdk/setup.cfg',
)

digest = hashlib.sha256()
for relative_path in manifest_paths:
    path = release_dir / relative_path
    if not path.is_file():
        continue
    digest.update(f'FILE:{relative_path}\n'.encode('utf-8'))
    digest.update(path.read_bytes())
    digest.update(b'\n')
print(digest.hexdigest())
PY
}

release_python_dependencies_match_current() {
  local release_dir="${1:?release dir is required}"
  local current_release=""
  current_release="$(current_target_path)"
  [[ -n "${current_release}" && -d "${current_release}" ]] || return 1
  [[ "$(release_python_dependency_fingerprint "${current_release}")" == "$(release_python_dependency_fingerprint "${release_dir}")" ]]
}

install_release_python_dependencies() {
  local release_dir="${1:?release dir is required}"
  ensure_python_runtime
  if release_python_dependencies_match_current "${release_dir}"; then
    log "Python dependency manifests unchanged; skipping pip requirements install"
  else
    log "Installing Python dependencies under deploy resource limits"
    run_deploy_job "python-deps" "${VENV_DIR}/bin/pip" install \
      -r "${release_dir}/backend/requirements.txt" \
      -r "${release_dir}/services/requirements.txt"
  fi
  log "Installing editable platform-sdk package"
  run_deploy_job "platform-sdk" "${VENV_DIR}/bin/pip" install --no-deps -e "${release_dir}/packages/platform-sdk"
}

build_release_frontend() {
  local release_dir="${1:?release dir is required}"
  ensure_node_runtime
  log "Installing workspace dependencies under deploy resource limits"
  run_deploy_job "node-install" env \
    CI=1 \
    npm_config_jobs="${DEPLOY_BUILD_NPM_JOBS}" \
    pnpm --dir "${release_dir}" install --frozen-lockfile
  log "Building frontend under deploy resource limits"
  run_deploy_job "frontend-build" env \
    CI=1 \
    npm_config_jobs="${DEPLOY_BUILD_NPM_JOBS}" \
    NODE_OPTIONS="--max-old-space-size=${DEPLOY_BUILD_NODE_MAX_OLD_SPACE_MB}" \
    pnpm --dir "${release_dir}" build
}

install_release_dependencies() {
  local release_dir="${1:?release dir is required}"
  install_release_python_dependencies "${release_dir}"
  build_release_frontend "${release_dir}"
}

release_artifact_env_path() {
  local release_dir="${1:?release dir is required}"
  printf '%s/%s\n' "${release_dir}" "${RELEASE_ARTIFACT_ENV_FILE}"
}

read_release_artifact_value() {
  local release_dir="${1:?release dir is required}"
  local key="${2:?key is required}"
  local env_file=""

  env_file="$(release_artifact_env_path "${release_dir}")"
  if [[ ! -f "${env_file}" ]]; then
    printf '\n'
    return 0
  fi
  awk -F= -v target="${key}" '$1 == target { sub(/^[^=]+=*/, "", $0); print $0; exit }' "${env_file}"
}

release_has_prebuilt_frontend() {
  local release_dir="${1:?release dir is required}"
  [[ -d "${release_dir}/dist" ]] || return 1
  [[ "$(read_release_artifact_value "${release_dir}" "prebuilt_dist")" == "true" ]]
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

link_frontend_dist() {
  local release_dir="${1:?release dir is required}"
  switch_frontend_to_release "${release_dir}"
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

release_supports_wave5_workers() {
  local release_dir="${1:?release dir is required}"
  local run_service="${release_dir}/scripts/cloud-deploy/run-service.sh"
  [[ -f "${run_service}" ]] || return 1

  for worker in "${WAVE5_WORKER_UNITS[@]}"; do
    grep -Fq "  ${worker})" "${run_service}" || return 1
  done
}

restart_service_units() {
  local target_release=""
  systemctl daemon-reload

  for service in "${CORE_SERVICE_UNITS[@]}"; do
    systemctl restart "ielts-service@${service}"
  done

  target_release="$(current_target_path)"
  if [[ -n "${target_release}" && -d "${target_release}" ]] && release_supports_wave5_workers "${target_release}"; then
    for worker in "${WAVE5_WORKER_UNITS[@]}"; do
      systemctl enable "ielts-service@${worker}" >/dev/null 2>&1 || true
      systemctl restart "ielts-service@${worker}"
    done
    return 0
  fi

  for worker in "${WAVE5_WORKER_UNITS[@]}"; do
    systemctl disable --now "ielts-service@${worker}" >/dev/null 2>&1 || true
  done
}

stop_all_http_slot_services() {
  stop_http_slot_services blue
  stop_http_slot_services green
}

restart_single_instance_units() {
  local target_release=""
  local service
  systemctl daemon-reload

  for service in "${SINGLE_INSTANCE_CORE_UNITS[@]}"; do
    systemctl restart "ielts-service@${service}"
  done

  target_release="$(current_target_path)"
  if [[ -n "${target_release}" && -d "${target_release}" ]] && release_supports_wave5_workers "${target_release}"; then
    for service in "${WAVE5_WORKER_UNITS[@]}"; do
      systemctl enable "ielts-service@${service}" >/dev/null 2>&1 || true
      systemctl restart "ielts-service@${service}"
    done
    return 0
  fi

  for service in "${WAVE5_WORKER_UNITS[@]}"; do
    systemctl disable --now "ielts-service@${service}" >/dev/null 2>&1 || true
  done
}

install_http_slot_systemd_template() {
  local release_dir="${1:?release dir is required}"
  local template_path="${release_dir}/scripts/cloud-deploy/ielts-http-slot@.service"
  local wrapper_path="${release_dir}/scripts/cloud-deploy/run-http-slot-service.sh"
  local fallback_template="${BASH_SOURCE[0]%/*}/ielts-http-slot@.service"
  local fallback_wrapper="${BASH_SOURCE[0]%/*}/run-http-slot-service.sh"
  if [[ ! -f "${template_path}" ]]; then
    template_path="${fallback_template}"
  fi
  if [[ ! -f "${wrapper_path}" ]]; then
    wrapper_path="${fallback_wrapper}"
  fi
  require_file "${template_path}"
  require_file "${wrapper_path}"
  mkdir -p "${APP_HOME}/bin"
  cp "${wrapper_path}" "${APP_HOME}/bin/run-http-slot-service.sh"
  chmod +x "${APP_HOME}/bin/run-http-slot-service.sh"
  cp "${template_path}" /etc/systemd/system/
  systemctl daemon-reload
}

install_runtime_systemd_units() {
  local release_dir="${1:?release dir is required}"
  local fallback_dir="${BASH_SOURCE[0]%/*}"
  local service_template="${release_dir}/scripts/cloud-deploy/ielts-service@.service"
  local watchdog_service="${release_dir}/scripts/cloud-deploy/ielts-health-watchdog.service"
  local watchdog_timer="${release_dir}/scripts/cloud-deploy/ielts-health-watchdog.timer"
  local watchdog_script="${release_dir}/scripts/cloud-deploy/health-watchdog.sh"

  [[ -f "${service_template}" ]] || service_template="${fallback_dir}/ielts-service@.service"
  [[ -f "${watchdog_service}" ]] || watchdog_service="${fallback_dir}/ielts-health-watchdog.service"
  [[ -f "${watchdog_timer}" ]] || watchdog_timer="${fallback_dir}/ielts-health-watchdog.timer"
  [[ -f "${watchdog_script}" ]] || watchdog_script="${fallback_dir}/health-watchdog.sh"

  require_file "${service_template}"
  require_file "${watchdog_service}"
  require_file "${watchdog_timer}"
  require_file "${watchdog_script}"

  mkdir -p "${APP_HOME}/bin" "${DEPLOY_RUNTIME_DIR}"
  cp "${service_template}" /etc/systemd/system/
  cp "${watchdog_service}" /etc/systemd/system/
  cp "${watchdog_timer}" /etc/systemd/system/
  cp "${watchdog_script}" "${APP_HOME}/bin/health-watchdog.sh"
  chmod +x "${APP_HOME}/bin/health-watchdog.sh"
  systemctl daemon-reload
}

enable_runtime_watchdog_timer() {
  systemctl enable --now ielts-health-watchdog.timer
}
