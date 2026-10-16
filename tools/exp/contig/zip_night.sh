#!/usr/bin/env bash
# IFA night 2026-10-14: the ZIP-pages layout (tools/maps/zip_pages.py, summary page first, metro
# labels) of a K folder, into the folder: zip_summary.png, zip_IFA.png, zip_pages.pdf.
#   tools/exp/contig/zip_night.sh <K folder> <label>    (TD_PY, TD_REPO set)
set -euo pipefail
"$TD_PY" tools/maps/zip_pages.py "$1" "$2" "$1" --corridor \
  --fac "$TD_REPO/runs/sweep/grid_2026-10-01/tables.json"
