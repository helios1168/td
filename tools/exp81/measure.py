"""measure.py -- the #81 measurements of one run directory (experimental, td#81).

    "$TD_PY" tools/exp81/measure.py <run_dir> --out <json>

A run directory has the layout `python -m td run` writes: `ledger.csv`, `districts.csv`,
`run.json`, `solver.json`, optionally the Hess arm's `hess_solver.json`.  Every measure is read
from the ledger (`docs/MODEL.md` §8), never from planned shares, so both objective families are
measured on the same drawn plan.  The instance (units, unit centroids, final bands, the declared
ZIP graph, the support master's size) is rebuilt from the run's spec on the extract, with the
two in-memory caveats of the 2026-10-01 looks driver (`runs/sweep/looks_2026-10-01/run3.py`): the
rounding margin is 0 and every cell below 1e-6 m_rel (ZIP 13027's FI cell) is zeroed at load.

Per channel c, with K_c districts j, drawn mass m_j = Σ of the ledger's m_rel over j's cells and
τ = (the channel's ledger total) / K_c:
- **balance**: deviation m_j / τ − 1; compliance is the audit's `check_bands`, m_j inside the
  channel's final band τ_c(1 ± final_delta) with slack `audit.BAND_SLACK` τ; worst = max |dev|;
- **support-diameter score** Σ_j w(S_j), S_j the units where j holds positive m_rel, w the
  master's `supports.diameter` (largest distance between land-weighted unit centroids, km; §3.5).
  This is Σ_S w_S n_S on the drawn plan's induced supports.  `planned` is the same sum over the
  `support` column of `districts.csv` (the master's objective for arm 1);
- **Hess score** Σ_j Σ_{z∈j} M_z ‖p_z − c_j‖², M_z the ZIP's m_rel in c, p_z its 2025 gazetteer
  point in EPSG:5070 (the reference table's x, y, the realizer's coordinates) in km, c_j the
  M-weighted centroid of j's ZIPs; unit m_rel·km².  Per district also `rms_km`, √(score_j / m_j);
- **extent**: the largest distance between two ZIP points j holds (any mass), km; max over j;
- **contacts** Σ_j |S_j| and **split units**, units with two or more districts of positive mass;
- **contiguity**: the audit's `check_contiguity` on the declared graph's explicit vertices,
  pieces = components of j's ZIPs beyond the heaviest; `pieces_bridged`, a lower bound, counts the
  same with every vertex that has no cell in c passable by any district (the pieces the run labels
  "connector ZIP not in ledger" disappear);
- **solver**: `solver.json`'s report per channel as written, `hess_solver.json` likewise when
  present, and the support master's size for the run's spec (`master.build`, before presolve).

Nothing is normalised across objectives: each score is in its own unit.
"""
from __future__ import annotations

import argparse
import collections
import csv
import json
import math
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from td import audit, data, geo, master, output, supports      # noqa: E402
from td import spec as tdspec                                   # noqa: E402

HUB = os.environ.get("TD_REPO", ROOT)
ZERO_BELOW = 1e-6               # run3.py:84: cells below this m_rel are zeroed at load


def load_extract(path: str):
    """The extract as the looks driver loads it: cells below `ZERO_BELOW` set to 0."""
    e = data.load(path)
    e.m_rel = [0.0 if m < ZERO_BELOW else m for m in e.m_rel]
    return e


def instance(spec_path: str, extract_path: str, public: str):
    """(spec, instance, declared graph, reference) as `output.run` builds them."""
    supports.margin = lambda *a, **k: 0.0           # run3.py:5, the margin off
    s = tdspec.load(spec_path)
    ref = geo.read_reference()
    ext = tdspec.scope(s, data.conus(load_extract(extract_path), ref))
    graph = output.declared_graph(ext, ref, public)
    return s, tdspec.build(s, ext, ref, graph), graph, ref


def extent_km(points: list) -> float:
    """The largest distance between two of `points` (km), over their convex hull."""
    if len(points) < 2:
        return 0.0
    import numpy as np
    pts = np.unique(np.asarray(points, dtype=float), axis=0)
    if len(pts) > 3:
        from scipy.spatial import ConvexHull, QhullError
        try:
            pts = pts[ConvexHull(pts).vertices]
        except QhullError:          # collinear points: the brute force below is exact
            pass
    d = pts[:, None, :] - pts[None, :, :]
    return float(np.sqrt((d ** 2).sum(-1)).max())


def components(zips, adj: dict) -> list:
    """Components of the graph `adj` induced on `zips`, as sets."""
    inside, seen, out = set(zips), set(), []
    for z in sorted(inside):
        if z in seen:
            continue
        comp, stack = set(), [z]
        seen.add(z)
        while stack:
            a = stack.pop()
            comp.add(a)
            for b in adj.get(a, ()):
                if b in inside and b not in seen:
                    seen.add(b)
                    stack.append(b)
        out.append(comp)
    return out


def model_size(inst, channel: str) -> dict:
    m = master.build(inst, channel)
    return {"supports": len(m.supports), "columns": len(m.cost),
            "integer_columns": sum(m.integer), "rows": len(m.rows),
            "nonzeros": sum(1 for r in m.rows for a in r.coef.values() if a != 0.0)}


def _read_json(path: str):
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def measure_channel(inst, c: str, rows: list, xy: dict, adj: dict, districts_csv: list) -> dict:
    ch = inst.channels[c]
    unit_of = inst.units.unit_of
    cells = [r for r in rows if r["model_channel"] == c]
    held: dict = collections.defaultdict(collections.Counter)     # district -> zip -> m_rel
    for r in cells:
        if r["district"]:
            held[r["district"]][r["zip_code"]] += r["m_rel"]
    total = math.fsum(r["m_rel"] for r in cells)
    tau = total / ch.k
    lo, hi = ch.final_band
    slack = audit.BAND_SLACK * tau
    free = set(adj) - {r["zip_code"] for r in cells}     # passable for `pieces_bridged`

    out_d, owners = [], collections.defaultdict(list)
    for j in sorted(held):
        zm = held[j]
        mass = math.fsum(zm.values())
        pts = {z: (xy[z][0] / 1000.0, xy[z][1] / 1000.0) for z in zm}
        w = mass if mass > 0 else float(len(zm))
        wt = (lambda z: zm[z]) if mass > 0 else (lambda z: 1.0)
        cx = math.fsum(wt(z) * pts[z][0] for z in zm) / w
        cy = math.fsum(wt(z) * pts[z][1] for z in zm) / w
        sse = math.fsum(zm[z] * ((pts[z][0] - cx) ** 2 + (pts[z][1] - cy) ** 2) for z in zm)
        units = collections.Counter()
        for z, m in zm.items():
            units[unit_of[z]] += m
        support = sorted(u for u, m in units.items() if m > 0)
        for u in support:
            owners[u].append(j)
        on_graph = [z for z in zm if z in adj]
        comps = sorted(components(on_graph, adj), key=lambda s: (-math.fsum(zm[z] for z in s), min(s)))
        comps_b = [s & set(zm) for s in components(set(on_graph) | free, adj)]
        comps_b = [s for s in comps_b if s]
        out_d.append({
            "district": j, "mass": mass, "deviation": mass / tau - 1.0,
            "within_final_band": lo - slack <= mass <= hi + slack,
            "support": support, "units": len(support),
            "unit_mass": {u: units[u] for u in support},
            "support_diameter_km": supports.diameter(inst, support),
            "hess_m_rel_km2": sse, "rms_km": math.sqrt(sse / mass) if mass > 0 else 0.0,
            "centroid_km": [cx, cy], "extent_km": extent_km(list(pts.values())),
            "zips": len(zm), "zips_off_graph": len(zm) - len(on_graph),
            "pieces": len(comps) - 1, "pieces_bridged": len(comps_b) - 1,
            "piece_masses": [math.fsum(zm[z] for z in s) / mass if mass > 0 else 0.0
                             for s in comps[1:]],
        })
    planned = None
    rows_c = [r for r in districts_csv if r["channel"] == c]
    if rows_c and all(r.get("support") for r in rows_c):
        planned = math.fsum(supports.diameter(inst, r["support"].split("+")) for r in rows_c)
    by_csv = {r["district"]: r for r in rows_c}
    checks = []
    for d in out_d:
        r = by_csv.get(d["district"])
        if r is None:
            checks.append(f"{d['district']}: not in districts.csv")
            continue
        if r.get("drawn_mass") and abs(float(r["drawn_mass"]) - d["mass"]) > 1e-6 * max(1.0, d["mass"]):
            checks.append(f"{d['district']}: drawn mass {d['mass']:.9g} against districts.csv "
                          f"{r['drawn_mass']}")
        if r.get("pieces") not in (None, "") and int(r["pieces"]) != d["pieces"]:
            checks.append(f"{d['district']}: {d['pieces']} pieces against districts.csv {r['pieces']}")
    split = {u: js for u, js in sorted(owners.items()) if len(js) > 1}
    devs = [d["deviation"] for d in out_d]
    return {
        "k": ch.k, "districts": len(out_d), "tau_m_rel": tau, "total_m_rel": total,
        "final_band": [lo, hi], "final_delta": ch.spec.final_delta,
        "within_final_band": sum(d["within_final_band"] for d in out_d),
        "worst_deviation": max(map(abs, devs)) if devs else None,
        "deviation_range": [min(devs), max(devs)] if devs else None,
        "unassigned_cells": sum(1 for r in cells if not r["district"]),
        "support_diameter_drawn_km": math.fsum(d["support_diameter_km"] for d in out_d),
        "support_diameter_planned_km": planned,
        "hess_m_rel_km2": math.fsum(d["hess_m_rel_km2"] for d in out_d),
        "max_rms_km": max(d["rms_km"] for d in out_d),
        "max_extent_km": max(d["extent_km"] for d in out_d),
        "max_support_diameter_km": max(d["support_diameter_km"] for d in out_d),
        "contacts": sum(d["units"] for d in out_d),
        "max_units_per_district": max(d["units"] for d in out_d),
        "split_units": len(split), "split": split,
        "districts_in_pieces": sum(d["pieces"] > 0 for d in out_d),
        "pieces": sum(d["pieces"] for d in out_d),
        "districts_in_pieces_bridged": sum(d["pieces_bridged"] > 0 for d in out_d),
        "pieces_bridged": sum(d["pieces_bridged"] for d in out_d),
        "zips_off_graph": sum(d["zips_off_graph"] for d in out_d),
        "cross_checks": checks,
        "district_rows": out_d,
    }


def measure(run_dir: str, spec_path: str | None = None, extract_path: str | None = None,
            public: str | None = None, sizes: bool = True) -> dict:
    run = _read_json(os.path.join(run_dir, "run.json")) or {}
    spec_path = spec_path or os.path.join(HUB, run["spec"])
    extract_path = extract_path or os.path.join(HUB, run.get("source") or "instance_descaled.json.gz")
    public = public or os.path.join(HUB, "data", "public")
    s, inst, graph, ref = instance(spec_path, extract_path, public)
    rows = output.read_ledger(os.path.join(run_dir, "ledger.csv"))
    with open(os.path.join(run_dir, "districts.csv"), encoding="utf-8", newline="") as fh:
        districts_csv = list(csv.DictReader(fh))
    zs = {r["zip_code"] for r in rows if r["district"]}
    r2 = ref.set_index("zcta").loc[sorted(zs)]
    xy = dict(zip(r2.index, zip(r2["x"].astype(float), r2["y"].astype(float))))
    vertices = set(graph["vertices"])
    adj: dict = {z: set() for z in vertices}
    for a, b, *_ in graph["edges"]:
        if a in vertices and b in vertices and a != b:
            adj[a].add(b)
            adj[b].add(a)
    solver = _read_json(os.path.join(run_dir, "solver.json")) or {}
    hess = _read_json(os.path.join(run_dir, "hess_solver.json"))
    out = {"run_dir": os.path.abspath(run_dir), "scenario": run.get("scenario", s.name),
           "spec": spec_path, "extract": os.path.basename(extract_path),
           "verdict": run.get("verdict"), "coordinates": "EPSG:5070 gazetteer points, km",
           "channels": {}}
    for c in inst.channels:
        m = measure_channel(inst, c, rows, xy, adj, districts_csv)
        m["solver"] = solver.get(c, {}).get("solver", solver.get(c))
        if hess is not None:
            m["hess_solver"] = hess.get(c, hess) if isinstance(hess, dict) else hess
        m["run_json"] = {k: v for k, v in (run.get("channels", {}).get(c) or {}).items()}
        if sizes:
            m["support_master_size"] = model_size(inst, c)
        out["channels"][c] = m
    return out


SUMMARY = (("within_final_band", "within final band"), ("worst_deviation", "worst deviation"),
           ("support_diameter_drawn_km", "support diameter, drawn (km)"),
           ("support_diameter_planned_km", "support diameter, planned (km)"),
           ("hess_m_rel_km2", "Hess (m_rel·km²)"), ("max_rms_km", "max district rms (km)"),
           ("max_extent_km", "max extent (km)"),
           ("contacts", "contacts"), ("split_units", "split units"),
           ("districts_in_pieces", "districts in pieces"), ("pieces", "pieces"),
           ("pieces_bridged", "pieces, connectors bridged"))


def summary(res: dict) -> str:
    chans = list(res["channels"])
    lines = ["| measure | " + " | ".join(chans) + " |", "|---|" + "---|" * len(chans)]
    for key, label in SUMMARY:
        cells = []
        for c in chans:
            v = res["channels"][c][key]
            cells.append("—" if v is None else f"{v:.4g}" if isinstance(v, float) else str(v))
        lines.append(f"| {label} | " + " | ".join(cells) + " |")
    return "\n".join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("run_dir")
    ap.add_argument("--out", required=True, help="the JSON file to write")
    ap.add_argument("--spec", help="the scenario TOML (default: run.json's spec under $TD_REPO)")
    ap.add_argument("--extract", help="the extract (default: run.json's source under $TD_REPO)")
    ap.add_argument("--public", help="the 2025 downloads (default: $TD_REPO/data/public)")
    ap.add_argument("--no-sizes", action="store_true", help="skip the support master's size")
    a = ap.parse_args(argv)
    res = measure(a.run_dir, a.spec, a.extract, a.public, not a.no_sizes)
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=1, sort_keys=True)
        fh.write("\n")
    print(summary(res))
    for c, m in res["channels"].items():
        for line in m["cross_checks"]:
            print(f"cross-check {c}: {line}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
