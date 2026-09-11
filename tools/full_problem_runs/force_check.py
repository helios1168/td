"""Check the forced-national rule on realised runs: every N_WH / N_FI cell of a forced state must
sit in a pure national (bundle N) district.  Prints one line per cell of the grid.
For cover-national states, check national-carrying bundles in the plan's planned stages
(subtracting swept shares) and in the realised assignment.

    force_check.py CELLS.json GRID_DIR
"""
import csv
import json
import os
import sys
from collections import defaultdict

NATIONAL = {
    "N_WH": {"N", "WH_PLUS", "WHFI_PLUS"},
    "N_FI": {"N", "FI_PLUS", "WHFI_PLUS"}}
PLANNED = {"other_first", "seq_N", "seq_WH", "seq_FI", "joint"}


def planned_check(path, national):
    """National mass comes from assignment.csv; slot y includes the logged sweep shares."""
    if not os.path.exists(path):
        return ["no plan.json"]
    with open(path) as fh:
        plan = json.load(fh)
    swept = defaultdict(float)
    for rec in plan.get("sweep", []):
        for channel in rec["channels"]:
            swept[rec["slot"], rec["state"], channel] += rec["share"]
    shares = defaultdict(float)
    issues = []
    for slot in plan["slots"]:
        if "stage" not in slot:
            issues.append(f"slot {slot['id']}: missing stage")
            continue
        if not slot["used"] or slot["stage"] not in PLANNED:
            continue
        for (state, channel), mass in national.items():
            if mass > 0 and slot["bundle"] in NATIONAL[channel]:
                shares[state, channel] += (slot["y"].get(state, 0.0) -
                                           swept[slot["id"], state, channel])
    for (state, channel), mass in sorted(national.items()):
        share = shares[state, channel]
        if mass > 0 and share < 1 - 1e-4:
            issues.append(f"({state}, {channel}, planned stages, {mass * (1 - share):.6g})")
    return issues


spec = json.load(open(sys.argv[1]))
out = sys.argv[2]
defaults = spec.get("defaults") or {}
for cell in spec["cells"]:
    tag = cell["tag"]
    flags = dict(defaults, **(cell.get("flags") or {}))
    forced = set((flags.get("force_national") or "").split(",")) - {""}
    covered = set((flags.get("cover_national") or "").split(",")) - {""}
    path = os.path.join(out, tag, "assignment.csv")
    if not os.path.exists(path):
        print(f"{tag}: " + ("VIOLATED  " if covered else "") + "no assignment.csv")
        continue
    bad = defaultdict(float)             # (state, bundle or 'unheld') -> mass
    nat = defaultdict(float)
    cover_nat = defaultdict(float)
    cover_bad = defaultdict(float)
    for r in csv.DictReader(open(path)):
        if r["state"] in covered and r["channel"] in NATIONAL:
            m = float(r["M_cell"] or 0.0)
            cover_nat[r["state"], r["channel"]] += m
            if m > 1e-9 and (r["bundle"] not in NATIONAL[r["channel"]] or not r["district"]):
                cover_bad[r["state"], r["channel"],
                          r["bundle"] if r["district"] else "unheld"] += m
        if r["state"] in forced and r["channel"] in ("N_WH", "N_FI"):
            m = float(r["M_cell"] or 0.0)
            nat[r["state"]] += m
            if m > 1e-9 and (r["bundle"] != "N" or not r["district"]):
                bad[r["state"], r["bundle"] or "unheld"] += m
    held = sum(nat.values()) - sum(bad.values())
    issues = (planned_check(os.path.join(out, tag, "plan.json"), cover_nat)
              if covered else [])
    issues.extend(f"({s}, {c}, {b}, {m:.6g})" for (s, c, b), m in sorted(cover_bad.items()))
    verdict = "OK" if not bad and not issues else "VIOLATED"
    print(f"{tag}: {verdict}  forced {len(forced)} states, national {sum(nat.values()):.1f}, "
          f"in N districts {held:.1f}" +
          ("" if not bad else "; outside N: " +
           ", ".join(f"{s}->{b} {m:.2f}" for (s, b), m in sorted(bad.items()))) +
          (f"; cover {len(covered)} states, national {sum(cover_nat.values()):.1f}" if covered else "") +
          ("; cover violations: " + ", ".join(issues) if issues else ""))
