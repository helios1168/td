"""oracle_power_penalty.py -- BORDERS_PLAN "Files": the `penalty=` additions to
`centers.power_labels` and `centers.power_weights`, which the plan asks for but Track 1 never
calls (no production caller; `power_weights(penalty=)` has no unit test).

Oracles, both independent of the implementation:
  * `power_labels(..., penalty=P)` == a plain-Python argmin over d^2 + P - w.
  * `power_weights(..., penalty=P)`: the returned duals are feasible for the PENALISED
    transportation dual (alpha_z + M_z beta_j <= M_z (d^2 + P)_zj) and `lp_bound` lies below the
    penalised cost of 20,000 random integer assignments that meet the targets exactly, plus the
    penalised cost of the LP's own labelling; and `labels` is the penalised power diagram.

Run:
  /Users/ntlee/projects/td/.venv/bin/python3 \
      /Users/ntlee/projects/td/.claude/worktrees/vbl/docs/verify/oracle_power_penalty.py
"""
from __future__ import annotations

import itertools
import sys

import numpy as np

ROOT = "/Users/ntlee/projects/td/.claude/worktrees/vbl"
sys.path.insert(0, ROOT)

from td.solvers import centers  # noqa: E402


def main():
    ok = True
    rng = np.random.default_rng(2)

    # --- power_labels
    n, k = 60, 4
    xy = rng.normal(size=(n, 2)) * 3
    C = rng.normal(size=(k, 2)) * 3
    w = rng.normal(size=k)
    P = rng.uniform(0, 5, size=(n, k))
    got = centers.power_labels(xy, C, w, P)
    want = []
    for z in range(n):
        vals = [float(((xy[z] - C[j]) ** 2).sum()) + float(P[z, j]) - float(w[j])
                for j in range(k)]
        want.append(int(np.argmin(vals)))
    lab_ok = got.tolist() == want
    print(f"[power_labels] penalised argmin matches a plain-Python argmin: {lab_ok}")
    ok &= lab_ok

    # --- power_weights on a small equal-mass instance, so integer assignments are enumerable
    n, k = 12, 3
    xy = rng.normal(size=(n, 2)) * 2
    M = np.ones(n)
    C = rng.normal(size=(k, 2)) * 2
    P = np.where(rng.random((n, k)) < 0.4, 4.0, 0.0)
    res = centers.power_weights(xy, M, C, penalty=P)

    d2 = np.empty((n, k))
    for z in range(n):
        for j in range(k):
            d2[z, j] = float(((xy[z] - C[j]) ** 2).sum())
    cost = M[:, None] * (d2 + P)

    # brute force: every balanced integer assignment (4 zips per district)
    best = np.inf
    per = n // k
    idx = list(range(n))
    for a in itertools.combinations(idx, per):
        rest = [z for z in idx if z not in a]
        for b in itertools.combinations(rest, per):
            c = [z for z in rest if z not in b]
            v = cost[list(a), 0].sum() + cost[list(b), 1].sum() + cost[c, 2].sum()
            best = min(best, float(v))
    bound = res["lp_bound"]
    print(f"[power_weights] lp_bound = {bound:.12g}; brute-force integer optimum = {best:.12g}")
    print(f"                bound <= optimum: {bound <= best + 1e-9}; "
          f"gap = {best - bound:.3e} (LP is integral here iff 0)")
    ok &= bound <= best + 1e-9

    # dual feasibility in the caller's units, checked here rather than trusting max_dual_violation
    alpha, beta = res["alpha"], res["beta"]
    mscale = float(M.mean())
    scale = float((M / mscale)[:, None].__mul__(d2 + P).mean())
    slack = cost / (scale * mscale) - (alpha[:, None] + (M / mscale)[:, None] * beta[None, :])
    print(f"                min dual slack (descaled) = {slack.min():.3e} (want >= -1e-9); "
          f"reported max_dual_violation_rel = {res['max_dual_violation_rel']:.3e}")
    ok &= slack.min() >= -1e-9

    lab_pw = centers.power_labels(xy, C, res["weights_raw"], P)
    same = np.array_equal(res["labels"], lab_pw)
    print(f"                returned labels are the PENALISED power diagram: {same}")
    ok &= same
    unpen = centers.power_labels(xy, C, res["weights_raw"])
    print(f"                (unpenalised diagram differs on "
          f"{int((unpen != res['labels']).sum())} zips -- the penalty is really carried)")

    print("\nALL:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
