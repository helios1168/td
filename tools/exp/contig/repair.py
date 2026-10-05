"""repair.py -- #109's exact window repair (large-neighbourhood search) of a drawn contig run
folder that fails M1.

    "$TD_PY" -u tools/exp/contig/repair.py <run_dir> --out <dir> [--extract PATH] [--plans PATH]
        [--h0 3] [--max-zctas 1500] [--time-limit 600] [--channels c ...] [--maps]

Per planning channel with a detached piece on the drawn map (the ledger of `<run_dir>`, read
back to each ZCTA's plan copy):

- **The window** W at h hops: every ZCTA within h hops of a detached piece on the instance's
  graph (M1's polygon graph with the approved connectors), kept when it is free (`draw.split_fixed`:
  a ZCTA of a split unit, an exclave or a dropped unit), plus the pieces themselves.  Every ZCTA
  outside W keeps its owner.
- **The model** is `draw._solve_group` on W: x_{z,j} for z in W and every district owning a ZCTA
  in or next to W, each district's ZCTAs outside W its bodies (each component one vertex, the
  largest the root), every district connected by the separator solve-check-cut loop, each
  district's total drawn mass in the channel's final band (the band the audit judged the run
  at), split units first in the objective, then holders (cuts), then geodesic shape; with the cap
  (the default) the window units' split units and cuts may not rise above the drawn map's.  The
  geodesic-DAG restriction runs first and seeds the complete model (`draw._attempt`).
- **Growth**: h doubles while W at h is proved infeasible, up to `--max-zctas` (the last step
  takes the largest h whose W fits); at the cap, an infeasible capped window is tried once more
  without the cap, and the rise in splits or cuts is reported.

Statuses stay apart: "optimal" is a connected optimum of W's complete model at
`mip_rel_gap = 0` (W only, everything outside fixed; never an optimum of the map), "connected"
is connected and feasible, "infeasible" proves only that W at that h, the rest fixed, has no
drawing (never a certificate for the map: no no-good cut), "unknown" is the time limit.

The output is a full run folder (ledger, scorecard, districts.csv, run.json; `run.write_folder`)
and a contig.json that copies the source run's channels and adds each window attempt under
`repair`: pieces before and after, |W|, h, status, seconds, worst deviation, split states and cuts
on the drawn map.  `tools/mandates/check.py` audits it like any run folder.
"""
from __future__ import annotations

import argparse
import collections
import importlib.util
import json
import math
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from td import audit, data, geo, output  # noqa: E402
from td import spec as tdspec  # noqa: E402


def _load(name: str, file: str):
    if name not in sys.modules:
        spec = importlib.util.spec_from_file_location(name, os.path.join(HERE, file))
        mod = importlib.util.module_from_spec(spec)
        sys.modules[name] = mod
        spec.loader.exec_module(mod)
    return sys.modules[name]


draw = _load("contig_draw", "draw.py")
run = _load("contig_run", "run.py")


def owners_from_ledger(rows: list, plans: dict) -> dict:
    """{channel: {zip: copy name}} from the ledger's district ids (`output.district_ids`)."""
    back = {(c, f"{c}_{i:02d}"): j for c, p in plans.items()
            for i, j in enumerate(sorted(cp.name for cp in p.copies), 1)}
    out = collections.defaultdict(dict)
    for r in rows:
        if not r["district"]:
            continue
        c, z = r["model_channel"], r["zip_code"]
        j = back[c, r["district"]]
        if out[c].setdefault(z, j) != j:
            raise RuntimeError(f"{c} {z}: two owners in the ledger")
    return dict(out)


def detached(owner: dict, adj: dict, m: dict) -> list:
    """[(district, frozenset of ZCTAs)] of every detached piece (all but the heaviest component,
    as `td.audit.district_pieces` orders them)."""
    return [(j, frozenset(cc)) for j, comps in audit.district_pieces(owner, adj, m).items()
            for cc in comps[1:]]


def window(seeds: set, free: set, adj: dict, h: int) -> set:
    """The ZCTAs within `h` hops of `seeds` that are free, and the seeds."""
    seen, layer = set(seeds), set(seeds)
    for _ in range(h):
        layer = {y for z in layer for y in adj[z]} - seen
        if not layer:
            break
        seen |= layer
    return (seen & free) | set(seeds)


def holders_on(owner: dict, units, vs) -> dict:
    return {v: {owner[z] for z in units.zips[v] if z in owner} for v in vs}


def map_figures(inst, c: str, owner: dict, state: dict) -> dict:
    """Worst |mass/τ − 1|, split states and cuts (by polygon ownership, as `report.py` counts on
    the ledger) of a channel's drawn map."""
    ch = inst.channels[c]
    mass = collections.Counter()
    by = collections.defaultdict(set)
    for z, j in owner.items():
        mass[j] += ch.m.get(z, 0.0)
        by[state[z]].add(j)
    split = sorted(s for s, js in by.items() if len(js) > 1)
    return {"worst_dev": max(abs(x / ch.tau - 1) for x in mass.values()),
            "split_states": len(split), "cuts": sum(len(by[s]) - 1 for s in split)}


def solve_window(inst, plan, owner: dict, W: set, p: dict, time_limit: float, cap: bool,
                 log=print):
    """`draw.Group` of the window `W` (module docstring), everything outside fixed."""
    c = plan.channel
    ch, units = inst.channels[c], inst.units
    adj, m, unit_of = units.zip_adj, ch.m, units.unit_of
    outside = {z: j for z, j in owner.items() if z not in W}
    js = sorted({owner[z] for z in W} | {outside[y] for z in W for y in adj[z] if y in outside})
    allowed = {z: list(js) for z in W}
    by_j = collections.defaultdict(set)
    for z, j in outside.items():
        if j in js:
            by_j[j].add(z)
    bodies = {j: draw.components(zs, adj) for j, zs in by_j.items()}
    body_of = {z: (j, i) for j, bs in bodies.items() for i, b in enumerate(bs) for z in b}
    hold = draw.holders(plan)
    planned = {(v, cp.name): cp.mass[v] for cp in plan.copies for v in cp.support}
    support = {cp.name: cp.support for cp in plan.copies}
    lo, hi = ch.final_band
    count = {"current": holders_on(owner, units, {unit_of[z] for z in W}), "cap": cap}
    zs = sorted(W)
    t_end = time.time() + time_limit

    def solve(_d, dag, seed):
        left = t_end - time.time()
        if left <= 1.0:
            return None
        g = draw._solve_group(c, zs, allowed, bodies, body_of, outside, adj, m, p, unit_of,
                              hold, plan, planned, support, inst, lo, hi, "arm1", False,
                              min(left, time_limit / 4) if dag else left, log, None, dag=dag,
                              start=seed, count=count)
        log(f"  {c} window of {len(zs)} ZCTAs{' (dag)' if dag else ''}"
            f"{'' if cap else ' (no cap)'}: {len(g.districts)} districts, {g.columns} columns"
            f" -> {g.status} in {g.seconds:.1f}s, {g.iterations} solves, {g.cuts} cuts"
            f"{(' (' + g.note + ')') if g.note else ''}")
        return g
    tried = []
    g = draw._attempt(solve, None, tried)
    if g is None:
        g = draw.Group(js, sorted({unit_of[z] for z in zs}), len(zs), 0, 0,
                       note="not tried: no time left")
    g.tried = tried
    g.seconds = sum(t["seconds"] for t in tried)
    return g


def heights(seeds: set, free: set, adj: dict, h0: int, max_zctas: int) -> list:
    """h0, 2 h0, 4 h0, ... while the window grows and fits in `max_zctas`; past it, the largest h
    whose window fits."""
    hs, h, prev = [], h0, None
    while True:
        n = len(window(seeds, free, adj, h))
        if n > max_zctas:
            k, floor = h - 1, (hs[-1] if hs else -1)
            while k > floor and len(window(seeds, free, adj, k)) > max_zctas:
                k -= 1
            if k > floor:
                hs.append(k)
            return hs
        if n == prev:           # the free area around the pieces is used up
            return hs
        hs.append(h)
        prev, h = n, 2 * h


def repair_channel(inst, plan, owner: dict, p: dict, state: dict, h0: int, max_zctas: int,
                   time_limit: float, log=print) -> tuple:
    """(the repaired owner, [attempt records]); the owner changes only by a connected window.
    Each round grows the window around the channel's pieces while it is proved infeasible
    (`heights`), then tries the last window without the cap; a round that connects its window
    and leaves pieces (none expected: W holds them all) starts another, at most three."""
    c = plan.channel
    ch, units = inst.channels[c], inst.units
    adj, m = units.zip_adj, ch.m
    _, free, _ = draw.split_fixed(inst, plan)
    free &= set(owner)
    owner = dict(owner)
    attempts = []
    pieces = detached(owner, adj, m)
    for _ in range(3):
        if not pieces:
            break
        seeds = set().union(*(cc for _, cc in pieces))
        hs = heights(seeds, free, adj, h0, max_zctas) or [0]
        steps = [(h, True) for h in hs] + [(hs[-1], False)]
        for h, cap in steps:
            W = window(seeds, free, adj, h)
            before = map_figures(inst, c, owner, state)
            t0 = time.time()
            g = solve_window(inst, plan, owner, W, p, time_limit, cap, log)
            rec = {"channel": c, "h": h, "window_zctas": len(W), "districts": g.districts,
                   "cap": cap, "pieces_before": len(pieces),
                   "piece_tau_before": [round(math.fsum(m.get(z, 0.0) for z in cc) / ch.tau, 4)
                                        for _, cc in pieces],
                   "status": g.status, "seconds": round(time.time() - t0, 1),
                   "objective": g.objective, "bound": g.bound, "gap": g.gap, "note": g.note,
                   "tried": g.tried, "before": before}
            if g.status in ("optimal", "connected"):
                owner.update(g.owner)
                pieces = detached(owner, adj, m)
                rec["after"] = map_figures(inst, c, owner, state)
            rec["pieces_after"] = len(pieces)
            rec["group"] = g.report()
            attempts.append(rec)
            log(f"{c}: h = {h}, |W| = {len(W)}{'' if cap else ' (no cap)'}: {g.status}, pieces "
                f"{rec['pieces_before']} -> {rec['pieces_after']}, {rec['seconds']}s")
            if g.status != "infeasible":
                break
        if attempts[-1]["status"] not in ("optimal", "connected"):
            break
    return owner, attempts


def load(run_dir: str, extract_path: str, plans_cache: str | None):
    with open(os.path.join(run_dir, "run.json")) as fh:
        src = json.load(fh)
    spec_path = src["spec"]
    s = tdspec.load(spec_path)
    ref = geo.read_reference()
    extract = data.load(extract_path)
    ext = tdspec.scope(s, data.conus(extract, ref))
    polygon = geo.polygon_graph()
    inst = tdspec.build(s, ext, ref)
    plans, reports = run.plans_for(inst, spec_path, extract_path, plans_cache)
    owners = owners_from_ledger(output.read_ledger(os.path.join(run_dir, "ledger.csv")), plans)
    return s, ref, ext, polygon, inst, plans, reports, owners, src


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("run_dir")
    ap.add_argument("--out", required=True)
    ap.add_argument("--extract", default=os.path.join(os.environ.get("TD_REPO", ROOT),
                                                      "instance_descaled.json.gz"))
    ap.add_argument("--plans", default=None)
    ap.add_argument("--h0", type=int, default=3)
    ap.add_argument("--max-zctas", type=int, default=1500)
    ap.add_argument("--time-limit", type=float, default=600.0, help="seconds per window")
    ap.add_argument("--channels", nargs="*", default=None)
    ap.add_argument("--maps", action="store_true")
    a = ap.parse_args(argv)
    output.check_out(a.out)
    s, ref, ext, polygon, inst, plans, reports, owners, src = load(a.run_dir, a.extract, a.plans)
    os.makedirs(a.out, exist_ok=True)
    rows = ref.set_index("zcta").loc[sorted(inst.units.unit_of)]
    p = {z: (float(x) / 1000.0, float(y) / 1000.0) for z, x, y in zip(rows.index, rows["x"], rows["y"])}
    state = dict(zip(rows.index, rows["state"]))
    with open(os.path.join(a.run_dir, "contig.json")) as fh:
        doc = json.load(fh)
    connectors = set(geo.approved_connectors(geo.read_connectors()))
    drawings = {}
    for c, plan in plans.items():
        owner = owners[c]
        attempts = []
        if a.channels is None or c in a.channels:
            owner, attempts = repair_channel(inst, plan, owner, p, state, a.h0, a.max_zctas,
                                             a.time_limit)
        res = draw.Result(c, owner, [], set(), [], [], plan.delta, "repair", False)
        d = draw.drawing(inst, plan, res)
        drawings[c] = d
        left = detached(owner, inst.units.zip_adj, inst.channels[c].m)
        entry = doc["channels"][c]
        entry["repair"] = attempts
        entry["groups"] = entry["groups"] + [r["group"] for r in attempts]
        if attempts:
            entry["connected"] = not left
            entry["status"] = "connected" if not left else entry["status"]
        entry.update(run.drawn_stats(inst, plan, d, connectors, not left))
    report, m1 = run.write_folder(a.out, s, inst, ext, ref, polygon, plans, reports, drawings,
                                  f"{s.name} (contig {doc['arm']} + window repair)",
                                  f"tools/exp/contig ({doc['arm']} + repair)", src.get("source", ""),
                                  a.maps)
    doc.update({"arm": doc["arm"] + "+repair", "repair_of": os.path.abspath(a.run_dir),
                "repair": {"h0": a.h0, "max_zctas": a.max_zctas, "time_limit": a.time_limit},
                "m1": report["m1"]})
    with open(os.path.join(a.out, "contig.json"), "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=2, sort_keys=True)
        fh.write("\n")
    print(f"{s.name} (repair of {a.run_dir}): M1 {m1.status} ({m1.summary}); audit "
          f"{report['verdict']}")
    return 0 if m1.status == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
