#!/usr/bin/env bash
set -euo pipefail

runner="${WORKSPACE_NODE22_RUNNER:-/Volumes/code/workspace/scripts/run-node22-command.sh}"
exec "${runner}" "$@"
