"""table.py -- the ranked Markdown table of the indexed runs, per lane or across lanes (#92).

    "$TD_PY" tools/exp/table.py [--lane L ...] [--across] [--root DIR] [--registry PATH]

Reads `<root>/index.jsonl` (`tools/exp/index.py`) and prints one table per lane, or one across
lanes with `--across`, each row with its run folder.  The order is the owner's (PROBLEM.md row
2026-10-04): done runs first, then eligible by the looks scorer (`tools/looks/score.py`: the
ledger audit at a plain ±15% band, the K and $ rules), then channel-state splits, then defects
(thin links + pieces under 20% τ + crowded states + ZIP-contiguity pieces), then largest extent
and states per district, then worst and mean deviation; a metric a run lacks sorts last.  td's
own audit verdict, at the scenario's declared band, is shown and does not rank.  `REVIEW` flags
an eligible run with one split more than the table's best eligible split count and fewer defects
than every eligible run at that count.

A run on the map shortlist (`tools/shortlist/shortlist.json`, mandate T1, #120; edited by hand)
shows its shortlist id and tier, matched by run folder.  Nothing is copied: a map is read in its
run folder.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("exp_index", os.path.join(HERE, "index.py"))
index = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(index)

REGISTRY = os.path.join(os.path.dirname(HERE), "shortlist", "shortlist.json")
DEFECTS = ("thin_links", "small_pieces", "crowded_states", "contiguity_pieces")


def defects(m: dict):
    return sum(m[k] for k in DEFECTS) if all(m.get(k) is not None for k in DEFECTS) else None


def rank_key(r: dict) -> tuple:
    m = r.get("metrics") or {}

    def last(v):
        return math.inf if v is None else v
    eligible = {True: 0, False: 1}.get(m.get("eligible"), 2)
    return (r["status"] != "done", eligible, last(m.get("splits")),
            last(defects(m)), last(m.get("largest_extent_km")), last(m.get("states_per_district")),
            last(m.get("worst_dev")), last(m.get("mean_dev")), r["run_id"])


def review(rows: list) -> set:
    """Run ids flagged `REVIEW`: eligible, one split above the best eligible split count, and
    fewer defects than every eligible run at that count; done runs only."""
    ok = [r for r in rows if r["status"] == "done"
          and (r.get("metrics") or {}).get("eligible") is True
          and r["metrics"].get("splits") is not None]
    if not ok:
        return set()
    best = min(r["metrics"]["splits"] for r in ok)
    at_best = [defects(r["metrics"]) for r in ok if r["metrics"]["splits"] == best]
    if any(d is None for d in at_best):
        return set()
    return {r["run_id"] for r in ok if r["metrics"]["splits"] == best + 1
            and defects(r["metrics"]) is not None and defects(r["metrics"]) < min(at_best)}


def read_shortlist(path: str = REGISTRY) -> list:
    """The shortlist's entries, each `run` made absolute against `$TD_REPO`."""
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as fh:
        maps = json.load(fh)["maps"]
    base = os.environ.get("TD_REPO", os.path.dirname(os.path.dirname(HERE)))
    return [{**e, "run": os.path.normpath(os.path.join(base, e["run"]))} for e in maps]


def _cell(v) -> str:
    if v is None:
        return ""
    if isinstance(v, bool):
        return "yes" if v else "no"
    if isinstance(v, float):
        return f"{v:.4g}"
    return str(v).replace("|", "\\|")


def markdown(rows: list, shortlist: list) -> str:
    """One ranked table of `rows`."""
    short = {}
    for e in shortlist:
        short.setdefault(os.path.normpath(e["run"]), []).append(e)
    flagged = review(rows)
    head = ("rank", "run", "status", "audit", "eligible", "splits", "defects", "extent km",
            "states/district", "worst dev", "mean dev", "flag", "shortlist", "tier", "folder")
    lines = ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    for i, r in enumerate(sorted(rows, key=rank_key), 1):
        m, s = r.get("metrics") or {}, short.get(os.path.normpath(r["folder"]), [])
        cells = (i, r["run_id"], r["status"], r.get("audit"), m.get("eligible"), m.get("splits"),
                 defects(m), m.get("largest_extent_km"), m.get("states_per_district"),
                 m.get("worst_dev"), m.get("mean_dev"),
                 "REVIEW" if r["run_id"] in flagged else "", " ".join(e["id"] for e in s) or None,
                " ".join(str(e["tier"]) for e in s) or None,
                 r["folder"])
        lines.append("| " + " | ".join(map(_cell, cells)) + " |")
    return "\n".join(lines)


def tables(rows: list, shortlist: list, lanes=None, across: bool = False) -> str:
    rows = [r for r in rows if not lanes or r["lane"] in lanes]
    if across:
        return f"## all lanes\n\n{markdown(rows, shortlist)}\n"
    return "\n".join(f"## {lane}\n\n{markdown([r for r in rows if r['lane'] == lane], shortlist)}\n"
                     for lane in sorted({r["lane"] for r in rows}))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="tools/exp/table.py", description=__doc__.splitlines()[0])
    ap.add_argument("--root", default=None, help="runs root (default $TD_REPO/runs/exp)")
    ap.add_argument("--lane", action="append", help="only this lane (repeatable)")
    ap.add_argument("--across", action="store_true", help="one table across lanes")
    ap.add_argument("--registry", default=REGISTRY, help="the map shortlist")
    a = ap.parse_args(argv)
    root = os.path.abspath(a.root or index.sweep.default_root())
    rows = index.read(root)
    print(tables(rows, read_shortlist(a.registry), a.lane, a.across), end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
