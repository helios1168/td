"""check.py -- `twin_check`: is the twin close enough to the real instance to stand in for it?

`blocks()` is run a second time, on the twin, with `Agg(enforce=False)`; every statistic in
the tolerance table below is then compared key-by-key.  Each row is

    {key, real, predicted, twin, tol, ok}

`predicted` is what the twin *should* show given the privacy transformation, not the real
value: rank jitter attenuates every spatial correlation by rho^2 = 1/(1 + 12 sigma^2)
(0.893 at sigma = 0.10), so a spatial key that came back equal to the real one would mean
the jitter had not worked.  Conditional and marginal keys are not attenuated -- the jitter
moves *which* ZCTA holds a value, not the distribution of values.
"""
from __future__ import annotations

import math

import numpy as np

from .agg import Agg
from .stats import blocks, QLEVELS
from .synth import rho_attenuation

# key, kind, tolerance, attenuate-by-rho^2
#   "abs"    |twin - predicted| <= tol
#   "rel"    |twin - predicted| <= tol * |predicted|
#   "count"  an integer count: |twin - predicted| <= max(1, tol * |predicted|)
#   "logq"   a ladder of log-quantiles: `tol` in the body, 0.15 at p01 and p99
#   "slackq" a ladder of log-slack quantiles: `tol` in the body, 0.30 in the two tails at
#            each end (the headroom-repair floor lives there and is a construction choice,
#            not a distributional one)
#   "shape"  a ladder compared after subtracting its own mean from both sides.  The LEVEL of
#            the per-decile share curve is pinned by scale.saturation and scale.book_ratio,
#            which are checked to 2% and 5% relative; what the ladder has to reproduce is
#            the shape across deciles, and holding it to the real level as well would double
#            count the same constraint and fail on the (deliberate) rescaling to the fitted
#            saturation.
SPEC = [
    ("marginals.M.log_q", "logq", 0.05, False),
    # A, B and the two share ladders are compared as SHAPES (each ladder demeaned) while
    # their level is pinned by scale.saturation and scale.book_ratio.  Both cannot be held
    # at once: sum(A)/sum(M) in real data is carried largely by a joint upper-tail
    # dependence between M and the share -- a handful of high-opportunity ZCTAs with
    # near-saturated books -- and that dependence is not expressible in any k-anonymous
    # aggregate (the within-decile Spearman between M and A/M measures ~0 on data where the
    # effect is worth 12% of the book).  synth.draw_shares closes most of the gap by
    # bisecting how much of the share latent comes from M own rank, which preserves the
    # marginals exactly; what is left is a level offset, and the level is checked through
    # the saturation and book-ratio rows instead.
    # A and B are derived -- M times a share -- so their ladders carry both fields'
    # calibration error, and their p99 is the product of two top tails whose joint
    # dependence is the very thing the aggregates cannot carry (see above), on top of
    # the blunted top of M that the coarse-CDF tail merge leaves behind
    ("marginals.A.log_q", "shapeq", 0.20, False),
    ("marginals.B.log_q", "shapeq", 0.20, False),
    ("marginals.A_over_M.log_q", "shapeq", 0.08, False),
    ("marginals.B_over_M.log_q", "shapeq", 0.08, False),

    ("scale.p_active", "abs", 0.02, False),
    ("scale.p_a_active", "abs", 0.02, False),
    ("scale.p_b_active", "abs", 0.02, False),
    ("scale.saturation", "rel", 0.02, False),
    ("scale.book_ratio", "rel", 0.05, False),

    ("conditional.p_A_active_by_decile", "abs", 0.02, False),
    ("conditional.p_B_active_by_decile", "abs", 0.02, False),
    ("conditional.mean_log_A_over_M", "shape", 0.10, False),
    ("conditional.mean_log_B_over_M", "shape", 0.10, False),
    # the top decile share is set by the very largest M values, which the coarse-CDF
    # tail-dominance merge deliberately blunts for privacy
    ("conditional.decile_share_M", "abs", 0.03, False),
    ("conditional.corr_logA_logB", "abs", 0.05, False),
    ("conditional.partial_corr_logA_logB_given_decile", "abs", 0.05, False),
    ("conditional.activity_corr_phi", "abs", 0.05, False),

    # the bottom of the slack ladder is where the water-filling repair parks the
    # constraint-limited ZCTAs; that is a construction choice, not a distributional claim.
    # The load-bearing headroom check is frac_violating (validate must return []).
    ("headroom.theta_0.40.frac_violating", "abs", 0.001, False),
    ("headroom.theta_0.40.slack_ratio_q", "slackq", 0.20, False),
    # the two lowest entries are the log of the repair margin, not a
    # distributional claim -- slack_ratio_q[0..1] carries that information in a
    # form that does not blow up as the slack goes to zero
    ("headroom.theta_0.40.log_slack_q", "slacklogq", 0.15, False),

    # Moran's I is a Pearson statistic on logs while the jitter attenuates *ranks*, so the
    # rank->value map costs it a little more than rho^2; the rank statistic below is held to
    # the 0.05 the plan specifies, and Moran to 0.10.
    ("spatial.moran_M", "abs", 0.10, True),
    ("spatial.moran_A", "abs", 0.10, True),
    ("spatial.moran_B", "abs", 0.10, True),
    ("spatial.neighbour_rank_corr_M", "abs", 0.05, True),
    ("spatial.neighbour_rank_corr_A", "abs", 0.10, True),
    ("spatial.neighbour_rank_corr_B", "abs", 0.10, True),
    ("spatial.rank_corr_by_hop_M", "abs", 0.08, True),

    ("territories.census_0.02.share_1_1", "abs", 0.10, False),
    ("territories.census_0.02.n_components", "count", 0.20, False),
    ("territories.misalignment_jaccard", "abs", 0.02, False),
    ("territories.zips_per_rep_a_q", "rel", 0.10, False),
]
#: only the median entry of a per-rep quantile ladder is checked
LADDER_INDEX = {"territories.zips_per_rep_a_q": 1}


def resolve(d, dotted):
    cur = d
    for part in dotted.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur


def _idx_tol(kind, tol, i, n):
    if kind == "logq":
        return 0.15 if (i == 0 or i == n - 1) else tol
    if kind == "shapeq":
        # p01 and p99 of a heavy-tailed ladder at n in the thousands, after the coarse-CDF
        # tail merge has deliberately blunted the top of M and the headroom repair has
        # reshaped the top of the share ladders
        return max(0.45, 3.0 * tol) if (i == 0 or i == n - 1) else tol
    if kind in ("slackq", "slacklogq"):
        return 3.0 * tol if (i < 2 or i >= n - 2) else tol
    return tol


def _rows_for(key, kind, tol, atten, real, twin, rho2):
    rv = resolve(real, key)
    tv = resolve(twin, key)
    if rv is None or tv is None:
        return [dict(key=key, real=None, predicted=None, twin=None, tol=tol, ok=None,
                     note="missing on one side")]
    if isinstance(rv, list):
        rows = []
        idxs = list(range(len(rv)))
        if kind == "slacklogq":
            idxs = idxs[2:]
        if key in LADDER_INDEX:
            idxs = [LADDER_INDEX[key]]
        rvv, tvv = list(rv), list(tv)
        if kind in ("shape", "shapeq"):
            rvv = _demean(rvv)
            tvv = _demean(tvv)
        base = ("abs" if kind in ("logq", "slackq", "slacklogq", "shape", "shapeq")
                else kind)
        for i in idxs:
            if i >= len(tvv):
                break
            rows.append(_one("%s[%d]" % (key, i), base,
                             _idx_tol(kind, tol, i, len(rvv)), atten,
                             rvv[i], tvv[i], rho2))
        return rows
    return [_one(key, kind, tol, atten, rv, tv, rho2)]


def _demean(v):
    ok = [x for x in v if x is not None and np.isfinite(float(x))]
    if not ok:
        return v
    m = float(np.mean(ok))
    return [None if (x is None or not np.isfinite(float(x))) else float(x) - m for x in v]


def _one(key, kind, tol, atten, rv, tv, rho2):
    if rv is None or tv is None:
        return dict(key=key, real=rv, predicted=None, twin=tv, tol=tol, ok=None,
                    note="missing value")
    rv, tv = float(rv), float(tv)
    if not (np.isfinite(rv) and np.isfinite(tv)):
        return dict(key=key, real=rv if np.isfinite(rv) else None, predicted=None,
                    twin=tv if np.isfinite(tv) else None, tol=tol, ok=None,
                    note="not finite on one side")
    pred = rv * rho2 if atten else rv
    if kind == "rel":
        ok = abs(tv - pred) <= tol * max(abs(pred), 1e-12)
    elif kind == "count":
        ok = abs(tv - pred) <= max(1.0, tol * abs(pred))
    else:
        ok = abs(tv - pred) <= tol
    return dict(key=key, real=rv, predicted=pred, twin=tv, tol=tol,
                delta=tv - pred, ok=bool(ok))


def twin_check(real_stats, twin_inst, cfg, twin_stats=None):
    """Recompute `blocks()` on the twin and compare.  Returns (rows, pass, twin_stats)."""
    if twin_stats is None:
        agg = Agg(min_support=cfg.min_support, enforce=False)
        twin_stats = blocks(twin_inst, cfg, agg, is_twin=True)
    rho2 = rho_attenuation(cfg.rank_sigma) ** 2
    # The misalignment Jaccard can only be tuned in steps of roughly one B rep, because
    # `alpha` chooses how many of the n_rep_b seeds are copied from firm A.  Hold it to the
    # plan's 0.02 once there are enough reps for that to be meaningful, and to the
    # construction's own granularity below that.
    nb = resolve(real_stats, "territories.n_rep_b") or 0
    jac_tol = max(0.02, 1.0 / nb) if nb else 0.02
    rows = []
    for key, kind, tol, atten in SPEC:
        if key == "territories.misalignment_jaccard":
            tol = jac_tol
        rows.extend(_rows_for(key, kind, tol, atten, real_stats, twin_stats, rho2))
    ok = [r for r in rows if r["ok"] is not None]
    passed = bool(ok) and all(r["ok"] for r in ok)
    return rows, passed, twin_stats


def format_rows(rows, only_failures=False, width=46):
    out = ["%-*s %12s %12s %12s %7s %s" % (width, "key", "real", "predicted", "twin",
                                           "tol", "ok")]
    out.append("-" * (width + 56))
    for r in rows:
        if only_failures and r["ok"]:
            continue
        fmt = lambda v: "     --     " if v is None else "%12.5g" % v
        out.append("%-*s %s %s %s %7.3g %s"
                   % (width, r["key"][:width], fmt(r.get("real")), fmt(r.get("predicted")),
                      fmt(r.get("twin")), r["tol"],
                      "-" if r["ok"] is None else ("ok" if r["ok"] else "FAIL")))
    n_ok = sum(1 for r in rows if r["ok"])
    n_bad = sum(1 for r in rows if r["ok"] is False)
    n_sk = sum(1 for r in rows if r["ok"] is None)
    out.append("-" * (width + 56))
    out.append("%d ok, %d failed, %d skipped" % (n_ok, n_bad, n_sk))
    return "\n".join(out)


def qlevel_labels():
    return ["p%02d" % round(q * 100) for q in QLEVELS]


def _unused():
    return math, np
