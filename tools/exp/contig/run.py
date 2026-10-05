"""run.py -- #109's run: a scenario's master plans drawn by the contiguity-aware realizer
(`tools/exp/contig/draw.py`) into a full run folder that `python -m td maps`,
`tools/mandates/check.py` and `tools/looks/score.py` read like a `python -m td run` folder.

    "$TD_PY" -u tools/exp/contig/run.py <spec.toml> --out <dir> [--extract PATH]
        [--arm arm1|band|split|move] [--fixed-targets] [--sequential] [--time-limit S]
        [--group-limit S] [--plans PATH] [--maps]

Or as the `contig` formulation of `tools/exp/sweep.py` (#92's tracker): params `scenario`,
`arm`, `time_limit` (seconds per channel), `group_limit`, `fixed_targets`, `sequential`, `plans`.

The steps are `td.output.run`'s with the realizer swapped: the instance on M1's polygon graph,
each channel's master (`td.master.plan_all`, cached in `--plans` when given, keyed by the spec's
and the extract's sha256), then per channel `draw.draw` at the arm's rules, the ledger, the audit,
names and `districts.csv`.  A group with no connected drawing keeps `td.realize` and
`td.territory`'s owners there, so the ledger stays full and M1 fails on them, never patched.

Arms (#109; what gives way is the owner's, #112, so each remedy is its own run):
- `arm1`: the master's support fixed, shares recomputed inside the plan's band;
- `band`: as arm1, a group without a drawing retried at δ = 0.05, 0.10, 0.15 (`WIDER`);
- `split`: a split unit's ZCTAs may also go to districts next to its free component (each
  extra holder a split, reported);
- `move`: as `split`, with no more holders per unit than the plan.
`--fixed-targets` adds each (unit, district) mass within the unit's heaviest ZCTA of the plan's
share (the triage's "fixed targets alone", row 15).  `--sequential` draws one split unit at a time
(`draw._sequential`), a restriction of the joint model for coupled groups too large to solve
jointly: its connected drawings are real, its failures prove nothing.

`contig.json` holds what #109 reports per channel: each group's size, solve status ("optimal"
is proved, "connected" is connected and feasible, "infeasible" is proved, "unknown" is the time
limit), solves, cuts, seconds and gap, the δ each group needed, share-only districts (U61),
exclave splits (D2), districts whose connectivity rests on one connector (U63), and drawn
deviations against τ.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import importlib.util
import json
import os
import pickle
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from td import audit, data, geo, master, output, realize, territory  # noqa: E402
from td import spec as tdspec  # noqa: E402


def _load_draw():
    if "contig_draw" in sys.modules:
        return sys.modules["contig_draw"]
    spec = importlib.util.spec_from_file_location("contig_draw", os.path.join(HERE, "draw.py"))
    mod = importlib.util.module_from_spec(spec)
    sys.modules["contig_draw"] = mod
    spec.loader.exec_module(mod)
    return mod


draw = _load_draw()
WIDER = (0.05, 0.10, 0.15)
ARMS = ("arm1", "band", "split", "move")


def sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def plans_for(inst, spec_path: str, extract_path: str | None, cache: str | None, time_limit=None):
    """The master's plans and reports, from `cache` when it holds this spec on this extract."""
    key = None
    if cache and extract_path:
        key = os.path.join(cache, f"{sha256(spec_path)[:16]}_{sha256(extract_path)[:16]}.pkl")
        if os.path.exists(key):
            with open(key, "rb") as fh:
                return pickle.load(fh)
    plans, reports = master.plan_all(inst, time_limit=time_limit)
    if key and all(p is not None for p in plans.values()):
        os.makedirs(cache, exist_ok=True)
        with open(key, "wb") as fh:
            pickle.dump((plans, reports), fh)
    return plans, reports


def single_connector(owner: dict, adj: dict, connectors: set) -> dict:
    """U63: {district: [connector edges]} for each district whose ZCTAs fall apart without one of
    its internal connector edges."""
    by = collections.defaultdict(set)
    for z, j in owner.items():
        by[j].add(z)
    out = {}
    for j, zs in by.items():
        inside = [(a, b) for a, b in connectors if a in zs and b in zs]
        hit = []
        for a, b in inside:
            seen, stack = {a}, [a]
            while stack:
                x = stack.pop()
                for y in adj[x]:
                    if y in zs and y not in seen and {x, y} != {a, b}:
                        seen.add(y)
                        stack.append(y)
            if b not in seen:
                hit.append(f"{a}-{b}")
        if hit:
            out[j] = sorted(hit)
    return out


def exclave_splits(inst, plan, owner: dict, exclave: set) -> list:
    """D2: (unit, district) for each district owning an exclave ZCTA of a unit it holds no share
    of; each is a split the proposed in-state connectors would save."""
    held = {(v, cp.name) for cp in plan.copies for v in cp.support if cp.mass[v] > 0}
    unit_of = inst.units.unit_of
    return sorted({(unit_of[z], owner[z]) for z in exclave if (unit_of[z], owner[z]) not in held})


def contig_run(spec_path: str, extract_path: str, out: str, arm: str = "arm1",
               fixed_targets: bool = False, time_limit: float = 900.0,
               group_limit: float | None = None, plans_cache: str | None = None,
               source: str = "", keep=(), maps: bool = False, sequential: bool = False,
               log=print) -> dict:
    if arm not in ARMS:
        raise ValueError(f"arm {arm!r} not in {ARMS}")
    s = tdspec.load(spec_path)
    output.check_file_names("planning channel", s.channels)
    output.check_out(out, keep)
    ref = geo.read_reference()
    extract = data.load(extract_path)
    conus = data.conus(extract, ref)
    ext = tdspec.scope(s, conus)
    polygon = geo.polygon_graph()
    inst = tdspec.build(s, ext, ref)
    os.makedirs(out, exist_ok=True)
    t0 = time.time()
    plans, reports = plans_for(inst, spec_path, extract_path, plans_cache)
    plan_seconds = time.time() - t0
    none = sorted(c for c, p in plans.items() if p is None)
    output.write_solver(os.path.join(out, "solver.json"), reports, {},
                        inst.report["components"])
    if none:
        raise output.RunError("no plan for " + ", ".join(none) + " at the declared δ")
    rows = ref.set_index("zcta").loc[sorted(inst.units.unit_of)]
    xy = dict(zip(rows.index, zip(rows["x"].astype(float), rows["y"].astype(float))))
    state = dict(zip(rows.index, rows["state"]))
    connectors = set(geo.approved_connectors(geo.read_connectors()))
    contig, drawings = {}, {}
    for c, p in plans.items():
        log(f"{c}: drawing ({arm}{', fixed targets' if fixed_targets else ''}"
            f"{', sequential' if sequential else ''})")
        res = draw.draw(inst, p, xy, arm="arm1" if arm == "band" else arm,
                        fixed_targets=fixed_targets, time_limit=time_limit,
                        wider=WIDER if arm == "band" else (), group_limit=group_limit,
                        sequential=sequential, log=log)
        fallback = None
        if res.undrawn:
            fallback = realize.realize(inst, p, xy)
            territory.own_territory(inst, p, fallback, xy, state)
        d = draw.drawing(inst, p, res, fallback)
        drawings[c] = d
        _, _, exclave = draw.split_fixed(inst, p)
        ch = inst.channels[c]
        dev = {j: (x - ch.tau) / ch.tau for j, x in d.mass.items()}
        held = collections.defaultdict(set)
        for z, j in d.owner.items():
            held[inst.units.unit_of[z]].add(j)
        contig[c] = {
            "status": res.status, "connected": res.connected, "undrawn_zctas": len(res.undrawn),
            "plan_delta": p.delta, "master_status": reports[c]["status"],
            "groups": [g.report() for g in res.groups],
            "group_delta_needed": max((g.delta for g in res.groups if g.delta is not None),
                                      default=p.delta),
            "fixed_split": res.fixed_split, "share_only": res.share_only,
            "exclave_splits": [f"{v} {j}" for v, j in exclave_splits(inst, p, d.owner, exclave)],
            "single_connector": single_connector(d.owner, inst.units.zip_adj, connectors)
            if res.connected else None,
            "worst_dev": max(abs(x) for x in dev.values()),
            "mean_dev": sum(abs(x) for x in dev.values()) / len(dev),
            "split_units": sorted(v for v, js in held.items() if len(js) > 1),
            "vanished_shares": [f"{v} {j}" for v, j in d.vanished]}
    areas = output.read_areas()
    led = output.ledger(inst, drawings, ext, ref)
    names = output.name_districts(led, output.cbsa_titles(areas))
    for r in led:
        r["district_name"] = names.get(r["district"], "")
    lpath = output.write_ledger(os.path.join(out, "ledger.csv"), led)
    led = output.read_ledger(lpath)
    with open(os.path.join(geo.REFERENCE_DIR, "MANIFEST.json"), encoding="utf-8") as fh:
        manifest = json.load(fh)
    split = output.ledger_pieces(led, polygon, drawings)
    checks = audit.audit(output.audit_run(inst, led, drawings, ext, reports, polygon, names,
                                          manifest, ref, split, polygon))
    audit.write_scorecard(out, checks, f"{s.name} (contig {arm}, {source or 'extract'})")
    output.write_districts(os.path.join(out, "districts.csv"), inst, plans, drawings, names, split)
    m1 = next(ch for ch in checks if ch.name == audit.M1_CHECK)
    report = {
        "scenario": s.name, "spec": s.path, "source": source, "verdict": audit.verdict(checks),
        "realizer": f"tools/exp/contig ({arm})", "fine_channels": list(s.fine_channels),
        "cells": len(led), "zips": len({r["zip_code"] for r in led}),
        "dropped_units": {c: list(u) for c, u in inst.report.get("dropped_units", {}).items()},
        "dropped_channels": list(inst.dropped_channels),
        "channels": {c: {"k": inst.channels[c].k, "delta": plans[c].delta,
                         "margin": inst.channels[c].spec.margin,
                         "tier": audit.tier(reports[c]), "status": reports[c]["status"],
                         "vanished": len(d.vanished), **output.piece_counts(split, c)}
                     for c, d in drawings.items()},
        "m1": {"status": m1.status, "summary": m1.summary,
               "coverage": "footprint coverage (D3)"}}
    if maps and output.zcta_file(geo.PUBLIC_DIR) is not None:
        output.draw_maps(lpath, out, ref, areas, geo.PUBLIC_DIR, root=out)
        report["maps"] = "drawn"
    else:
        report["maps"] = "not drawn (python -m td maps <dir> draws them)"
    with open(os.path.join(out, "run.json"), "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2, sort_keys=True)
        fh.write("\n")
    doc = {"scenario": s.name, "arm": arm, "fixed_targets": fixed_targets,
           "sequential": sequential,
           "plan_seconds": round(plan_seconds, 1), "m1": report["m1"], "channels": contig}
    with open(os.path.join(out, "contig.json"), "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=2, sort_keys=True)
        fh.write("\n")
    log(f"{s.name} ({arm}): M1 {m1.status} ({m1.summary}); audit {report['verdict']}")
    return doc


def run_contig(m: dict, folder: str) -> None:
    """The `contig` formulation of `tools/exp/sweep.py`."""
    p = m["params"]
    spec_path = os.path.join(folder, "scenario.toml")
    contig_run(spec_path, m["extract"], folder, p.get("arm", "arm1"),
               bool(p.get("fixed_targets", False)), float(p.get("time_limit", 900)),
               p.get("group_limit"), p.get("plans"), m["provenance"]["instance"],
               keep=tuple(os.listdir(folder)), maps=bool(p.get("maps", False)),
               sequential=bool(p.get("sequential", False)))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("spec")
    ap.add_argument("--out", required=True)
    ap.add_argument("--extract", default=os.path.join(os.environ.get("TD_REPO", ROOT),
                                                      "instance_descaled.json.gz"))
    ap.add_argument("--arm", default="arm1", choices=ARMS)
    ap.add_argument("--fixed-targets", action="store_true")
    ap.add_argument("--sequential", action="store_true")
    ap.add_argument("--time-limit", type=float, default=900.0)
    ap.add_argument("--group-limit", type=float, default=None)
    ap.add_argument("--plans", default=None, help="a directory caching the master's plans")
    ap.add_argument("--maps", action="store_true")
    a = ap.parse_args(argv)
    doc = contig_run(a.spec, a.extract, a.out, a.arm, a.fixed_targets, a.time_limit,
                     a.group_limit, a.plans, os.path.basename(a.extract), maps=a.maps,
                     sequential=a.sequential)
    return 0 if doc["m1"]["status"] == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
