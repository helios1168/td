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


def _gini(v):
    v = np.sort(np.asarray(v, float)); m = len(v); s = v.sum()
    if m == 0 or s <= 0:
        return 0.0
    return float((2.0 * np.arange(1, m + 1) - m - 1).dot(v) / (m * s))


def activity_report(G):
    """Instance-level activity/concentration summary (the `activity` knob's target stats).

    active   : the zip has a book to fight over        (A + B > 0)
    untapped : opportunity but no book yet             (M > 0, A = B = 0)
    glue     : nothing at all                          (A = B = M = 0) -- mechanism (d)
    `active_pieces` counts the components of the active subgraph; > 1 is the point of
    S10_glue (zero-value zips that only connect other zips).
    """
    nodes = list(G)
    A = np.array([G.nodes[z]["A"] for z in nodes], float)
    B = np.array([G.nodes[z]["B"] for z in nodes], float)
    M = np.array([G.nodes[z]["M"] for z in nodes], float)
    act = (A + B) > 0
    glue = (M <= 0) & ~act
    untapped = (M > 0) & ~act
    sub = G.subgraph([z for z, a in zip(nodes, act) if a])
    sizes = sorted((len(c) for c in nx.connected_components(sub)), reverse=True)
    return dict(n=len(nodes),
                active_frac=float(act.mean()) if len(nodes) else 0.0,
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
                  sales_tail_alpha=None, sales_tail_beta=None):
    rng = np.random.default_rng(seed)
    n_metros = n_metros or max(2, min(6, n_rep_a + 1))

    # ---- geography: metro clusters + rural scatter, planar adjacency -----------
    metros = rng.random((n_metros, 2)) * .76 + .12
    covs = [np.diag(rng.uniform(.008, .022, 2)) for _ in range(n_metros)]
    n_clust = int(.70 * n)
    counts = rng.multinomial(n_clust, np.ones(n_metros) / n_metros)
    P = np.vstack([rng.multivariate_normal(metros[m], covs[m] * 2.2, counts[m])
                   for m in range(n_metros)] + [rng.random((n - n_clust, 2))])
    P = np.clip(P, .02, .98)
    G = _adjacency(P)

    # ---- opportunity: density field x heavy-tail multiplier --------------------
    dens = sum(_gauss(P, metros[m], covs[m]) for m in range(n_metros))
    Mz = (0.80 * dens / dens.max() + 0.20) * _dpln(rng, n, tail, m_tail_alpha, m_tail_beta)

    # ---- rep territories: the alignment dial -----------------------------------
    a_idx = rng.choice(n, n_rep_a, replace=False, p=Mz / Mz.sum())
    a_seeds = P[a_idx]
    n_shared = min(n_rep_a, n_rep_b)
    b_seeds = np.vstack([alpha * a_seeds[:n_shared]
                         + (1 - alpha) * (rng.random((n_shared, 2)) * .76 + .12)]
                        + ([rng.random((n_rep_b - n_shared, 2)) * .76 + .12]
                           if n_rep_b > n_shared else []))
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
    G.graph.update(params=dict(n=n, n_rep_a=n_rep_a, n_rep_b=n_rep_b, alpha=alpha,
                               rho_books=rho_books, n_states=n_states, sliver=sliver,
                               saturation=saturation, tail=tail, tight=tight,
                               cap_corr=cap_corr, seed=seed,
                               book_ratio=book_ratio, theta=theta, lam=lam,
                               n_metros=n_metros,
                               m_tail_alpha=m_tail_alpha, m_tail_beta=m_tail_beta,
                               sales_tail=sales_tail, sales_tail_alpha=sales_tail_alpha,
                               sales_tail_beta=sales_tail_beta),
                   corr_AB=float(np.corrcoef(Az, Bz)[0, 1]),
                   Sa=float(Az.sum()), Sb=float(Bz.sum()), Mtot=float(Mz.sum()),
                   cap_a=cap_a.tolist(), cap_b=cap_b.tolist(),
                   metros=metros.tolist())
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
