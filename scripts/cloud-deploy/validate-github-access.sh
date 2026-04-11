#!/usr/bin/env bash
set -euo pipefail

APP_HOME="${APP_HOME:-/opt/ielts-vocab}"
PROBE_REPO="${GITHUB_ACCESS_REPO:-}"
CRITICAL_ONLY=0
REQUIRE_WEB_GITHUB="${REQUIRE_WEB_GITHUB:-0}"
RETRY_ATTEMPTS="${RETRY_ATTEMPTS:-3}"
RETRY_DELAY_SECONDS="${RETRY_DELAY_SECONDS:-2}"
PUBLIC_REPO_SSH="${PUBLIC_REPO_SSH:-git@github.com:octocat/Hello-World.git}"
RAW_URL="${RAW_URL:-https://raw.githubusercontent.com/github/gitignore/main/README.md}"
ARCHIVE_URL="${ARCHIVE_URL:-https://github.com/octocat/Hello-World/archive/refs/heads/master.tar.gz}"
RELEASE_URL="${RELEASE_URL:-https://github.com/jqlang/jq/releases/download/jq-1.6/jq-linux64}"

log() {
  printf '[%s] %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*"
}

fail() {
  log "ERROR: $*"
  exit 1
}

usage() {
  cat <<'EOF'
Usage: validate-github-access.sh [--repo PATH] [--critical-only] [--require-web]

Checks whether a remote host can use GitHub for deploys and direct repository
pulls. By default, the HTML github.com homepage is informational; all git,
archive, raw, and release checks are treated as critical.
EOF
}

run_check() {
  local label="${1:?label is required}"
  shift
  log "Checking ${label}"
  run_with_retry "$@" || fail "${label} failed"
}

run_with_retry() {
  local attempt=1
  while true; do
    if "$@"; then
      return 0
    fi
    if (( attempt >= RETRY_ATTEMPTS )); then
      return 1
    fi
    log "Retrying after transient failure (${attempt}/${RETRY_ATTEMPTS})"
    attempt=$((attempt + 1))
    sleep "${RETRY_DELAY_SECONDS}"
  done
}

check_dns_endpoints() {
  local endpoint=""
  for endpoint in github.com ssh.github.com api.github.com raw.githubusercontent.com codeload.github.com release-assets.githubusercontent.com; do
    getent hosts "${endpoint}" >/dev/null
  done
}

check_ssh_auth() {
  local output=""
  output="$(timeout 20s ssh -T github.com 2>&1 || true)"
  printf '%s\n' "${output}" | grep -Fq "successfully authenticated"
}

check_public_repo() {
  timeout 30s git ls-remote "${PUBLIC_REPO_SSH}" HEAD >/dev/null
}

check_raw_url() {
  timeout 20s curl -fsSI "${RAW_URL}" >/dev/null
}

check_archive_url() {
  timeout 20s curl -fsSI -L "${ARCHIVE_URL}" >/dev/null
}

check_release_url() {
  timeout 30s curl -fsSI -L "${RELEASE_URL}" >/dev/null
}

check_repo_origin() {
  timeout 30s git -C "${PROBE_REPO}" ls-remote --exit-code origin HEAD >/dev/null
}

check_optional_web() {
  timeout 20s curl -fsSI https://github.com >/dev/null
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --repo)
      [[ $# -ge 2 ]] || fail "Missing value for --repo"
      PROBE_REPO="$2"
      shift 2
      ;;
    --critical-only)
      CRITICAL_ONLY=1
      shift
      ;;
    --require-web)
      REQUIRE_WEB_GITHUB=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      fail "Unknown argument: $1"
      ;;
  esac
done

command -v curl >/dev/null 2>&1 || fail "Missing required command: curl"
command -v getent >/dev/null 2>&1 || fail "Missing required command: getent"
command -v git >/dev/null 2>&1 || fail "Missing required command: git"
command -v ssh >/dev/null 2>&1 || fail "Missing required command: ssh"
command -v timeout >/dev/null 2>&1 || fail "Missing required command: timeout"

if [[ -z "${PROBE_REPO}" && -d "${APP_HOME}/repository/.git" ]]; then
  PROBE_REPO="${APP_HOME}/repository"
elif [[ -z "${PROBE_REPO}" && -d .git ]]; then
  PROBE_REPO="$(pwd)"
fi

run_check "DNS for GitHub endpoints" check_dns_endpoints
run_check "GitHub SSH auth over port 443" check_ssh_auth
run_check "Public GitHub repo refs" check_public_repo
run_check "raw.githubusercontent.com" check_raw_url
run_check "GitHub source archive download" check_archive_url
run_check "GitHub release asset download" check_release_url

if [[ -n "${PROBE_REPO}" ]]; then
  [[ -d "${PROBE_REPO}/.git" ]] || fail "Repository path is not a git checkout: ${PROBE_REPO}"
  run_check "origin reachability for ${PROBE_REPO}" check_repo_origin
fi

if (( CRITICAL_ONLY == 1 )); then
  log "Skipping optional github.com HTML probe"
  log "GitHub access baseline is healthy"
  exit 0
fi

if check_optional_web; then
  log "github.com HTML endpoint is reachable"
elif [[ "${REQUIRE_WEB_GITHUB}" == "1" ]]; then
  fail "github.com HTML endpoint is not reachable"
else
  log "WARNING: github.com HTML endpoint is not healthy, but git/archive/release paths are available"
fi

log "GitHub access baseline is healthy"
