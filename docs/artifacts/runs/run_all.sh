#!/bin/bash
# The 14+1 pin-cost catalogue on instance_descaled_v2.json.gz -- docs/RUNS_PLAN.md §5.
# Run from the repo root of this worktree. ~14 min total (15 runs x ~56s).
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$REPO_ROOT"

PYTHON=/Users/ntlee/projects/td/.venv/bin/python3
INSTANCE=instance_descaled_v2.json.gz
DATE=$(date +%Y%m%d)
OUT_ROOT="battery/results/runs_${DATE}"
SCEN_DIR="docs/artifacts/runs/scenarios"
K_RANGE="14-22"
SEEDS="0-9"

mkdir -p "$OUT_ROOT"

run() {
  local name="$1"; shift
  echo "=== $name ==="
  "$PYTHON" tools/run_draw.py "$INSTANCE" --k "$K_RANGE" --seeds "$SEEDS" \
    --workers 8 --out "$OUT_ROOT/$name" "$@"
}

run baseline

for region in CALIFORNIA TEXAS NEWYORK MIDWEST CAROLINAS SOUTHWEST FLORIDA; do
  for mode in fix anchor; do
    run "${region}_${mode}" --scenario "$SCEN_DIR/${region}_${mode}.json"
  done
done

echo "all 15 runs complete -> $OUT_ROOT"
