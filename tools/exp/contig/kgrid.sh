#!/usr/bin/env bash
# IFA K grid (2026-10-13): merge, render, score and gate one CONUS point of the nested ladder.
#   tools/exp/contig/kgrid.sh <K>    (from the repo or worktree root; TD_PY, TD_REPO set)
# Each K names its six region folders; every region not redrawn at that K is v2's.
set -euo pipefail
K=$1
C=runs/exp/contig/ifa; G=$C/kgrid; R=$G/regions
NE=$C/newengland/merged; MA=$C/midatl/merged_v2; SA=$C/southatl/merged; SC=$C/southcentral/merged_b
MW=$C/midwest/ifa_mw_merge; W=$C/west/merged
kne=4 kma=12 ksa=9 ksc=6 kmw=14 kw=7
case $K in
  52) ;;
  53) SA=$R/southatl_k10 ksa=10 ;;
  54) SA=$R/southatl_k10 ksa=10 W=$R/west_k8 kw=8 ;;
  51) MW=$R/midwest_k13 kmw=13 ;;
  50) MW=$R/midwest_k13 kmw=13 W=$R/west_k6 kw=6 ;;
  49) MW=$R/midwest_k13 kmw=13 W=$R/west_k6 kw=6 SA=$R/southatl_k8 ksa=8 ;;
  48) MW=$R/midwest_k13 kmw=13 W=$R/west_k6 kw=6 SA=$R/southatl_k8 ksa=8 MA=$R/midatl_k11 kma=11 ;;
  *) echo "K $K is not on the ladder" >&2; exit 2 ;;
esac
OUT=$G/K$K
rm -rf "$OUT"
"$TD_PY" -u tools/exp/contig/merge.py runs/exp/contig/_specs/ifa_conus_merge.toml $NE $MA $SA $SC $MW $W \
  --out "$OUT" --extract-out $G/_inst/K$K.json.gz --base-extract "$TD_REPO/instance_descaled.json.gz" \
  --window 798.74,1148.19 --gap-width || echo "merge: exit $? (an M1 or window fail is not an error)"
# the run records its spec relative to the repo: render with TD_REPO here and the untracked
# inputs from the hub, as ifa_conus_v2 was rendered
A=$TD_REPO/runs/sweep/grid_2026-10-01
TD_REPO=$PWD "$TD_PY" tools/maps/render.py "$OUT" --corridor --fac $A/tables.json \
  --geo-cache $A/present/legacy/archive/geo --zcta-shp $A/present/legacy/archive/data/tiger/2025/tl_2025_us_zcta520.shp \
  --zip-cache "$TD_REPO/runs/autonomous_2026-10-05/batch/geo" \
  --label "K$K: IFA CONUS, $K districts (New England $kne, Middle Atlantic $kma, South Atlantic $ksa, South Central $ksc, Midwest $kmw, West $kw); MD whole (F1); Manhattan neck open"
"$TD_PY" tools/looks/score.py "$OUT" > "$OUT/score.txt" 2>&1 || true
"$TD_PY" tools/mandates/check.py "$OUT" > "$OUT/check.txt" 2>&1 || true
