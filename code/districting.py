"""
districting.py -- two-district territory design with hard contiguity, as a MILP.

WHAT A DISTRICTING ILP IS
-------------------------
An integer program that partitions geographic units (here ZCTAs) into districts
subject to balance and contiguity, optimising some objective. Standard in electoral
redistricting and sales-territory alignment. The three pieces are always:

  decision   x_z in {0,1}          which district unit z joins   (2 districts => one binary)
  balance    a linear condition    here: the KS fairness gap
  contiguity the hard part         handled below by lazy separator cuts

WHY A COMPACTNESS TERM IS NOT OPTIONAL
--------------------------------------
Fairness alone is DEGENERATE: with n ZCTAs and fine-grained values, many different
allocations achieve essentially the same gap (subset-sum gets arbitrarily close to any
target). Contiguity cuts then never bite -- the solver simply finds another equally
fair but equally disconnected allocation, and cut generation thrashes forever.
The fix is the standard districting objective:

    minimise   gap  +  rho * (number of boundary edges)

The boundary-edge count is a compactness proxy: it is the perimeter of the partition.
It breaks the tie toward geographically coherent shapes and makes cuts effective.

CONTIGUITY: SEPARATOR CUTS
--------------------------
Fix a root ZCTA for each side. Given a candidate solution whose a-side splits into
components, for each component S not containing a's root:

    |S| * sum_{w in N(S)} x_w  >=  sum_{v in S} x_v

"if any of S is with a, some neighbour just outside S must be too". Symmetric form in
(1-x) for b. Add, re-solve, repeat. This is the cut formulation; the alternative is a
single-commodity FLOW formulation (ship one unit from every assigned unit to the
district root along in-district edges), which is exact in one shot but needs
O(|E|) extra continuous variables per district.
"""
from __future__ import annotations
import numpy as np, networkx as nx
from scipy.optimize import milp, LinearConstraint, Bounds
from scipy.sparse import lil_matrix, csr_matrix


def _ratio_guard(ua, ub):
    """u_a/u_b with the zero-value-zip guard (PLAN.md C.0 #9).

    Identical to ua/ub wherever ub > 0.  A zip with ub == 0 and ua > 0 ranks first
    (ratio +inf); a zip with ua == ub == 0 (regime (d) glue) gets ratio 1 -- neutral.
    """
    ua = np.asarray(ua, float); ub = np.asarray(ub, float)
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.where(ub > 0, ua / ub, np.where(ua > 0, np.inf, 1.0))


def solve_contiguous_nash(G, nodes, theta=0.40, lam=0.30, rho=2e-3,
                          respect_state=False, max_iter=30, time_limit=20.0,
                          verbose=True, deadline=None, on_iter=None,
                          g0_seeds=None, z_bound=50.0, seed=None, threads=None):
    """
    Contiguous NASH by OUTER APPROXIMATION.

    log(g_a g_b) = log g_a + log g_b is separable but NOT linear: it is CONCAVE in the
    linear expressions g_a, g_b. A concave function is the lower envelope of its
    tangents, so introduce z_a <= log g_a and add supporting cuts

        z_a  <=  log(ghat) + (g_a - ghat)/ghat

    one linear constraint per tangent point, no extra binaries. Maximise z_a + z_b.
    The tangent set is an OUTER approximation (an upper bound) that tightens as
    tangents are added at the incumbent. Interleaved with the contiguity separator
    cuts, both converge together -- typically in ~5 iterations, versus ~16 separate
    MILP solves for an epsilon-constraint sweep.

    `rho` prices boundary edges (compactness). It competes directly with the log
    objective: sweep it and report both the product and the perimeter.  The model
    decision (2026-08-28) is rho = 0 with contiguity as a hard constraint; rho > 0 is
    kept for continuity with the battery numbers.

    Harness hooks (PLAN.md C.4; every default reproduces the pre-2026-08-29 behaviour):

      deadline   absolute time.time() at which to stop; each MILP gets
                 min(time_limit, deadline - now).  If that is <= 0 before a solve the
                 function returns status "time limit" carrying the last iterate.
      on_iter    callback(dict(it, x, ga, gb, master_obj, dual_bound, added, n_cuts,
                 n_tangents, pieces, perimeter_true)) after every master solve, the
                 converging one included.  master_obj / dual_bound are in maximisation
                 units (z_a + z_b - rho * perimeter); dual_bound is NaN if HiGHS gave none.
      g0_seeds   None -> the legacy absolute seeds (1, 3, 5, 8, 11); "quantile" -> the
                 data-scaled geomspace that territory.nash_exact uses; or an iterable.
      z_bound    box on z_a, z_b (legacy 50.0 -- absolute, wrong on dollar data).
      seed, threads   recorded in the result only; HiGHS through scipy.milp is
                 single-threaded and deterministic already.

    Every return dict carries `status`, `iters`, `n_cuts`, `n_tangents`, `seed`, `threads`
    and, whenever an iterate exists, `to_a, k, g_a, g_b, product, perimeter,
    perimeter_true, pieces, n_edges, message`.  `perimeter` reads the edge variables (at
    rho = 0 they are unpriced slack); `perimeter_true` counts boundary edges of `to_a`.
    `pieces` = (components of a's side, components of b's side) in the filtered graph.
    Statuses: "optimal", "iteration limit", "time limit", "solver failed".
    """
    import time as _time
    nodes = list(nodes); n = len(nodes); idx = {z: i for i, z in enumerate(nodes)}
    A = np.array([G.nodes[z]["A"] for z in nodes], float)
    B = np.array([G.nodes[z]["B"] for z in nodes], float)
    M = np.array([G.nodes[z]["M"] for z in nodes], float)
    c1, c2 = 1 - lam, theta * (1 - lam)
    ua, ub = c1*A + c2*B + lam*M, c2*A + c1*B + lam*M
    Sa, Sb = 0.0, 0.0   # disagreement point d=(0,0): gains ARE bundle utilities

    H = G.subgraph(nodes).copy()
    if respect_state:
        H.remove_edges_from([(u, v) for u, v in H.edges()
                             if G.nodes[u].get("state") != G.nodes[v].get("state")])
    E = [(idx[u], idx[v]) for u, v in H.edges()]; m = len(E)
    r = _ratio_guard(ua, ub)
    root_a = int(np.argmax(r)); root_b = int(np.argmin(r))

    NV = n + 2 + m; IA, IB = n, n + 1
    rows, rl, ru = [], [], []
    def add(pairs, lo, hi): rows.append(pairs); rl.append(lo); ru.append(hi)
    add([(root_a, 1.0)], 1, 1); add([(root_b, 1.0)], 0, 0)
    for e, (i, j) in enumerate(E):
        add([(n+2+e, 1.0), (i, -1.0), (j, 1.0)], 0, np.inf)
        add([(n+2+e, 1.0), (i, 1.0), (j, -1.0)], 0, np.inf)

    n_cuts = 0; n_tangents = 0
    def tangent(side, ghat):
        nonlocal n_tangents
        if ghat <= 1e-9: return
        if side == "a":
            add([(IA, 1.0)] + [(i, -ua[i]/ghat) for i in range(n)],
                -np.inf, np.log(ghat) - 1.0 - Sa/ghat)
        else:
            add([(IB, 1.0)] + [(i, ub[i]/ghat) for i in range(n)],
                -np.inf, np.log(ghat) - 1.0 + (ub.sum() - Sb)/ghat)
        n_tangents += 1
    if g0_seeds is None:
        seeds = (1.0, 3.0, 5.0, 8.0, 11.0)
    elif isinstance(g0_seeds, str) and g0_seeds == "quantile":
        span = max(ua.sum() - Sa, ub.sum() - Sb)
        seeds = np.geomspace(max(span*1e-3, 1e-3), span, 8)
    else:
        seeds = tuple(float(g) for g in g0_seeds)
    for g0 in seeds:
        tangent("a", g0); tangent("b", g0)

    c_obj = np.zeros(NV); c_obj[IA] = c_obj[IB] = -1.0; c_obj[n+2:] = rho
    integ = np.zeros(NV); integ[:n] = 1
    lo = np.zeros(NV); hi = np.ones(NV)
    lo[IA] = lo[IB] = -float(z_bound); hi[IA] = hi[IB] = float(z_bound)

    def build():
        Am = lil_matrix((len(rows), NV))
        for k, pr in enumerate(rows):
            for c_, v_ in pr: Am[k, c_] += v_
        return LinearConstraint(csr_matrix(Am), np.array(rl), np.array(ru))

    def pieces_of(x):
        sel_a = [z for z in nodes if x[idx[z]]]
        sel_b = [z for z in nodes if not x[idx[z]]]
        return (nx.number_connected_components(H.subgraph(sel_a)) if sel_a else 0,
                nx.number_connected_components(H.subgraph(sel_b)) if sel_b else 0)

    def iterate(status, x, ga, gb, per, iters, message=""):
        return dict(status=status, to_a={nodes[i] for i in range(n) if x[i]},
                    k=int(x.sum()), g_a=float(ga), g_b=float(gb),
                    product=float(ga*gb), perimeter=per,
                    perimeter_true=int(sum(1 for i, j in E if x[i] != x[j])),
                    pieces=pieces_of(x), n_edges=m, iters=iters, message=message,
                    n_cuts=n_cuts, n_tangents=n_tangents, seed=seed, threads=threads)

    last = None
    for it in range(max_iter):
        tl = time_limit
        if deadline is not None:
            tl = min(time_limit, deadline - _time.time())
            if tl <= 0:
                if last is None:
                    return dict(status="time limit", iters=it, n_cuts=n_cuts,
                                n_tangents=n_tangents, seed=seed, threads=threads,
                                message="deadline reached before the first master solve")
                last.update(status="time limit", iters=it,
                            message="deadline reached between master solves")
                return last
        res = milp(c=c_obj, constraints=build(), integrality=integ,
                   bounds=Bounds(lo, hi), options=dict(time_limit=tl))
        if not res.success:
            out = dict(status="solver failed", message=str(res.message), iters=it,
                       n_cuts=n_cuts, n_tangents=n_tangents, seed=seed, threads=threads)
            if getattr(res, "x", None) is not None:
                x = np.round(res.x[:n]).astype(bool)
                ga = ua[x].sum() - Sa; gb = ub[~x].sum() - Sb
                out.update(iterate("solver failed", x, ga, gb,
                                   int(round(res.x[n+2:].sum())), it, str(res.message)))
            return out
        x = np.round(res.x[:n]).astype(bool)
        ga = ua[x].sum() - Sa; gb = ub[~x].sum() - Sb
        added = 0
        for side in ("a", "b"):
            root = root_a if side == "a" else root_b
            sel = [z for z in nodes if x[idx[z]] == (side == "a")]
            for S in nx.connected_components(H.subgraph(sel)):
                if nodes[root] in S: continue
                nb = {w for z in S for w in H.neighbors(z)} - S
                if not nb: continue
                k_ = len(S)
                if side == "a":
                    add([(idx[w], float(k_)) for w in nb] +
                        [(idx[v], -1.0) for v in S], 0, np.inf)
                else:
                    add([(idx[w], -float(k_)) for w in nb] +
                        [(idx[v], 1.0) for v in S], k_ - k_*len(nb), np.inf)
                added += 1; n_cuts += 1
        sa = res.x[IA] - (np.log(ga) if ga > 0 else -float(z_bound))
        sb = res.x[IB] - (np.log(gb) if gb > 0 else -float(z_bound))
        if ga > 0 and sa > 1e-6: tangent("a", ga); added += 1
        if gb > 0 and sb > 1e-6: tangent("b", gb); added += 1
        per = int(round(res.x[n+2:].sum()))
        last = iterate("iteration limit", x, ga, gb, per, it + 1)
        if verbose:
            print(f"    it {it:>2}: g_a={ga:8.4f} g_b={gb:8.4f} product={ga*gb:9.5f} "
                  f"log-slack {sa:.1e}/{sb:.1e}  cuts+={added}")
        if on_iter is not None:
            db = getattr(res, "mip_dual_bound", None)
            on_iter(dict(it=it, x=x.copy(), ga=float(ga), gb=float(gb),
                         master_obj=float(-res.fun),
                         dual_bound=float(-db) if db is not None else float("nan"),
                         added=added, n_cuts=n_cuts, n_tangents=n_tangents,
                         pieces=last["pieces"], perimeter_true=last["perimeter_true"]))
        if added == 0:
            last["status"] = "optimal"
            return last
    if last is None:
        return dict(status="iteration limit", iters=0, n_cuts=n_cuts,
                    n_tangents=n_tangents, seed=seed, threads=threads, message="max_iter=0")
    last["message"] = f"iteration limit ({max_iter}) reached"
    return last


def solve_contiguous(G, nodes, theta=0.40, lam=0.30, rho=1e-3, welfare_floor=0.95,
                     linear_w=None, min_gb=None,
                     root_a=None, root_b=None, respect_state=False,
                     max_rounds=30, time_limit=30.0, verbose=True):
    nodes = list(nodes); n = len(nodes); idx = {z: i for i, z in enumerate(nodes)}
    A = np.array([G.nodes[z]["A"] for z in nodes], float)
    B = np.array([G.nodes[z]["B"] for z in nodes], float)
    M = np.array([G.nodes[z]["M"] for z in nodes], float)
    c1, c2 = 1 - lam, theta * (1 - lam)
    ua, ub = c1*A + c2*B + lam*M, c2*A + c1*B + lam*M
    Sa, Sb = A.sum(), B.sum()
    Amax, Bmax = ua.sum() - Sa, ub.sum() - Sb

    H = G.subgraph(nodes).copy()
    if respect_state:
        H.remove_edges_from([(u, v) for u, v in H.edges()
                             if G.nodes[u].get("state") != G.nodes[v].get("state")])
    E = [(idx[u], idx[v]) for u, v in H.edges()]
    m = len(E)

    r = ua / ub
    if root_a is None: root_a = nodes[int(np.argmax(r))]
    if root_b is None: root_b = nodes[int(np.argmin(r))]

    # variables: x (n) | t (1) | y_e (m boundary indicators)
    NV = n + 1 + m
    c_obj = np.zeros(NV); c_obj[n+1:] = rho
    if linear_w is None:
        c_obj[n] = 1.0                          # minimise the KS gap
    else:
        # maximise w*g_a + (1-w)*g_b  ==  minimise  -(w*g_a + (1-w)*g_b)
        c_obj[:n] = -(linear_w * ua - (1 - linear_w) * ub)
    integ = np.zeros(NV); integ[:n] = 1
    lo_b = np.zeros(NV); hi_b = np.ones(NV); hi_b[n] = np.inf

    rows, rl, ru = [], [], []
    def add(pairs, lo, hi):
        rows.append(pairs); rl.append(lo); ru.append(hi)

    coef = ua/Amax + ub/Bmax
    const = -Sa/Amax - Bmax/Bmax
    add([(i, coef[i]) for i in range(n)] + [(n, -1.0)], -np.inf, -const)   # gap - t <= 0
    add([(i, -coef[i]) for i in range(n)] + [(n, -1.0)], -np.inf, const)   # -gap - t <= 0
    add([(idx[root_a], 1.0)], 1, 1)
    add([(idx[root_b], 1.0)], 0, 0)
    # WELFARE FLOOR: equalisation objectives can buy a small gap by making BOTH
    # wholesalers worse off. Require total gain within `welfare_floor` of the
    # utilitarian maximum, which is attained at the prefix {z : u_a(z) > u_b(z)}.
    if min_gb is not None:
        # g_b = sum_z (1-x_z) u_b(z) - Sb  >=  tau
        add([(i, -float(ub[i])) for i in range(n)], min_gb - (ub.sum() - Sb), np.inf)
    if welfare_floor is not None:
        d_ = ua - ub                       # total = sum_S d + (sum ub - Sa - Sb)
        base = ub.sum() - Sa - Sb
        wmax = d_[d_ > 0].sum() + base
        add([(i, float(d_[i])) for i in range(n)], welfare_floor * wmax - base, np.inf)
    for e, (i, j) in enumerate(E):                                         # y_e >= |x_i - x_j|
        add([(n+1+e, 1.0), (i, -1.0), (j, 1.0)], 0, np.inf)
        add([(n+1+e, 1.0), (i, 1.0), (j, -1.0)], 0, np.inf)

    def build():
        Amat = lil_matrix((len(rows), NV))
        for k, pr in enumerate(rows):
            for c_, v_ in pr: Amat[k, c_] += v_
        return LinearConstraint(csr_matrix(Amat), np.array(rl), np.array(ru))

    hist = []
    for rnd in range(max_rounds):
        res = milp(c=c_obj, constraints=build(), integrality=integ,
                   bounds=Bounds(lo_b, hi_b), options=dict(time_limit=time_limit))
        if not res.success:
            return dict(status="solver failed", message=str(res.message),
                        rounds=rnd, history=hist)
        x = np.round(res.x[:n]).astype(bool)
        to_a = {nodes[i] for i in range(n) if x[i]}
        cuts = 0; ca = cb = 0
        for side in ("a", "b"):
            root = root_a if side == "a" else root_b
            sel = [z for z in nodes if (z in to_a) == (side == "a")]
            comps = list(nx.connected_components(H.subgraph(sel)))
            if side == "a": ca = len(comps)
            else: cb = len(comps)
            for S in comps:
                if root in S: continue
                nb = {w for z in S for w in H.neighbors(z)} - S
                if not nb: continue
                k_ = len(S)
                if side == "a":
                    add([(idx[w], float(k_)) for w in nb] +
                        [(idx[v], -1.0) for v in S], 0, np.inf)
                else:
                    add([(idx[w], -float(k_)) for w in nb] +
                        [(idx[v], 1.0) for v in S], k_ - k_*len(nb), np.inf)
                cuts += 1
        ga = ua[x].sum() - Sa; gb = ub[~x].sum() - Sb
        gap = abs(ga/Amax - gb/Bmax); per = int(round(res.x[n+1:].sum()))
        hist.append(dict(round=rnd, gap=gap, perimeter=per, pieces=(ca, cb), cuts=cuts))
        if verbose:
            print(f"    round {rnd:>2}: gap={gap:.6f}  perimeter={per:>3}  "
                  f"pieces A/B={ca}/{cb}  cuts+={cuts}")
        if cuts == 0:
            return dict(status="optimal", to_a=to_a, k=int(x.sum()),
                        g_a=float(ga), g_b=float(gb), ks_gap=float(gap),
                        perimeter=per, rounds=rnd+1, history=hist)
    return dict(status="round limit", history=hist)
