"""audit.py -- the #52 §4 audit (`docs/MODEL.md` §9): check a run's ledger, write `scorecard.md`.

A run hands the audit a `Run`: its ledger, one `Cell` per (ZIP, fine channel), and what it
planned.  Every mass and share the audit reports comes from the ledger (S26); the run's own
reports are only compared with it.  Each check ends in one status:

    pass        the check holds
    fail        a hard failure, so the run fails (S28, C16, OD1, OD3)
    listed      it holds, with items the scorecard lists for a reader
    unverified  the run lacks what the check needs, as the tagged catalog lacks opportunity

Two share defects are kept apart (#70):
- a *phantom share* is a share the run reports that the ledger does not back: a reported drawn
  share of a unit that differs from the ledger's, or a cell owned by a pseudo-district such as
  the legacy `other`.  It fails the run (S26: a share exists only as a set of ZIPs).
- a *vanished share* is a planned share drawn as no ZIPs.  It is listed, not failed (C8).

**M1** (`docs/problem/MANDATES.md`, #108) is `check_m1`, on the polygon graph
(`geo.polygon_graph`: every CONUS ZCTA, the TIGER ZCTA polygons' rook edges and the owner-approved
connectors only).  It fails the run when a district's ZCTAs in the ledger are not one component
of that graph, when a district has a neck (#121, `district_necks`: a connected part holding 5% of
its land area beyond a passage under 10 km of shared border, an approved connector counting as
unlimited unless land within the district's states would do through a passage itself 10 km wide
(`NeckGraph.land_would_do`), where it is 0 km; the necks by mass
are listed beside M1 for the owner, and fail nothing), or when a CONUS
ZCTA is not owned exactly once per fine channel (#116): every
(ZCTA, fine channel) cell of the scenario has a row, at most one owned row, and an owned row
unless the planning channel holding it was dropped for zero opportunity (not among the run's
channels, no districts), in which case its blank row is excused.  The fine channels and the
planning channel holding each cell come from the scenario (`Run.fine`, `Run.route`), never from
the ledger: a run without them, as a run folder read back, checks the fine channels of
`run.json` or, before #116, of the ledger, and cannot check the routing.  Two districts owning one
ZCTA in one planning channel also fail.  No tolerance: every detached piece fails, and each is
listed with its ZIP count, its mass over τ_c and its cause.
A run without a polygon graph, or with one that carries no border lengths, leaves M1
`unverified`, never `pass`.  `check_contiguity` still
lists pieces on the run's declared (Voronoi) graph.

`python -m td.audit catalog` scores the tagged catalog (`archive/pre-support-2026-09`,
`scenarios.csv`) once, for `docs/RESULTS.md` (S22).  Its contiguity runs on the OD2 graph built
over the catalog's own ZIPs, since the tag does not ship the graph it was drawn on.
"""
from __future__ import annotations

import collections
import math
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field, replace
from typing import NamedTuple

from td import geo

MODES = ("whole", "clipped", "free")
PSEUDO = frozenset({"other", "unserved", "unassigned", "none"})   # owners that are not districts
SHARE_TOL = 1e-9
DROPPED = "dropped: zero opportunity"   # a ledger row's reason for a blank district (MODEL §1)
NOT_PLACED = "not placed: not a vertex of the declared ZIP graph"   # the reason for a ZIP with no unit
NO_CELL = "no cell in the extract: territory at zero opportunity"   # a footprint cell the extract lacks (#116)
BAND_SLACK = 1e-9        # OD1: numerical slack at each band boundary, times τ_c
# How far a certificate's bound may sit from its objective and still count as equal, in objective
# units: EXACT_ALLOWANCE × max(1, |objective|), mixed absolute/relative as HiGHS, so float noise at
# a proved optimum still earns `exact`. Decided on #70:
# https://github.com/helios1168/td/issues/70#issuecomment-5908116656
EXACT_ALLOWANCE = 1e-9
TAG = "archive/pre-support-2026-09"
TAG_URL = f"https://github.com/helios1168/td/blob/{TAG}"


class Cell(NamedTuple):
    """One ledger row: `m` is the cell's opportunity, None when the ledger carries none."""
    zip: str
    fine: str
    channel: str
    district: str
    m: float | None = None
    rep: str = ""
    reason: str = ""                 # DROPPED for a cell of a unit or channel dropped before solving,
    #                                  NO_CELL for a cell of the footprint the extract lacks (#116)


@dataclass
class Channel:
    k: int
    lo: float | None = None      # the final tolerance on drawn mass (OD1)
    hi: float | None = None


@dataclass
class Run:
    """What the audit needs from a run.  Anything left None makes its checks `unverified`.

    `planned` and `reported` map (channel, unit, district) to a share of the unit: the master's
    planned share and the drawn share the run's diagnostics report.  `solver` maps a channel to
    {status, objective, bound, gap, mip_rel_gap}; `causes` maps (district, zip) to the realizer's
    cause for the piece holding that ZIP.
    """
    cells: list
    channels: dict
    expected: set | None = None          # every (zip, fine channel) cell of the extract
    unit_of: dict | None = None
    mode: dict | None = None             # (channel, unit) -> whole | clipped | free
    planned: dict | None = None
    reported: dict | None = None
    graph: dict | None = None            # geo.zip_graph's {"vertices", "edges"}
    causes: dict = field(default_factory=dict)
    metro_exceptions: list = field(default_factory=list)
    manifest: dict | None = None
    solver: dict | None = None
    names: dict | None = None            # district -> name
    polygon: dict | None = None          # geo.polygon_graph's {"vertices", "edges"[, "state"]} (M1)
    fine: tuple | None = None            # the scenario's fine channels F, planned_elsewhere excluded
    route: dict | None = None            # (unit, fine channel) -> the planning channel holding it


@dataclass
class Check:
    name: str
    status: str
    summary: str
    items: list = field(default_factory=list)
    counts: dict = field(default_factory=dict)


def _real(district: str) -> bool:
    return bool(district) and district.lower() not in PSEUDO


def _masses(run: Run) -> bool:
    return all(c.m is not None for c in run.cells)


def _drawn(run: Run) -> dict:
    """{(channel, unit, district): drawn share}, from the ledger alone."""
    if run.unit_of is None or not _masses(run):
        return {}
    unit_mass, held = collections.Counter(), collections.Counter()
    for c in run.cells:
        v = run.unit_of[c.zip]
        unit_mass[c.channel, v] += c.m
        held[c.channel, v, c.district] += c.m
    return {(ch, v, j): m / unit_mass[ch, v] for (ch, v, j), m in held.items() if unit_mass[ch, v] > 0}


def _unsolved(run: Run) -> set:
    """Channels whose every cell was dropped for zero opportunity: not solved, so K_c and the
    solver report do not apply (MODEL §1, §9)."""
    return {c.channel for c in run.cells} - {c.channel for c in run.cells if c.reason != DROPPED}


def _owners(run: Run, positive: bool = False) -> dict:
    """{(channel, unit): {district: set of its ZIPs there}}; with `positive`, less the cells known to
    hold no opportunity, so a zero-opportunity ZCTA the territory pass gave across a unit owns no
    share (#116); a cell of unknown mass still owns."""
    out: dict = collections.defaultdict(lambda: collections.defaultdict(set))
    for c in run.cells:
        if _real(c.district) and (not positive or c.m is None or c.m > 0):
            out[c.channel, run.unit_of[c.zip]][c.district].add(c.zip)
    return out


# ------------------------------------------------------------------------------ the checks
def _not_placed(run: Run) -> tuple:
    """(failed, listed) items for the `NOT_PLACED` cells (#89): a cell is excused, and listed, only
    when it has no owner, its ZIP no unit, and its whole ZIP no opportunity in the ledger."""
    zip_m = collections.defaultdict(float)
    for c in run.cells:
        zip_m[c.zip] += math.nan if c.m is None else c.m
    bad, listed = [], []
    for c in run.cells:
        if c.reason != NOT_PLACED:
            continue
        if c.district:
            bad.append(f"cell {c.zip}/{c.fine}: not placed but owned by {c.district}")
        elif run.unit_of is not None and c.zip in run.unit_of:
            bad.append(f"cell {c.zip}/{c.fine}: not placed but ZIP {c.zip} is in unit {run.unit_of[c.zip]}")
        elif zip_m[c.zip] != 0:
            bad.append(f"cell {c.zip}/{c.fine}: not placed, ZIP {c.zip} has opportunity {zip_m[c.zip]:.6g}")
        else:
            listed.append(f"cell {c.zip}/{c.fine} ({c.channel}): {NOT_PLACED}, ZIP has no opportunity")
    return bad, listed


def check_cells(run: Run) -> Check:
    seen = collections.Counter((c.zip, c.fine) for c in run.cells)
    items = [f"cell {z}/{f}: {n} owners" for (z, f), n in sorted(seen.items()) if n > 1]
    # a blank row is excused only in a channel dropped for zero opportunity, which has no districts
    items += [f"cell {c.zip}/{c.fine}: no owner" for c in run.cells if not c.district
              and c.reason != NOT_PLACED and (c.reason != DROPPED or c.channel in run.channels)]
    if run.unit_of is not None:
        items += [f"cell {c.zip}/{c.fine}: ZIP has no unit" for c in run.cells
                  if c.zip not in run.unit_of and c.reason != NOT_PLACED]
    bad, listed = _not_placed(run)
    items += bad
    # the owner comes from the channel realizer's ZIP (§8), so a ZIP's cells in one channel share it
    held = collections.defaultdict(set)
    for c in run.cells:
        if _real(c.district):
            held[c.zip, c.channel].add(c.district)
    items += [f"ZIP {z} in {ch}: {len(js)} owners ({', '.join(sorted(js))})"
              for (z, ch), js in sorted(held.items()) if len(js) > 1]
    if run.expected is not None:
        items += [f"cell {z}/{f}: not in the ledger" for z, f in sorted(run.expected - set(seen))]
        # a footprint cell the extract lacks is territory at zero opportunity (#116)
        territory = {(c.zip, c.fine) for c in run.cells if c.reason in (NO_CELL, DROPPED) and c.m == 0}
        items += [f"cell {z}/{f}: not expected" for z, f in sorted(set(seen) - run.expected - territory)]
    items += [f"cell {c.zip}/{c.fine}: {NO_CELL} but in the extract" for c in run.cells
              if c.reason == NO_CELL and run.expected is not None and (c.zip, c.fine) in run.expected]
    items += [f"cell {c.zip}/{c.fine}: {NO_CELL} with opportunity {c.m:.6g}" for c in run.cells
              if c.reason == NO_CELL and c.m]
    return Check("one owner per cell", "fail" if items else "listed" if listed else "pass",
                 f"{len(seen)} cells, {len(items)} with other than one owner, "
                 f"{len(listed)} not placed with no opportunity", items + listed)


def check_count(run: Run) -> Check:
    got = collections.defaultdict(set)
    for c in run.cells:
        if _real(c.district):
            got[c.channel].add(c.district)
    unsolved = _unsolved(run)
    items = [f"{ch}: {len(got[ch])} districts, K = {spec.k}"
             for ch, spec in sorted(run.channels.items()) if ch not in unsolved and len(got[ch]) != spec.k]
    items += [f"{ch}: not a declared channel" for ch in sorted(set(got) - set(run.channels))]
    return Check("district count per channel", "fail" if items else "pass",
                 f"{len(run.channels)} channels, {len(items)} off K", items)


def check_dropped(run: Run) -> Check:
    """Cells dropped for zero opportunity (MODEL §1, §9) are listed and do not fail the run.  A drop
    fails only when it is not one: the cell has an owner in a channel not solved, or its unit has
    opportunity there.  A dropped unit's cell in a solved channel is owned by the territory pass
    (#116)."""
    name = "dropped for zero opportunity"
    dropped = [c for c in run.cells if c.reason == DROPPED]
    if not dropped:
        return Check(name, "pass", "no cells dropped")
    mass = collections.Counter()
    if run.unit_of is not None and _masses(run):
        for c in run.cells:
            mass[c.channel, run.unit_of[c.zip]] += c.m
    bad = [f"cell {c.zip}/{c.fine}: dropped but owned by {c.district} in {c.channel}, not solved"
           for c in dropped if c.district and c.channel not in run.channels]
    bad += [f"cell {c.zip}/{c.fine}: dropped but {c.channel}/{run.unit_of[c.zip]} has opportunity "
            f"{mass[c.channel, run.unit_of[c.zip]]:.6g}"
            for c in dropped if mass[c.channel, (run.unit_of or {}).get(c.zip)] > 0]
    listed = [f"cell {c.zip}/{c.fine} ({c.channel}): {DROPPED}" for c in dropped]
    return Check(name, "fail" if bad else "listed", f"{len(dropped)} cells dropped, {len(bad)} not valid",
                 bad + listed)


def check_bands(run: Run) -> Check:
    name = "final bands on drawn mass"
    if not _masses(run):
        return Check(name, "unverified", "the ledger carries no opportunity")
    if any(s.lo is None or s.hi is None for s in run.channels.values()):
        return Check(name, "unverified", "no final tolerance declared (OD1)")
    mass, total = collections.Counter(), collections.Counter()
    for c in run.cells:
        total[c.channel] += c.m
        if _real(c.district):
            mass[c.channel, c.district] += c.m
    drawn = _drawn(run)
    items = []
    for (ch, j), m in sorted(mass.items()):
        spec = run.channels.get(ch)
        if spec is None:
            items.append(f"{ch}/{j}: drawn {m:.6g} in an undeclared channel, no band")
            continue
        slack = BAND_SLACK * total[ch] / spec.k     # τ_c from the ledger's own mass
        if spec.lo - slack <= m <= spec.hi + slack:
            continue
        short = sorted(v for (c2, v, j2), p in (run.planned or {}).items()
                       if c2 == ch and j2 == j and drawn.get((ch, v, j), 0.0) < p - SHARE_TOL)
        cause = f"; undrawn share of {', '.join(short)}" if short else ""
        items.append(f"{ch}/{j}: drawn {m:.6g} outside [{spec.lo:.6g}, {spec.hi:.6g}]{cause}")
    return Check(name, "fail" if items else "pass",
                 f"{len(mass)} districts, {len(items)} outside the final tolerance", items)


def check_phantom(run: Run) -> Check:
    items = [f"cell {c.zip}/{c.fine}: owned by pseudo-district {c.district!r}"
             for c in run.cells if c.district and not _real(c.district)]
    compared = 0
    if run.reported is not None and run.unit_of is not None:
        drawn, owners = _drawn(run), _owners(run)
        for (ch, v, j), share in sorted(run.reported.items()):
            compared += 1
            if not _finite(share):          # NaN fails every comparison below, so it is refused first
                items.append(f"{ch}/{v}/{j}: reports share {share!r}, not a finite number")
            elif share > SHARE_TOL and j not in owners.get((ch, v), {}):
                items.append(f"{ch}/{v}/{j}: reports share {share:.6g}, owns no ZIP there")
            elif drawn and abs(share - drawn.get((ch, v, j), 0.0)) > SHARE_TOL:
                items.append(f"{ch}/{v}/{j}: reports share {share:.6g}, "
                             f"ledger draws {drawn.get((ch, v, j), 0.0):.6g}")
    return Check("phantom shares", "fail" if items else "pass",
                 f"{compared} reported shares compared with the ledger, {len(items)} not backed", items)


def check_planned(run: Run) -> Check:
    name = "planned against drawn owners"
    if run.planned is None or run.unit_of is None or run.mode is None:
        return Check(name, "unverified", "the run reports no planned shares")
    owners = _owners(run, positive=True)
    items = [f"{ch}/{v}/{j}: planned share {p:.6g} drawn as no ZIPs (C8)"
             for (ch, v, j), p in sorted(run.planned.items())
             if p > SHARE_TOL and j not in owners.get((ch, v), {})]
    planned = {(ch, v, j) for (ch, v, j), p in run.planned.items() if p > SHARE_TOL}
    items += [f"{ch}/{v}/{j}: extra owner from repair in a free unit"
              for (ch, v), held in sorted(owners.items()) if run.mode.get((ch, v)) == "free"
              for j in sorted(held) if (ch, v, j) not in planned]
    return Check(name, "listed" if items else "pass", f"{len(items)} listed", items)


def check_modes(run: Run) -> Check:
    name = "mode compliance"
    if run.unit_of is None or run.mode is None:
        return Check(name, "unverified", "the run declares no units or modes")
    owners = _owners(run, positive=True)       # modes split opportunity (#116)
    reach = collections.defaultdict(set)       # (channel, district) -> units it owns ZIPs in
    for (ch, v), held in owners.items():
        for j in held:
            reach[ch, j].add(v)
    items = []
    for (ch, v), held in sorted(owners.items()):
        mode = run.mode.get((ch, v))
        if mode not in MODES:
            items.append(f"{ch}/{v}: mode {mode!r} not in {MODES}")
        elif mode == "whole" and len(held) > 1:
            items.append(f"{ch}/{v}: whole unit with {len(held)} owners ({', '.join(sorted(held))})")
        elif mode == "clipped" and len(held) > 1:
            items += [f"{ch}/{v}/{j}: owner outside the clipped unit, also in "
                      f"{', '.join(sorted(reach[ch, j] - {v}))} (C16)"
                      for j in sorted(held) if reach[ch, j] != {v}]
    listed = [f"metro exception (S14): {m}" for m in run.metro_exceptions]
    zero = collections.defaultdict(list)
    for (ch, v), held in sorted(_owners(run).items()):
        for j, zs in sorted(held.items()):
            if j not in owners.get((ch, v), {}):
                zero[ch, v, j] = sorted(zs - set().union(*owners.get((ch, v), {}).values()))
    across = [f"{ch}/{v}: {len(zs)} zero-opportunity ZCTAs ({', '.join(zs[:3])}"
              f"{', ...' if len(zs) > 3 else ''}) owned by {j}, which holds no opportunity there"
              for (ch, v, j), zs in sorted(zero.items()) if zs]
    status = "fail" if items else "listed" if listed or across else "pass"
    return Check(name, status, f"{len(items)} violations, {len(listed)} metro exceptions, "
                 f"{len(across)} units with zero-opportunity ZCTAs owned across them",
                 items + listed + across)


def check_contiguity(run: Run) -> Check:
    name = "ZIP contiguity"
    if run.graph is None:
        return Check(name, "unverified", "no declared graph")
    import networkx as nx
    g = nx.Graph()
    vertices = set(run.graph["vertices"])     # explicit (trap 21): an edge adds no vertex
    g.add_nodes_from(vertices)
    g.add_edges_from((a, b) for a, b, *_ in run.graph["edges"] if a in vertices and b in vertices)
    weigh = _masses(run)
    held = collections.defaultdict(lambda: collections.Counter())
    for c in run.cells:
        if _real(c.district):
            held[c.channel, c.district][c.zip] += c.m if weigh else 0.0
    items, split, pieces, gaps = [], 0, 0, 0
    for (ch, j), zips in sorted(held.items()):
        size = (lambda s: sum(zips[z] for z in s)) if weigh else len
        total = size(set(zips)) or 1
        outside = sorted(z for z in zips if z not in g)
        gaps += len(outside)
        items += [f"{ch}/{j}: ZIP {z} not in the graph (graph gap)" for z in outside]
        comps = sorted(nx.connected_components(g.subgraph(z for z in zips if z in g)),
                       key=lambda s: (-size(s), min(s)))
        if len(comps) > 1:
            split += 1
            pieces += len(comps) - 1
        for comp in comps[1:]:
            cause = next((run.causes[j, z] for z in sorted(comp) if (j, z) in run.causes), "unreported")
            items.append(f"{ch}/{j}: piece of {len(comp)} ZIPs, {size(comp) / total:.3g} of the "
                         f"district's {'mass' if weigh else 'ZIPs'}, cause {cause}")
    return Check(name, "listed" if items else "pass",
                 f"{split} districts in pieces, {pieces} pieces, {gaps} ZIPs not in the graph", items,
                 {"split": split, "pieces": pieces, "gaps": gaps})


M1_CHECK = "M1 polygon contiguity"
M1_ISLAND = "no approved connector"            # the piece lies in another component of the graph
M1_UNOWNED = "ZCTAs with no owner between"      # it joins the main piece only through unowned ZCTAs
M1_CUT = "cut off by other districts"


def adjacency(graph: dict) -> dict:
    """{vertex: set of neighbours} over the graph's explicit vertices (trap 21)."""
    adj = {z: set() for z in graph["vertices"]}
    for a, b, *_ in graph["edges"]:
        if a in adj and b in adj:
            adj[a].add(b)
            adj[b].add(a)
    return adj


def _components(zips: set, adj: dict) -> list:
    out, seen = [], set()
    for z in sorted(zips):
        if z in seen:
            continue
        comp, stack = {z}, [z]
        seen.add(z)
        while stack:
            for w in adj.get(stack.pop(), ()):
                if w in zips and w not in seen:
                    seen.add(w)
                    comp.add(w)
                    stack.append(w)
        out.append(comp)
    return out


def _reach(start: set, allowed: set, adj: dict) -> set:
    """The vertices of `allowed` reachable from `start` through `allowed`."""
    seen, stack = set(start), list(start)
    while stack:
        for w in adj.get(stack.pop(), ()):
            if w in allowed and w not in seen:
                seen.add(w)
                stack.append(w)
    return seen


def district_pieces(owner: dict, adj: dict, mass: dict) -> dict:
    """{district: [components of its ZIPs on `adj`]}, the main piece first: heaviest by `mass`
    ({zip: m}, missing = 0), then most ZIPs, then smallest ZIP.  `owner` is {zip: district} in one
    channel; a ZIP that is not a vertex of `adj` is its own component."""
    held = collections.defaultdict(set)
    for z, j in owner.items():
        held[j].add(z)
    return {j: sorted(_components(zs, adj),
                      key=lambda c: (-math.fsum(mass.get(z, 0.0) for z in c), -len(c), min(c)))
            for j, zs in sorted(held.items())}


# ------------------------------------------------------------------------------ M1's necks (#121)
NECK_W_KM = 10.0        # owner, 2026-10-05 (#121): a passage narrower than this is a neck; never tuned
NECK_SHARE = 0.05       # owner: a part holding this share of the district's land area
NECK_TIME = 60.0        # seconds per district component; past it the district is listed unresolved
NECK_TOL = 1e-9         # relative slack of the width and share comparisons, against float noise


class Neck(NamedTuple):
    """One neck of a district: `zips`, the side cut off (the side without the district's heaviest
    part that no narrow cut divides);
    `area` and `mass`, that side's shares of the district's land area and mass; `cut`, the cut's
    edges (a, b, km), a "land would do" connector at 0 km; `status` `proved` (a set meeting the
    definition) or `unresolved` (the search stopped without proof either way: listed, and failed)."""
    width_km: float
    zips: tuple
    area: float
    mass: float
    cut: tuple
    status: str = "proved"


class NeckGraph:
    """The polygon graph as the neck check reads it: `border` {zip: {zip: km}} over the polygon
    edges, `connector` {zip: set of zips} over the approved connectors, `aland` {zip: m²} and
    `state`.  `polygon` is `geo.polygon_graph`'s dict, which carries "border", "connectors" and
    "aland" since #121.  An edge of the graph that is neither a bordered polygon edge nor a
    connector counts as a polygon edge 0 km wide."""

    def __init__(self, polygon: dict):
        self.state = polygon.get("state", {})
        self.aland = polygon["aland"]
        border = {tuple(sorted(e)): m for e, m in polygon["border"].items()}
        joins = {tuple(sorted(e)) for e in polygon["connectors"]}
        self.border = collections.defaultdict(dict)
        self.connector = collections.defaultdict(set)
        for a, b, *_ in polygon["edges"]:
            e = tuple(sorted((a, b)))
            if e in joins:
                self.connector[a].add(b)
                self.connector[b].add(a)
            if e in border or e not in joins:
                self.border[a][b] = self.border[b][a] = border.get(e, 0.0) / 1000.0
        self.by_state = collections.defaultdict(set)
        for z in polygon["vertices"]:
            self.by_state[self.state.get(z, "")].add(z)
        self._land = {}
        self._flow_net = {}
        self._wide = {}

    def land_component(self, states: frozenset) -> dict:
        """{zip: component id} of the ZCTAs of `states` on the polygon edges alone (no connector)."""
        if states not in self._land:
            inside = set().union(*(self.by_state.get(s, set()) for s in states))
            comp = {}
            for i, c in enumerate(_components(inside, self.border)):
                comp.update(dict.fromkeys(c, i))
            self._land[states] = comp
        return self._land[states]

    def land_flow_net(self, states: frozenset) -> tuple:
        """({zip: index}, rows, cols, km) of the polygon edges (no connector) among the ZCTAs of
        `states`, each edge in both directions."""
        if states not in self._flow_net:
            comp = self.land_component(states)
            idx = {z: i for i, z in enumerate(sorted(comp))}
            rows, cols, km = [], [], []
            for z, i in idx.items():
                for y, k in self.border.get(z, {}).items():
                    if y in idx:
                        rows.append(i)
                        cols.append(idx[y])
                        km.append(k)
            self._flow_net[states] = idx, rows, cols, km
        return self._flow_net[states]

    def land_would_do(self, a: str, b: str, states: frozenset) -> bool:
        """A connector a-b is a neck of width 0 when land would do: its sides are joined in the
        polygon graph without connectors, within `states`, the states the district owns ZCTAs in,
        through a passage itself at least `NECK_W_KM` wide, the max flow between a and b with each
        edge's shared border as its capacity (owner, 2026-10-05, "No, unless land would do", then
        "Land must be a real passage").  A narrower land route leaves the connector at full width.

        Exact: the flow runs on whole millimetres, each border rounded up, so a flow under the
        limit proves the land narrow; each edge and the source are capped at the limit, which keeps
        whether the flow reaches it.  A flow at the limit makes the connector width 0, the true
        flow being at most a millimetre per cut edge less: the check may over-report a neck but
        never misses one."""
        key = (states, *sorted((a, b)))
        if key in self._wide:
            return self._wide[key]
        comp = self.land_component(states)
        wide = False
        if a in comp and comp.get(a) == comp.get(b):
            import numpy as np
            import scipy.sparse as sp
            from scipy.sparse.csgraph import maximum_flow
            idx, rows, cols, km = self.land_flow_net(states)
            n, lim_mm = len(idx), NECK_W_KM * 1e6 * (1 - NECK_TOL)
            cap_mm = math.ceil(lim_mm)                      # int32 holds it, and every flow under it

            cap = [min(math.ceil(k * 1e6), cap_mm) for k in km] + [cap_mm]
            net = sp.csr_matrix((np.array(cap, dtype=np.int32),
                                 (np.array(rows + [n], dtype=np.int32),
                                  np.array(cols + [idx[a]], dtype=np.int32))), shape=(n + 1, n + 1))
            wide = int(maximum_flow(net, n, idx[b]).flow_value) >= lim_mm
        self._wide[key] = wide
        return wide


def district_necks(zips: set, mass: dict, g: NeckGraph, time_limit: float = NECK_TIME,
                   by: str = "area") -> list:
    """[Neck] of one district (`zips`, `mass` {zip: m}): at most one per component of the district,
    the narrowest.  M1's neck (owner, 2026-10-05, #121, structured picks "Area only" and "One
    connected piece"): a connected part A of the district holding at least `NECK_SHARE` of its land
    area (`aland`) that reaches the rest only through a passage under `NECK_W_KM`, the total shared
    border across the cut.  The rest must hold `NECK_SHARE` too, each of its pieces: else the heavy
    body of a district with a small fringe on a narrow border would itself be a part cut off, and
    two small fringes would combine.  That is the same as the rest being one connected part
    holding `NECK_SHARE` (a light piece of the rest can join A, which stays connected, and the cut
    only narrows; a heavy one alone is a rest), so both sides are connected here.  A polygon edge
    is as wide as its border; an approved connector is unlimited, unless its two sides are joined
    by land within the district's states, where it is 0 km wide.  With `by="mass"` the shares are
    of the district's mass: the owner's diagnostic list, not M1.

    **Exact**, to HiGHS's tolerances: two ZCTAs no cut under `NECK_W_KM` can separate are merged
    first (an edge, or an edge plus its two-edge paths, at least `NECK_W_KM` wide, or a needed
    connector), which keeps every narrow cut; the heaviest merged vertex Q is then on one side of
    every narrow cut, and as the definition is symmetric, naming that side the rest loses nothing;
    if less than the share lies outside Q, no neck exists.  Otherwise a MILP finds the narrowest cut
    with both sides holding the share (`mip_rel_gap = 0`, trap 12), stopping once its bound
    proves no cut is under `NECK_W_KM`; when its sides are not both connected, a second MILP adds a
    single-commodity flow on each side (from Q, and from a chosen root of A) and finds the
    narrowest cut with both sides connected.  A component a MILP cannot settle in `time_limit`
    seconds is listed as an `unresolved` neck, so the check may over-report but never misses a
    neck.  The MILPs leave `threads` at the process's own count (trap 18)."""
    import highspy
    import numpy as np
    states = frozenset(g.state.get(z, "") for z in zips)
    weight = g.aland if by == "area" else mass
    area_tot = math.fsum(g.aland.get(z, 0.0) for z in zips)
    mass_tot = math.fsum(mass.get(z, 0.0) for z in zips)
    w_tot = area_tot if by == "area" else mass_tot
    need = NECK_SHARE * w_tot * (1 - NECK_TOL)
    w_lim = NECK_W_KM * (1 - NECK_TOL)
    width = {}                                  # (a, b) with a < b -> km (inf: a needed connector)
    for z in zips:
        for y, km in g.border.get(z, {}).items():
            if y in zips and z < y:
                width[z, y] = km
        for y in g.connector.get(z, ()):
            if y in zips and z < y:
                width[z, y] = width.get((z, y), 0.0) + (0.0 if g.land_would_do(z, y, states) else math.inf)
    adj = collections.defaultdict(set)
    for a, b in width:
        adj[a].add(b)
        adj[b].add(a)

    def share(side, of):
        tot = area_tot if of is g.aland else mass_tot
        return math.fsum(of.get(z, 0.0) for z in side) / tot if tot > 0 else 1.0

    def qualifies(side):
        return math.fsum(weight.get(z, 0.0) for z in side) >= need
    out = []
    for comp in _components(set(zips), adj):
        if len(comp) < 2:
            continue
        parent = {z: z for z in comp}

        def find(z):
            while parent[z] != z:
                parent[z] = parent[parent[z]]
                z = parent[z]
            return z
        while True:                             # merge what no narrow cut separates
            agg = collections.defaultdict(float)
            for (a, b), km in width.items():
                if a in parent:
                    ra, rb = find(a), find(b)
                    if ra != rb:
                        agg[min(ra, rb), max(ra, rb)] += km
            nb = collections.defaultdict(dict)
            for (a, b), km in agg.items():
                nb[a][b] = nb[b][a] = km
            merged = False
            for (a, b), km in sorted(agg.items()):
                ra, rb = find(a), find(b)
                if ra == rb:
                    continue
                if km < NECK_W_KM:
                    km += math.fsum(min(k, nb[b].get(x, 0.0)) for x, k in nb[a].items() if x != b)
                if km >= NECK_W_KM:
                    parent[ra] = rb
                    merged = True
            if not merged:
                break
        group = collections.defaultdict(list)
        for z in sorted(comp):
            group[find(z)].append(z)
        gs = sorted(group)
        g_w = {r: math.fsum(weight.get(z, 0.0) for z in group[r]) for r in gs}
        core = max(gs, key=lambda r: g_w[r])    # ties: the first
        if not qualifies([z for r in gs if r != core for z in group[r]]):
            continue                            # nothing outside the core can hold the share
        order = [core] + [r for r in gs if r != core]
        ix = {r: i for i, r in enumerate(order)}
        n = len(order)
        edges, links = collections.defaultdict(float), set()
        for (a, b), km in width.items():
            if a in parent and find(a) != find(b):
                e = tuple(sorted((ix[find(a)], ix[find(b)])))
                links.add(e)
                if km > 0:
                    edges[e] += km
        el = sorted(edges.items())
        wv = [g_w[r] for r in order]
        w_comp = math.fsum(wv)

        def solve(connected: bool):
            """(status, info, side or None) of the narrowest cut, sides connected when asked."""
            inf = highspy.kHighsInf
            h = highspy.Highs()
            h.setOptionValue("output_flag", False)
            h.setOptionValue("mip_rel_gap", 0.0)
            h.setOptionValue("time_limit", float(time_limit))
            h.setOptionValue("objective_bound", NECK_W_KM)
            arcs = [(i, j) for i, j in sorted(links)] + [(j, i) for i, j in sorted(links)]
            nf = len(arcs) if connected else 0
            # columns: x (n), y (edges), then with `connected`: r (n), supply (n), f_R, f_A (arcs)
            x0, y0 = 0, n
            r0, s0, fr0 = n + len(el), n + len(el) + n, n + len(el) + 2 * n
            fa0 = fr0 + nf
            nv = n + len(el) + (2 * n + 2 * nf if connected else 0)
            lower, upper = np.zeros(nv), np.ones(nv)
            upper[0] = 0.0                      # the core is in the rest
            upper[y0:y0 + len(el)] = inf
            if connected:
                upper[r0] = 0.0
                upper[s0:s0 + n] = n
                upper[fr0:fa0 + nf] = n
            cost = np.zeros(nv)
            cost[y0:y0 + len(el)] = [km for _, km in el]
            h.addVars(nv, lower, upper)
            h.changeColsCost(nv, np.arange(nv, dtype=np.int32), cost)
            ints = list(range(n)) + (list(range(r0, r0 + n)) if connected else [])
            h.changeColsIntegrality(len(ints), np.array(ints, dtype=np.int32),
                                    np.array([highspy.HighsVarType.kInteger] * len(ints)))

            def row(lo, hi, idx, val):
                h.addRow(lo, hi, len(idx), np.array(idx, dtype=np.int32), np.array(val, dtype=float))
            for k, ((i, j), _) in enumerate(el):    # y_e >= |x_i - x_j|
                row(0.0, inf, [y0 + k, i, j], [1.0, -1.0, 1.0])
                row(0.0, inf, [y0 + k, i, j], [1.0, 1.0, -1.0])
            row(need, inf, list(range(n)), wv)                      # A holds the share
            row(-inf, w_comp - need, list(range(n)), wv)            # and so does the rest
            row(1.0, inf, list(range(1, n)), [1.0] * (n - 1))       # A is not empty
            if connected:
                row(1.0, 1.0, list(range(r0, r0 + n)), [1.0] * n)   # one root of A
                into = collections.defaultdict(list)
                for a, (u, v) in enumerate(arcs):
                    into[v].append(a)
                    for f0, side in ((fr0, -1.0), (fa0, 1.0)):
                        # an arc carries flow only inside its side: f <= n x (A), f <= n (1 - x) (rest)
                        for w_ in (u, v):
                            if side > 0:
                                row(-inf, 0.0, [f0 + a, x0 + w_], [1.0, -float(n)])
                            else:
                                row(-inf, float(n), [f0 + a, x0 + w_], [1.0, float(n)])
                outs = collections.defaultdict(list)
                for a, (u, v) in enumerate(arcs):
                    outs[u].append(a)
                for v in range(n):
                    io = [fr0 + a for a in into[v]] + [fr0 + a for a in outs[v]]
                    vals = [1.0] * len(into[v]) + [-1.0] * len(outs[v])
                    if v != 0:                  # each rest vertex but the core takes one unit
                        row(1.0, 1.0, io + [x0 + v], vals + [1.0])
                    ia = [fa0 + a for a in into[v]] + [fa0 + a for a in outs[v]]
                    row(0.0, 0.0, ia + [x0 + v, s0 + v], vals + [-1.0, 1.0])   # A: one unit each
                    row(-inf, 0.0, [s0 + v, r0 + v], [1.0, -float(n)])        # supply at its root
                    row(-inf, 0.0, [r0 + v, x0 + v], [1.0, -1.0])            # the root is in A
            h.run()
            info, st = h.getInfo(), h.getModelStatus()
            side = None
            if info.primal_solution_status == 2:
                xs = h.getSolution().col_value
                side = sorted(z for r, i in ix.items() if xs[i] > 0.5 for z in group[r])
            return st, info, side

        def judge(side):
            """(width, cut) of `side` when it and the rest of the component are each connected and
            hold the share, else None."""
            inside = set(side)
            rest = set(comp) - inside
            if not side or not rest or not qualifies(inside) or not qualifies(rest):
                return None
            if len(_components(inside, adj)) != 1 or len(_components(rest, adj)) != 1:
                return None
            cut = tuple(sorted((a, b, km) for (a, b), km in width.items()
                               if a in parent and (a in inside) != (b in inside)))
            return math.fsum(km for _, _, km in cut), cut
        settled = (highspy.HighsModelStatus.kInfeasible, highspy.HighsModelStatus.kObjectiveBound)
        found = None
        for connected in (False, True):
            st, info, side = solve(connected)
            got = judge(side) if side else None
            wkm = math.inf
            if side:
                inside = set(side)
                wkm = math.fsum(km for (a, b), km in width.items()
                                if a in parent and (a in inside) != (b in inside))
            if got is not None and got[0] < w_lim:
                found = Neck(got[0], tuple(side), share(side, g.aland), share(side, mass), got[1])
                break
            if st in settled or (st == highspy.HighsModelStatus.kOptimal and wkm >= w_lim):
                break                           # proved: no cut under NECK_W_KM (of this model)
            if connected or st != highspy.HighsModelStatus.kOptimal:
                found = Neck(min(wkm, info.mip_dual_bound), tuple(side or ()),
                             share(side or (), g.aland), share(side or (), mass), (), "unresolved")
                break
            # the narrowest cut has a side in pieces: solve again with both sides connected
        if found is not None:
            out.append(found)
    return out


MASS_NECK = "mass neck (diagnostic, not M1)"   # the owner's list for a later decision (#121)


def neck_item(ch: str, j: str, nk: Neck, kind: str = "neck") -> str:
    """One item for a neck: M1's (`kind` "neck"), or a `MASS_NECK` the check lists beside M1."""
    if nk.status != "proved":
        return (f"{ch}/{j}: {kind} unresolved (the search stopped at bound {nk.width_km:.3g} km, "
                f"under {NECK_W_KM:g} km): listed as a {kind}")
    cut = ", ".join(f"{a}-{b} {km:.2f} km" for a, b, km in nk.cut[:6]) + (", ..." if len(nk.cut) > 6 else "")
    return (f"{ch}/{j}: {kind} {nk.width_km:.2f} km wide cuts off {len(nk.zips)} ZIPs ({nk.zips[0]}...), "
            f"{nk.area:.1%} of its land area and {nk.mass:.1%} of its mass; cut {cut}")


def check_m1(run: Run) -> Check:
    """M1 (module doc): one connected piece per district on the polygon graph, no neck
    (`district_necks`), and every (ZCTA, fine channel) cell of the scenario owned exactly once, in
    the planning channel holding it.  A polygon graph without border lengths leaves the necks, and
    so M1, unverified."""
    name = M1_CHECK
    if run.polygon is None:
        return Check(name, "unverified", "no polygon graph: M1 is not checked")
    adj = adjacency(run.polygon)
    state = run.polygon.get("state", {})
    weigh = _masses(run)
    owner, mass, total = collections.defaultdict(dict), collections.defaultdict(dict), collections.Counter()
    at = collections.defaultdict(list)                  # (zip, fine channel) -> its rows
    clash = collections.defaultdict(set)                # (channel, zip) -> its districts
    items = []
    for c in run.cells:
        if weigh:
            total[c.channel] += c.m
        if c.fine:
            at[c.zip, c.fine].append(c)
        else:
            items.append(f"{c.channel}: a row of ZIP {c.zip} has no fine channel")
        if _real(c.district):
            j = owner[c.channel].setdefault(c.zip, c.district)
            if j != c.district:
                clash[c.channel, c.zip] |= {j, c.district}
            mass[c.channel][c.zip] = mass[c.channel].get(c.zip, 0.0) + (c.m if weigh else 0.0)
    if run.fine is not None or run.route is not None:
        fine, source = sorted(run.fine if run.fine is not None else {f for _, f in run.route}), ""
    else:
        fine, source = sorted({f for z, f in at if z in adj}), " (fine channels from the ledger)"
    items += [f"fine channel {f}: has rows but is not a fine channel of the scenario"
              for f in sorted({f for _, f in at} - set(fine)) if not source]
    items += [f"{ch}: ZCTA {z} owned by {', '.join(sorted(js))}" for (ch, z), js in sorted(clash.items())]
    foot, free, missing = (collections.defaultdict(set) for _ in range(3))
    n_double, dup, unexcused = 0, set(), []
    for z in sorted(adj):
        for f in fine:
            rows = at.get((z, f), [])
            want = None if run.route is None else run.route.get(((run.unit_of or {}).get(z), f))
            if want is not None:
                items += [f"fine channel {f}: ZCTA {z} has a row in {ch}, held by {want}"
                          for ch in sorted({c.channel for c in rows} - {want})]
            elif run.route is not None:
                items.append(f"fine channel {f}: ZCTA {z} is in no planning channel of the scenario")
            solved = ({want} if want else {c.channel for c in rows}) & set(run.channels)
            for ch in solved:
                foot[ch].add(z)
            if not rows:
                missing[f].add(z)
                continue
            owned = sorted(c.channel for c in rows if _real(c.district))
            if len(owned) > 1:
                n_double += 1
                dup |= {(ch, z) for ch in owned}
                items.append(f"fine channel {f}: ZCTA {z} owned in {', '.join(owned)}")
            if not owned:                   # a blank row is excused in a dropped channel only
                for ch in solved:
                    free[ch].add(z)
                if not solved and not any(c.channel not in run.channels and c.reason == DROPPED
                                          and c.m == 0.0 for c in rows):
                    unexcused.append((f, z))
                    items.append(f"fine channel {f}: ZCTA {z} has no owner, and no zero-opportunity "
                                 "DROPPED row of a dropped channel excuses it")
    n_double += sum(1 for k in clash if k not in dup)  # a clash across fine channels, not one cell's
    whole = {}
    for i, comp in enumerate(_components(set(adj), adj)):
        whole.update(dict.fromkeys(comp, i))
    uncovered, n_pieces, split, largest, n_free = [], 0, 0, 0.0, 0
    ng = NeckGraph(run.polygon) if {"border", "connectors", "aland"} <= set(run.polygon) else None
    neck_items, mass_items, vertices = [], [], set(adj)
    for ch in sorted(set(run.channels) | set(owner)):
        spec = run.channels.get(ch)
        tau = total[ch] / spec.k if weigh and spec and spec.k and total[ch] > 0 else None
        items += [f"{ch}: ZIP {z} of {j} is not a vertex of the polygon graph"
                  for z, j in sorted(owner[ch].items()) if z not in adj]
        for j, comps in district_pieces(owner[ch], adj, mass[ch]).items():
            if ng is not None:
                zs = set().union(*comps) & vertices
                neck_items += [neck_item(ch, j, nk) for nk in district_necks(zs, mass[ch], ng)]
                if weigh:
                    mass_items += [neck_item(ch, j, nk, MASS_NECK)
                                   for nk in district_necks(zs, mass[ch], ng, by="mass")]
            if len(comps) < 2:
                continue
            split += 1
            n_pieces += len(comps) - 1
            main = _reach(comps[0], set().union(*comps) | free[ch], adj)
            for comp in comps[1:]:
                m = math.fsum(mass[ch].get(z, 0.0) for z in comp)
                share = f"{m / tau:.3g} τ" if tau else "mass not in the ledger"
                largest = max(largest, m / tau if tau else 0.0)
                z0 = min(comp)
                if whole.get(z0) != whole.get(min(comps[0])):
                    cause = M1_ISLAND
                else:
                    cause = next((run.causes[j, z] for z in sorted(comp) if (j, z) in run.causes),
                                 M1_UNOWNED if z0 in main else M1_CUT)
                items.append(f"{ch}/{j}: detached piece of {len(comp)} ZIPs ({z0}...), {share}, "
                             f"cause {cause}")
        if free[ch] and ch in run.channels:
            n_free += len(free[ch])
            items.append(f"{ch}: {len(free[ch])} of {len(foot[ch])} ZCTAs have no owner")
            by_state = collections.Counter(state.get(z, "?") for z in free[ch])
            uncovered += [f"{ch}: {n} ZCTAs of {s} have no owner" for s, n in sorted(by_state.items())]
    n_norow = sum(len(zs) for zs in missing.values())
    n_free += len(unexcused)
    for f in sorted(missing):
        items.append(f"fine channel {f}: {len(missing[f])} of {len(adj)} CONUS ZCTAs have no row")
        by_state = collections.Counter(state.get(z, "?") for z in missing[f])
        uncovered += [f"fine channel {f}: {n} ZCTAs of {s} have no row" for s, n in sorted(by_state.items())]
    items += neck_items
    necks = f"{len(neck_items)} necks" if ng is not None else "necks not checked (no border lengths)"
    status = "fail" if items else "pass" if ng is not None else "unverified"
    return Check(name, status,
                 f"{split} districts in pieces, {n_pieces} detached pieces (largest {largest:.3g} τ), "
                 f"{necks}, {n_free} channel ZCTAs with no owner, {n_norow} (ZCTA, fine channel) "
                 f"cells with no row, {n_double} owned twice, {len(mass_items)} mass necks listed "
                 f"beside M1{source}", items + uncovered + mass_items,
                 {"split": split, "pieces": n_pieces, "largest_tau": largest, "no_owner": n_free,
                  "no_row": n_norow, "double": n_double,
                  "necks": len(neck_items) if ng is not None else None,
                  "mass_necks": len(mass_items) if ng is not None else None})


def check_geography(run: Run) -> Check:
    name = "geography manifest is 2025"
    if run.manifest is None:
        return Check(name, "unverified", "no manifest")
    try:
        geo.check_manifest(run.manifest)
    except ValueError as e:
        return Check(name, "fail", "not all 2025 (S17)", [str(e)])
    return Check(name, "pass", f"{len(run.manifest['sources'])} sources, all 2025")


def _finite(x) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


def allowance(obj: float) -> float:
    """EXACT_ALLOWANCE × max(1, |objective|): the distance, in objective units, at which a bound
    still counts as equal to the objective (#70)."""
    return EXACT_ALLOWANCE * max(1.0, abs(obj))


def actual_gap(obj: float, bound: float) -> float:
    """The relative gap of a minimisation, (objective - bound) / |objective|, as HiGHS reports it."""
    if obj == bound:
        return 0.0
    return (obj - bound) / abs(obj) if obj != 0 else math.inf


def solver_problems(report: dict) -> list:
    """Why a report with an incumbent cannot back a tier: an objective or bound that is not a
    finite number, a bound above the incumbent, or a reported gap the objective and bound do not
    give.  A report with no bound claims no optimality, so it needs no gap."""
    obj, bound, gap = report.get("objective"), report.get("bound"), report.get("gap")
    if not _finite(obj):
        return [f"objective {obj!r} is not a finite number"]
    if bound is None:
        return [] if gap is None else [f"gap {gap!r} reported without a bound"]
    if not _finite(bound):
        return [f"bound {bound!r} is not a finite number"]
    if bound - obj > allowance(obj):
        return [f"bound {bound!r} above the incumbent {obj!r}"]
    if gap is not None and not _gap_agrees(gap, obj, min(bound, obj)):
        return [f"reported gap {gap!r}, objective and bound give {actual_gap(obj, min(bound, obj)):.6g}"]
    return []


def _gap_agrees(gap, obj: float, bound: float) -> bool:
    """A reported gap agrees when it is the actual gap, or when the bound it implies,
    objective − gap × |objective|, lies within the allowance of `bound`.  At a zero objective a
    gap implies no bound, so only the actual gap, or 0 with the bound within the allowance, agrees."""
    if not isinstance(gap, (int, float)) or isinstance(gap, bool):
        return False
    if gap == actual_gap(obj, bound):
        return True
    if not math.isfinite(gap):
        return False
    if obj == 0:
        return gap == 0 and obj - bound <= allowance(obj)
    return abs(obj - bound - gap * abs(obj)) <= allowance(obj)


def tier(report: dict) -> str:
    """OD3 (#58): exact, bounded or feasible only; `none` without an incumbent, and `invalid`
    when the report cannot back a tier (`solver_problems`).  Exact needs a proven optimum at
    `mip_rel_gap=0`, a reported gap of 0, and a bound within `allowance(objective)` =
    EXACT_ALLOWANCE × max(1, |objective|) of the objective."""
    obj, bound = report.get("objective"), report.get("bound")
    if obj is None:
        return "none"
    if solver_problems(report):
        return "invalid"
    if bound is None:
        return "feasible only"
    if (report.get("status") == "optimal" and report.get("mip_rel_gap") == 0
            and report.get("gap") == 0 and obj - min(bound, obj) <= allowance(obj)):
        return "exact"
    return "bounded"


def _shown_gap(report: dict) -> str:
    """The gap a solver row prints: the actual gap of a report that backs a tier, None without a
    bound, and the report's own value when it backs none."""
    obj, bound = report.get("objective"), report.get("bound")
    if tier(report) in ("invalid", "none"):
        return f"{report.get('gap')}"
    if bound is None:
        return "None"
    return f"{actual_gap(obj, min(bound, obj)):.6g}"


def check_solver(run: Run) -> list:
    if run.solver is None:
        return [Check("solver status, bound and gap", "unverified", "no solver report"),
                Check("certificate tier", "unverified", "no solver report")]
    rows = [f"{ch}: status {r.get('status')}, objective {r.get('objective')}, bound {r.get('bound')}, "
            f"gap {_shown_gap(r)}, tier {tier(r)}" for ch, r in sorted(run.solver.items())]
    tiers = {ch: tier(r) for ch, r in run.solver.items()}
    missing = sorted(set(run.channels) - set(run.solver) - _unsolved(run))
    bad = [f"{ch}: no incumbent" for ch, t in sorted(tiers.items()) if t == "none"]
    bad += [f"{ch}: invalid report, {why}" for ch, r in sorted(run.solver.items())
            if tiers[ch] == "invalid" for why in solver_problems(r)]
    bad += [f"{ch}: no solver report" for ch in missing]
    order = ["exact", "bounded", "feasible only", "invalid"]
    worst = max((t for t in tiers.values() if t in order), key=order.index, default="none")
    return [Check("solver status, bound and gap", "fail" if bad else "listed",
                  f"{len(rows)} channels", bad + rows),
            Check("certificate tier", "fail" if bad else "pass", f"weakest tier: {worst}",
                  [f"{ch}: {t}" for ch, t in sorted(tiers.items())])]


def check_names(run: Run) -> Check:
    name = "one name per district"
    if run.names is None:
        return Check(name, "unverified", "no district names")
    districts = sorted({c.district for c in run.cells if _real(c.district)})
    items = [f"{j}: no name" for j in districts if not run.names.get(j)]
    by_name = collections.defaultdict(list)
    for j in districts:
        if run.names.get(j):
            by_name[run.names[j]].append(j)
    items += [f"{n!r} names {', '.join(js)}" for n, js in sorted(by_name.items()) if len(js) > 1]
    return Check(name, "fail" if items else "pass", f"{len(districts)} districts", items)


def check_reps(run: Run) -> Check:
    labels = collections.defaultdict(set)
    for c in run.cells:
        if c.rep:
            labels[c.channel, c.district].add(c.rep)
    if not labels:
        return Check("rep labels", "pass", "blank, as OD3 (#58) decides")
    items = [f"{ch}/{j}: {len(r)} rep labels" for (ch, j), r in sorted(labels.items()) if len(r) > 1]
    return Check("rep labels", "fail" if items else "pass",
                 f"{len(items)} districts with conflicting rep labels", items)


def audit(run: Run) -> list:
    """Every §9 check on `run`, in the scorecard's order.  A ledger cell whose ZIP has no unit fails
    `check_cells`, unless it is a `NOT_PLACED` cell of a ZIP with no opportunity, which it lists;
    the other checks run without it, so the scorecard still completes."""
    mapped = run
    if run.unit_of is not None and any(c.zip not in run.unit_of for c in run.cells):
        mapped = replace(run, cells=[c for c in run.cells if c.zip in run.unit_of])
    return [check_cells(run), check_count(mapped), check_dropped(mapped), check_bands(mapped),
            check_phantom(mapped), check_planned(mapped), check_modes(mapped), check_contiguity(mapped),
            check_m1(run), check_geography(mapped), *check_solver(mapped), check_names(mapped), check_reps(mapped)]


def verdict(checks: list) -> str:
    return "fail" if any(c.status == "fail" for c in checks) else "pass"


def scorecard(checks: list, title: str) -> str:
    lines = [f"# Scorecard: {title}", "", f"**Verdict: {verdict(checks)}**", "",
             "| check | status | summary |", "|---|---|---|"]
    lines += [f"| {c.name} | {c.status} | {c.summary} |" for c in checks]
    for c in checks:
        if c.items:
            lines += ["", f"## {c.name}", ""] + [f"- {i}" for i in c.items]    # every item (§9)
    return "\n".join(lines) + "\n"


def write_scorecard(run_dir: str, checks: list, title: str) -> str:
    path = os.path.join(run_dir, "scorecard.md")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(scorecard(checks, title))
    return path


# ------------------------------------------------------------------------------ the tagged catalog
LAYERS = {"n": "N", "wh": "WH", "fi": "FI", "wifi": "WHFI"}


def catalog_k(scenario: str) -> dict:
    """{layer: K} from a catalog scenario name such as `51_total_13n_11wh_24fi_3wifi`."""
    got = {LAYERS[k]: int(n) for n, k in re.findall(r"_(\d+)(n|wh|fi|wifi)(?=_|$)", scenario)}
    if set(got) != set(LAYERS.values()):
        raise ValueError(f"not a catalog scenario name: {scenario!r}")
    return got


def read_catalog(path: str | None = None):
    """The tag's `scenarios.csv`, from `path` or from git."""
    import io
    import pandas as pd
    if path is None:
        raw = subprocess.run(["git", "show", f"{TAG}:scenarios.csv"], cwd=geo.ROOT,
                             capture_output=True, check=True).stdout
        path = io.BytesIO(raw)
    return pd.read_csv(path, dtype=str, keep_default_na=False)


def catalog_graph(frame, public: str = geo.PUBLIC_DIR, reference=None) -> dict:
    """The OD2 graph over the catalog's ZIPs; `excluded` lists those without a 2025 point."""
    from td import data
    ref = (geo.read_reference() if reference is None else reference).set_index("zcta")
    zips = sorted(set(frame["zip_code"]))
    placed = [z for z in zips if z in ref.index and ref.at[z, "state"]]
    points = {z: (float(ref.at[z, "x"]), float(ref.at[z, "y"])) for z in placed}
    g = geo.zip_graph(points, {z: ref.at[z, "state"] for z in placed}, data.state_polygons(public))
    g["excluded"] = sorted(set(zips) - set(placed))
    return g


def catalog_runs(frame, graph: dict | None = None):
    """(scenario, Run) for each tagged scenario.  A cell's channel is its district's layer; units
    are states.  The tag has no opportunity, plan, modes, solver report, names or manifest."""
    for scenario, rows in frame.groupby("scenario", sort=True):
        cells = [Cell(z, f, ch, j, None, r) for z, f, ch, j, r in
                 zip(rows["zip_code"], rows["current_channel"], rows["district_channels"],
                     rows["district"], rows["rep"])]
        yield scenario, Run(cells, {ch: Channel(k) for ch, k in catalog_k(scenario).items()},
                            unit_of=dict(zip(rows["zip_code"], rows["state"])), graph=graph)


def catalog_scorecard(frame, graph: dict) -> str:
    """The §9 audit of every tagged scenario, as markdown for `docs/RESULTS.md`."""
    rows, statuses = [], collections.defaultdict(collections.Counter)
    totals = collections.Counter()
    for scenario, run in catalog_runs(frame, graph):
        checks = {c.name: c for c in audit(run)}
        for c in checks.values():
            statuses[c.name][c.status] += 1
        reps = len(checks["rep labels"].items)
        split, pieces = (checks["ZIP contiguity"].counts.get(k, 0) for k in ("split", "pieces"))
        totals.update(reps=reps, split=split, pieces=pieces)
        rows.append(f"| {scenario} | {verdict(checks.values())} | {checks['one owner per cell'].status} "
                    f"| {checks['district count per channel'].status} | {reps} | {split} | {pieces} |")
    zips = frame["zip_code"].nunique()
    lines = [
        f"Scored with `td/audit.py` on the tag's [`scenarios.csv`]({TAG_URL}/scenarios.csv): "
        f"{frame['scenario'].nunique()} scenarios, {zips} ZIPs, {len(frame)} cells.",
        "",
        f"Contiguity is on the 2025 Voronoi rook graph over the catalog's ZIPs (OD2, built by "
        f"`geo.zip_graph`: {len(graph['vertices'])} vertices, {len(graph['edges'])} edges). "
        f"{len(graph['excluded'])} catalog ZIPs have no 2025 gazetteer point and are left out; "
        f"{len(graph['missing'])} lose their cell. The tag does not ship the graph it was drawn "
        "on, so these counts are not comparable with older ones.",
        "",
        "| check | " + " | ".join(("pass", "fail", "listed", "unverified")) + " |",
        "|---|---|---|---|---|",
    ]
    lines += [f"| {n} | " + " | ".join(str(s[k]) for k in ("pass", "fail", "listed", "unverified")) + " |"
              for n, s in statuses.items()]
    lines += ["", "| scenario | verdict | one owner per cell | district count | districts with "
              "conflicting rep labels | districts in pieces | pieces |", "|---|---|---|---|---|---|---|"]
    lines += rows
    lines.append(f"| **total** | | | | {totals['reps']} | {totals['split']} | {totals['pieces']} |")
    return "\n".join(lines) + "\n"


def main(argv=None) -> int:
    import argparse
    ap = argparse.ArgumentParser(prog="python -m td.audit", description=__doc__.splitlines()[0])
    ap.add_argument("command", choices=["catalog"])
    ap.add_argument("--csv", help="the tag's scenarios.csv (default: read it from git)")
    ap.add_argument("--public", default=geo.PUBLIC_DIR, help="where tl_2025_us_state.zip is")
    a = ap.parse_args(argv)
    frame = read_catalog(a.csv)
    sys.stdout.write(catalog_scorecard(frame, catalog_graph(frame, a.public)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
