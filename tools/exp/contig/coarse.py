"""coarse.py -- a single-state channel drawn by coarsening to legislative districts: each ZCTA of
the state's induced polygon graph goes to the TIGER 2025 district (state senate `sldu` or
congressional `cd`) holding most of its land, each district's ZCTAs split into connected
components (the coarse units), the units grouped into K connected districts in the mass band at
the least total border between groups (a small flow-contiguity MILP), and the groups expanded to
ZCTAs and written as a `run.py` folder audited on the full polygon graph (#52).

    "$TD_PY" -u tools/exp/contig/coarse.py --state NY --k 5 --level sldu|cd --out <dir>
        [--extract PATH] [--spec PATH] [--lo M --hi M] [--window] [--time-limit S]
        [--nogood UNITS ...] [--thin-floor]
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import sys
import time

import numpy as np
from scipy import sparse
from scipy.optimize import Bounds, LinearConstraint, milp

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)

FIPS = {"NY": "36"}
TIGER_FILE = {"sldu": "tl_2025_{fips}_sldu.zip", "cd": "tl_2025_{fips}_cd119.zip"}
KEY = {"sldu": "SLDUST", "cd": "CD119FP"}
DATA = os.path.join(ROOT, "runs", "exp", "contig", "nycd", "data")
ZCTA_ZIP = os.path.join(os.environ.get("TD_REPO", ROOT), "data", "public", "tl_2025_us_zcta520.zip")


def components(nodes, adj: dict) -> list:
    """Connected components of `nodes` on `adj` restricted to `nodes`, each a sorted list."""
    left, out = set(nodes), []
    while left:
        stack, comp = [left.pop()], []
        while stack:
            z = stack.pop()
            comp.append(z)
            for y in adj.get(z, ()):
                if y in left:
                    left.remove(y)
                    stack.append(y)
        out.append(sorted(comp))
    return sorted(out)


def adjacency(edges) -> dict:
    adj = collections.defaultdict(set)
    for a, b in edges:
        adj[a].add(b)
        adj[b].add(a)
    return adj


def district_of(vertices, state: str, level: str) -> dict:
    """{zcta: district code} by the largest land overlap (EPSG:5070 area); a ZCTA overlapping no
    district takes the nearest."""
    import geopandas as gpd
    fips = FIPS[state]
    dist = gpd.read_file(os.path.join(DATA, TIGER_FILE[level].format(fips=fips)))
    dist = dist[[KEY[level], "geometry"]].rename(columns={KEY[level]: "unit"}).to_crs(5070)
    dist = dist[~dist["unit"].str.startswith("Z")]          # ZZZ: water-only remainder
    z = gpd.read_file(ZCTA_ZIP, bbox=tuple(dist.to_crs(4269).total_bounds))
    z = z[z["ZCTA5CE20"].isin(set(vertices))][["ZCTA5CE20", "geometry"]].to_crs(5070)
    ov = gpd.overlay(z, dist, how="intersection", keep_geom_type=True)
    ov["a"] = ov.geometry.area
    best = ov.sort_values("a").groupby("ZCTA5CE20").tail(1)
    out = dict(zip(best["ZCTA5CE20"], best["unit"]))
    rest = z[~z["ZCTA5CE20"].isin(set(out))]
    if len(rest):
        near = gpd.sjoin_nearest(rest, dist, how="left")
        out.update(dict(zip(near["ZCTA5CE20"], near["unit"])))
    missing = set(vertices) - set(out)
    if missing:
        raise RuntimeError(f"{len(missing)} vertices without a polygon: {sorted(missing)[:5]}")
    return out


def assign_units(vertices, edges, district: dict) -> dict:
    """{zcta: unit id}: each district's ZCTAs split into connected components on `edges`, unit
    `<district>.<i>` (i by size, 0 the largest)."""
    adj = adjacency(edges)
    by = collections.defaultdict(list)
    for z in vertices:
        by[district[z]].append(z)
    unit = {}
    for d, zs in sorted(by.items()):
        for i, comp in enumerate(sorted(components(zs, adj), key=len, reverse=True)):
            unit.update({z: f"{d}.{i}" for z in comp})
    return unit


def coarse_graph(unit: dict, edges, border_km: dict, mass: dict) -> dict:
    """{"units", "mass", "edges": {(u, v): km}} the unit graph: unit mass, and per adjacent unit
    pair the summed border km of their ZCTA edges (0 for a connector-only adjacency)."""
    m = collections.Counter()
    for z, u in unit.items():
        m[u] += mass.get(z, 0.0)
    e = collections.defaultdict(float)
    for a, b in edges:
        ua, ub = unit[a], unit[b]
        if ua != ub:
            e[tuple(sorted((ua, ub)))] += border_km.get(tuple(sorted((a, b))), 0.0)
    units = sorted(set(unit.values()))
    return {"units": units, "mass": {u: float(m[u]) for u in units}, "edges": dict(e)}


def thin_units(unit: dict, mass: dict, polygon: dict, log=print) -> tuple:
    """({unit: land m²}, {unit: land m² if thin else 0}): a unit is thin when, as a district on its
    own, it has an M1 neck on the full polygon graph (`audit.district_necks`)."""
    from td import audit
    ng = audit.NeckGraph(polygon)
    by = collections.defaultdict(set)
    for z, u in unit.items():
        by[u].add(z)
    land, thin = {}, {}
    for u, zs in sorted(by.items()):
        land[u] = float(sum(polygon["aland"].get(z, 0.0) for z in zs))
        necks = audit.district_necks(zs, {z: mass.get(z, 0.0) for z in zs}, ng)
        thin[u] = land[u] if necks else 0.0
        if necks:
            log(f"thin unit {u}: {len(zs)} ZCTAs, land {land[u] / 1e6:.1f} km², {necks}")
    return land, thin


def partition(g: dict, k: int, lo: float, hi: float, time_limit: float = 300.0,
              nogood=(), land=None, thin=None, log=print) -> dict:
    """{"group": {unit: 0..k-1}, "status", "gap", "seconds", "cut_km"}: k connected groups of the
    unit graph `g`, each of mass in [lo, hi], at the least total border between groups.  A
    single-commodity flow per group from a chosen root; the heaviest unit is fixed to group 0;
    each set in `nogood` may not be a group exactly.  With `land` and `thin` ({unit: m²}, see
    `thin_units`), each group's thin land is at most `audit.NECK_SHARE` of its land."""
    U, E = g["units"], sorted(g["edges"])
    n, ne = len(U), len(E)
    idx = {u: i for i, u in enumerate(U)}
    arcs = [(idx[a], idx[b]) for a, b in E] + [(idx[b], idx[a]) for a, b in E]
    na = len(arcs)
    # columns: x[u,g] | r[u,g] | f[a,g] | y[e]
    X = lambda u, h: u * k + h
    R = lambda u, h: n * k + u * k + h
    F = lambda a, h: 2 * n * k + a * k + h
    Y = lambda e: 2 * n * k + na * k + e
    nv = 2 * n * k + na * k + ne
    rows, cols, vals, lb, ub = [], [], [], [], []
    r = 0

    def add(terms, lo_, hi_):
        nonlocal r
        for c, v in terms:
            rows.append(r)
            cols.append(c)
            vals.append(v)
        lb.append(lo_)
        ub.append(hi_)
        r += 1

    mass = np.array([g["mass"][u] for u in U])
    for u in range(n):
        add([(X(u, h), 1) for h in range(k)], 1, 1)
    for h in range(k):
        add([(X(u, h), mass[u]) for u in range(n)], lo, hi)
        add([(R(u, h), 1) for u in range(n)], 1, 1)
        for u in range(n):
            add([(R(u, h), 1), (X(u, h), -1)], -np.inf, 0)
        out_arcs = collections.defaultdict(list)
        in_arcs = collections.defaultdict(list)
        for a, (s, t) in enumerate(arcs):
            out_arcs[s].append(a)
            in_arcs[t].append(a)
            add([(F(a, h), 1), (X(s, h), -(n - 1))], -np.inf, 0)
            add([(F(a, h), 1), (X(t, h), -(n - 1))], -np.inf, 0)
        for u in range(n):    # inflow - outflow >= x - n r  (a root may emit up to n)
            add([(F(a, h), 1) for a in in_arcs[u]] + [(F(a, h), -1) for a in out_arcs[u]]
                + [(X(u, h), -1), (R(u, h), n)], 0, np.inf)
    for e, (a, b) in enumerate(E):
        for h in range(k):
            add([(Y(e), 1), (X(idx[a], h), -1), (X(idx[b], h), 1)], 0, np.inf)
            add([(Y(e), 1), (X(idx[b], h), -1), (X(idx[a], h), 1)], 0, np.inf)
    for bad in nogood:      # sum_{u in S} x[u,h] - sum_{u not in S} x[u,h] <= |S| - 1, all h
        S = {idx[u] for u in bad}
        for h in range(k):
            add([(X(u, h), 1 if u in S else -1) for u in range(n)], -np.inf, len(S) - 1)
    if thin is not None:    # sum_u x[u,h] (thin(u) - NECK_SHARE land(u)) <= 0, all h
        from td.audit import NECK_SHARE
        for h in range(k):
            add([(X(u, h), thin[U[u]] - NECK_SHARE * land[U[u]]) for u in range(n)], -np.inf, 0)
    lo_b, hi_b = np.zeros(nv), np.ones(nv)
    hi_b[2 * n * k: 2 * n * k + na * k] = n - 1
    heavy = int(np.argmax(mass))
    lo_b[X(heavy, 0)] = 1
    integ = np.zeros(nv)
    integ[: 2 * n * k] = 1
    c = np.zeros(nv)
    for e, (a, b) in enumerate(E):
        c[Y(e)] = g["edges"][a, b] + 1e-3      # tie-break: fewer cut adjacencies
    A = sparse.csr_matrix((vals, (rows, cols)), shape=(r, nv))
    log(f"partition: {n} units, {ne} unit edges, k {k}, band [{lo:.2f}, {hi:.2f}], "
        f"{nv} columns, {r} rows")
    t0 = time.time()
    res = milp(c, constraints=LinearConstraint(A, lb, ub), integrality=integ,
               bounds=Bounds(lo_b, hi_b),
               options={"time_limit": time_limit, "mip_rel_gap": 0.0, "disp": False})
    sec = time.time() - t0
    out = {"status": res.message, "success": res.x is not None, "seconds": round(sec, 1),
           "gap": getattr(res, "mip_gap", None), "bound": getattr(res, "mip_dual_bound", None),
           "units": n, "unit_edges": ne}
    if res.x is None:
        return out
    x = res.x[: n * k].reshape(n, k)
    out["group"] = {U[u]: int(np.argmax(x[u])) for u in range(n)}
    out["cut_km"] = float(sum(g["edges"][e] for e in E
                              if out["group"][e[0]] != out["group"][e[1]]))
    out["objective"] = float(res.fun)
    return out


def expand(unit: dict, group: dict, names: list) -> dict:
    """{zcta: district name}: every ZCTA takes its unit's group, group h named `names[h]`."""
    return {z: names[group[u]] for z, u in unit.items()}


def main(argv=None) -> int:
    import run as contig
    from draw import drawing, Result
    from td import data, geo, master, output, spec as tdspec

    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--state", default="NY")
    ap.add_argument("--k", type=int, default=5)
    ap.add_argument("--level", choices=sorted(TIGER_FILE), default="sldu")
    ap.add_argument("--out", required=True)
    ap.add_argument("--extract", default=os.path.join(ROOT, "runs/exp/contig/nj/_inst/ifa_ny.json.gz"))
    ap.add_argument("--spec", default=None)
    ap.add_argument("--lo", type=float, default=798.74, help="E2's lower mass bound (m_rel)")
    ap.add_argument("--hi", type=float, default=1148.19, help="E2's upper mass bound (m_rel)")
    ap.add_argument("--window", action="store_true",
                    help="band = [lo, hi] exactly, not intersected with the plan's τ band")
    ap.add_argument("--thin-floor", action="store_true",
                    help="each group's thin-unit land at most NECK_SHARE of its land")
    ap.add_argument("--time-limit", type=float, default=300.0)
    ap.add_argument("--nogood", nargs="*", default=[],
                    help="comma-separated unit sets no group may equal")
    a = ap.parse_args(argv)
    spec_path = a.spec or os.path.join(ROOT, f"runs/exp/contig/_specs/ifa_{a.state.lower()}_k{a.k}.toml")
    params = {k: v for k, v in vars(a).items() if k != "out"}
    output.check_out(a.out)
    contig.write_manifest(a.out, "coarse", spec_path, a.extract, params)
    s = tdspec.load(spec_path)
    ref = geo.read_reference()
    ext = tdspec.scope(s, data.conus(data.load(a.extract), ref))
    polygon = geo.polygon_graph()
    planning = contig.induced_graph(polygon, (a.state,))
    inst = tdspec.build(s, ext, ref, graph=planning)
    plans, reports = master.plan_all(inst)
    (c, p), = plans.items()
    ch = inst.channels[c]
    band = ((a.lo, a.hi) if a.window else
            (max(a.lo, ch.tau * (1 - p.delta)), min(a.hi, ch.tau * (1 + p.delta))))
    print(f"{c}: τ {ch.tau:.2f}, plan δ {p.delta}, band {band[0]:.2f}..{band[1]:.2f}")
    district = district_of(planning["vertices"], a.state, a.level)
    unit = assign_units(planning["vertices"], planning["edges"], district)
    border = contig.draw.border_km(planning)
    g = coarse_graph(unit, planning["edges"], border, ch.m)
    print(f"{len(set(district.values()))} {a.level} districts -> {len(g['units'])} units")
    land, thin = thin_units(unit, ch.m, polygon) if a.thin_floor else (None, None)
    part = partition(g, a.k, *band, time_limit=a.time_limit,
                     nogood=[x.split(",") for x in a.nogood], land=land, thin=thin)
    print({k: v for k, v in part.items() if k != "group"})
    if "group" not in part:
        contig.write_manifest(a.out, "coarse", spec_path, a.extract, params, status="failed",
                              stop_reason=f"partition: {part['status']}")
        return 2
    heavy = sorted(range(a.k), key=lambda h: -sum(g["mass"][u] for u, x in part["group"].items() if x == h))
    names = [cp.name for cp in p.copies]
    order = {h: i for i, h in enumerate(heavy)}
    owner = expand(unit, {u: order[h] for u, h in part["group"].items()}, names)
    res = Result(c, owner, [], set(), [], [], p.delta, "coarse", False)
    d = drawing(inst, p, res)
    report, m1 = contig.write_folder(a.out, s, inst, ext, ref, polygon, plans, reports, {c: d},
                                     f"{s.name} (coarse {a.level})", f"tools/exp/contig/coarse ({a.level})",
                                     os.path.basename(a.extract), False)
    groups = collections.defaultdict(list)
    for u, h in part["group"].items():
        groups[names[order[h]]].append(u)
    doc = {"state": a.state, "k": a.k, "level": a.level, "band": band,
           "districts": len(set(district.values())), "units": len(g["units"]),
           "partition": {k: v for k, v in part.items() if k != "group"},
           "thin": {u: land[u] for u in sorted(thin) if thin[u]} if thin else None,
           "groups": {j: {"units": sorted(us), "mass": sum(g["mass"][u] for u in us)}
                      for j, us in sorted(groups.items())},
           "m1": report["m1"], "verdict": report["verdict"]}
    with open(os.path.join(a.out, "coarse.json"), "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=2, sort_keys=True)
        fh.write("\n")
    contig.write_manifest(a.out, "coarse", spec_path, a.extract, params, status="done",
                          stop_reason="drawn", audit=report["verdict"], m1=m1.status)
    print(f"M1 {m1.status}: {m1.summary}; audit {report['verdict']}")
    return 0 if m1.status == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
