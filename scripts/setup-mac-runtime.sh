#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
root="$(cd "${script_dir}/.." && pwd)"

mamba_bin="${IELTS_MAC_MAMBA_BIN:-$HOME/.local/bin/micromamba}"
mamba_root="${IELTS_MAC_MAMBA_ROOT:-$HOME/.local/share/micromamba}"
runtime_env="${IELTS_MAC_RUNTIME_ENV:-ielts-mac-runtime}"
runtime_prefix="${IELTS_MAC_RUNTIME_PREFIX:-${mamba_root}/envs/${runtime_env}}"

log() {
  printf '[mac-runtime] %s\n' "$1"
}

require_command() {
  command -v "$1" >/dev/null 2>&1 || {
    printf '[ERROR] Required command not found: %s\n' "$1" >&2
    exit 1
  }
}

ensure_micromamba() {
  if [[ -x "${mamba_bin}" ]]; then
    return 0
  fi

  require_command curl
  require_command tar
  mkdir -p "$(dirname "${mamba_bin}")" "${mamba_root}"
  log "Installing micromamba -> ${mamba_bin}"
  tmp_dir="$(mktemp -d)"
  trap 'rm -rf "${tmp_dir}"' EXIT
  curl -Ls https://micro.mamba.pm/api/micromamba/osx-arm64/latest \
    | tar -xj -C "${tmp_dir}" bin/micromamba
  install -m 755 "${tmp_dir}/bin/micromamba" "${mamba_bin}"
  rm -rf "${tmp_dir}"
  trap - EXIT
}

create_runtime_env() {
  if [[ -d "${runtime_prefix}" ]]; then
    return 0
  fi

  log "Creating runtime env ${runtime_env}"
  MAMBA_ROOT_PREFIX="${mamba_root}" "${mamba_bin}" create -y -n "${runtime_env}" -c conda-forge \
    python=3.12 \
    nodejs=24 \
    postgresql \
    redis-server \
    rabbitmq-server
}

install_python_packages() {
  log "Installing Python runtime packages"
  MAMBA_ROOT_PREFIX="${mamba_root}" "${mamba_bin}" run -n "${runtime_env}" \
    python -m pip install -q \
      -r "${root}/backend/requirements.txt" \
      -r "${root}/services/requirements.txt" \
      -e "${root}/packages/platform-sdk" \
      pytest
}

prepare_pnpm() {
  log 'Enabling pnpm via corepack'
  MAMBA_ROOT_PREFIX="${mamba_root}" "${mamba_bin}" run -n "${runtime_env}" \
    bash -lc 'corepack enable && corepack prepare pnpm@9.0.0 --activate && pnpm --version >/dev/null'
}

print_summary() {
  log "Runtime ready: ${runtime_prefix}"
  MAMBA_ROOT_PREFIX="${mamba_root}" "${mamba_bin}" run -n "${runtime_env}" \
    bash -lc 'python --version && node --version && pnpm --version && psql --version && redis-server --version | head -n 1'
}

ensure_micromamba
create_runtime_env
install_python_packages
prepare_pnpm
print_summary
