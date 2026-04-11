#!/usr/bin/env bash
set -euo pipefail

SSH_HOME="${SSH_HOME:-${HOME}/.ssh}"
GITHUB_SSH_KEY_PATH="${GITHUB_SSH_KEY_PATH:-${SSH_HOME}/ielts-vocab-github}"
REPO_PATH="${REPO_PATH:-}"

log() {
  printf '[%s] %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*"
}

fail() {
  log "ERROR: $*"
  exit 1
}

usage() {
  cat <<'EOF'
Usage: configure-github-access.sh [--repo PATH] [--key PATH] [--ssh-home PATH]

Configures a remote host so GitHub git traffic uses SSH over port 443 and
GitHub HTTPS clone URLs are rewritten to SSH automatically.
EOF
}

normalize_github_remote() {
  local remote_url="${1:-}"
  case "${remote_url}" in
    git@github.com:*)
      printf '%s\n' "${remote_url}"
      ;;
    https://github.com/*)
      printf 'git@github.com:%s\n' "${remote_url#https://github.com/}"
      ;;
    http://github.com/*)
      printf 'git@github.com:%s\n' "${remote_url#http://github.com/}"
      ;;
    ssh://git@github.com/*)
      printf 'git@github.com:%s\n' "${remote_url#ssh://git@github.com/}"
      ;;
    *)
      printf '\n'
      ;;
  esac
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --repo)
      [[ $# -ge 2 ]] || fail "Missing value for --repo"
      REPO_PATH="$2"
      shift 2
      ;;
    --key)
      [[ $# -ge 2 ]] || fail "Missing value for --key"
      GITHUB_SSH_KEY_PATH="$2"
      shift 2
      ;;
    --ssh-home)
      [[ $# -ge 2 ]] || fail "Missing value for --ssh-home"
      SSH_HOME="$2"
      shift 2
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

command -v git >/dev/null 2>&1 || fail "Missing required command: git"
command -v ssh-keyscan >/dev/null 2>&1 || fail "Missing required command: ssh-keyscan"
command -v mktemp >/dev/null 2>&1 || fail "Missing required command: mktemp"

[[ -f "${GITHUB_SSH_KEY_PATH}" ]] || fail "Missing GitHub SSH key: ${GITHUB_SSH_KEY_PATH}"

mkdir -p "${SSH_HOME}"
chmod 700 "${SSH_HOME}"

cat > "${SSH_HOME}/config" <<EOF
Host github.com
  HostName ssh.github.com
  Port 443
  User git
  IdentityFile ${GITHUB_SSH_KEY_PATH}
  IdentitiesOnly yes
  StrictHostKeyChecking accept-new

Host ssh.github.com
  HostName ssh.github.com
  Port 443
  User git
  IdentityFile ${GITHUB_SSH_KEY_PATH}
  IdentitiesOnly yes
  StrictHostKeyChecking accept-new
EOF
chmod 600 "${SSH_HOME}/config"
log "Wrote ${SSH_HOME}/config"

known_hosts_file="${SSH_HOME}/known_hosts"
tmp_scan="$(mktemp)"
tmp_hosts="$(mktemp)"
trap 'rm -f "${tmp_scan}" "${tmp_hosts}"' EXIT

ssh-keyscan -p 443 ssh.github.com > "${tmp_scan}" 2>/dev/null || fail "ssh-keyscan failed for ssh.github.com:443"
if [[ -f "${known_hosts_file}" ]]; then
  grep -v '^\[ssh\.github\.com\]:443 ' "${known_hosts_file}" > "${tmp_hosts}" || true
else
  : > "${tmp_hosts}"
fi
cat "${tmp_scan}" >> "${tmp_hosts}"
mv "${tmp_hosts}" "${known_hosts_file}"
chmod 600 "${known_hosts_file}"
log "Refreshed ${known_hosts_file}"

git config --global --unset-all url."git@github.com:".insteadOf >/dev/null 2>&1 || true
git config --global --add url."git@github.com:".insteadOf https://github.com/
git config --global --add url."git@github.com:".insteadOf http://github.com/
git config --global --add url."git@github.com:".insteadOf git://github.com/
log "Configured global GitHub URL rewrite"

if [[ -n "${REPO_PATH}" ]]; then
  [[ -d "${REPO_PATH}/.git" ]] || fail "Repository path is not a git checkout: ${REPO_PATH}"
  current_origin="$(git -C "${REPO_PATH}" remote get-url origin 2>/dev/null || true)"
  if [[ -n "${current_origin}" ]]; then
    ssh_origin="$(normalize_github_remote "${current_origin}")"
    if [[ -n "${ssh_origin}" && "${ssh_origin}" != "${current_origin}" ]]; then
      git -C "${REPO_PATH}" remote set-url origin "${ssh_origin}"
      log "Rewrote origin to ${ssh_origin}"
    else
      log "Origin already uses SSH or is not a GitHub remote"
    fi
  else
    log "Repository has no origin remote: ${REPO_PATH}"
  fi
fi

log "GitHub access baseline configured"
