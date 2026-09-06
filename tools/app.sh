#!/bin/bash
# Start the scenario app. Run from anywhere; it resolves its own worktree.
#   tools/app.sh                          # loopback:8501, for an SSH tunnel
#   tools/app.sh --server.address=100.69.120.67   # bind the tailnet address instead
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

# `streamlit run app/main.py` puts `app/` on sys.path, not the worktree root, so `from app
# import ...` fails without this.
export PYTHONPATH="$ROOT${PYTHONPATH:+:$PYTHONPATH}"

exec .venv-app/bin/streamlit run app/main.py "$@"
