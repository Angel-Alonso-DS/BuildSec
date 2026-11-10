#!/usr/bin/env bash
# Installs backend (uv) and frontend (npm) dependencies. Safe to re-run.
set -euo pipefail
cd "$(dirname "$0")/.."

command -v uv >/dev/null  || { echo "uv not found. Run inside 'nix develop'." >&2; exit 1; }
command -v npm >/dev/null || { echo "npm not found. Run inside 'nix develop'." >&2; exit 1; }

echo "==> Backend: creating .venv"
[ -d .venv ] || uv venv .venv

echo "==> Backend: installing dependencies"
if [ -f requirements.txt ]; then
  uv pip install --python .venv/bin/python -r requirements.txt
elif [ -f pyproject.toml ]; then
  uv pip install --python .venv/bin/python -e .
else
  echo "No requirements.txt or pyproject.toml found." >&2
  exit 1
fi

echo "==> Backend: checking imports"
.venv/bin/python -c "import openai; print('openai', openai.__version__)"

if [ -f frontend/package-lock.json ]; then
  echo "==> Frontend: npm ci"
  (cd frontend && npm ci)
else
  echo "==> Frontend: no package-lock.json, skipping (check you're in the right repo)"
fi

echo "Done. Start everything with: ./scripts/run.sh"
