"""Data for the interactive step-through: geometry, the level-1 solve replayed, level-2 iterates.

Per-zip content kept to coordinates, state, district labels and a size class (quintile of M);
masses leave only as state aggregates in tau units.
"""
import csv
import json
import os
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
# battery/results, data/geo and the descaled instance are gitignored and hub-only
# (CLAUDE.md); a worktree carries none, so TD_DATA_ROOT points a run there at the hub's copy.
DATA_ROOT = Path(os.environ.get("TD_DATA_ROOT", REPO))
# borders_report and this state_splits driver, at the time this script was written, existed
# only on the vbl worktree; TD_VBL_ROOT overrides if that worktree moves or is recreated
# elsewhere. The default assumes the hub sits at TD_REPO (or ~/projects/td) with vbl beside it.
HUB = Path(os.environ.get("TD_REPO", Path.home() / "projects" / "td"))
VBL = Path(os.environ.get("TD_VBL_ROOT", HUB / ".claude" / "worktrees" / "vbl"))

sys.path.insert(0, str(VBL / "tools"))
sys.path.insert(0, str(VBL))
import borders_report  # noqa: E402
import state_splits as drv  # noqa: E402
from td import geo  # noqa: E402
from td.solvers import centers, state_splits as ss  # noqa: E402

ROOT = DATA_ROOT / "battery" / "results" / "borders_k18_v2_20260907"
OUT = DATA_ROOT / "battery" / "results" / "motion_page" / "steps.json"   # hub, gitignored
OUT.parent.mkdir(parents=True, exist_ok=True)
GEO = str(DATA_ROOT / "data" / "geo")
DELTA, ETA = 0.05, 0.01

ctx = borders_report.load_committed(str(DATA_ROOT / "instance_descaled_v2.json.gz"),
                                    str(ROOT.parent / "draw_k18_v2_20260904/k18/draw.csv"), GEO)
M_s, D, edges, tau, C0 = drv._state_masses_and_moments(ctx, GEO)
S, k = D.shape
known = ctx.state_idx >= 0

# ---- geometry: state polygons in LAEA, simplified; zips with coordinates
gdf = geo.states_outline(GEO)
polys = {}
for code, g in zip(gdf["STUSPS"], gdf.geometry):
    g = g.simplify(3000, preserve_topology=True)   # metres in LAEA
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
    track1=dict(iterates=t1, spread=float(row1["d0.05_lam100"]["spread_rel"]),
                outside=float(row1["d0.05_lam100"]["outside_owner_share"]),
                split_states=row1["d0.05_lam100"]["states_split"]),
)
OUT.write_text(json.dumps(data, separators=(",", ":")))
print(f"wrote {OUT} ({OUT.stat().st_size / 1e6:.2f} MB); level-2 rounds "
      f"{[(d['state'], len(d['iterates']) - 1) for d in level2]}; track1 iterates {len(t1)}", flush=True)
