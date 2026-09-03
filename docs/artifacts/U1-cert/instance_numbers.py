"""U1-cert: every number quoted in `docs/MODEL_U1-cert.md` section 4, on the real instance.

Run from the worktree root:

    /Users/ntlee/projects/td/.venv/bin/python3 docs/artifacts/U1-cert/instance_numbers.py

Reads (read-only) `instance_descaled.json.gz` and
`battery/results/draw_k13_20260901/{draw.csv,metrics.json}` -- the committed k=13 draw,
seed 3.  Writes nothing.  Deterministic: proportional response starts from the uniform
allocation, so there is no seed; the only stochastic input anywhere in this unit is the toy's,
which this script does not use.

The EG value is reported as a **bracket** `[primal, dual]`: the primal is the objective at a
feasible fractional assignment (a lower bound by feasibility), the dual is the Lagrangian dual
value at the iterate's prices (an upper bound by weak duality, for any strictly positive p).
Neither half depends on the iteration having converged.
"""
from __future__ import annotations

import csv
import json
import math
import sys

import numpy as np

sys.path.insert(0, __file__.rsplit("/", 1)[0])
sys.path.insert(0, ".")
import eg  # noqa: E402
from td import channel, instance, model  # noqa: E402

INSTANCE = "instance_descaled.json.gz"
DRAW = "battery/results/draw_k13_20260901"
THETA, LAM = 0.40, 0.30
ITERS = 60_000


def utility_matrix(G, nodes, staff, filler="theta"):
    """`U[z, i]` in `td/channel.py::gain_matrix`'s unmasked convention (candidacy ignored)."""
    c1, c2 = 1.0 - LAM, THETA * (1.0 - LAM)
    c_free = {"theta": c2, "full": c1, "opportunity": LAM}[filler]
    idx = {r: i for i, r in enumerate(staff)}
    U = np.zeros((len(nodes), len(staff)))
    for j, z in enumerate(nodes):
        S = model.books(G, z)
        T = float(sum(S.values()))
        U[j, :] = c2 * T + c_free * model.free_book(G, z) + LAM * float(G.nodes[z]["M"])
        for r, s in S.items():
            i = idx.get(r)
            if i is not None:
                U[j, i] += (c1 - c2) * float(s)
    return U


def main():
    out = {}
    d = instance.load_descaled(INSTANCE)
    G = d.G
    nodes = sorted(G)
    M = np.array([float(G.nodes[z]["M"]) for z in nodes])
    n = len(nodes)
    T = float(M.sum())
    k = 13
    target = T / k
    out["n_zips"] = n
    out["total_M"] = T
    out["min_M"] = float(M.min())
    out["max_M"] = float(M.max())
    out["max_M_share"] = float(M.max() / T)
    out["ceiling_k_log_T_over_k"] = k * math.log(target)

    # ---- headroom: is u_i(z) <= M_z?  (the hypothesis that makes the ceiling bound V)
    for filler in ("theta", "full"):
        U_all = utility_matrix(G, nodes, sorted({r for z in nodes
                                                 for r in model.books(G, z)}), filler)
        out[f"max_u_over_M[{filler}]"] = float((U_all.max(axis=1) / M).max())

    # ---- the delivered coverage
    to_district = {row["zip"]: row["district"]
                   for row in csv.DictReader(open(f"{DRAW}/draw.csv"))}
    meta = json.load(open(f"{DRAW}/metrics.json"))
    res = channel.stage2(G, to_district, theta=THETA, lam=LAM)
    S13 = sorted(res["assignment"].values())
    assert S13 == sorted(meta["winner"]["assignment"].values())
    g_deliv = np.array([res["gains"][j] for j in res["districts"]])
    out["V_delivered"] = float(res["value"])
    out["V_delivered_metrics_json"] = float(meta["winner"]["stage2_value"])
    out["g_spread_rel_delivered"] = float((g_deliv.max() - g_deliv.min()) / g_deliv.mean())
    out["M_spread_rel_delivered"] = float(res["balance"]["spread_rel"])
    out["g_min_delivered"] = float(g_deliv.min())

    # ---- EG_{S13}: the fibre bound at the delivered roster
    U = utility_matrix(G, nodes, S13)
    X, p, gstar, prim, dual = eg.eg_solve(U, iters=ITERS)
    out["EG_S13_primal"] = prim
    out["EG_S13_dual"] = dual
    out["EG_S13_bracket_width"] = dual - prim
    out["EG_minus_V_delivered"] = dual - out["V_delivered"]
    out["ceiling_minus_EG"] = out["ceiling_k_log_T_over_k"] - prim
    out["ceiling_minus_V_delivered"] = out["ceiling_k_log_T_over_k"] - out["V_delivered"]
    out["EG_g_spread_rel"] = float((gstar.max() - gstar.min()) / gstar.mean())

    # ---- tau = 0 sanity: the fibre degenerates to the analytic ceiling, exactly
    U0 = np.tile(M[:, None], (1, k))
    _, p0, _, prim0, dual0 = eg.eg_solve(U0, iters=5_000)
    out["EG_tau0_primal"] = prim0
    out["EG_tau0_dual"] = dual0
    out["EG_tau0_dual_at_closed_form_prices"] = eg.eg_dual(U0, (k / T) * M)

    # ---- a vertex of the optimal face: the split zips, and the rounded integral coverage
    Xv = eg.eg_vertex(U, gstar)
    split = np.flatnonzero((Xv > 1e-9).sum(axis=1) >= 2)
    out["n_split_zips"] = int(len(split))
    out["split_zips"] = [nodes[i] for i in split]
    out["M_F_split_mass"] = float(M[split].sum())
    out["M_F_share_of_T"] = float(M[split].sum() / T)
    out["M_F_worst_case_top_k_minus_1"] = float(np.sort(M)[::-1][:k - 1].sum())
    out["M_F_worst_case_share_of_T"] = out["M_F_worst_case_top_k_minus_1"] / T
    lab = Xv.argmax(axis=1)
    g_r = np.array([U[lab == i, i].sum() for i in range(k)])
    m_r = np.array([M[lab == i].sum() for i in range(k)])
    out["V_rounded_vertex"] = float(np.log(g_r).sum())
    out["V_rounded_minus_V_delivered"] = out["V_rounded_vertex"] - out["V_delivered"]
    out["integrality_gap_measured"] = dual - out["V_rounded_vertex"]
    out["M_spread_rel_rounded"] = float((m_r.max() - m_r.min()) / m_r.mean())
    out["M_max_dev_rel_rounded"] = float(np.abs(m_r - target).max() / target)

    # ---- P3's bounds on the *value* of the integrality gap
    L = (U[split, :] * Xv[split, :]).sum(axis=0)
    out["P3_bound_tight_per_agent"] = -float(np.log(1.0 - L / gstar).sum())
    out["max_L_over_g"] = float((L / gstar).max())
    mf = out["M_F_split_mass"]
    out["P3_bound_realised_MF"] = (-math.log(1 - mf / gstar.min())
                                   if mf < gstar.min() else math.inf)
    wc = out["M_F_worst_case_top_k_minus_1"]
    out["P3_bound_a_priori_top12"] = (-math.log(1 - wc / gstar.min())
                                      if wc < gstar.min() else math.inf)
    out["P3_a_priori_ratio_MF_over_gmin"] = wc / float(gstar.min())
    out["EG_g_min"] = float(gstar.min())

    # ---- the thresholds that would flip this unit's conclusions
    PREMIUM = 3.7                                # FRAME section 6: the incumbency swing, nats
    out["premium_swing_nats_FRAME"] = PREMIUM
    out["threshold_EG_R_useful"] = out["V_delivered"] + PREMIUM
    gm = float(gstar.min())
    out["threshold_MF_swamps_premium"] = gm * (1.0 - math.exp(-PREMIUM))
    out["threshold_MF_share_of_T"] = out["threshold_MF_swamps_premium"] / T
    out["ceiling_correction_export_rounding"] = k * math.log(out["max_u_over_M[theta]"])
    out["ceiling_correction_filler_full"] = k * math.log(out["max_u_over_M[full]"])
    out["ceiling_over_EG_tightness_factor"] = (out["ceiling_minus_V_delivered"]
                                               / out["EG_minus_V_delivered"])
    out["EG_gap_as_share_of_premium"] = out["EG_minus_V_delivered"] / PREMIUM
    out["g_spread_over_M_spread"] = (out["g_spread_rel_delivered"]
                                     / out["M_spread_rel_delivered"])

    for key, val in out.items():
        if isinstance(val, float):
            print(f"{key:38s} {val:.12g}")
        else:
            print(f"{key:38s} {val}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
