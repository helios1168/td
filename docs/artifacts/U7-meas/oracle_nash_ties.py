"""oracle_nash_ties.py -- is `S13 = im sigma_nash` unique on the real instance?

`P_S`, U4 and U8 are functions of the *set* S13, which the implementation takes to be the
image of `channel.stage2`'s Nash matching.  When the Nash matching has alternative optima the
set is only defined up to `scipy.optimize.linear_sum_assignment`'s tie-break -- and a tie is
structurally likely here, because every rep with no book in a district values it identically
(CLAUDE.md trap 4).  A random 5-rep search found 20 tied instances in 4000.

This checks the two real draws directly: for every rep `c` outside S13 and every district `j`,
re-solve the Nash matching with `c` forced onto `j` and compare the value to the optimum.  An
equal value (to 1e-12 in nats, and exactly in gain terms) is an alternative optimum with a
different S13.  Also reports the smallest strictly-positive loss, i.e. how far the tie-break
is from binding.

    .venv/bin/python3 docs/artifacts/U7-meas/oracle_nash_ties.py \
        instance_descaled.json.gz battery/results/draw_k13_20260901
"""
from __future__ import annotations

import csv
import gzip
import json
import sys

import numpy as np
from scipy.optimize import linear_sum_assignment

THETA, LAM = 0.40, 0.30


def load(inst, drawdir):
    with gzip.open(inst, "rt", encoding="utf-8") as fh:
        obj = json.load(fh)
    n = obj["nodes"]
    zips = list(n["z"])
    m = np.array([float(v) for v in n["m_rel"]], float)
    free = np.array([float(v or 0.0) for v in (n.get("share_free") or [0.0] * len(zips))],
                    float) * m
    reps = sorted({r for sh in n["share"] for r in sh})
    ir = {r: i for i, r in enumerate(reps)}
    S = np.zeros((len(reps), len(zips)), float)
    for j, sh in enumerate(n["share"]):
        for r, s in sh.items():
            S[ir[r], j] = float(s) * m[j]
    with open(f"{drawdir}/draw.csv", newline="", encoding="utf-8") as fh:
        to_d = {r["zip"]: r["district"] for r in csv.DictReader(fh)}
    D = sorted(set(to_d.values()))
    jd = {d: j for j, d in enumerate(D)}
    col = np.array([jd[to_d[z]] for z in zips], int)
    return zips, reps, S, m, free, D, col


def main(inst, drawdir):
    zips, reps, S, M, free, D, col = load(inst, drawdir)
    c1, c2 = 1.0 - LAM, THETA * (1.0 - LAM)
    common = c2 * S.sum(axis=0) + c2 * free + LAM * M
    g = np.zeros((len(reps), len(D)))
    for j in range(len(D)):
        sel = col == j
        g[:, j] = common[sel].sum() + (c1 - c2) * S[:, sel].sum(axis=1)
    L = np.log(g)
    rows, cols = linear_sum_assignment(-L)
    V = float(L[rows, cols].sum())
    roster = {int(j): int(i) for i, j in zip(rows, cols)}
    S13 = sorted(roster.values())
    print(f"{drawdir}: V = {V:.15f}, S13 = {[reps[i] for i in S13]}")

    def forced(i0, j0):
        ri = [i for i in range(len(reps)) if i != i0]
        cj = [j for j in range(len(D)) if j != j0]
        sub = L[np.ix_(ri, cj)]
        r2, c2_ = linear_sum_assignment(-sub)
        return float(sub[r2, c2_].sum()) + float(L[i0, j0])

    alts, losses = [], []
    for i0 in range(len(reps)):
        if i0 in S13:
            continue
        for j0 in range(len(D)):
            v = forced(i0, j0)
            d = V - v
            losses.append(d)
            if d <= 1e-12:
                alts.append((reps[i0], D[j0], d))
    losses = np.array(losses)
    print(f"outside-S13 forcings tried: {losses.size}; "
          f"alternative optima (loss <= 1e-12): {len(alts)}")
    print(f"smallest loss over all forcings: {losses.min():.6e} nats")
    for a in alts[:10]:
        print("  ALT OPT:", a)

    # how much would P_S move if the tie-break went the other way?
    def P_S(idx):
        return float(S[list(idx)].max(axis=0).sum())
    print(f"P_S at the chosen S13: {P_S(S13):.10f}")
    for r, d, _ in alts[:10]:
        i0, j0 = reps.index(r), D.index(d)
        alt = sorted(set(S13) - {roster[j0]} | {i0})
        print(f"  P_S if {r} replaced {reps[roster[j0]]} on {d}: {P_S(alt):.10f}")
    return 0


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:3]))
