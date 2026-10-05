"""run_hess.py -- #81's Hess arm: solve each channel, then assemble one run directory.

    "$TD_PY" -u tools/exp81/run_hess.py solve <channel> [--band planning|final] [--out DIR]
    "$TD_PY" -u tools/exp81/run_hess.py assemble [--out DIR]

`solve` runs `hess.plan` on one planning channel and writes `<out>/plans/<channel>.json`: the
item assignment, centres, stop reason and every iteration's MILP report.  Run one process per
channel; each fixes its HiGHS thread count (trap 18).  `assemble` reads the three plans and
writes the run directory in the layout `python -m td run` writes (ledger.csv, districts.csv,
run.json, solver.json, scorecard.md, maps/), plus `hess_solver.json`.

The support arm's caveats hold here too (#81 brief): the rounding margin is off in memory
(`supports.margin`, unused by this planner but kept for parity with run3.py), ZIP 13027's
sub-tolerance FI cell is zeroed at load, and the ZCTA polygons are read in batches.

**From an assignment to a map** (`drawing`), each step the support arm's own code:
- a district's copy is named by its drawn support, as `td.master.Copy` names one, and its planned
  masses are the Hess assignment's, so the audit compares them with the drawn ones;
- a free unit's zero-mass ZIPs go by `td.realize.place_zero`, from the unit's placed ZIPs, with
  the district centres as the fallback;
- one repair pass, `td.realize.repair`, under the final band and the mode guard (S23, C16);
- pieces and their causes by `td.realize.pieces`, the territory pass `td.territory.own_territory`
  (#116), then the ledger, names, audit, districts and maps by `td.output`, as `td.output.run`
  calls them.

`solver.json` carries one report per channel for the audit: status `local optimum`, the Hess
objective, and no bound, since the loop proves none over all centres; the audit's tier is then
`feasible only`.  `hess_solver.json` has the engine detail: each MILP's status, bound and gap at
its fixed centres, model size, wall time and the loop's iterations.  `policy_check` lists any
drawn district whose unit set breaks a support-family rule after repair.
"""
from __future__ import annotations

import argparse
import collections
import json
import math
import os
import re
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from td import audit, data, geo, master, output, realize, supports, territory  # noqa: E402
from td import spec as tdspec  # noqa: E402

import hess  # noqa: E402

TD_REPO = os.environ.get("TD_REPO", "/Users/Shared/sv-ntlee/td")
EXTRACT = os.path.join(TD_REPO, "instance_descaled.json.gz")
PUBLIC = os.path.join(TD_REPO, "data", "public")
SPEC = os.path.join(ROOT, "scenarios", "experiments", "16n_12wh_24fi_nowifi_mtn1600.toml")
OUT = os.path.join(TD_REPO, "runs", "exp81", "hess")

supports.margin = lambda *a, **k: 0.0          # run3.py:5, the margin off in memory


def load_extract(path: str):
    """The extract with ZIP 13027's sub-tolerance FI cell zeroed (run3.py:84-85, #73)."""
    e = data.load(path)
    e.m_rel = [0.0 if m < 1e-6 else m for m in e.m_rel]
    return e


def zcta_polygons(zips, public=geo.PUBLIC_DIR):
    """`output.zcta_polygons` in batches of 500: GDAL rejects one 6,623-item IN list (run3.py)."""
    path = output.zcta_file(public)
    if path is None:
        raise output.RunError(f"{output.MAPS_SKIPPED}: no {output.ZCTA_FILE} in {public}")
    zs = sorted(z for z in set(zips) if re.fullmatch(r"\d{5}", z))
    out = {}
    for i in range(0, len(zs), 500):
        df = geo._read(path, ["ZCTA5CE20"],
                       where=f"ZCTA5CE20 IN ({','.join(repr(z) for z in zs[i:i + 500])})")
        out.update({z: g.simplify(output.SIMPLIFY_M, preserve_topology=True)
                    for z, g in zip(df["ZCTA5CE20"], df.geometry)})
    return out


output.zcta_polygons = zcta_polygons


def instance():
    """(spec, scoped extract, reference, graph, instance), as `td.output.run` builds them."""
    s = tdspec.load(os.path.relpath(SPEC, ROOT) if os.getcwd() == ROOT else SPEC)
    ref = geo.read_reference()
    ext = tdspec.scope(s, data.conus(load_extract(EXTRACT), ref))
    graph = output.declared_graph(ext, ref, PUBLIC)
    return s, ext, ref, graph, tdspec.build(s, ext, ref, graph)


def band_of(ch, which: str) -> tuple:
    """(L, U, δ): the planning band (the master's band row, margin off) or the final band."""
    if which == "planning":
        return (*ch.band, ch.spec.delta)
    return (*ch.final_band, ch.spec.final_delta)


# ------------------------------------------------------------------------------ solve
def cmd_solve(a) -> int:
    hess.THREADS = a.threads
    s, ext, ref, graph, inst = instance()
    ch = inst.channels[a.channel]
    lo, hi, delta = band_of(ch, a.band)
    p = hess.positions(inst)

    def log(msg):
        print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)

    log(f"{a.channel}: K {ch.k}, band {a.band} δ {delta} [{lo:.6g}, {hi:.6g}], "
        f"{a.threads} threads")
    res, m = hess.plan(inst, a.channel, p, (lo, hi), a.max_iters, a.time_limit, a.total_limit, log)
    doc = {
        "channel": a.channel, "k": ch.k, "band": a.band, "delta": delta, "band_m_rel": [lo, hi],
        "threads": a.threads, "stop": res.stop, "objective": res.objective, "time_s": res.time_s,
        "seed_centres": res.seed_centres, "relaxed_rounds": res.relaxed, "centres": res.centres,
        "items": [{"unit": it.unit, "zips": list(it.zips), "district": j}
                  for it, j in zip(m.items, res.assign)],
        "iterations": res.iterations,
        "model": {"rows": len(m.rows), "cols": m.ncols, "integers": sum(m.integer),
                  "nonzeros": sum(len(coef) for coef, _, _, _ in m.rows),
                  "items": len(m.items), "upfront_cuts": m.upfront, "cuts": len(m.cuts),
                  "rows_by_kind": dict(collections.Counter(k for _, _, _, k in m.rows))}}
    os.makedirs(os.path.join(a.out, "plans"), exist_ok=True)
    path = os.path.join(a.out, "plans", f"{a.channel}.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=1)
        fh.write("\n")
    log(f"{a.channel}: {res.stop}, objective {res.objective:.6g}, {res.time_s}s -> {path}")
    return 0


# ------------------------------------------------------------------------------ assemble
def drawing(inst, doc: dict, p: dict) -> tuple:
    """(Plan, Drawing) of one channel from its plan file (module docstring)."""
    c = doc["channel"]
    ch, units = inst.channels[c], inst.units
    by_j: dict = collections.defaultdict(collections.Counter)    # j -> unit -> planned mass
    owner_j = {}
    for it in doc["items"]:
        for z in it["zips"]:
            owner_j[z] = it["district"]
            by_j[it["district"]][it["unit"]] += ch.m[z]
    if sorted(by_j) != list(range(ch.k)):
        raise output.RunError(f"channel {c}: the plan fills {len(by_j)} of K = {ch.k} districts")
    copies, name, seen = [], {}, collections.Counter()
    for j in range(ch.k):
        sup = frozenset(by_j[j])
        seen[sup] += 1
        mass = {v: by_j[j][v] for v in sorted(sup)}
        cp = master.Copy(sup, seen[sup], {v: x / ch.M[v] for v, x in mass.items()}, mass)
        copies.append(cp)
        name[j] = cp.name
    support = {cp.name: cp.support for cp in copies}
    planned = {(v, cp.name): x for cp in copies for v, x in cp.mass.items()}
    owner = {z: name[j] for z, j in owner_j.items()}
    centre = {name[j]: tuple(xy) for j, xy in enumerate(doc["centres"])}
    for v in ch.units:
        zeros = [z for z in units.zips[v] if z not in owner]
        if zeros:
            own = {z: owner[z] for z in units.zips[v] if z in owner}
            owner.update(realize.place_zero(zeros, own, units.zip_adj, p, centre))
    moved = realize.repair(inst, c, owner, support)
    drawn, mass = dict.fromkeys(planned, 0.0), {cp.name: 0.0 for cp in copies}
    for z, j in owner.items():
        drawn[units.unit_of[z], j] = drawn.get((units.unit_of[z], j), 0.0) + ch.m[z]
        mass[j] += ch.m[z]
    d = realize.Drawing(c, owner, mass, planned, drawn,
                        realize.pieces(inst, c, owner, support, planned), moved)
    report = {"status": "local optimum", "objective": doc["objective"], "bound": None,
              "gap": None, "mip_rel_gap": 0.0, "time_s": doc["time_s"]}
    n = collections.Counter(cp.support for cp in copies)
    t = {(v, s): math.fsum(cp.share[v] for cp in copies if cp.support == s) for s in n for v in s}
    plan = master.Plan(c, doc["delta"], dict(n), t, copies, doc["objective"], report)
    return plan, d, report


def drawn_objective(inst, c: str, d, p: dict) -> float:
    """Σ_z m_z ‖p_z − c_j‖² over the drawn map, c_j its district's opportunity-weighted centroid."""
    m = inst.channels[c].m
    groups = collections.defaultdict(list)
    for z, j in d.owner.items():
        if m[z] > 0:
            groups[j].append(z)
    out = 0.0
    for zs in groups.values():
        cx, cy = realize.centroid(zs, m, p)
        out += math.fsum(m[z] * ((p[z][0] - cx) ** 2 + (p[z][1] - cy) ** 2) for z in zs)
    return out


def policy_check(inst, c: str, d) -> list:
    """Drawn districts whose unit set breaks a support-family or master rule after repair."""
    ch, cs = inst.channels[c], inst.channels[c].spec
    adj = supports.unit_graph(inst, c)
    sets = collections.defaultdict(set)
    for (v, j), x in d.drawn.items():
        if x > 0:
            sets[j].add(v)
    out = []
    for j, s in sorted(sets.items()):
        if len(s) > cs.max_size:
            out.append(f"{j}: {len(s)} units > max_size {cs.max_size}")
        far = [(a, b) for a in sorted(s) for b in sorted(s)
               if a < b and inst.units.distance_km(a, b) > cs.dist_cap(a, b)]
        if far:
            out.append(f"{j}: beyond the distance cap {far}")
        if not supports.connected(s, adj):
            out.append(f"{j}: unit set {sorted(s)} not connected in G")
        thin = [v for v in sorted(s) if d.drawn[v, j] < cs.eta * ch.M[v] * (1 - 1e-9)]
        if thin:
            out.append(f"{j}: drawn share below η {cs.eta} in {thin}")
    touch = collections.Counter(v for s in sets.values() for v in s)
    for v, cap in sorted(cs.contact_caps.items()):
        if touch[v] > cap:
            out.append(f"{v}: {touch[v]} districts > contact cap {cap}")
    for v in ch.units:
        if ch.mode[v] == "free" and touch[v] > master.eta_cap(cs.eta):
            out.append(f"{v}: {touch[v]} districts > ⌊1/η⌋ {master.eta_cap(cs.eta)}")
    return out


def cmd_assemble(a) -> int:
    s, ext, ref, graph, inst = instance()
    p = hess.positions(inst)
    docs = {}
    for c in inst.channels:
        with open(os.path.join(a.out, "plans", f"{c}.json"), encoding="utf-8") as fh:
            docs[c] = json.load(fh)
    plans, drawings, reports = {}, {}, {}
    state = dict(zip(ref["zcta"], ref["state"]))
    for c in inst.channels:
        plans[c], drawings[c], reports[c] = drawing(inst, docs[c], p)
        territory.own_territory(inst, plans[c], drawings[c], p, state)   # #116, as td.output.run
    out = a.out
    for f in ("ledger.csv", "districts.csv", "run.json", "solver.json", "scorecard.md"):
        if os.path.exists(os.path.join(out, f)):
            os.remove(os.path.join(out, f))
    conus = data.conus(load_extract(EXTRACT), ref)
    paths = {"solver": output.write_solver(os.path.join(out, "solver.json"), reports, {})}
    areas = output.read_areas()
    led = output.ledger(inst, drawings, ext, ref)
    names = output.name_districts(led, output.cbsa_titles(areas))
    for r in led:
        r["district_name"] = names.get(r["district"], "")
    paths["ledger"] = output.write_ledger(os.path.join(out, "ledger.csv"), led)
    led = output.read_ledger(paths["ledger"])
    with open(os.path.join(geo.REFERENCE_DIR, "MANIFEST.json"), encoding="utf-8") as fh:
        manifest = json.load(fh)
    split = output.ledger_pieces(led, graph, drawings)
    checks = audit.audit(output.audit_run(inst, led, drawings, ext, reports, graph, names,
                                          manifest, ref, split))
    paths["scorecard"] = audit.write_scorecard(out, checks, f"{s.name} Hess arm "
                                               f"({os.path.basename(EXTRACT)})")
    paths["districts"] = output.write_districts(os.path.join(out, "districts.csv"), inst, plans,
                                                drawings, names, split)
    report = {
        "scenario": s.name, "spec": s.path, "source": os.path.basename(EXTRACT),
        "planner": "tools/exp81/hess.py (Hess-style ZIP planner, #81)",
        "verdict": audit.verdict(checks), "cells": len(led),
        "zips": len({r["zip_code"] for r in led}),
        "not_placed_zips": len({r["zip_code"] for r in led if r["reason"] == output.NOT_PLACED}),
        "zero_opportunity_zips": len(set(ext.zips) - output.positive_zips(ext)),
        "conus_dropped": ext.dropped,
        "planned_elsewhere": {f: sum(1 for c in conus.channel if c == f) for f in s.planned_elsewhere},
        "dropped_units": {c: list(u) for c, u in inst.report.get("dropped_units", {}).items()},
        "dropped_channels": list(inst.dropped_channels),
        "national_moved_units": sorted(inst.report.get("national_moved", {})),
        "disconnected_units": sorted(inst.report.get("disconnected", {})),
        "channels": {c: {"k": inst.channels[c].k, "delta": plans[c].delta,
                         "tier": audit.tier(reports[c]), "status": reports[c]["status"],
                         "moved": len(d.moved), "vanished": len(d.vanished),
                         **output.piece_counts(split, c)}
                     for c, d in drawings.items()}}
    if output.zcta_file(PUBLIC) is None:
        report["maps"] = output.MAPS_SKIPPED
    else:
        drawn = output.draw_maps(paths["ledger"], os.path.join(out, "maps"), ref, areas, PUBLIC,
                                 root=out)
        report["maps"] = "drawn"
        report["maps_missing_polygons"] = sorted({z for m in drawn.values() for z in m["missing"]})
    with open(os.path.join(out, "run.json"), "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2, sort_keys=True)
        fh.write("\n")
    import highspy
    hs = {}
    for c, doc in docs.items():
        steps = [st for it in doc["iterations"] for st in it["steps"]]
        full = [st for st in steps if st["nearest"] is None]
        last = (full or steps)[-1]
        hs[c] = {
            "engine": f"HiGHS {highspy.Highs().version()} (highspy), MILP at fixed centres",
            "band": doc["band"], "delta": doc["delta"], "threads": doc["threads"],
            "stop_reason": doc["stop"], "certificate": "local optimum of location-allocation; "
            "each MILP certified at its own centres only when it ends optimal; no bound over "
            "all centres",
            "objective": doc["objective"], "objective_units": "m_rel * km^2 (EPSG:5070 km)",
            "objective_drawn": drawn_objective(inst, c, drawings[c], p),
            "last_milp": {k: last[k] for k in ("status", "objective", "bound", "gap", "time_s")},
            "full_milps_optimal": sum(st["status"] == "optimal" for st in full),
            "full_milps": len(full),
            "wall_time_s": doc["time_s"],
            "milp_time_s": round(math.fsum(st["time_s"] for st in steps), 3),
            "model": {**doc["model"], "rows_final": last["rows"], "nonzeros_final": last["nonzeros"]},
            "centre_iterations": sum(it["iteration"] >= 0 for it in doc["iterations"]),
            "milp_solves": len(steps),
            "nodes": sum(st["nodes"] for st in steps),
            "simplex_iterations": sum(st["lp_iterations"] for st in steps),
            "connect_cuts": {"upfront": doc["model"]["upfront_cuts"],
                             "lazy": doc["model"]["cuts"] - doc["model"]["upfront_cuts"]},
            "iterations": doc["iterations"],
            "repair_moves": len(drawings[c].moved),
            "policy_check": policy_check(inst, c, drawings[c])}
    with open(os.path.join(out, "hess_solver.json"), "w", encoding="utf-8") as fh:
        json.dump(hs, fh, indent=2, sort_keys=True)
        fh.write("\n")
    for c, r in report["channels"].items():
        print(f"{c}: K = {r['k']}, δ = {r['delta']}, {r['status']}, tier {r['tier']}, "
              f"{r['pieces']} pieces, {r['moved']} moved; policy {hs[c]['policy_check'] or 'held'}")
    print(f"audit: {report['verdict']}; {out}")
    return 0 if report["verdict"] == "pass" else 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    sv = sub.add_parser("solve")
    sv.add_argument("channel")
    sv.add_argument("--band", choices=("planning", "final"), default="planning")
    sv.add_argument("--threads", type=int, default=hess.THREADS)
    sv.add_argument("--max-iters", type=int, default=hess.MAX_ITERS)
    sv.add_argument("--time-limit", type=float, default=hess.TIME_LIMIT)
    sv.add_argument("--total-limit", type=float, default=hess.TOTAL_LIMIT)
    sv.add_argument("--out", default=OUT)
    asm = sub.add_parser("assemble")
    asm.add_argument("--out", default=OUT)
    a = ap.parse_args(argv)
    return cmd_solve(a) if a.cmd == "solve" else cmd_assemble(a)


if __name__ == "__main__":
    sys.exit(main())
