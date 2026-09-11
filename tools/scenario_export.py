"""scenario_export.py: realised plan runs -> one table that joins onto the source rows.

    .venv/bin/python3 tools/scenario_export.py --out scenarios.csv \\
        --scenario "G1 - national k 14 (12 used) - 48 wholesalers" <grid>/P1_n14w11f21 \\
        --scenario "G2 - national k 10 (9 used) - 45 wholesalers" <grid>/P2_n10w11f21

One row per (scenario, zip_code, current_channel), the grain of the table the instance was
exported from, so the output joins onto it on `zip_code` (ZCTA5, zero-padded) and
`current_channel` (the source spellings in `SOURCE_CHANNELS`).  A run's `assignment.csv` is one
row per (zip, model channel), and the export folds the source's five channels into the four
model channels (`td.channels.FINE_OF_SUB`), so an `N_FI` row becomes two source rows, National
(Chase) and Wells FI, with the same district and rep.

Columns: scenario, zip_code, current_channel, state, model_channel, district (the id as drawn,
`WHFI_PLUS_07` reads `WIFI_07`; `other` for a cell no district holds), district_channels (the
district's channel mix as on the figure: N, WH, FI, WH+, FI+, WHFI, WIFI), rep.  Identifiers
only, never a mass: the values come from the source table through the join.  `rep` is the
export's surrogate id (`R0002`) unless `--rep-map` gives the map the export wrote with its own
`--rep-map`, in which case it is the raw rep id.
"""
from __future__ import annotations

import argparse
import csv
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
for _p in (ROOT, HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from plan_summary import display_id                                          # noqa: E402

# the source table's channel spellings (user, 2026-09-11), per model channel
SOURCE_CHANNELS = {"N_WH": ("Wells WH",), "N_FI": ("National (Chase)", "Wells FI"),
                   "WH": ("WH",), "FI": ("FI",)}
CHANNEL_ORDER = ("National (Chase)", "Wells WH", "Wells FI", "WH", "FI")
MIX = {"N": "N", "WH": "WH", "FI": "FI", "WH_PLUS": "WH+", "FI_PLUS": "FI+", "WHFI": "WHFI",
       "WHFI_PLUS": "WIFI"}
COLUMNS = ("scenario", "zip_code", "current_channel", "state", "model_channel", "district",
           "district_channels", "rep")
ASSIGNMENT_COLUMNS = ("zip", "state", "channel", "file_channel", "district", "bundle",
                      "wholesaler", "M_cell")


def build_argparser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", required=True, help="the CSV to write")
    ap.add_argument("--scenario", nargs=2, action="append", required=True,
                    metavar=("NAME", "RUN_DIR"),
                    help="a scenario name (the figure's name) and its realised run; repeatable")
    ap.add_argument("--rep-map", default=None, metavar="PATH",
                    help="the export's rep map (rep_surrogate, rep_id): write raw rep ids")
    return ap


def read_rep_map(path: str) -> dict[str, str]:
    with open(path, encoding="utf-8", newline="") as fh:
        r = csv.DictReader(fh)
        if not {"rep_surrogate", "rep_id"} <= set(r.fieldnames or ()):
            raise ValueError(f"{path}: needs columns rep_surrogate and rep_id")
        return {row["rep_surrogate"]: row["rep_id"] for row in r}


def scenario_rows(name: str, run_dir: str, rep_map: dict[str, str] | None = None) -> list[dict]:
    """The output rows of one scenario, sorted by zip then source channel order."""
    path = os.path.join(run_dir, "assignment.csv")
    rows: list[dict] = []
    missing: set[str] = set()
    with open(path, encoding="utf-8", newline="") as fh:
        r = csv.DictReader(fh)
        if tuple(r.fieldnames or ()) != ASSIGNMENT_COLUMNS:
            raise ValueError(f"{path}: expected columns {','.join(ASSIGNMENT_COLUMNS)}, "
                             f"got {','.join(r.fieldnames or ())}")
        for rec in r:
            rep = rec["wholesaler"]
            if rep and rep_map is not None:
                if rep in rep_map:
                    rep = rep_map[rep]
                else:
                    missing.add(rep)
            mix = MIX[rec["bundle"]] if rec["bundle"] else ""
            for src in SOURCE_CHANNELS[rec["channel"]]:
                rows.append(dict(scenario=name, zip_code=rec["zip"], current_channel=src,
                                 state=rec["state"], model_channel=rec["channel"],
                                 district=display_id(rec["district"]), district_channels=mix,
                                 rep=rep))
    if missing:
        raise ValueError(f"{name}: --rep-map has no row for {' '.join(sorted(missing))}")
    rows.sort(key=lambda row: (row["zip_code"], CHANNEL_ORDER.index(row["current_channel"])))
    return rows


def main(argv=None) -> int:
    args = build_argparser().parse_args(argv)
    names = [name for name, _ in args.scenario]
    if len(set(names)) != len(names):
        print("scenario names must be distinct", file=sys.stderr)
        return 1
    try:
        rep_map = read_rep_map(args.rep_map) if args.rep_map else None
        table: list[dict] = []
        for name, run_dir in sorted(args.scenario):
            rows = scenario_rows(name, run_dir, rep_map)
            print(f"{name}: {len(rows)} rows from {run_dir}", flush=True)
            table.extend(rows)
    except (OSError, ValueError, KeyError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    with open(args.out, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUMNS)
        w.writeheader()
        w.writerows(table)
    print(f"wrote {args.out}: {len(table)} rows, {len(names)} scenario(s)", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
