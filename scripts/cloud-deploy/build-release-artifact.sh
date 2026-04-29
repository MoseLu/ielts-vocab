#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")" && pwd)"
repo_root="$(cd "${script_dir}/../.." && pwd)"
repo_root_native="${repo_root}"
source "${script_dir}/release-common.sh"

git_ref="${1:-HEAD}"
output_path="${2:?output path is required}"
tmp_dir="$(mktemp -d)"
stage_dir="${tmp_dir}/stage"
stage_dir_native="${stage_dir}"
commit_sha=""
asset_base=""

cleanup() {
  rm -rf "${tmp_dir}"
}

trap cleanup EXIT

require_command git
require_command tar
require_command node

if command -v cygpath >/dev/null 2>&1; then
  repo_root_native="$(cygpath -w "${repo_root}")"
  stage_dir_native="$(cygpath -w "${stage_dir}")"
fi

commit_sha="$(git -C "${repo_root_native}" rev-parse --verify "${git_ref}^{commit}")"
asset_base="$(resolve_frontend_asset_base)"

if ! command -v pnpm >/dev/null 2>&1 || ! pnpm --version >/dev/null 2>&1; then
  ensure_node_runtime
fi
mkdir -p "${stage_dir}"
git -C "${repo_root_native}" archive "${commit_sha}" | tar -xf - -C "${stage_dir}"
git -C "${stage_dir_native}" init -q
git -C "${stage_dir_native}" add -A

log "Building frontend artifact for ${commit_sha}"
pnpm --dir "${stage_dir_native}" install --frozen-lockfile
env CI=1 FRONTEND_ASSET_BASE_URL="${asset_base}" VITE_ASSET_BASE_URL="${asset_base}" \
  pnpm --dir "${stage_dir_native}" build
cat > "${stage_dir}/${RELEASE_ARTIFACT_ENV_FILE}" <<EOF
commit_sha=${commit_sha}
prebuilt_dist=true
frontend_asset_base_url=${asset_base}
built_at=$(date -u +%Y-%m-%dT%H:%M:%SZ)
EOF

rm -rf "${stage_dir}/.git" "${stage_dir}/node_modules" "${stage_dir}/frontend/node_modules"
mkdir -p "$(dirname "${output_path}")"
tar -czf "${output_path}" -C "${stage_dir}" .
log "Release artifact written to ${output_path}"
