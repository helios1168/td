"""
brute.py -- exhaustive ground truth for n <= MAX_N (PLAN.md C.1, C.5).

Feasibility is component-wise (C.0 #1, `base.pieces`): for every connected component K
of the pair graph, S∩K and K∖S must each be connected or empty.  This module computes,
for each component independently, EVERY mask of K that is feasible under that rule --
via a vectorised bitmask BFS closure over all 2**|K| subsets at once (no Python loop
over subsets), so a single 20-node component finishes in a couple of seconds, not
1e6 individual connectivity checks.  A pair graph with more than one component is then
handled by combining each component's list of (g_a, g_b, perimeter) contributions,
after a Pareto prune (a component-local triple dominated in all of "bigger g_a, bigger
g_b, smaller perimeter" by another can never be part of the joint optimum, since
obj(S) = log(sum g_a) + log(sum g_b) - rho * sum(perimeter) is monotone in each sum
independently of what the other components contribute).

Vectorised bitmask trick (per component, size k <= MAX_N):
  masks              0 .. 2**k - 1, bit i <-> the i-th node of the component (sorted)
  low = masks & -masks                     lowest set bit of each mask (0 for mask 0)
  reach = closure of {low} under the adjacency, restricted to bits also in mask:
             reach_bits (2**k, k) boolean  =  bit-unpack(reach)
             frontier_bits = (reach_bits @ A) > 0          A = k x k adjacency, BLAS
             frontier = bit-pack(frontier_bits)
             new_reach = reach | (frontier & masks)
           iterate to a fixed point (<= diameter <= k steps)
  connected[mask]  =  (reach[mask] == mask)                (mask 0 is trivially True)
  feasible[mask]   =  connected[mask] & connected[full ^ mask]
This is the same "reachability from the lowest bit" idea a per-subset BFS would use,
done for every subset at once via one small matrix multiply per iteration instead of
a Python loop, which is what keeps it inside the < 60 s budget at k = 20 (C.5).

Single-component pairs (the common case, and the only case that can reach k = 20
worst-case) need no cross-component combination: the component's own feasible-mask
argmax over obj(S) IS the global optimum, computed directly.  Multi-component pairs
combine each component's pruned candidate list via outer-product accumulation,
carrying an index "path" back to the winning per-component mask so `to_a` can be
reconstructed (not just the winning objective value).
"""
from __future__ import annotations

import math

import networkx as nx
import numpy as np

from . import base

NAME = "brute"
EXACT = True
MAX_N = 20


# --------------------------------------------------------------- per-component table
def _component_table(H, comp_nodes, ua_map, ub_map):
    """All 2**k masks of `comp_nodes` (sorted, bit i <-> comp_nodes[i]): feasibility,
    g_a, g_b, perimeter.  Returns (masks, ga, gb, per, feasible) as aligned arrays."""
    k = len(comp_nodes)
    idx = {v: i for i, v in enumerate(comp_nodes)}
    edges_idx = [(idx[u], idx[v]) for u, v in H.subgraph(comp_nodes).edges()]

    nmasks = 1 << k
    masks = np.arange(nmasks, dtype=np.int64)

    if k == 0:
        return masks, np.zeros(0), np.zeros(0), np.zeros(0), np.zeros(0, dtype=bool)

    bits = ((masks[:, None] >> np.arange(k)) & 1).astype(np.float64)  # (nmasks, k)
    ua_arr = np.array([ua_map[v] for v in comp_nodes], dtype=np.float64)
    ub_arr = np.array([ub_map[v] for v in comp_nodes], dtype=np.float64)
    ga = bits @ ua_arr
    gb = ub_arr.sum() - bits @ ub_arr

    per = np.zeros(nmasks, dtype=np.float64)
    for i, j in edges_idx:
        per += np.abs(bits[:, i] - bits[:, j])

    if edges_idx:
        A = np.zeros((k, k), dtype=np.int64)
        for i, j in edges_idx:
            A[i, j] = 1
            A[j, i] = 1
        low = masks & (-masks)
        reach = low.copy()
        powers = (1 << np.arange(k)).astype(np.int64)
        for _ in range(k):
            reach_bits = ((reach[:, None] >> np.arange(k)) & 1)
            frontier_bits = (reach_bits.astype(np.int64) @ A) > 0
            frontier = frontier_bits.astype(np.int64) @ powers
            new_reach = reach | (frontier & masks)
            if np.array_equal(new_reach, reach):
                reach = new_reach
                break
            reach = new_reach
        connected = (reach == masks)
    else:
        connected = np.ones(nmasks, dtype=bool)  # no edges: every mask trivially "connected"
    connected[0] = True

    full = nmasks - 1
    feasible = connected & connected[full ^ masks]
    return masks, ga, gb, per, feasible


def _pareto_prune(ga, gb, per):
    """Indices of (ga, gb, per) triples not dominated (weakly worse in all three) by
    another triple in the same array.  O(m^2); only used for multi-component pairs,
    whose per-component m is small by construction (component sizes sum to <= MAX_N)."""
    m = len(ga)
    if m <= 1:
        return np.arange(m)
    GA, GB, PE = ga[:, None], gb[:, None], per[:, None]
    ga_r, gb_r, per_r = ga[None, :], gb[None, :], per[None, :]
    dominates = ((ga_r >= GA) & (gb_r >= GB) & (per_r <= PE) &
                ((ga_r > GA) | (gb_r > GB) | (per_r < PE)))
    dominated = dominates.any(axis=1)
    return np.where(~dominated)[0]


def _best_single(masks, ga, gb, per, feasible, rho):
    obj = np.where((ga > 0) & (gb > 0) & feasible,
                   np.log(np.where(ga > 0, ga, 1.0)) + np.log(np.where(gb > 0, gb, 1.0))
                   - rho * per, -np.inf)
    i = int(np.argmax(obj))
    return int(masks[i]), float(obj[i]) if np.isfinite(obj[i]) else -math.inf


def solve(G, nodes, *, theta, lam, rho, respect_state, time_limit, seed,
          warm_start=None, reductions=None, trace=None, kappa=0.0, **opts) -> base.Result:
    nodes = list(nodes)
    n = len(nodes)
    if n > MAX_N:
        return base.Result(status="error",
                           message=f"brute: n={n} exceeds MAX_N={MAX_N}")

    ua, ub = base.utilities(G, nodes, theta, lam, kappa)
    ua_map = dict(zip(nodes, ua))
    ub_map = dict(zip(nodes, ub))
    H = G.subgraph(nodes)
    comps = [sorted(c) for c in nx.connected_components(H)]

    if len(comps) == 1:
        K = comps[0]
        masks, ga, gb, per, feasible = _component_table(H, K, ua_map, ub_map)
        n_feasible = int(feasible.sum())
        mask, obj = _best_single(masks, ga, gb, per, feasible, rho)
        to_a = {K[i] for i in range(len(K)) if (mask >> i) & 1}
    else:
        cand = []          # per component: (K, ga, gb, per, masks) after pruning
        n_feasible_total = 1
        for comp in comps:
            K = comp
            masks, ga, gb, per, feasible = _component_table(H, K, ua_map, ub_map)
            n_feasible_total *= int(feasible.sum())
            fi = np.where(feasible)[0]
            ga_f, gb_f, per_f, masks_f = ga[fi], gb[fi], per[fi], masks[fi]
            keep = _pareto_prune(ga_f, gb_f, per_f)
            cand.append((K, ga_f[keep], gb_f[keep], per_f[keep], masks_f[keep]))
        n_feasible = n_feasible_total

        K0, ga0, gb0, per0, masks0 = cand[0]
        acc_ga, acc_gb, acc_per = ga0, gb0, per0
        paths = [np.arange(len(ga0))]
        for c in range(1, len(cand)):
            _, ga_c, gb_c, per_c, masks_c = cand[c]
            acc_ga = (acc_ga[:, None] + ga_c[None, :]).ravel()
            acc_gb = (acc_gb[:, None] + gb_c[None, :]).ravel()
            acc_per = (acc_per[:, None] + per_c[None, :]).ravel()
            paths = [np.repeat(p, len(ga_c)) for p in paths] + \
                    [np.tile(np.arange(len(ga_c)), len(paths[0]) if paths else 1)]
        obj_arr = np.where((acc_ga > 0) & (acc_gb > 0),
                           np.log(np.where(acc_ga > 0, acc_ga, 1.0)) +
                           np.log(np.where(acc_gb > 0, acc_gb, 1.0)) - rho * acc_per,
                           -np.inf)
        best_i = int(np.argmax(obj_arr))
        obj = float(obj_arr[best_i]) if np.isfinite(obj_arr[best_i]) else -math.inf
        to_a = set()
        for c, p in enumerate(paths):
            K, _, _, _, masks_f = cand[c]
            mask = int(masks_f[p[best_i]])
            to_a |= {K[i] for i in range(len(K)) if (mask >> i) & 1}

    x = base.mask(nodes, to_a)
    per_true = base.perimeter(G, nodes, to_a)
    OPT = base.objective(ua, ub, x, rho, per_true)

    r = base.ratio(ua, ub)
    root_a = nodes[int(np.argmax(r))]
    root_b = nodes[int(np.argmin(r))]
    opt_has_ratio_roots = bool((root_a in to_a) and (root_b not in to_a))

    return base.Result(status="optimal", to_a=to_a, LB=OPT, UB=OPT, ub_scope="global",
                       extra=dict(n_feasible=int(n_feasible),
                                 opt_has_ratio_roots=opt_has_ratio_roots))
