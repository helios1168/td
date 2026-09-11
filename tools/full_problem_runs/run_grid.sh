#!/bin/zsh
# Run a cell file end to end: tools/full_grid.py, then rerealise.sh on every cell that has a
# plan.json, then force_check.py (its report also lands in OUT_DIR/force_check.txt).
# TD_ROOT (the directory holding .venv, the instance and data/geo) defaults to the repo root;
# PY defaults to $TD_ROOT/.venv/bin/python3.
# Usage: run_grid.sh CELLS.json OUT_DIR [CONCURRENCY, default 3]
set -u
HERE=${0:A:h}
WT=${HERE:h:h}
TD_ROOT=${TD_ROOT:-$WT}
PY=${PY:-$TD_ROOT/.venv/bin/python3}
CELLS=${1:A}; OUT=${2:A}; CONC=${3:-3}
mkdir -p $OUT
$PY -u $WT/tools/full_grid.py $CELLS --out $OUT --concurrency $CONC --geo-cache $TD_ROOT/data/geo \
  > $OUT/grid_runner.log 2>&1
echo "grid done"
for d in $OUT/*(/); do
  [[ -f $d/plan.json ]] || { echo "no plan.json: ${d:t}"; continue; }
  PY=$PY TD_ROOT=$TD_ROOT zsh $HERE/rerealise.sh $d
done
$PY $HERE/force_check.py $CELLS $OUT | tee $OUT/force_check.txt
echo "run_grid done -> $OUT"
