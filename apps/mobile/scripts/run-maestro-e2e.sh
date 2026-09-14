#!/usr/bin/env bash
set -euo pipefail

MODE="${1:-all}"
MOBILE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ROOT_DIR="$(cd "$MOBILE_DIR/../.." && pwd)"
FLOW_DIR="$MOBILE_DIR/e2e/maestro"
AVD_NAME="${IELTS_MOBILE_AVD:-ielts_vocab_api35}"
APP_ID="${IELTS_MOBILE_ANDROID_APP_ID:-com.axiomaticworld.ieltsvocab}"
ADB="${ANDROID_HOME:-$HOME/.local/opt/android-sdk}/platform-tools/adb"
EMULATOR="${ANDROID_HOME:-$HOME/.local/opt/android-sdk}/emulator/emulator"
LOG_DIR="${TMPDIR:-/tmp}/ielts-vocab-mobile-e2e"

export MAESTRO_CLI_ANALYSIS_NOTIFICATION_DISABLED="${MAESTRO_CLI_ANALYSIS_NOTIFICATION_DISABLED:-true}"
export MAESTRO_CLI_NO_ANALYTICS="${MAESTRO_CLI_NO_ANALYTICS:-1}"

fail() {
  echo "mobile:e2e: $*" >&2
  exit 1
}

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || fail "missing command: $1"
}

port_open() {
  nc -z 127.0.0.1 "$1" >/dev/null 2>&1
}

wait_for_port() {
  local port="$1"
  local label="$2"
  for _ in $(seq 1 60); do
    port_open "$port" && return 0
    sleep 1
  done
  fail "$label did not open on port $port"
}

boot_emulator() {
  if "$ADB" devices | awk 'NR > 1 && $2 == "device" { found = 1 } END { exit found ? 0 : 1 }'; then
    return
  fi
  [[ -x "$EMULATOR" ]] || fail "Android emulator binary not found at $EMULATOR"
  mkdir -p "$LOG_DIR"
  "$EMULATOR" -avd "$AVD_NAME" -no-snapshot-load >"$LOG_DIR/emulator.log" 2>&1 &
  "$ADB" wait-for-device
  for _ in $(seq 1 90); do
    [[ "$("$ADB" shell getprop sys.boot_completed 2>/dev/null | tr -d '\r')" == "1" ]] && return
    sleep 2
  done
  fail "AVD $AVD_NAME did not finish booting"
}

ensure_metro() {
  if port_open 8081; then
    return
  fi
  mkdir -p "$LOG_DIR"
  (cd "$MOBILE_DIR" && pnpm start -- --port 8081 >"$LOG_DIR/metro.log" 2>&1 &)
  wait_for_port 8081 "Metro"
}

check_local_runtime() {
  wait_for_port 8000 "gateway-bff"
  wait_for_port 5001 "speech service"
}

install_app() {
  if [[ "${IELTS_MOBILE_SKIP_INSTALL:-0}" == "1" ]]; then
    return
  fi
  (cd "$ROOT_DIR" && IELTS_MOBILE_ENV=dev pnpm --dir apps/mobile android:dev)
}

run_flow() {
  local flow="$1"
  [[ -f "$flow" ]] || fail "missing Maestro flow: $flow"
  MAESTRO_APP_ID="$APP_ID" maestro test "$flow"
}

require_cmd pnpm
require_cmd maestro
[[ -x "$ADB" ]] || fail "adb not found at $ADB"
[[ -d "$FLOW_DIR" ]] || fail "missing Maestro flow directory: $FLOW_DIR"

boot_emulator
"$ADB" reverse tcp:8081 tcp:8081
"$ADB" reverse tcp:8000 tcp:8000
"$ADB" reverse tcp:5001 tcp:5001
ensure_metro
check_local_runtime
install_app

case "$MODE" in
  smoke)
    run_flow "$FLOW_DIR/login-smoke.yaml"
    ;;
  all)
    for flow in "$FLOW_DIR"/[0-9]*.yaml; do
      run_flow "$flow"
    done
    ;;
  *)
    run_flow "$FLOW_DIR/$MODE.yaml"
    ;;
esac
