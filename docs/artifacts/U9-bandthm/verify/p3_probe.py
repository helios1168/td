"""P3-split: isolate and dissect every apparent violation of #splits <= k-1+t.

For each candidate vertex we record, in exact-ish detail:
  * is it really OPTIMAL (Sum log g == phi within the certified bracket)?
  * is it really a VERTEX of the optimal face (rank of tight rows == |supp|)?
  * t under several tightness thresholds (the count that sets the bound)
  * whether the claimed dependency D actually annihilates the tight rows
"""
from __future__ import annotations

import math
import sys

import numpy as np
from pyscipopt import Model, quicksum

import oracle as O


def face_vertex(u, M, delta, gstar, c):
    k, n = u.shape
    T = float(M.sum())
    m = Model()
    m.hideOutput()
    m.setParam("limits/gap", 0.0)
    x = [[m.addVar(lb=0.0, ub=1.0) for _ in range(n)] for _ in range(k)]
    for z in range(n):
        m.addCons(quicksum(x[i][z] for i in range(k)) == 1.0)
    for i in range(k):
        m.addCons(quicksum(float(M[z]) * x[i][z] for z in range(n)) <= (1 + delta) * T / k)
        m.addCons(quicksum(float(M[z]) * x[i][z] for z in range(n)) >= (1 - delta) * T / k)
        m.addCons(quicksum(float(u[i, z]) * x[i][z] for z in range(n)) == float(gstar[i]))
    m.setObjective(quicksum(float(c[i, z]) * x[i][z] for i in range(k) for z in range(n)),
                   "maximize")
    m.optimize()
    if m.getStatus() != "optimal":
        return None
    return np.array([[m.getVal(x[i][z]) for z in range(n)] for i in range(k)])


def dissect(u, M, delta, V, gstar, bracket, xtol=1e-9):
    k, n = u.shape
    T = float(M.sum())
    sup = V > xtol
    cols = [(i, z) for i in range(k) for z in range(n) if sup[i, z]]
    splits = sum(1 for z in range(n) if sup[:, z].sum() >= 2)
    mm = (V * M[None, :]).sum(axis=1)
    gg = (u * V).sum(axis=1)
    val = float(np.sum(np.log(gg))) if gg.min() > 0 else -math.inf
    out = {"splits": splits, "supp": len(cols), "m": mm, "g": gg, "val": val,
           "in_bracket": bracket["L"] - 1e-7 <= val <= bracket["U"] + 1e-7}
    for tol in (1e-12, 1e-9, 1e-7, 1e-5):
        out[f"t@{tol:g}"] = int(sum(
            1 for i in range(k)
            if mm[i] >= (1 + delta) * T / k - tol * T / k
            or mm[i] <= (1 - delta) * T / k + tol * T / k))
    # rank of the tight rows (supply + gain + tight band) restricted to supp columns
    rows = []
    for z in range(n):
        rows.append([1.0 if zz == z else 0.0 for (ii, zz) in cols])
    for i in range(k):
        rows.append([float(u[i, zz]) if ii == i else 0.0 for (ii, zz) in cols])
    tb = [i for i in range(k)
          if mm[i] >= (1 + delta) * T / k - 1e-9 * T / k
          or mm[i] <= (1 - delta) * T / k + 1e-9 * T / k]
    for i in tb:
        rows.append([float(M[zz]) if ii == i else 0.0 for (ii, zz) in cols])
    A = np.array(rows)
    out["rank_all_rows"] = int(np.linalg.matrix_rank(A, tol=1e-8))
    out["is_vertex"] = out["rank_all_rows"] == len(cols)
    out["nrows"] = A.shape[0]
    out["tightband"] = tb
    out["dev"] = np.abs(mm - T / k) / (T / k)
    return out


def main():
    rng = np.random.default_rng(5150)
    found = 0
    scanned = 0
    for trial in range(400):
        n = int(rng.integers(4, 11))
        k = int(rng.integers(2, 6))
        if k > n:
            continue
        style = int(rng.integers(0, 3))
        if style == 0:
            M = np.round(rng.uniform(1.0, 50.0, size=n), 3)
        elif style == 1:
            M = np.round(np.exp(rng.normal(2.0, 1.4, size=n)), 3)
        else:
            M = np.round(rng.uniform(1.0, 5.0, size=n), 3)
            M[0] *= 12.0
        u = np.round(rng.uniform(0.25, 1.0, size=(k, n)) * M[None, :], 4)
        d = float(rng.choice([0.0, 1e-4, 0.01, 0.05, 0.15, 0.5]))
        try:
            pr = O.scip_primal(u, M, d, tl=25)
            if pr["status"] != "optimal":
                continue
            br = O.bracket(u, M, d)
        except Exception:
            continue
        gstar = (u * pr["X"]).sum(axis=1)
        for _ in range(4):
            V = face_vertex(u, M, d, gstar, rng.normal(size=(k, n)))
            if V is None:
                continue
            scanned += 1
            info = dissect(u, M, d, V, gstar, br)
            if info["splits"] <= k - 1 + info["t@1e-09"]:
                continue
            found += 1
            if found > 6:
                return
            print("=" * 78)
            print(f"CANDIDATE VIOLATION  n={n} k={k} delta={d}  style={style}")
            print(f"  M = {M}")
            print(f"  u =\n{u}")
            print(f"  X =\n{np.round(V, 10)}")
            print(f"  splits = {info['splits']}   |supp| = {info['supp']}   "
                  f"n+k = {n+k}")
            print(f"  masses = {np.round(info['m'],8)}   T/k = {M.sum()/k:.8f}   "
                  f"band = [{(1-d)*M.sum()/k:.8f}, {(1+d)*M.sum()/k:.8f}]")
            print(f"  relative deviation |m-T/k|/(T/k) = {info['dev']}")
            print(f"  t at tolerances: " + ", ".join(
                f"{tt}={info[f't@{tt:g}']}" for tt in (1e-12, 1e-9, 1e-7, 1e-5)))
            print(f"  bound k-1+t (t@1e-9) = {k-1+info['t@1e-09']};  2k-1 = {2*k-1}")
            print(f"  objective at V = {info['val']:.12f}; certified bracket = "
                  f"[{br['L']:.12f}, {br['U']:.12f}];  optimal = {info['in_bracket']}")
            print(f"  rank(tight rows | supp cols) = {info['rank_all_rows']} of "
                  f"{info['nrows']} rows, |supp| = {info['supp']} "
                  f"=> is a vertex: {info['is_vertex']}")
            print(f"  n + k + t - 1 = {n + k + info['t@1e-09'] - 1}")
    print(f"\nscanned {scanned} vertices, {found} candidate violations")


if __name__ == "__main__":
    sys.exit(main())
