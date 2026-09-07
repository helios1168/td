"""Scale check for td/solvers/state_splits.py: counts at S = 49, k = 18, E = 107, and the
runtime the plan calls "seconds", on two synthetic real-shape geometries.

    /Users/ntlee/projects/td/.venv/bin/python3 docs/verify/codeverify_state_splits_scale.py [secs]
"""
from __future__ import annotations

import sys
import time

import numpy as np
from scipy.optimize import Bounds, LinearConstraint, milp

sys.path.insert(0, "/Users/ntlee/projects/td/.claude/worktrees/vbl")
from td.solvers import state_splits as ss   # noqa: E402

LIMIT = float(sys.argv[1]) if len(sys.argv) > 1 else 300.0
S, K, E = 49, 18, 107


def grid_instance(seed=7):
    """A planar 7x7 'rook' graph (84 edges) topped up to 107 with diagonals; D from a planar
    embedding, so the geometry is the kind the real instance has."""
    rng = np.random.default_rng(seed)
    pts = np.array([[i, j] for i in range(7) for j in range(7)], float)

    def idx(i, j):
        return i * 7 + j
    edges = ([(idx(i, j), idx(i + 1, j)) for i in range(6) for j in range(7)]
             + [(idx(i, j), idx(i, j + 1)) for i in range(7) for j in range(6)])
    diag = [(idx(i, j), idx(i + 1, j + 1)) for i in range(6) for j in range(6)]
    edges += [diag[t] for t in rng.choice(len(diag), E - len(edges), replace=False)]
    M = rng.uniform(0.5, 6.0, S)
    C = pts[rng.choice(S, K, replace=False)] + rng.normal(0, 0.2, (K, 2))
    D = ((pts[:, None, :] - C[None, :, :]) ** 2).sum(axis=2)
    return M, D, edges


def random_instance(seed=49):
    rng = np.random.default_rng(seed)
    edges = [(s, s + 1) for s in range(S - 1)]
    pool = [(u, v) for u in range(S) for v in range(u + 2, S)]
    edges += [pool[i] for i in rng.choice(len(pool), E - len(edges), replace=False)]
    return rng.uniform(0.2, 12.0, S), rng.uniform(0.01, 100.0, (S, K)), edges


for name, (M, D, edges) in (("planar 7x7", grid_instance()), ("random", random_instance())):
    p = ss.build_milp(M, D, edges, float(M.sum()) / K, 0.05, ss.eps_lexicographic(M, D))
    print(f"\n-- {name}: E = {len(edges)}")
    print("   variables", p.n_var, "integral", int(p.integrality.sum()))
    print("   rows", p.A.shape[0], {n: b - a for n, (a, b) in p.rows.items()})
    t = time.time()
    res = milp(c=p.c, constraints=LinearConstraint(p.A, p.lb, p.ub), integrality=p.integrality,
               bounds=Bounds(p.var_lb, p.var_ub),
               options={"mip_rel_gap": 0.0, "time_limit": LIMIT})
    el = time.time() - t
    inc = None if res.x is None else int(round(np.asarray(res.x)[:S * K].sum() - S))
    print(f"   status {res.status} ({res.message}) in {el:.1f}s; "
          f"incumbent splits {inc}, gap {res.mip_gap}")
