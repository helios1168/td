"""atoms.py -- state atoms for stage 1: whole states, with the oversized ones cut into pieces.

Stage 1 wants k districts of roughly equal opportunity, contiguous.  Zips cannot deliver that
-- v2's zip adjacency has 862 components over 3,748 zips -- so this module pre-aggregates them
into **state atoms** and hands the result to `solvers.atom_draw`, which draws on the TIGER
state rook graph.  That graph is connected, so contiguity becomes achievable rather than
vacuous.

Only the states above the per-district target need cutting.  At k=18 on v2 the target is 473.5
and exactly five states exceed it -- CA 4.126x, TX 2.020x, NY 1.794x, FL 1.398x, NJ 1.037x --
while the largest atom needing no cut is IL at 0.677x.  A piece left above target can never
combine with anything, so it strands as an oversized district; that is the whole mechanism
behind the cost of a too-coarse cut.

NY and NJ are cut as **one pooled group**, so a cut line may cross the state border.  They are
2.831x together, and the delivered zip-level draw already fuses them.  Cutting the pair into
only two pieces severs New England: CT MA ME NH RI VT reach the network through NY alone, so
two oversized NY pieces leave them a 0.434x district.  A third piece repairs it.

This module composes `instance`, `geo` and `solvers.centers`; it is not itself a solver, which
is why it sits beside `channel.py` rather than under `solvers/`.  The search it feeds takes a
graph and a mass table and nothing else, so it can be tested with no geometry at all.

Reproducibility
---------------
`build` must be given `zips` in the instance's own node order, not sorted.  That order decides
the atom table's insertion order, which decides edge insertion order in the atom graph, which
decides `graph.neighbors` order for the whole run.  Together with `PYTHONHASHSEED=0` (see
`solvers.atom_draw`) that is what makes a draw reproduce.

Piece names are load-bearing for the same reason: the search tie-breaks on set iteration over
atom names, so renaming `CA1` changes the answer.

Open questions this module carries rather than answers
------------------------------------------------------
`geo.states_outline` keeps the lower 48 plus DC, so AK and HI have no polygon and no rook
entry.  `MERGE_LONE` folds their mass into a neighbour on the sales-territory convention that
AK is worked from the Pacific Northwest and HI from California.  Nobody has decided that; it is
the measured default, and the remaining `NON_CONUS` codes raise instead, because as isolated
graph nodes they would each silently consume a district.

Zips the instance carries no state for -- 32 of them, 33.4M, 0.4% -- belong to no atom.  They
are returned separately and `atom_draw.draw` adds their mass to the lightest district.  That is
also a placeholder: `STATE.md` still lists the rule as open.

A piece has no polygon, only its zips' points, so "does this piece touch Nevada?" is answered
by proximity: within `BORDER_TOL` of the state's polygon, plus an unconditional link from the
nearest piece so a piece is never orphaned.  Atom-graph contiguity is therefore a modelling
artefact at the cut boundaries, not verified map contiguity -- check the map.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

import networkx as nx
import numpy as np

from . import geo
from .solvers import centers

BORDER_TOL = 40_000.0        # metres: a piece touches a state if any of its zips is this close
CUT_SEED = 2                 # the `centers.draw` seed for the within-group cut
STATELESS = "??"             # sentinel for a zip the instance carries no state for

# decided 2026-09-06: the cheapest measured setting, 0.094 nats below the balanced ceiling.
# CA 3 / TX 2 / NY+NJ 2 costs 0.864 -- more than the incumbency premium -- and strands New
# England; CA 4 / TX 2 / NY+NJ 3 costs 0.123.  TX at 2 is right at every setting tried.
DEFAULT_CUTS = ("CA:5", "TX:2", "NY,NJ:3", "FL:2")

# states `geo.states_outline` drops, and the atom or group that absorbs each one's mass
MERGE_LONE = (("AK", "WA"), ("HI", "CA"))


@dataclass(frozen=True)
class Atoms:
    """The atom set: masses, the graph the draw runs on, and the zips behind each atom."""
    mass: dict
    graph: "nx.Graph"
    zips_of: dict
    pieces: dict                          # group name -> the piece names it was cut into
    stateless: list = field(default_factory=list)
    stateless_mass: float = 0.0
    merged: dict = field(default_factory=dict)


def parse_cuts(specs) -> dict:
    """`["CA:5", "NY,NJ:3"] -> {"CA": (("CA",), 5), "NYNJ": (("NY", "NJ"), 3)}`.

    The group name is the state codes concatenated, so a pooled group is `NYNJ` and its pieces
    are `NYNJ1`..`NYNJ3`.
    """
    out = {}
    for spec in specs:
        head, sep, tail = str(spec).partition(":")
        states = tuple(s.strip().upper() for s in head.split(",") if s.strip())
        if not sep or not states or not tail.strip().isdigit():
            raise ValueError(f"cut spec must be ST[,ST]:N, got {spec!r}")
        for st in states:
            if len(st) != 2 or not st.isalpha():
                raise ValueError(f"cut spec {spec!r} has a bad state code {st!r}")
        n = int(tail)
        if n < 2:
            raise ValueError(f"cut spec {spec!r} asks for {n} pieces; cutting means at least 2")
        name = "".join(states)
        if name in out:
            raise ValueError(f"duplicate cut group {name!r}")
        out[name] = (states, n)
    return out


def piece_names(name: str, n: int) -> tuple:
    """`("CA1", ..., "CAn")` -- a group's piece names, 1-based as the prototype wrote them."""
    return tuple(f"{name}{i + 1}" for i in range(n))


def cut_group(name: str, zips, M: dict, xy: dict, n: int, *, seed: int = CUT_SEED) -> dict:
    """`{zip: piece name}` -- one group's zips cut into `n` mass-balanced pieces.

    The cut is `centers.draw` on the group's own zips: the same balanced-assignment machinery
    stage 1 uses, applied one group at a time.  A zip with no coordinate or no opportunity
    cannot enter the LP (`centers.draw` requires positive mass), so it is attached afterwards
    to the nearest piece centre, or to the group's first piece when it has no coordinate.
    """
    zs = [z for z in zips if z in xy and M[z] > 0]
    if len(zs) < n:
        raise ValueError(f"group {name} has {len(zs)} usable zips, cannot cut into {n}")
    res = centers.draw(np.array([xy[z] for z in zs], float),
                       np.array([M[z] for z in zs], float), n, seed=seed)
    names = piece_names(name, n)
    piece = {z: names[int(lab)] for z, lab in zip(zs, np.asarray(res["labels"]).ravel())}
    cen = {names[i]: np.asarray(res["centers"])[i] for i in range(n)}
    for z in zips:
        if z not in piece:
            if z in xy:
                p = np.asarray(xy[z], float)
                piece[z] = min(cen, key=lambda a: float(np.sum((p - cen[a]) ** 2)))
            else:
                piece[z] = names[0]
    return piece


def border_states(pieces, zips_of: dict, xy: dict, neighbours, polygons: dict,
                  tol: float = BORDER_TOL) -> dict:
    """`{piece: [outside states it touches]}` for one cut group.

    A piece is a cluster of zip points with no polygon of its own, so adjacency to an outside
    state is decided by distance: any of the piece's zips within `tol` metres of that state's
    polygon.  The **nearest** piece is linked to each neighbour unconditionally, so a state the
    group borders is never left unreachable by a tolerance that happens to be too tight.
    """
    pts = {p: np.asarray([xy[z] for z in zips_of[p] if z in xy], float) for p in pieces}
    out = {p: [] for p in pieces}
    import shapely
    for nb in sorted(neighbours):
        poly = polygons.get(nb)
        if poly is None:
            continue
        best, bestd = None, float("inf")
        for p in pieces:
            if not len(pts[p]):
                continue
            d = float(shapely.distance(shapely.points(pts[p][:, 0], pts[p][:, 1]), poly).min())
            if d < bestd:
                best, bestd = p, d
            if d <= tol:
                out[p].append(nb)
        if best is not None and nb not in out[best]:
            out[best].append(nb)
    return out


def build(zips, M: dict, states: dict, xy: dict, cuts=DEFAULT_CUTS, *, seed: int = CUT_SEED,
          tol: float = BORDER_TOL, cache: str = geo.DEFAULT_DEST,
          rook: dict = None, polygons: dict = None) -> Atoms:
    """State atoms for one instance: whole states, the `cuts` groups cut, and their adjacency.

    `zips` must be in the instance's own node order (see the module docstring).  `xy` is
    `{zip: (x, y)}` already projected into LAEA metres -- the caller projects once, vectorised.
    `rook`/`polygons` default to `geo.state_rook(cache)` and are injectable so the atom graph
    can be built and tested with no geometry.

    Raises `ValueError` for a non-CONUS state that `MERGE_LONE` does not cover, since as an
    isolated node it would silently consume a district.
    """
    cuts = parse_cuts(cuts) if not isinstance(cuts, dict) else cuts
    if rook is None or polygons is None:
        rook, polygons = geo.state_rook(cache)
    st_of = {z: (states.get(z) or STATELESS) for z in zips}

    atom_of, pieces = {}, {}
    for gname, (group, n) in cuts.items():
        want = set(group)
        gzips = [z for z in zips if st_of[z] in want]
        atom_of.update(cut_group(gname, gzips, M, xy, n, seed=seed))
        pieces[gname] = piece_names(gname, n)
    for z in zips:
        atom_of.setdefault(z, st_of[z])

    atom_M, zips_of = defaultdict(float), defaultdict(list)
    for z in zips:
        atom_M[atom_of[z]] += float(M[z])
        zips_of[atom_of[z]].append(z)

    cut_states = {s for (group, _) in cuts.values() for s in group}
    adj = defaultdict(set)

    def link(a, b):
        if a != b and a in atom_M and b in atom_M:
            adj[a].add(b)
            adj[b].add(a)

    for a in [x for x in atom_M if x in polygons]:
        for b in rook.get(a, ()):
            link(a, b)
    for gname, (group, _) in cuts.items():
        ps = sorted(pieces[gname])
        for i, p in enumerate(ps):
            for q in ps[i + 1:]:
                link(p, q)
        nbrs = set()
        for s in group:
            nbrs |= set(rook.get(s, ()))
        nbrs -= cut_states
        for p, outside in border_states(ps, zips_of, xy, nbrs, polygons, tol).items():
            for nb in outside:
                link(p, nb)

    merged = {}
    for lone, host in MERGE_LONE:
        if lone not in atom_M:
            continue
        target = sorted(pieces[host])[0] if host in pieces else host
        if target in atom_M:
            atom_M[target] += atom_M.pop(lone)
            zips_of[target] += zips_of.pop(lone)
            adj.pop(lone, None)
            for s in adj.values():
                s.discard(lone)
            merged[lone] = target
    stray = sorted(a for a in atom_M if a in geo.NON_CONUS and atom_M[a] > 0)
    if stray:
        raise ValueError(f"non-CONUS states with opportunity and no rook entry: {stray}. "
                         f"They would each become an isolated atom and consume a district; "
                         f"add them to MERGE_LONE with a host state.")

    stateless = list(zips_of.pop(STATELESS, []))
    stateless_mass = float(atom_M.pop(STATELESS, 0.0))
    for s in adj.values():
        s.discard(STATELESS)

    graph = nx.Graph()
    graph.add_nodes_from(atom_M)
    for a in atom_M:
        for b in adj[a]:
            if b in atom_M:
                graph.add_edge(a, b)
    return Atoms(mass=dict(atom_M), graph=graph, zips_of=dict(zips_of), pieces=pieces,
                 stateless=stateless, stateless_mass=stateless_mass, merged=merged)
