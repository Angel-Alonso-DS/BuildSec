#!/usr/bin/env bash
# Usage: ./scripts/run.sh [demo|openai] [--backend-only|--frontend-only]
# Starts the API on 127.0.0.1:8000 and the Vite dev server (proxy -> backend).
set -euo pipefail
cd "$(dirname "$0")/.."

MODE="${1:-demo}"
ONLY="${2:-}"

[ -x .venv/bin/python ] || { echo "Missing .venv. Run ./scripts/init.sh first." >&2; exit 1; }

if [ "$MODE" = "openai" ] && [ -z "${OPENAI_MODEL:-}" ]; then
  echo "OPENAI_MODEL is not set (see README-SECRETS.md for credentials)." >&2
  exit 1
fi

PIDS=()
cleanup() {
  echo; echo "Stopping..."
  for pid in "${PIDS[@]:-}"; do kill "$pid" 2>/dev/null || true; done
  wait 2>/dev/null || true
}
trap cleanup INT TERM EXIT

if [ "$ONLY" != "--frontend-only" ]; then
  echo "==> Backend (mode: $MODE) on http://127.0.0.1:8000"
  .venv/bin/python -m src.api.runtime --mode "$MODE" &
  PIDS+=($!)
fi

if [ "$ONLY" != "--backend-only" ] && [ -d frontend ]; then
  echo "==> Frontend (Vite)"
  (cd frontend && npm run dev) &
  PIDS+=($!)
fi

# Exit as soon as either process dies
wait -n
