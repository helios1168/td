"""supports.py -- the closed support family 𝒮_c and its drawability terms (`MODEL.md` §2, §4).

**The family.**  `family(inst, channel)` is, in order:
1. every set S ⊆ V_c with G[S] connected, |S| ≤ s̄_c and d(u, v) ≤ R_c(u, v) for every pair
   (skipped when the channel's supports are `listed`).  The legacy `generate_valid_supports`
   (`tools/group2_support.py:27–63` at the tag) builds the same family; here each connected set
   is enumerated once (Wernicke's ESU) and the distance cap prunes during the search, which is
   exact because the cap is pairwise;
2. the spec's extra supports, each with all of its connected subsets;
3. the filters, all forbidden pairs: a support holding both units of a pair is removed.  The
   legacy National filter is not ported (C19): its "New England only as a block" and "SC only
   with NC or GA" rules drop subsets of supports they keep.  A forbidden pair only ever removes
   supersets, so the family stays closed;
4. the closure check on the final family (C2, C19), which raises if any support has a connected
   subset outside the family, and a coverage check that every unit of V_c is in some support.

The distance d(u, v) is between the unit centroids of `td.spec` (land-weighted ZIP points, km).
R_c(u, v) = max(max_dist_km, dist_km[u], dist_km[v]), the legacy per-state rule.

**Drawability terms**, per channel:
- `corridor_floor(inst, ch, S, v)`: c_v(S), the component-versus-rest floor of §4.2 (C6), by
  node-weighted shortest paths on G_v;
- `border_count(inst, u, v)`: b_{uv}, the number of v's ZIPs with a ZIP-graph edge into u;
- `border_rows(fam)`: for each free v and u ∈ N(v), the supports of the corrected border cap
  Σ_{S∋v, N(v)∩S={u}} n_S ≤ b_{uv} (C7);
- `margin(inst, c, S)`: μ_S, the sum over S's splittable units of the heaviest ZIP (§4.6);
- `diameter(inst, S)`: w_S, the largest centroid distance in S (§3.5).
"""
from __future__ import annotations

import heapq
import math
from dataclasses import dataclass

from td.spec import SpecError


@dataclass
class Family:
    channel: str
    supports: tuple             # frozensets, by size then by sorted units
    adj: dict                   # the unit graph G[V_c]
    enumerated: int             # step 1's count, before extras and filters
    removed: int                # supports the filters removed

    def __len__(self) -> int:
        return len(self.supports)

    def __contains__(self, s) -> bool:
        return frozenset(s) in self._set

    def __post_init__(self):
        self._set = frozenset(self.supports)


def unit_graph(inst, channel: str) -> dict:
    ch = inst.channels[channel]
    keep = set(ch.units)
    return {u: inst.units.unit_adj[u] & keep for u in ch.units}


def connected(nodes, adj) -> bool:
    nodes = set(nodes)
    if not nodes:
        return False
    start = next(iter(nodes))
    seen, stack = {start}, [start]
    while stack:
        a = stack.pop()
        for b in adj[a]:
            if b in nodes and b not in seen:
                seen.add(b)
                stack.append(b)
    return len(seen) == len(nodes)


def connected_sets(nodes, adj: dict, max_size: int, ok=lambda u, v: True) -> list:
    """Every S ⊆ nodes with G[S] connected, |S| ≤ max_size and ok(u, v) for all pairs, each
    once (ESU: extend only by vertices above the seed that are not already next to the set)."""
    order = {v: i for i, v in enumerate(sorted(nodes))}
    out = []

    def extend(sub, ext, near, seed):
        out.append(frozenset(sub))
        if len(sub) >= max_size:
            return
        ext = sorted(ext, key=order.get)
        while ext:
            w = ext.pop()
            new = [u for u in adj[w] if u in order and order[u] > order[seed] and u not in near
                   and all(ok(u, x) for x in sub) and ok(u, w)]
            rest = [u for u in ext if ok(u, w)]
            extend(sub | {w}, rest + new, near | adj[w] | {w}, seed)

    for v in sorted(nodes, key=order.get):
        ext = [u for u in adj[v] if u in order and order[u] > order[v] and ok(u, v)]
        extend({v}, ext, adj[v] | {v}, v)
    return out


def connected_subsets(s, adj) -> list:
    """Every connected subset of S (S itself included)."""
    s = sorted(s)
    sub_adj = {u: adj[u] & set(s) for u in s}
    return connected_sets(s, sub_adj, len(s))


def closure_violations(supports, adj: dict) -> list:
    """(S, T) for each support S and connected T = S − x not in the family.  Checking one
    deletion at a time suffices: every connected T ⊊ S is reached from S by deleting, one at a
    time, a vertex of S − T whose removal keeps the set connected."""
    have = set(map(frozenset, supports))
    out = []
    for s in have:
        for x in s:
            t = s - {x}
            if t and t not in have and connected(t, adj):
                out.append((s, t))
    return out


def family(inst, channel: str, max_size: int | None = None) -> Family:
    """The final closed family 𝒮_c.  `max_size` overrides the spec's size cap (U32 counts)."""
    ch = inst.channels[channel]
    cs = ch.spec
    adj = unit_graph(inst, channel)
    cap = cs.max_size if max_size is None else max_size
    if isinstance(cap, bool) or not isinstance(cap, int) or cap < 1:
        raise SpecError(f"channel {channel}: max_size must be an integer >= 1, not {cap!r}")

    def ok(u, v):
        return inst.units.distance_km(u, v) <= cs.dist_cap(u, v)

    found = set() if cs.listed_only else set(connected_sets(ch.units, adj, cap, ok))
    enumerated = len(found)
    for s in cs.extra_supports:
        s = s & set(ch.units)       # a unit dropped for zero opportunity leaves the extra
        if not s:
            continue
        if not connected(s, adj):
            raise SpecError(f"channel {channel}: extra support {sorted(s)} is not connected")
        found |= set(connected_subsets(s, adj))
    before = len(found)
    found = {s for s in found if not any(p <= s for p in cs.forbid_pairs)}
    for s in cs.extra_supports:
        s = frozenset(s & set(ch.units))
        if s and s not in found:
            raise SpecError(f"channel {channel}: a filter removes the extra support {sorted(s)}")
    bad = closure_violations(found, adj)
    if bad:
        raise SpecError(f"channel {channel}: the family is not closed under connected subsets: "
                        f"{len(bad)} cases, e.g. {sorted(bad[0][0])} without {sorted(bad[0][1])}")
    covered = set().union(*found) if found else set()
    if set(ch.units) - covered:
        raise SpecError(f"channel {channel}: units in no support: "
                        f"{sorted(set(ch.units) - covered)}")
    supports = tuple(sorted(found, key=lambda s: (len(s), sorted(s))))
    return Family(channel, supports, adj, enumerated, before - len(found))


# ------------------------------------------------------------------------------ drawability
def cut_components(s, v, adj) -> list:
    """The components of G[S] − v, as frozensets; two or more when v is a cut vertex of G[S]."""
    rest = set(s) - {v}
    comps, seen = [], set()
    for a in sorted(rest):
        if a in seen:
            continue
        comp, stack = {a}, [a]
        seen.add(a)
        while stack:
            x = stack.pop()
            for y in adj[x]:
                if y in rest and y not in seen:
                    seen.add(y)
                    comp.add(y)
                    stack.append(y)
        comps.append(frozenset(comp))
    return comps


def cut_vertices(s, adj) -> list:
    return [v for v in sorted(s) if len(s) > 2 and len(cut_components(s, v, adj)) >= 2]


def borders(inst, v: str) -> dict:
    """u -> the set of v's ZIPs with a ZIP-graph edge into unit u."""
    units, out = inst.units, {}
    for z in units.zips[v]:
        for y in units.zip_adj[z]:
            u = units.unit_of[y]
            if u != v:
                out.setdefault(u, set()).add(z)
    return out


def border_count(inst, u: str, v: str) -> int:
    """b_{uv}."""
    return len(borders(inst, v).get(u, ()))


def lightest_path(zs, zip_adj, m: dict, sources, targets) -> float:
    """The least Σ m_z over the ZIPs of a path in G[zs] from `sources` to `targets`; a ZIP in
    both is a path.  inf when there is none."""
    inside, targets = set(zs), set(targets)
    dist = {z: m[z] for z in sources}
    heap = [(d, z) for z, d in dist.items()]
    heapq.heapify(heap)
    while heap:
        d, z = heapq.heappop(heap)
        if d > dist[z]:
            continue
        if z in targets:
            return d
        for y in zip_adj[z]:
            if y in inside and d + m[y] < dist.get(y, math.inf):
                dist[y] = d + m[y]
                heapq.heappush(heap, (dist[y], y))
    return math.inf


def corridor_floor(inst, channel: str, s, v: str, _cache: dict | None = None,
                   _adj: dict | None = None) -> float:
    """c_v(S) = max_i c^i_v(S), for v a cut vertex of G[S] (§4.2, C6); 0 when it is not."""
    ch = inst.channels[channel]
    adj = unit_graph(inst, channel) if _adj is None else _adj
    comps = cut_components(s, v, adj)
    if len(comps) < 2:
        return 0.0
    bd = borders(inst, v)
    sides = [frozenset().union(*(bd.get(u, set()) for u in a)) for a in comps]
    # the sides as a multiset: two components on one border make that side meet the rest there,
    # so a set of sides would share its key with a support whose floor differs
    key = (channel, v, tuple(sorted(tuple(sorted(side)) for side in sides)))
    if _cache is not None and key in _cache:
        return _cache[key]
    zs = inst.units.zips[v]
    floor = 0.0
    for i, side in enumerate(sides):
        rest = frozenset().union(*(t for j, t in enumerate(sides) if j != i))
        floor = max(floor, lightest_path(zs, inst.units.zip_adj, ch.m, side, rest))
    if _cache is not None:
        _cache[key] = floor
    return floor


def corridor_floors(inst, fam: Family) -> dict:
    """(S, v) -> c_v(S) for every support and each of its cut vertices."""
    cache: dict = {}
    return {(s, v): corridor_floor(inst, fam.channel, s, v, cache, fam.adj)
            for s in fam.supports for v in cut_vertices(s, fam.adj)}


def border_rows(inst, fam: Family) -> dict:
    """(u, v) -> (b_{uv}, [S ∈ 𝒮_c : v ∈ S, N(v) ∩ S = {u}]) for each free v and u ∈ N(v)
    (§4.3, C7: the sum runs over supports holding v)."""
    ch = inst.channels[fam.channel]
    rows = {}
    for v in ch.units:
        if ch.mode[v] != "free":
            continue
        for u in sorted(fam.adj[v]):
            rows[u, v] = (border_count(inst, u, v),
                          [s for s in fam.supports if v in s and fam.adj[v] & s == {u}])
    return rows


def margin(inst, channel: str, s) -> float:
    """μ_S (§4.6)."""
    ch = inst.channels[channel]
    return sum(max(ch.m[z] for z in inst.units.zips[v]) for v in s if ch.splittable(v))


def diameter(inst, s) -> float:
    """w_S = max_{u,v∈S} d(u, v), km."""
    return max((inst.units.distance_km(u, v) for u in s for v in s), default=0.0)
