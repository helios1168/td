"""realize.py -- the ZIP realizer (`docs/MODEL.md` §7, S21): a decoded master plan to a ZIP map.

Whole units go to their one owner.  For each splittable unit v shared by the copies J_v:
1. **Centres** (S24, #65 F6).  The copies of {v} take the centres of a deterministic opportunity-
   weighted k-means on v's ZIPs (`kmeans`), clipped or free.  A copy of S with |S| ≥ 2 (free v
   only: a clipped v in a multi-unit copy is held whole) takes the mass-weighted centroid of its
   border in v, the ZIPs with a ZIP-graph edge into S − v, unweighted when the border's mass is 0.
2. **Transport LP** (Claim 3) over v's ZIPs with m_z > 0, in mass flows x_{zj} = m_z f_{zj},
   solved by dual simplex (`highs-ds` with an explicit options dict, trap 14) so the solution is
   basic.  A positive flow graph that is not a forest stops the run (Lemma 3a, C5).
3. **Tree rounding** along the forest (`round_forest`), not ZIP by ZIP: a district takes a split
   ZIP when its running error is negative and passes it otherwise; where both moves keep
   |e_j| < m*_j, the one cheaper under the transport cost wins.  Zero-mass ZIPs and ZIPs below
   the LP's tolerance (#86), which the LP does not place, go by breadth-first search from the
   rounded ZIPs of v (`place_zero`); the latter keep their mass and are listed.
4. **One repair pass** (S23), then **one swap pass** (`td.swap`).  A detached piece, a component
   of a district other than its heaviest, goes to a district whose main component it touches only if
   both stay inside the final tolerance (OD1), the target is admissible in every unit the piece
   touches (C16: nobody in a whole unit, only another copy of {u} in a clipped unit u, anybody in a
   free one), and a move across exchange components improves the pair's worse district (#85).

Contiguity is read on the instance's ZIP graph, which is the declared graph (#11, trap 21).
Every remaining piece gets one cause, the first that applies (`CAUSES`):
- *graph gap*: no path joins it to the district's main component through the ZIPs of the
  district's support, as with a ZIP without edges or a unit that is not ZIP-connected;
- *corridor*: it holds a unit the district holds whole, cut off because a split unit's share
  does not link it (#7; U39, a master question);
- *tiny share*: the district's planned mass in the piece's unit is below that unit's heaviest ZIP;
- *attachment*: the district's ZIPs in that unit touch none of its ZIPs outside it;
- *shape*: otherwise, a convex cut across a non-convex unit.
"""
from __future__ import annotations

import collections
import math
from dataclasses import dataclass, field

import numpy as np
from scipy import sparse
from scipy.optimize import linprog

from td import audit, swap
from td.spec import zip_components

POS_TOL = 1e-9          # a flow below POS_TOL × m_z is zero
FLOW_TOL = 1e-6         # conservation slack of the normalised LP; HiGHS's own is 1e-7 (trap 14)
KMEANS_ITERS = 100
LP_OPTIONS = {"time_limit": 600.0, "presolve": True}     # trap 14: always an explicit dict
CAUSES = ("graph gap", "corridor", "tiny share", "attachment", "shape")


class RealizeError(RuntimeError):
    """The realizer cannot go on: the run stops."""


@dataclass
class Piece:
    district: str
    zips: tuple
    mass: float
    cause: str


@dataclass
class Drawing:
    """One channel's map.  Districts are the plan's copies, by `Copy.name`."""
    channel: str
    owner: dict                 # zip -> district
    mass: dict                  # district -> drawn mass
    planned: dict               # (unit, district) -> a_{v,j}
    drawn: dict                 # (unit, district) -> drawn mass in the unit, 0 when vanished
    pieces: list                # the pieces left after repair, each with its cause
    moved: list = field(default_factory=list)   # (zips, from, to) done by repair
    sub_tolerance: list = field(default_factory=list)   # positive ZIPs placed by adjacency (#86)
    swapped: list = field(default_factory=list)  # (zip, from, to) done by the swap pass

    @property
    def error(self) -> dict:
        """Δ_{v,j} = drawn − planned mass of district j in unit v (§7)."""
        return {key: self.drawn[key] - a for key, a in self.planned.items()}

    @property
    def vanished(self) -> list:
        """Planned shares drawn as no ZIP (C8): listed by the audit, not failed."""
        return sorted(key for key, a in self.planned.items() if a > 0 and self.drawn[key] <= 0)

    def counts(self) -> dict:
        """U34 for this map: pieces and districts in pieces, in total and by cause."""
        return {"pieces": len(self.pieces),
                "districts": len({p.district for p in self.pieces}),
                "pieces_by_cause": dict(collections.Counter(p.cause for p in self.pieces)),
                "districts_by_cause": {c: len({p.district for p in self.pieces if p.cause == c})
                                       for c in CAUSES if any(p.cause == c for p in self.pieces)}}


# ------------------------------------------------------------------------------ centres
def _d2(a, b) -> float:
    return (a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2


def centroid(zs, m: dict, p: dict) -> tuple:
    """The mass-weighted centroid of `zs`, unweighted when their mass is 0."""
    w = [m[z] for z in zs]
    if sum(w) <= 0:
        w = [1.0] * len(zs)
    tot = math.fsum(w)
    return (math.fsum(wi * p[z][0] for wi, z in zip(w, zs)) / tot,
            math.fsum(wi * p[z][1] for wi, z in zip(w, zs)) / tot)


def kmeans(zs, m: dict, p: dict, k: int) -> list:
    """k centres of opportunity-weighted k-means on `zs`, deterministic (#65 F6): the first centre
    is the heaviest ZIP, each next one the ZIP farthest from the chosen ones weighted by mass,
    ties by ZIP id; then at most KMEANS_ITERS Lloyd steps.  k = 1 is the weighted centroid."""
    zs = sorted(zs)
    if k == 1:
        return [centroid(zs, m, p)]
    w = {z: m[z] for z in zs} if any(m[z] > 0 for z in zs) else dict.fromkeys(zs, 1.0)
    chosen = [max(zs, key=lambda z: w[z])]          # max keeps the first, the smallest id
    while len(chosen) < k:
        rest = [z for z in zs if z not in chosen]
        score = {z: w[z] * min(_d2(p[z], p[c]) for c in chosen) for z in rest}
        if max(score.values()) <= 0:                # fewer weighted points than centres
            score = {z: min(_d2(p[z], p[c]) for c in chosen) for z in rest}
        chosen.append(max(rest, key=lambda z: score[z]))
    cs = [p[z] for z in chosen]
    for _ in range(KMEANS_ITERS):
        groups = [[] for _ in cs]
        for z in zs:
            if w[z] > 0:
                groups[min(range(len(cs)), key=lambda i: _d2(p[z], cs[i]))].append(z)
        new = [centroid(g, w, p) if g else c for g, c in zip(groups, cs)]
        if new == cs:
            break
        cs = new
    return cs


def centres(inst, channel: str, v: str, support: dict, p: dict) -> dict:
    """district -> its centre in unit v, for the districts `support` {district: S} holding v."""
    units, m = inst.units, inst.channels[channel].m
    singles = sorted(j for j, s in support.items() if len(s) == 1)
    out = dict(zip(singles, kmeans(units.zips[v], m, p, len(singles)))) if singles else {}
    for j, s in sorted(support.items()):
        if len(s) > 1:
            border = [z for z in units.zips[v]
                      if any(units.unit_of[y] in s and units.unit_of[y] != v for y in units.zip_adj[z])]
            if not border:
                raise RealizeError(f"channel {channel}: {j} has no border in {v}")
            out[j] = centroid(border, m, p)
    return out


# ------------------------------------------------------------------------------ transport and rounding
def transport(zs, m: dict, p: dict, c: dict, a: dict) -> dict:
    """{(z, j): x_{zj} > 0}: the transport LP of Claim 3 in mass flows, at a basic solution.  It
    runs on masses over their mean, so HiGHS's absolute tolerances cannot swallow a small-scale
    unit (#72 B1); a ZIP below FLOW_TOL there is left out, the implied last target short by its
    mass (#86).  Flows that miss a row by FLOW_TOL, or leave another ZIP unshipped, stop the run."""
    scale = math.fsum(m[z] for z in zs) / len(zs)
    tiny = [z for z in zs if m[z] < FLOW_TOL * scale]
    zs = [z for z in zs if z not in tiny]
    js, n, k = sorted(a), len(zs), len(a)
    cost = np.array([_d2(p[z], c[j]) for z in zs for j in js])
    rows = [i for i in range(n) for _ in js] + [n + jj for _ in zs for jj in range(k)]
    a_eq = sparse.csr_matrix((np.ones(2 * n * k), (rows, list(range(n * k)) * 2)), shape=(n + k, n * k))
    b_eq = np.array([m[z] for z in zs] + [a[j] for j in js]) / scale
    b_eq[-1] -= math.fsum(m[z] for z in tiny) / scale
    res = linprog(cost, A_eq=a_eq[:-1], b_eq=b_eq[:-1], bounds=(0.0, None), method="highs-ds",
                  options=dict(LP_OPTIONS))                  # the last target is implied
    if res.status != 0:
        raise RealizeError(f"the transport LP failed: {res.message}")
    if (miss := np.abs(a_eq @ res.x - b_eq)).max() > FLOW_TOL * max(1.0, float(b_eq.max())):
        worst = int(miss.argmax())
        name = f"ZIP {zs[worst]}" if worst < n else f"district {js[worst - n]}"
        raise RealizeError(f"the transport LP's flows miss {name} by {miss[worst] * scale:.3g}")
    x = res.x.reshape(n, k) * scale
    flow = {(z, j): float(x[i, jj]) for i, z in enumerate(zs) for jj, j in enumerate(js)
            if x[i, jj] > POS_TOL * m[z]}
    if lost := sorted({z for z in zs if m[z] > 0} - {z for z, _ in flow}):
        raise RealizeError(f"the transport LP places no flow on {len(lost)} ZIPs, e.g. {lost[:3]}")
    return flow


def check_forest(flow: dict) -> None:
    """Stop the run when the positive flow graph has a cycle (Lemma 3a, C5)."""
    parent: dict = {}

    def find(a):
        while parent.setdefault(a, a) != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    for z, j in sorted(flow):
        rz, rj = find(("z", z)), find(("j", j))
        if rz == rj:
            raise RealizeError(f"the transport LP's fractional graph is not a forest: a cycle "
                               f"through ZIP {z} and district {j}")
        parent[rz] = rj


def round_forest(m: dict, flow: dict, cost) -> dict:
    """zip -> district by Claim 3's rounding along the forest; `cost(z, j)` breaks choices."""
    check_forest(flow)
    nb = collections.defaultdict(list)
    for z, j in sorted(flow):
        nb[z].append(j)
    owner = {z: js[0] for z, js in nb.items() if len(js) == 1}
    split = collections.defaultdict(list)
    for z, js in sorted(nb.items()):
        if len(js) > 1:
            for j in js:
                split[j].append(z)
    err, seen = {}, set()
    for root in sorted(split):
        if root in seen:
            continue
        queue, err[root] = collections.deque([(root, None)]), 0.0
        seen.add(root)
        while queue:
            j, z0 = queue.popleft()
            top = max(m[z] for z in split[j])           # m*_j
            for z in split[j]:
                if z == z0:
                    continue
                kids = [k for k in nb[z] if k != j]
                kid = min(kids, key=lambda k: (cost(z, k), k))
                take, keep = err[j] + m[z] - flow[z, j], err[j] - flow[z, j]
                if abs(take) < top and abs(keep) < top:
                    took = cost(z, j) <= cost(z, kid)
                else:
                    took = err[j] < 0                   # the sign rule
                owner[z], err[j] = (j, take) if took else (kid, keep)
                for k in kids:
                    err[k] = m[z] - flow[z, k] if owner[z] == k else -flow[z, k]
                    seen.add(k)
                    queue.append((k, z))
    return owner


def place_zero(zeros, owner: dict, zip_adj: dict, p: dict, c: dict) -> dict:
    """ZIPs the LP does not place (§7 step 2) by breadth-first search from the ZIPs `owner` places
    in the unit; one the search cannot reach goes to the nearest centre among those districts."""
    left, out = set(zeros), {}
    queue = collections.deque(sorted(owner))
    while queue:
        z = queue.popleft()
        for y in sorted(zip_adj[z]):
            if y in left:
                left.discard(y)
                out[y] = out.get(z, owner.get(z))
                queue.append(y)
    held = sorted(set(owner.values()))
    for z in sorted(left):
        out[z] = min(held, key=lambda j: (_d2(p[z], c[j]), j))
    return out


# ------------------------------------------------------------------------------ the map
def _parts(zs, adj: dict, m: dict) -> list:
    """The components of `zs`, the heaviest first, ties by smallest ZIP id, as `td.audit` orders them."""
    return sorted(zip_components(zs, adj), key=lambda c: (-math.fsum(m.get(z, 0.0) for z in c), min(c)))


def _districts(owner: dict) -> dict:
    out = collections.defaultdict(list)
    for z, j in owner.items():
        out[j].append(z)
    return out


def realize(inst, plan, xy: dict) -> Drawing:
    """The channel's map for a decoded plan (`td.master.Plan`); `xy` is {zip: (x, y)} in metres,
    as `td.spec.Units.from_graph` takes it."""
    ch, units = inst.channels[plan.channel], inst.units
    p = {z: (xy[z][0] / 1000.0, xy[z][1] / 1000.0) for z in units.unit_of}
    support = {c.name: c.support for c in plan.copies}
    planned = {(v, c.name): c.mass[v] for c in plan.copies for v in c.support}
    owner, tiny = {}, []
    for v in ch.units:
        mine = {j: support[j] for (u, j), a in planned.items() if u == v and a > 0}
        if len(mine) == 1:
            owner.update(dict.fromkeys(units.zips[v], next(iter(mine))))
            continue
        c = centres(inst, plan.channel, v, mine, p)
        pos = [z for z in units.zips[v] if ch.m[z] > 0]
        flow = transport(pos, ch.m, p, c, {j: planned[v, j] for j in mine})
        own = round_forest(ch.m, flow, lambda z, j: ch.m[z] * _d2(p[z], c[j]))
        tiny += [z for z in pos if z not in own]            # the ZIPs `transport` left out
        owner.update(own)
        owner.update(place_zero([z for z in units.zips[v] if z not in own], own, units.zip_adj, p, c))
    moved = repair(inst, plan.channel, owner, support, swap.components(planned))
    swapped = swap.swap(inst, plan.channel, owner, planned)
    drawn, mass = dict.fromkeys(planned, 0.0), {c.name: 0.0 for c in plan.copies}
    for z, j in owner.items():
        drawn[units.unit_of[z], j] = drawn.get((units.unit_of[z], j), 0.0) + ch.m[z]
        mass[j] += ch.m[z]
    return Drawing(plan.channel, owner, mass, planned, drawn,
                   pieces(inst, plan.channel, owner, support, planned), moved, sorted(tiny),
                   swapped=swapped)


def _admissible(ch, units, piece, k, owner, support) -> bool:
    """The mode guard (C16): `k` may own the piece in every unit it touches, and gains no ZIP
    outside a clipped unit it already owns part of."""
    for u in {units.unit_of[z] for z in piece}:
        if ch.mode[u] == "whole" or (ch.mode[u] == "clipped" and support[k] != frozenset({u})):
            return False
    held = {units.unit_of[z] for z, j in owner.items() if j == k}
    return not any(ch.mode[u] == "clipped" and any(units.unit_of[z] != u for z in piece) for u in held)


def repair(inst, channel: str, owner: dict, support: dict, comp: dict | None = None) -> list:
    """One pass (S23) over the detached pieces found at its start; moves `owner` in place.
    `comp` is district -> exchange component, by default read off `support`."""
    comp = swap.support_components(support) if comp is None else comp
    ch, units = inst.channels[channel], inst.units
    (lo, hi), adj, m = ch.final_band, units.zip_adj, ch.m
    mass = collections.Counter({j: sum(m[z] for z in zs) for j, zs in _districts(owner).items()})
    todo = [(j, part) for j, zs in sorted(_districts(owner).items()) for part in _parts(zs, adj, m)[1:]]
    moved = []
    for j, part in todo:
        if any(owner[z] != j for z in part):
            continue
        main_j = _parts(_districts(owner)[j], adj, m)[0]
        if set(part) & set(main_j):
            continue
        w = math.fsum(m[z] for z in part)
        near = sorted({owner.get(y) for z in part for y in adj[z]} - {j, None})   # None: not in c
        ok = []
        for k in near:
            main_k = set(_parts(_districts(owner)[k], adj, m)[0])
            if (any(y in main_k for z in part for y in adj[z])
                    and _admissible(ch, units, part, k, owner, support)
                    and lo <= mass[j] - w <= hi and lo <= mass[k] + w <= hi
                    and swap.may_cross(comp, ch.tau, j, k, mass[j], mass[k], w)):
                ok.append(k)
        if ok:
            k = min(ok, key=lambda k: (abs(mass[k] + w - ch.tau), k))
            owner.update(dict.fromkeys(part, k))
            mass[j], mass[k] = mass[j] - w, mass[k] + w
            moved.append((part, j, k))
    return moved


def pieces(inst, channel: str, owner: dict, support: dict, planned: dict) -> list:
    """Every detached piece, with its cause (the module docstring's order)."""
    units, out = inst.units, []
    adj, m = units.zip_adj, inst.channels[channel].m
    for j, zs in sorted(_districts(owner).items()):
        parts = _parts(zs, adj, m)
        if len(parts) < 2:
            continue
        s = support[j]
        inside = {z for u in s for z in units.zips[u]}
        reach, queue = set(parts[0]), collections.deque(parts[0])
        while queue:
            for y in adj[queue.popleft()]:
                if y in inside and y not in reach:
                    reach.add(y)
                    queue.append(y)
        whole = {u for u in s if all(owner.get(z) == j for z in units.zips[u])}
        for part in parts[1:]:
            by_unit = collections.Counter()
            for z in part:
                by_unit[units.unit_of[z]] += m.get(z, 0.0)
            v = min(by_unit, key=lambda u: (-by_unit[u], u))
            mine_v = [z for z in zs if units.unit_of[z] == v]
            if not reach & set(part):
                cause = "graph gap"
            elif set(by_unit) & whole:
                cause = "corridor"
            elif planned.get((v, j), 0.0) < max(m.get(z, 0.0) for z in units.zips[v]):
                cause = "tiny share"
            elif len(s) > 1 and not any(units.unit_of[y] != v and owner.get(y) == j
                                        for z in mine_v for y in adj[z]):
                cause = "attachment"
            else:
                cause = "shape"
            out.append(Piece(j, part, math.fsum(m.get(z, 0.0) for z in part), cause))
    return out


# ------------------------------------------------------------------------------ the audit's view
def to_run(inst, drawings: dict, reports: dict | None = None, graph: dict | None = None):
    """`td.audit.Run` over the maps {channel: Drawing}: one ledger row per (ZIP, planning
    channel), the planning channel standing in for the fine channel until the ledger (#71)
    splits it.  District ids are `<channel>:<copy>`.  `graph` defaults to the instance's."""
    units = inst.units
    cells, expected, chans, mode, planned, reported, causes, names = [], set(), {}, {}, {}, {}, {}, {}
    for c, d in drawings.items():
        ch = inst.channels[c]
        chans[c] = audit.Channel(ch.k, *ch.final_band)
        mode.update({(c, v): ch.mode[v] for v in ch.units})
        for z, j in sorted(d.owner.items()):
            cells.append(audit.Cell(z, c, c, f"{c}:{j}", ch.m.get(z, 0.0)))
        expected |= {(z, c) for v in ch.units for z in units.zips[v]}    # the input, not the map
        for (v, j), a in d.planned.items():
            planned[c, v, f"{c}:{j}"] = a / ch.M[v]
        for (v, j), x in d.drawn.items():
            reported[c, v, f"{c}:{j}"] = x / ch.M[v]
        for pc in d.pieces:
            causes.update({(f"{c}:{pc.district}", z): pc.cause for z in pc.zips})
        names.update({f"{c}:{j}": f"{c} {j}" for j in d.mass})
    if graph is None:
        graph = {"vertices": sorted(units.unit_of),
                 "edges": sorted((a, b) for a in units.zip_adj for b in units.zip_adj[a] if a < b)}
    return audit.Run(cells, chans, expected, dict(units.unit_of), mode, planned, reported, graph,
                     causes, solver=reports, names=names)
