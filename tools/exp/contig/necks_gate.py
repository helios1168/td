"""necks_gate.py -- M1's neck model as the gate (`td.audit.check_m1`) reads it, for every check
that runs before the gate: window repair (`repair.py`), plan checking (`plancheck.py`), whole-unit
plans (`wholeplan.py`) and glue (`glue.py`).  One place, so that they cannot drift again (#142; the
review `notes/2026-10-14_national-approaches-review.md` §2 C14, C15, §3.1).

The gate judges a district with `td.audit.district_necks(zips, mass, ng, free=zero)`:

- `ng` is `gate_graph(polygon)`: gap width on unless `TD_NECK_GAP_WIDTH` is "0", the pre-2026-10-14
  land rule off unless `TD_NECK_PRE_2026_10_14_LAND_RULE` is "1" (`check_m1`'s defaults);
- `zero` is the ZCTAs of zero opportunity in the district's planning channel (`zero_opportunity`),
  whoever owns them: they join the district's graph as relays (R3, `audit.neck_relays`);
- the width of an edge is `audit.neck_widths`: the polygon border or gap width in whole cm plus, for
  an approved connector, the limit (#140, R1); a cut is a neck under 10 km.

`gate_necks` is that call; `edge_km` is one edge's width in a row of a MILP.  `cut_terms` is the
edge list of a `draw.NeckCut` row and `bridged` the condition of the plan check's wide-passage rows;
each says under which condition it is valid for the gate's model."""
from __future__ import annotations

import collections
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from td import audit  # noqa: E402

# a cut of floored whole cm (`audit.border_cm`) is a neck at NECK_W_CM - 1 or less and none at
# NECK_W_CM or more; half a cm between keeps a row's float sums off either side
NECK_KM = (audit.NECK_W_CM - 0.5) / 1e5


def gate_graph(polygon: dict, gap_width: bool | None = None,
               land_rule: bool | None = None) -> "audit.NeckGraph":
    """`audit.NeckGraph` as `audit.check_m1` builds its own: `gap_width` None reads
    `audit.gap_width_on()`, `land_rule` None reads `TD_NECK_PRE_2026_10_14_LAND_RULE`."""
    if gap_width is None:
        gap_width = audit.gap_width_on()
    if land_rule is None:
        land_rule = os.environ.get(audit.LAND_RULE_ENV) == "1"
    return audit.NeckGraph(polygon, gap_width=gap_width, pre_2026_10_14_land_rule=land_rule)


def zero_opportunity(m: dict) -> frozenset:
    """The gate's relay candidates in a channel with masses `m` {ZCTA: m}: the ZCTAs of `m` with no
    opportunity (`check_m1`: `{z for z, m in chm[ch].items() if not m > 0}`).  `m` must list every
    ZCTA of the channel, those of dropped units too (`channel_mass`); a ZCTA it does not list is
    never a relay."""
    return frozenset(z for z, x in m.items() if not x > 0)


_MASS = {}      # (id(inst), channel) -> (inst, {zip: m})


def channel_mass(inst, c: str) -> dict:
    """`inst.channels[c].m` plus 0.0 for the ZCTAs of the channel's dropped units (zero
    opportunity, and rows of the channel in the ledger: the gate's `chm[c]` counts them), so that
    `zero_opportunity` of it is the gate's relay set."""
    key = (id(inst), c)
    if key not in _MASS:
        ch = inst.channels[c]
        m = {z: 0.0 for u in ch.dropped_units for z in inst.units.zips.get(u, ())}
        m.update(ch.m)
        _MASS[key] = (inst, m)
    return _MASS[key][1]


def gate_necks(zips, m: dict, ng, time_limit: float = audit.NECK_TIME) -> list:
    """The necks the gate finds in a district holding `zips`: `audit.district_necks` with the
    channel's zero-opportunity ZCTAs as relays (`m`: `channel_mass`)."""
    return audit.district_necks(set(zips), m, ng, time_limit, free=zero_opportunity(m))


def width_nbrs(ng, z: str) -> set:
    """The ZCTAs `z` shares a width edge with in the gate: polygon and gap edges and connectors."""
    return set(ng.border_cm.get(z, ())) | ng.connector.get(z, set())


def edge_km(ng, u: str, v: str, states: frozenset) -> float:
    """The width of the edge u-v as `audit.neck_widths` counts it, in km, at most `NECK_KM`;
    `states` are the states of the district (read only with the pre-2026-10-14 land rule)."""
    a, b = sorted((u, v))
    return min(audit.neck_widths((a, b), ng, states).get((a, b), 0) / 1e5, NECK_KM)


def cut_terms(nk, D: set, fixed: set, W: set, seed: set, ng, zero, states: frozenset,
              area_fixed: float):
    """(const, {z: km}, [(u, v, km)]) of a `draw.NeckCut` row for the neck `nk` of district j
    (`repair.neck_cuts`): const + Σ single[z]·[z is j's] + Σ km·[u and v are j's] is at least the
    gate's cut of j's part C of A = `nk.zips`, over the gate's width graph (`edge_km`).  `D` is
    j's ZCTAs on the map `nk` was found on, `fixed` those j owns outside the window `W` (A lies in
    `fixed | W`), `seed` the anchor set in A that j holds when the row binds, `area_fixed` the
    land of `fixed` (m²).

    **Valid for every drawing of W in which j has no neck, as `draw.NeckCut` binds it**, that is
    when C, the own-connected part of A that holds `seed`, holds the share of j's land.  If A holds
    at most half of `area_fixed`, C holds no more than half of j's land in every drawing (it lies
    in A, and j owns all of `fixed`), so the gate may cut C off, with every relay and every other
    ZCTA on either side.  The row takes one such cut, the relays where the gate's cut `nk.cut`
    puts them: those of D joined to A by edges the cut spares (`RA`) go with C, the others, and
    every ZCTA that is a relay only in another drawing, with the rest.  The terms are the widths
    of all edges between the sides, counting more than the cut of a drawing where they do not
    apply:

    - from a ZCTA of A to every ZCTA outside A and outside `RA` that is j's, or a possible relay
      (`audit.neck_relays` of `fixed | W`), or in W and of zero opportunity (j's or a relay:
      counted as present either way; the widened rows below count it a possible relay too), polygon, gap and connector edges alike;
    - inside A, but for edges between two ZCTAs of `core` (both in C in every drawing: j's `fixed`
      ZCTAs of A connected to `seed`), every edge that is no own edge (`NeckGraph.own_edge`: C is a
      component of j's part of A, so it may join C to the rest of A), and every edge to a ZCTA of W
      of zero opportunity, an own edge too: j may not own it in the drawing, and it is a relay;
    - from a relay of `RA` outside W (on C's side in every drawing, and never j's) to everything it
      touches that is j's, a possible relay or in W and of zero opportunity, but for `core`;
    - for a relay r of `RA` in W, which j may own instead: the larger of its edges from A (j owns it,
      it is off C) and its edges to the rest (j does not, it goes with C), all ends counted as
      present; and, only if j owns r, its edges to the relays that stay with C (`RA` outside W, the
      other relays of `RA` in W): owning r cuts them.

    When A holds more than half of `area_fixed`, C may hold more than half of j's land and the gate
    then cuts off another part K of j instead, among the rest: the terms then count also every edge
    among `fixed | W` and the possible relays outside A that is no own edge, and every edge from a
    possible relay to them, whatever side the cut puts the relays on.  Counting more edges only
    weakens a row, so it stays valid, at the price of binding less next to large relays."""
    A = set(nk.zips)
    area_a = sum(ng.aland.get(z, 0.0) for z in A)
    widen = area_a > 0.5 * (1 + audit.NECK_TOL) * area_fixed
    relays = audit.neck_relays(fixed | W, ng, zero) | (W & set(zero))      # as `bridged`'s candidates
    cut = {(a, b) for a, b, _ in nk.cut}
    side = set(A)                       # A and the relays of D it keeps, without a cut edge
    stack = list(A)
    relays_d = audit.neck_relays(set(D), ng, zero)
    while stack:
        z = stack.pop()
        for y in width_nbrs(ng, z):
            if y in relays_d and y not in side and tuple(sorted((z, y))) not in cut:
                side.add(y)
                stack.append(y)
    ra = side - A
    ra_out = ra - W
    core = set(seed & fixed & A)
    stack = list(core)
    while stack:
        z = stack.pop()
        for y in width_nbrs(ng, z):
            if y in A and y in fixed and y not in core and ng.own_edge(z, y):
                core.add(y)
                stack.append(y)

    def kind(z, tail=False):
        """f: j's always (const); a: present whoever owns it (const); w: present if j's.  The end of
        an edge that lies in C (`tail`) must be j's; the other end may also be a relay."""
        if z in fixed:
            return "f"
        if tail:
            return "w" if z in A and z in W else None
        if z in relays or (z in W and z in zero):
            return "a"
        return "w" if z in W else None

    def terms_of(edges):
        """(const, Counter single, [pair]) of the edges (u, v, tail) whose two ends can be present."""
        const, single, pair = 0.0, collections.Counter(), []
        for u, v, tail in edges:
            ku, kv = kind(u, tail), kind(v)
            if ku is None or kv is None:
                continue
            w = edge_km(ng, u, v, states)
            if w <= 0:
                continue
            if ku != "w" and kv != "w":
                const += w
            elif kv != "w":
                single[u] += w
            elif ku != "w":
                single[v] += w
            else:
                pair.append((min(u, v), max(u, v), w))
        return const, single, pair

    ra_w = ra & W                       # relays on C's side that j may own instead
    edges = []
    for u in sorted(A):
        for v in sorted(width_nbrs(ng, u)):
            if v in ra_out or v in ra_w:
                continue
            if v not in A or (not (u in core and v in core) and (
                    (not ng.own_edge(u, v) and u < v) or (ng.own_edge(u, v) and v in W and v in zero))):
                edges.append((u, v, True))
    for r in sorted(ra_out):            # relays that go with C: the edges to the rest of j
        edges += [(v, r, False) for v in sorted(width_nbrs(ng, r))
                  if v not in ra_out and v not in ra_w and v not in core]
    if widen:
        rest = (fixed | W | relays) - A
        for z in sorted(rest):
            edges += [(z, y, False) for y in sorted(width_nbrs(ng, z))
                      if y > z and y in rest and not (z in relays and y in relays)
                      and (z in relays or y in relays or not ng.own_edge(z, y))]
    const, single, pair = terms_of(edges)
    for r in sorted(ra_w):
        # j owns r (then the edges from A count: r lies outside A, off C) or not (then r is a relay
        # with C and its edges to the rest count): the row takes the larger of the two, all ends
        # counted as present.  Owning r also cuts it off from the relays that stay with C, those of
        # `ra_out` and the other relays of `ra_w` (which j may leave to C): those edges count only if
        # j owns r, so they are a term of r's own (an edge in both its ends' terms only weakens the
        # row)
        mine = [(u, r, True) for u in sorted(A) if r in width_nbrs(ng, u)]
        relay_edges = [(v, r, False) for v in sorted(width_nbrs(ng, r))
                       if v in ra_out or (v in ra_w and v != r)]
        theirs = [(v, r, False) for v in sorted(width_nbrs(ng, r))
                  if v not in ra_out and v not in ra_w and v not in core and v not in A]
        const += max(sum(c + sum(sg.values()) + sum(w for *_, w in pr)
                         for c, sg, pr in [terms_of(es)]) for es in (mine, theirs))
        c, sg, pr = terms_of(relay_edges)
        if c + sum(sg.values()) + sum(w for *_, w in pr) > 0:
            single[r] += c + sum(sg.values()) + sum(w for *_, w in pr)
    return const, dict(single), pair


def bridged(fixed: set, optional: set, ng, zero, node_of=None) -> bool:
    """Whether the gate's width graph over the ZCTAs a district may own (`fixed`, which it owns in
    every drawing, and `optional`) has an edge that a flow among its nodes would not count right.
    `node_of(z)` names the node a ZCTA is contracted into (default: itself; the plan check
    contracts a held unit's component into a body).  That is a width edge between two nodes that
    is no own edge (`NeckGraph.own_edge`), or a possible relay cluster touching two nodes or more:
    a connected set of zero-opportunity ZCTAs that are not `fixed` and that `audit.neck_relays`
    reaches (an optional one too: left out of the district it is a relay), touching the nodes that
    are not in it.  The plan check's wide-passage rows (`plancheck.wide_rows`) are valid for the
    gate only when this is False: with nothing bridged every relay cluster touches one node at most
    and goes to that node's side of any cut at no cost, and no cut gains an edge the flow does not
    carry."""
    node_of = node_of or (lambda z: z)
    zips = set(fixed) | set(optional)
    for z in zips:
        for y in width_nbrs(ng, z):
            if y in zips and z < y and node_of(z) != node_of(y) and not ng.own_edge(z, y):
                return True
    cand = audit.neck_relays(zips, ng, zero) | (set(optional) & set(zero))
    seen = set()
    for r0 in sorted(cand):
        if r0 in seen:
            continue
        touched, stack = set(), [r0]
        seen.add(r0)
        while stack:
            r = stack.pop()
            for y in width_nbrs(ng, r):
                if y in cand:
                    if y not in seen:
                        seen.add(y)
                        stack.append(y)
                elif y in zips:
                    touched.add(node_of(y))
        if len(touched) > 1:
            return True
    return False
