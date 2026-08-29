"""
loop_v2.py -- Option G (W9a): the engineered multi-tree outer-approximation + connectivity
loop, rebuilt from scratch each round on `scipy.optimize.milp` (HiGHS).  Same master
structure as `districting.solve_contiguous_nash` (x binary, z_a, z_b continuous, edge
variables only when rho > 0, tangent rows, cut rows) -- `districting.py` itself is
untouched; this is a from-scratch re-engineering of the same idea with four fixes:

  G1  in-out stabilisation of the tangent step (Ben-Ameur & Neto 2007)
  G2  root-free minimal-separator connectivity cuts (Validi, Buchanan & Lykhovyd 2022 --
      CLAUDE.md trap 13: districting.py's single global root per side is *invalid*, not
      merely loose, on a pair graph with more than one connected component)
  G4  data-scaled initial tangents and z-variable box bounds (the legacy g0 in {1,3,5,8,11}
      and z in [-50,50] are absolute and wrong on dollar-scaled real data)

G3 (highspy warm start / threads) is dropped (OPTIONS.md S8): scipy's `milp` wrapper does
not expose HiGHS' callback API either way, so a "single-tree, lazily cut" engine is not on
the table here -- this module *is* the multi-tree design being measured, rebuilding the
LinearConstraint from an ever-growing row list every round.  It never touches
`districting.py`.  `base.lexi_perimeter`'s implementation (the lexicographic perimeter
post-pass, `solve_lexi` below) reuses the same tangent/cut machinery with the objective and
the value constraint swapped.

------------------------------------------------------------------ G1: in-out stabilisation
Kelley's cutting-plane method (repeatedly re-linearising at the master's own optimum) is
notoriously unstable near a kink -- CLAUDE.md trap 7's rho=0 thrash is exactly this.  In-out
stabilisation (Ben-Ameur & Neto 2007) separates instead at a point between the master's raw
optimum and a "stable centre": a point already known to be genuinely achievable.

Exact rule implemented here.  Maintain a stable centre (g_bar_a, g_bar_b): initially the
`warm_start` allocation's gains if one is given and is itself feasible with both gains
positive, else undefined.  After every master solve, for each side s in {a, b} with the
master's current point (g_hat_s = the actual gain of the rounded incumbent, z_s = the
master's z variable at that side):

    slack   = z_s - log(g_hat_s)
    g_tilde = g_hat_s                                        if no centre yet
            = lambda*g_hat_s + (1 - lambda)*g_bar_s           otherwise   (lambda = lambda_inout)
    if slack > tol: add a tangent at g_tilde (not at g_hat_s)

lambda_inout = 1.0 recovers plain Kelley (tangent always at the raw master point) --
`loop_v2_noinout`.  lambda_inout = 0.5 (default) tangents half-way toward the centre, giving
smaller, more stable steps once a centre exists.

The centre update runs *after* tangent placement for the round (so round k's tangent uses
round k-1's centre): if the current incumbent is contiguity-feasible and both gains are
positive, and its log g_a + log g_b exceeds the centre's, the centre moves to it.  This
still yields a *valid* outer approximation at every step regardless of lambda or where the
centre sits: a tangent to a concave function lies on or above the function everywhere, no
matter which point it was taken at (log(g_hat) + (g - g_hat)/g_hat >= log(g) for all g > 0,
any g_hat > 0), so g_tilde need not even be a feasible point for the tangent to be a valid
cut on the true log(g) curve.  In-out changes *where* tangents land, never whether they are
valid -- the exact-outer-approximation guarantee (Duran-Grossmann finite convergence) is
therefore unaffected; only the number of rounds needed changes.

Stall-breaking amendment, found while validating on `two_component_instance` (hand fixture,
`tests/test_loop_v2.py`).  A literal fixed-lambda reading of the rule above can stall: if the
centre does not move (the incumbent x is feasible but not better than the existing centre,
e.g. it ping-pongs between two components' local optima) and x itself repeats next round,
g_tilde is identical to last round's, so the "new" tangent is a duplicate row -- it tightens
nothing, x recurs a third time, and the loop never terminates (confirmed empirically: 500
rounds, no cuts, thousands of duplicate tangents, `two_component_instance` never converges
at lambda_inout=0.5 without this amendment).  Fix: track the previous round's `to_a`; if the
CURRENT round's `to_a` equals it, use lambda_eff = 1.0 (an exact tangent at g_hat, not the
interpolated g_tilde) for that round only, regardless of `lambda_inout`.  An exact tangent at
g_hat is tight there (touches the log curve), so it strictly removes the (x, z) pair that
just recurred -- either a different x becomes the master's argmax next round (real progress)
or the same x recurs with its z now capped at exactly log(g_hat) (no residual slack, so no
further tangent needed on that side, guaranteeing the stall cannot repeat a third time).
This is still a valid tangent under the same concavity argument, so exactness is unaffected;
it only prevents literal non-termination on instances where the interpolated point happens
to coincide with itself round after round.  `loop_v2_noinout` (lambda_inout=1.0) never
triggers this branch (it is already using the exact point every round).

------------------------------------------------------------- G2: root-free connectivity cuts
`districting.py` fixes one root per side and, for every a-side component not containing
root_a, forces its outside neighbours onto side a too.  CLAUDE.md trap 13: on a pair graph
with more than one connected component, that cut can target a stray component that can
never reach either root, and is then not merely loose but WRONG -- it can exclude points
that are genuinely feasible under the harness's own component-wise contiguity definition
(`base.pieces`).  This module never fixes a root at all.

At the current incumbent x, for every connected component K of the (fixed, x-independent)
pair graph and every side s, let the s-side pieces of K be the connected components of
{z in K : x_z is s}.  If there is more than one piece, let P be the largest and, for every
other piece Q, add ONE cut linking P and Q.  Two cut families (`cut_family`):

  "minimal" (default) -- a minimum vertex separator.  Pick u in P, v in Q minimising hop
    distance inside K (via one multi-source Dijkstra/BFS run from P; unweighted, so this is
    ordinary BFS).  u and v cannot be adjacent in K at this incumbent: if they were, and
    both are on side s (which they are, by construction of P and Q), that edge would already
    be an s-side edge inside K, merging P and Q into one piece -- contradiction.  So
    `nx.minimum_node_cut(K, u, v)` (Menger's theorem via max-flow) is always well-defined
    here.  Let C_min be that minimum cut.

    VALIDITY.  For side a: `sum_{w in C} x_w >= x_u + x_v - 1`.  If x_u = x_v = 1 (both on
    side a) and side a is connected within K (a requirement of any feasible allocation, by
    `base.pieces`'s per-component definition), there is a side-a path from u to v inside K.
    Every u-v path in K passes through C (C separates them), so that path uses at least one
    vertex of C, and since the path lies entirely on side a, that vertex is on side a too:
    sum_{w in C} x_w >= 1.  If x_u and x_v are not both 1 the right-hand side is <= 0 and the
    inequality is trivial (the left side is always >= 0).  The cut is therefore satisfied by
    *every* feasible allocation with u, v both on side a, and never restricts an allocation
    with u or v on side b -- so it never excludes the true optimum.  Side b is the mirror in
    (1 - x): `sum_{w in C} x_w <= x_u + x_v + |C| - 2` (equivalently `sum_C x_w - x_u - x_v
    <= |C| - 1`), by the same argument with "side a" replaced by "side b" throughout.

    TERMINATION / guaranteed progress.  A minimum separator can, in principle, contain a
    vertex that happens to sit on side s at the current x through some *third*, unrelated
    piece R (R is not adjacent to P or Q, since if it were it would already have merged with
    one of them) -- in which case the cut as stated is not violated by the current x, and
    adding it would not shrink the master's next answer, risking a stall.  This module
    therefore checks: is every vertex of C_min currently off side s (for side a: none of
    C_min assigned to a; for side b: none of C_min assigned to b)?  If not, it falls back to
    C = N(Q), the full external boundary of Q.  N(Q) is *always* a valid u-v separator too
    (removing it isolates Q from the rest of K entirely, and u is not in Q), and because Q is
    a *maximal* connected piece of the s-side subgraph, every external neighbour of Q is
    necessarily off side s right now (an on-side neighbour would already be part of Q's
    piece) -- so the N(Q) cut is *always* violated by the current incumbent, exactly like
    the legacy neighbourhood cut. Either way the added row excludes the current incumbent, so
    the master's finite discrete feasible region strictly shrinks every round that adds a
    cut; with finitely many binary vectors this is a finite process (standard cutting-plane
    termination).  `minimal=True` (default) additionally greedily drops any vertex from the
    chosen C whose removal still separates u from v (a fixed-point pass over `nx.has_path`
    on a restricted view) -- redundant when C = C_min (a *minimum* cut is already
    inclusion-minimal) but tightens the N(Q) fallback.

  "nbr" (`loop_v2_nbr`) -- the legacy neighbourhood-cut *shape*, made root-free by anchoring
    it on a canonical vertex u of P instead of a fixed global root.  Side a:

        |Q| * sum_{w in N(Q)} x_w  >=  sum_{v in Q} x_v  -  |Q| * (1 - x_u)

    When x_u = 1 (the anchor is on side a -- always true at generation time, since u in P and
    P is itself an a-side piece) this is exactly the legacy form `|Q| sum_{N(Q)} x_w >=
    sum_Q x_v` for the single piece Q, and by the N(Q) argument above (Q maximal => every
    external neighbour is off-side) it is violated by the current x.  When x_u = 0 the
    right-hand side collapses to `sum_Q x_v - |Q| <= 0`, always true, so the cut is inactive
    -- this is what makes it root-free and still valid: without an anchor, "the outside
    neighbours of Q must include an a-side vertex whenever Q is nonempty on side a" is false
    in general (Q could legitimately be the *only* a-side piece in K, with u itself on side
    b); conditioning on x_u makes the implication correct precisely when u, the piece the cut
    is drawn *from*, is really on side a.  Side b mirrors with (1 - x) throughout.

G2 cuts, once added, are never removed -- the row list only grows, and the master is rebuilt
from it every round (the multi-tree design this workstream measures).

--------------------------------------------------------------------------- G4: data-scaled seeds
Initial tangents seed at `np.geomspace(max(span*1e-3, 1e-3), span, 8)` PER SIDE, with
`span_a = sum(u_a)` and `span_b = sum(u_b)` (mirrors `territory.nash_exact`'s single-span
geomspace, split per side since the two totals can differ by an order of magnitude on real
data), plus a tangent at the warm start's own gains if one is given.  The z_a, z_b box bounds
are likewise data-scaled (`log(max(span*1e-6, 1e-12))` to `log(span) + 1`) rather than the
legacy absolute [-50, 50] -- flagged in PLAN.md Stage 0 as "absolute and wrong on
dollar-scaled data".

------------------------------------------------------------------------------- Certificate
`UB` = the running min, across rounds, of the master's dual bound (`res.mip_dual_bound`,
negated to maximisation units; falls back to `-res.fun`, the master's own fully-solved
value, when HiGHS reports no dual bound -- valid either way since every row ever added is a
provably necessary condition, so the master's feasible region always contains the true
feasible set: any real, feasible, positive-gain x satisfies every tangent for any g_hat by
concavity, and every G2 cut by the argument above).  `LB` = the best feasible incumbent's
`base.objective` value, recomputed with `perimeter_true` counted directly from `to_a`
(never from the edge variables).  Terminate `optimal` when a round adds no new cut or
tangent AND `UB - LB <= 1e-9`; `gap_limit` if it stalls (no new row) with a larger gap
(reported, should not happen given the termination argument above but guarded defensively);
`iteration_limit` at `max_iter` (default 500); `time_limit` if the wall-clock deadline is
reached first.  `ub_scope = "global"` always -- nothing here restricts the feasible set to a
root-fixed subproblem.

------------------------------------------------------------------------------------ Variants
`loop_v2` (lambda_inout=0.5, cut_family="minimal"), `loop_v2_noinout` (lambda_inout=1.0,
plain Kelley), `loop_v2_nbr` (cut_family="nbr").  `loop_v2_rho` is not registered: rho is a
plain keyword argument, not a variant.

--------------------------------------------------------------------------------- Determinism
No randomness anywhere (anchors are `min(..., key=base._sort_key)`; BFS/Dijkstra and
`minimum_node_cut` are deterministic given the graph; HiGHS through `scipy.optimize.milp`
is single-threaded and deterministic).  `seed` is accepted for contract conformance and
recorded nowhere else, exactly like `current.py`'s `seed, threads` note.
"""
from __future__ import annotations

import math
import time as _time
from typing import Optional

import networkx as nx
import numpy as np
from scipy.optimize import milp, LinearConstraint, Bounds
from scipy.sparse import lil_matrix, csr_matrix

from . import base

NAME = "loop_v2"
EXACT = True
MAX_N = None
VARIANTS = {
    "loop_v2_noinout": dict(lambda_inout=1.0),
    "loop_v2_nbr": dict(cut_family="nbr"),
}

_TANGENT_TOL = 1e-9       # tangent-violation trigger (matches territory.nash_exact's tol)
_CERT_TOL = 1e-9          # UB - LB <= this -> "optimal" (tighter than base.CERT_TOL=1e-8)


# --------------------------------------------------------------------------- small helpers
def _anchor(piece) -> object:
    """Canonical (deterministic) vertex of a piece: the smallest node under base._sort_key."""
    return min(piece, key=base._sort_key)


def _z_bounds(span: float) -> tuple:
    """Data-scaled box for a z_a / z_b variable (G4): replaces the legacy absolute [-50,50]."""
    lo = math.log(max(span * 1e-6, 1e-12))
    hi = math.log(max(span, 1e-12)) + 1.0
    return lo, hi


def _tangent_row(add, side: str, ghat: float, IA: int, IB: int, n: int, ua, ub) -> bool:
    """Append one supporting-hyperplane row for `side` at `ghat`.  Returns False (no row
    added) if ghat is not usably positive."""
    if ghat <= 1e-12:
        return False
    if side == "a":
        add([(IA, 1.0)] + [(i, -float(ua[i]) / ghat) for i in range(n)],
            -np.inf, math.log(ghat) - 1.0)
    else:
        add([(IB, 1.0)] + [(i, float(ub[i]) / ghat) for i in range(n)],
            -np.inf, math.log(ghat) - 1.0 + float(ub.sum()) / ghat)
    return True


def _shrink_separator(Ksub, u, v, C) -> set:
    """Greedily drop vertices from `C` while it still separates u from v in `Ksub` (a
    fixed-point pass; a *minimum* cut is already inclusion-minimal, so this mainly tightens
    the N(Q) fallback described in the module docstring)."""
    C = set(C)
    changed = True
    while changed:
        changed = False
        for w in sorted(C, key=base._sort_key):
            trial = C - {w}
            view = nx.restricted_view(Ksub, trial, [])
            if not nx.has_path(view, u, v):
                C = trial
                changed = True
                break
    return C


def _sep_cut(side: str, C, u, v, idx: dict) -> tuple:
    """(row, lo, hi) for the G2 "minimal" cut: `sum_C x_w - x_u - x_v` bounded as derived
    in the module docstring (>= -1 for side a; <= |C|-1 for side b)."""
    coeffs: dict = {}
    for w in C:
        coeffs[idx[w]] = coeffs.get(idx[w], 0.0) + 1.0
    coeffs[idx[u]] = coeffs.get(idx[u], 0.0) - 1.0
    coeffs[idx[v]] = coeffs.get(idx[v], 0.0) - 1.0
    row = list(coeffs.items())
    if side == "a":
        return row, -1.0, np.inf
    return row, -np.inf, float(len(C) - 1)


def _nbr_cut(side: str, Q, NQ, u, idx: dict) -> tuple:
    """(row, lo, hi) for the G2 "nbr" (anchored neighbourhood) cut, as derived in the
    module docstring."""
    k_ = float(len(Q))
    coeffs: dict = {}
    if side == "a":
        for w in NQ:
            coeffs[idx[w]] = coeffs.get(idx[w], 0.0) + k_
        for v in Q:
            coeffs[idx[v]] = coeffs.get(idx[v], 0.0) - 1.0
        coeffs[idx[u]] = coeffs.get(idx[u], 0.0) - k_
        return list(coeffs.items()), -k_, np.inf
    for w in NQ:
        coeffs[idx[w]] = coeffs.get(idx[w], 0.0) - k_
    for v in Q:
        coeffs[idx[v]] = coeffs.get(idx[v], 0.0) + 1.0
    coeffs[idx[u]] = coeffs.get(idx[u], 0.0) + k_
    return list(coeffs.items()), float(k_ - k_ * len(NQ)), np.inf


def _add_connectivity_cuts(H, comps, x, idx, nodes, add, *, cut_family="minimal",
                           minimal=True, debug_cuts=None) -> int:
    """Root-free G2 cuts (module docstring) for every excess piece of every component, both
    sides.  Returns the number of rows added."""
    added = 0
    for side in ("a", "b"):
        want = side == "a"
        for K in comps:
            if len(K) < 2:
                continue
            Ksub = H.subgraph(K)
            sel = [z for z in K if bool(x[idx[z]]) == want]
            if not sel:
                continue
            pieces_side = sorted(nx.connected_components(Ksub.subgraph(sel)),
                                 key=len, reverse=True)
            if len(pieces_side) <= 1:
                continue
            P = pieces_side[0]
            u_anchor = _anchor(P) if cut_family == "nbr" else None
            for Q in pieces_side[1:]:
                Qs = set(Q)
                NQ = {w for z in Qs for w in Ksub.neighbors(z)} - Qs
                if not NQ:
                    continue    # cannot happen: K is connected and Q is a proper subset of it
                if cut_family == "nbr":
                    row, lo_, hi_ = _nbr_cut(side, Qs, NQ, u_anchor, idx)
                else:
                    dist, paths = nx.multi_source_dijkstra(Ksub, sources=set(P))
                    v = min(Qs, key=lambda z: dist.get(z, math.inf))
                    if v not in dist:
                        continue   # cannot happen: K is connected
                    u = paths[v][0]
                    C = set(nx.minimum_node_cut(Ksub, u, v))
                    off_side = (all(not x[idx[w]] for w in C) if side == "a"
                               else all(x[idx[w]] for w in C))
                    if not off_side:
                        C = set(NQ)             # guaranteed-violated fallback (docstring)
                    if minimal:
                        C = _shrink_separator(Ksub, u, v, C)
                    row, lo_, hi_ = _sep_cut(side, C, u, v, idx)
                add(row, lo_, hi_)
                added += 1
                if debug_cuts is not None:
                    debug_cuts.append(dict(
                        side=side, kind=cut_family,
                        coeffs={nodes[c]: float(v_) for c, v_ in row},
                        lo=float(lo_), hi=float(hi_)))
    return added


def _milp_options(tl: float) -> dict:
    # HiGHS has a separate absolute-gap stopping rule (default ~1e-6) on top of
    # mip_rel_gap; found while validating on a 25-node grid instance (loop_v2_nbr): the
    # loop could stall at gap ~3.6e-7 -- comfortably under HiGHS' own default absolute
    # tolerance but above both _TANGENT_TOL and base.CERT_TOL -- with `added == 0` (no
    # tangent or cut violated) because HiGHS itself had already stopped branching once its
    # absolute gap closed, without driving the true dual bound all the way to the true
    # optimum. mip_abs_gap=0.0 closes that gap too.
    return dict(time_limit=tl, mip_rel_gap=0.0, mip_abs_gap=0.0,
               mip_feasibility_tolerance=1e-9, primal_feasibility_tolerance=1e-9)


def _build(rows, rl, ru, NV) -> LinearConstraint:
    Am = lil_matrix((len(rows), NV))
    for k, pr in enumerate(rows):
        for c_, v_ in pr:
            Am[k, c_] += v_
    return LinearConstraint(csr_matrix(Am), np.array(rl), np.array(ru))


def _warm_start_gains(H, nodes, ua, ub, warm_start):
    """Best-effort extraction of a `to_a`-shaped assignment from `warm_start` (no convention
    is established elsewhere in the harness yet -- W5 warm starts land later); tolerates
    `None`, a bare iterable of nodes, or anything exposing `.to_a`."""
    if warm_start is None:
        return None
    try:
        raw = warm_start.to_a if hasattr(warm_start, "to_a") else warm_start
        to_a = set(raw) & set(nodes)
    except TypeError:
        return None
    x = base.mask(nodes, to_a)
    ga, gb = base.gains(ua, ub, x)
    if ga > 0 and gb > 0 and base.is_feasible(H, nodes, to_a):
        return to_a, ga, gb
    return None


# =============================================================================== the solve
def solve(G, nodes, *, theta, lam, rho, respect_state, time_limit, seed,
         warm_start=None, reductions=None, trace=None, kappa=0.0,
         max_iter=500, lambda_inout=0.5, cut_family="minimal", minimal=True,
         check_cuts=False, **opts) -> base.Result:
    t_start = _time.perf_counter()
    deadline = t_start + time_limit

    nodes = list(nodes)
    n = len(nodes)
    idx = {z: i for i, z in enumerate(nodes)}
    ua, ub = base.utilities(G, nodes, theta, lam, kappa)

    H = G.subgraph(nodes)                       # never mutated; respect_state pre-filtered
    E = [(idx[u_], idx[v_]) for u_, v_ in H.edges()]
    m = len(E)
    comps = [frozenset(c) for c in nx.connected_components(H)]   # fixed; root-free

    IA, IB = n, n + 1
    has_edges = rho > 0 and m > 0
    NV = n + 2 + (m if has_edges else 0)

    rows: list = []; rl: list = []; ru: list = []
    def add(pairs, lo, hi):
        rows.append(pairs); rl.append(float(lo)); ru.append(float(hi))

    # -- zero-value-side guard (binding req #7): keep both gains strictly positive ---------
    pos_a = [i for i in range(n) if ua[i] > 0]
    pos_b = [i for i in range(n) if ub[i] > 0]
    if pos_a:
        add([(i, 1.0) for i in pos_a], 1, np.inf)
    if pos_b:
        add([(i, -1.0) for i in pos_b], 1 - len(pos_b), np.inf)

    # -- perimeter (edge) variables, only when rho > 0 (binding req #1) --------------------
    if has_edges:
        for e, (i, j) in enumerate(E):
            add([(n + 2 + e, 1.0), (i, -1.0), (j, 1.0)], 0, np.inf)
            add([(n + 2 + e, 1.0), (i, 1.0), (j, -1.0)], 0, np.inf)

    n_tangents = 0
    def tangent(side, ghat):
        nonlocal n_tangents
        if _tangent_row(add, side, ghat, IA, IB, n, ua, ub):
            n_tangents += 1

    # -- G4 data-scaled seeds ----------------------------------------------------------------
    span_a, span_b = float(ua.sum()), float(ub.sum())
    for g0 in np.geomspace(max(span_a * 1e-3, 1e-3), span_a, 8):
        tangent("a", float(g0))
    for g0 in np.geomspace(max(span_b * 1e-3, 1e-3), span_b, 8):
        tangent("b", float(g0))

    g_bar: Optional[tuple] = None                # stable centre (g_bar_a, g_bar_b)
    g_bar_val = -math.inf
    ws = _warm_start_gains(H, nodes, ua, ub, warm_start)
    if ws is not None:
        _, ga_ws, gb_ws = ws
        g_bar = (ga_ws, gb_ws)
        g_bar_val = math.log(ga_ws) + math.log(gb_ws)
        tangent("a", ga_ws); tangent("b", gb_ws)

    c_obj = np.zeros(NV); c_obj[IA] = c_obj[IB] = -1.0
    if has_edges:
        c_obj[n + 2:] = rho
    integ = np.zeros(NV); integ[:n] = 1
    lo = np.zeros(NV); hi = np.ones(NV)
    lo[IA], hi[IA] = _z_bounds(span_a)
    lo[IB], hi[IB] = _z_bounds(span_b)
    bounds = Bounds(lo, hi)

    best_obj = -math.inf
    best_to_a: Optional[set] = None
    own_ub = math.inf
    n_cuts = 0
    total_nodes_bb = 0
    rounds_with_cuts = rounds_with_tangents = stall_rounds = 0
    debug_cuts = [] if check_cuts else None

    status = "iteration_limit"
    message = ""
    it = -1
    prev_to_a: Optional[frozenset] = None
    for it in range(max_iter):
        tl = deadline - _time.perf_counter()
        if tl <= 0:
            status = "time_limit"
            message = "loop_v2: deadline reached before a master solve"
            break

        res = milp(c=c_obj, constraints=_build(rows, rl, ru, NV), integrality=integ,
                   bounds=bounds, options=_milp_options(tl))
        total_nodes_bb += int(getattr(res, "mip_node_count", 0) or 0)
        if getattr(res, "x", None) is None:
            status = "infeasible" if res.status == 2 else "error"
            message = f"loop_v2: solver returned no iterate ({res.message})"
            break

        x = np.round(res.x[:n]).astype(bool)
        to_a = {nodes[i] for i in range(n) if x[i]}
        ga, gb = base.gains(ua, ub, x)
        per_true = base.perimeter(H, nodes, to_a)
        feas = base.is_feasible(H, nodes, to_a)
        obj = base.objective(ua, ub, x, rho, per_true)

        if feas and math.isfinite(obj) and obj > best_obj:
            best_obj = obj
            best_to_a = to_a
            if trace is not None:
                trace.incumbent(to_a, obj)

        db = getattr(res, "mip_dual_bound", None)
        ub_round = -float(db) if (db is not None and np.isfinite(db)) else -float(res.fun)
        if ub_round < own_ub:
            own_ub = ub_round
        if trace is not None:
            trace.bound(own_ub)

        added = 0

        # ---- G1 in-out tangents (stall-breaking amendment: see module docstring) ----
        to_a_key = frozenset(to_a)
        lambda_eff = 1.0 if to_a_key == prev_to_a else lambda_inout
        prev_to_a = to_a_key
        for side, ghat, z_val in (("a", ga, res.x[IA]), ("b", gb, res.x[IB])):
            if ghat <= 1e-12:
                continue
            slack = float(z_val) - math.log(ghat)
            if slack > _TANGENT_TOL:
                centre = g_bar[0 if side == "a" else 1] if g_bar is not None else None
                g_tilde = ghat if centre is None else \
                          lambda_eff * ghat + (1.0 - lambda_eff) * centre
                tangent(side, g_tilde)
                added += 1
        if added:
            rounds_with_tangents += 1

        # move the stable centre (docstring: after this round's tangent, before the next)
        if feas and ga > 0 and gb > 0:
            cand_val = math.log(ga) + math.log(gb)
            if cand_val > g_bar_val:
                g_bar, g_bar_val = (ga, gb), cand_val

        # ---- G2 root-free connectivity cuts ----
        cuts_here = _add_connectivity_cuts(H, comps, x, idx, nodes, add,
                                           cut_family=cut_family, minimal=minimal,
                                           debug_cuts=debug_cuts)
        n_cuts += cuts_here
        added += cuts_here
        if cuts_here:
            rounds_with_cuts += 1

        gap = own_ub - best_obj
        if added == 0:
            if gap <= _CERT_TOL:
                status = "optimal"
            else:
                status = "gap_limit"
                stall_rounds += 1
                message = f"loop_v2: stalled with no new rows, gap {gap:.3e} nats"
            break
    else:
        status = "iteration_limit"
        message = f"loop_v2: iteration limit ({max_iter}) reached"

    iters = it + 1
    LB = best_obj if (best_to_a is not None and math.isfinite(best_obj)) else None
    UB = own_ub if math.isfinite(own_ub) else None
    extra = dict(lambda_inout=lambda_inout, cut_family=cut_family,
                rounds_with_cuts=rounds_with_cuts, rounds_with_tangents=rounds_with_tangents,
                stall_rounds=stall_rounds)
    if debug_cuts is not None:
        extra["cuts_debug"] = debug_cuts

    return base.Result(status=status, to_a=best_to_a, LB=LB, UB=UB, ub_scope="global",
                       iters=iters, n_cuts=n_cuts, n_tangents=n_tangents,
                       nodes=total_nodes_bb, extra=extra, message=message)


# ===================================================================== lexi post-pass engine
def solve_lexi(G, nodes, opt_value: float, *, theta: float = 0.40, lam: float = 0.30,
              kappa: float = 0.0, time_limit: float = 60.0, seed: int = 0,
              max_iter: int = 200, lambda_inout: float = 0.5, cut_family: str = "minimal",
              minimal: bool = True) -> dict:
    """Internal engine behind `base.lexi_perimeter` (W9a).  Minimise Sum boundary edges
    subject to hard contiguity and `log g_a + log g_b >= opt_value - 1e-9`.

    Same outer-approximation idea as `solve`, roles swapped: the tangent rows here upper-
    bound log g_a, log g_b (concavity, same as `solve`), so `z_a + z_b >= opt_value - 1e-9`
    is a RELAXATION of the true value floor, not an enforcement of it -- an x that satisfies
    it in the master need not satisfy it for real.  Every round therefore recomputes the
    incumbent's TRUE log g_a + log g_b; if it falls short, a tangent is added AT THAT EXACT
    (g_a, g_b) point (tight there, by construction of a tangent), permanently excluding that
    specific shortfall while never excluding a truly value-passing point (again: a tangent to
    a concave function never lies below it, anywhere).  Connectivity uses the identical G2
    root-free cuts as `solve`.  Termination is finite by the same cutting-plane argument: any
    round that does not return a genuine (feasible, value-passing) answer adds at least one
    row that the current incumbent violates (a tightened tangent, or a G2 cut -- see `solve`'s
    docstring for why G2 cuts are always violated at generation time), so the master's finite
    discrete feasible region strictly shrinks.

    Soundness note: this function's own return value is *not* trusted blindly -- `base.
    lexi_perimeter` independently recomputes gains, contiguity and the value floor on
    whatever `to_a` comes back and falls back to the untouched input allocation on any
    discrepancy (defence in depth against a bug here).
    """
    t_start = _time.perf_counter()
    deadline = t_start + time_limit
    nodes = list(nodes)
    n = len(nodes)
    idx = {z: i for i, z in enumerate(nodes)}
    ua, ub = base.utilities(G, nodes, theta, lam, kappa)

    H = G.subgraph(nodes)
    E = [(idx[u_], idx[v_]) for u_, v_ in H.edges()]
    m = len(E)
    comps = [frozenset(c) for c in nx.connected_components(H)]

    IA, IB = n, n + 1
    NV = n + 2 + m

    rows: list = []; rl: list = []; ru: list = []
    def add(pairs, lo, hi):
        rows.append(pairs); rl.append(float(lo)); ru.append(float(hi))

    pos_a = [i for i in range(n) if ua[i] > 0]
    pos_b = [i for i in range(n) if ub[i] > 0]
    if pos_a:
        add([(i, 1.0) for i in pos_a], 1, np.inf)
    if pos_b:
        add([(i, -1.0) for i in pos_b], 1 - len(pos_b), np.inf)

    for e, (i, j) in enumerate(E):
        add([(n + 2 + e, 1.0), (i, -1.0), (j, 1.0)], 0, np.inf)
        add([(n + 2 + e, 1.0), (i, 1.0), (j, -1.0)], 0, np.inf)

    # the value floor (relaxation; see docstring)
    add([(IA, 1.0), (IB, 1.0)], float(opt_value) - 1e-9, np.inf)

    def tangent(side, ghat):
        _tangent_row(add, side, ghat, IA, IB, n, ua, ub)

    span_a, span_b = float(ua.sum()), float(ub.sum())
    for g0 in np.geomspace(max(span_a * 1e-3, 1e-3), span_a, 8):
        tangent("a", float(g0))
    for g0 in np.geomspace(max(span_b * 1e-3, 1e-3), span_b, 8):
        tangent("b", float(g0))

    c_obj = np.zeros(NV); c_obj[n + 2:] = 1.0          # minimise perimeter directly (exact)
    integ = np.zeros(NV); integ[:n] = 1
    lo = np.zeros(NV); hi = np.ones(NV)
    lo[IA], hi[IA] = _z_bounds(span_a)
    lo[IB], hi[IB] = _z_bounds(span_b)
    bounds = Bounds(lo, hi)

    best_per: Optional[int] = None
    best_to_a: Optional[set] = None
    status = "iteration_limit"
    it = -1
    for it in range(max_iter):
        tl = deadline - _time.perf_counter()
        if tl <= 0:
            status = "time_limit"
            break
        res = milp(c=c_obj, constraints=_build(rows, rl, ru, NV), integrality=integ,
                   bounds=bounds, options=_milp_options(tl))
        if getattr(res, "x", None) is None:
            status = "infeasible" if res.status == 2 else "error"
            break

        x = np.round(res.x[:n]).astype(bool)
        to_a = {nodes[i] for i in range(n) if x[i]}
        ga, gb = base.gains(ua, ub, x)
        per_true = base.perimeter(H, nodes, to_a)
        feas = base.is_feasible(H, nodes, to_a)
        value_ok = ga > 0 and gb > 0 and (math.log(ga) + math.log(gb) >= opt_value - 1e-9)

        added = 0
        if not value_ok and ga > 0 and gb > 0:
            tangent("a", ga); tangent("b", gb)
            added += 2

        added += _add_connectivity_cuts(H, comps, x, idx, nodes, add,
                                        cut_family=cut_family, minimal=minimal)

        if feas and value_ok and (best_per is None or per_true < best_per):
            best_per, best_to_a = per_true, to_a

        if added == 0:
            status = "optimal" if (feas and value_ok) else "infeasible"
            break
    else:
        status = "iteration_limit"

    return dict(to_a=best_to_a, perimeter=(int(best_per) if best_per is not None else None),
               status=status, iters=it + 1)
