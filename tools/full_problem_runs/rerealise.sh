#!/bin/zsh
# Re-realise run directories with every adopted rule: plan_realise --sweep-zips --split-cut
# contiguous on the bundles in SPLIT_CUT_BUNDLES (default WH, the adopted setting; the whole list
# N,WH,FI,WH_PLUS,FI_PLUS,WHFI,WHFI_PLUS is the open proposal), then plan_maps and plan_summary.
# Overwrites the directory's realise outputs and maps.  TD_ROOT and PY as in run_grid.sh.
# Usage: rerealise.sh DIR [DIR ...]
set -u
HERE=${0:A:h}
WT=${HERE:h:h}
TD_ROOT=${TD_ROOT:-$WT}
PY=${PY:-$TD_ROOT/.venv/bin/python3}
GEO=$TD_ROOT/data/geo
BUNDLES=${SPLIT_CUT_BUNDLES:-WH}
for d in "$@"; do
  echo "rerealise (sweep, contiguous $BUNDLES): ${d:t}"
  $PY $WT/tools/plan_realise.py $d --geo-cache $GEO --sweep-zips --split-cut contiguous \
    --split-cut-bundles $BUNDLES > $d/step_plan_realise.log 2>&1 || echo "  realise failed"
  $PY $WT/tools/plan_maps.py $d --geo-cache $GEO > $d/step_plan_maps.log 2>&1 || echo "  maps failed"
  $PY $WT/tools/plan_summary.py $d --geo-cache $GEO --no-cache > $d/step_plan_summary.log 2>&1 \
    || echo "  summary failed"
done
echo "rerealise done"
