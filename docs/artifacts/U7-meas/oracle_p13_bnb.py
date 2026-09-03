"""oracle_p13_bnb.py -- a third, solver-free proof of P13 on the real instance.

Branch and bound over staff sets with the standard submodular bound: for a partial set `C`
with `r` picks left, no completion can beat `f(C) + sum of the r largest marginal gains
f(C + i) - f(C)` (submodularity, DOMAIN_optimization §2.3's max-k-coverage).  Depth-first,
seeded with the greedy incumbent, so it certifies the optimum without scipy.milp, SCIP or
any LP.

    .venv/bin/python3 docs/artifacts/U7-meas/oracle_p13_bnb.py instance_descaled.json.gz 13
"""
from __future__ import annotations

import gzip
import json
import sys
import time

import numpy as np


def load_S(inst):
    with gzip.open(inst, "rt", encoding="utf-8") as fh:
        obj = json.load(fh)
    n = obj["nodes"]
    m = np.array([float(v) for v in n["m_rel"]], float)
    reps = sorted({r for sh in n["share"] for r in sh})
    ir = {r: i for i, r in enumerate(reps)}
    S = np.zeros((len(reps), len(m)), float)
    for j, sh in enumerate(n["share"]):
        for r, s in sh.items():
            S[ir[r], j] = float(s) * m[j]
    return S, reps


def main(inst, k=13):
    k = int(k)
    S, reps = load_S(inst)
    n = S.shape[0]
    order = np.argsort(-S.sum(axis=1))          # strongest books first: better pruning
    S = S[order]
    reps = [reps[i] for i in order]

    # greedy incumbent
    held = np.zeros(S.shape[1])
    chosen = []
    for _ in range(k):
        cand = np.maximum(S, held).sum(axis=1)
        cand[chosen] = -np.inf
        i = int(np.argmax(cand))
        chosen.append(i)
        held = np.maximum(held, S[i])
    best = float(held.sum())
    best_set = list(chosen)
    print(f"greedy incumbent {best:.10f} at {sorted(reps[i] for i in best_set)}")

    nodes = [0]
    t0 = time.time()

    def bound(held, start, left):
        """f(C) + the `left` largest single marginals over i >= start (submodular bound)."""
        if left == 0:
            return float(held.sum())
        marg = np.maximum(S[start:], held).sum(axis=1) - held.sum()
        if marg.size == 0:
            return float(held.sum())
        top = np.sort(marg)[::-1][:left]
        return float(held.sum() + top.sum())

    def rec(start, left, held):
        nonlocal best, best_set
        nodes[0] += 1
        if left == 0:
            v = float(held.sum())
            if v > best + 1e-12:
                best = v
            return
        if n - start < left:
            return
        if bound(held, start, left) <= best + 1e-12:
            return
        # branch on candidates in decreasing marginal order
        marg = np.maximum(S[start:], held).sum(axis=1) - held.sum()
        for off in np.argsort(-marg):
            i = start + int(off)
            if n - i < left:
                continue
            rec(i + 1, left - 1, np.maximum(held, S[i]))

    sys.setrecursionlimit(10000)
    rec(0, k, np.zeros(S.shape[1]))
    print(f"B&B optimum {best:.10f}  ({nodes[0]:,} nodes, {time.time() - t0:.1f}s)")
    return 0


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:3]))
