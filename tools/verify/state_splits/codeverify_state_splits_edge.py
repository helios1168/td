"""Boundary / degenerate inputs plus a targeted search against "the pass never widens spread".

    /Users/ntlee/projects/td/.venv/bin/python3 docs/verify/codeverify_state_splits_edge.py
"""
from __future__ import annotations

import sys

import numpy as np

sys.path.insert(0, "/Users/ntlee/projects/td/.claude/worktrees/vbl")
from td.solvers import state_splits as ss   # noqa: E402

FAIL = []


def check(name, ok, detail=""):
    print(f"{'ok  ' if ok else 'FAIL'} {name} {detail}")
    if not ok:
        FAIL.append(f"{name} {detail}")


def raises(fn, exc=Exception):
    try:
        fn()
    except exc:
        return True
    except Exception as e:                      # noqa: BLE001
        print("   unexpected:", type(e).__name__, e)
        return False
    return False


print("== degenerate inputs ==")
one = np.array([5.0])
check("S=1, k=1 solves with 0 splits",
      ss.solve(ss.build_milp(one, np.array([[1.0]]), [], 5.0, 0.0, 0.0))["splits"] == 0)
check("k=1, S=3, no edges -> infeasible (contiguity)",
      raises(lambda: ss.solve(ss.build_milp(np.ones(3), np.zeros((3, 1)), [], 3.0, 0.0, 0.0)),
             RuntimeError))
check("k=1, S=3, path -> feasible, 0 splits",
      ss.solve(ss.build_milp(np.ones(3), np.zeros((3, 1)), [(0, 1), (1, 2)], 3.0, 0.0,
                             0.0))["splits"] == 0)
check("tau <= 0 raises", raises(lambda: ss.build_milp(one, np.array([[1.0]]), [], 0.0, 0.0, 0.0),
                                ValueError))
check("shape mismatch raises",
      raises(lambda: ss.build_milp(np.ones(3), np.zeros((2, 2)), [], 1.0, 0.0, 0.0), ValueError))
check("self-loop / out-of-range edge raises",
      raises(lambda: ss.build_milp(np.ones(3), np.zeros((3, 2)), [(1, 1)], 1.0, 0.0, 0.0),
             ValueError)
      and raises(lambda: ss.build_milp(np.ones(3), np.zeros((3, 2)), [(0, 3)], 1.0, 0.0, 0.0),
                 ValueError))
check("eps_lexicographic on all-zero D raises",
      raises(lambda: ss.eps_lexicographic(np.ones(3), np.zeros((3, 2))), ValueError))
check("balance_pass rejects a mis-shaped z",
      raises(lambda: ss.balance_pass(ss.build_milp(np.ones(3), np.zeros((3, 2)),
                                                   [(0, 1), (1, 2)], 1.5, 0.5, 0.0),
                                     np.ones((2, 2), bool)), ValueError))

# infeasible band: 2 states, k = 2, masses 1 and 3, delta = 0 -> the split fixes it; masses 1,3
# with eta = 0.9 cannot
M_s = np.array([1.0, 3.0])
D = np.array([[1.0, 2.0], [2.0, 1.0]])
r = ss.solve(ss.build_milp(M_s, D, [(0, 1)], 2.0, 0.0, 0.0))
check("delta = 0 forces the split", r["splits"] == 1 and abs(r["masses"] - 2.0).max() < 1e-7,
      f"{r['masses']}")
check("eta = 0.9 makes it infeasible",
      raises(lambda: ss.solve(ss.build_milp(M_s, D, [(0, 1)], 2.0, 0.0, 0.0, eta=0.9)),
             RuntimeError))

# a zero-mass state: it must still be placed and must not break the band
M0 = np.array([10.0, 0.0, 10.0])
r0 = ss.solve(ss.build_milp(M0, np.array([[1., 3.], [2., 2.], [3., 1.]]),
                            [(0, 1), (1, 2)], 10.0, 0.0, 0.0))
check("zero-mass state is placed and the band holds",
      np.isclose(r0["y"].sum(axis=1), 1).all() and abs(r0["masses"] - 10.0).max() < 1e-7,
      f"splits {r0['splits']} masses {r0['masses']}")

# realise with a state that owns no zips
xy = np.array([[0., 0.], [0.1, 0.], [2., 0.], [2.1, 0.]])
M = np.array([1., 1., 1., 1.])
state_idx = np.array([0, 0, 2, 2])              # state 1 has no zips
z = np.array([[1, 0], [1, 0], [0, 1]], bool)
y = np.array([[1., 0.], [1., 0.], [0., 1.]])
out = ss.realise(xy, M, state_idx, z, y, np.array([[0., 0.], [2., 0.]]), rounds=2)
check("realise tolerates a zip-less state", (out["labels"] == [0, 0, 1, 1]).all(),
      f"{out['labels']}")
check("realise rejects a state touching no district",
      raises(lambda: ss.realise(xy, M, state_idx, np.zeros((3, 2), bool), y,
                                np.array([[0., 0.], [2., 0.]])), ValueError))
check("realise rejects an out-of-range state_idx",
      raises(lambda: ss.realise(xy, M, np.array([0, 0, 3, 3]), z, y,
                                np.array([[0., 0.], [2., 0.]])), ValueError))

print("\n== targeted search: can the pass widen the spread? ==")
rng = np.random.default_rng(31337)
edges6 = [(0, 1), (1, 2), (2, 3), (3, 4), (4, 5)]
edgesC = edges6 + [(5, 0)]
wider, n, worst = 0, 0, 0.0
for t in range(400):
    S = 6
    k = int(rng.choice([2, 3, 4]))
    edges = edges6 if t % 2 else edgesC
    M_s = rng.uniform(0.2, 8.0, S)
    D = rng.uniform(0.01, 80.0, (S, k))
    tau = float(M_s.sum()) / k
    delta = 0.10
    try:
        prob = ss.build_milp(M_s, D, edges, tau, delta, ss.eps_lexicographic(M_s, D))
        res = ss.solve(prob)
    except RuntimeError:
        continue
    pas = ss.balance_pass(prob, res["z"])
    n += 1
    d = pas["spread_rel"] - res["spread_rel"]
    if d > 1e-9:
        wider += 1
        worst = max(worst, d)
        print("   WIDER", d, M_s.tolist(), delta, k)
check("pass spread <= MILP spread at delta = 10%", wider == 0,
      f"{n} feasible trials, {wider} wider, worst {worst:.3g}")

print("\n", "-" * 60)
print(f"{len(FAIL)} failing checks")
for f in FAIL:
    print("  FAIL", f)
