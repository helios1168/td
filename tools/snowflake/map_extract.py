"""map_extract.py -- 06_map_extract.sql's CSV split into piece.csv, cell.csv, zip.csv, wholesaler.csv.

    "$TD_PY" tools/snowflake/map_extract.py $TD_REPO/data/safe/<result>.csv [--out DIR]

One file per LAYER, with that layer's columns only (the SQL's header comment lists them).  HOLDER is the surrogate R<n>, there is
no wholesaler name and no sales value in the input.  Refuses (exit 1), writing nothing, while a CHECKS row has a MUST_BE_ZERO that is not exactly 0 or 1, or 1 with a VALUE that is not
numeric zero (empty and non-numeric included), or when
the CSV has no CHECKS row or a layer has no row.  Default out: $TD_REPO/data/safe/map_extract_<csv stem>/ (data/safe/ is git-excluded).
"""
from __future__ import annotations

import argparse
import csv
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
LAYERS = {
    "PIECE": "source holder kept role zip_code state terr_channel piece_in_role in_assigned_state n_role_holders n_role_firms",
    "CELL": "est_source zip_code state dist_ch new_dist channel new_terr_channel fit_channel mm_opp n_holders holder_status",
    "ZIP": "zip_code role n_role_holders n_role_firms",
    "WHOLESALER": "source holder kept role assigned_states est_source n_zips n_zips_in_role states opp_main opp_in_role "
                  "opp_out_of_role opp_overlap opp_in_assigned_states",
}


def _passes(r):
    """MUST_BE_ZERO exactly 0 or 1, and when 1 a VALUE that parses as numeric zero (an empty or non-numeric one fails)."""
    if r["must_be_zero"] not in ("0", "1"):
        return False
    if r["must_be_zero"] == "0":
        return True
    try:
        return float(r["value"]) == 0
    except ValueError:
        return False


def read(path):
    with open(path, newline="", encoding="utf-8-sig") as fh:
        rows = [{k.strip().lower(): (v or "") for k, v in r.items()} for r in csv.DictReader(fh)]
    checks = [r for r in rows if r["layer"] == "CHECKS"]
    if not checks:
        sys.exit("refused: no CHECKS rows, the file cannot be verified")
    bad = [r for r in checks if not _passes(r)]
    if bad:
        sys.exit("refused: " + "; ".join(f"{r['source']} {r['name']}: MUST_BE_ZERO {r['must_be_zero']!r}, VALUE {r['value']!r}" for r in bad))
    empty = [k for k in LAYERS if not any(r["layer"] == k for r in rows)]
    if empty:
        sys.exit(f"refused: no rows for layer {', '.join(empty)}")
    return rows


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("csv")
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    out = a.out or os.path.join(os.environ.get("TD_REPO", ROOT), "data", "safe",
                                "map_extract_" + os.path.splitext(os.path.basename(a.csv))[0])
    rows = read(a.csv)
    os.makedirs(out, exist_ok=True)
    for layer, cols in LAYERS.items():
        cols = cols.split()
        path = os.path.join(out, layer.lower() + ".csv")
        with open(path, "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh, lineterminator="\n")
            w.writerow([c.upper() for c in cols])
            w.writerows([r[c] for c in cols] for r in rows if r["layer"] == layer)
        print(f"{path}: {sum(r['layer'] == layer for r in rows)} rows")


if __name__ == "__main__":
    main()
