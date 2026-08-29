"""
synth.py -- synthetic ZCTA-instance generator with gate-targeted dials.

zip50.py generates one fixed 50-zip instance with NO rep structure (implicitly one A
rep vs one B rep) -- exactly the case the census critique (review objection 6, kill
criterion 1) says will not survive contact with real data. This generator produces
graphs matching territory.py's expected schema, with every dial aimed at a named gate:

  dial          gate it targets
  ----          ---------------
  alpha         objection 6 / kill criterion 1: rep-territory alignment. B-rep seeds
                interpolate between copied-from-A (alpha=1: clean 1-1 pairs, two-player
                theory applies everywhere) and independent (alpha=0: dense overlap
                components, unsupported downstream)
  sliver        census's min_share=2% default: boundary noise that creates overlap
                edges just above/below the trim threshold, to audit whether the
                verdict depends on a number nobody chose
  rho_books     kill criterion 4: latent-field correlation in [-1, 1]. Realized
                corr(A_z,B_z) runs ~0 (books separate, machinery answers nothing;
                negative rho cancels the shared-M floor) to ~0.9 (heavily
                contested). Reported in G.graph -- monotone, not calibrated
  n_states      kill criterion 3: state-scoped edges; does respect_state fragment the
                feasible set before contiguity even gets priced
  saturation /  headroom stress: combined share of market, and (tight=True) a mode
  tight         where many zips sit close to the pointwise headroom bound
  tail          heavy-tailed M_z (real ZCTA opportunity is heavy-tailed; zip50's
                mixture is smooth)
  cap_corr      objection 2 follow-up: per-rep capacity field with controllable
                correlation to book size, so capacity can be tested as its own signal
                rather than through the book proxy shown to be a side door
  sales_tail_   commercial concentration: A_z/B_z noise defaults to lognormal(0,
  alpha/beta    sales_tail) same as today, but alpha/beta (dPlN shape params) turn on
                genuine Pareto tails on top/bottom -- financial-advisor office
                clustering is a B2B commercial-real-estate pattern, plausibly more
                concentrated than residential population (Eeckhout 2004 AER; Reed
                2001 Econ Lett, 2002 J Reg Sci; Giesen/Zimmermann/Suedekum 2010
                J Urban Econ). m_tail_alpha/beta exist symmetrically for M_z but
                default off -- ZCTA-level population looks near-lognormal, not
                power-law (USPS boundary redrawing smooths it), so M_z stays as-is

Schema produced (matches territory.py REQUIRED + optional state):
  G.nodes[z] = {rep_a, rep_b, A, B, M, state?, pos}
  G.graph    = {params, corr_AB, Sa, Sb, Mtot, cap_a, cap_b}
Edges: planar Delaunay adjacency, long edges trimmed, connectivity restored.
"""
from __future__ import annotations
import numpy as np, networkx as nx
from scipy.spatial import Delaunay


def _gauss(P, mu, cov):
    d = P - mu; ic = np.linalg.inv(cov)
    return np.exp(-.5 * np.einsum("ij,jk,ik->i", d, ic, d)) / (
        2 * np.pi * np.sqrt(np.linalg.det(cov)))


def _dpln(rng, n, sigma, alpha=None, beta=None):
    """Multiplicative noise: plain lognormal(0, sigma) by default (exact call kept
    identical to the legacy path for bit-for-bit seeded reproducibility), or double
    Pareto-lognormal when alpha/beta are both given -- a normal perturbed by the
    difference of two independent exponentials in log-space (Reed 2001, 2002; Reed &
    Jorgensen 2004). alpha governs the upper tail (smaller = heavier, Zipf-like
    organic-city values near 1), beta the lower tail (typically steeper, 3-4x alpha).
    As alpha, beta -> inf this converges to lognormal(0, sigma), so it nests the
    legacy model exactly."""
    if alpha is None or beta is None:
        return rng.lognormal(0, sigma, n)
    return np.exp(sigma * rng.standard_normal(n)
                  + rng.exponential(1 / alpha, n) - rng.exponential(1 / beta, n))


def _adjacency(P, trim=2.5):
    """Delaunay edges, drop edges longer than trim*median, reconnect components."""
    tri = Delaunay(P)
    E = set()
    for s in tri.simplices:
        for i in range(3):
            u, v = int(s[i]), int(s[(i + 1) % 3])
            E.add((min(u, v), max(u, v)))
    E = list(E)
    L = np.array([np.linalg.norm(P[u] - P[v]) for u, v in E])
    thr = trim * np.median(L)                   # hoisted out of the comprehension:
    keep = [e for e, l in zip(E, L) if l <= thr]   # identical output, O(|E|) not O(|E|^2)
    G = nx.Graph(); G.add_nodes_from(range(len(P))); G.add_edges_from(keep)
    comps = list(nx.connected_components(G))
    while len(comps) > 1:                       # reattach by shortest bridging pair
        main = max(comps, key=len)
        main_l = list(main); Pm = P[main_l]      # hoisted: same list, built once
        best = None
        for C in comps:
            if C is main: continue
            for u in C:
                d = np.linalg.norm(Pm - P[u], axis=1)
                j = int(np.argmin(d))
                if best is None or d[j] < best[0]:
                    best = (d[j], u, main_l[j])
        G.add_edge(best[1], best[2])
        comps = list(nx.connected_components(G))
    return G


def _zipf_weights(k, s=1.0):
    """Zipf metro shares: metro m (1-indexed, m=1 the largest) gets mass proportional to
    m^-s.  s=1 is the classic rank-size law; s=0 recovers equal weights."""
    w = np.arange(1, k + 1, dtype=float) ** (-float(s))
    return w / w.sum()


def _density_base(dens, n, gamma, dens_floor, core_tail, core_cap, rng_core):
    """Normalised density -> the multiplicative base of M_z, with the concentration dials.

    `gamma` is superlinear urban scaling (M ~ dens^gamma, gamma in [1.1, 1.3] in the
    scaling literature); `dens_floor` is the rural floor the legacy code fixed at 0.20;
    `core_tail=(alpha, frac)` mixes a Pareto multiplier into the densest `frac` of zips so
    the top of the distribution is genuinely heavy rather than merely peaked.  The Pareto
    draw is capped at `core_cap` -- uncapped, a single seed's draw can carry a third of
    total M and Gini swings by 0.1 between seeds.

    Renormalisation after the boost is **mean-preserving, not max-preserving**.  The U5
    plan specified `dn /= dn.max()`, but that divides the whole field by the single largest
    Pareto draw, so `dn` collapses towards zero, `dens_floor` dominates the sum, and the
    field comes out *more* uniform than with `core_tail=None`: measured Gini(M) 0.16 vs
    0.43 at the S11 settings.  Restoring the pre-boost mean instead keeps the floor at its
    intended size relative to a typical zip and gives Gini(M) ~ 0.55, the S11 target.
    """
    dn0 = dens / dens.max()
    dn = dn0
    if core_tail is not None:
        ct_alpha, ct_frac = core_tail
        k_core = int(ct_frac * n)
        if k_core > 0:
            idx = np.argsort(-dn)[:k_core]
            dn = dn.copy()
            dn[idx] *= np.minimum((1.0 - rng_core.random(k_core)) ** (-1.0 / ct_alpha),
                                  core_cap)
        m = dn.mean()
        if m > 0:
            dn = dn * (dn0.mean() / m)
    return (1.0 - dens_floor) * dn ** gamma + dens_floor


def _zscore(x):
    x = np.asarray(x, float); s = x.std()
    return (x - x.mean()) / (s if s > 0 else 1.0)


def _smooth(G, x, k=3, nodelist=None):
    """`k` rounds of x <- 0.5*x + 0.5*(W @ x) on the row-normalised adjacency, standardised.

    Gives a spatially autocorrelated field on the actual adjacency graph (not on the
    coordinates), which is what the twin's Moran's I is measured against.  Isolated nodes
    keep degree 1 so W stays well defined.
    """
    import scipy.sparse as sp
    nodes = list(G) if nodelist is None else list(nodelist)
    A = nx.to_scipy_sparse_array(G, nodelist=nodes, format="csr", dtype=float)
    deg = np.asarray(A.sum(axis=1)).ravel()
    deg[deg == 0] = 1.0
    W = sp.diags(1.0 / deg) @ A
    x = np.asarray(x, float).copy()
    for _ in range(int(k)):
        x = 0.5 * x + 0.5 * (W @ x)
    return _zscore(x)


def _sigmoid(t):
    return 1.0 / (1.0 + np.exp(-t))


def _fit_intercept(z, slope, target, lo=-40.0, hi=40.0):
    """b with mean(sigmoid(b - slope*z)) == target (monotone in b, so plain bisection)."""
    target = float(np.clip(target, 1e-9, 1 - 1e-9))
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if _sigmoid(mid - slope * z).mean() < target:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def _top_frac(s, pool, frac):
    """Boolean mask: the top `frac` of `pool` (a boolean mask) by score `s`."""
    out = np.zeros(len(s), bool)
    idx = np.flatnonzero(pool)
    k = int(round(float(frac) * len(idx)))
    if k <= 0 or len(idx) == 0:
        return out
    k = min(k, len(idx))
    out[idx[np.argsort(-s[idx], kind="stable")[:k]]] = True
    return out


def _activity_masks(G, Mz, cfg, rng_act):
    """(glue, untapped) masks: which zips have nothing, and which have only opportunity.

    A graph-smoothed Gaussian field `f` is tilted by log density,
    `s = f - slope * z(log M)`, so quiet zips cluster spatially *and* sit in the thin part
    of the map -- exactly the "sparse active zips with zero-value glue" regime (mechanism
    (d)) that real data adds.  `mode="quantile"` (the default) hits the requested
    fractions exactly; `mode="bernoulli"` hits them in expectation via a fitted logistic
    intercept, which is the closer analogue of the twin's per-decile P(A>0).
    """
    n = len(Mz)
    p_glue = float(cfg.get("p_glue", 0.0) or 0.0)
    p_unt = float(cfg.get("p_untapped", 0.0) or 0.0)
    slope = float(cfg.get("slope", 1.5))
    k = int(cfg.get("smooth_k", 3))
    mode = cfg.get("mode", "quantile")
    by_dec = cfg.get("p_untapped_by_decile")
    if mode not in ("quantile", "bernoulli"):
        raise ValueError(f"activity mode must be 'quantile' or 'bernoulli', got {mode!r}")
    if p_glue + p_unt >= 1.0:
        raise ValueError(f"p_glue + p_untapped must be < 1, got {p_glue} + {p_unt}")

    f = _smooth(G, rng_act.standard_normal(n), k)
    zM = _zscore(np.log(np.maximum(Mz, np.finfo(float).tiny)))
    s = f - slope * zM                       # high s = quiet zip
    dec = _deciles(Mz)

    if mode == "quantile":
        glue = _top_frac(s, np.ones(n, bool), p_glue)
    else:
        b0 = _fit_intercept(zM, slope, p_glue)
        glue = _uniform_from(f) < _sigmoid(b0 - slope * zM)
    rest = ~glue

    if by_dec is not None:
        by_dec = np.asarray(by_dec, float)
        untapped = np.zeros(n, bool)
        for d in range(10):
            pool = rest & (dec == d)
            untapped |= _top_frac(s, pool, by_dec[min(d, len(by_dec) - 1)])
    elif mode == "quantile":
        share = p_unt / max(1e-12, 1.0 - p_glue)
        untapped = _top_frac(s, rest, share)
    else:
        b1 = _fit_intercept(zM[rest], slope, p_unt / max(1e-12, 1.0 - p_glue))
        f2 = _smooth(G, rng_act.standard_normal(n), k)
        untapped = rest & (_uniform_from(f2) < _sigmoid(b1 - slope * zM))
    return glue, untapped & ~glue


def _uniform_from(f):
    """Standard-normal field -> spatially correlated uniform (probability integral xform)."""
    from scipy.stats import norm
    return norm.cdf(f)


def _deciles(v):
    """Rank-based decile index 0..9 (ties broken by position; exact 10-way split)."""
    n = len(v)
    order = np.argsort(np.asarray(v, float), kind="stable")
    rank = np.empty(n, int); rank[order] = np.arange(n)
    return np.minimum(rank * 10 // max(n, 1), 9)


def _split_seeds(P, Mz, rep_host, host_seeds, k, split_pos, split_weight, rng_s):
    """Zips at which to plant an intruding seed inside `k` of the host firm's territories.

    Picks the territories with probability proportional to their opportunity
    (`split_weight="M"`) or uniformly, then one zip inside each: the metro core
    (`split_pos="core"`, argmax M) or the periphery (`"edge"`, farthest from the host
    seed).  The host's own seed zip is excluded so the intruder never lands on top of it
    (an exact positional tie would silently give the new rep an empty territory).
    """
    n_host = len(host_seeds)
    terr_M = np.array([Mz[rep_host == r].sum() for r in range(n_host)])
    ok = np.flatnonzero(terr_M > 0)
    k = int(min(k, len(ok)))
    if k <= 0:
        return []
    if split_weight == "M":
        p = terr_M[ok] / terr_M[ok].sum()
    elif split_weight == "uniform":
        p = None
    else:
        raise ValueError(f"split_weight must be 'M' or 'uniform', got {split_weight!r}")
    out = []
    for r in rng_s.choice(ok, k, replace=False, p=p):
        members = np.flatnonzero(rep_host == r)
        keep = members[~np.all(P[members] == host_seeds[r], axis=1)]
        if len(keep):
            members = keep
        if split_pos == "core":
            z = members[int(np.argmax(Mz[members]))]
        elif split_pos == "edge":
            z = members[int(np.argmax(np.linalg.norm(P[members] - host_seeds[r], axis=1)))]
        else:
            raise ValueError(f"split_pos must be 'core' or 'edge', got {split_pos!r}")
        out.append(int(z))
    return out


def _gini(v):
    v = np.sort(np.asarray(v, float)); m = len(v); s = v.sum()
    if m == 0 or s <= 0:
        return 0.0
    return float((2.0 * np.arange(1, m + 1) - m - 1).dot(v) / (m * s))


def activity_report(G):
    """Instance-level activity/concentration summary (the `activity` knob's target stats).

    active   : the zip is worth something to somebody  (A + B + M > 0)
    booked   : the zip has a book to fight over        (A + B > 0)
    untapped : opportunity but no book yet             (M > 0, A = B = 0)  -- still active
    glue     : nothing at all                          (A = B = M = 0) -- mechanism (d)

    `active` is defined to agree with `contig_methods/base.covariates`, which calls a zip
    active when `u_a + u_b > 0`; at lam > 0 an untapped zip has u > 0, so
    `active_frac == 1 - glue_frac`.  `active_pieces` counts the components of the active
    subgraph; > 1 is the point of S10_glue (zero-value zips that only connect other zips).
    """
    nodes = list(G)
    A = np.array([G.nodes[z]["A"] for z in nodes], float)
    B = np.array([G.nodes[z]["B"] for z in nodes], float)
    M = np.array([G.nodes[z]["M"] for z in nodes], float)
    booked = (A + B) > 0
    act = (A + B + M) > 0
    glue = ~act
    untapped = (M > 0) & ~booked
    sub = G.subgraph([z for z, a in zip(nodes, act) if a])
    sizes = sorted((len(c) for c in nx.connected_components(sub)), reverse=True)
    return dict(n=len(nodes),
                active_frac=float(act.mean()) if len(nodes) else 0.0,
                booked_frac=float(booked.mean()) if len(nodes) else 0.0,
                glue_frac=float(glue.mean()) if len(nodes) else 0.0,
                untapped_frac=float(untapped.mean()) if len(nodes) else 0.0,
                active_pieces=len(sizes),
                largest_active_share=float(sizes[0] / act.sum()) if sizes else 0.0,
                M_share_untapped=float(M[untapped].sum() / M.sum()) if M.sum() > 0 else 0.0,
                gini_M=_gini(M), gini_u=_gini(A + B + M),
                top1_share_M=float(np.sort(M)[-max(1, len(M) // 100):].sum() / M.sum())
                if M.sum() > 0 else 0.0,
                top10_share_M=float(np.sort(M)[-max(1, len(M) // 10):].sum() / M.sum())
                if M.sum() > 0 else 0.0)


def make_instance(n=200, n_rep_a=4, n_rep_b=4, alpha=1.0, rho_books=0.7,
                  n_states=0, sliver=0.0, saturation=0.12, tail=0.25,
                  book_ratio=5/3, theta=0.40, lam=0.30, tight=False, cap_corr=1.0,
                  n_metros=None, seed=0,
                  m_tail_alpha=None, m_tail_beta=None, sales_tail=0.20,
                  sales_tail_alpha=None, sales_tail_beta=None,
                  # ---- generator v2 (PLAN.md G.2); every default below is a no-op ----
                  metro_weights=None, zipf_s=1.0, gamma=1.0, dens_floor=0.20,
                  core_tail=None, core_cap=50.0,
                  split_a=0, split_b=0, split_pos="core", split_weight="M",
                  activity=None, assign="euclid", b_hops=4, share_curve=None,
                  graph=None, pos=None, density_field=None, states=None,
                  validate_self=True, _calib=None, **unknown):
    """Synthetic ZCTA instance.  See the module docstring for the dial-to-gate map.

    THE INVARIANCE RULE (generator v2, U5)
    --------------------------------------
    S1-S7 at every seed must stay **byte-identical** to the pre-v2 generator, guarded by
    `battery/code/tests/test_synth_compat.py::test_bit_identity`.  That holds because every
    knob added below is one of exactly three things:

      (a) a pure post-transform of arrays `rng` has already produced;
      (b) an argument substitution whose default branch is the *literal* current
          expression (`metro_weights`, `gamma`/`dens_floor`, `share_curve`); or
      (c) a consumer of `rng2` -- a disjoint child generator -- only.

    `rng` is never called from a new code path, no existing `rng` call is moved, removed,
    or made conditional, and no existing call's arguments change shape.  Two traps that
    make this stricter than it looks:

      * the `rng.random((n_shared, 2))` at the `b_seeds` vstack is drawn **unconditionally**,
        including at alpha=1.0 where its value is multiplied by zero.  It still runs under
        `assign="graph"` (result discarded) for exactly this reason.
      * `rng.multinomial` and `rng.choice(p=...)` consume a *data-dependent* number of
        bit-generator words, so any change to `w` or `Mz` shifts every later draw.  The
        default `metro_weights=None` branch is therefore textually `np.ones(n_metros)/n_metros`.

    `rng2 = default_rng([seed, 7919])` is spawned into one stream per knob, so switching one
    knob on can never move another knob's draws.
    """
    if unknown:
        if "calibrated" in unknown:
            raise TypeError(
                "make_instance() got 'calibrated=': that is a scenario() sentinel, not a "
                "generator argument.  Use synth.scenario('S8_twin', stats=...), or splat "
                "synth.calibrate(stats)['overrides'] yourself.")
        raise TypeError(f"make_instance() got unexpected keyword argument(s) "
                        f"{sorted(unknown)}")
    rng = np.random.default_rng(seed)
    rng2 = np.random.default_rng([seed, 7919])
    (r_core, r_act, r_split, r_assign, r_books, r_share, r_geo, _r_spare) = rng2.spawn(8)
    n_metros = n_metros or max(2, min(6, n_rep_a + 1))
    density_field_hash = graph_hash = None

    # ---- geography: metro clusters + rural scatter, planar adjacency -----------
    # metro_weights=None must reproduce the literal `np.ones(n_metros)/n_metros` that
    # rng.multinomial saw before v2: multinomial consumes a data-dependent number of
    # bit-generator words, so an equal-but-differently-computed p moves every later draw.
    if metro_weights is None:
        mw = np.ones(n_metros) / n_metros
    elif isinstance(metro_weights, str):
        if metro_weights != "zipf":
            raise ValueError(f"metro_weights must be None, 'zipf' or an array, "
                             f"got {metro_weights!r}")
        mw = _zipf_weights(n_metros, zipf_s)
    else:
        mw = np.asarray(metro_weights, float); mw = mw / mw.sum()
    metros = rng.random((n_metros, 2)) * .76 + .12
    covs = [np.diag(rng.uniform(.008, .022, 2)) for _ in range(n_metros)]
    n_clust = int(.70 * n)
    counts = rng.multinomial(n_clust, mw)
    P = np.vstack([rng.multivariate_normal(metros[m], covs[m] * 2.2, counts[m])
                   for m in range(n_metros)] + [rng.random((n - n_clust, 2))])
    P = np.clip(P, .02, .98)
    G = _adjacency(P)

    # ---- opportunity: density field x heavy-tail multiplier --------------------
    if metro_weights is None:
        dens = sum(_gauss(P, metros[m], covs[m]) for m in range(n_metros))
    else:                       # metro m carries n_metros*mw[m] x its equal-weight mass
        dens = sum(n_metros * mw[m] * _gauss(P, metros[m], covs[m])
                   for m in range(n_metros))
    if gamma == 1.0 and dens_floor == 0.20 and core_tail is None and density_field is None:
        base = 0.80 * dens / dens.max() + 0.20          # the literal legacy expression
    else:
        base = _density_base(dens, n, gamma, dens_floor, core_tail, core_cap, r_core)
    Mz = base * _dpln(rng, n, tail, m_tail_alpha, m_tail_beta)

    # ---- rep territories: the alignment dial -----------------------------------
    a_idx = rng.choice(n, n_rep_a, replace=False, p=Mz / Mz.sum())
    a_seeds = P[a_idx]
    n_shared = min(n_rep_a, n_rep_b)
    b_seeds = np.vstack([alpha * a_seeds[:n_shared]
                         + (1 - alpha) * (rng.random((n_shared, 2)) * .76 + .12)]
                        + ([rng.random((n_rep_b - n_shared, 2)) * .76 + .12]
                           if n_rep_b > n_shared else []))

    # ---- designed dense components (split_b: 1Ax2B, split_a: 2Ax1B) -------------
    # Provisional labels from the un-split seed sets decide which territories get an
    # intruder; split_b runs first so split_a sees the post-split B map.  Pure
    # post-transform of already-drawn arrays + r_split, so `rng` is untouched.
    if split_a or split_b:
        rep_a0 = np.argmin(np.linalg.norm(P[:, None] - a_seeds[None], axis=2), axis=1)
        rep_b0 = np.argmin(np.linalg.norm(P[:, None] - b_seeds[None], axis=2), axis=1)
        if split_b:
            add = _split_seeds(P, Mz, rep_a0, a_seeds, split_b, split_pos,
                               split_weight, r_split)
            if add:
                b_seeds = np.vstack([b_seeds, P[add]])
                rep_b0 = np.argmin(np.linalg.norm(P[:, None] - b_seeds[None], axis=2),
                                   axis=1)
        if split_a:
            add = _split_seeds(P, Mz, rep_b0, b_seeds, split_a, split_pos,
                               split_weight, r_split)
            if add:
                a_seeds = np.vstack([a_seeds, P[add]])
        n_rep_a, n_rep_b = len(a_seeds), len(b_seeds)

    rep_a = np.argmin(np.linalg.norm(P[:, None] - a_seeds[None], axis=2), axis=1)
    db = np.linalg.norm(P[:, None] - b_seeds[None], axis=2)
    rep_b = np.argmin(db, axis=1)
    if sliver > 0 and n_rep_b > 1:              # flip a fraction to 2nd-nearest B seed
        flip = rng.random(n) < sliver
        second = np.argsort(db, axis=1)[:, 1]
        rep_b = np.where(flip, second, rep_b)

    # ---- books: the correlation dial -------------------------------------------
    # Latent share fields built on the metro basis. Field B mixes field A with a
    # component orthogonalized against it IN SAMPLE, so rho_books in [-1, 1] is a
    # clean correlation dial between the latent fields. Realized corr(A_z, B_z) is
    # floored above zero by the shared M_z factor (real books share market size);
    # negative rho_books cancels that floor -- S4_separate uses it. Realized corr
    # is reported in G.graph["corr_AB"]; the dial is monotone, not calibrated.
    gm = np.stack([_gauss(P, metros[m], covs[m]) for m in range(n_metros)])
    gm = gm / gm.max(axis=1, keepdims=True)
    FA = rng.normal(0, 1, n_metros) @ gm
    FI = rng.normal(0, 1, n_metros) @ gm
    FA0 = FA - FA.mean(); FI0 = FI - FI.mean()
    FI0 -= (FI0 @ FA0) / (FA0 @ FA0) * FA0
    FA_n = FA0 / FA0.std(); FI_n = FI0 / FI0.std()
    FB_n = rho_books * FA_n + np.sqrt(max(0.0, 1 - rho_books ** 2)) * FI_n
    def _share(f):
        u = (f - f.mean()) / (f.std() + 1e-9)
        return .02 + .43 * (1 / (1 + np.exp(-1.5 * u))) ** 1.5
    Az = Mz * _share(FA_n) * _dpln(rng, n, sales_tail, sales_tail_alpha, sales_tail_beta)
    Bz = Mz * _share(FB_n) * _dpln(rng, n, sales_tail, sales_tail_alpha, sales_tail_beta)

    # ---- scale to target totals, enforce pointwise headroom --------------------
    Mz *= (40.0 * n / 50) / Mz.sum()
    tgt = saturation * Mz.sum()
    Sa_t = tgt * book_ratio / (1 + book_ratio); Sb_t = tgt - Sa_t
    Az *= Sa_t / Az.sum(); Bz *= Sb_t / Bz.sum()
    slack = 1.02 if tight else 1.05
    need = np.maximum(Az + theta * Bz, Bz + theta * Az)
    bad = Mz < slack * need
    Mz[bad] = slack * need[bad]
    Mz *= (40.0 * n / 50) / Mz.sum()
    need = np.maximum(Az + theta * Bz, Bz + theta * Az)
    bad = Mz < need                              # renorm may re-break a few: hard-fix
    Mz[bad] = 1.001 * need[bad]

    # ---- activity: glue / untapped / active (mechanism (d)) --------------------
    # Applied AFTER the two-pass headroom repair, never before: zeroing A, B, M only
    # slackens M >= max(A + theta*B, B + theta*A), so the repair cannot be undone, while
    # running it before would let the repair put opportunity back on a glue zip.  The
    # final renormalisation of M to 40n/50 scales A and B by the same factor, so the
    # saturation ratio survives losing the glue zips' opportunity.
    if activity is not None:
        glue_m, untapped_m = _activity_masks(G, Mz, activity, r_act)
        off = glue_m | untapped_m
        Az = Az.copy(); Bz = Bz.copy(); Mz = Mz.copy()
        Az[off] = 0.0; Bz[off] = 0.0
        Mz[glue_m] = 0.0
        tot_M = Mz.sum()
        if tot_M <= 0:
            raise ValueError("activity zeroed every zip's opportunity (p_glue too high)")
        f_act = (40.0 * n / 50) / tot_M
        Mz *= f_act; Az *= f_act; Bz *= f_act

    # ---- states ------------------------------------------------------------------
    states = None
    if n_states > 0:
        s_seeds = rng.random((n_states, 2))
        states = np.argmin(np.linalg.norm(P[:, None] - s_seeds[None], axis=2), axis=1)

    # ---- per-rep capacity field (objection 2 follow-up) -------------------------
    book_a = np.array([Az[rep_a == r].sum() for r in range(n_rep_a)])
    book_b = np.array([Bz[rep_b == r].sum() for r in range(n_rep_b)])
    def caps(book, m):
        shuf = rng.permutation(book)
        base = cap_corr * book + (1 - cap_corr) * shuf
        return (base / base.sum()) * book.sum() * rng.lognormal(0, .15, m)
    cap_a, cap_b = caps(book_a, n_rep_a), caps(book_b, n_rep_b)

    for z in range(n):
        G.nodes[z].update(rep_a=int(rep_a[z]), rep_b=int(rep_b[z]),
                          A=float(Az[z]), B=float(Bz[z]), M=float(Mz[z]),
                          pos=(float(P[z, 0]), float(P[z, 1])))
        if states is not None:
            G.nodes[z]["state"] = f"S{int(states[z])}"
    act_rep = activity_report(G)
    G.graph.update(params=dict(n=n, n_rep_a=n_rep_a, n_rep_b=n_rep_b, alpha=alpha,
                               rho_books=rho_books, n_states=n_states, sliver=sliver,
                               saturation=saturation, tail=tail, tight=tight,
                               cap_corr=cap_corr, seed=seed,
                               book_ratio=book_ratio, theta=theta, lam=lam,
                               n_metros=n_metros,
                               m_tail_alpha=m_tail_alpha, m_tail_beta=m_tail_beta,
                               sales_tail=sales_tail, sales_tail_alpha=sales_tail_alpha,
                               sales_tail_beta=sales_tail_beta,
                               # ---- generator v2 ----
                               split_a=split_a, split_b=split_b, split_pos=split_pos,
                               split_weight=split_weight, activity=activity,
                               metro_weights=metro_weights, zipf_s=zipf_s, gamma=gamma,
                               dens_floor=dens_floor, core_tail=core_tail,
                               core_cap=core_cap, assign=assign, b_hops=b_hops,
                               share_curve=share_curve,
                               calibrated=bool((_calib or {}).get("calibrated", False)),
                               calib_source=(_calib or {}).get("calib_source"),
                               active_frac=act_rep["active_frac"],
                               glue_frac=act_rep["glue_frac"],
                               untapped_frac=act_rep["untapped_frac"],
                               density_field_hash=density_field_hash,
                               graph_hash=graph_hash),
                   corr_AB=float(np.corrcoef(Az, Bz)[0, 1]),
                   Sa=float(Az.sum()), Sb=float(Bz.sum()), Mtot=float(Mz.sum()),
                   cap_a=cap_a.tolist(), cap_b=cap_b.tolist(),
                   metros=(metros.tolist() if metros is not None else []))
    if validate_self and (activity is not None or graph is not None
                          or density_field is not None):
        import territory as _T
        probs = _T.validate(G)
        assert probs == [], f"make_instance produced an invalid instance: {probs}"
    return G


# ---- the scenario battery: each row names the gate it instantiates --------------
SCENARIOS = {
    "S1_aligned":   dict(alpha=1.0, n_rep_a=4, n_rep_b=4),                 # sanity: pure 1-1
    "S2_entangled": dict(alpha=0.0, n_rep_a=4, n_rep_b=5),                 # kill criterion 1
    "S3_slivers":   dict(alpha=1.0, n_rep_a=4, n_rep_b=4, sliver=0.03),    # min_share audit
    "S4_separate":  dict(alpha=1.0, rho_books=-0.5),                       # kill criterion 4
    "S5_states":    dict(alpha=0.7, n_states=6),                           # kill criterion 3
    "S6_tight":     dict(saturation=0.55, tight=True),                     # headroom stress
    "S7_heavytail": dict(alpha=1.0, sales_tail_alpha=1.0, sales_tail_beta=3.5),  # kill criterion: commercially-concentrated sales (heavy Pareto tail, Zipf-like) independent of population/opportunity smoothing
}


def scenario(name, n=200, seed=0, stats=None, **overrides):
    kw = dict(SCENARIOS[name]); kw.update(overrides)
    return make_instance(n=n, seed=seed, **kw)


def _report(name, G, T):
    probs = T.validate(G)
    cen = T.census(G)
    share11 = sum(c["share"] for c in cen if c["shape"] == "1-1 pair")
    act = activity_report(G)
    print(f"{name:<14} n={G.number_of_nodes():<5} corr={G.graph['corr_AB']:+.2f}  "
          f"comps={len(cen)}  1-1 opp share={share11:.0%}  "
          f"active={act['active_frac']:.2f}  gini(M)={act['gini_M']:.2f}  "
          f"validate: {'ok' if not probs else probs}")


if __name__ == "__main__":
    import argparse
    import territory as T

    ap = argparse.ArgumentParser(
        description="Generate a synthetic ZCTA instance (or self-test every scenario).")
    ap.add_argument("--scenario", help="name from SCENARIOS; omit to sweep them all")
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--n", type=int, default=200)
    ap.add_argument("--stats", help="twin_stats.json for the calibrated scenarios")
    ap.add_argument("--dump", help="write the instance summary to this JSON path")
    args = ap.parse_args()

    if args.scenario is None:
        for nm in SCENARIOS:
            if SCENARIOS[nm].get("regional"):
                print(f"{nm:<14} (regional: needs U8 battery/code/regions.py)")
                continue
            _report(nm, scenario(nm, n=args.n, seed=args.seed, stats=args.stats), T)
    else:
        G = scenario(args.scenario, n=args.n, seed=args.seed, stats=args.stats)
        _report(args.scenario, G, T)
        if args.dump:
            import json
            zs = list(G)
            json.dump(dict(n_zips=len(zs), S_a=G.graph["Sa"], S_b=G.graph["Sb"],
                           M=G.graph["Mtot"],
                           A_z=[G.nodes[z]["A"] for z in zs],
                           B_z=[G.nodes[z]["B"] for z in zs],
                           M_z=[G.nodes[z]["M"] for z in zs],
                           state=[G.nodes[z].get("state") for z in zs],
                           rep_a=[G.nodes[z]["rep_a"] for z in zs],
                           rep_b=[G.nodes[z]["rep_b"] for z in zs],
                           edges=[[int(u), int(v)] for u, v in G.edges()],
                           params=G.graph["params"]),
                      open(args.dump, "w"), indent=1, default=float)
            print(f"wrote {args.dump}")
