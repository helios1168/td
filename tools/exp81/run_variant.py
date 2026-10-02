"""run_variant.py -- #81's variant: lane A's Hess loop seeded from the support arm's map.

    "$TD_PY" -u tools/exp81/run_variant.py solve <channel> [--out DIR]
    "$TD_PY" -u tools/exp81/run_hess.py assemble --out DIR
    "$TD_PY" -u tools/exp81/run_variant.py compare [--out DIR]

`solve` is `run_hess.py solve` with one change: `hess.plan` starts from the support arm's drawn
district centroids (`seed_support`) instead of the k-means seed, and skips the LP-relaxed rounds,
so the first assignment is made at the support map's own geometry.  Everything else, the rows,
the restricted first assignment, the fixed-centre MILPs and the stop rule, is lane A's, and the
plan file has lane A's format plus a `seed` record: the ledger it came from, the support
district behind each centre, and the support map's Hess objective at those centres.

`compare` reads the variant's plans, lane A's plans and the support ledger, and reports per
channel the seed's objective, the variant's converged objective and iterations, its distance from
lane A's objective, and the ZIPs (m_z > 0) and whole units that left their support district.
Variant district j is matched to the support district its centre started at, and also, as a check
on label drift, by the one-to-one matching of largest shared mass; the variant and lane A are
matched by the latter.  It writes `<out>/compare.json`.
"""
from __future__ import annotations

import argparse
import collections
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, HERE)

import hess  # noqa: E402
import run_hess  # noqa: E402  (sets the margin off and the batched polygons, as run3.py does)
import seed_support  # noqa: E402

OUT = os.path.join(run_hess.TD_REPO, "runs", "exp81", "hess_from_support")
LANE_A = os.path.join(run_hess.TD_REPO, "runs", "exp81", "hess")


def seed_record(inst, channel: str, p: dict, ledger: str) -> tuple:
    """(centres, record): the seed of `channel` and what the plan file says about it.  The
    ledger's masses must be the instance's on every ZIP with m_z > 0."""
    ch = inst.channels[channel]
    owner, mass = seed_support.read(ledger, channel)
    pos = {z for z in ch.m if ch.m[z] > 0}
    if pos - set(owner):
        raise hess.HessError(f"{ledger}: {len(pos - set(owner))} positive {channel} ZIPs unplaced")
    off = [z for z in pos if abs(mass[z] - ch.m[z]) > 1e-6 * max(1.0, ch.m[z])]
    if off:
        raise hess.HessError(f"{ledger}: m_rel differs from the instance on {sorted(off)[:5]}")
    ids, centres = seed_support.centres(ledger, channel, p)
    if len(ids) != ch.k:
        raise hess.HessError(f"{ledger}: {len(ids)} {channel} districts for K = {ch.k}")
    m = {z: ch.m.get(z, 0.0) for z in owner}
    return centres, {"source": ledger, "districts": ids, "relaxed_rounds": False,
                     "objective": seed_support.objective(owner, m, p)}


def cmd_solve(a) -> int:
    real_plan, record = hess.plan, {}

    def plan(inst, channel, p, band, *args, **kw):
        centres, record["seed"] = seed_record(inst, channel, p, a.ledger)
        print(f"{channel}: seed from {len(centres)} support districts, Hess objective "
              f"{record['seed']['objective']:.6g} at their centroids", flush=True)
        return real_plan(inst, channel, p, band, *args, seed=centres, relax=False, **kw)

    hess.plan = plan
    try:
        rc = run_hess.cmd_solve(a)
    finally:
        hess.plan = real_plan
    path = os.path.join(a.out, "plans", f"{a.channel}.json")
    with open(path, encoding="utf-8") as fh:
        doc = json.load(fh)
    doc["seed"] = record["seed"]
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=1)
        fh.write("\n")
    return rc


def plan_owner(doc: dict, m: dict) -> dict:
    """{zip: district index} over a plan's ZIPs with m_z > 0 (a whole unit's item also lists
    its zero-mass ZIPs)."""
    return {z: it["district"] for it in doc["items"] for z in it["zips"] if m.get(z, 0.0) > 0}


def max_overlap(a: dict, b: dict, m: dict) -> dict:
    """{label of a: label of b}, the one-to-one matching of largest shared mass."""
    from scipy.optimize import linear_sum_assignment
    la, lb = sorted(set(a.values())), sorted(set(b.values()))
    w = [[0.0] * len(lb) for _ in la]
    ia, ib = {x: i for i, x in enumerate(la)}, {x: i for i, x in enumerate(lb)}
    for z in a:
        w[ia[a[z]]][ib[b[z]]] += m[z]
    r, c = linear_sum_assignment(w, maximize=True)
    return {la[i]: lb[j] for i, j in zip(r, c)}


def moved(inst, channel: str, a: dict, b: dict, match: dict) -> dict:
    """What left its district between maps a and b (labels of a sent through `match`)."""
    ch, units = inst.channels[channel], inst.units
    zs = [z for z in a if match[a[z]] != b[z]]
    whole = sorted({units.unit_of[z] for z in zs if ch.mode[units.unit_of[z]] == "whole"})
    free = [z for z in zs if ch.mode[units.unit_of[z]] == "free"]
    total = math.fsum(ch.m[z] for z in a)
    return {"zips": len(zs), "of_zips": len(a),
            "m_rel_share": math.fsum(ch.m[z] for z in zs) / total,
            "whole_units": len(whole), "whole_unit_names": whole,
            "of_whole_units": sum(ch.mode[v] == "whole" for v in ch.units),
            "free_unit_zips": len(free),
            "free_units_touched": sorted({units.unit_of[z] for z in free})}


def cmd_compare(a) -> int:
    s, ext, ref, graph, inst = run_hess.instance()
    out = {}
    for c in inst.channels:
        docs = {}
        for arm, d in (("variant", a.out), ("lane_a", a.lane_a)):
            with open(os.path.join(d, "plans", f"{c}.json"), encoding="utf-8") as fh:
                docs[arm] = json.load(fh)
        var, la = docs["variant"], docs["lane_a"]
        sup_owner, _ = seed_support.read(a.ledger, c)
        vo, lo = plan_owner(var, inst.channels[c].m), plan_owner(la, inst.channels[c].m)
        if set(vo) != set(lo):
            raise SystemExit(f"{c}: the two plans place different ZIPs")
        so = {z: sup_owner[z] for z in vo}
        by_label = dict(enumerate(var["seed"]["districts"]))
        by_mass = max_overlap(vo, so, inst.channels[c].m)
        steps = [st for it in var["iterations"] for st in it["steps"]]
        full = [st for st in steps if st["nearest"] is None]
        out[c] = {
            "k": var["k"], "stop": var["stop"], "time_s": var["time_s"],
            "seed_objective": var["seed"]["objective"],
            "start_objective_recentred": var["iterations"][0]["objective_recentred"],
            "objective": var["objective"],
            "centre_iterations": sum(it["iteration"] >= 0 for it in var["iterations"]),
            "full_milps": len(full),
            "full_milps_optimal": sum(st["status"] == "optimal" for st in full),
            "last_milp": {k: (full or steps)[-1][k] for k in ("status", "objective", "bound", "gap")},
            "lane_a_objective": la["objective"],
            "vs_lane_a": (var["objective"] - la["objective"]) / la["objective"],
            "vs_seed": (var["objective"] - var["seed"]["objective"]) / var["seed"]["objective"],
            "match_by_label_is_max_overlap": by_mass == by_label,
            "moved_from_support": moved(inst, c, vo, so, by_label),
            "moved_from_support_max_overlap": moved(inst, c, vo, so, by_mass),
            "differs_from_lane_a": moved(inst, c, vo, lo, max_overlap(vo, lo, inst.channels[c].m)),
        }
        r = out[c]
        print(f"{c}: seed {r['seed_objective']:.6g} -> {r['objective']:.6g} "
              f"({100 * r['vs_seed']:+.2f}%), {r['centre_iterations']} iterations, {r['stop']}; "
              f"lane A {r['lane_a_objective']:.6g} ({100 * r['vs_lane_a']:+.3f}%); moved "
              f"{r['moved_from_support']['zips']} ZIPs, {r['moved_from_support']['whole_units']} "
              f"whole units; {r['differs_from_lane_a']['zips']} ZIPs differ from lane A",
              flush=True)
    with open(os.path.join(a.out, "compare.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2, sort_keys=True)
        fh.write("\n")
    return 0


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
    cp = sub.add_parser("compare")
    cp.add_argument("--lane-a", default=LANE_A)
    for p in (sv, cp):
        p.add_argument("--out", default=OUT)
        p.add_argument("--ledger", default=seed_support.SUPPORT_LEDGER)
    a = ap.parse_args(argv)
    return cmd_solve(a) if a.cmd == "solve" else cmd_compare(a)


if __name__ == "__main__":
    sys.exit(main())
