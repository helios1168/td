#!/usr/bin/env bash
# IFA K grid, night of 2026-10-14: kgrid.sh's merge, score and gate for one K, into the sealed root,
# with the South Atlantic folder replaceable (the MD-shared redraws of tools/exp/contig/sa_night.sh).
#   tools/exp/contig/kgrid_night.sh <K> [OUTNAME] [SA_FOLDER]    (repo or worktree root; TD_PY, TD_REPO set)
# OUTNAME defaults to K<K>; SA_FOLDER defaults to the ladder's choice for K (kgrid.sh).
set -euo pipefail
K=$1; NAME=${2:-K$K}; SAX=${3:-}
H=$TD_REPO/runs/exp/contig/ifa; R=$H/kgrid/regions
NE=$H/newengland/merged; MA=$H/midatl/merged_v2; SA=$H/southatl/merged; SC=$H/southcentral/merged_b
MW=$H/midwest/ifa_mw_merge; W=$H/west/merged
case $K in
  52) ;;
  53) SA=$R/southatl_k10 ;;
  54) SA=$R/southatl_k10 W=$R/west_k8 ;;
  51) MW=$R/midwest_k13 ;;
  50) MW=$R/midwest_k13 W=$R/west_k6 ;;
  49) MW=$R/midwest_k13 W=$R/west_k6 SA=$R/southatl_k8 ;;
  48) MW=$R/midwest_k13 W=$R/west_k6 SA=$R/southatl_k8 MA=$R/midatl_k11 ;;
  *) echo "K $K is not on the ladder" >&2; exit 2 ;;
esac
[ -n "$SAX" ] && SA=$SAX
G=$TD_REPO/runs/exp/sealed_2026-10-14/ifa; OUT=$G/$NAME
rm -rf "$OUT"; mkdir -p "$G/_inst"
"$TD_PY" -u tools/exp/contig/merge.py scenarios/regions/ifa/ifa_conus_merge.toml $NE $MA $SA $SC $MW $W \
  --out "$OUT" --extract-out "$G/_inst/$NAME.json.gz" --base-extract "$TD_REPO/instance_descaled.json.gz" \
  --window 798.74,1148.19 --gap-width || echo "merge: exit $? (an M1 or window fail is not an error)"
"$TD_PY" tools/looks/score.py "$OUT" > "$OUT/score.txt" 2>&1 || true
"$TD_PY" tools/mandates/check.py "$OUT" > "$OUT/check.txt" 2>&1 || true
