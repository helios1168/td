"""swap.py -- the swap pass toward τ inside split units (`docs/MODEL.md` §7 step 5, #85).

Two districts *share* a split unit v when both are planned there (a_{v,j} > 0).  The districts
linked through shared units form an *exchange component* (`components`): before repair, drift
(drawn − planned mass) sums to zero over each one (U41), so moving ZIPs inside a component moves
its districts toward the component's mean and leaves the plan alone.

After repair, `swap` moves one ZIP at a time from a district j to a district k that shares the
ZIP's unit with j and owns a neighbour of the ZIP.  A move is accepted only when
1. the worse of the pair improves, by more than GAIN_TOL τ:
   max(|m_j − w − τ|, |m_k + w − τ|) < max(|m_j − τ|, |m_k − τ|), so no deviation in the
   component grows past its old worst, and a pair inside the final band stays inside it;
2. neither district gains a piece and no piece grows: the ZIP's neighbours in j stay joined
   without it, and it touches k's main component, the heaviest, as `td.audit` orders them;
3. j keeps a ZIP of positive mass in the unit, so no planned share vanishes (C8).
Each step takes the accepted move of largest gain, ties by ZIP id and target.  A move lowers the
districts' deviations, sorted from the worst, lexicographically, so the pass ends.

`may_cross` is repair's hook: a piece moves between exchange components only when the worse
district of the pair improves.
"""
from __future__ import annotations

import collections
import math

from td.spec import zip_components

GAIN_TOL = 1e-9         # a move must lower the pair's worse deviation by more than GAIN_TOL × τ


def sharing(planned: dict) -> dict:
    """unit -> the districts planned in it, for the units two or more districts share."""
    by = collections.defaultdict(set)
    for (v, j), a in planned.items():
        if a > 0:
            by[v].add(j)
    return {v: js for v, js in by.items() if len(js) > 1}


def components(planned: dict) -> dict:
    """district -> its exchange component, named by the component's smallest district id."""
    parent = {j: j for _, j in planned}

    def find(j):
        while parent[j] != j:
            parent[j] = parent[parent[j]]
            j = parent[j]
        return j

    for js in sharing(planned).values():
        first, *rest = sorted(js)
        for k in rest:
            a, b = sorted((find(first), find(k)))
            parent[b] = a
    return {j: find(j) for j in parent}


def support_components(support: dict) -> dict:
    """`components` with every district planned in every unit of its support."""
    return components({(v, j): 1.0 for j, units in support.items() for v in units})


def worse(tau: float, *masses) -> float:
    """The largest |mass − τ| among `masses`."""
    return max(abs(x - tau) for x in masses)


def may_cross(comp: dict, tau: float, j: str, k: str, mj: float, mk: float, w: float) -> bool:
    """Whether mass w may go from j (mass mj) to k (mass mk): inside one exchange component
    always, across two only when the worse of the pair improves."""
    return comp[j] == comp[k] or worse(tau, mj - w, mk + w) < worse(tau, mj, mk)


def stays_joined(z, zs: set, adj: dict) -> bool:
    """Whether z's neighbours in `zs` lie in one component of `zs` − {z}: removing z from the
    district `zs` leaves it with no more components than it had."""
    nb = sorted(y for y in adj[z] if y in zs)
    if len(nb) < 2:
        return True
    want, seen, stack = set(nb[1:]), {z, nb[0]}, [nb[0]]
    while stack and want:
        for y in adj[stack.pop()]:
            if y in zs and y not in seen:
                seen.add(y)
                want.discard(y)
                stack.append(y)
    return not want


def main_part(zs, adj: dict, m: dict) -> set:
    """The heaviest component of `zs`, ties by smallest ZIP id, as `td.audit` orders them."""
    return set(min(zip_components(zs, adj), key=lambda c: (-math.fsum(m[z] for z in c), min(c))))


def swap(inst, channel: str, owner: dict, planned: dict) -> list:
    """The pass (module docstring) over `owner`, in place; the moves [(zip, from, to)] in order."""
    ch, units = inst.channels[channel], inst.units
    adj, m, tau = units.zip_adj, ch.m, ch.tau
    share = sharing(planned)
    mass, region, kept = collections.Counter(), collections.defaultdict(set), collections.Counter()
    for z, j in owner.items():
        mass[j] += m[z]
        region[j].add(z)
        if m[z] > 0:
            kept[units.unit_of[z], j] += 1
    main = {j: main_part(zs, adj, m) for j, zs in region.items()}
    moves = []
    while True:
        found = []
        for v in sorted(share):
            for z in units.zips[v]:
                j = owner.get(z)
                if j not in share[v] or m[z] <= 0 or kept[v, j] < 2:
                    continue
                for k in sorted({owner.get(y) for y in adj[z]} & share[v] - {j}):
                    gain = worse(tau, mass[j], mass[k]) - worse(tau, mass[j] - m[z], mass[k] + m[z])
                    if gain > GAIN_TOL * tau:
                        found.append((-gain, z, k))
        for _, z, k in sorted(found):
            j = owner[z]
            if any(y in main[k] for y in adj[z]) and stays_joined(z, region[j], adj):
                break
        else:
            return moves
        owner[z] = k
        mass[j], mass[k] = mass[j] - m[z], mass[k] + m[z]
        region[j].discard(z)
        region[k].add(z)
        main[j], main[k] = main_part(region[j], adj, m), main_part(region[k], adj, m)
        v = units.unit_of[z]
        kept[v, j], kept[v, k] = kept[v, j] - 1, kept[v, k] + 1
        moves.append((z, j, k))
