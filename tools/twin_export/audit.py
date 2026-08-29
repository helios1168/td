"""audit.py -- the privacy sign-off table.

The whole export rests on one contrast, and this module is how the user checks it before
anything leaves:

    individual level    real vs twin, ZCTA by ZCTA.  These must be WEAK.  If they are
                        strong, the twin is a thin disguise over confidential values.
    neighbourhood level real vs twin, after averaging over a 3-hop neighbourhood, plus the
                        Moran / hop-correlation / decile-share structure.  These must be
                        STRONG -- they are the reason the twin is worth exporting at all.

`sigma_effective` inverts the measured Spearman back through rho = 1/sqrt(1+12 sigma^2), so
the user can confirm the jitter actually applied is the jitter they asked for.
"""
from __future__ import annotations

import math

import numpy as np
from scipy.stats import rankdata

from . import spatial as SP
from .synth import rho_attenuation, sigma_from_rho, jitter_ranks

FIELDS = ("M", "A", "B")


def _lognorm(v):
    v = np.asarray(v, dtype=float)
    pos = v[v > 0]
    med = float(np.median(pos)) if pos.size else 1.0
    return np.log(np.maximum(v, 1e-3 * med) / med)


def _pearson(a, b):
    a = np.asarray(a, float) - np.mean(a)
    b = np.asarray(b, float) - np.mean(b)
    den = math.sqrt(float(a.dot(a)) * float(b.dot(b)))
    return float(a.dot(b) / den) if den > 0 else float("nan")


def _spearman(a, b):
    return _pearson(rankdata(a), rankdata(b))


def _exact_rank_band(M_real, sigma, cfg, n_rep=20):
    """Monte-Carlo band for the number of ZCTAs whose rank survives the jitter untouched."""
    n = M_real.size
    counts = []
    r0 = np.argsort(np.argsort(M_real, kind="stable"), kind="stable")
    for k in range(n_rep):
        rng = np.random.default_rng([cfg.seed, 9001, k])
        r1 = jitter_ranks(M_real, sigma, rng)
        counts.append(int((r0 == r1).sum()))
    c = np.sort(np.array(counts, dtype=float))
    return dict(mc_mean=float(c.mean()),
                mc_p05=float(c[max(0, int(0.05 * (len(c) - 1)))]),
                mc_p95=float(c[int(0.95 * (len(c) - 1))]), mc_reps=int(n_rep))


def _local_rank_agreement(G, real, twin, n, rng, k_hop=3, n_sample=300):
    """Mean Spearman of real vs twin *within* each sampled node's k-hop neighbourhood."""
    nbr = SP.neighbour_lists(G, n)
    srcs = rng.permutation(n)[:min(n_sample, n)]
    vals = []
    for s in srcs:
        d = SP.bfs_levels(nbr, int(s), k_hop)
        idx = np.fromiter(d.keys(), dtype=np.int64)
        if idx.size < 8:
            continue
        a, b = real[idx], twin[idx]
        if np.ptp(a) == 0 or np.ptp(b) == 0:
            continue
        vals.append(_spearman(a, b))
    return float(np.mean(vals)) if vals else float("nan")


def audit(inst, twin, cfg, twin_stats=None, real_stats=None, n_local=300):
    """Build the audit dict.  `twin` is the dict returned by `synth.build_twin`."""
    n = inst.n
    G = inst.G
    W = SP.row_normalized_adj(G, n)
    rng = np.random.default_rng([cfg.seed, 4242])
    rho_expected = rho_attenuation(cfg.rank_sigma)

    per_field = {}
    for name in FIELDS:
        real = getattr(inst, name)
        tw = twin[name]
        lr, lt = _lognorm(real), _lognorm(tw)
        rr, rt = rankdata(real), rankdata(tw)
        drank = np.abs(rr - rt) / float(n)
        with np.errstate(divide="ignore", invalid="ignore"):
            dlog = np.abs(lr - lt)
        live = (real > 0) & (tw > 0)          # zeros match by design, not by leakage
        act_r, act_t = real > 0, tw > 0
        agree = float((act_r == act_t).mean())
        p_r, p_t = float(act_r.mean()), float(act_t.mean())
        chance = p_r * p_t + (1 - p_r) * (1 - p_t)
        sp = _spearman(real, tw)
        row = dict(
            # ---- individual level (must be weak) -----------------------------
            pearson_log=_pearson(lr, lt),
            spearman=sp,
            share_within_1pct_rank=float((drank <= 0.01).mean()),
            share_within_5pct_rank=float((drank <= 0.05).mean()),
            share_within_1pct_value=float((dlog[live] <= math.log(1.01)).mean())
            if live.any() else 0.0,
            share_within_5pct_value=float((dlog[live] <= math.log(1.05)).mean())
            if live.any() else 0.0,
            exact_rank_matches=int((np.argsort(np.argsort(real, kind="stable"),
                                               kind="stable")
                                    == np.argsort(np.argsort(tw, kind="stable"),
                                                  kind="stable")).sum()),
            exact_value_matches=int((dlog[live] < 1e-12).sum()),
            activity_flag_agreement=agree,
            activity_chance_baseline=chance,
            local_rank_agreement_3hop=_local_rank_agreement(G, real, tw, n, rng,
                                                            n_sample=n_local),
            # ---- neighbourhood level (must be strong) ------------------------
            corr_3hop_neighbourhood=_pearson(SP.khop_mean(W, lr, 3),
                                             SP.khop_mean(W, lt, 3)),
            moran_real=SP.morans_i(W, lr),
            moran_twin=SP.morans_i(W, lt),
        )
        hop_r = SP.hop_rank_corr(G, real, hops=cfg.hop_max, n_sources=min(500, n),
                                 rng=np.random.default_rng([cfg.seed, 55, 1]), n=n)
        hop_t = SP.hop_rank_corr(G, tw, hops=cfg.hop_max, n_sources=min(500, n),
                                 rng=np.random.default_rng([cfg.seed, 55, 1]), n=n)
        row["rank_corr_by_hop_real"] = [hop_r[h]["rho"] for h in range(1, cfg.hop_max + 1)]
        row["rank_corr_by_hop_twin"] = [hop_t[h]["rho"] for h in range(1, cfg.hop_max + 1)]
        if name == "M":
            row.update(_exact_rank_band(inst.M, cfg.rank_sigma, cfg))
            row["sigma_effective"] = sigma_from_rho(max(min(abs(sp), 0.999999), 1e-6))
        per_field[name] = row

    dsr = _decile_share(inst.M)
    dst = _decile_share(twin["M"])
    ind = max(abs(per_field[f]["spearman"]) for f in FIELDS)
    nbh = min(per_field[f]["corr_3hop_neighbourhood"] for f in FIELDS)
    # M is the field the rank jitter acts on, so it is the one whose neighbourhood structure
    # is meant to survive; A and B are redrawn from the aggregates conditional on M, so a
    # low individual *and* neighbourhood correlation for them is the design working, not a
    # defect.  The usefulness test is therefore on M.
    nbh_M = per_field["M"]["corr_3hop_neighbourhood"]
    out = dict(
        fields=per_field,
        decile_share_M_real=dsr,
        decile_share_M_twin=dst,
        rank_sigma=cfg.rank_sigma,
        rho_expected=rho_expected,
        rho2_expected=rho_expected ** 2,
        sigma_effective=per_field["M"]["sigma_effective"],
        individual_max_spearman=float(ind),
        neighbourhood_min_corr=float(nbh),
        neighbourhood_corr_M=float(nbh_M),
        verdict=_verdict(ind, nbh_M, per_field),
        headroom=twin.get("report", {}).get("headroom"),
        reps=twin.get("report", {}).get("reps"),
    )
    del twin_stats, real_stats
    return out


def _decile_share(M):
    M = np.asarray(M, dtype=float)
    n = M.size
    order = np.argsort(np.argsort(M, kind="stable"), kind="stable")
    dec = np.minimum((order * 10) // max(n, 1), 9)
    tot = max(float(M.sum()), 1e-300)
    return [float(M[dec == k].sum() / tot) for k in range(10)]


def _verdict(ind, nbh, per_field):
    zero_exact = all(per_field[f]["exact_value_matches"] == 0 for f in FIELDS)
    if not zero_exact:
        return "FAIL: some ZCTA kept an exact value -- do not export"
    if ind > 0.99:
        return "FAIL: individual-level Spearman above 0.99 -- the twin is a relabelling"
    if not np.isfinite(nbh) or nbh < 0.5:
        return ("WARN: the 3-hop neighbourhood correlation of M is %.3f (below 0.5) -- the "
                "twin is private but may not be a useful stand-in" % nbh)
    return ("OK: individual-level agreement is weak (max Spearman %.3f), neighbourhood-level "
            "structure survives (3-hop correlation of M %.3f)" % (ind, nbh))


# -------------------------------------------------------------------- printing
IND_KEYS = [("pearson_log", "Pearson on log"),
            ("spearman", "Spearman"),
            ("share_within_1pct_rank", "share within 1% rank"),
            ("share_within_5pct_rank", "share within 5% rank"),
            ("share_within_1pct_value", "share within 1% value"),
            ("share_within_5pct_value", "share within 5% value"),
            ("exact_rank_matches", "exact-rank matches"),
            ("exact_value_matches", "exact-value matches (must be 0)"),
            ("activity_flag_agreement", "activity-flag agreement"),
            ("activity_chance_baseline", "  ... chance baseline"),
            ("local_rank_agreement_3hop", "local rank agreement (3 hop)")]
NBH_KEYS = [("corr_3hop_neighbourhood", "3-hop neighbourhood-mean corr"),
            ("moran_real", "Moran's I  real"),
            ("moran_twin", "Moran's I  twin")]


def format_audit(a):
    L = []
    L.append("PRIVACY AUDIT -- individual level (want WEAK) vs neighbourhood level (want STRONG)")
    L.append("")
    hdr = "%-34s %12s %12s %12s" % ("", "M", "A", "B")
    L.append(hdr)
    L.append("-" * len(hdr))
    L.append("individual level")
    for k, lab in IND_KEYS:
        L.append("  %-32s %s" % (lab, _cells(a, k)))
    L.append("")
    L.append("neighbourhood level")
    for k, lab in NBH_KEYS:
        L.append("  %-32s %s" % (lab, _cells(a, k)))
    L.append("  %-32s %s" % ("rank corr by hop, real",
                             _vec(a["fields"]["M"]["rank_corr_by_hop_real"])))
    L.append("  %-32s %s" % ("rank corr by hop, twin",
                             _vec(a["fields"]["M"]["rank_corr_by_hop_twin"])))
    L.append("")
    L.append("  %-32s %s" % ("decile share of M, real", _vec(a["decile_share_M_real"])))
    L.append("  %-32s %s" % ("decile share of M, twin", _vec(a["decile_share_M_twin"])))
    mm = a["fields"]["M"]
    L.append("")
    L.append("  exact-rank matches for M: %d observed; Monte-Carlo band under sigma=%.3f "
             "is [%.0f, %.0f] (mean %.1f over %d draws)"
             % (mm["exact_rank_matches"], a["rank_sigma"], mm["mc_p05"], mm["mc_p95"],
                mm["mc_mean"], mm["mc_reps"]))
    L.append("  rank jitter: sigma requested %.3f -> rho %.4f (rho^2 %.4f); "
             "sigma_effective from the measured Spearman %.4f"
             % (a["rank_sigma"], a["rho_expected"], a["rho2_expected"],
                a["sigma_effective"]))
    L.append("")
    L.append("VERDICT: " + a["verdict"])
    return "\n".join(L)


def _cells(a, key):
    out = []
    for f in FIELDS:
        v = a["fields"][f].get(key)
        if v is None:
            out.append("%12s" % "--")
        elif isinstance(v, int):
            out.append("%12d" % v)
        else:
            out.append("%12.4f" % float(v))
    return " ".join(out)


def _vec(v, fmt="%.3f"):
    return " ".join((fmt % float(x)) if x is not None and np.isfinite(float(x)) else " nan"
                    for x in v)


def sigma_sweep(inst, real_stats, cfg, sigmas, build_twin_fn, make_instance_fn):
    """Rerun the synthesis at each sigma and report the audit contrast for each."""
    rows = []
    for s in sigmas:
        c = _clone(cfg, rank_sigma=float(s))
        tw = build_twin_fn(inst, real_stats, c)
        a = audit(inst, tw, c, n_local=120)
        rows.append(dict(sigma=float(s),
                         rho=rho_attenuation(float(s)),
                         spearman_M=a["fields"]["M"]["spearman"],
                         spearman_A=a["fields"]["A"]["spearman"],
                         within_5pct_rank_M=a["fields"]["M"]["share_within_5pct_rank"],
                         exact_value_matches=sum(a["fields"][f]["exact_value_matches"]
                                                 for f in FIELDS),
                         corr_3hop_M=a["fields"]["M"]["corr_3hop_neighbourhood"],
                         moran_twin_M=a["fields"]["M"]["moran_twin"],
                         moran_real_M=a["fields"]["M"]["moran_real"],
                         individual_max_spearman=a["individual_max_spearman"],
                         neighbourhood_min_corr=a["neighbourhood_min_corr"]))
    del make_instance_fn
    return rows


def format_sweep(rows):
    L = ["sigma sweep -- pick the smallest sigma whose individual column you are comfortable with",
         "",
         "%7s %7s %10s %10s %12s %12s %12s" % ("sigma", "rho", "Spearman M", "Spearman A",
                                               "w/in 5% rk", "3hop corr M", "Moran twin")]
    L.append("-" * 76)
    for r in rows:
        L.append("%7.3f %7.4f %10.4f %10.4f %12.4f %12.4f %12.4f"
                 % (r["sigma"], r["rho"], r["spearman_M"], r["spearman_A"],
                    r["within_5pct_rank_M"], r["corr_3hop_M"], r["moran_twin_M"]))
    L.append("-" * 76)
    L.append("real Moran's I of log M: %.4f" % rows[0]["moran_real_M"] if rows else "")
    return "\n".join(L)


def _clone(cfg, **kw):
    import copy
    c = copy.copy(cfg)
    for k, v in kw.items():
        setattr(c, k, v)
    return c
