"""Data for the interactive step-through: geometry, the level-1 solve replayed, level-2 iterates.

Per-zip content kept to coordinates, state, district labels and a size class (quintile of M);
masses leave only as state aggregates in tau units.
"""
import csv
import json
import sys
import time
from pathlib import Path

import numpy as np

_REPO = Path(__file__).resolve().parents[2]     # the checkout this script lives in
sys.path.insert(0, str(_REPO / "tools"))
sys.path.insert(0, str(_REPO))
import borders_report  # noqa: E402
import state_splits as drv  # noqa: E402
from td import geo  # noqa: E402
from td.solvers import centers, state_splits as ss  # noqa: E402

ROOT = Path("/Users/ntlee/projects/td/battery/results/borders_k18_v2_20260907")
OUT = Path("/Users/ntlee/projects/td/battery/results/motion_page/steps.json")   # hub, gitignored
OUT.parent.mkdir(parents=True, exist_ok=True)
GEO = "/Users/ntlee/projects/td/data/geo"
DELTA, ETA = 0.05, 0.01

ctx = borders_report.load_committed("/Users/ntlee/projects/td/instance_descaled_v2.json.gz",
                                    str(ROOT.parent / "draw_k18_v2_20260904/k18/draw.csv"), GEO)
M_s, D, edges, tau, C0 = drv._state_masses_and_moments(ctx, GEO)
S, k = D.shape
known = ctx.state_idx >= 0

# ---- geometry: state polygons in LAEA, simplified; zips with coordinates
gdf = geo.states_outline(GEO)
polys = {}
geom = {}
for code, g in zip(gdf["STUSPS"], gdf.geometry):
    g = g.simplify(3000, preserve_topology=True)   # metres in LAEA
    geom[code] = g                                 # kept for the power-cell clip below
    parts = list(g.geoms) if g.geom_type == "MultiPolygon" else [g]
    largest = max(parts, key=lambda p: p.area)
    keep = [p for p in parts if p.area > 2e8 or p is largest]   # islets under 200 km^2 go, the
    polys[code] = [[[round(x / 1000, 1), round(y / 1000, 1)] for x, y in p.exterior.coords]
                   for p in keep]                                # largest part never does (DC)
xy_km = ctx.xy / 1000.0
q = np.quantile(ctx.M, [0.2, 0.4, 0.6, 0.8])
size_class = np.searchsorted(q, ctx.M).astype(int)
zips = dict(x=[round(float(v), 1) for v in xy_km[:, 0]], y=[round(float(v), 1) for v in xy_km[:, 1]],
            s=[int(v) for v in ctx.state_idx], c=[int(v) for v in size_class])

# ---- committed and the state aggregation
labels0 = ctx.labels0.astype(int)
mass_sd = np.zeros((S, k))
np.add.at(mass_sd, (ctx.state_idx[known], labels0[known]), ctx.M[known])
plurality = mass_sd.argmax(axis=1)
home = [int(h) for h in ctx.home]

# ---- level 1, replayed (the same program the run solved), then the pass
eps = ss.eps_lexicographic(M_s, D)
anchors = [(int(ctx.home[j]), j) for j in range(k) if ctx.home[j] >= 0]
prob = ss.build_milp(M_s, D, edges, tau, DELTA, eps, eta=ETA, anchors=anchors)
CACHE = OUT.with_name("steps_milp_cache.json")
if CACHE.exists():                      # the solve is deterministic; reuse it on a rebuild
    c = json.load(open(CACHE))
    res = dict(status=c["status"], splits=c["splits"], z=np.array(c["z"], bool), y=np.array(c["y"]),
               masses=np.array(c["masses"]))
    solve_s = c["solve_s"]
else:
    t0 = time.time()
    res = ss.solve(prob, time_limit=900, strict=False)
    solve_s = time.time() - t0
    json.dump(dict(status=str(res["status"]), splits=int(res["splits"]), z=res["z"].astype(int).tolist(),
                   y=res["y"].tolist(), masses=[float(v) for v in res["masses"]], solve_s=round(solve_s)),
              open(CACHE, "w"))
pas = ss.balance_pass(prob, res["z"])
print(f"milp: status={res['status']} splits={res['splits']} {solve_s:.0f}s; pass spread {pas['spread_rel']:.4f}",
      flush=True)

# ---- level 2 with iterates
xy_k, M_k, st_k = ctx.xy[known], ctx.M[known], ctx.state_idx[known]
real = ss.realise(xy_k, M_k, st_k, res["z"], pas["y"], C0, rounds=5)
known_idx = np.flatnonzero(known)
level2 = []
for s in real["split_states"]:
    st = real["states"][s]
    members = known_idx[st_k == s]
    level2.append(dict(
        state=ctx.state_list[s], zips=[int(i) for i in members], districts=st["districts"],
        cost=[float(c) for c in st["cost_rounds"]],
        iterates=[dict(labels=[int(v) for v in lab], centers=[[round(float(x) / 1000, 1), round(float(y) / 1000, 1)] for x, y in cen])
                  for lab, cen in st["iterates"]]))
labels_final = np.full(len(ctx.zips), -1, int)
labels_final[known] = real["labels"]

# ---- the cut inside each split state: the power diagram of that round's centres, clipped
# to the state.  The LP's duals beta make the boundary between i and j the line
# ||q - c_i||^2 - b_i = ||q - c_j||^2 - b_j, so the viewer sees the cut move as the centres do.
from shapely.geometry import Polygon                                          # noqa: E402

BIG = 8e6   # metres: larger than the LAEA extent of the lower 48


def _half_plane(a, b, near):
    """Polygon covering {q : a·q <= b} around `near`, big enough to clip any state.

    The box is built at the point of the line nearest `near`, not at the point nearest the
    origin: in LAEA metres `b/|a|` runs to 1e7 and a box hung there misses the state entirely.
    """
    n = float(np.hypot(*a))
    ah = np.asarray(a, float) / n
    d = np.array([-ah[1], ah[0]])
    p0 = ah * (b / n)
    p0 = p0 + float((np.asarray(near, float) - p0) @ d) * d      # slide along the line
    return Polygon([p0 + BIG * d, p0 - BIG * d, p0 - BIG * d - BIG * ah, p0 + BIG * d - BIG * ah])


def _cut_lines(code, cen, beta):
    """Boundaries between the power cells of `cen` (metres) inside state `code`, in km."""
    poly = geom.get(code)
    if poly is None or len(cen) < 2:
        return []
    near = np.array([poly.centroid.x, poly.centroid.y], float)
    cells = []
    for i, ci in enumerate(cen):
        cell = poly
        for j, cj in enumerate(cen):
            if i == j:
                continue
            # ||q-ci||^2 - bi <= ||q-cj||^2 - bj  <=>  2(cj-ci)·q <= |cj|^2 - |ci|^2 - bj + bi
            a = 2.0 * (np.asarray(cj) - np.asarray(ci))
            b = float(cj @ cj - ci @ ci - beta[j] + beta[i])
            cell = cell.intersection(_half_plane(a, b, near))
            if cell.is_empty:
                break
        cells.append(cell)
    out = []
    for i in range(len(cells)):
        for j in range(i + 1, len(cells)):
            if cells[i].is_empty or cells[j].is_empty:
                continue
            seg = cells[i].boundary.intersection(cells[j].boundary)
            if seg.is_empty:
                continue
            geoms = list(seg.geoms) if hasattr(seg, "geoms") else [seg]
            for gg in geoms:
                if gg.geom_type != "LineString" or gg.length < 1000:
                    continue
                out.append([[round(x / 1000, 1), round(y / 1000, 1)] for x, y in gg.coords])
    return out


for si, s in enumerate(real["split_states"]):
    st = real["states"][s]
    code = ctx.state_list[s]
    members = known_idx[st_k == s]
    xy_st, M_st = ctx.xy[members], ctx.M[members]
    js = list(st["districts"])
    tgt = np.array([pas["y"][s, j] for j in js], float)
    tgt = tgt / tgt.sum() * M_st.sum()
    for it, (lab, cen) in enumerate(st["iterates"]):
        cen = np.asarray(cen, float)
        try:
            beta = centers.power_weights(xy_st, M_st, cen, targets=tgt)["weights"]
        except Exception as exc:                     # a degenerate round must not lose the page
            print(f"  power_weights failed for {code} round {it}: {exc}", flush=True)
            level2[si]["iterates"][it]["cut"] = []
            continue
        level2[si]["iterates"][it]["cut"] = _cut_lines(code, cen, np.asarray(beta, float))
print("cut segments per state/round:",
      [(d["state"], [len(i["cut"]) for i in d["iterates"]]) for d in level2], flush=True)

# ---- the figures' palette, so the page and "The Five Percent Map" agree hue for hue
import us_maps                                                                # noqa: E402
XY_D = {z: (float(ctx.xy[i, 0]), float(ctx.xy[i, 1])) for i, z in enumerate(ctx.zips)}
VAL_D = {z: float(ctx.M[i]) for i, z in enumerate(ctx.zips)}


def _palette(lab):
    d = {z: f"D{lab[i] + 1:02d}" for i, z in enumerate(ctx.zips) if lab[i] >= 0}
    _, _, colors = us_maps.draw_palette(d, VAL_D, XY_D)
    return [colors.get(f"D{j + 1:02d}", "#8a8a8a") for j in range(k)]


palette_final, palette_committed = _palette(labels_final), _palette(labels0)

# ---- Track 1 iterates at delta 5%, lambda 100
t1 = []
zip_index = {z: i for i, z in enumerate(ctx.zips)}
for p in sorted((ROOT / "d0.05_lam100" / "iterates").glob("*.csv")):
    lab = np.full(len(ctx.zips), -1, int)
    for r in csv.DictReader(open(p)):
        i = zip_index.get(r["zip"])
        if i is not None:
            lab[i] = int(r["district"][1:]) - 1
    t1.append([int(v) for v in lab])

# owner sets per Track 1 iterate: which districts own each state at that round (item 3g)
from td.solvers import state_borders as sb                                    # noqa: E402
t1_owners = []
for lab in t1:
    la = np.array(lab)
    _, own = sb.owner_sets(la[known], ctx.state_idx[known], ctx.M[known], k, S)
    t1_owners.append([[int(j) for j in np.flatnonzero(own[s])] for s in range(S)])

# ---- metrics from the grids
row = list(csv.DictReader(open(ROOT / "track2_anchored/d0.05/grid.csv")))[-1]
row1 = {r["name"]: r for r in csv.DictReader(open(ROOT / "grid.csv"))}

data = dict(
    k=k, tau=tau, state_list=ctx.state_list, polys=polys, zips=zips,
    M_s_tau=[round(float(m / tau), 3) for m in M_s], edges=[[int(a), int(b)] for a, b in edges],
    home=home, plurality=[int(p) for p in plurality],
    committed_share=[[round(float(mass_sd[s, j] / M_s[s]), 3) if M_s[s] > 0 else 0 for j in range(k)] for s in range(S)],
    labels0=[int(v) for v in labels0],
    centres0=[[round(float(x) / 1000, 1), round(float(y) / 1000, 1)] for x, y in C0],
    milp=dict(status=str(res["status"]), splits=int(res["splits"]), solve_s=round(solve_s),
              z=res["z"].astype(int).tolist(), y=[[round(float(v), 4) for v in r] for r in res["y"]],
              masses=[round(float(v) / tau, 4) for v in res["masses"]]),
    balance=dict(y=[[round(float(v), 4) for v in r] for r in pas["y"]],
                 masses=[round(float(v) / tau, 4) for v in pas["masses"]],
                 spread=float(pas["spread_rel"]), max_dev=float(pas["max_dev_rel"])),
    level2=level2, labels_final=[int(v) for v in labels_final],
    n_placed=int((~known).sum()) + len(ctx.missing),
    final=dict(spread=float(row["spread_rel"]), max_dev=float(row["max_dev_rel"]), gap=float(row["gap"]),
               stage2=float(row["stage2_value"]), zips_changed=int(row["zips_changed"]), n_fractional=int(row["n_fractional"])),
    committed=dict(spread=float(row1["committed"]["spread_rel"]), gap=float(row1["committed"]["gap"]),
                   stage2=float(row1["committed"]["stage2_value"])),
    palette=palette_final, palette_committed=palette_committed,
    track1=dict(iterates=t1, owners=t1_owners, spread=float(row1["d0.05_lam100"]["spread_rel"]),
                outside=float(row1["d0.05_lam100"]["outside_owner_share"]),
                split_states=row1["d0.05_lam100"]["states_split"]),
)
OUT.write_text(json.dumps(data, separators=(",", ":")))
print(f"wrote {OUT} ({OUT.stat().st_size / 1e6:.2f} MB); level-2 rounds "
      f"{[(d['state'], len(d['iterates']) - 1) for d in level2]}; track1 iterates {len(t1)}", flush=True)
