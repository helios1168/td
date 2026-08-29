"""synth.py -- build the synthetic twin from the aggregates.

The twin keeps what is public (ZCTA ids, the Rook edge list, state membership) and replaces
everything confidential (M, A, B, and the rep maps) with a fresh draw calibrated to the
aggregates in `twin_stats.json`.

Pipeline, in order (PLAN.md C.2):

    1  rank M, zeros at the bottom
    2  jitter the ranks:  r' = r + sigma*n*eps          (this is the privacy step)
    3  bottom 1-p_active -> M = 0; the rest by inverse coarse-CDF; rescale sum M = 40n/50
    4  activity fields for A and B: graph-smoothed Gaussians, per-decile thresholds,
       calibrated to the measured activity correlation
    5  log(A/M), log(B/M) from the per-decile mu/sd with the measured partial correlation,
       eps_A graph-smoothed one step
    6  headroom repair: scale A, B down jointly until M >= max(A+theta*B, B+theta*A)
    7  rep maps: seeds proportional to M, multi-source BFS Voronoi, B seeds copying A's with
       probability alpha, alpha bisected to the measured misalignment Jaccard

**Every field is attenuated by rho^2 on purpose.**  Rank jitter attenuates the Spearman
correlation of M by rho = 1/sqrt(1 + 12*sigma^2) (0.945 at sigma = 0.10), and hence every
neighbour correlation by rho^2 (0.893).  The share and activity fields are smoothed to
rho^2 times *their* measured targets so the whole instance is attenuated uniformly -- which
is what makes `twin_check`'s prediction `predicted = rho^2 * real` well defined instead of
a fudge factor.

RNG: one named stream per stage, `default_rng([seed, tag])`, so changing one stage does not
move the others.
"""
from __future__ import annotations

import math

import numpy as np

from . import fit as F
from . import spatial as SP
from .stats import NDEC, _decile_index

TAG = dict(jitter=101, M=102, act=103, share=104, repa=105, repb=106, probe=107)


def rho_attenuation(sigma):
    """Spearman attenuation of a rank field under r' = r + sigma*n*eps."""
    return 1.0 / math.sqrt(1.0 + 12.0 * float(sigma) ** 2)


def sigma_from_rho(rho):
    rho = float(min(max(rho, 1e-6), 1.0 - 1e-12))
    return math.sqrt((1.0 / (rho * rho) - 1.0) / 12.0)


# ------------------------------------------------------------------- step 1 and 2
def jitter_ranks(M, sigma, rng, W=None, smooth_w=0.0, coarsen=None, swap_rounds=0):
    """Rank M (zeros first), add sigma*n*N(0,1) to the rank, return the new rank order."""
    M = np.asarray(M, dtype=float)
    n = M.size
    r = np.argsort(np.argsort(M, kind="stable"), kind="stable").astype(float)
    eps = rng.standard_normal(n)
    if smooth_w and W is not None:
        eps = SP.smooth_field(W, eps, k=1, w=float(smooth_w))
    rp = r + float(sigma) * n * eps
    if coarsen:
        k = dict(decile=10, percentile=100).get(str(coarsen))
        if k is None:
            raise ValueError("--coarsen must be 'decile' or 'percentile'")
        bucket = np.minimum((np.argsort(np.argsort(rp)) * k) // n, k - 1)
        rp = bucket.astype(float) * n / k + rng.random(n) * (n / float(k))
    if swap_rounds:
        order = np.argsort(rp, kind="stable")
        for _ in range(int(swap_rounds)):
            i = rng.integers(0, n - 1, size=n // 4)
            for a in i:
                order[a], order[a + 1] = order[a + 1], order[a]
        rp = np.empty(n)
        rp[order] = np.arange(n, dtype=float)
    return np.argsort(np.argsort(rp, kind="stable"), kind="stable")


# ------------------------------------------------------------------------- step 3
def draw_M(stats, new_rank, n, rng):
    """Zeros at the bottom, the rest by the inverse coarse-CDF; then sum M = 40n/50."""
    mblock = stats["marginals"]["M"]
    p_active = float(stats["scale"]["p_active"])
    q = F.quantile_fn_from_coarse(mblock["coarse_cdf"], _tail_fit(mblock))
    n_zero = int(round((1.0 - p_active) * n))
    M = np.zeros(n, dtype=float)
    active = new_rank >= n_zero
    k = int(active.sum())
    if k:
        u = (new_rank[active] - n_zero + 0.5) / float(k)
        M[active] = q(np.clip(u, 1e-9, 1 - 1e-9))
    tot = M.sum()
    if tot > 0:
        M *= (40.0 * n / 50.0) / tot
    return M


def _tail_fit(block):
    """Rebuild the `fit_marginal` shape the quantile function expects from a stats block."""
    if "lognormal" not in block:
        return None
    out = dict(prefer_dpln=bool(block.get("prefer_dpln", False)),
               lognormal=dict(block["lognormal"]))
    if "dpln" in block:
        out["dpln"] = dict(block["dpln"])
    return out


# ------------------------------------------------------------------------- step 4
def _threshold_by_decile(g, dec, p_active_by_decile, rng, live=None):
    """Turn a continuous field into an activity flag hitting P(active | decile) per decile.

    `p_active_by_decile` is P(A > 0 AND M > 0 | decile) -- the denominator is the whole
    decile, but only ZCTAs with opportunity can be candidates.  On a zero-inflated instance
    the bottom decile is mostly glue, so drawing candidates from the whole decile would put
    the flag on ZCTAs with M = 0, where it is then masked away.
    """
    act = np.zeros(g.size, dtype=bool)
    for k in range(NDEC):
        in_dec = dec == k
        n_dec = int(in_dec.sum())
        sel = np.flatnonzero(in_dec if live is None else (in_dec & live))
        if sel.size == 0 or n_dec == 0:
            continue
        p = p_active_by_decile[k]
        p = 0.0 if p is None or not np.isfinite(p) else float(p)
        n_on = int(round(p * n_dec))
        if n_on <= 0:
            continue
        if n_on >= sel.size:
            act[sel] = True
            continue
        thr = np.partition(g[sel], sel.size - n_on)[sel.size - n_on]
        on = sel[g[sel] >= thr]
        if on.size > n_on:                       # ties: drop the excess at random
            on = rng.permutation(on)[:n_on]
        act[on] = True
    return act


def _phi(a, b):
    n11 = float((a & b).sum())
    n10 = float((a & ~b).sum())
    n01 = float((~a & b).sum())
    n00 = float((~a & ~b).sum())
    den = math.sqrt((n11 + n10) * (n01 + n00) * (n11 + n01) * (n10 + n00))
    return (n11 * n00 - n10 * n01) / den if den > 0 else float("nan")


def draw_activity(W, M_twin, stats, cfg, rng, rho2):
    """Two graph-smoothed Gaussian fields, thresholded per M-decile, coupled to match phi."""
    n = M_twin.size
    dec = _decile_index(M_twin)
    sp = stats["spatial"]
    wA = SP.fit_smoothing(W, rho2 * _f(sp.get("moran_activity_A"), 0.0), k=2, n=n)
    wB = SP.fit_smoothing(W, rho2 * _f(sp.get("moran_activity_B"), 0.0), k=2, n=n)
    gA = SP.smooth_field(W, rng.standard_normal(n), k=2, w=wA)
    gI = SP.smooth_field(W, rng.standard_normal(n), k=2, w=wB)
    pa = stats["conditional"]["p_A_active_by_decile"]
    pb = stats["conditional"]["p_B_active_by_decile"]
    target = _f(stats["conditional"].get("activity_corr_phi"), 0.0)

    live = M_twin > 0

    def make(c):
        gB = c * gA + math.sqrt(max(0.0, 1.0 - c * c)) * gI
        a = _threshold_by_decile(gA, dec, pa, rng, live=live)
        b = _threshold_by_decile(gB, dec, pb, rng, live=live)
        return a, b

    lo, hi = -0.999, 0.999
    a, b = make(0.0)
    if np.isfinite(target):
        for _ in range(24):                       # phi is monotone in c
            mid = 0.5 * (lo + hi)
            a, b = make(mid)
            if _phi(a, b) < target:
                lo = mid
            else:
                hi = mid
        a, b = make(0.5 * (lo + hi))
    return (a & live), (b & live), dec


def _f(x, default=0.0):
    if x is None:
        return default
    x = float(x)
    return default if not np.isfinite(x) else x


# ------------------------------------------------------------------------- step 5
def _marginal_quantile(stats, key):
    """Quantile function of a fitted marginal: empirical body, parametric extreme tails."""
    block = stats.get("marginals", {}).get(key)
    if not block or "coarse_cdf" not in block:
        return None
    return F.quantile_fn_from_coarse(block["coarse_cdf"], tail_fit=_tail_fit(block))


def _standardise_within_decile(e, dec, act):
    """Zero-mean, unit-sd *inside each M-decile*.

    Without this the shares are biased: the smoothed noise field is spatially correlated
    with M, so its mean inside a decile is not zero, and every per-decile mean log(A/M)
    comes out shifted by sd * mean(e | decile).  The within-decile spatial structure is
    untouched -- only the decile-level offset and spread are removed.
    """
    out = np.asarray(e, dtype=float).copy()
    for k in range(NDEC):
        sel = np.flatnonzero((dec == k) & act)
        if sel.size >= 2:
            v = out[sel]
            out[sel] = (v - v.mean()) / (v.std(ddof=0) or 1.0)
        elif sel.size == 1:
            out[sel] = 0.0
    return out


def _first_valid(seq, k):
    """The k-th entry of a per-decile ladder, falling back to the nearest non-null one."""
    if seq is None:
        return None
    if seq[k] is not None:
        return seq[k]
    for j in range(len(seq)):
        for cand in (k - j, k + j):
            if 0 <= cand < len(seq) and seq[cand] is not None:
                return seq[cand]
    return None


def _latent(dec, e, mu, sd, act, zM=None, c_m=0.0):
    """The per-decile location-scale score that decides a ZCTA's rank in the share marginal.

    `zM` is log M standardised inside each decile and `c_m` the measured within-decile
    correlation between log M and log(A/M).  Without that term the share is independent of M
    inside a decile, sum(A)/sum(M) comes out low, and the correction to the target saturation
    lands as a level shift on the whole share distribution.
    """
    t = np.zeros(e.size, dtype=float)
    c_m = float(np.clip(c_m if np.isfinite(c_m) else 0.0, -0.99, 0.99))
    if zM is not None and c_m != 0.0:
        e = c_m * zM + math.sqrt(max(0.0, 1.0 - c_m * c_m)) * e
    for k in range(NDEC):
        sel = np.flatnonzero((dec == k) & act)
        if sel.size == 0:
            continue
        m = _f(_first_valid(mu, k), -3.0)
        s = abs(_f(_first_valid(sd, k), 0.5))
        t[sel] = m + s * e[sel]
    return t


def _rank_map(t, act, qfn):
    """Rank-map the latent score onto the empirical share marginal.

    Drawing log(A/M) as mu_d + sd_d * (a fitted residual) does not work: the fitted residual
    tail is Pareto with index ~1.4, while the real A/M is capped at 1 by the headroom
    constraint, so the draw puts A/M in the tens on a few ZCTAs and the repair then has to
    destroy them.  Clamping the residual instead squashes the top and (to keep the variance)
    lifts the whole body.  Rank-mapping the same latent score onto the *measured* A/M
    quantile function reproduces the marginal by construction, bound and all, and keeps the
    per-decile ordering the latent encodes.
    """
    out = np.zeros(t.size, dtype=float)
    idx = np.flatnonzero(act)
    if idx.size == 0 or qfn is None:
        return None
    r = np.argsort(np.argsort(t[idx], kind="stable"), kind="stable").astype(float)
    u = (r + 0.5) / idx.size
    out[idx] = np.asarray(qfn(u), dtype=float)
    return out


def draw_shares(W, M_twin, act_a, act_b, dec, stats, cfg, rng, rho2=1.0, rounds=2):
    """A/M and B/M by rank-mapping a per-decile latent score onto the measured marginals.

    Three quantities are solved for, alternately, because they interact:

    ``c``      the coupling between A's and B's latents, against the measured partial
               correlation.  Bisected rather than set directly because log A and log B both
               contain log M, which survives the within-decile demeaning that defines the
               partial correlation, so the realised value sits above the coupling constant.

    ``kappa``  how much of each latent comes from M's own within-decile rank, against the
               measured sum(A)/sum(M) and sum(B)/sum(M).  This is what closes the
               penetration gap *without* touching the share marginals.  The alternative --
               draw the shares, then multiply A and B by whatever it takes to hit the target
               saturation -- moves the whole share ladder by that factor, and the factor is
               not small: in real data sum(A)/sum(M) is carried largely by a joint
               upper-tail dependence between M and the share (the few high-opportunity
               ZCTAs whose books are near-saturated), which no single exported correlation
               can express.  Choosing the *pairing* rather than the *values* leaves every
               quantile of A/M and B/M where the aggregates say it should be.

    ``w``      the graph smoothing of the noise field, against the measured Moran's I of
               log A and log B (attenuated by rho^2).  Calibrating it on the residual field
               alone is not enough once kappa is large, because the M-rank component dilutes
               the smoothed noise; bisecting on the final observable fixes that.
    """
    n = M_twin.size
    cond = stats["conditional"]
    sp = stats.get("spatial", {})
    qA = _marginal_quantile(stats, "A_over_M")
    qB = _marginal_quantile(stats, "B_over_M")
    lm = np.log(np.maximum(M_twin, 1e-300))
    zM_a = _standardise_within_decile(lm, dec, act_a)
    zM_b = _standardise_within_decile(lm, dec, act_b)
    nA0 = rng.standard_normal(n)
    nI0 = rng.standard_normal(n)
    target_pc = _f(cond.get("partial_corr_logA_logB_given_decile"), 0.0)
    mor_A = rho2 * _f(sp.get("moran_A"), 0.0)
    mor_B = rho2 * _f(sp.get("moran_B"), 0.0)
    sat = _f(stats["scale"].get("saturation"), 0.25)
    br = _f(stats["scale"].get("book_ratio"), 1.0)
    tgt_a = sat * br / (1.0 + br)
    tgt_b = sat - tgt_a
    totM = max(float(M_twin.sum()), 1e-300)

    st = dict(c=float(np.clip(target_pc, -0.99, 0.99)),
              ka=_f(cond.get("corr_logM_logA_over_M_given_decile"), 0.0),
              kb=_f(cond.get("corr_logM_logB_over_M_given_decile"), 0.0),
              wA=SP.fit_smoothing(W, rho2 * _f(sp.get("moran_resid_A"), 0.0), k=1, n=n),
              wB=SP.fit_smoothing(W, rho2 * _f(sp.get("moran_resid_B"), 0.0), k=1, n=n))

    def field_a(w):
        return _standardise_within_decile(SP.smooth_field(W, nA0, k=1, w=w), dec, act_a)

    def field_b(c, w):
        base = c * SP.smooth_field(W, nA0, k=1, w=st["wA"]) + \
            math.sqrt(max(0.0, 1.0 - c * c)) * SP.smooth_field(W, nI0, k=1, w=w)
        return _standardise_within_decile(base, dec, act_b)

    def side(tag, e, act, q, zM, kappa):
        t = _latent(dec, e, cond["mean_log_%s_over_M" % tag],
                    cond["sd_log_%s_over_M" % tag], act, zM=zM, c_m=kappa)
        share = _rank_map(t, act, q)
        out = M_twin * (np.exp(t) if share is None else share)
        out[~act] = 0.0
        return out

    def make():
        A = side("A", field_a(st["wA"]), act_a, qA, zM_a, st["ka"])
        B = side("B", field_b(st["c"], st["wB"]), act_b, qB, zM_b, st["kb"])
        return A, B

    def _bisect(f, target, lo, hi, iters=16, increasing=True):
        best = 0.5 * (lo + hi)
        for _ in range(iters):
            mid = 0.5 * (lo + hi)
            got = f(mid)
            best = mid
            if not np.isfinite(got):
                break
            if (got < target) == increasing:
                lo = mid
            else:
                hi = mid
        return best

    for _ in range(int(rounds)):
        # kappa: hit the measured penetration on each side
        st["ka"] = _bisect(lambda k: float(side("A", field_a(st["wA"]), act_a, qA,
                                                zM_a, k).sum()) / totM,
                           tgt_a, -0.99, 0.99)
        st["kb"] = _bisect(lambda k: float(side("B", field_b(st["c"], st["wB"]), act_b, qB,
                                                zM_b, k).sum()) / totM,
                           tgt_b, -0.99, 0.99)
        # w: hit the measured (attenuated) spatial autocorrelation of log A, log B
        if np.isfinite(mor_A):
            st["wA"] = _bisect(lambda w: SP.morans_i(
                W, _logfield_local(side("A", field_a(w), act_a, qA, zM_a, st["ka"]))),
                mor_A, 0.0, 3.0, iters=14)
        if np.isfinite(mor_B):
            st["wB"] = _bisect(lambda w: SP.morans_i(
                W, _logfield_local(side("B", field_b(st["c"], w), act_b, qB, zM_b,
                                        st["kb"]))),
                mor_B, 0.0, 3.0, iters=14)
        # c: hit the measured partial correlation
        if np.isfinite(target_pc):
            st["c"] = _bisect(lambda c: _partial_pc(
                side("A", field_a(st["wA"]), act_a, qA, zM_a, st["ka"]),
                side("B", field_b(c, st["wB"]), act_b, qB, zM_b, st["kb"]), dec),
                target_pc, -0.999, 0.999, iters=14)
    return make()


def _logfield_local(v, floor_frac=1e-3):
    v = np.asarray(v, dtype=float)
    pos = v[v > 0]
    med = float(np.median(pos)) if pos.size else 1.0
    return np.log(np.maximum(v, floor_frac * med))


def _partial_pc(A, B, dec):
    both = (A > 0) & (B > 0)
    if both.sum() < 8:
        return float("nan")
    la = np.log(np.maximum(A[both], 1e-300))
    lb = np.log(np.maximum(B[both], 1e-300))
    db = dec[both]
    for k in range(NDEC):
        sel = db == k
        if sel.sum() >= 2:
            la[sel] = la[sel] - la[sel].mean()
            lb[sel] = lb[sel] - lb[sel].mean()
    la = la - la.mean()
    lb = lb - lb.mean()
    den = math.sqrt(float(la.dot(la)) * float(lb.dot(lb)))
    return float(la.dot(lb) / den) if den > 0 else float("nan")


def rescale_books(A, B, M, saturation, book_ratio):
    """Hit  (sum A + sum B) / sum M = saturation  and  sum A / sum B = book_ratio."""
    tot = float(saturation) * float(M.sum())
    br = float(book_ratio)
    tgt_a = tot * br / (1.0 + br)
    tgt_b = tot - tgt_a
    if A.sum() > 0:
        A = A * (tgt_a / A.sum())
    if B.sum() > 0:
        B = B * (tgt_b / B.sum())
    return A, B


# ------------------------------------------------------------------------- step 6
def clip_to_headroom(A, B, M, theta, margin=0.999):
    """Scale the offending (A, B) pairs down jointly until M >= max(A+theta B, B+theta A).

    Joint, not per-column: the constraint couples the two books, and scaling only one of
    them would move the book ratio at the same time.
    """
    need = np.maximum(A + theta * B, B + theta * A)
    bad = need > M
    n_bad = int(bad.sum())
    if n_bad:
        f = np.ones_like(M)
        f[bad] = margin * M[bad] / np.maximum(need[bad], 1e-300)
        A = A * f
        B = B * f
    return A, B, n_bad


def headroom_repair(A, B, M, theta, saturation=None, book_ratio=None, rounds=12,
                    tol=2e-3, margin=0.999):
    """Water-fill: clip to the headroom bound, rescale to the target totals, repeat.

    A single clip-then-rescale pass shifts the whole distribution: the clip takes mass off
    the ZCTAs at the bound and the rescale hands it back to every ZCTA uniformly, so the
    body of log(A/M) comes out too high while the top stays cut.  Iterating converges to
    the water-filling fixed point -- the bound-limited ZCTAs sit at the bound and everything
    else carries the target totals -- with the level shift an order of magnitude smaller.
    """
    A = np.asarray(A, dtype=float).copy()
    B = np.asarray(B, dtype=float).copy()
    a0, b0 = float(A.sum()), float(B.sum())
    n_first = None
    n_last = 0
    for _ in range(int(rounds)):
        A, B, n_bad = clip_to_headroom(A, B, M, theta, margin=margin)
        if n_first is None:
            n_first = n_bad
        n_last = n_bad
        if saturation is None or book_ratio is None:
            break
        A, B = rescale_books(A, B, M, saturation, book_ratio)
        got = (A.sum() + B.sum()) / max(float(M.sum()), 1e-300)
        if n_bad == 0 and abs(got - saturation) <= tol * max(saturation, 1e-12):
            break
    A, B, n_final = clip_to_headroom(A, B, M, theta, margin=margin)
    rep = dict(margin=float(margin),frac_touched=(n_first or 0) / float(max(M.size, 1)),
               frac_touched_pass2=n_last / float(max(M.size, 1)),
               frac_touched_final=n_final / float(max(M.size, 1)),
               frac_A_lost=1.0 - (float(A.sum()) / a0 if a0 > 0 else 1.0),
               frac_B_lost=1.0 - (float(B.sum()) / b0 if b0 > 0 else 1.0))
    return A, B, rep


# ------------------------------------------------------------------------- step 7
def _seed_nodes(M, k, rng, forbid=None):
    """k distinct nodes sampled without replacement with probability proportional to M."""
    n = M.size
    p = np.maximum(M, 0.0).astype(float)
    if forbid is not None:
        p = p.copy()
        p[list(forbid)] = 0.0
    if p.sum() <= 0:
        p = np.ones(n)
    p = p / p.sum()
    k = int(min(k, int((p > 0).sum())))
    return list(rng.choice(n, size=k, replace=False, p=p))


def _walk(nbr, start, hops, rng):
    u = int(start)
    for _ in range(int(hops)):
        nb = nbr[u]
        if not nb:
            break
        u = int(nb[int(rng.integers(0, len(nb)))])
    return u


B_HOP_LADDER = (4, 8, 16, 32, 64, 128, 256)


def rep_maps(G, M_twin, state, stats, cfg, rng_a, rng_b, n=None):
    """Voronoi rep maps; `alpha` bisected under common random numbers to the real Jaccard."""
    n = int(n if n is not None else M_twin.size)
    nbr = SP.neighbour_lists(G, n)
    terr = stats["territories"]
    n_rep_a = int(terr["n_rep_a"])
    n_rep_b = int(terr["n_rep_b"])
    target_j = _f(terr.get("misalignment_jaccard"), float("nan"))
    purity = _f(terr.get("rep_state_purity"), 0.0)
    in_state = bool(state is not None and purity > 0.95)

    seeds_a = _seed_nodes(M_twin, n_rep_a, rng_a)
    allowed = None
    if in_state:
        st = np.asarray(state)
        seed_state = np.array([st[s] for s in seeds_a])

        def allowed(li, v):
            return st[v] == seed_state[li]

    lab_a = SP.multi_source_voronoi(nbr, seeds_a, n, allowed=allowed)

    # common random numbers: draw every stochastic input for B's seeds once, so alpha is
    # the only thing that moves during the bisection (and the bisection is monotone).
    u = rng_b.random(n_rep_b)
    base = [seeds_a[i % len(seeds_a)] for i in range(n_rep_b)]

    def walked_at(hops):
        return [_walk(nbr, base[i], hops,
                      np.random.default_rng([cfg.seed, TAG["repb"], i]))
                for i in range(n_rep_b)]

    walked = walked_at(B_HOP_LADDER[0])
    b_hops = B_HOP_LADDER[0]

    from .stats import _best_match_jaccard

    def build(alpha):
        seeds_b = [base[i] if u[i] < alpha else walked[i] for i in range(n_rep_b)]
        allowed_b = None
        if in_state:
            st = np.asarray(state)
            sb = np.array([st[s] for s in seeds_b])

            def allowed_b(li, v):
                return st[v] == sb[li]

        lab_b = SP.multi_source_voronoi(nbr, seeds_b, n, allowed=allowed_b)
        j, _ = _best_match_jaccard(lab_a, lab_b, n_rep_a, n_rep_b)
        return lab_b, j

    def slivered(lab, frac, seed_tag):
        """Flip a fraction of boundary ZCTAs to a neighbouring rep -- real rep maps have
        these, and without them a BFS-Voronoi map is cleaner than any real one, so the
        misalignment Jaccard has a floor the alpha bisection cannot get under."""
        if frac <= 0:
            return lab
        out = np.asarray(lab).copy()
        rg = np.random.default_rng([cfg.seed, TAG["repb"], seed_tag])
        bnd = [i for i in range(n) if any(out[v] != out[i] for v in nbr[i])]
        if not bnd:
            return out
        take = rg.permutation(np.array(bnd, dtype=np.int64))[:int(round(frac * len(bnd)))]
        for i in take:
            alt = [out[v] for v in nbr[int(i)] if out[v] != out[int(i)]]
            if alt:
                out[int(i)] = alt[int(rg.integers(0, len(alt)))]
        return out

    lab_b, j = build(1.0)
    alpha = 1.0
    sliver = 0.0
    if np.isfinite(target_j):
        # alpha=1 copies A's seeds exactly (maximum Jaccard); alpha=0 walks every seed away.
        # If even alpha=0 stays above the target, the walk is too short to decorrelate the
        # map on this graph -- lengthen it before giving up, rather than silently missing.
        for hops in B_HOP_LADDER:
            walked = walked_at(hops)
            b_hops = hops
            lab_lo, j_lo = build(0.0)
            if j_lo <= target_j:
                break
        if j_lo > target_j:
            # the walk cannot decorrelate the map on this graph; draw B's seeds
            # independently of A's, which is the least-aligned construction available
            walked = _seed_nodes(M_twin, n_rep_b, np.random.default_rng(
                [cfg.seed, TAG["repb"], 7777]))
            walked = [walked[i % len(walked)] for i in range(n_rep_b)]
            b_hops = -1
            lab_lo, j_lo = build(0.0)
        lab_hi, j_hi = build(1.0)
        if target_j <= j_lo:
            lab_b, alpha, j = lab_lo, 0.0, j_lo
        elif target_j >= j_hi:
            lab_b, alpha, j = lab_hi, 1.0, j_hi
        else:
            lo, hi = 0.0, 1.0
            for _ in range(18):
                mid = 0.5 * (lo + hi)
                lab_m, j_m = build(mid)
                if j_m < target_j:
                    lo = mid
                else:
                    hi = mid
                lab_b, alpha, j = lab_m, mid, j_m
        if j > target_j + 1e-9:
            slo, shi = 0.0, 1.0
            for _ in range(14):
                smid = 0.5 * (slo + shi)
                lab_s = slivered(lab_b, smid, 31)
                j_s, _ = _best_match_jaccard(lab_a, lab_s, n_rep_a, n_rep_b)
                if j_s > target_j:
                    slo = smid
                else:
                    shi = smid
                sliver, j = smid, j_s
            lab_b = slivered(lab_b, sliver, 31)
            j, _ = _best_match_jaccard(lab_a, lab_b, n_rep_a, n_rep_b)
    return lab_a, lab_b, dict(alpha=float(alpha), jaccard=float(j), b_hops=int(b_hops),
                              sliver=float(sliver),
                              target_jaccard=float(target_j) if np.isfinite(target_j) else None,
                              in_state=in_state, n_rep_a=n_rep_a, n_rep_b=n_rep_b)


# ------------------------------------------------------------------------- driver
def build_twin(inst, stats, cfg):
    """Run the whole pipeline.  Returns a dict with the twin arrays and a synthesis report."""
    n = inst.n
    W = SP.row_normalized_adj(inst.G, n)
    rho = rho_attenuation(cfg.rank_sigma)
    rho2 = rho * rho

    rng_j = np.random.default_rng([cfg.seed, TAG["jitter"]])
    rng_m = np.random.default_rng([cfg.seed, TAG["M"]])
    rng_act = np.random.default_rng([cfg.seed, TAG["act"]])
    rng_sh = np.random.default_rng([cfg.seed, TAG["share"]])
    rng_a = np.random.default_rng([cfg.seed, TAG["repa"]])
    rng_b = np.random.default_rng([cfg.seed, TAG["repb"]])

    new_rank = jitter_ranks(inst.M, cfg.rank_sigma, rng_j, W=W,
                            smooth_w=cfg.jitter_smooth, coarsen=cfg.coarsen,
                            swap_rounds=cfg.swap_rounds)
    M = draw_M(stats, new_rank, n, rng_m)
    act_a, act_b, dec = draw_activity(W, M, stats, cfg, rng_act, rho2)
    A, B = draw_shares(W, M, act_a, act_b, dec, stats, cfg, rng_sh, rho2=rho2)
    sat = _f(stats["scale"].get("saturation"), 0.25)
    br = _f(stats["scale"].get("book_ratio"), 1.0)
    A, B = rescale_books(A, B, M, sat, br)
    # Park constraint-limited ZCTAs at the *smallest slack the real data actually shows*,
    # not hard against the bound: a repair that leaves zero slack shows up as a spurious
    # spike at the bottom of the twin's headroom-slack ladder.
    hb = stats.get("headroom", {}).get("theta_%.2f" % cfg.theta, {})
    sr = hb.get("slack_ratio_q") or [0.001]
    margin = 1.0 - float(np.clip(_f(sr[0], 0.001), 0.001, 0.30))
    A, B, hrep = headroom_repair(A, B, M, cfg.theta, saturation=sat, book_ratio=br,
                                 margin=margin)
    lab_a, lab_b, rrep = rep_maps(inst.G, M, inst.state, stats, cfg, rng_a, rng_b, n=n)

    report = dict(headroom=hrep, reps=rrep, rho=rho, rho2=rho2,
                  sigma_effective=cfg.rank_sigma)
    if hrep["frac_touched"] > 0.02:
        print("WARNING: headroom repair touched %.1f%% of ZCTAs (> 2%%); the fitted "
              "saturation may be too close to the headroom bound"
              % (100.0 * hrep["frac_touched"]))

    # --- invariants ---------------------------------------------------------
    # Compared on the ZCTAs that are active on BOTH sides: a ZCTA that is zero-opportunity
    # in both is not a leaked value, it is the p_active flag being reproduced, and the audit
    # reports that agreement against its chance baseline separately.
    both = (inst.M > 0) & (M > 0)
    real_log = np.log(np.maximum(inst.M[both] / max(_med_pos(inst.M), 1e-300), 1e-300))
    twin_log = np.log(np.maximum(M[both] / max(_med_pos(M), 1e-300), 1e-300))
    exact = int(np.sum(np.abs(real_log - twin_log) < 1e-12))
    if exact:
        raise AssertionError("twin synthesis: %d ZCTAs kept their exact median-normalised "
                             "log M -- the draw is not independent of the real values" % exact)
    if np.array_equal(np.sort(inst.M), np.sort(M)):
        raise AssertionError("twin synthesis: twin M is a permutation of the real M "
                             "multiset -- values must be redrawn, not shuffled")
    report["exact_log_matches"] = exact
    return dict(M=M, A=A, B=B, rep_a=lab_a, rep_b=lab_b, new_rank=new_rank,
                report=report)


def _med_pos(v):
    p = np.asarray(v, dtype=float)
    p = p[p > 0]
    return float(np.median(p)) if p.size else 1.0
