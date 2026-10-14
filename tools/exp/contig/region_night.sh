#!/usr/bin/env bash
# IFA night 2026-10-14: draw and repair one South Atlantic region (a state group, MD split-able).
#   tools/exp/contig/region_night.sh <spec stem> <STATES>    (repo or worktree root; TD_PY, TD_REPO set)
# Spec scenarios/regions/ifa/ifa_night_<stem>.toml; folders <sealed>/ifa/sa/<stem>[-rep], extract
# <sealed>/ifa/sa/_inst/<stem>.json.gz.  Each solve is capped at 45 min of wall clock.  A drawing
# whose contig.json reports undrawn ZCTAs or a channel status other than optimal/connected is a
# failure (the realizer fell back to a non-contiguous assignment): exit 3, never repaired or merged.
set -uo pipefail
STEM=$1; ST=$2
S=scenarios/regions/ifa/ifa_night_$STEM.toml
N=$TD_REPO/runs/exp/sealed_2026-10-14/ifa/sa; X=$N/_inst/$STEM.json.gz; W=798.74,1148.19
D=$(sed -n 's/^delta = //p' "$S" | head -1)
OUT=$N/$STEM
rm -rf "$OUT" "$OUT-rep"
"$TD_PY" tools/exp/contig/state_extract.py "$X" "$ST" > "$N/$STEM.run.log" 2>&1
gtimeout 2700 "$TD_PY" -u tools/exp/contig/run.py "$S" --out "$OUT" --extract "$X" --states "$ST" \
  --delta "$D" --jobs 1 --time-limit 1500 >> "$N/$STEM.run.log" 2>&1
echo "run exit $?" >> "$N/$STEM.run.log"
"$TD_PY" - "$OUT" <<'PY' || exit 3
import json, sys
c = json.load(open(sys.argv[1] + "/contig.json"))["channels"]["IFA"]
bad = c["undrawn_zctas"] or c["status"] not in ("optimal", "connected")
print("drawing:", c["status"], "undrawn", c["undrawn_zctas"], "connected", c["connected"])
sys.exit(1 if bad else 0)
PY
gtimeout 2700 "$TD_PY" -u tools/exp/contig/repair.py "$OUT" --out "$OUT-rep" --extract "$X" --states "$ST" \
  --window $W --flow --time-limit 240 --jobs 1 > "$N/$STEM.rep.log" 2>&1
echo "repair exit $?" >> "$N/$STEM.rep.log"
