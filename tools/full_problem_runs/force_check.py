"""Check the forced-national rule on realised runs: every N_WH / N_FI cell of a forced state must
sit in a pure national (bundle N) district.  Prints one line per cell of the grid.

    force_check.py CELLS.json GRID_DIR
"""
import csv
import json
import os
import sys
from collections import defaultdict

spec = json.load(open(sys.argv[1]))
out = sys.argv[2]
defaults = spec.get("defaults") or {}
for cell in spec["cells"]:
    tag = cell["tag"]
    flags = dict(defaults, **(cell.get("flags") or {}))
    forced = set((flags.get("force_national") or "").split(",")) - {""}
    path = os.path.join(out, tag, "assignment.csv")
    if not os.path.exists(path):
        print(f"{tag}: no assignment.csv")
        continue
    bad = defaultdict(float)             # (state, bundle or 'unheld') -> mass
    nat = defaultdict(float)
    for r in csv.DictReader(open(path)):
        if r["state"] in forced and r["channel"] in ("N_WH", "N_FI"):
            m = float(r["M_cell"] or 0.0)
            nat[r["state"]] += m
            if m > 1e-9 and (r["bundle"] != "N" or not r["district"]):
                bad[r["state"], r["bundle"] or "unheld"] += m
    held = sum(nat.values()) - sum(bad.values())
    verdict = "OK" if not bad else "VIOLATED"
    print(f"{tag}: {verdict}  forced {len(forced)} states, national {sum(nat.values()):.1f}, "
          f"in N districts {held:.1f}" +
          ("" if not bad else "; outside N: " +
           ", ".join(f"{s}->{b} {m:.2f}" for (s, b), m in sorted(bad.items()))))
