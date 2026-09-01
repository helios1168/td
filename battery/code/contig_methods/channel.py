"""channel.py -- the national-channel two-stage problem (NWAY.md 7; decided 2026-08-31).

The business is standing up a new "national" channel by carving the two largest firms out of
the financial-institutions and wirehouse channels, and wants territories of roughly equal
opportunity (~$1B each).  That is not the two-player merger problem, and it is handled in two
stages::

    stage 1   draw k balanced contiguous districts on opportunity alone
    stage 2   match retained reps to those districts

Why Nash still applies to stage 1
---------------------------------
Every zip lands in exactly one district, so `sum_j M_j` is the same for every partition.
Maximising `sum_j log M_j` subject to a fixed sum equalises the terms (d/dM_j gives
1/M_j = mu), so **maximum Nash welfare on a common measure IS equal-size districting** -- the
same optimum, not an approximation.  That is why the ~$1B target does not need to be a
constraint: pick `k = total_opportunity / 1e9` and the balance falls out.

It also sidesteps trap 2.  Explicitly minimising a spread can leave everyone worse off;
Nash gets the balance as the maximiser of a concave objective and stays Pareto efficient.

This module owns **stage 2**, which is exact and cheap.  Stage 1 is the hard part and is a
balanced contiguous districting problem -- see NWAY.md 7 for its status.

Stage 2 in one line
-------------------
Rep `i`'s utility from district `j` is `g_ij = sum_{z in A_j} u_i(z)` (`nway.utilities`, so
the vacancy and unowned-book handling comes along).  Nash-optimal staffing maximises
`sum_i log g_{i,sigma(i)}` over assignments sigma, which is a max-weight matching on the
*logs* -- solvable exactly by the Hungarian algorithm.  With more reps than districts the
matching is rectangular and therefore also *selects* which k reps to keep: well-posed only
because k is fixed, which it is (see NWAY.md 6.3).
"""
from __future__ import annotations

import math

import numpy as np
from scipy.optimize import linear_sum_assignment

from . import base, nway


def districts_from(to_district: dict) -> list:
    """Stable ordered list of district labels, in first-appearance order over sorted nodes.

    Uses `base._sort_key`, which orders ints before strings numerically.  Plain `str` sorting
    would put node 10 before node 2 and silently permute the district order.
    """
    seen, out = set(), []
    for z in sorted(to_district, key=base._sort_key):
        d = to_district[z]
        if d not in seen:
            seen.add(d)
            out.append(d)
    return out


def district_opportunity(G, to_district, districts=None) -> dict:
    """`M_j` per district -- the stage-1 objective's argument."""
    out = {} if districts is None else {d: 0.0 for d in districts}
    for z, d in to_district.items():
        out[d] = out.get(d, 0.0) + float(G.nodes[z]["M"])
    return out


def balance_report(G, to_district, target=None) -> dict:
    """How close the draw is to equal opportunity.  `target` defaults to the mean."""
    M = district_opportunity(G, to_district)
    vals = np.array([M[d] for d in sorted(M, key=base._sort_key)], float)
    if vals.size == 0:
        return dict(k=0)
    tgt = float(np.mean(vals)) if target is None else float(target)
    return dict(
        k=int(vals.size),
        total=float(vals.sum()),
        target=tgt,
        mean=float(vals.mean()),
        min=float(vals.min()),
        max=float(vals.max()),
        spread_rel=float((vals.max() - vals.min()) / vals.mean()) if vals.mean() else 0.0,
        max_dev_rel=float(np.abs(vals - tgt).max() / tgt) if tgt else 0.0,
        # the stage-1 objective itself; maximised exactly when the districts are equal
        log_sum=float(np.log(vals).sum()) if (vals > 0).all() else -math.inf,
    )


# ------------------------------------------- district budget across graph components
def allocate_districts(component_M: dict, k: int, target=None) -> dict:
    """Best split of `k` districts among disconnected components, and the balance ceiling.

    A contiguous district cannot span two components, so when the footprint is disconnected
    (here: west coast / east coast / Texas / Florida, with the midwest uncovered) the problem
    separates -- each component `c` gets an integer `k_c >= 1`, and `sum k_c = k`.

    Within a component the best conceivable outcome is `k_c` equal districts of `M_c / k_c`.
    That is an **upper bound** on any real partition, since contiguity may not permit an even
    split, so the balance reported here is a *ceiling*: the geometry cannot do better, and a
    solver can only do worse.  Compute it before any solver work -- if the ceiling already
    misses the target band, no amount of solving will reach it and `k` (or the band) has to
    move.

    Maximises the stage-1 objective `sum_c k_c * log(M_c / k_c)`, which is Nash welfare under
    perfect within-component balance.
    """
    comps = {c: float(m) for c, m in component_M.items() if float(m) > 0}
    n = len(comps)
    if n == 0:
        return dict(feasible=False, reason="no components with positive opportunity")
    if k < n:
        return dict(feasible=False, k=k, n_components=n,
                    reason=f"k={k} districts cannot cover {n} disconnected components; "
                           f"every component needs at least one")
    names = sorted(comps, key=base._sort_key)
    total = sum(comps.values())
    tgt = total / k if target is None else float(target)

    best = None
    def walk(i, left, acc):
        nonlocal best
        if i == n - 1:
            acc = acc + [left]
            val = sum(kc * math.log(comps[c] / kc) for c, kc in zip(names, acc))
            if best is None or val > best[0]:
                best = (val, list(acc))
            return
        # leave at least one district for each remaining component
        for kc in range(1, left - (n - i - 1) + 1):
            walk(i + 1, left - kc, acc + [kc])
    walk(0, k, [])

    val, alloc = best
    per = {c: comps[c] / kc for c, kc in zip(names, alloc)}
    sizes = np.array([comps[c] / kc for c, kc in zip(names, alloc)
                      for _ in range(kc)], float)
    return dict(
        feasible=True, k=k, n_components=n, total=total, target=tgt,
        districts_per_component=dict(zip(names, alloc)),
        district_size=per,                       # the size every district in c would have
        ceiling_log_sum=val,
        ceiling_min=float(sizes.min()), ceiling_max=float(sizes.max()),
        ceiling_spread_rel=float((sizes.max() - sizes.min()) / sizes.mean()),
        ceiling_max_dev_rel=float(np.abs(sizes - tgt).max() / tgt),
    )


def component_opportunity(G, nodes=None) -> dict:
    """Opportunity per connected component of the footprint, keyed by a sorted-first node."""
    import networkx as nx
    H = G if nodes is None else G.subgraph(nodes)
    out = {}
    for comp in nx.connected_components(H):
        key = sorted(comp, key=base._sort_key)[0]
        out[key] = sum(float(G.nodes[z]["M"]) for z in comp)
    return out


def gain_matrix(G, to_district, reps_order=None, districts=None, *,
                theta: float = 0.40, lam: float = 0.30, filler_capture: str = "theta"):
    """`(g, reps, districts)` with `g[i, j]` = rep `reps[i]`'s utility from district `j`.

    Utilities come from `nway.utilities`, so unowned book (`S_free`) and the vacancy
    treatment carry through unchanged.  A rep's utility is evaluated on **every** district,
    not only where it holds book -- staffing is not restricted by legacy candidacy, which is
    the whole point of drawing the map first.
    """
    nodes = sorted(to_district)
    R = list(reps_order) if reps_order is not None else nway.reps(G, nodes)
    D = list(districts) if districts is not None else districts_from(to_district)
    if not R or not D:
        return np.zeros((len(R), len(D)), float), R, D

    # utilities of every rep on every node, ignoring candidacy: staffing is unconstrained
    c1, c2 = 1.0 - lam, theta * (1.0 - lam)
    if filler_capture not in nway.FILLER_CAPTURE:
        raise ValueError(f"filler_capture {filler_capture!r} not in {nway.FILLER_CAPTURE}")
    c_free = {"theta": c2, "full": c1, "opportunity": lam}[filler_capture]
    jd = {d: j for j, d in enumerate(D)}
    ir = {r: i for i, r in enumerate(R)}
    g = np.zeros((len(R), len(D)), float)
    for z in nodes:
        j = jd[to_district[z]]
        S = nway.books(G, z)
        T = float(sum(S.values()))
        free = nway.free_book(G, z)
        M = float(G.nodes[z]["M"])
        common = c2 * T + c_free * free + lam * M
        for r, i in ir.items():
            s = float(S.get(r, 0.0))
            g[i, j] += common + (c1 - c2) * s
    return g, R, D


def match(g: np.ndarray, criterion: str = "nash"):
    """Assign reps to districts, one each.  Returns `(pairs, value)`.

    `nash` maximises `sum_i log g_{i,sigma(i)}` -- the same objective as stage 1, and the
    reason to prefer it: a utilitarian match can hand one rep a district containing almost
    none of their book as long as the total looks good.  `utilitarian` maximises the raw sum.

    Rectangular is fine and meaningful: with more reps than districts the unmatched reps are
    the ones not retained, and the choice is well-posed because k is fixed.
    """
    if g.size == 0:
        return [], 0.0
    if criterion == "nash":
        if (g <= 0).any():
            raise ValueError("nash matching needs strictly positive gains; "
                             "a zero means a rep gets no utility at all from a district")
        cost = -np.log(g)
    elif criterion == "utilitarian":
        cost = -g
    else:
        raise ValueError(f"criterion {criterion!r} not in ('nash', 'utilitarian')")
    rows, cols = linear_sum_assignment(cost)
    pairs = list(zip(rows.tolist(), cols.tolist()))
    value = float(sum(np.log(g[i, j]) if criterion == "nash" else g[i, j] for i, j in pairs))
    return pairs, value


def stage2(G, to_district, reps_order=None, districts=None, *, theta: float = 0.40,
           lam: float = 0.30, filler_capture: str = "theta", criterion: str = "nash") -> dict:
    """Staff a drawn map: which rep runs which district, and what it is worth."""
    g, R, D = gain_matrix(G, to_district, reps_order, districts,
                          theta=theta, lam=lam, filler_capture=filler_capture)
    pairs, value = match(g, criterion)
    assign = {D[j]: R[i] for i, j in pairs}
    gains = {D[j]: float(g[i, j]) for i, j in pairs}
    matched = {R[i] for i, _ in pairs}
    return dict(
        assignment=assign,                       # district -> rep
        gains=gains,                             # district -> that rep's utility
        value=value,                             # sum log g (nash) or sum g (utilitarian)
        criterion=criterion,
        reps=R, districts=D,
        unmatched_reps=[r for r in R if r not in matched],   # i.e. not retained
        unstaffed_districts=[d for d in D if d not in assign],
        balance=balance_report(G, to_district),
    )


def score_draws(G, draws, reps_order=None, **kw) -> list:
    """Score several stage-1 draws by their best staffing, best first.

    Stage 2 is milliseconds, so the cheap way to recover some of what the two-stage split
    gives up (CLAUDE.md's objection to decoupling: it relocates the difficulty rather than
    removing it) is to generate a *portfolio* of balanced draws and keep the one that staffs
    best.  It is not the joint optimum, but it costs almost nothing.
    """
    out = []
    for idx, to_district in enumerate(draws):
        res = stage2(G, to_district, reps_order, **kw)
        res["draw"] = idx
        out.append(res)
    out.sort(key=lambda r: -r["value"])
    return out
