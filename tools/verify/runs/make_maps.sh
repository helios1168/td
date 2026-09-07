#!/bin/bash
# One power-diagram map per scenario at k=18 -- docs/RUNS_PLAN.md §6.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$REPO_ROOT"

PYTHON=/Users/ntlee/projects/td/.venv/bin/python3
INSTANCE=instance_descaled_v2.json.gz
DATE=$(date +%Y%m%d)
RESULTS_ROOT="battery/results/runs_${DATE}"
FIG_ROOT="figures/runs_${DATE}"

mkdir -p "$FIG_ROOT"

first=1
for name in baseline CALIFORNIA_fix CALIFORNIA_anchor TEXAS_fix TEXAS_anchor \
            NEWYORK_fix NEWYORK_anchor MIDWEST_fix MIDWEST_anchor \
            CAROLINAS_fix CAROLINAS_anchor SOUTHWEST_fix SOUTHWEST_anchor \
            FLORIDA_fix FLORIDA_anchor; do
  out_dir="$FIG_ROOT/$name"
  mkdir -p "$out_dir"
  echo "=== $name ==="
  "$PYTHON" tools/us_maps.py "$INSTANCE" --out "$out_dir" \
    --regions "$RESULTS_ROOT/$name/k18/draw.csv"
  if [ "$first" = "1" ]; then
    cp "$out_dir/opportunity.png" "$FIG_ROOT/opportunity.png"
    first=0
  fi
  rm -f "$out_dir/opportunity.png" "$out_dir/firm_a.png" "$out_dir/firm_b.png" "$out_dir/contestability.png"
done

echo "all 15 maps complete -> $FIG_ROOT"
