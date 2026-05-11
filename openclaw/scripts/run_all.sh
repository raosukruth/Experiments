#!/usr/bin/env bash
# Launch the three bot adapters in the background, run the orchestrator
# against an OpenClaw gateway, then clean up bot processes on exit.
#
# Usage: bash scripts/run_all.sh "small modular reactors" [--fresh-session]
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [[ -f "$ROOT/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "$ROOT/.env"
  set +a
fi

PYTHON="${PYTHON:-python3}"
LOG_DIR="$ROOT/.logs"
mkdir -p "$LOG_DIR"

PIDS=()
trap 'echo "[run_all] stopping bots: ${PIDS[*]}"; for p in "${PIDS[@]}"; do kill "$p" 2>/dev/null || true; done; wait 2>/dev/null || true' EXIT

start_bot() {
  local name="$1"
  local port="$2"
  echo "[run_all] starting ${name} on :${port}"
  "$PYTHON" -m "bots.${name}" >"$LOG_DIR/${name}.log" 2>&1 &
  PIDS+=("$!")
}

start_bot researcher 8001
start_bot writer     8002
start_bot critic     8003

echo "[run_all] waiting for bots to come up…"
for port in 8001 8002 8003; do
  for _ in {1..40}; do
    if curl -sf "http://127.0.0.1:${port}/healthz" >/dev/null; then
      break
    fi
    sleep 0.25
  done
done
echo "[run_all] bots healthy"

echo "[run_all] running orchestrator"
"$PYTHON" run.py "$@"
