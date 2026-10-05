"""report.py -- #109's results table from contig run folders (`tools/exp/contig/run.py`).

    "$TD_PY" tools/exp/contig/report.py <run_dir> [<run_dir> ...] [--json PATH]

One row per run folder and channel: M1 from the audit's `check_m1` on the ledger (footprint
coverage, D3) with the largest detached piece, the channel's drawn worst and mean |mass/τ − 1|,
split units and cuts counted on the drawn map (a state two or more of the channel's districts own
a ZCTA of, zero-opportunity ZCTAs included; cuts Σ (districts − 1)), the realizer's status per
group ("optimal" proved, "connected" connected and feasible, "infeasible" proved, "unknown" a time
limit or a restricted model), the solve seconds and the worst gap, the internal δ the drawing
needed (U54), share-only districts (U61), exclave splits (D2), districts resting on one connector
(U63), and the split count against a covering bound (U56): "not covered", since no all-M1 bound
exists yet (#119).
"""
from __future__ import annotations

import argparse
import collections
import csv
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


def drawn_splits(ledger_path: str) -> dict:
    """{channel: (split states, cuts)} on the drawn ledger, by polygon ownership."""
    own = collections.defaultdict(lambda: collections.defaultdict(set))
    with open(ledger_path, newline="") as fh:
        for r in csv.DictReader(fh):
            if r["district"]:
                own[r["model_channel"]][r["state"]].add(r["district"])
    out = {}
    for c, by in own.items():
        split = sorted(s for s, js in by.items() if len(js) > 1)
        out[c] = (split, sum(len(by[s]) - 1 for s in split))
    return out


def m1_pieces(scorecard_path: str) -> dict:
    """{channel: [mass/τ of each detached piece]} from the scorecard's M1 section."""
    out = collections.defaultdict(list)
    with open(scorecard_path, encoding="utf-8") as fh:
        for line in fh:
            hit = re.match(r"- (\S+?)/\S+: detached piece of \d+ ZIPs \(.*?\), ([\d.e+-]+) τ", line)
            if hit:
                out[hit.group(1)].append(float(hit.group(2)))
    return out


def deviations(districts_path: str) -> dict:
    """{channel: (worst, mean)} of |drawn mass / channel mean − 1|."""
    mass = collections.defaultdict(list)
    with open(districts_path, newline="") as fh:
        for r in csv.DictReader(fh):
            mass[r["channel"]].append(float(r["drawn_mass"]))
    out = {}
    for c, xs in mass.items():
        tau = sum(xs) / len(xs)
        d = [abs(x / tau - 1) for x in xs]
        out[c] = (max(d), sum(d) / len(d))
    return out


def rows(run_dir: str) -> list:
    with open(os.path.join(run_dir, "contig.json")) as fh:
        doc = json.load(fh)
    with open(os.path.join(run_dir, "run.json")) as fh:
        run = json.load(fh)
    splits = drawn_splits(os.path.join(run_dir, "ledger.csv"))
    pieces = m1_pieces(os.path.join(run_dir, "scorecard.md"))
    dev = deviations(os.path.join(run_dir, "districts.csv"))
    m1 = doc["m1"]
    out = []
    for c, r in sorted(doc["channels"].items()):
        groups = r["groups"]
        st = collections.Counter(g["status"] for g in groups)
        gaps = [g["gap"] for g in groups if g.get("gap") is not None]
        split, cuts = splits.get(c, ([], 0))
        out.append({
            "run": os.path.basename(os.path.normpath(run_dir)), "scenario": doc["scenario"],
            "arm": doc["arm"] + (" seq" if doc.get("sequential") else "")
            + (" fixed-targets" if doc.get("fixed_targets") else ""),
            "channel": c, "k": run["channels"][c]["k"], "plan_delta": r["plan_delta"],
            "m1_map": m1["status"], "m1_summary": m1["summary"],
            "pieces_m1": len(pieces.get(c, [])), "largest_tau": max(pieces.get(c, [0.0])),
            "pieces": run["channels"][c].get("pieces"),
            "connected": r["connected"], "status": r["status"],
            "groups": dict(st),
            "seconds": round(sum(sum(t["seconds"] for t in g["tried"]) or g["seconds"]
                                 for g in groups), 1),
            "worst_gap": max(gaps) if gaps else None,
            "delta_needed": r["group_delta_needed"] if r["connected"] else None,
            "worst_dev": dev[c][0], "mean_dev": dev[c][1],
            "split_units": len(split), "split_states": split, "cuts": cuts,
            "share_only": len(r["share_only"]), "exclave_splits": r["exclave_splits"],
            "single_connector": r["single_connector"],
            "covering_bound": "not covered (#119)"})
    return out


def table(all_rows: list) -> str:
    cols = ("run", "arm", "channel", "K", "plan δ", "M1 (map, D3)", "pieces", "largest piece",
            "drawn", "groups",
            "s", "worst gap", "δ needed", "worst / mean dev", "split units", "cuts",
            "share-only (U61)", "exclave splits", "one-connector districts (U63)")
    lines = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for r in all_rows:
        groups = ", ".join(f"{k} {v}" for k, v in sorted(r["groups"].items()))
        gap = "" if r["worst_gap"] is None else f"{r['worst_gap']:.2g}"
        need = "" if r["delta_needed"] is None else f"{r['delta_needed']:g}"
        one = "n/a" if r["single_connector"] is None else str(len(r["single_connector"]))
        cells = (r["run"], r["arm"], r["channel"], str(r["k"]), f"{r['plan_delta']:g}",
                 r["m1_map"], str(r["pieces_m1"]), f"{r['largest_tau']:.3g} τ",
                 f"{'all' if r['connected'] else 'not all'} ({r['status']})", groups,
                 f"{r['seconds']:g}", gap, need,
                 f"{100 * r['worst_dev']:.1f}% / {100 * r['mean_dev']:.1f}%",
                 str(r["split_units"]), str(r["cuts"]), str(r["share_only"]),
                 str(len(r["exclave_splits"])), one)
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("runs", nargs="+")
    ap.add_argument("--json")
    a = ap.parse_args(argv)
    all_rows = [r for d in a.runs if os.path.exists(os.path.join(d, "contig.json")) for r in rows(d)]
    print(table(all_rows))
    if a.json:
        with open(a.json, "w") as fh:
            json.dump(all_rows, fh, indent=2)
    return 0


if __name__ == "__main__":
    sys.exit(main())
