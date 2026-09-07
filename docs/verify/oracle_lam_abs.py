"""oracle_lam_abs.py -- BORDERS_PLAN Track 1, mapping 2 on the REAL instance.

The driver writes `lam_abs = lam_rel * compactness0 / sum(M)` into params.json but never passes
it; `state_borders.refine` recomputes its own from `labels0`.  This checks the two agree
exactly on the real k=18 committed draw, and that the value is a mass-weighted mean d^2 (i.e.
in the same units as the d^2 the LP adds it to), by recomputing the mean d^2 here from the raw
coordinates without calling `centers.metrics`.

Run:
  /Users/ntlee/projects/td/.venv/bin/python3 \
      /Users/ntlee/projects/td/.claude/worktrees/vbl/docs/verify/oracle_lam_abs.py
"""
from __future__ import annotations

import json
import sys

import numpy as np

ROOT = "/Users/ntlee/projects/td/.claude/worktrees/vbl"
sys.path.insert(0, ROOT)
sys.path.insert(0, ROOT + "/tools")

import borders_report  # noqa: E402
from td.solvers import centers  # noqa: E402

RES = "/Users/ntlee/projects/td/battery/results/borders_k18_v2_20260907"
ctx = borders_report.load_committed(
    "/Users/ntlee/projects/td/instance_descaled_v2.json.gz",
    "/Users/ntlee/projects/td/battery/results/draw_k18_v2_20260904/k18/draw.csv",
    "/Users/ntlee/projects/td/data/geo")

# the driver's formula
comp0 = centers.metrics(ctx.M, ctx.labels0, ctx.xy)["compactness"]
driver = 100.0 * comp0 / ctx.M.sum()

# refine's internal formula, transcribed
C = centers._centroids(ctx.xy, ctx.M, ctx.labels0, ctx.k)
refine_lam = 100.0 * float((ctx.M * ((ctx.xy - C[ctx.labels0]) ** 2).sum(axis=1)).sum()
                           / ctx.M.sum())

# my own, from scratch: mass-weighted mean squared distance to the district centroid
cen = np.zeros((ctx.k, 2))
for j in range(ctx.k):
    sel = ctx.labels0 == j
    cen[j] = (ctx.M[sel, None] * ctx.xy[sel]).sum(axis=0) / ctx.M[sel].sum()
num = sum(float(ctx.M[i]) * float(((ctx.xy[i] - cen[ctx.labels0[i]]) ** 2).sum())
          for i in range(len(ctx.M)))
mine = 100.0 * num / float(ctx.M.sum())

recorded = json.load(open(f"{RES}/params.json"))["lam_abs"]["100.0"]
d2 = centers._dist2(ctx.xy, C)
print(f"driver   lam_abs(100) = {driver:.12g}")
print(f"refine   lam_abs(100) = {refine_lam:.12g}   rel {abs(driver-refine_lam)/driver:.3e}")
print(f"mine     lam_abs(100) = {mine:.12g}         rel {abs(driver-mine)/driver:.3e}")
print(f"params.json recorded  = {recorded:.12g}     rel {abs(driver-recorded)/driver:.3e}")
print(f"lam_abs/100 = {driver/100:.6g}; median d^2(z, own centre) = "
      f"{np.median(d2[np.arange(len(ctx.M)), ctx.labels0]):.6g}; "
      f"mean over all (z,j) = {d2.mean():.6g}  -- same order, same units")
ok = (abs(driver - refine_lam) < 1e-9 * driver and abs(driver - mine) < 1e-9 * driver
      and abs(driver - recorded) < 1e-9 * driver)
print("\nALL:", "PASS" if ok else "FAIL")
sys.exit(0 if ok else 1)
