"""draw.py -- #109's contiguity-aware realizer: a decoded master plan to a ZIP map in which every
district is one piece of the graph the instance plans on (M1's polygon graph since #114).

Experimental, not a production realizer.  Per planning channel:

- **Fixed and free ZCTAs.**  A unit held by one district is that district's, except the ZCTAs of
  its components other than the largest (an exclave, joined to its state only through another
  state on the approved graph, D2).  The free ZCTAs are every ZCTA of a split unit (two or more
  holders), of an exclave and of a domain unit dropped for zero opportunity, zero-opportunity
  ZCTAs included.  A district's fixed ZCTAs fall into components, its *bodies*.
- **Allowed districts.**  `arm1` keeps the master's support: a split unit's ZCTAs may go only to
  the districts whose support holds it (allowed, not required: a share may vanish).  An exclave or
  dropped ZCTA may go to any district that holds a share in, or has a body touching, its free
  component (any other owner could not be connected).  `split` also lets a split unit's ZCTAs go
  to those districts (each extra holder is a split, reported); `move` does the same but keeps each
  split unit's number of holders at most the plan's.
- **Coupled groups.**  Free components that share an allowed district are solved together, one
  MILP per group, over the group's free ZCTAs and its districts' bodies contracted to one vertex
  each.  Variables x_{z,j} (ZCTA z to district j) and y_{v,j} (j owns a ZCTA of unit v); rows:
  each ZCTA one owner, x ≤ y, each district's drawn mass in the internal band [τ(1−δ), τ(1+δ)]
  (the plan's δ unless a wider one is asked), and with `fixed` targets each (unit, district) mass
  within the unit's heaviest ZCTA of the plan's share (Claim 3's bound).
- **Connectivity, exactly.**  highspy 1.15.1 never invokes its lazy-constraint callback, so the
  realizer runs a solve-check-cut loop: a ZCTA given to a district must have a neighbour of that
  district (rows up front), and every detached component C of a district's solution adds the
  separator rows x_{z,j} ≤ Σ_{s ∈ N(C)} x_{s,j} for z ∈ C (rooted at the district's heaviest body;
  a district with no body uses x_{a,j} + x_{b,j} − Σ_{s ∈ N(C)} x_{s,j} ≤ 1).  Each row holds for
  every connected drawing, so an infeasible step proves that no connected drawing exists under the
  group's rules (a certificate), and a connected optimum of a step is optimal for the group.
- **Objective**, in the settled order (PROBLEM.md, 2026-10-05): holders per unit first (splits
  and cuts, weight `SPLIT_WEIGHT` each), then shape, Σ (m_z / m̄ + `AREA_FLOOR`) ‖p_z − c_j‖²,
  scaled below one split; c_j is `td.realize.centres`' centre of j in the unit.  Balance is held
  by the band, not optimised.
- **Status per group**: `optimal` (a connected optimum at `mip_rel_gap = 0`, trap 12),
  `connected` (connected and feasible, stopped by the time limit), `infeasible` (proved), or
  `unknown` (the time limit with no connected incumbent; never read as infeasible).
"""
from __future__ import annotations

import collections
import math
import time
from dataclasses import dataclass, field

import highspy
import numpy as np

from td import realize as tdrealize
from td import territory

SPLIT_WEIGHT = 1000.0       # one more holder of a unit outweighs any shape difference
SHAPE_SCALE = 0.9 * SPLIT_WEIGHT
AREA_FLOOR = 0.1            # a zero-opportunity ZCTA's weight in the shape term, in m̄
MASS_TOL = 1e-9
PHASE1_GAP = 0.05           # the cut loop's absolute gap until a connected drawing exists
FINAL_ABS_GAP = 1e-6        # then mip_rel_gap = 0 and this absolute gap (trap 12)
ARMS = ("arm1", "split", "move")


@dataclass
class Group:
    """One coupled group's solve."""
    districts: list
    units: list                 # the units with free ZCTAs in the group
    free: int                   # free ZCTAs
    columns: int
    rows: int
    status: str = "unknown"
    iterations: int = 0
    cuts: int = 0
    seconds: float = 0.0
    objective: float | None = None
    bound: float | None = None
    gap: float | None = None
    note: str = ""
    owner: dict = field(default_factory=dict)
    delta: float | None = None
    tried: list = field(default_factory=list)
    dag: bool = False

    def report(self) -> dict:
        return {"districts": self.districts, "units": self.units, "free_zctas": self.free,
                "columns": self.columns, "rows": self.rows, "status": self.status,
                "iterations": self.iterations, "cuts": self.cuts,
                "seconds": round(self.seconds, 2), "objective": self.objective,
                "bound": self.bound, "gap": self.gap, "note": self.note, "delta": self.delta,
                "tried": self.tried, "dag": self.dag}


@dataclass
class Result:
    channel: str
    owner: dict                 # every footprint ZCTA -> copy name; failed groups not drawn
    groups: list
    undrawn: set                # free ZCTAs of groups without a connected drawing
    fixed_split: list           # districts whose bodies no free ZCTA can join
    share_only: list            # U61
    delta: float
    arm: str
    fixed_targets: bool
    sequential: bool = False

    @property
    def connected(self) -> bool:
        return not self.undrawn and not self.fixed_split

    @property
    def status(self) -> str:
        st = {g.status for g in self.groups}
        if self.fixed_split or "infeasible" in st:
            return "infeasible"
        if "unknown" in st:
            return "unknown"
        return "connected" if "connected" in st or self.sequential else "optimal"


# ------------------------------------------------------------------------------ the instance view
def components(zs, adj) -> list:
    """Components of `zs` on `adj`, largest first, ties by smallest id."""
    inside, seen, out = set(zs), set(), []
    for z in sorted(inside):
        if z in seen:
            continue
        comp, stack = [], [z]
        seen.add(z)
        while stack:
            a = stack.pop()
            comp.append(a)
            for b in adj[a]:
                if b in inside and b not in seen:
                    seen.add(b)
                    stack.append(b)
        out.append(frozenset(comp))
    return sorted(out, key=lambda c: (-len(c), min(c)))


def holders(plan) -> dict:
    """{unit: [copy names holding a positive share]}."""
    out = collections.defaultdict(list)
    for c in plan.copies:
        for v in c.support:
            if c.mass[v] > 0:
                out[v].append(c.name)
    return {v: sorted(js) for v, js in out.items()}


def split_fixed(inst, plan) -> tuple:
    """(fixed {zip: copy}, free set, exclave set) over the channel's footprint."""
    ch, units = inst.channels[plan.channel], inst.units
    hold = holders(plan)
    fixed, free, exclave = {}, set(), set()
    for v in ch.units:
        js = hold.get(v, [])
        comps = units.components.get(v)
        main = set(comps[0]) if comps else set(units.zips[v])
        if len(js) != 1:
            free |= set(units.zips[v])
            exclave |= set(units.zips[v]) - main
            continue
        for z in units.zips[v]:
            if z in main:
                fixed[z] = js[0]
            else:
                free.add(z)
                exclave.add(z)
    for v in ch.dropped_units:
        free |= set(units.zips.get(v, ()))
    return fixed, free, exclave


# ------------------------------------------------------------------------------ the realizer
def draw(inst, plan, xy: dict, arm: str = "arm1", delta: float | None = None,
         fixed_targets: bool = False, time_limit: float = 600.0, wider=(),
         group_limit: float | None = None, sequential: bool = False, log=print) -> Result:
    """The channel's contiguity-aware map (module docstring); `xy` is {zip: (x, y)} in metres.
    A group with no connected drawing in the band of `delta` (the plan's by default) is tried
    again at each wider δ of `wider` in turn (the remedy "a wider internal band", reported per
    group); each attempt has `group_limit` seconds, all of them `time_limit` together."""
    if arm not in ARMS:
        raise ValueError(f"arm {arm!r} not in {ARMS}")
    c = plan.channel
    ch, units = inst.channels[c], inst.units
    adj, m = units.zip_adj, ch.m
    delta = plan.delta if delta is None else delta
    lo, hi = ch.tau * (1 - delta), ch.tau * (1 + delta)
    p = {z: (xy[z][0] / 1000.0, xy[z][1] / 1000.0) for z in units.unit_of}
    hold = holders(plan)
    planned = {(v, cp.name): cp.mass[v] for cp in plan.copies for v in cp.support}
    support = {cp.name: cp.support for cp in plan.copies}
    fixed, free, exclave = split_fixed(inst, plan)
    unit_of = units.unit_of

    bodies = collections.defaultdict(list)       # copy -> its fixed components
    by_j = collections.defaultdict(set)
    for z, j in fixed.items():
        by_j[j].add(z)
    for j, zs in by_j.items():
        bodies[j] = components(zs, adj)
    body_of = {z: (j, i) for j, bs in bodies.items() for i, b in enumerate(bs) for z in b}

    # free components and who may own each ZCTA
    fcomps = components(free, adj)
    near = []
    for q in fcomps:
        js = {fixed[y] for z in q for y in adj[z] if y in fixed}
        js |= {j for v in {unit_of[z] for z in q} if len(hold.get(v, [])) > 1 for j in hold[v]}
        near.append(sorted(js))
    next_to = collections.defaultdict(set)      # unit -> districts owning a ZCTA next to it
    for v in ch.units:
        for z in units.zips[v]:
            for y in adj[z]:
                w = unit_of[y]
                if w == v:
                    continue
                if y in fixed:
                    next_to[v].add(fixed[y])
                elif len(hold.get(w, [])) > 1:
                    next_to[v] |= set(hold[w])
    allowed = {}
    for qi, q in enumerate(fcomps):
        for z in q:
            v = unit_of[z]
            if len(hold.get(v, [])) > 1 and arm == "arm1" and z not in exclave:
                allowed[z] = list(hold[v])
            elif len(hold.get(v, [])) > 1:      # `split`, `move`: v's neighbouring districts
                allowed[z] = sorted(set(hold[v]) | next_to[v])
            else:
                allowed[z] = list(near[qi])
    # coupled groups: free components joined by a shared district
    parent = list(range(len(fcomps)))

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a
    first = {}
    for qi, q in enumerate(fcomps):
        for j in {j for z in q for j in allowed[z]}:
            if j in first:
                parent[find(qi)] = find(first[j])
            else:
                first[j] = qi
    groups = collections.defaultdict(list)
    for qi in range(len(fcomps)):
        groups[find(qi)].append(qi)

    owner = dict(fixed)
    in_group = {j for z in free for j in allowed[z]}
    fixed_split = sorted(j for j, bs in bodies.items() if len(bs) > 1 and j not in in_group)
    touches = collections.defaultdict(set)      # copy -> the units its bodies touch
    for j, bs in bodies.items():
        touches[j] = {unit_of[y] for b in bs for z in b for y in adj[z]}
    share_only = sorted({j for v, js in hold.items() if len(js) > 1 for j in js
                         if v not in touches[j]})
    out, undrawn = [], set()
    t_end = time.time() + time_limit
    if sequential:
        return _sequential(inst, plan, c, owner, free, exclave, allowed, hold, planned, support,
                           p, delta, wider, arm, fixed_targets, t_end, group_limit,
                           fixed_split, share_only, log)
    for gi, qis in enumerate(sorted(groups.values(), key=lambda g: -sum(len(fcomps[q]) for q in g))):
        zs = sorted(z for q in qis for z in fcomps[q])
        tried, g = [], None

        def solve(d, dag, seed):
            left = t_end - time.time()
            if left <= 1.0:
                return None
            r = _solve_group(c, zs, allowed, bodies, body_of, fixed, adj, m, p, unit_of, hold,
                             plan, planned, support, inst, ch.tau * (1 - d), ch.tau * (1 + d),
                             arm, fixed_targets, min(left, group_limit or left), log, dag=dag,
                             start=seed)
            log(f"  {c} group {gi} at δ = {d:g}{' (dag)' if dag else ''}: {len(r.districts)} "
                f"districts, {r.free} free ZCTAs, {r.columns} columns -> {r.status} in "
                f"{r.seconds:.1f}s, {r.iterations} solves, {r.cuts} cuts"
                f"{(' (' + r.note + ')') if r.note else ''}")
            return r
        for d in [delta] + sorted(x for x in wider if x > delta):
            g = _attempt(solve, d, tried) or g
            if g is not None and g.status in ("optimal", "connected", "infeasible"):
                break
        if g is None:       # no time left for this group
            g = Group(sorted({j for z in zs for j in allowed[z]}), sorted({unit_of[z] for z in zs}),
                      len(zs), 0, 0, note="not tried: the channel's time limit")
        g.tried = tried
        out.append(g)
        if g.status in ("optimal", "connected"):
            owner.update(g.owner)
        else:
            undrawn |= set(zs)
    return Result(c, owner, out, undrawn, fixed_split, share_only, delta, arm, fixed_targets)


def _attempt(solve, d, tried):
    """One band: the geodesic-DAG restriction first, then the complete model started from the
    restriction's drawing; the better of the two that is connected, else the complete model's
    verdict.  `solve(d, dag, seed)` returns a Group, or None when the time is up."""
    out = None
    for dag in (True, False):
        seed = out.owner if out is not None and out.status == "connected" else None
        r = solve(d, dag, seed)
        if r is None:
            break
        r.delta = d
        tried.append({"delta": d, "dag": dag, "status": r.status, "seconds": round(r.seconds, 2),
                      "note": r.note})
        if not dag and seed is not None and r.status not in ("optimal", "connected"):
            break           # the complete model lost the DAG's drawing: keep the DAG's
        out = r
    return out


def _sequential(inst, plan, c, owner, free, exclave, allowed, hold, planned, support, p, delta,
                wider, arm, fixed_targets, t_end, group_limit, fixed_split, share_only, log):
    """The sequential restriction (`draw(sequential=True)`): one split unit at a time, each
    district's ZCTAs in the unit attached to what it already owns next to the unit (its whole
    units and the units drawn before, taken as one body), the units it has yet to draw counted at
    their planned shares in the band row; then the exclave and dropped ZCTAs, all of zero
    opportunity here, grown breadth first from the drawn map.  Neither a restriction nor a
    relaxation of the joint model: a unit it cannot draw proves nothing (`unknown`), and only the
    M1 audit of the finished ledger says whether a district is one piece."""
    ch, units = inst.channels[c], inst.units
    adj, m, unit_of = units.zip_adj, ch.m, units.unit_of
    split = [v for v in ch.units if len(hold.get(v, [])) > 1]
    pending = set(split)

    def entry(v):       # holders with nothing next to v yet go last
        return (sum(1 for j in hold[v] if not any(owner.get(y) == j for z in units.zips[v]
                                                   for y in adj[z])), len(units.zips[v]), v)
    out, undrawn = [], set()
    while pending:
        v = min(pending, key=entry)
        pending.discard(v)
        zs = sorted(z for z in units.zips[v] if z in free and z not in exclave)
        js = sorted({j for z in zs for j in allowed[z]})
        mine = collections.defaultdict(set)
        for z, j in owner.items():
            if j in js:
                mine[j].add(z)
        # what each district owns next to v is one body: v's share must attach to it, and the
        # rest of the district joins through units drawn later (a relaxation the audit checks)
        near = set().union(*(adj[z] for z in zs)) if zs else set()
        bodies, extra = {}, {}
        for j in js:
            touching = set().union(*([cc for cc in components(mine[j], adj) if cc & near] or [set()]))
            if touching:
                bodies[j] = [frozenset(touching)]
            extra[j] = math.fsum(planned.get((w, j), 0.0) for w in pending) + math.fsum(
                m.get(z, 0.0) for z in mine[j] - touching)
        body_of = {z: (j, i) for j, bs in bodies.items() for i, b in enumerate(bs) for z in b}
        g, tried = None, []

        def solve(d, dag, seed):
            left = t_end - time.time()
            if left <= 1.0:
                return None
            r = _solve_group(c, zs, allowed, bodies, body_of, owner, adj, m, p, unit_of, hold,
                             plan, planned, support, inst, ch.tau * (1 - d), ch.tau * (1 + d),
                             arm, fixed_targets, min(left, group_limit or left), log, extra,
                             dag=dag, start=seed)
            log(f"  {c} unit {v} at δ = {d:g}{' (dag)' if dag else ''}: {len(r.districts)} "
                f"districts, {r.free} ZCTAs -> {r.status} in {r.seconds:.1f}s, "
                f"{r.iterations} solves, {r.cuts} cuts{(' (' + r.note + ')') if r.note else ''}")
            return r
        for d in [delta] + sorted(x for x in wider if x > delta):
            g = _attempt(solve, d, tried) or g
            if g is not None and g.status in ("optimal", "connected"):
                break
        if g is None:       # no time left: this unit and the rest stay undrawn
            undrawn |= set(zs) | {z for w in pending for z in units.zips[w] if z in free}
            break
        g.tried = tried
        if g.status == "infeasible":
            g.status, g.note = "unknown", "restricted model infeasible: " + g.note
        out.append(g)
        if g.status in ("optimal", "connected"):
            owner.update(g.owner)
        else:
            undrawn |= set(zs)
    left = {z for z in free if z not in owner and z not in undrawn}
    grown = territory.grow(owner, left, adj)
    undrawn |= left
    log(f"  {c}: {len(grown)} exclave and dropped ZCTAs grown from the drawn map, "
        f"{len(left)} unreached")
    return Result(c, owner, out, undrawn, fixed_split, share_only, delta, arm, fixed_targets,
                  sequential=True)


def geodesic(zs, allowed, js, gadj, vert_of, cen, unit_of, p) -> dict:
    """{district: {zip: km}}, the shortest path in km along the group graph from the district's
    bodies (a ZCTA touching one starts at 0) or, for a district with none, from its ZCTA nearest
    its centre in each unit, through the ZCTAs it may own: the shape term's distance, under which
    a compact share hugs the border it must touch."""
    import heapq
    out = {}
    for j in js:
        mine = {z for z in zs if j in allowed[z]}
        src = {z for z in mine if any(vert_of.get(y) == j for y in gadj[z])}
        if not src:
            for v in sorted({unit_of[z] for z in mine}):
                if (v, j) in cen:
                    src.add(min((z for z in mine if unit_of[z] == v),
                                key=lambda z: (tdrealize._d2(p[z], cen[v, j]), z)))
        dist, heap = {}, [(0.0, z) for z in sorted(src)]
        while heap:
            d, z = heapq.heappop(heap)
            if z in dist:
                continue
            dist[z] = d
            for y in gadj[z]:
                if y in mine and y not in dist:
                    heapq.heappush(heap, (d + math.dist(p[z], p[y]), y))
        out[j] = dist
    return out


def prune(zs, allowed, js, root, gadj, vert_of, m, fixed_mass, lo, hi) -> dict:
    """`allowed` less the pairs no connected drawing in the band can use: a district with a body
    reaches ZCTA z only along a path of ZCTAs it may own, whose mass (Dijkstra on node weights from
    its heaviest body) must fit in hi less its fixed mass; a district with no body lies inside one
    component of the ZCTAs it may own, which must hold at least lo less its mass elsewhere."""
    import heapq
    keep = {z: set(allowed[z]) for z in zs}
    for j in js:
        mine = {z for z in zs if j in keep[z]}
        if j in root:
            budget = hi - fixed_mass[j] + MASS_TOL * max(1.0, hi)
            starts = [y for y in gadj[root[j]] if y in mine]
            dist = {}
            heap = [(m.get(y, 0.0), y) for y in starts]
            heapq.heapify(heap)
            while heap:
                d, z = heapq.heappop(heap)
                if z in dist or d > budget:
                    continue
                dist[z] = d
                for y in gadj[z]:
                    if y not in dist and (y in mine or (vert_of.get(y) == j and y != root[j])):
                        heapq.heappush(heap, (d + m.get(y, 0.0), y))   # a body counts 0 here
            for z in mine - set(dist):
                keep[z].discard(j)
        else:
            for comp in components(mine, gadj):
                need = lo - fixed_mass[j]       # its mass elsewhere counts (`extra`)
                if math.fsum(m.get(z, 0.0) for z in comp) < need - MASS_TOL * max(1.0, lo):
                    for z in comp:
                        keep[z].discard(j)
    return {z: sorted(keep[z]) for z in zs}


def _solution(n, x0):
    sol = highspy.HighsSolution()
    sol.col_value = list(map(float, x0))
    sol.value_valid = True
    return sol


def construct(zs, allowed, js, gadj, vert_of, m, fixed_mass, lo, hi, geo, target, root,
              seed: dict | None = None, moves: int = 20000) -> tuple:
    """(a connected drawing of the group, or None with the reason), a heuristic that proves
    nothing.  Each district starts from its bodies and, given a `seed` drawing (a cut-loop
    solution), the component of its seed ZCTAs that holds its heaviest body (its heaviest
    component if it has none); with no seed, a district with no body starts at its ZCTA nearest its
    centre.  Districts then claim the free ZCTA next to them nearest along `geo`, the one furthest
    below its plan target first, and border moves that keep both districts connected and lower
    Σ (distance outside [lo, hi])² bring the masses into the band."""
    import heapq
    zset = set(zs)
    owner = {}
    region = {j: {b for b, k in vert_of.items() if k == j} for j in js}
    mass = dict(fixed_mass)
    if seed is not None:
        mine = collections.defaultdict(set)
        for z, j in seed.items():
            mine[j].add(z)
        for j in js:
            comps = components(mine[j] | region[j], gadj)
            if not comps:
                continue
            keep = next((cc for cc in comps if root.get(j) in cc), None) or max(
                comps, key=lambda cc: (math.fsum(m.get(z, 0.0) for z in cc), len(cc), min(cc)))
            for z in keep:
                if z in zset:
                    owner[z] = j
                    mass[j] += m.get(z, 0.0)
            region[j] |= set(keep)
    for j in js:
        if not region[j]:
            cand = [z for z in zs if j in allowed[z] and geo[j].get(z) == 0.0 and z not in owner]
            if not cand:
                return None, f"{j} has no seed"
            owner[cand[0]] = j
            region[j].add(cand[0])
            mass[j] += m.get(cand[0], 0.0)
    front = {j: [] for j in js}

    def push(j, z):
        for y in gadj[z]:
            if y in zset and y not in owner and j in allowed[y]:
                heapq.heappush(front[j], (geo[j].get(y, math.inf), y))
    for j in js:
        for z in list(region[j]):
            push(j, z)
    while len(owner) < len(zs):
        live = [j for j in js if front[j]]
        if not live:
            return None, f"growth stuck with {len(zs) - len(owner)} ZCTAs unclaimed"
        j = max(live, key=lambda j: ((target[j] - mass[j]) / max(1e-12, target[j]), j))
        while front[j]:
            d, z = heapq.heappop(front[j])
            if z not in owner:
                owner[z] = j
                region[j].add(z)
                mass[j] += m.get(z, 0.0)
                push(j, z)
                break
    for j in js:
        if len(components(region[j], gadj)) > 1:
            return None, f"{j}'s bodies do not join"

    def connected_without(j, z):
        rest = region[j] - {z}
        if not rest:
            return False
        start = root.get(j) or next(iter(rest))
        if start not in rest:
            return False
        seen, stack = {start}, [start]
        while stack:
            for y in gadj[stack.pop()]:
                if y in rest and y not in seen:
                    seen.add(y)
                    stack.append(y)
        return len(seen) == len(rest)

    def bad(x):
        return max(0.0, lo - x, x - hi)

    def path_move(t, donor):
        """{zip: t} for the shortest path from t's region to a positive ZCTA, through ZCTAs t may
        own (held by `donor` only, when given), when every donor stays connected and
        Σ (distance outside the band)² falls; else None."""
        prev, queue, hit = {}, collections.deque(sorted(region[t], key=str)), None
        seen = set(region[t])
        while queue and hit is None:
            z = queue.popleft()
            for y in sorted(gadj[z]):
                if y in seen or y not in owner or t not in allowed[y]:
                    continue
                if donor is not None and owner[y] != donor:
                    continue
                seen.add(y)
                prev[y] = z
                if m.get(y, 0.0) > 0:
                    hit = y
                    break
                queue.append(y)
        if hit is None:
            return None
        path = []
        while hit in prev:
            path.append(hit)
            hit = prev[hit]
        delta = collections.Counter()
        for z in path:
            delta[owner[z]] -= m.get(z, 0.0)
            delta[t] += m.get(z, 0.0)
        before = sum(bad(mass[j]) ** 2 for j in delta)
        after = sum(bad(mass[j] + delta[j]) ** 2 for j in delta)
        if after >= before - 1e-12 * max(1.0, hi) ** 2:
            return None
        for x in {owner[z] for z in path}:
            rest = region[x] - set(path)
            if not rest or len(components(rest, gadj)) > 1:
                return None
        return dict.fromkeys(path, t)

    tol = MASS_TOL * max(1.0, hi)
    for _ in range(moves):
        off = [j for j in js if bad(mass[j]) > tol]
        if not off:
            return owner, ""
        best = None
        for a in sorted(off, key=lambda j: -bad(mass[j])):
            if mass[a] > hi:        # a gives a border ZCTA to a neighbour
                pairs = [(z, a, k) for z in region[a] if z in owner
                         for k in {owner.get(y) or vert_of.get(y) for y in gadj[z]} - {a, None}
                         if k in allowed[z]]
            else:                   # a takes one from a neighbour
                pairs = [(y, owner[y], a) for z in region[a] for y in gadj[z]
                         if y in owner and owner[y] != a and a in allowed[y]]
            for z, x, y in pairs:
                w = m.get(z, 0.0)
                if w <= 0:
                    continue
                gain = bad(mass[x]) ** 2 + bad(mass[y]) ** 2 - bad(mass[x] - w) ** 2 \
                    - bad(mass[y] + w) ** 2
                if gain <= 1e-12 * max(1.0, hi) ** 2:
                    continue
                key = (gain, -geo[y].get(z, math.inf))
                if (best is None or key > best[0]) and connected_without(x, z):
                    best = (key, z, x, y)
            if best is not None:
                break
        if best is None:        # no single ZCTA helps: move a path through zero-mass ZCTAs
            path = None
            for a in sorted(off, key=lambda j: -bad(mass[j])):
                takers = [a] if mass[a] < lo else sorted(
                    {owner.get(y) or vert_of.get(y) for z in region[a] for y in gadj[z]} - {a, None})
                for t in takers:
                    path = path_move(t, a if mass[a] > hi else None)
                    if path is not None:
                        break
                if path is not None:
                    break
            if path is None:
                worst = max(off, key=lambda j: bad(mass[j]))
                return None, (f"no move helps {worst} ({mass[worst]:.6g} against "
                              f"[{lo:.6g}, {hi:.6g}])")
            for z in path:
                x = owner[z]
                owner[z] = path[z]
                region[x].discard(z)
                region[path[z]].add(z)
                mass[x] -= m.get(z, 0.0)
                mass[path[z]] += m.get(z, 0.0)
            continue
        _, z, x, y = best
        owner[z] = y
        region[x].discard(z)
        region[y].add(z)
        mass[x] -= m.get(z, 0.0)
        mass[y] += m.get(z, 0.0)
    return None, "move limit"


def _solve_group(c, zs, allowed, bodies, body_of, fixed, adj, m, p, unit_of, hold, plan, planned,
                 support, inst, lo, hi, arm, fixed_targets, time_limit, log=print,
                 extra: dict | None = None, dag: bool = False, start: dict | None = None) -> Group:
    t0 = time.time()
    ch, units = inst.channels[c], inst.units
    js = sorted({j for z in zs for j in allowed[z]})
    zset = set(zs)
    # the group graph: free ZCTAs and the bodies of its districts, each body one vertex
    bnode = {(j, i): f"@{j}#{i}" for j in js for i in range(len(bodies.get(j, ())))}
    gadj = collections.defaultdict(set)
    for z in zs:
        for y in adj[z]:
            if y in zset:
                gadj[z].add(y)
            elif y in body_of and body_of[y][0] in js:
                b = bnode[body_of[y]]
                gadj[z].add(b)
                gadj[b].add(z)
    vert_of = {b: j for (j, _), b in bnode.items()}         # body vertex -> its district
    for b in bnode.values():
        gadj.setdefault(b, set())
    root = {j: bnode[j, 0] for j in js if bodies.get(j)}     # the heaviest body: largest first
    fixed_mass = {j: math.fsum(m.get(z, 0.0) for b in bodies.get(j, ()) for z in b)
                  + (extra or {}).get(j, 0.0) for j in js}
    # shape centres per (unit, district), as td.realize places them
    cen = {}
    for v in sorted({unit_of[z] for z in zs}):
        mine = {j: support[j] for j in hold.get(v, []) if j in js}
        if v in ch.M and len(mine) > 1:     # only a share-only district's seed reads its centre
            cen.update({(v, j): x for j, x in tdrealize.centres(inst, c, v, mine, p).items()})
    allowed = prune(zs, allowed, js, root, gadj, vert_of, m, fixed_mass, lo, hi)
    empty = sorted(z for z in zs if not allowed[z])
    if empty:
        g = Group(js, sorted({unit_of[z] for z in zs}), len(zs), 0, 0, "infeasible",
                  note=f"{len(empty)} ZCTAs ({empty[0]}...) reachable by no district within the band")
        g.seconds = time.time() - t0
        return g
    mbar = (math.fsum(m.get(z, 0.0) for z in zs) / max(1, sum(1 for z in zs if m.get(z, 0.0) > 0))) or 1.0
    # columns
    geo = geodesic(zs, allowed, js, gadj, vert_of, cen, unit_of, p)
    col = {}
    cost = []
    for z in zs:
        for j in allowed[z]:
            col[z, j] = len(cost)
            cost.append((m.get(z, 0.0) / mbar + AREA_FLOOR) * geo[j].get(z, math.inf) ** 2)
    far = max((x for x in cost if math.isfinite(x)), default=1.0)
    cost = [x if math.isfinite(x) else 4.0 * far for x in cost]
    scale = SHAPE_SCALE / max(1e-12, math.fsum(max(cost[col[z, j]] for j in allowed[z]) for z in zs))
    cost = [x * scale for x in cost]
    ycol = {}
    for z in zs:
        v = unit_of[z]
        for j in allowed[z]:
            if (v, j) not in ycol:
                ycol[v, j] = len(cost)
                held = any(fixed.get(y) == j for y in units.zips.get(v, ()))
                cost.append(0.0 if held else SPLIT_WEIGHT)
    n = len(cost)
    h = highspy.Highs()
    h.setOptionValue("output_flag", False)
    h.setOptionValue("mip_rel_gap", 0.0)
    inf = highspy.kHighsInf
    h.addVars(n, np.zeros(n), np.ones(n))
    h.changeColsCost(n, np.arange(n, dtype=np.int32), np.array(cost))
    h.changeColsIntegrality(n, np.arange(n, dtype=np.int32),
                            np.array([highspy.HighsVarType.kInteger] * n))
    nrows = 0

    stored = []

    def row(lo_, hi_, idx, val):
        nonlocal nrows
        h.addRow(lo_, hi_, len(idx), np.array(idx, dtype=np.int32), np.array(val, dtype=float))
        stored.append((lo_, hi_, idx, val))
        nrows += 1

    for z in zs:
        row(1.0, 1.0, [col[z, j] for j in allowed[z]], [1.0] * len(allowed[z]))
        for j in allowed[z]:
            row(-inf, 0.0, [col[z, j], ycol[unit_of[z], j]], [1.0, -1.0])
    for j in js:
        idx = [col[z, j] for z in zs if (z, j) in col and m.get(z, 0.0) > 0]
        row(lo - fixed_mass[j], hi - fixed_mass[j], idx, [m[z] for z in zs if (z, j) in col and m.get(z, 0.0) > 0])
    if arm == "move":
        for v in sorted({unit_of[z] for z in zs}):
            if len(hold.get(v, [])) > 1:
                ks = [k for (u, j), k in ycol.items() if u == v]
                row(-inf, float(len(hold[v])), ks, [1.0] * len(ks))
    if fixed_targets:
        for v in sorted({unit_of[z] for z in zs}):
            if v not in ch.M:
                continue
            top = max(m[z] for z in units.zips[v])
            for j in js:
                idx = [col[z, j] for z in units.zips[v] if (z, j) in col and m[z] > 0]
                a = planned.get((v, j), 0.0) - math.fsum(m[z] for z in units.zips[v]
                                                         if fixed.get(z) == j and z not in zset)
                row(a - top, a + top, idx, [m[z] for z in units.zips[v] if (z, j) in col and m[z] > 0])
    # a ZCTA of a district needs a neighbour of it (when the district has two vertices or more);
    # under `dag`, a neighbour nearer its bodies or seed along `geo` (CONTIGUITY.md §4 rank 2)
    for z in zs:
        for j in allowed[z]:
            nb = sorted(gadj[z])
            if any(vert_of.get(y) == j for y in nb):
                continue
            if dag:
                dz = geo[j].get(z, math.inf)
                if dz == 0.0:
                    continue
                idx = [col[y, j] for y in nb if (y, j) in col and geo[j].get(y, math.inf) < dz]
                row(-inf, 0.0, [col[z, j]] + idx, [1.0] + [-1.0] * len(idx))
                continue
            if j not in root and max((m.get(y, 0.0) for y in zs if (y, j) in col),
                                     default=0.0) >= lo - fixed_mass[j]:
                continue
            idx = [col[y, j] for y in nb if (y, j) in col]
            row(-inf, 0.0, [col[z, j]] + idx, [1.0] + [-1.0] * len(idx))
    g = Group(js, sorted({unit_of[z] for z in zs}), len(zs), n, nrows)
    deadline = t0 + time_limit
    gap = PHASE1_GAP            # until a connected drawing is found, then 0 (trap 12)
    found = None                # the best connected drawing: (owner, objective, bound)
    target = {cp.name: cp.total for cp in plan.copies}
    tol = 1e-7 * max(1.0, hi)

    def accept(start, how):
        """Keep `start` (a connected drawing) when it meets every row and beats `found`."""
        nonlocal found, x_best
        x0 = np.zeros(n)
        for z, j in start.items():
            x0[col[z, j]] = 1.0
            x0[ycol[unit_of[z], j]] = 1.0
        if not all(lo_ - tol <= sum(x0[i] * a for i, a in zip(idx, val)) <= hi_ + tol
                   for lo_, hi_, idx, val in stored):
            log(f"    the {how} drawing breaks a row (band or targets)")
            return
        obj = float(np.dot(cost, x0))
        if found is None or obj < found[1] - 1e-9:
            found, x_best = (dict(start), obj, None), x0
            log(f"    {how}: a connected drawing in the band, objective {obj:.6g}, "
                f"{time.time() - t0:.1f}s")

    x_best = None
    if start is not None:
        accept(start, "given")
    built, why = construct(zs, allowed, js, gadj, vert_of, m, fixed_mass, lo, hi, geo, target, root)
    if built is None:
        log(f"    no constructed drawing: {why}")
    else:
        accept(built, "constructed")
    info = None
    while True:
        left = deadline - time.time()
        if left <= 0:
            g.note = "time limit"
            break
        h.setOptionValue("time_limit", float(left))
        h.setOptionValue("mip_abs_gap", gap)
        if x_best is not None:
            h.setSolution(_solution(n, x_best))
        h.run()
        g.iterations += 1
        st = h.getModelStatus()
        info = h.getInfo()
        log(f"    solve {g.iterations} (gap {gap:g}): {h.modelStatusToString(st)}, "
            f"objective {info.objective_function_value:.6g}, {time.time() - t0:.1f}s, {nrows} rows")
        if st == highspy.HighsModelStatus.kInfeasible:
            g.status, g.note = "infeasible", f"proved at solve {g.iterations}"
            break
        has = info.primal_solution_status == 2
        if not has:
            g.note = f"no incumbent ({h.modelStatusToString(st)})"
            break
        if found is not None and info.objective_function_value >= found[1] - 1e-9 \
                and st != highspy.HighsModelStatus.kOptimal:
            g.note = "time limit: the constructed drawing stands"
            break
        x = h.getSolution().col_value
        own = {z: max(allowed[z], key=lambda j: x[col[z, j]]) for z in zs}
        verts = collections.defaultdict(set)
        for z, j in own.items():
            verts[j].add(z)
        for b, j in vert_of.items():
            verts[j].add(b)
        new, detached = 0, []
        for j in js:
            comps = components(verts[j], gadj)
            if len(comps) < 2:
                continue
            if j in root:
                main = next(cc for cc in comps if root[j] in cc)
            else:
                main = max(comps, key=lambda cc: (math.fsum(m.get(z, 0.0) for z in cc), len(cc)))
            for cc in comps:
                if cc is main:
                    continue
                detached.append((len(cc), round(math.fsum(m.get(z, 0.0) for z in cc), 4), j,
                                 "+".join(sorted({unit_of.get(z, "body") for z in cc})), min(cc)))
                # two separators: the ring around cc, and the ring around the main component
                # seen from cc (every path of j's from cc to main crosses each)
                can = {y for y in gadj if (y, j) in col or vert_of.get(y) == j}
                seen, stack = set(cc), list(cc)
                while stack:
                    for y in gadj[stack.pop()]:
                        if y not in seen and y in can and y not in main:
                            seen.add(y)
                            stack.append(y)
                near_main = {y for z in main for y in gadj[z]} - main
                seps = {tuple(sorted({y for z in cc for y in gadj[z]} - cc)),
                        tuple(sorted(near_main & seen))}
                for sep in sorted(seps):
                    sidx = [col[y, j] for y in sep if (y, j) in col]
                    if j in root:
                        for z in cc:
                            if z in vert_of:
                                row(1.0, inf, sidx, [1.0] * len(sidx))
                            else:
                                row(-inf, 0.0, [col[z, j]] + sidx, [1.0] + [-1.0] * len(sidx))
                            new += 1
                    else:
                        b = max((y for y in main if (y, j) in col), key=lambda y: (m.get(y, 0.0), y))
                        for z in cc:
                            row(-inf, 1.0, [col[z, j], col[b, j]] + sidx, [1.0, 1.0] + [-1.0] * len(sidx))
                            new += 1
        g.cuts += new
        if new:
            log(f"      {len(detached)} detached components: sizes {sorted(detached)[-4:]}; band [{lo:.4g}, {hi:.4g}]")
            fixed_up, why = construct(zs, allowed, js, gadj, vert_of, m, fixed_mass, lo, hi, geo,
                                      target, root, seed=own)
            if fixed_up is None:
                log(f"      no repaired drawing: {why}")
            else:
                accept(fixed_up, "repaired")
        optimal = st == highspy.HighsModelStatus.kOptimal
        if new == 0:
            found = (own, info.objective_function_value, info.mip_dual_bound)
            if optimal and gap == FINAL_ABS_GAP:
                g.status = "optimal"
                break
            if not optimal:
                break
            gap = FINAL_ABS_GAP         # connected at the phase-1 gap: prove it at 0
            continue
        if not optimal:
            g.note = f"stopped at solve {g.iterations} ({h.modelStatusToString(st)}) with a detached incumbent"
            break
    if found is not None and g.status != "infeasible":
        g.owner, g.objective, g.bound = found
        if g.bound is None and info is not None and info.mip_dual_bound is not None \
                and math.isfinite(info.mip_dual_bound):
            g.bound = info.mip_dual_bound       # the last solve's bound holds for every drawing
        g.gap = abs(g.objective - g.bound) / max(1e-12, abs(g.objective)) if g.bound is not None else None
        if g.status != "optimal" or dag:
            g.status = "connected"      # under `dag` an optimum is the restriction's only
    if dag and g.status == "infeasible":
        g.status, g.note = "unknown", "the geodesic-DAG restriction is infeasible"
    g.dag = dag
    g.rows = nrows
    g.seconds = time.time() - t0
    return g


# ------------------------------------------------------------------------------ the map
def drawing(inst, plan, res: Result, fallback=None) -> tdrealize.Drawing:
    """`td.realize.Drawing` of `res`, every footprint ZCTA owned.  The ZCTAs of a group without a
    connected drawing take `fallback`'s owner (`td.realize` + `td.territory`), so the run still
    writes a full ledger and M1 fails on them."""
    c = plan.channel
    ch, units = inst.channels[c], inst.units
    owner = dict(res.owner)
    if res.undrawn:
        owner.update({z: fallback.owner[z] for z in res.undrawn})
    foot = territory.footprint(inst, c)
    missing = foot - set(owner)
    if missing:
        raise RuntimeError(f"{c}: {len(missing)} footprint ZCTAs without an owner")
    planned = {(v, cp.name): cp.mass[v] for cp in plan.copies for v in cp.support}
    drawn = dict.fromkeys(planned, 0.0)
    mass = {cp.name: 0.0 for cp in plan.copies}
    for z, j in owner.items():
        x = ch.m.get(z, 0.0)
        mass[j] += x
        v = units.unit_of[z]
        if (v, j) in drawn or (x > 0 and v in ch.M):
            drawn[v, j] = drawn.get((v, j), 0.0) + x
    support = {cp.name: frozenset(cp.support) | {units.unit_of[z] for z, j in owner.items()
                                                 if j == cp.name and ch.m.get(z, 0.0) > 0}
               for cp in plan.copies}
    return tdrealize.Drawing(c, owner, mass, planned, drawn,
                             tdrealize.pieces(inst, c, owner, support, planned))
