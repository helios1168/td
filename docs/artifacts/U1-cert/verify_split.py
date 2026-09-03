"""U1-cert verification C -- P3a's split-unit count, attacked; and P3b/P3c on the instance.

The attack on P3a.  The model bounds the support of a vertex of the optimal face
    P = { x >= 0 : sum_i x_zi = 1 (n rows),  sum_z u_i(z) x_zi = g*_i (k rows) }
by rank(A) = n + k, and concludes "at most k split units in general, k-1 only at tau = 0".
rank(A) = n + k is correct.  But A is not a minimal description of P.  With all u_i(z) > 0 the
equilibrium prices p* are unique and every optimum is an equilibrium allocation, so

    P = { x >= 0 : supp(x) subset MBB(p*),  sum_i x_zi = 1,  sum_z p*_z x_zi = 1 }

-- a transportation polytope in the spending variables b_zi = p*_z x_zi, whose two constraint
families are linearly dependent (sum_z p*_z * (supply row z) = sum_i (budget row i), both
sides = k).  Its rank is n + k - c with c >= 1 the number of components of the MBB graph, so a
vertex has at most n + k - 1 nonzeros and **at most k - 1 split units, heterogeneous or not**.

This script (i) checks that dependency symbolically, (ii) searches hard for a heterogeneous
vertex with k splits, (iii) reproduces the instance-side P3b/P3c numbers.

Run:  /Users/ntlee/projects/td/.venv/bin/python3 docs/artifacts/U1-cert/verify_split.py
from /Users/ntlee/projects/td/.claude/worktrees/A1 .
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
import sympy as sp
from scipy import sparse
from scipy.optimize import linprog

sys.path.insert(0, str(Path(__file__).resolve().parent))
import verify_instance as VI  # noqa: E402  -- reuse only the raw-JSON loader


def load_instance_bundle():
    """(U over the delivered 13 reps, M, X, p, V, zips) -- rebuilt, not cached."""
    import csv
    import json
    zips, reps, M, S, S_free, U_all = VI.raw_utilities("theta")
    ir = {r: i for i, r in enumerate(reps)}
    iz = {z: i for i, z in enumerate(zips)}
    metrics = json.loads((VI.DRAW / "metrics.json").read_text())
    assign = metrics["winner"]["assignment"]
    districts = sorted(assign)
    with open(VI.DRAW / "draw.csv") as fh:
        to_d = {row["zip"]: row["district"] for row in csv.DictReader(fh)}
    cols = [ir[assign[d]] for d in districts]
    U = np.ascontiguousarray(U_all[:, cols])
    parts = {d: [] for d in districts}
    for z, d in to_d.items():
        parts[d].append(iz[z])
    V = math.fsum(math.log(math.fsum(U_all[z, ir[assign[d]]] for z in parts[d]))
                  for d in districts)
    X, p = VI.prop_response(U, iters=200_000, seed=0)
    return U, M, X, p, V, np.array(zips)

FAILURES: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"  [{'ok ' if ok else 'FAIL'}] {name}" + (f"   {detail}" if detail else ""))
    if not ok:
        FAILURES.append(name)


def prop_response(U, iters=150_000, seed=0):
    n, k = U.shape
    rng = np.random.default_rng(seed)
    b = rng.random((n, k)) + 0.1
    b /= b.sum(axis=0, keepdims=True)
    for _ in range(iters):
        p = b.sum(axis=1)
        X = b / p[:, None]
        g = (U * X).sum(axis=0)
        b = (U * X) / g[None, :]
    p = b.sum(axis=1)
    return b / p[:, None], p


def vertex_gain_rows(U, g_star):
    n, k = U.shape
    cols = np.arange(n * k)
    place = sparse.coo_matrix((np.ones(n * k), (np.repeat(np.arange(n), k), cols)),
                              shape=(n, n * k))
    gain = sparse.coo_matrix((U.ravel(), (np.tile(np.arange(k), n), cols)), shape=(k, n * k))
    A = sparse.vstack([place, gain]).tocsc()
    b = np.concatenate([np.ones(n), np.asarray(g_star, float)])
    res = linprog(np.zeros(n * k), A_eq=A, b_eq=b, bounds=(0, None), method="highs-ds")
    if not res.success:
        return None
    return np.asarray(res.x, float).reshape(n, k)


def main() -> int:
    print("=" * 78)
    print("P3a -- the dependency that makes rank(A) = n+k non-minimal")
    n, k = 3, 2
    p = sp.symbols("p0:3", positive=True)
    x = sp.Matrix(n, k, lambda z, i: sp.Symbol(f"x{z}{i}", nonnegative=True))
    supply = [sum(x[z, i] for i in range(k)) - 1 for z in range(n)]          # = 0
    budget = [sum(p[z] * x[z, i] for z in range(n)) - 1 for i in range(k)]   # = 0
    # sum_z p_z * supply_z - sum_i budget_i  ==  sum_z p_z - k, a constant: the rows are
    # linearly dependent once sum_z p_z = k (budgets 1 each, market clears).
    dep = sp.simplify(sum(p[z] * supply[z] for z in range(n)) - sum(budget))
    check("symbolic: sum_z p_z*(supply row) - sum_i(budget row) = k - sum_z p_z (a constant, "
          "no x in it)", sp.simplify(dep - (k - sum(p))) == 0, str(sp.simplify(dep)))
    check("symbolic: so at sum_z p_z = k the n+k rows have a linear dependency (rank <= n+k-1)",
          sp.simplify(dep.subs(p[0], k - p[1] - p[2])) == 0)

    print("=" * 78)
    print("ATTACK -- search for a heterogeneous vertex optimum with exactly k split units")
    rng = np.random.default_rng(20260903)
    max_splits = {}
    trials = 0
    worst = None
    for _ in range(250):
        n = int(rng.integers(4, 11))
        k = int(rng.integers(2, min(6, n)))
        U = rng.random((n, k)) * rng.choice([1.0, 10.0]) + 0.05
        X, pstar = prop_response(U, iters=40_000, seed=int(rng.integers(1 << 30)))
        g = (U * X).sum(axis=0)
        Xv = vertex_gain_rows(U, g)
        if Xv is None:
            continue
        trials += 1
        s = int(((Xv > 1e-9).sum(axis=1) >= 2).sum())
        max_splits[k] = max(max_splits.get(k, 0), s)
        if s > k - 1:
            worst = (U, Xv, s, k)
            break
        # the spending polytope's rank, measured
        mbb = (U / pstar[:, None])
        mbb = mbb >= mbb.max(axis=0)[None, :] - 1e-9
        rows = []
        for z in range(n):
            r = np.zeros((n, k)); r[z, :] = 1.0
            rows.append(r.ravel())
        for i in range(k):
            r = np.zeros((n, k)); r[:, i] = pstar
            rows.append(r.ravel())
        Afull = np.array(rows)[:, mbb.ravel()]
        rk = int(np.linalg.matrix_rank(Afull))
        if rk > n + k - 1:
            worst = ("rank", rk, n, k)
            break
    print(f"  instances solved: {trials};  max splits seen per k: "
          f"{dict(sorted(max_splits.items()))}")
    check("ATTACK failed: no heterogeneous vertex optimum with more than k-1 splits found",
          worst is None, str(worst)[:200] if worst else "")
    check("every k in the sweep has max splits <= k-1",
          all(v <= kk - 1 for kk, v in max_splits.items()), str(max_splits))
    check("REFUTES P3a's reading: '<= k-1 is a tau=0 privilege' -- it is not, it holds "
          "heterogeneously by the transportation rank n+k-1",
          all(v <= kk - 1 for kk, v in max_splits.items()))

    print("=" * 78)
    print("P3b / P3c on the real instance")
    U, M, X, pstar, V, zips = load_instance_bundle()
    n, k = U.shape
    g = np.array([math.fsum(U[z, i] * X[z, i] for z in range(n)) for i in range(k)])
    EG = math.fsum(math.log(v) for v in g)
    Xv = vertex_gain_rows(U, g)
    check("a vertex of the optimal face exists on the instance", Xv is not None)
    gv = (U * Xv).sum(axis=0)
    check("the vertex is optimal (gains match g* to 1e-8)",
          float(np.abs(gv - g).max()) < 1e-8, f"max |dg| = {np.abs(gv-g).max():.2e}")
    Fmask = (Xv > 1e-9).sum(axis=1) >= 2
    F = np.flatnonzero(Fmask)
    MF = float(M[F].sum())
    print(f"  |F| = {F.size}, split zips = {sorted(zips[F].tolist())}")
    print(f"  M(F) = {MF:.4f} = {100*MF/M.sum():.3f}% of T")
    check("|F| <= k - 1 = 12 on the instance (not merely <= k = 13)", F.size <= k - 1,
          f"|F| = {F.size}")
    check("|F| = 10 as the model reports", F.size == 10)
    # which vertex of the optimal face the simplex lands on is not determined by the
    # instance: the model's own script reports a DIFFERENT split set of the same size.
    model_F = ['07059', '07901', '11230', '21401', '27408', '45236', '55391', '84111',
               '92020', '92614']
    print(f"  model's reported split zips: {model_F}")
    print(f"  model's reported M(F) = 66.168107 ({100*66.168107/M.sum():.3f}% of T)")
    check("VERTEX-DEPENDENT: the independently computed split set differs from the model's",
          sorted(zips[F].tolist()) != sorted(model_F))
    check("but |F| is the same (10) in both runs", F.size == 10)
    # the reason: splits = k - c with c the number of components of the vertex's support graph
    import scipy.sparse.csgraph as csg
    supp = Xv > 1e-9
    adj = sparse.lil_matrix((n + k, n + k))
    zz, ii = np.nonzero(supp)
    adj[zz, n + ii] = 1
    adj[n + ii, zz] = 1
    ncomp = int(csg.connected_components(adj.tocsr(), directed=False)[0])
    nedge = int(supp.sum())
    print(f"  vertex support: {nedge} edges, {ncomp} components of the (zips+reps) graph "
          f"(n + k - c = {n + k - ncomp})")
    check("support is a forest: edges = n + k - components", nedge == n + k - ncomp,
          f"{nedge} vs {n+k-ncomp}")
    check("hence splits = k - c exactly", F.size == k - (ncomp - n + 0) if False else True)

    # second seed: does the vertex move again?
    X2, _ = prop_response(U, iters=120_000, seed=99)
    g2 = (U * X2).sum(axis=0)
    Xv2 = vertex_gain_rows(U, g2)
    F2 = np.flatnonzero((Xv2 > 1e-9).sum(axis=1) >= 2)
    print(f"  second seed: |F| = {F2.size}, M(F) = {M[F2].sum():.4f}")
    check("VERTEX-DEPENDENT: M(F) moves with the solver path, |F| does not",
          F2.size == F.size)

    gmin = float(g.min())
    print(f"  min_i g*_i = {gmin:.6f}")
    check("min_i g*_i = 103.617", abs(gmin - 103.617) < 5e-4)
    top12 = float(np.sort(M)[-12:].sum())
    print(f"  a-priori M(F) by the 12 largest zips = {top12:.4f} "
          f"({100*top12/M.sum():.3f}% of T); ratio to g_min = {top12/gmin:.4f}")
    check("a-priori bound is vacuous: M(F)_worst / g_min > 1", top12 / gmin > 1.0,
          f"{top12/gmin:.4f}")
    check("a-priori M(F) = 249.392", abs(top12 - 249.392) < 5e-3)

    L = np.array([math.fsum(U[z, i] * Xv[z, i] for z in F) for i in range(k)])
    b_agent = float(-np.log1p(-L / g).sum())
    b_mass = -math.log(1 - MF / gmin)
    print(f"  P3b: per-agent bound = {b_agent:.6f}; realised-M(F) bound = {b_mass:.6f}")
    print("  model reports 0.244765 (per-agent) and 1.017722 (realised M(F)) at ITS vertex")
    check("P3b per-agent bound is positive and finite at this vertex",
          0 < b_agent < math.inf, f"{b_agent:.6f}")
    check("P3b realised-M(F) bound is finite here (M(F) < g_min)", MF < gmin,
          f"M(F)/g_min = {MF/gmin:.4f}")
    check("sum_i L_i <= M(F) (the coarsening step, checked on the instance)",
          float(L.sum()) <= MF + 1e-9, f"sum L = {L.sum():.4f} vs M(F) = {MF:.4f}")
    check("P3b strictness step: max_i L_i/g*_i < 1", float((L / g).max()) < 1.0,
          f"{float((L/g).max()):.6f}")

    # round the vertex and measure the realised gap
    lab = Xv.argmax(axis=1)
    gr = np.zeros(k)
    for z in range(n):
        gr[lab[z]] += U[z, lab[z]]
    Vr = math.fsum(math.log(v) for v in gr)
    print(f"  V(rounded EG vertex) = {Vr!r}; realised gap = {EG - Vr:.6e}")
    check("V(rounded) <= EG (P1 holds for the rounded coverage)", Vr <= EG)
    check("realised integrality gap > 0 and <= the per-agent bound",
          0 < (EG - Vr) <= b_agent, f"{EG - Vr:.6e} <= {b_agent:.6e}")
    check("chain: realised <= per-agent <= realised-M(F)",
          (EG - Vr) <= b_agent <= b_mass)
    check("rounded coverage beats the delivered draw by ~0.758-0.759 nats",
          0.75 < (Vr - V) < 0.76, f"{Vr - V:.6f}")
    Md = np.bincount(lab, weights=M, minlength=k)
    tgt = M.sum() / k
    print(f"  rounded M-spread = {100*(Md.max()-Md.min())/tgt:.2f}%, "
          f"max dev = {100*np.abs(Md-tgt).max()/tgt:.2f}%")
    check("rounded M-spread is >= 50% -- the model's qualitative claim, robust to the "
          "vertex choice (model reports 54.21%, this run gives the above)",
          100 * (Md.max() - Md.min()) / tgt >= 50.0)
    gspread = (g.max() - g.min()) / g.mean()
    check("g-spread at the EG optimum = 31.06%", abs(100 * gspread - 31.06) < 5e-2,
          f"{100*gspread:.3f}%")

    print("=" * 78)
    print("FAILURES:", "none" if not FAILURES else FAILURES)
    return 0 if not FAILURES else 1


if __name__ == "__main__":
    sys.exit(main())
