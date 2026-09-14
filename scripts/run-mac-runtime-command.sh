#!/usr/bin/env bash
set -euo pipefail

runner="${WORKSPACE_NODE22_RUNNER:-/Volumes/code/workspace/scripts/run-node22-command.sh}"

if [[ "${CI:-}" == "true" && -z "${WORKSPACE_NODE22_RUNNER:-}" ]]; then
  exec "$@"
fi

if [[ -x "${runner}" ]]; then
  exec "${runner}" "$@"
fi

if [[ -n "${WORKSPACE_NODE22_RUNNER:-}" ]]; then
  printf '[ERROR] WORKSPACE_NODE22_RUNNER is not executable: %s\n' "${runner}" >&2
  exit 127
fi

exec "$@"
