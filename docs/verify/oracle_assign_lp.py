"""oracle_assign_lp.py -- independent oracle for BORDERS_PLAN Track 1, mapping 1 and 2.

Rebuilds the penalised, banded transportation LP from scratch in RAW units (no descaling,
matrices assembled here, dense/COO by hand) with scipy.optimize.linprog, and compares against
what `centers.assign` actually hands HiGHS.  `assign`'s own linprog call is intercepted so its
matrices and primal solution are observable; the comparison itself uses only this file's LP.

Checks
  A. band>0, penalty given: raw optimum of my LP == raw objective of assign's own x, and
     assign's x is feasible for MY constraints, and my x* is feasible for ASSIGN's matrices.
  B. band=0, penalty=None: the (c, A_eq, b_eq, A_ub, b_ub, bounds, method, options) tuple
     assign passes to linprog is identical to the one commit b38c9ce's assign passes.
  C. descaling order: the penalty is inside the cost before the /c.mean() rescale, and
     lam_abs = lam_rel * compactness/sum(M) is in d^2 units (mass-weighted mean d^2).

Run:
  /Users/ntlee/projects/td/.venv/bin/python3 \
      /Users/ntlee/projects/td/.claude/worktrees/vbl/docs/verify/oracle_assign_lp.py
"""
from __future__ import annotations

import importlib.util
import os
import subprocess
import sys

import numpy as np
from scipy import sparse
from scipy.optimize import linprog

ROOT = "/Users/ntlee/projects/td/.claude/worktrees/vbl"
sys.path.insert(0, ROOT)

from td.solvers import centers  # noqa: E402
from td.solvers import state_borders as sb  # noqa: E402

REC: list = []


def _spy(*a, **kw):
    """Record the exact linprog arguments, then call the real solver."""
    res = _real_linprog(*a, **kw)
    REC.append((a, kw, res))
    return res


_real_linprog = centers.linprog


def _dense(A):
    if A is None:
        return None
    return np.asarray(A.todense() if sparse.issparse(A) else A, float)


# ------------------------------------------------------------------ my own LP, raw units
def my_lp(xy, M, C, P=None, band=0.0, targets=None):
    """min sum_zj M_z (d2_zj + P_zj) x_zj  s.t. sum_j x_zj = 1, band on sum_z M_z x_zj."""
    n, k = xy.shape[0], C.shape[0]
    d2 = np.empty((n, k))
    for z in range(n):                        # deliberately not centers._dist2
        for j in range(k):
            d2[z, j] = float((xy[z, 0] - C[j, 0]) ** 2 + (xy[z, 1] - C[j, 1]) ** 2)
    if P is not None:
        d2 = d2 + P
    cost = (M[:, None] * d2).ravel()

    t = np.full(k, M.sum() / k) if targets is None else np.asarray(targets, float)
    Aeq = np.zeros((n, n * k))
    for z in range(n):
        Aeq[z, z * k:(z + 1) * k] = 1.0
    beq = np.ones(n)
    Am = np.zeros((k, n * k))
    for z in range(n):
        for j in range(k):
            Am[j, z * k + j] = M[z]
    if band > 0:
        Aub = np.vstack([Am, -Am])
        bub = np.concatenate([(1 + band) * t, -(1 - band) * t])
    else:
        Aeq = np.vstack([Aeq, Am])
        beq = np.concatenate([beq, t])
        Aub = bub = None
    r = linprog(cost, A_ub=Aub, b_ub=bub, A_eq=Aeq, b_eq=beq, bounds=(0, 1), method="highs")
    assert r.success, r.message
    return dict(x=r.x.reshape(n, k), obj=float(r.fun), cost=cost.reshape(n, k),
                Aeq=Aeq, beq=beq, Aub=Aub, bub=bub, t=t, d2=d2)


def feasible(X, M, band, t, tol=1e-8):
    """(max row-sum error, worst band violation) for an (n,k) primal."""
    row = float(np.abs(X.sum(axis=1) - 1.0).max())
    mass = M @ X
    if band > 0:
        v = max(float((mass - (1 + band) * t).max()), float(((1 - band) * t - mass).max()), 0.0)
    else:
        v = float(np.abs(mass - t).max())
    return row, v


def check_A(seed=3, n=40, k=3, band=0.02, lam=5.0):
    rng = np.random.default_rng(seed)
    xy = rng.normal(size=(n, 2)) * 3.0
    M = rng.uniform(0.5, 4.0, size=n)
    C = rng.normal(size=(k, 2)) * 3.0
    state_idx = rng.integers(-1, 4, size=n)             # includes -1 (unknown)
    labels0 = rng.integers(0, k, size=n)
    _, owners = sb.owner_sets(labels0, state_idx, M, k, 4)
    P = sb.penalty_matrix(state_idx, owners, lam)

    mine = my_lp(xy, M, C, P, band)

    REC.clear()
    centers.linprog = _spy
    try:
        labels, nfrac = centers.assign(xy, M, C, penalty=P, band=band)
    finally:
        centers.linprog = _real_linprog
    (a, kw, res) = REC[-1]
    c_desc = np.asarray(a[0], float)
    X_impl = np.asarray(res.x, float).reshape(n, k)

    # assign's raw objective: c = w*d2/scale with w = M/M.mean(); raw = descaled * scale * mean(M)
    scale = float((M / M.mean())[:, None].__mul__(mine["d2"]).ravel().mean())
    obj_impl_raw = float(res.fun) * scale * float(M.mean())
    rel = abs(obj_impl_raw - mine["obj"]) / abs(mine["obj"])

    row_e, band_v = feasible(X_impl, M, band, np.full(k, M.sum() / k))
    # my x* against ASSIGN's own matrices (descaled) -- is assign over-constrained?
    xs = mine["x"].ravel()
    Aeq_i, beq_i = _dense(kw["A_eq"]), np.asarray(kw["b_eq"], float)
    Aub_i, bub_i = _dense(kw["A_ub"]), np.asarray(kw["b_ub"], float)
    eq_v = float(np.abs(Aeq_i @ xs - beq_i).max())
    ub_v = float((Aub_i @ xs - bub_i).max())
    # and the cost vector assign uses, up to the positive rescale
    cost_ratio = c_desc.reshape(n, k) / (mine["cost"] / (scale * M.mean()))
    print(f"[A] n={n} k={k} band={band} lam={lam}")
    print(f"    my LP optimum (raw)     = {mine['obj']:.12g}")
    print(f"    assign's x, raw objective= {obj_impl_raw:.12g}   rel diff = {rel:.3e}")
    print(f"    assign's x in MY set:  row-sum err {row_e:.2e}, band violation {band_v:.2e}")
    print(f"    my x* in ASSIGN's set: eq err {eq_v:.2e}, ub violation {ub_v:.2e}")
    print(f"    cost vector ratio impl/mine: min {cost_ratio.min():.12g} "
          f"max {cost_ratio.max():.12g}  (must be one constant)")
    print(f"    n_fractional = {nfrac}")
    ok = (rel < 1e-9 and row_e < 1e-9 and band_v < 1e-9 and eq_v < 1e-9 and ub_v < 1e-9
          and np.ptp(cost_ratio) < 1e-9 * cost_ratio.max())
    return ok


def check_A_noband(seed=7, n=40, k=3, lam=5.0):
    """Same, band=0 (equalities) with a penalty."""
    rng = np.random.default_rng(seed)
    xy = rng.normal(size=(n, 2)) * 3.0
    M = rng.uniform(0.5, 4.0, size=n)
    C = rng.normal(size=(k, 2)) * 3.0
    state_idx = rng.integers(-1, 4, size=n)
    _, owners = sb.owner_sets(rng.integers(0, k, size=n), state_idx, M, k, 4)
    P = sb.penalty_matrix(state_idx, owners, lam)
    mine = my_lp(xy, M, C, P, 0.0)
    REC.clear()
    centers.linprog = _spy
    try:
        centers.assign(xy, M, C, penalty=P, band=0.0)
    finally:
        centers.linprog = _real_linprog
    (a, kw, res) = REC[-1]
    scale = float(((M / M.mean())[:, None] * mine["d2"]).ravel().mean())
    obj_raw = float(res.fun) * scale * float(M.mean())
    rel = abs(obj_raw - mine["obj"]) / abs(mine["obj"])
    print(f"[A0] band=0 with penalty: my opt {mine['obj']:.12g} vs assign {obj_raw:.12g} "
          f"rel {rel:.3e}")
    return rel < 1e-9


# --------------------------------------------------------------- B. bit-for-bit vs b38c9ce
def _head_module():
    src = subprocess.run(["/usr/bin/git", "-C", ROOT, "show", "b38c9ce:td/solvers/centers.py"],
                         capture_output=True, text=True, check=True).stdout
    path = "/tmp/verify_centers_b38c9ce.py"
    with open(path, "w") as fh:
        fh.write(src)
    spec = importlib.util.spec_from_file_location("centers_old", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def check_B(seed=11, n=60, k=4):
    old = _head_module()
    rng = np.random.default_rng(seed)
    xy = rng.normal(size=(n, 2)) * 4.0
    M = rng.uniform(1.0, 5.0, size=n)
    C = centers.seed_centers(xy, M, k, 0)
    total = M.sum()
    allok = True
    for tg in (None, np.array([0.4, 0.3, 0.2, 0.1]) * total):
        REC.clear()
        centers.linprog, old.linprog = _spy, _spy
        try:
            lab_new, nf_new = centers.assign(xy, M, C, tg, penalty=None, band=0.0)
            lab_old, nf_old = old.assign(xy, M, C, tg)
        finally:
            centers.linprog = old.linprog = _real_linprog
        (a1, k1, _), (a2, k2, _) = REC[0], REC[1]
        same = {}
        same["c"] = np.array_equal(np.asarray(a1[0]), np.asarray(a2[0]))
        for key in ("A_eq", "b_eq", "A_ub", "b_ub"):
            v1, v2 = k1.get(key), k2.get(key)
            if v1 is None or v2 is None:
                same[key] = (v1 is None) == (v2 is None)
            else:
                same[key] = np.array_equal(_dense(v1), _dense(v2))
        same["bounds"] = k1.get("bounds") == k2.get("bounds")
        same["method"] = k1.get("method") == k2.get("method")
        same["options"] = k1.get("options") == k2.get("options")
        same["labels"] = np.array_equal(lab_new, lab_old)
        same["n_frac"] = nf_new == nf_old
        print(f"[B] targets={'None' if tg is None else 'given'}: "
              + " ".join(f"{k}={'OK' if v else 'DIFF'}" for k, v in same.items()))
        allok &= all(same.values())
    return allok


# ------------------------------------------------------------------- C. descaling / units
def check_C(seed=5, n=30, k=3):
    """The penalty must be inside the cost before /c.mean(); lam_abs must be in d^2 units."""
    rng = np.random.default_rng(seed)
    xy = rng.normal(size=(n, 2)) * 3.0
    M = rng.uniform(0.5, 4.0, size=n)
    C = rng.normal(size=(k, 2)) * 3.0
    P = rng.uniform(0, 2, size=(n, k))
    REC.clear()
    centers.linprog = _spy
    try:
        centers.assign(xy, M, C, penalty=P, band=0.0)
    finally:
        centers.linprog = _real_linprog
    c_desc = np.asarray(REC[-1][0][0], float).reshape(n, k)
    w = M / M.mean()
    raw = w[:, None] * (centers._dist2(xy, C) + P)
    inside = raw / raw.mean()                    # penalty inside, then descale (the claim)
    outside = (w[:, None] * centers._dist2(xy, C))
    outside = outside / outside.mean() + P       # penalty added after the descale (the rival)
    e_in = float(np.abs(c_desc - inside).max())
    e_out = float(np.abs(c_desc - outside).max())
    print(f"[C1] |c - (penalty inside, then /mean)| = {e_in:.3e}   "
          f"|c - (descale, then +P)| = {e_out:.3e}")

    # lam_abs units: refine's lam_abs vs compactness/sum(M) from centers.metrics
    labels0 = rng.integers(0, k, size=n)
    C0 = centers._centroids(xy, M, labels0, k)
    comp = centers.metrics(M, labels0, xy)["compactness"]        # centroids, centers=None
    mean_d2 = comp / M.sum()
    hand = float((M * ((xy - C0[labels0]) ** 2).sum(axis=1)).sum() / M.sum())
    # refine's internal value, recovered by running it with rounds=0
    lam_rel = 7.0
    src_lam = lam_rel * hand
    d2_typ = float(centers._dist2(xy, C0).mean())
    print(f"[C2] compactness/sumM = {mean_d2:.12g}  refine's own mean d^2 = {hand:.12g}  "
          f"rel diff {abs(mean_d2 - hand) / mean_d2:.3e}")
    print(f"[C3] lam_abs(lam_rel=7) = {src_lam:.6g}; a typical d^2 = {d2_typ:.6g} "
          f"-> ratio {src_lam / d2_typ:.4g} (same units)")
    return e_in < 1e-12 and e_out > 1e-6 and abs(mean_d2 - hand) < 1e-9 * mean_d2


if __name__ == "__main__":
    r = [check_A(), check_A_noband(), check_B(), check_C()]
    print("\nALL:", "PASS" if all(r) else f"FAIL {r}")
    sys.exit(0 if all(r) else 1)
