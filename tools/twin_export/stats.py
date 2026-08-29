"""stats.py -- `blocks(inst, cfg, agg)`: everything that goes into twin_stats.json.

One function, one `Instance` type.  It is run twice:

    * on the confidential instance with `Agg(enforce=True)`  -> the exported aggregates
    * on the synthetic twin with `Agg(enforce=False)`        -> `twin_check` (check.py)

so a statistic can never be defined differently for the two sides.

Blocks: scale, marginals, conditional, headroom, spatial, graph, territories, per_state,
radius.  Every number goes through `agg.put`, and every quantile through the windowed
order-statistic estimator in `agg.smoothed_quantiles`.
"""
from __future__ import annotations

import math

import numpy as np
import networkx as nx

from . import fit as F
from . import spatial as SP
from . import _territory_vendored as TV
from .agg import smoothed_quantiles, window_halfwidth

QLEVELS = (0.01, 0.05, 0.10, 0.25, 0.50, 0.75, 0.90, 0.95, 0.99)
PAIRQ = (0.10, 0.25, 0.50, 0.75, 0.90)
REPQ = (0.25, 0.50, 0.75, 0.90)
NDEC = 10


# ------------------------------------------------------------------------ helpers
def _logfield(v, floor_frac=1e-3):
    """log of a nonnegative field with zeros pinned to a floor below the positive median."""
    v = np.asarray(v, dtype=float)
    pos = v[v > 0]
    med = float(np.median(pos)) if pos.size else 1.0
    return np.log(np.maximum(v, floor_frac * med))


def _median_positive(v):
    v = np.asarray(v, dtype=float)
    pos = v[v > 0]
    return float(np.median(pos)) if pos.size else 1.0


def _gini(v):
    """Gini coefficient of a nonnegative vector (assumed already restricted to v > 0)."""
    v = np.sort(np.asarray(v, dtype=float))
    m = v.size
    s = float(v.sum())
    if m == 0 or s <= 0:
        return 0.0
    return float((2.0 * np.arange(1, m + 1) - m - 1).dot(v) / (m * s))


def _decile_index(M):
    """M-decile 0..9 by rank over ALL zips (zeros land in the bottom deciles)."""
    n = M.size
    order = np.argsort(np.argsort(M, kind="stable"), kind="stable")
    return np.minimum((order * NDEC) // max(n, 1), NDEC - 1)


def _rep_windowed(values, weights, qs, halfwidth=3):
    """Per-rep quantiles: mean of the rep-level statistics in a +/-halfwidth rank window.

    Support is the number of *ZCTAs* behind the window, not the number of reps, since that
    is what a disclosure would have to be inverted through.
    """
    v = np.asarray(values, dtype=float)
    w = np.asarray(weights, dtype=float)
    ok = np.isfinite(v)
    v, w = v[ok], w[ok]
    m = v.size
    if m == 0:
        return [None] * len(qs), 0
    order = np.argsort(v, kind="stable")
    vs, ws = v[order], w[order]
    out, sup = [], []
    for q in qs:
        r = int(round(float(q) * (m - 1)))
        lo, hi = max(0, r - halfwidth), min(m - 1, r + halfwidth)
        out.append(float(vs[lo:hi + 1].mean()))
        sup.append(int(ws[lo:hi + 1].sum()))
    return out, int(min(sup))


def _corr(a, b):
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    ok = np.isfinite(a) & np.isfinite(b)
    a, b = a[ok] - 0.0, b[ok]
    if a.size < 3:
        return float("nan"), int(a.size)
    a = a - a.mean()
    b = b - b.mean()
    den = math.sqrt(float(a.dot(a)) * float(b.dot(b)))
    return (float(a.dot(b) / den) if den > 0 else float("nan")), int(a.size)


def _contingency(la, lb, na, nb):
    C = np.zeros((na, nb), dtype=np.int64)
    np.add.at(C, (la, lb), 1)
    return C


def _ari_nmi(C):
    """Adjusted Rand index and normalised mutual information from a contingency table."""
    n = float(C.sum())
    if n <= 1:
        return float("nan"), float("nan")
    a = C.sum(axis=1).astype(float)
    b = C.sum(axis=0).astype(float)
    comb2 = lambda x: x * (x - 1.0) / 2.0
    sij = comb2(C.astype(float)).sum()
    sa, sb = comb2(a).sum(), comb2(b).sum()
    exp = sa * sb / comb2(n)
    mx = 0.5 * (sa + sb)
    ari = float((sij - exp) / (mx - exp)) if mx != exp else float("nan")

    pij = C.astype(float) / n
    pa, pb = a / n, b / n
    nz = pij > 0
    mi = float(np.sum(pij[nz] * np.log(pij[nz] / np.outer(pa, pb)[nz])))
    ha = float(-np.sum(pa[pa > 0] * np.log(pa[pa > 0])))
    hb = float(-np.sum(pb[pb > 0] * np.log(pb[pb > 0])))
    denom = 0.5 * (ha + hb)
    nmi = float(mi / denom) if denom > 0 else float("nan")
    return ari, nmi


def _best_match_jaccard(la, lb, na, nb):
    """Zip-weighted mean Jaccard of each A-rep's territory with its best-matching B-rep.

    This is the number `synth.rep_maps` bisects `alpha` against.
    """
    C = _contingency(la, lb, na, nb)
    sa = C.sum(axis=1).astype(float)
    sb = C.sum(axis=0).astype(float)
    tot, wsum = 0.0, 0.0
    for i in range(na):
        if sa[i] == 0:
            continue
        j = int(np.argmax(C[i]))
        inter = float(C[i, j])
        union = sa[i] + sb[j] - inter
        if union > 0:
            tot += sa[i] * (inter / union)
            wsum += sa[i]
    return (float(tot / wsum) if wsum > 0 else float("nan")), C


def _pieces_per_rep(G, labels, n_reps):
    out = np.zeros(n_reps, dtype=np.int64)
    size = np.zeros(n_reps, dtype=np.int64)
    for r in range(n_reps):
        idx = np.flatnonzero(labels == r)
        size[r] = idx.size
        if idx.size:
            out[r] = nx.number_connected_components(G.subgraph(idx.tolist()))
    return out, size


# ---------------------------------------------------------------------- the blocks
def prepare(inst, cfg):
    """Divide M, A and B by ONE common number when --strip-scale: the median positive M.

    A common divisor, not three separate ones.  Dividing each column by its own median
    would silently rescale A relative to M, which destroys every cross-column statistic --
    the A/M share curves and, worse, the headroom slack M - max(A + theta B, B + theta A),
    which would come out negative on data that satisfies the constraint exactly.  What
    `--strip-scale` is for is removing the *absolute dollar level*, and one divisor does
    that while leaving every ratio intact.
    """
    M, A, B = inst.M.astype(float), inst.A.astype(float), inst.B.astype(float)
    raw = dict(sum_M=float(M.sum()), sum_A=float(A.sum()), sum_B=float(B.sum()))
    div = 1.0
    if cfg.strip_scale:
        div = _median_positive(M)
        M = M / div
        A = A / div
        B = B / div
    return dict(M=M, A=A, B=B, raw=raw, scale=dict(M=div, A=div, B=div), divisor=div)


def blocks(inst, cfg, agg, tiger_edges=None, is_twin=False):
    """Fill `agg` with every exported statistic and return `agg.to_dict()`."""
    n = inst.n
    d = prepare(inst, cfg)
    M, A, B = d["M"], d["A"], d["B"]
    G = inst.G
    W = SP.row_normalized_adj(G, n)
    nbr = SP.neighbour_lists(G, n)
    rng = np.random.default_rng([cfg.seed, 991])

    # -------------------------------------------------------------------- scale
    with agg.block("scale"):
        sm, sa, sb = d["raw"]["sum_M"], d["raw"]["sum_A"], d["raw"]["sum_B"]
        sat = (sa + sb) / sm if sm > 0 else float("nan")
        if cfg.strip_penetration and math.isfinite(sat):
            sat = round(sat / 0.05) * 0.05
        agg.put("saturation", sat, n,
                note="(sum A + sum B) / sum M; a ratio, approved to leave")
        agg.put("book_ratio", (sa / sb) if sb > 0 else float("nan"), n)
        agg.put("p_active", float((M > 0).mean()), n)
        agg.put("p_glue", float((M <= 0).mean()), n)
        agg.put("p_untapped", float(((M > 0) & (A + B <= 0)).mean()), n)
        agg.put("p_a_active", float((A > 0).mean()), n)
        agg.put("p_b_active", float((B > 0).mean()), n)
        agg.put("gini_M", _gini(M[M > 0]), n,
                note="Gini coefficient of M over positive-M ZCTAs only (zero/glue ZCTAs "
                     "excluded, since they are a separate mechanism -- see p_glue -- not "
                     "part of the concentration of what IS active)")
        agg.put("scale_convention", "median_M", n,
                note="M, A and B were all divided by the median positive M")
        agg.put("strip_scale", bool(cfg.strip_scale), n)

    # ---------------------------------------------------------------- marginals
    with agg.block("marginals"):
        ratio_A = np.where(M > 0, A / np.maximum(M, 1e-300), 0.0)
        ratio_B = np.where(M > 0, B / np.maximum(M, 1e-300), 0.0)
        dec = _decile_index(M)
        fields = [("M", M), ("A", A), ("B", B),
                  ("A_over_M", ratio_A), ("B_over_M", ratio_B)]
        for name, v in fields:
            _marginal_block(agg, name, v, cfg)
        for name, v in (("A_over_M", ratio_A), ("B_over_M", ratio_B)):
            _residual_block(agg, name, v, dec, cfg)
        with agg.block("M"):
            agg.put("calibration_method", "bisect_on_probe", int((M > 0).sum()))

    # -------------------------------------------------------------- conditional
    with agg.block("conditional"):
        dec = _decile_index(M)
        counts = np.array([int((dec == k).sum()) for k in range(NDEC)])
        for tag, v in (("A", A), ("B", B)):
            mu, sd, pa, sup = [], [], [], []
            for k in range(NDEC):
                sel = dec == k
                nk = int(sel.sum())
                act = sel & (v > 0) & (M > 0)
                nact = int(act.sum())
                pa.append(float(nact) / nk if nk else float("nan"))
                if nact >= 2:
                    r = np.log(v[act] / M[act])
                    mu.append(float(r.mean()))
                    sd.append(float(r.std(ddof=1)))
                else:
                    mu.append(None)
                    sd.append(None)
                sup.append(nk)
            s = int(min(sup)) if sup else 0
            agg.put_vec("mean_log_%s_over_M" % tag, mu, s)
            agg.put_vec("sd_log_%s_over_M" % tag, sd, s)
            agg.put_vec("p_%s_active_by_decile" % tag, pa, s)
        agg.put_vec("decile_share_M",
                    [float(M[dec == k].sum() / max(M.sum(), 1e-300)) for k in range(NDEC)],
                    int(counts.min()))

        # within-decile dependence of the share on M: the decile ladder alone leaves the
        # share independent of M inside a decile, which biases sum(A)/sum(M) downward and
        # then forces a level correction onto the whole share distribution
        for tag, v in (("A", A), ("B", B)):
            act = (v > 0) & (M > 0)
            if act.sum() >= 8:
                lr = np.log(v[act] / M[act])
                lm = np.log(M[act])
                dk = dec[act]
                for k in range(NDEC):
                    sel = dk == k
                    if sel.sum() >= 2:
                        lr[sel] = lr[sel] - lr[sel].mean()
                        lm[sel] = lm[sel] - lm[sel].mean()
                cc, nn = _corr(lm, lr)
            else:
                cc, nn = float("nan"), int(act.sum())
            agg.put("corr_logM_log%s_over_M_given_decile" % tag, cc, nn)

        both = (A > 0) & (B > 0)
        c, nb_ = _corr(np.log(np.maximum(A[both], 1e-300)), np.log(np.maximum(B[both], 1e-300)))
        agg.put("corr_logA_logB", c, nb_)
        # partial correlation given the M-decile: correlate the within-decile residuals
        ra = np.log(np.maximum(A[both], 1e-300))
        rb = np.log(np.maximum(B[both], 1e-300))
        db = dec[both]
        for k in range(NDEC):
            s = db == k
            if s.sum() >= 2:
                ra[s] = ra[s] - ra[s].mean()
                rb[s] = rb[s] - rb[s].mean()
        pc, npc = _corr(ra, rb)
        agg.put("partial_corr_logA_logB_given_decile", pc, npc)

        aa, ab = (A > 0), (B > 0)
        cells = [int((aa & ab).sum()), int((aa & ~ab).sum()),
                 int((~aa & ab).sum()), int((~aa & ~ab).sum())]
        nz = [c for c in cells if c > 0]
        agg.put_vec("activity_table", [c / float(n) for c in cells],
                    int(min(nz)) if nz else 0,
                    note="P(A>0,B>0), P(A>0,B=0), P(A=0,B>0), P(A=0,B=0)")
        n11, n10, n01, n00 = cells
        den = math.sqrt(float((n11 + n10) * (n01 + n00) * (n11 + n01) * (n10 + n00)))
        agg.put("activity_corr_phi",
                ((n11 * n00 - n10 * n01) / den) if den > 0 else float("nan"),
                int(min(nz)) if nz else 0)

    # ----------------------------------------------------------------- headroom
    with agg.block("headroom"):
        for th in cfg.THETA_GRID:
            slack = M - np.maximum(A + th * B, B + th * A)
            key = "theta_%.2f" % th
            with agg.block(key):
                pos = M > 0
                ratio = np.where(pos, slack / np.maximum(M, 1e-300), np.nan)
                v, s = smoothed_quantiles(ratio[pos], QLEVELS, cfg.min_support)
                agg.put_vec("slack_ratio_q", v, s)
                good = slack > 0
                v2, s2 = smoothed_quantiles(np.log(slack[good]), QLEVELS, cfg.min_support)
                agg.put_vec("log_slack_q", v2, s2)
                agg.put("frac_violating", float((slack < 0).mean()), n)
                agg.put("frac_zero_slack", float((np.abs(slack) <= 1e-12).mean()), n)
        agg.put_vec("q_levels", list(QLEVELS), n)

    # ------------------------------------------------------------------ spatial
    with agg.block("spatial"):
        fields = [("M", _logfield(M)), ("A", _logfield(A)), ("B", _logfield(B)),
                  ("activity_M", (M > 0).astype(float)),
                  ("activity_A", (A > 0).astype(float)),
                  ("activity_B", (B > 0).astype(float))]
        for name, x in fields:
            mi = SP.morans_i(W, x)
            agg.put("moran_%s" % name, mi, n)
            if name in ("M", "A", "B", "activity_A", "activity_B", "activity_M"):
                agg.put("smoothing_w_%s" % name,
                        SP.fit_smoothing(W, mi, k=2, n=n) if np.isfinite(mi) else 0.0, n)
        # the decile-demeaned share residuals: what draw_shares has to reproduce
        dec_sp = _decile_index(M)
        for tag, v in (("A", A), ("B", B)):
            r = np.zeros(n)
            act = (v > 0) & (M > 0)
            if act.sum() >= 2:
                rr = np.log(v[act] / M[act])
                dk = dec_sp[act]
                for k in range(NDEC):
                    sel = dk == k
                    if sel.sum() >= 2:
                        rr[sel] = rr[sel] - rr[sel].mean()
                r[act] = rr
            mi = SP.morans_i(W, r)
            agg.put("moran_resid_%s" % tag, mi, n)
            agg.put("smoothing_w_resid_%s" % tag,
                    SP.fit_smoothing(W, mi, k=1, n=n) if np.isfinite(mi) else 0.0, n)
        for name, x in (("M", M), ("A", A), ("B", B)):
            rc, ne = SP.neighbour_rank_corr(G, x, n)
            agg.put("neighbour_rank_corr_%s" % name, rc, n)
            hop = SP.hop_rank_corr(G, x, hops=cfg.hop_max, n_sources=cfg.n_sources,
                                   max_pairs=cfg.max_pairs,
                                   rng=np.random.default_rng([cfg.seed, 7, ord(name[0])]),
                                   n=n)
            vals = [hop[h]["rho"] for h in range(1, cfg.hop_max + 1)]
            sup = min(hop[h]["n_pairs"] for h in range(1, cfg.hop_max + 1))
            agg.put_vec("rank_corr_by_hop_%s" % name, vals, int(sup))
            del ne

    # -------------------------------------------------------------------- graph
    with agg.block("graph"):
        deg = np.array([dgr for _, dgr in G.degree()], dtype=float)
        agg.put("n", n, n)
        agg.put("m", G.number_of_edges(), n)
        agg.put("mean_degree", float(deg.mean()) if deg.size else 0.0, n)
        maxd = 20
        hist = np.zeros(maxd + 2, dtype=np.int64)
        for x in deg.astype(int):
            hist[min(x, maxd + 1)] += 1
        merged = []
        acc = 0
        for i, c in enumerate(hist):
            acc += int(c)
            if acc >= cfg.min_support or i == len(hist) - 1:
                merged.append(acc)
                acc = 0
        if acc:
            merged[-1] += acc
        while len(merged) > 1 and merged[-1] < cfg.min_support:
            merged[-2] += merged.pop()
        agg.put_vec("degree_hist_counts", merged, int(min(merged)) if merged else 0,
                    note="degrees 0..%d then a tail bucket, adjacent bins merged up to "
                         "min_support" % maxd)
        comps = sorted((len(c) for c in nx.connected_components(G)), reverse=True)
        agg.put("n_components", len(comps), n)
        agg.put("largest_component_frac", comps[0] / float(n) if comps else 0.0, n)
        agg.put("n_articulation_points", len(list(nx.articulation_points(G))), n)
        bsz = sorted(len(c) for c in nx.biconnected_components(G))
        if bsz:
            v, _ = smoothed_quantiles(np.array(bsz, dtype=float), PAIRQ, cfg.min_support)
            agg.put_vec("bicomp_size_q", v, n,
                        note="graph structure only -- public TIGER geometry, not "
                             "confidential values")
        if inst.state is not None:
            st = np.array(inst.state)
            cross = sum(1 for u, v in G.edges if st[int(u)] != st[int(v)])
            agg.put("state_cross_share", cross / float(max(G.number_of_edges(), 1)), n)
        agg.put("no_polygon_count", int(getattr(inst, "no_polygon_count", 0)), n,
                note="ZCTAs present in the value tables with no polygon in the graph")
        if tiger_edges is not None:
            agg.put("edge_jaccard_vs_tiger", _edge_jaccard(inst, tiger_edges), n)

    # ------------------------------------------------------------- territories
    with agg.block("territories"):
        na = int(inst.rep_a.max()) + 1 if n else 0
        nb = int(inst.rep_b.max()) + 1 if n else 0
        agg.put("n_rep_a", na, n)
        agg.put("n_rep_b", nb, n)
        for tag, lab, nr in (("a", inst.rep_a, na), ("b", inst.rep_b, nb)):
            pieces, sizes = _pieces_per_rep(G, lab, nr)
            live = sizes > 0
            v, s = _rep_windowed(sizes[live], sizes[live], REPQ)
            agg.put_vec("zips_per_rep_%s_q" % tag, v, s)
            v, s = _rep_windowed(pieces[live], sizes[live], REPQ)
            agg.put_vec("pieces_per_rep_%s_q" % tag, v, s)
            agg.put("mean_pieces_per_rep_%s" % tag,
                    float(pieces[live].mean()) if live.any() else float("nan"), n)
        agg.put_vec("rep_q_levels", list(REPQ), n)

        jac, C = _best_match_jaccard(inst.rep_a, inst.rep_b, na, nb)
        ari, nmi = _ari_nmi(C)
        agg.put("misalignment_jaccard", jac, n)
        agg.put("misalignment_ari", ari, n)
        agg.put("misalignment_nmi", nmi, n)

        if inst.state is not None:
            st = np.array(inst.state)
            pur = []
            for tag, lab, nr in (("a", inst.rep_a, na), ("b", inst.rep_b, nb)):
                p = []
                for r in range(nr):
                    idx = lab == r
                    if idx.sum() == 0:
                        continue
                    _, cnt = np.unique(st[idx], return_counts=True)
                    p.append(float(cnt.max()) / float(idx.sum()))
                agg.put("rep_state_purity_%s" % tag,
                        float(np.mean(p)) if p else float("nan"), n)
                pur.extend(p)
            agg.put("rep_state_purity", float(np.mean(pur)) if pur else float("nan"), n)

        H = inst.to_schema_graph()
        for ms in cfg.MIN_SHARE_GRID:
            rows = TV.census(H, min_share=ms)
            key = "census_%.2f" % ms
            with agg.block(key):
                agg.put("n_components", len(rows), n)
                one = [r for r in rows if r["shape"] == "1-1 pair"]
                agg.put("share_1_1", float(sum(r["share"] for r in one)), n)
                agg.put("orphan_share", float(1.0 - sum(r["share"] for r in rows)), n)
                agg.put("dense_share",
                        float(sum(r["share"] for r in rows if r["shape"] != "1-1 pair")), n)
                sizes = []
                for r in one:
                    ra = r["reps_a"][0][1]
                    rb = r["reps_b"][0][1]
                    sizes.append(int(((inst.rep_a == ra) & (inst.rep_b == rb)).sum()))
                if sizes:
                    v, s = _rep_windowed(sizes, sizes, PAIRQ)
                    agg.put_vec("pair_size_q", v, s)
                    agg.put("n_pairs_1_1", len(sizes), n)

    # ---------------------------------------------------------------- per_state
    if inst.state is not None:
        _per_state(agg, inst, cfg, M, A, B)

    # ------------------------------------------------------------------- radius
    _radius(agg, inst, cfg, M, nbr)

    del rng
    return agg.to_dict()


# --------------------------------------------------------------------- sub-blocks
def _marginal_block(agg, name, v, cfg):
    v = np.asarray(v, dtype=float)
    pos = v[v > 0]
    with agg.block(name):
        agg.put("p_positive", float(pos.size) / max(v.size, 1), v.size)
        if pos.size < max(50, cfg.min_support):
            agg.put("prefer_dpln", False, v.size)
            agg.put("gof_note", "too few positive values to fit", v.size)
            return
        mf = F.fit_marginal(pos, name=name)
        _put_fit(agg, mf, cfg, pos.size)
        q, s = smoothed_quantiles(np.log(pos), QLEVELS, cfg.min_support)
        agg.put_vec("log_q", q, s)
        agg.put_vec("q_levels", list(QLEVELS), pos.size)
        cc = F.coarse_cdf(pos, n_bins=cfg.n_bins, min_support=cfg.min_support)
        with agg.block("coarse_cdf"):
            agg.put("n_bins", cc["n_bins"], pos.size)
            agg.put("n_bins_merged", cc["n_bins_merged"], pos.size)
            agg.put("min_bin_count", cc.get("min_bin_count", 0), pos.size)
            agg.put("top_bin_share", cc.get("top_bin_share", 0.0), pos.size)
            agg.put("tail_dominance_resolved",
                    bool(cc.get("tail_dominance_resolved", True)), pos.size)
            if not cc.get("tail_dominance_resolved", True):
                print("WARNING: %s: one ZCTA still supplies more than half of the top "
                      "coarse-CDF bin after merging every bin together -- its value is "
                      "recoverable from the bin mean.  Consider dropping the %s marginal."
                      % (name, name))
            agg.put_vec("bin_p", cc["bin_p"], int(cc.get("min_bin_count", 0)))
            agg.put_vec("bin_mean", cc["bin_mean"], int(cc.get("min_bin_count", 0)))


def _residual_block(agg, name, v, dec, cfg):
    """The decile-demeaned residual fit -- the one synth.py calibrates against."""
    v = np.asarray(v, dtype=float)
    act = v > 0
    if act.sum() < max(50, cfg.min_support):
        return
    r = np.log(v[act])
    dk = dec[act]
    for k in range(NDEC):
        s = dk == k
        if s.sum() >= 2:
            r[s] = r[s] - r[s].mean()
    with agg.block(name + "_resid"):
        mf = F.fit_marginal(np.exp(r), name=name + "_resid")
        _put_fit(agg, mf, cfg, int(act.sum()))
        q, s = smoothed_quantiles(r, QLEVELS, cfg.min_support)
        agg.put_vec("log_q", q, s)
        agg.put("use_for_calibration", "residual", int(act.sum()))
        cc = F.coarse_cdf(np.exp(r), n_bins=cfg.n_bins, min_support=cfg.min_support)
        with agg.block("coarse_cdf"):
            agg.put("n_bins", cc["n_bins"], int(act.sum()))
            agg.put("n_bins_merged", cc["n_bins_merged"], int(act.sum()))
            agg.put("min_bin_count", cc.get("min_bin_count", 0), int(act.sum()))
            agg.put("top_bin_share", cc.get("top_bin_share", 0.0), int(act.sum()))
            agg.put_vec("bin_p", cc["bin_p"], int(cc.get("min_bin_count", 0)))
            agg.put_vec("bin_mean", cc["bin_mean"], int(cc.get("min_bin_count", 0)))


def _put_fit(agg, mf, cfg, sup):
    ln = mf.get("lognormal")
    if ln:
        with agg.block("lognormal"):
            for k in ("mu", "sigma", "loglik", "ks", "ad"):
                agg.put(k, ln[k], sup)
    dp = mf.get("dpln")
    if dp:
        with agg.block("dpln"):
            for k in ("alpha", "beta", "nu", "tau", "loglik", "ks", "ad",
                      "n_starts", "start_spread_ll"):
                agg.put(k, dp[k], sup)
            agg.put("converged", bool(dp["converged"]), sup)
    agg.put("delta_loglik", mf.get("delta_loglik"), sup)
    agg.put("prefer_dpln", bool(mf.get("prefer_dpln", False)), sup)
    agg.put("gof_note", "ks/ad are statistics only, not p-values (parameters estimated "
                        "from the same sample)", sup)


def _per_state(agg, inst, cfg, M, A, B):
    st = np.array(inst.state)
    labels, counts = np.unique(st, return_counts=True)
    big = set(labels[counts >= cfg.min_state].tolist())
    key_of = dict((s, (s if s in big else "OTHER")) for s in labels.tolist())
    groups = {}
    for i, s in enumerate(st.tolist()):
        groups.setdefault(key_of[s], []).append(i)
    with agg.block("per_state"):
        agg.put("min_state", cfg.min_state, inst.n)
        agg.put("n_states_reported", len(big), inst.n)
        agg.put("n_states_merged_to_other", int(len(labels) - len(big)), inst.n)
        totM = float(M.sum())
        for name in sorted(groups):
            idx = np.array(groups[name], dtype=np.int64)
            nk = idx.size
            with agg.block(name):
                agg.put("n_zips", int(nk), nk)
                agg.put("share_M", float(M[idx].sum() / max(totM, 1e-300)), nk)
                agg.put("p_active", float((M[idx] > 0).mean()), nk)
                for tag, v in (("M", M[idx]), ("A_over_M",
                                               np.where(M[idx] > 0, A[idx] / np.maximum(M[idx], 1e-300), 0.0)),
                               ("B_over_M",
                                np.where(M[idx] > 0, B[idx] / np.maximum(M[idx], 1e-300), 0.0))):
                    p = v[v > 0]
                    if p.size < cfg.min_support:
                        continue
                    qs, s = smoothed_quantiles(np.log(p), (0.25, 0.50, 0.75), cfg.min_support)
                    agg.put("med_log_%s" % tag, qs[1], s)
                    agg.put("iqr_log_%s" % tag, float(qs[2] - qs[0]), s)


def _radius(agg, inst, cfg, M, nbr):
    """W11 territory-radius aggregates: how far a rep's zips are from the rep's centre."""
    n = inst.n
    have_km = bool(cfg.radius_km and inst.has_coords())
    with agg.block("radius"):
        agg.put("km_reported", bool(have_km), n)
        if have_km:
            e = list(inst.G.edges)
            if e:
                iu = np.array([int(u) for u, _ in e])
                iv = np.array([int(v) for _, v in e])
                dkm = SP.haversine_km(inst.lon[iu], inst.lat[iu], inst.lon[iv], inst.lat[iv])
                v, s = smoothed_quantiles(dkm, (0.50,), cfg.min_support)
                agg.put("median_adjacent_km", v[0], s)
        for tag, lab in (("a", inst.rep_a), ("b", inst.rep_b)):
            nr = int(lab.max()) + 1 if n else 0
            hop_mean, hop_p90, km_mean, km_p90, sizes = [], [], [], [], []
            for r in range(nr):
                idx = np.flatnonzero(lab == r)
                if idx.size == 0:
                    continue
                sizes.append(idx.size)
                w = M[idx]
                if w.sum() <= 0:
                    w = np.ones_like(w)
                if have_km:
                    clon = float(np.average(inst.lon[idx], weights=w))
                    clat = float(np.average(inst.lat[idx], weights=w))
                    dk = SP.haversine_km(inst.lon[idx], inst.lat[idx], clon, clat)
                    base = int(idx[int(np.argmin(dk))])
                    km_mean.append(float(np.average(dk, weights=w)))
                    km_p90.append(float(np.quantile(dk, 0.90)))
                else:
                    base = int(idx[int(np.argmax(M[idx]))])
                dist = SP.bfs_levels(nbr, base, 64)
                hops = np.array([dist.get(int(i), 64) for i in idx], dtype=float)
                hop_mean.append(float(np.average(hops, weights=w)))
                hop_p90.append(float(np.quantile(hops, 0.90)))
            if not sizes:
                continue
            for nm, vals in (("hop_mean", hop_mean), ("hop_p90", hop_p90),
                             ("km_mean", km_mean), ("km_p90", km_p90)):
                if not vals:
                    continue
                v, s = _rep_windowed(vals, sizes, REPQ)
                agg.put_vec("%s_%s_q" % (nm, tag), v, s)
        agg.put_vec("q_levels", list(REPQ), n)


def _edge_jaccard(inst, tiger_edges):
    mine = set()
    for u, v in inst.G.edges:
        a, b = inst.z[int(u)], inst.z[int(v)]
        mine.add((min(a, b), max(a, b)))
    zset = set(inst.z)
    theirs = set()
    for u, v in tiger_edges:
        a, b = str(u), str(v)
        if a in zset and b in zset:
            theirs.add((min(a, b), max(a, b)))
    union = mine | theirs
    return float(len(mine & theirs)) / len(union) if union else 1.0
