#!/usr/bin/env bash
# Usage: ./scripts/run.sh [demo|openai] [--backend-only|--frontend-only]
# Starts the API on 127.0.0.1:8000 and the Vite dev server (proxy -> backend).
set -euo pipefail
cd "$(dirname "$0")/.."

MODE="${1:-demo}"
ONLY="${2:-}"
BACKEND_PORT="${BUILDSEC_BACKEND_PORT:-8000}"
FRONTEND_PORT="${BUILDSEC_FRONTEND_PORT:-5173}"

case "$MODE" in demo|openai) ;; *) echo "Usage: $0 [demo|openai] [--backend-only|--frontend-only]" >&2; exit 2;; esac
case "$ONLY" in ''|--backend-only|--frontend-only) ;; *) echo "Invalid service selection." >&2; exit 2;; esac

[ -x .venv/bin/python ] || { echo "Missing .venv. Run ./scripts/init.sh first." >&2; exit 1; }

if [ "$ONLY" != "--frontend-only" ] && [ "$MODE" = "openai" ] && [ -z "${OPENAI_MODEL:-}" ]; then
  echo "OPENAI_MODEL is not set (see README-SECRETS.md for credentials)." >&2
  exit 1
fi

PIDS=()
cleanup() {
  echo; echo "Stopping..."
  for pid in "${PIDS[@]:-}"; do kill "$pid" 2>/dev/null || true; done
  wait 2>/dev/null || true
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

check_port() {
  .venv/bin/python - "$1" <<'PY'
import socket, sys
try:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", int(sys.argv[1])))
except (OSError, ValueError):
    print("Port is unavailable or invalid: " + sys.argv[1], file=sys.stderr)
    sys.exit(1)
PY
}

wait_port() {
  local pid="$1" port="$2"
  for _ in {1..100}; do
    kill -0 "$pid" 2>/dev/null || return 1
    if .venv/bin/python - "$port" <<'PY'
import socket, sys
try:
    with socket.create_connection(("127.0.0.1", int(sys.argv[1])), timeout=0.1): pass
except OSError:
    sys.exit(1)
PY
    then return 0; fi
    sleep 0.1
  done
  return 1
}

if [ "$ONLY" != "--frontend-only" ]; then check_port "$BACKEND_PORT"; fi
if [ "$ONLY" != "--backend-only" ]; then check_port "$FRONTEND_PORT"; fi

if [ "$ONLY" != "--frontend-only" ]; then
  echo "==> Starting backend (mode: $MODE)"
  .venv/bin/python -m src.api.runtime --mode "$MODE" --port "$BACKEND_PORT" &
  PIDS+=($!)
  wait_port "${PIDS[-1]}" "$BACKEND_PORT" || { echo "Backend failed to start." >&2; exit 1; }
fi

if [ "$ONLY" != "--backend-only" ] && [ -d frontend ]; then
  echo "==> Frontend (Vite)"
  [ -f frontend/node_modules/vite/bin/vite.js ] || { echo "Missing frontend dependencies. Run ./scripts/init.sh." >&2; exit 1; }
  (cd frontend && export BUILDSEC_BACKEND_PORT="$BACKEND_PORT" && exec node node_modules/vite/bin/vite.js --host 127.0.0.1 --port "$FRONTEND_PORT" --strictPort) &
  PIDS+=($!)
  wait_port "${PIDS[-1]}" "$FRONTEND_PORT" || { echo "Frontend failed to start." >&2; exit 1; }
  echo "Frontend listening on http://127.0.0.1:$FRONTEND_PORT"
fi

# Exit as soon as either process dies
wait -n
