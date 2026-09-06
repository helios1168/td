"""
test_atoms.py -- state atoms for stage 1 (td/atoms.py).

The load-bearing test is `test_pieces_link_only_the_states_they_touch`: cutting a state removes
it from the rook graph, so the pieces have to re-earn their neighbours by proximity, and a
piece wired to the wrong state would make the draw contiguous on paper and wrong on the map.

The geography is a hand-built four-box world with an injected rook table and injected
polygons, so nothing here reads the TIGER cache: no instance file, no network, no geometry
cache.  `cut_group` does call `centers.draw`, which is a scipy LP and needs neither.
"""
from __future__ import annotations

import networkx as nx
from shapely import box

from td import atoms                                   # noqa: E402

# a four-box world, in metres.  CA sits south-west, NV east of it, OR north, WA north of OR.
POLY = {"CA": box(0, 0, 10_000, 10_000),
        "NV": box(10_000, 0, 20_000, 10_000),
        "OR": box(0, 10_000, 10_000, 20_000),
        "WA": box(0, 20_000, 10_000, 30_000)}
ROOK = {"CA": ("NV", "OR"), "NV": ("CA",), "OR": ("CA", "WA"), "WA": ("OR",)}


def world(extra_zips=(), extra_states=None):
    """`(zips, M, states, xy)` -- 4 CA zips spread west-to-east, one each for NV, OR, WA."""
    xy = {"ca-w1": (1_000, 2_000), "ca-w2": (1_000, 8_000),
          "ca-e1": (9_000, 2_000), "ca-e2": (9_000, 8_000),
          "nv-1": (15_000, 5_000), "or-1": (5_000, 15_000), "wa-1": (5_000, 25_000)}
    states = {z: z.split("-")[0].upper() for z in xy}
    M = {z: 10.0 for z in xy}
    zips = list(xy)
    for z, st, m, pt in extra_zips:
        zips.append(z)
        states[z] = st
        M[z] = m
        if pt is not None:
            xy[z] = pt
    if extra_states:
        states.update(extra_states)
    return zips, M, states, xy


def build(cuts=(), **kw):
    zips, M, states, xy = world(**kw.pop("world", {}))
    return atoms.build(zips, M, states, xy, cuts, rook=ROOK, polygons=POLY, **kw)


# ---------------------------------------------------------------------------- the cut specs
def test_parse_cuts():
    assert atoms.parse_cuts(["CA:5"]) == {"CA": (("CA",), 5)}
    assert atoms.parse_cuts(["NY,NJ:3"]) == {"NYNJ": (("NY", "NJ"), 3)}
    assert atoms.parse_cuts(["ca:2"]) == {"CA": (("CA",), 2)}
    for bad in (["CA"], ["CA:0"], ["CA:1"], ["CA:x"], ["TEX:2"], [":2"], ["CA:2", "CA:3"]):
        try:
            atoms.parse_cuts(bad)
        except ValueError:
            pass
        else:
            raise AssertionError(f"expected ValueError for {bad!r}")


def test_piece_names_are_one_based():
    assert atoms.piece_names("NYNJ", 3) == ("NYNJ1", "NYNJ2", "NYNJ3")


# ------------------------------------------------------------------------------- the graph
def test_uncut_atoms_are_the_rook_graph():
    """With nothing cut, the atom graph is exactly the states and exactly the rook edges."""
    A = build()
    assert set(A.mass) == {"CA", "NV", "OR", "WA"}
    assert A.mass["CA"] == 40.0 and A.mass["WA"] == 10.0
    assert set(map(frozenset, A.graph.edges)) == {frozenset(e) for e in
                                                  (("CA", "NV"), ("CA", "OR"), ("OR", "WA"))}
    assert nx.is_connected(A.graph)


def test_cut_group_partitions_and_balances():
    """Every zip of the group lands in exactly one piece, and the pieces split the mass."""
    zips, M, states, xy = world()
    ca = [z for z in zips if states[z] == "CA"]
    piece = atoms.cut_group("CA", ca, M, xy, 2, seed=0)
    assert set(piece) == set(ca)
    assert set(piece.values()) == {"CA1", "CA2"}
    per = {}
    for z, p in piece.items():
        per[p] = per.get(p, 0.0) + M[z]
    assert per["CA1"] == per["CA2"] == 20.0


def test_cut_group_places_coordinateless_and_massless_zips():
    """A zip the LP cannot take still gets a piece: nearest centre, or piece 1 with no point."""
    world_kw = {"extra_zips": [("ca-zero", "CA", 0.0, (9_500, 5_000)),
                               ("ca-nopt", "CA", 7.0, None)]}
    zips, M, states, xy = world(**world_kw)
    ca = [z for z in zips if states[z] == "CA"]
    piece = atoms.cut_group("CA", ca, M, xy, 2, seed=0)
    assert set(piece) == set(ca)
    assert piece["ca-nopt"] == "CA1"
    assert piece["ca-zero"] == piece["ca-e1"], "a zero-mass zip joins its nearest piece"


def test_pieces_link_only_the_states_they_touch():
    """Cut CA in two: the pieces are mutually adjacent, and each reaches the states it nears."""
    A = build(cuts=["CA:2"], tol=2_000.0)
    assert A.pieces == {"CA": ("CA1", "CA2")}
    assert set(A.mass) == {"CA1", "CA2", "NV", "OR", "WA"}
    assert A.graph.has_edge("CA1", "CA2")
    east = "CA1" if "ca-e1" in A.zips_of["CA1"] else "CA2"
    west = "CA2" if east == "CA1" else "CA1"
    assert A.graph.has_edge(east, "NV"), "the eastern piece borders NV"
    assert not A.graph.has_edge(west, "NV"), "the western piece is 9 km from NV, tol is 2 km"
    assert A.graph.has_edge("OR", "WA")
    assert nx.is_connected(A.graph)


def test_a_neighbour_is_never_orphaned_by_a_tight_tolerance():
    """Below every tolerance, the nearest piece still links -- so the graph stays connected."""
    A = build(cuts=["CA:2"], tol=0.0)
    assert nx.is_connected(A.graph)
    assert sum(1 for p in ("CA1", "CA2") if A.graph.has_edge(p, "NV")) == 1


# ----------------------------------------------------------------- stateless and non-CONUS
def test_stateless_zips_are_not_atoms():
    A = build(world={"extra_zips": [("orphan", "", 4.0, None)]})
    assert A.stateless == ["orphan"]
    assert A.stateless_mass == 4.0
    assert atoms.STATELESS not in A.mass
    assert atoms.STATELESS not in A.graph
    assert all("orphan" not in zs for zs in A.zips_of.values())


def test_merge_lone_states():
    """AK's mass joins WA and HI's joins CA's first piece; both vanish from the graph."""
    A = build(cuts=["CA:2"],
              world={"extra_zips": [("ak-1", "AK", 5.0, None), ("hi-1", "HI", 3.0, None)]})
    assert A.merged == {"AK": "WA", "HI": "CA1"}
    assert "AK" not in A.mass and "HI" not in A.mass
    assert A.mass["WA"] == 15.0
    assert "ak-1" in A.zips_of["WA"] and "hi-1" in A.zips_of["CA1"]


def test_merge_lone_state_without_a_cut_uses_the_whole_state():
    A = build(world={"extra_zips": [("hi-1", "HI", 3.0, None)]})
    assert A.merged == {"HI": "CA"}
    assert A.mass["CA"] == 43.0


def test_non_conus_without_a_host_raises():
    """PR has no polygon and no rook entry, so as an atom it would silently eat a district."""
    try:
        build(world={"extra_zips": [("pr-1", "PR", 6.0, None)]})
    except ValueError as e:
        assert "PR" in str(e) and "MERGE_LONE" in str(e)
    else:
        raise AssertionError("expected a non-CONUS state with opportunity to be rejected")


def test_default_cuts_are_the_decided_ones():
    """The 2026-09-06 decision, parsed: CA 5 / TX 2 / NY+NJ 3 / FL 2."""
    assert atoms.parse_cuts(atoms.DEFAULT_CUTS) == {
        "CA": (("CA",), 5), "TX": (("TX",), 2), "NYNJ": (("NY", "NJ"), 3), "FL": (("FL",), 2)}
