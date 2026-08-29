"""
warm.py -- Option F warm starts (PLAN.md OPTIONS.md sec:7; W5): F1 spanning-tree
bisection + boundary-swap local search, and F3 OT-threshold construction feeding the
same local search.  `EXACT = False`: neither variant produces a bound, so every row
this module writes is `status="heuristic"`, `UB=None` (`base.evaluate` enforces that
pairing).  No guarantee on welfare; gap is a cross-method question the harness answers
by comparing against the best UB from an exact option (bounds.py, current, etc).

Feasibility is component-wise (PLAN.md C.0 #1 / `base.pieces`): the pair graph may be
disconnected, and every construction here works per connected component of the
(already state-filtered) pair graph, then combines the per-component choices.  Both
constructors are followed by the same contiguity-preserving boundary-swap local search
(`_local_search`).  `base.is_feasible` is asserted on every allocation returned to the
caller; a violation is a bug in this module, not a shrug -- it raises, which
`base.run_method` turns into a `status="error"` row rather than a silently-wrong one.

F1 -- spanning-tree bisection (ReCom-style)
--------------------------------------------
Per component `K`: draw `n_trees` randomized spanning trees of `K` (a randomised
BFS/DFS hybrid: at each step, pop a uniformly random node off the growing frontier
and add its unvisited neighbours in random order -- cheap, diverse, no claim of a
uniform spanning-tree distribution, which this heuristic does not need).  A single
post-order accumulation per tree gives, for every non-root node `v`, the two
one-cut candidates "subtree(v) -> A, rest -> B" and "subtree(v) -> B, rest -> A" in
O(|K|) total (no O(|K|^2) blow-up from materialising every candidate's node set: a
bounded min-heap keeps the best `keep` candidates by `log(ga)+log(gb)` across all
trees, and only the *survivors'* node sets are ever reconstructed, by walking the
one retained tree's parent pointers).  Plus the two trivial "whole component to A /
to B" candidates (needed when `|K| == 1`, and generally safe to keep).

Combining across components (binding requirement #2): with <= 3 components and a
handful of candidates each, an exhaustive product search (`_combine`) finds the true
joint argmax over the candidate sets (obj is additive in each component's (ga, gb,
per) contribution, exactly as in `brute.py`'s multi-component combination -- same
argument, no shared code, since this is a heuristic and brute's bitmask machinery
does not scale to |K| ~ 400).  Above `MAX_COMBO` combinations (many components, the
"(d) sparse active zips" regime), a coordinate-ascent pass over the same candidate
lists is used instead: always feasible, not guaranteed globally optimal over the
candidate sets, but this whole module carries no guarantee regardless.

F3 -- OT-threshold warm start
------------------------------
Smooth `u_a, u_b` by `k` steps of `x <- 0.5*x + 0.5*mean(neighbours)` (isolated nodes
unchanged), threshold at the free-Nash ratio `lambda* = g_a/g_b` from
`contig_methods.bounds.ub_free_nash` (the harness's own method-independent bound, so
no per-method free-Nash recomputation), then repair connectivity component-by-
component: iteratively flip the smallest ("stray") pieces of a side onto the other
side whenever that keeps the other side connected, until each component has at most
one piece per side.  A component that cannot be repaired within a bounded number of
iterations falls back to its own F1 candidate list's best single cut (`_component_
candidates` is shared machinery, not a second implementation).  Both branches then
run the identical local search.

Local search (binding requirement #4)
--------------------------------------
First-improvement boundary swaps in deterministic (sorted) node order.  A boundary
zip `z` on side `S` may move to the other side iff (i) `z` is not an articulation
point of `G[S]` restricted to `z`'s own connected piece (checked via
`nx.articulation_points` on the *whole* current side -- this is correct on a
disconnected side too, since networkx computes articulation points component-by-
component) -- losing `z` then leaves that piece connected, or empty if `z` was its
only member, both feasible -- and (ii) `z` has a neighbour already on the other side,
so gaining `z` cannot disconnect the destination piece.  Every accepted move updates
`g_a, g_b` and the perimeter exactly (O(deg(z))); the reported `LB` is always
recomputed once more via `base.objective` on the final allocation, never trusted from
the incremental running total, so it matches what `base.evaluate` will independently
recompute.  Bounded by `swap_cap` and `time_limit` (a wall-clock deadline checked
inside both the tree-cut and local-search loops, so a small `time_limit` degrades
gracefully to whatever trivial-but-feasible allocation is on hand, never to nothing).

Determinism (binding requirement #6): `np.random.default_rng(seed)` is the only source
of randomness (spanning-tree draws); the local search and the repair pass are both
deterministic given their input allocation, so `warm_f1`/`warm_f3_*` reproduce their
`to_a` bit-for-bit at fixed `seed`.  Single-threaded; `G` is never mutated (module
functions only ever read node/edge attributes off it).
"""
from __future__ import annotations

import heapq
import itertools
import math
import time

import networkx as nx
import numpy as np

from . import base
from . import bounds

NAME = "warm"
EXACT = False

DEFAULT_N_TREES = 50
DEFAULT_KEEP = 8            # per-component candidates kept for the combine step
MAX_COMBO = 5000            # cap on the exhaustive cross-component product search

VARIANTS = {
    "warm_f1": dict(method="f1"),
    "warm_f1_n200": dict(method="f1", n_trees=200),
    "warm_f3_k1": dict(method="f3", k=1),
    "warm_f3_k2": dict(method="f3", k=2),
    "warm_f3_k4": dict(method="f3", k=4),
}


def solve(G, nodes, *, theta, lam, rho, respect_state, time_limit, seed,
          warm_start=None, reductions=None, trace=None, kappa=0.0,
          method="f1", n_trees=DEFAULT_N_TREES, k=2, swap_cap=None,
          keep=DEFAULT_KEEP, **opts) -> base.Result:
    t0 = time.perf_counter()
    tl = float(time_limit) if time_limit else 30.0
    deadline = t0 + max(1.0, tl)

    nodes = list(nodes)
    n = len(nodes)
    ua, ub = base.utilities(G, nodes, theta, lam, kappa)
    ua_map = {z: float(ua[i]) for i, z in enumerate(nodes)}
    ub_map = {z: float(ub[i]) for i, z in enumerate(nodes)}
    rng = np.random.default_rng(seed)
    if swap_cap is None:
        swap_cap = min(max(4 * n, 200), 4000)

    comps = [sorted(c, key=base._sort_key)
             for c in nx.connected_components(G.subgraph(nodes))]

    if method == "f1":
        to_a0, extra0 = _f1_construct(G, comps, ua_map, ub_map, rho, rng, n_trees,
                                      deadline, keep)
    elif method == "f3":
        to_a0, extra0 = _f3_construct(G, nodes, comps, ua_map, ub_map, theta, lam,
                                      kappa, rho, rng, k, n_trees, deadline, keep)
    else:
        raise ValueError(f"warm: unknown method {method!r}")

    if not base.is_feasible(G, nodes, to_a0):
        raise RuntimeError(f"warm/{method}: constructed allocation is infeasible")

    x0 = base.mask(nodes, to_a0)
    per0 = base.perimeter(G, nodes, to_a0)
    obj0 = base.objective(ua, ub, x0, rho, per0)

    to_a, n_swaps = _local_search(G, nodes, ua_map, ub_map, to_a0, rho, deadline, swap_cap)

    if not base.is_feasible(G, nodes, to_a):
        raise RuntimeError(f"warm/{method}: local search produced an infeasible allocation")

    x_f = base.mask(nodes, to_a)
    per_f = base.perimeter(G, nodes, to_a)
    obj_final = base.objective(ua, ub, x_f, rho, per_f)

    if trace is not None:
        if math.isfinite(obj0):
            trace.incumbent(to_a0, obj0)
        if math.isfinite(obj_final) and (not math.isfinite(obj0) or obj_final > obj0):
            trace.incumbent(to_a, obj_final)

    LB_out = float(obj_final) if math.isfinite(obj_final) else None
    extra = dict(extra0)
    extra.update(
        n_swaps=n_swaps,
        best_tree_obj=float(obj0) if math.isfinite(obj0) else None,
        ls_gain=(float(obj_final - obj0)
                if math.isfinite(obj_final) and math.isfinite(obj0) else None),
        method=method, k=(int(k) if method == "f3" else 0))
    return base.Result(status="heuristic", to_a=to_a, LB=LB_out, UB=None, extra=extra)


# ------------------------------------------------------------------------------ F1
def _f1_construct(G, comps, ua_map, ub_map, rho, rng, n_trees, deadline, keep):
    cand_lists = [_component_candidates(G, K, ua_map, ub_map, rng, n_trees, deadline, keep)
                 for K in comps]
    choice = _combine(cand_lists, rho)
    to_a = set()
    for lst, i in zip(cand_lists, choice):
        to_a |= set(lst[i][3])
    return to_a, dict(n_trees=int(n_trees))


def _log_prod(ga: float, gb: float) -> float:
    if ga <= 0 or gb <= 0:
        return -math.inf
    return math.log(ga) + math.log(gb)


def _random_spanning_tree(K, adj, root, rng):
    """A randomised spanning tree of the connected node list `K` (adjacency `adj`),
    rooted at `root`.  Returns (parent, order); `order` lists nodes with every
    parent before its children -- the property `_component_candidates` needs to
    accumulate subtree sums via a single reverse pass."""
    parent = {root: None}
    visited = {root}
    order = [root]
    frontier = [root]
    while frontier:
        pos = int(rng.integers(0, len(frontier)))
        v = frontier[pos]
        frontier[pos] = frontier[-1]
        frontier.pop()
        nbrs = list(adj[v])
        if len(nbrs) > 1:
            rng.shuffle(nbrs)
        for w in nbrs:
            if w not in visited:
                visited.add(w)
                parent[w] = v
                order.append(w)
                frontier.append(w)
    return parent, order


def _descendants(K, parent, v):
    children = {u: [] for u in K}
    for u in K:
        p = parent.get(u)
        if p is not None:
            children[p].append(u)
    out = set()
    stack = [v]
    while stack:
        u = stack.pop()
        out.add(u)
        stack.extend(children[u])
    return out


def _induced_perimeter(edges, mask):
    return sum(1 for u, v in edges if (u in mask) != (v in mask))


def _component_candidates(G, K, ua_map, ub_map, rng, n_trees, deadline, keep=DEFAULT_KEEP):
    """Up to `keep` + 2 (ga, gb, per, mask) candidates for one connected component
    `K`: the two trivial whole-component splits, plus the best (by log ga + log gb,
    ignoring rho -- the local search fixes up perimeter afterwards) single-tree-edge
    cuts seen across `n_trees` randomised spanning trees.  Shared by F1 and by F3's
    per-component repair fallback."""
    if len(K) == 1:
        z = K[0]
        return [(ua_map[z], 0.0, 0, frozenset(K)), (0.0, ub_map[z], 0, frozenset())]

    sub = G.subgraph(K)
    edges = list(sub.edges())
    adj = {v: list(sub.neighbors(v)) for v in K}
    total_ua = sum(ua_map[v] for v in K)
    total_ub = sum(ub_map[v] for v in K)
    root = K[0]

    heap = []      # bounded min-heap: (obj, seq, ga_c, gb_c, tree_index, v, orient)
    seq = 0
    trees = []

    t = 0
    while t < n_trees:
        if time.perf_counter() > deadline:
            break
        parent, order = _random_spanning_tree(K, adj, root, rng)
        if len(order) != len(K):
            t += 1
            continue  # defensive: K is a connected component, this shouldn't fire
        trees.append(parent)
        subtree_ua = {v: ua_map[v] for v in K}
        subtree_ub = {v: ub_map[v] for v in K}
        for v in reversed(order):
            p = parent[v]
            if p is not None:
                subtree_ua[p] += subtree_ua[v]
                subtree_ub[p] += subtree_ub[v]
        for v in K:
            if v == root:
                continue
            ga1, gb1 = subtree_ua[v], total_ub - subtree_ub[v]
            ga2, gb2 = total_ua - subtree_ua[v], subtree_ub[v]
            for ga_c, gb_c, orient in ((ga1, gb1, 1), (ga2, gb2, 2)):
                o = _log_prod(ga_c, gb_c)
                if not math.isfinite(o):
                    continue
                item = (o, seq, ga_c, gb_c, t, v, orient)
                seq += 1
                if len(heap) < keep:
                    heapq.heappush(heap, item)
                elif o > heap[0][0]:
                    heapq.heapreplace(heap, item)
        t += 1

    cand = []
    seen = set()
    whole_a, whole_b = frozenset(K), frozenset()
    cand.append((total_ua, 0.0, 0, whole_a)); seen.add(whole_a)
    cand.append((0.0, total_ub, 0, whole_b)); seen.add(whole_b)

    for o, _seq, ga_c, gb_c, ti, v, orient in sorted(heap, key=lambda w: -w[0]):
        parent = trees[ti]
        desc = _descendants(K, parent, v)
        mask = frozenset(desc) if orient == 1 else frozenset(set(K) - desc)
        if mask in seen:
            continue
        seen.add(mask)
        per_c = _induced_perimeter(edges, mask)
        cand.append((ga_c, gb_c, per_c, mask))
    return cand


def _combine(cand_lists, rho):
    """Choose one candidate index per component maximising log(sum ga) + log(sum gb)
    - rho * sum(per).  Exhaustive when the product of candidate-list sizes is small
    (binding requirement #2: true for <= 3 components), else coordinate ascent."""
    m = len(cand_lists)
    sizes = [len(c) for c in cand_lists]

    if m == 1:
        lst = cand_lists[0]
        best_i, best_o = 0, -math.inf
        for i, (ga, gb, per, _m) in enumerate(lst):
            o = _log_prod(ga, gb) - rho * per
            if o > best_o:
                best_o, best_i = o, i
        return [best_i]

    def total_obj(choice):
        ga = sum(cand_lists[i][choice[i]][0] for i in range(m))
        gb = sum(cand_lists[i][choice[i]][1] for i in range(m))
        per = sum(cand_lists[i][choice[i]][2] for i in range(m))
        return _log_prod(ga, gb) - rho * per

    total = 1
    for s in sizes:
        total *= max(s, 1)
        if total > MAX_COMBO:
            break

    if total <= MAX_COMBO:
        best_choice, best_o = None, -math.inf
        for combo in itertools.product(*(range(s) for s in sizes)):
            o = total_obj(combo)
            if o > best_o:
                best_o, best_choice = o, combo
        if best_choice is not None:
            return list(best_choice)

    choice = []
    for lst in cand_lists:
        bi, bo = 0, -math.inf
        for i, (ga, gb, per, _m) in enumerate(lst):
            o = _log_prod(ga, gb) - rho * per
            if o > bo:
                bo, bi = o, i
        choice.append(bi)
    cur = total_obj(choice)
    for _ in range(20):
        improved = False
        for ci in range(m):
            for j in range(sizes[ci]):
                if j == choice[ci]:
                    continue
                trial = list(choice); trial[ci] = j
                o = total_obj(trial)
                if o > cur:
                    choice, cur, improved = trial, o, True
        if not improved:
            break
    if not math.isfinite(cur):
        # last resort: exactly one component's "whole to B" (index 1), rest "whole
        # to A" (index 0) -- both trivial candidates always exist (or the component
        # is a singleton, whose only two candidates are exactly this pair).
        best_choice, best_o = [0] * m, -math.inf
        for ci in range(m):
            trial = [0] * m
            trial[ci] = 1 if sizes[ci] > 1 else 0
            o = total_obj(trial)
            if o > best_o:
                best_o, best_choice = o, trial
        choice = best_choice
    return choice


# ------------------------------------------------------------------------------ F3
def _smooth(G, nodes, ua, ub, k):
    a, b = np.asarray(ua, float).copy(), np.asarray(ub, float).copy()
    if k <= 0:
        return a, b
    idx = {z: i for i, z in enumerate(nodes)}
    nbrs_idx = [[idx[w] for w in G.neighbors(z)] for z in nodes]
    for _ in range(int(k)):
        new_a, new_b = a.copy(), b.copy()
        for i, nb in enumerate(nbrs_idx):
            if not nb:
                continue
            ma = sum(a[j] for j in nb) / len(nb)
            mb = sum(b[j] for j in nb) / len(nb)
            new_a[i] = 0.5 * a[i] + 0.5 * ma
            new_b[i] = 0.5 * b[i] + 0.5 * mb
        a, b = new_a, new_b
    return a, b


def _f3_construct(G, nodes, comps, ua_map, ub_map, theta, lam, kappa, rho, rng, k,
                  n_trees, deadline, keep):
    ua = np.array([ua_map[z] for z in nodes], dtype=float)
    ub = np.array([ub_map[z] for z in nodes], dtype=float)
    s_ua, s_ub = _smooth(G, nodes, ua, ub, k)

    free = bounds.ub_free_nash(G, nodes, theta, lam, kappa=kappa)
    x_free = base.mask(nodes, set(free["to_a"]))
    ga_free, gb_free = base.gains(ua, ub, x_free)
    lam_star = (ga_free / gb_free) if gb_free > 0 else math.inf

    r = base.ratio(s_ua, s_ub)
    to_a_thresh = {nodes[i] for i in range(len(nodes)) if r[i] >= lam_star}

    to_a = _repair(G, comps, to_a_thresh, ua_map, ub_map, rho, rng, n_trees, deadline, keep)
    extra = dict(n_trees=int(n_trees),
                lam_star=float(lam_star) if math.isfinite(lam_star) else None)
    return to_a, extra


def _repair(G, comps, to_a_thresh, ua_map, ub_map, rho, rng, n_trees, deadline, keep):
    to_a = set(to_a_thresh)
    for K in comps:
        Kset = set(K)
        side_a = {z for z in K if z in to_a}
        side_b = Kset - side_a
        fixed = _repair_component(G, K, side_a, side_b)
        if fixed is None:
            cand = _component_candidates(G, K, ua_map, ub_map, rng, n_trees, deadline, keep)
            best_i, best_o = 0, -math.inf
            for i, (ga, gb, per, _m) in enumerate(cand):
                o = _log_prod(ga, gb) - rho * per
                if o > best_o:
                    best_o, best_i = o, i
            fixed = set(cand[best_i][3])
        to_a -= Kset
        to_a |= fixed
    return to_a


def _repair_component(G, K, side_a, side_b, max_iters=None):
    """Flip stray (non-largest) pieces of one side onto the other, whenever that
    keeps the other side connected, until each side has <= 1 piece.  Returns the
    resolved A-side node set, or None if not resolved within `max_iters` (caller
    falls back to the F1 candidate list for this component)."""
    if max_iters is None:
        max_iters = 2 * len(K) + 4
    sub = G.subgraph(K)
    side_a, side_b = set(side_a), set(side_b)
    for _ in range(max_iters):
        pieces_a = list(nx.connected_components(sub.subgraph(side_a))) if side_a else []
        pieces_b = list(nx.connected_components(sub.subgraph(side_b))) if side_b else []
        if len(pieces_a) <= 1 and len(pieces_b) <= 1:
            return set(side_a)
        main_a = max(pieces_a, key=len) if pieces_a else None
        main_b = max(pieces_b, key=len) if pieces_b else None
        progress = False
        for p in sorted(pieces_a, key=lambda s: tuple(sorted(s, key=base._sort_key))):
            if p is main_a:
                continue
            trial_b = side_b | p
            if nx.is_connected(sub.subgraph(trial_b)):
                side_b, side_a = trial_b, side_a - p
                progress = True
                break
        if progress:
            continue
        for p in sorted(pieces_b, key=lambda s: tuple(sorted(s, key=base._sort_key))):
            if p is main_b:
                continue
            trial_a = side_a | p
            if nx.is_connected(sub.subgraph(trial_a)):
                side_a, side_b = trial_a, side_b - p
                progress = True
                break
        if not progress:
            return None
    pieces_a = list(nx.connected_components(sub.subgraph(side_a))) if side_a else []
    pieces_b = list(nx.connected_components(sub.subgraph(side_b))) if side_b else []
    if len(pieces_a) <= 1 and len(pieces_b) <= 1:
        return set(side_a)
    return None


# --------------------------------------------------------------------- local search
def _local_search(G, nodes, ua_map, ub_map, to_a0, rho, deadline, swap_cap):
    """First-improvement contiguity-preserving boundary swaps (module docstring)."""
    adj = {z: list(G.neighbors(z)) for z in nodes}
    side = {z: (z in to_a0) for z in nodes}
    ga = float(sum(ua_map[z] for z in nodes if side[z]))
    gb = float(sum(ub_map[z] for z in nodes if not side[z]))
    per = base.perimeter(G, nodes, {z for z in nodes if side[z]})

    def cur_obj(ga_, gb_, per_):
        if ga_ <= 0 or gb_ <= 0:
            return -math.inf
        return math.log(ga_) + math.log(gb_) - rho * per_

    obj = cur_obj(ga, gb, per)
    n_swaps = 0
    order_nodes = sorted(nodes, key=base._sort_key)

    while n_swaps < swap_cap and time.perf_counter() < deadline:
        side_a_nodes = [z for z in nodes if side[z]]
        side_b_nodes = [z for z in nodes if not side[z]]
        cuts_a = (set(nx.articulation_points(G.subgraph(side_a_nodes)))
                 if len(side_a_nodes) >= 3 else set())
        cuts_b = (set(nx.articulation_points(G.subgraph(side_b_nodes)))
                 if len(side_b_nodes) >= 3 else set())
        moved = False
        for z in order_nodes:
            if time.perf_counter() > deadline:
                break
            is_a = side[z]
            if is_a and z in cuts_a:
                continue
            if (not is_a) and z in cuts_b:
                continue
            nbrs = adj[z]
            if not nbrs:
                continue
            wants_other = not is_a
            if not any(side[w] == wants_other for w in nbrs):
                continue
            uz_a, uz_b = ua_map[z], ub_map[z]
            if is_a:
                new_ga, new_gb = ga - uz_a, gb + uz_b
            else:
                new_ga, new_gb = ga + uz_a, gb - uz_b
            before = sum(1 for w in nbrs if side[w] != is_a)
            after = sum(1 for w in nbrs if side[w] != (not is_a))
            new_per = per - before + after
            new_obj = cur_obj(new_ga, new_gb, new_per)
            if new_obj > obj + 1e-12:
                side[z] = not is_a
                ga, gb, per, obj = new_ga, new_gb, new_per, new_obj
                n_swaps += 1
                moved = True
                break
        if not moved:
            break

    to_a = {z for z in nodes if side[z]}
    return to_a, n_swaps
