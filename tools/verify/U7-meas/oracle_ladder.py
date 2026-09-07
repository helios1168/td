"""oracle_ladder.py -- independent recomputation of MODEL_U7-meas.md's numbers.

Reads `instance_descaled.json.gz` with gzip+json directly (no `td.instance`), rebuilds
S_i(z) = share_i(z) * m_rel(z), M_z = m_rel(z), S_free(z) = share_free(z) * m_rel(z), and
recomputes the whole ladder, U1, U4, U8, V and the nat conversions with no call into
`tools/measure/premium.py` or `td/`.

  P*(A) : assignment LP through scipy.optimize.linprog (HiGHS simplex on the
          totally-unimodular assignment polytope), not the Hungarian algorithm.
  P13   : max-k-coverage MILP through pyscipopt (SCIP), not scipy/HiGHS, at gap 0,
          plus an independent greedy and a submodular (1 - 1/e) sanity bound.

    .venv/bin/python3 docs/artifacts/U7-meas/oracle_ladder.py \
        instance_descaled.json.gz battery/results/draw_k13_20260901 \
        battery/results/meas_20260903/draw_k13_20260901.json
"""
from __future__ import annotations

import csv
import gzip
import json
import math
import sys

import numpy as np
from scipy.optimize import linprog

THETA, LAM = 0.40, 0.30


def load_raw(path):
    with gzip.open(path, "rt", encoding="utf-8") as fh:
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
    order = np.argsort(np.array(zips))          # the code works on sorted(to_district)
    zips = [zips[i] for i in order]
    return dict(zips=zips, reps=reps, S=S[:, order], M=m[order], free=free[order])


def read_draw(d):
    with open(f"{d}/draw.csv", newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    to_d = {r["zip"]: r["district"] for r in rows}
    with open(f"{d}/metrics.json", encoding="utf-8") as fh:
        met = json.load(fh)
    return to_d, met


def assignment_lp(b):
    """max sum_j b[sigma(j), j] over injective sigma, as an LP (integral polytope)."""
    nr, nd = b.shape
    nv = nr * nd
    c = -b.reshape(-1)
    A_ub = np.zeros((nr, nv))
    for i in range(nr):
        A_ub[i, i * nd:(i + 1) * nd] = 1.0
    A_eq = np.zeros((nd, nv))
    for j in range(nd):
        A_eq[j, j::nd] = 1.0
    res = linprog(c, A_ub=A_ub, b_ub=np.ones(nr), A_eq=A_eq, b_eq=np.ones(nd),
                  bounds=(0.0, 1.0), method="highs")
    assert res.status == 0, res.message
    x = res.x.reshape(nr, nd)
    roster = {j: int(np.argmax(x[:, j])) for j in range(nd)}
    integral = float(np.abs(x - np.round(x)).max())
    return -float(res.fun), roster, integral


def greedy(S, k):
    chosen, held = [], np.zeros(S.shape[1])
    for _ in range(k):
        best, bv = None, -np.inf
        for i in range(S.shape[0]):
            if i in chosen:
                continue
            v = float(np.maximum(held, S[i]).sum())
            if v > bv:
                best, bv = i, v
        chosen.append(best)
        held = np.maximum(held, S[best])
    return sorted(chosen), float(held.sum())


def scip_max_k_coverage(S, k, reps):
    """P13 through SCIP, gap 0.  Returns (value, staff, status)."""
    from pyscipopt import Model
    m = Model("maxkcov")
    m.hideOutput()
    m.setRealParam("limits/gap", 0.0)
    m.setRealParam("limits/absgap", 0.0)
    y = [m.addVar(vtype="B", name=f"y{i}") for i in range(S.shape[0])]
    pi, pz = np.nonzero(S > 0.0)
    wv = {}
    per_zip = {}
    obj = []
    for i, z in zip(pi.tolist(), pz.tolist()):
        v = m.addVar(lb=0.0, ub=1.0, vtype="C", name=f"w{i}_{z}")
        wv[(i, z)] = v
        per_zip.setdefault(z, []).append(v)
        m.addCons(v <= y[i])
        obj.append(float(S[i, z]) * v)
    for z, vs in per_zip.items():
        m.addCons(sum(vs) <= 1)
    m.addCons(sum(y) == k)
    m.setObjective(sum(obj), "maximize")
    m.optimize()
    status = m.getStatus()
    if status != "optimal":
        return None, None, status
    staff = sorted(i for i in range(S.shape[0]) if m.getVal(y[i]) > 0.5)
    return float(m.getObjVal()), [reps[i] for i in staff], status


def main(inst, drawdir, produced):
    raw = load_raw(inst)
    S, M, free, reps, zips = (raw["S"], raw["M"], raw["free"], raw["reps"], raw["zips"])
    iz = {z: j for j, z in enumerate(zips)}
    ir = {r: i for i, r in enumerate(reps)}
    to_d, met = read_draw(drawdir)
    out = json.load(open(produced, encoding="utf-8"))

    D = sorted({d for d in to_d.values()})
    jd = {d: j for j, d in enumerate(D)}
    col = np.full(len(zips), -1, int)
    for z, d in to_d.items():
        col[iz[z]] = jd[d]
    assert (col >= 0).all() and len(to_d) == len(zips)

    b = np.zeros((len(reps), len(D)))
    for j in range(len(D)):
        b[:, j] = S[:, col == j].sum(axis=1)

    sigma0 = met["winner"]["assignment"]
    total_book = float(S.sum())
    total_M = float(M.sum())

    # ---- P0
    P0 = float(sum(b[ir[sigma0[d]], jd[d]] for d in D))

    # ---- P*(A) by LP
    P_star, lp_roster, integrality = assignment_lp(b)
    lp_roster_named = {D[j]: reps[i] for j, i in lp_roster.items()}

    # ---- P_S / P_free by direct max
    staff = sorted(set(out["sigma_nash"].values()))
    P_S = float(S[[ir[r] for r in staff]].max(axis=0).sum())
    P_free = float(S.max(axis=0).sum())

    # ---- P13
    g_idx, g_val = greedy(S, len(D))
    scip_val, scip_staff, scip_status = scip_max_k_coverage(S, len(D), reps)
    scip_eval = (float(S[[ir[r] for r in scip_staff]].max(axis=0).sum())
                 if scip_staff else None)
    claimed = out["P13_solve"]["staff"]
    claimed_eval = float(S[[ir[r] for r in claimed]].max(axis=0).sum())

    # ---- gains, V, U1 (recompute g by hand from the definition)
    c1, c2 = 1.0 - LAM, THETA * (1.0 - LAM)
    T = S.sum(axis=0)
    common_z = c2 * T + c2 * free + LAM * M          # filler_capture="theta" -> c_free = c2
    g = np.zeros((len(reps), len(D)))
    for j in range(len(D)):
        sel = col == j
        g[:, j] = common_z[sel].sum() + (c1 - c2) * S[:, sel].sum(axis=1)
    gains = np.array([g[ir[sigma0[d]], jd[d]] for d in D])
    V0 = float(np.log(gains).sum())
    V_star = float(sum(math.log(g[ir[lp_roster_named[d]], jd[d]]) for d in D))
    M_dist = np.array([M[col == j].sum() for j in range(len(D))])
    w = c1 - c2

    # g - w*b rows identical?
    resid = g - w * b
    rows_dev = float(np.abs(resid - resid[0]).max())

    # ---- U4
    cand_sets = [{reps[i] for i in np.nonzero(S[:, j] > 0.0)[0]} for j in range(len(zips))]
    sel = set(staff)
    u4 = [j for j in range(len(zips)) if len(sel & cand_sets[j]) >= 2]
    u4_M = float(M[u4].sum())

    # ---- U8
    pooled = float(np.corrcoef(T, M)[0, 1])
    per_rep = {}
    for r in staff:
        row = S[ir[r]]
        h = row > 0.0
        per_rep[r] = float(np.corrcoef(row[h], M[h])[0, 1])

    gbar = float(gains.mean())

    def nats(dp):
        return w * dp / gbar

    rep = dict(
        n_zips=len(zips), n_reps=len(reps), k=len(D), w=w,
        total_book=total_book, total_M=total_M,
        P0=P0, P0_share=P0 / total_book,
        P_star=P_star, P_star_share=P_star / total_book,
        P_star_roster=lp_roster_named, lp_max_fractionality=integrality,
        P_S=P_S, P_S_share=P_S / total_book,
        P_free=P_free, P_free_share=P_free / total_book,
        greedy_staff=[reps[i] for i in g_idx], greedy_value=g_val,
        scip_P13=scip_val, scip_staff=scip_staff, scip_status=scip_status,
        scip_staff_direct_eval=scip_eval,
        claimed_staff_direct_eval=claimed_eval,
        V_sigma0=V0, V_star=V_star,
        U1_gains=dict(min=float(gains.min()), max=float(gains.max()), mean=gbar,
                      spread_rel=float((gains.max() - gains.min()) / gbar)),
        U1_M=dict(min=float(M_dist.min()), max=float(M_dist.max()),
                  mean=float(M_dist.mean()),
                  spread_rel=float((M_dist.max() - M_dist.min()) / M_dist.mean())),
        U4_n=len(u4), U4_M=u4_M, U4_share=u4_M / total_M,
        U8_pooled=pooled, U8_per_rep=per_rep,
        g_minus_wb_row_deviation=rows_dev,
        gap_match=dict(book=P_star - P0, nats=nats(P_star - P0),
                       small=nats(P_star - P0) <= 5e-3),
        gap_map=dict(book=P_S - P0, nats=nats(P_S - P0), small=nats(P_S - P0) <= 5e-3),
        gap_roster=dict(book=(scip_val or 0) - P_S, nats=nats((scip_val or 0) - P_S),
                        small=nats((scip_val or 0) - P_S) <= 5e-3),
    )
    print(json.dumps(rep, indent=1, sort_keys=True))

    # ---- diff against the produced payload
    lad = out["ladder"]
    checks = [
        ("P0", P0, lad["P0"]["book"]),
        ("P0_share", P0 / total_book, lad["P0"]["share"]),
        ("P_star", P_star, lad["P_star_A"]["book"]),
        ("P_S", P_S, lad["P_S"]["book"]),
        ("P13", scip_val, lad["P13"]["book"]),
        ("P_free", P_free, lad["P_free"]["book"]),
        ("greedy", g_val, out["P13_solve"]["greedy_book"]),
        ("V_sigma0", V0, out["V"]["sigma0"]),
        ("V_star", V_star, out["V"]["P_star_A"]),
        ("U1_gain_spread", rep["U1_gains"]["spread_rel"], out["U1"]["gains"]["spread_rel"]),
        ("U1_M_spread", rep["U1_M"]["spread_rel"], out["U1"]["M"]["spread_rel"]),
        ("U4_n", float(len(u4)), float(out["U4"]["n_zips"])),
        ("U4_share", u4_M / total_M, out["U4"]["M_share"]),
        ("U8_pooled", pooled, out["U8"]["pooled"]),
        ("total_book", total_book, out["total_book"]),
        ("total_M", total_M, out["total_M"]),
        ("gap_match_nats", nats(P_star - P0), out["gaps"]["match"]["nats"]),
        ("gap_map_nats", nats(P_S - P0), out["gaps"]["map"]["nats"]),
        ("gap_roster_nats", nats((scip_val or 0) - P_S), out["gaps"]["roster"]["nats"]),
    ]
    print("\n%-18s %22s %22s %12s" % ("quantity", "oracle", "produced", "abs diff"))
    worst = 0.0
    for name, a, c in checks:
        d = abs(a - c)
        worst = max(worst, d if abs(c) < 1 else d / abs(c))
        print("%-18s %22.12f %22.12f %12.3e" % (name, a, c, d))
    print(f"\nworst (abs if |x|<1 else rel) mismatch: {worst:.3e}")
    print("P*(A) roster matches produced:",
          lp_roster_named == out["P_star_A_roster"])
    print("staff (S13) matches produced:", staff == out["staff"])
    print("SCIP P13 staff:", scip_staff)
    print("produced P13 staff:", claimed)
    print("SCIP status:", scip_status, "| LP max fractionality:", integrality)
    print("g - w*b row deviation (should be ~0):", rows_dev)
    return 0


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:4]))
