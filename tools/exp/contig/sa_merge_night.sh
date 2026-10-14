#!/usr/bin/env bash
# IFA night 2026-10-14: merge a South Atlantic north folder and a FL+GA folder into one SA folder.
#   [NS=MD,DE,DC,VA,WV,NC,SC FS=FL,GA] tools/exp/contig/sa_merge_night.sh <name> <north folder> <south folder>
#   (TD_PY, TD_REPO set; NS and FS are the states of the two folders)
set -euo pipefail
NAME=$1; NORTH=$2; FLGA=$3; NS=${NS:-MD,DE,DC,VA,WV,NC,SC}; FS=${FS:-FL,GA}
N=$TD_REPO/runs/exp/sealed_2026-10-14/ifa/sa
rm -rf "$N/$NAME"
"$TD_PY" -u tools/exp/contig/merge.py scenarios/regions/ifa/ifa_southatl_merge.toml \
  $NS="$NORTH" $FS="$FLGA" --out "$N/$NAME" --extract-out "$N/_inst/$NAME.json.gz" \
  --base-extract "$TD_REPO/instance_descaled.json.gz" --window 798.74,1148.19 --gap-width || echo "merge: exit $?"
