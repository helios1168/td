"""
prep.py -- Option E preprocessing (PLAN.md W8, OPTIONS.md #6): E1 safe reductions and
E3 component-quotient fixing, as wrappers around any other registered method.

    from contig_methods import REGISTRY
    spec = REGISTRY["prep_e1_current_tight"]     # inner="current_tight", rules=("e1",)
    res = base.run_method(spec.solve, G, nodes, time_limit=60, **spec.kwargs)

`solve(..., inner="current_tight", rules=("e1",), check=False, **opts)` builds a reduced
instance, hands it to `contig_methods.REGISTRY[inner].solve` (looked up lazily, inside
`solve`, to avoid a circular import at package-discovery time -- `REGISTRY` does not exist
yet while `contig_methods/__init__.py:discover()` is still importing this module), and
expands the reduced allocation back to the full node set before returning.

============================================================================ E1: safe rules
Two rules only, both restricted to *zero-value* zips (`u_a(z) = u_b(z) = 0`) so that where a
zip ends up can never change either side's gain -- only, at rho > 0, the perimeter.  Both are
proved safe *for the two-sided contiguity constraint* (both S and its complement must stay
connected within every pair component), which the one-sided PCST/MWCS literature this idea
comes from does not need to consider.  OPTIONS.md #6 flags this as the open risk; the proof:

  Rule L (zero-value leaf).  z has u_a(z) = u_b(z) = 0 and degree 1, with sole neighbour w.
  Remove z from the instance; after solving, assign z to w's side (whichever side that turns
  out to be).
    Safety.  Gains are unaffected (z contributes 0 to either sum).  Connectivity: z is a leaf,
    so removing it cannot disconnect anything else, and attaching it back to w's side cannot
    disconnect anything either (a pendant vertex attached to a connected set stays connected).
    The *other* completion -- assigning z to the side opposite w -- is also always feasible
    (z, alone, is trivially "connected"), so this is not a feasibility argument alone; it is
    an optimality argument: attaching z to w's side adds 0 boundary edges to the perimeter
    (the z-w edge is internal to one side), whereas attaching z to the other side adds exactly
    1 (the z-w edge crosses).  No other edge's crossing status changes either way, since z has
    no other edges.  So "z joins w's side" weakly dominates for every rho >= 0, with strict
    dominance whenever rho > 0 -- it is never worse and is the unique optimal choice once
    rho > 0.  This is exactly the classical PCST free-leaf argument, but the equal-or-better
    conclusion (rather than the one-sided "z is free money") is what makes it hold with *two*
    sides needing to stay connected: neither side's connectivity is ever put at risk by the
    choice, so the argument reduces to the pure perimeter comparison above.

  Rule C (zero-value degree-2 chain).  A maximal path w - z_1 - ... - z_k - w' of zero-value,
  degree-2 zips (w, w' are the first non-chain nodes reached in each direction; they may
  coincide -- see the pendant-cycle case below).  Contract the chain to a single edge (w, w')
  (noting a multiplicity if that edge already exists in the graph -- see the caveat below).
    Safety, w != w'.  Bijection between feasible allocations of the reduced and the original
    instance, of *equal* objective:
      (i) If w and w' land on the same side after solving the reduced instance, the entire
          chain joins that side.  Every chain zip contributes 0 gain.  Connectivity: the chain
          is a simple path whose only external attachments are at its two ends, both now on
          the same side, so appending the whole path to that side keeps it one connected
          piece; nothing on the *other* side is touched.  Perimeter: the contracted edge (w,w')
          was internal (both ends same side, 0 crossings); the expanded chain also contributes
          0 crossings, since every edge of the path now has both endpoints on the joining side.
      (ii) If w and w' land on different sides, the chain must be split at exactly one interior
           point: the prefix (nearest w) joins w's side, the suffix (nearest w') joins w's
           side.  *Any* split point is feasible -- each half is a path attached at one end to
           an already-connected, correctly-sided node, and the two halves never touch each
           other once separated by the split.  Perimeter: whichever point is chosen, the chain
           contributes exactly 1 crossing edge (the one edge at the split), matching the
           contracted edge (w,w')'s own single crossing when w, w' differ.  So the choice of
           split point is a genuine degeneracy in the optimum (any split gives the same
           objective) -- `to_a` after expansion is therefore not unique on such chains, only
           the objective is; the code splits at the chain's midpoint, and tests check
           objective/feasibility equality rather than a specific `to_a` on split chains.
      Restricting the original instance's feasible allocations to the reduced node set (drop
      the chain zips, replace them with the single edge they contracted to) is the inverse map,
      and is exact by the same argument run backwards.  So the reduced instance's optimum
      equals the original's, and every optimal-on-reduced allocation expands to an
      optimal-on-original one.
    Safety, w == w' (pendant cycle).  The chain's *only* attachment to the rest of the graph
    is the single vertex w (both walks from an interior zip reach the same boundary node --
    the chain plus w forms a cycle hanging off the rest of the graph at w alone).  There is no
    "other side" for the chain to reach: whichever side w ends up on, the whole chain must go
    with it (it cannot reach the opposite side without passing back through w, which is already
    claimed).  No edge is contracted (there is nothing on "the other end" to connect to); the
    chain zips are simply assigned to w's side, exactly as in Rule L, and by the same argument
    (0 gain, and joining w's side cannot add a crossing since no interior chain edge ever
    touches the opposite side).
    Caveat (both cases).  If the graph already has a direct (w, w') edge alongside the chain,
    contraction would try to add a second (w, w') edge; `nx.Graph` cannot represent that, so
    the code records a `mult` attribute on the surviving edge instead of erroring.  This means
    the *reduced graph's own* internal perimeter accounting (used only by an inner method's own
    rho > 0 objective while it solves the reduced instance) can under-count by the multiplicity
    minus one in that rare case.  It does not affect correctness at rho = 0 (the model; PLAN.md
    "Decisions taken"), and does not affect this wrapper's own `LB`, which is always recomputed
    on the *full*, unreduced graph (see below) -- only a rho > 0 *inner* solve's internal search
    could, in principle, be marginally misled.  Not fixed here; flagged, not exercised by any
    T0/T1 zero-value zip in this repo's synthetic instances.
    What is deliberately NOT implemented.  The more general PCST-style rule -- "any zero-value
    zip whose removal does not disconnect either side's candidate region is free" -- needs a
    disconnection check that depends on which side the removed zip's neighbours end up on, so
    it is not a *structural* (topology-only) reduction the way L and C are; OPTIONS.md #6 notes
    it as future work.  Only L and C are applied here.

Guarantee.  E1 preserves the inner method's certificate exactly: because every rule above is an
objective- and feasibility-preserving bijection, the inner method's `UB` (a bound on the
*reduced* problem's optimum) is, by the equalities proved above, also a valid bound on the
*full* problem's optimum -- so it is returned unchanged as this wrapper's `UB`.  `LB` is never
taken from the inner method, though; it is always recomputed here via `base.objective` on the
*expanded* allocation against the *full* instance, per the harness contract (`base.py`: "what
the harness recomputes, never trusts").

============================================================================ E3: quotient
No published precedent (OPTIONS.md #6); **not** optimality-preserving in general.  Compute the
free (no-contiguity) Nash allocation (`bounds.ub_free_nash`).  Within each connected component
of the pair graph, a "stray" is any connected piece of one side other than that side's largest
piece (measured by node count) -- i.e. every fragment the free solve produced beyond the one
"main" piece per side per component.  Each stray is contracted to a single super-node (summed
A, B, M -- utilities are linear, so this is exact) with edges to the union of its boundary
neighbours.  The inner method then solves on this quotient graph and decides, as one block,
which side every stray goes to -- this is a "block-quotient" E3, not literally "fixed in place":
fixing a stray's *exact* free-Nash side would need a per-instance constraint the generic
`solve(...)` contract has no slot for, so the wrapper instead removes the stray's internal
fragmentation (the actual failure mode E3 targets) while leaving the inner method free to place
the whole block optimally.  This changes the feasible set relative to the true problem (a stray
can no longer be split across the boundary the way the true optimum might place it), so it is a
heuristic: never `status="optimal"`, always `UB=None`.  `status` otherwise mirrors the inner
method's, downgraded (`_e3_status`): the inner's own "optimal" or any non-time-limit non-
terminal status becomes "heuristic" (a certificate on the quotient is not a certificate on the
original); "infeasible"/"error" pass through unchanged; "time_limit" passes through unchanged
(it is still an honest description of what happened).  Feasibility of the expansion is
guaranteed: each super-node is contracted from a connected node set, so replacing it with that
set in a solution that treats the super-node as an atomic unit yields a connected set again
(standard quotient-graph feasibility argument -- a bipartition connected in the quotient expands
to a connected bipartition in the original whenever every contracted blob is itself connected,
which every stray is by construction).  `n_strays` and `stray_share_u` (the strays' share of
total zip utility mass) are reported in `extra` so the harness can see how much of the instance
E3 actually touched.

`rules=("e1", "e3")` (the `prep_e13_*` variants) applies E1 first, then E3 on the already
E1-reduced graph, then solves, then expands back through E3's map and finally E1's.
"""
from __future__ import annotations

import math
import time

import networkx as nx

from . import base

NAME = "prep"
EXACT = True    # true for every E1-only variant; E3 variants enforce non-"optimal" at runtime
MAX_N = None

VARIANTS = {
    "prep_e1_brute":          dict(inner="brute",        rules=("e1",)),
    "prep_e1_current_tight":  dict(inner="current_tight", rules=("e1",)),
    "prep_e1_current_tu":     dict(inner="current_tu",    rules=("e1",)),
    # "flow" (Option D) has not landed yet as of this workstream; until it does, this variant
    # produces a clean status="error" row (see the REGISTRY lookup in solve() below) rather
    # than crashing the harness -- flip to a real inner once flow.py exists.
    "prep_e1_flow":           dict(inner="flow",          rules=("e1",)),
    "prep_e3_current_tight":  dict(inner="current_tight", rules=("e3",)),
    "prep_e13_current_tight": dict(inner="current_tight", rules=("e1", "e3")),
}


# ============================================================================== E1 machinery
def _walk_chain(Hr, start, zero, global_visited):
    """From a zero-value degree-2 `start`, walk both directions along zero-value degree-2
    nodes.  Returns (interior_ordered_w_to_wprime, w, wprime), or (None, None, None) if the
    walk runs into an already-visited chain node (a fully isolated zero-value cycle with no
    real boundary -- degenerate; left unreduced, not covered by rules L/C)."""
    nbrs = list(Hr.neighbors(start))
    if len(nbrs) != 2:
        return None, None, None
    local_visited = {start}

    def walk(cur, prev):
        path = []
        while True:
            ok = (cur in zero and cur not in global_visited and cur not in local_visited
                  and Hr.degree(cur) == 2)
            if not ok:
                return path, cur
            local_visited.add(cur)
            path.append(cur)
            nxts = [x for x in Hr.neighbors(cur) if x != prev]
            if len(nxts) != 1:
                return path, cur
            prev, cur = cur, nxts[0]

    left_path, w = walk(nbrs[0], start)
    right_path, wp = walk(nbrs[1], start)
    interior = list(reversed(left_path)) + [start] + right_path
    if w in interior or wp in interior:
        return None, None, None
    return interior, w, wp


def _reduce_e1(G, nodes, theta, lam, kappa):
    """Apply Rule L and Rule C to a fixpoint.  Returns (Hr, nodes_r, leaf_assign,
    chain_records, rules_fired).  `leaf_assign[z] = w` covers both true leaves and
    pendant-cycle interiors (both are "z joins w's side" completions).  `chain_records` is a
    list of dict(w=, wprime=, interior=[...], loop=bool) for the w != w' (split-or-join) case
    and the w == w' (pendant-cycle) case alike, kept for reporting even though pendant-cycle
    expansion is driven by `leaf_assign`."""
    ua, ub = base.utilities(G, nodes, theta, lam, kappa)
    zero = {z for z, a, b in zip(nodes, ua, ub) if abs(a) < 1e-9 and abs(b) < 1e-9}
    Hr = G.subgraph(nodes).copy()
    leaf_assign: dict = {}
    chain_records: list = []
    fired = {"L": 0, "C": 0}

    changed = True
    while changed:
        changed = False
        progressed = True
        while progressed:
            progressed = False
            for z in [z for z in zero if z in Hr and Hr.degree(z) == 1]:
                w = next(iter(Hr.neighbors(z)))
                leaf_assign[z] = w
                Hr.remove_node(z)
                fired["L"] += 1
                progressed = True
                changed = True

        visited: set = set()
        for z in [z for z in zero if z in Hr and Hr.degree(z) == 2]:
            if z in visited:
                continue
            interior, w, wp = _walk_chain(Hr, z, zero, visited)
            if interior is None:
                continue
            visited.update(interior)
            Hr.remove_nodes_from(interior)
            if w == wp:
                for iz in interior:
                    leaf_assign[iz] = w
                chain_records.append(dict(w=w, wprime=wp, interior=list(interior), loop=True))
            else:
                if Hr.has_edge(w, wp):
                    Hr[w][wp]["mult"] = Hr[w][wp].get("mult", 1) + 1
                else:
                    Hr.add_edge(w, wp, mult=1)
                chain_records.append(dict(w=w, wprime=wp, interior=list(interior), loop=False))
            fired["C"] += 1
            changed = True

    nodes_r = sorted(Hr.nodes(), key=base._sort_key)
    return Hr, nodes_r, leaf_assign, chain_records, fired


def _expand_e1(to_a_reduced, leaf_assign, chain_records):
    to_a = set(to_a_reduced)
    for z, w in leaf_assign.items():
        if w in to_a:
            to_a.add(z)
    for rec in chain_records:
        if rec["loop"]:
            continue
        w, wp, interior = rec["w"], rec["wprime"], rec["interior"]
        w_in, wp_in = (w in to_a), (wp in to_a)
        if w_in == wp_in:
            if w_in:
                to_a.update(interior)
        else:
            mid = len(interior) // 2
            for i, z in enumerate(interior):
                if (w_in if i < mid else wp_in):
                    to_a.add(z)
    return to_a


def _debug_check_e1(G, nodes, theta, lam, kappa, rho):
    """check=True: brute on the E1-reduced graph, expanded, must equal brute on the original
    graph (within float tolerance).  Independent of `inner`/`rules`; skipped silently above
    `brute.MAX_N`."""
    from contig_methods import REGISTRY   # noqa: PLC0415 -- lazy, see module docstring
    brute_spec = REGISTRY.get("brute")
    if brute_spec is None or len(nodes) > brute_spec.max_n:
        return
    Hr, nodes_r, leaf_assign, chain_records, _ = _reduce_e1(
        G.subgraph(nodes).copy(), list(nodes), theta, lam, kappa)
    if len(nodes_r) > brute_spec.max_n:
        return
    res_r = brute_spec.solve(Hr, nodes_r, theta=theta, lam=lam, rho=rho, respect_state=False,
                             time_limit=30.0, seed=0)
    res_o = brute_spec.solve(G, list(nodes), theta=theta, lam=lam, rho=rho, respect_state=False,
                             time_limit=30.0, seed=0)
    to_a_x = _expand_e1(set(res_r.to_a), leaf_assign, chain_records)
    ua, ub = base.utilities(G, nodes, theta, lam, kappa)
    per = base.perimeter(G, nodes, to_a_x)
    obj_x = base.objective(ua, ub, base.mask(nodes, to_a_x), rho, per)
    if abs(obj_x - res_o.LB) > 1e-9:
        raise AssertionError(
            f"prep check=True: E1 reduction changed the optimum: expanded {obj_x!r} vs "
            f"brute-on-original {res_o.LB!r}")


# ============================================================================== E3 machinery
def _reduce_e3(G, nodes, theta, lam, kappa):
    """Block-quotient E3 (see module docstring).  Returns (Hq, nodes_q, stray_map, n_strays,
    stray_share_u).  `stray_map[supernode] = frozenset(original zips)`."""
    from contig_methods import bounds as boundsmod   # noqa: PLC0415 -- lazy (W2 module)
    free = boundsmod.ub_free_nash(G, nodes, theta, lam, kappa=kappa)["to_a"]

    sub = G.subgraph(nodes)
    strays: list = []
    for K in nx.connected_components(sub):
        Sa = [z for z in K if z in free]
        Sb = [z for z in K if z not in free]
        for S in (Sa, Sb):
            if len(S) <= 1:
                continue
            pieces_ = list(nx.connected_components(sub.subgraph(S)))
            if len(pieces_) <= 1:
                continue
            pieces_sorted = sorted(pieces_, key=len, reverse=True)
            strays.extend(pieces_sorted[1:])

    if not strays:
        return G, list(nodes), {}, 0, 0.0

    ua, ub = base.utilities(G, nodes, theta, lam, kappa)
    u_map = {z: float(a) + float(b) for z, a, b in zip(nodes, ua, ub)}
    total_u = sum(u_map.values())

    stray_of, stray_map = {}, {}
    for i, S in enumerate(strays):
        sn = ("stray", i)
        stray_map[sn] = frozenset(S)
        for z in S:
            stray_of[z] = sn

    Hq = nx.Graph()
    for z in nodes:
        if z not in stray_of:
            Hq.add_node(z, **G.nodes[z])
    for sn, S in stray_map.items():
        A = sum(float(G.nodes[z]["A"]) for z in S)
        B = sum(float(G.nodes[z]["B"]) for z in S)
        M = sum(float(G.nodes[z]["M"]) for z in S)
        attrs = dict(A=A, B=B, M=M)
        states = {G.nodes[z].get("state") for z in S}
        if len(states) == 1:
            attrs["state"] = next(iter(states))
        Hq.add_node(sn, **attrs)

    added: set = set()
    for u, v in sub.edges():
        su = stray_of.get(u, u)
        sv = stray_of.get(v, v)
        if su == sv:
            continue
        key = frozenset((su, sv))
        if key in added:
            continue
        added.add(key)
        Hq.add_edge(su, sv)

    nodes_q = sorted(Hq.nodes(), key=base._sort_key)
    n_strays = len(strays)
    stray_u = sum(u_map[z] for S in strays for z in S)
    stray_share = (stray_u / total_u) if total_u > 0 else 0.0
    return Hq, nodes_q, stray_map, n_strays, float(stray_share)


def _expand_e3(to_a_reduced, stray_map):
    to_a = set()
    for z in to_a_reduced:
        if z in stray_map:
            to_a.update(stray_map[z])
        else:
            to_a.add(z)
    return to_a


def _e3_status(inner_status: str) -> str:
    if inner_status in ("infeasible", "error", "time_limit"):
        return inner_status
    return "heuristic"    # optimal, gap_limit, iteration_limit, heuristic all downgrade


# =================================================================================== solve()
def solve(G, nodes, *, theta, lam, rho, respect_state, time_limit, seed,
         warm_start=None, reductions=None, trace=None, kappa=0.0,
         inner="current_tight", rules=("e1",), check=False, **opts) -> base.Result:
    t0 = time.perf_counter()
    from contig_methods import REGISTRY   # noqa: PLC0415 -- avoids the discovery-time cycle
    nodes = list(nodes)

    if inner not in REGISTRY:
        return base.Result(
            status="error",
            message=f"prep: inner method {inner!r} not registered (available: "
                    f"{sorted(REGISTRY)}) -- this variant will start producing rows once "
                    f"that method lands",
            extra=dict(n_before=len(nodes), n_after=None, rules_fired={},
                      articulation_points=[], t_reduce=0.0, inner_status=None, inner_extra={},
                      n_strays=0, stray_share_u=0.0))
    mspec = REGISTRY[inner]

    sub_full = G.subgraph(nodes)
    artic = sorted(nx.articulation_points(sub_full), key=base._sort_key)
    ua_full, ub_full = base.utilities(G, nodes, theta, lam, kappa)

    if check and "e1" in rules:
        _debug_check_e1(G, nodes, theta, lam, kappa, rho)

    cur_G, cur_nodes = G.subgraph(nodes).copy(), list(nodes)
    rules_fired: dict = {}
    leaf_assign, chain_records = {}, []
    stray_map, n_strays, stray_share_u = {}, 0, 0.0

    if "e1" in rules:
        n_comp_before = nx.number_connected_components(sub_full)
        cur_G, cur_nodes, leaf_assign, chain_records, fired = _reduce_e1(
            cur_G, cur_nodes, theta, lam, kappa)
        rules_fired.update(fired)
        n_comp_after = nx.number_connected_components(cur_G)
        assert n_comp_after == n_comp_before, (
            f"prep E1: reduction changed pair-component count {n_comp_before} -> "
            f"{n_comp_after} (should be a no-op on component structure)")

    if "e3" in rules:
        cur_G, cur_nodes, stray_map, n_strays, stray_share_u = _reduce_e3(
            cur_G, cur_nodes, theta, lam, kappa)

    t_reduce = time.perf_counter() - t0
    inner_time_limit = max(0.0, time_limit - t_reduce)

    res_inner = mspec.solve(cur_G, cur_nodes, theta=theta, lam=lam, rho=rho,
                            respect_state=False, time_limit=inner_time_limit, seed=seed,
                            warm_start=warm_start, reductions=reductions, trace=trace,
                            kappa=kappa, **dict(mspec.kwargs))

    extra = dict(n_before=len(nodes), n_after=len(cur_nodes), rules_fired=rules_fired,
                articulation_points=artic, t_reduce=t_reduce, inner_status=res_inner.status,
                inner_extra=res_inner.extra, n_strays=n_strays, stray_share_u=stray_share_u)

    if res_inner.to_a is None:
        status, UB = res_inner.status, res_inner.UB
        if "e3" in rules:
            status, UB = _e3_status(res_inner.status), None
        return base.Result(status=status, to_a=None, LB=None, UB=UB,
                           ub_scope=res_inner.ub_scope, eps=res_inner.eps, iters=res_inner.iters,
                           n_cuts=res_inner.n_cuts, n_tangents=res_inner.n_tangents,
                           nodes=res_inner.nodes, message=res_inner.message, extra=extra)

    to_a = set(res_inner.to_a)
    if "e3" in rules:
        to_a = _expand_e3(to_a, stray_map)
    if "e1" in rules:
        to_a = _expand_e1(to_a, leaf_assign, chain_records)

    feas = base.is_feasible(G, nodes, to_a)
    if check:
        reduced_feas = base.is_feasible(cur_G, cur_nodes, res_inner.to_a)
        if reduced_feas and not feas:
            raise AssertionError(
                "prep check=True: expansion produced an infeasible full allocation from a "
                "feasible reduced iterate")

    if feas:
        per = base.perimeter(G, nodes, to_a)
        LB = base.objective(ua_full, ub_full, base.mask(nodes, to_a), rho, per)
        if not math.isfinite(LB):
            LB = None
    else:
        LB = None

    status, UB = res_inner.status, res_inner.UB
    if "e3" in rules:
        status, UB = _e3_status(res_inner.status), None

    return base.Result(status=status, to_a=to_a, LB=LB, UB=UB, ub_scope=res_inner.ub_scope,
                       eps=res_inner.eps, iters=res_inner.iters, n_cuts=res_inner.n_cuts,
                       n_tangents=res_inner.n_tangents, nodes=res_inner.nodes,
                       message=res_inner.message, extra=extra)
