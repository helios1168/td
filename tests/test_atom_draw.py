"""
test_atom_draw.py -- stage 1 on an atom graph (td/solvers/atom_draw.py).

The load-bearing tests are `test_every_district_is_connected` and
`test_ceiling_bounds_the_draw`: contiguity is the whole claim of this route, so it is asserted
rather than assumed, and the only honest bound is the Jensen ceiling -- `free_search` is a
reference, and `test_free_search_is_not_asserted_to_bound` records that on purpose.

Fixtures are synthetic named graphs with hand-set masses: no instance file, no network, no
geometry cache.  Every case is small enough that the winning partition is hand-checkable.
"""
from __future__ import annotations

import math

import networkx as nx
import numpy as np

from td.solvers import atom_draw, cert_draw            # noqa: E402


def path_atoms(masses):
    """A path of named atoms, `S00-S01-...`, with the given masses."""
    names = [f"S{i:02d}" for i in range(len(masses))]
    g = nx.Graph()
    nx.add_path(g, names)
    return g, {n: float(m) for n, m in zip(names, masses)}


def grid_atoms(r=4, c=4, heavy=None, heavy_mass=6.0):
    """An `r x c` grid of unit-mass atoms; 2-connected, so contiguity actually binds."""
    name = {(i, j): f"R{i}C{j}" for i in range(r) for j in range(c)}
    g = nx.Graph()
    g.add_nodes_from(name.values())
    for i in range(r):
        for j in range(c):
            if i + 1 < r:
                g.add_edge(name[(i, j)], name[(i + 1, j)])
            if j + 1 < c:
                g.add_edge(name[(i, j)], name[(i, j + 1)])
    mass = {n: 1.0 for n in name.values()}
    if heavy:
        mass[heavy] = float(heavy_mass)
    return g, mass


def two_blocks():
    """Two disjoint 6-cliques of mass 3 and 1 per atom -- the seat-allocation case."""
    g = nx.Graph()
    a = [f"A{i}" for i in range(6)]
    b = [f"B{i}" for i in range(6)]
    g.add_edges_from((x, y) for i, x in enumerate(a) for y in a[i + 1:])
    g.add_edges_from((x, y) for i, x in enumerate(b) for y in b[i + 1:])
    return g, {**{n: 3.0 for n in a}, **{n: 1.0 for n in b}}


def _members(res, k):
    return [{a for a, d in res["atom_district"].items() if d == j} for j in range(k)]


# ------------------------------------------------------------------------------- contiguity
def test_every_district_is_connected():
    """The claim of this route. Every district induces a connected subgraph, at every seed."""
    g, mass = grid_atoms()
    for seed in range(3):
        res = atom_draw.draw(g, mass, 4, seed=seed, restarts=6)
        for part in _members(res, 4):
            assert part, "empty district"
            assert nx.is_connected(g.subgraph(part)), sorted(part)


def test_check_contiguous_rejects_a_disconnected_district():
    g, mass = grid_atoms(3, 3)
    good = atom_draw.draw(g, mass, 3, seed=0, restarts=4)["atom_district"]
    atom_draw.check_contiguous(g, good, 3)                      # the real draw passes
    bad = dict(good)
    corners = ["R0C0", "R2C2"]
    for a in corners:                                           # two opposite corners, one id
        bad[a] = 0
    for a in bad:
        if a not in corners and bad[a] == 0:
            bad[a] = 1
    try:
        atom_draw.check_contiguous(g, bad, 3)
    except ValueError as e:
        assert "disconnected" in str(e)
    else:
        raise AssertionError("expected a disconnected district to be rejected")


def test_check_contiguous_rejects_empty_and_unassigned():
    g, mass = path_atoms([1, 1, 1, 1])
    labelled = {a: 0 for a in mass}
    try:
        atom_draw.check_contiguous(g, labelled, 2)              # district 1 is empty
    except ValueError:
        pass
    else:
        raise AssertionError("expected an empty district to be rejected")
    partial = {a: 0 for a in list(mass)[:2]}
    try:
        atom_draw.check_contiguous(g, partial, 1)               # two atoms unassigned
    except ValueError as e:
        assert "unassigned" in str(e)
    else:
        raise AssertionError("expected unassigned atoms to be rejected")


# --------------------------------------------------------------------------------- the draw
def test_draw_finds_the_hand_checkable_split():
    """Path 10-1-1-1-10, k=2: the only contiguous cuts are the four prefixes; 12/11 wins."""
    g, mass = path_atoms([10, 1, 1, 1, 10])
    res = atom_draw.draw(g, mass, 2, seed=0, restarts=20)
    assert sorted(res["masses"], reverse=True) == [12.0, 11.0], res["masses"]
    assert math.isclose(res["nash"], math.log(12) + math.log(11), rel_tol=0, abs_tol=1e-12)


def test_draw_labels_index_sorted_atoms():
    g, mass = grid_atoms(3, 3)
    res = atom_draw.draw(g, mass, 3, seed=0, restarts=4)
    assert res["atoms"] == sorted(mass)
    assert len(res["labels"]) == len(res["atoms"])
    assert [res["atom_district"][a] for a in res["atoms"]] == list(res["labels"])
    assert math.isclose(sum(res["masses"]), sum(mass.values()), rel_tol=0, abs_tol=1e-9)


def test_same_seed_same_labels():
    g, mass = grid_atoms()
    a = atom_draw.draw(g, mass, 4, seed=7, restarts=5)
    b = atom_draw.draw(g, mass, 4, seed=7, restarts=5)
    assert np.array_equal(a["labels"], b["labels"])
    assert a["nash"] == b["nash"]


def test_draw_rejects_bad_k_and_nonpositive_mass():
    g, mass = grid_atoms(2, 2)
    for k in (0, 5):
        try:
            atom_draw.draw(g, mass, k, restarts=2)
        except ValueError:
            pass
        else:
            raise AssertionError(f"expected ValueError for k={k}")
    zeroed = dict(mass)
    zeroed["R0C0"] = 0.0
    try:
        atom_draw.draw(g, zeroed, 2, restarts=2)
    except ValueError as e:
        assert "positive opportunity" in str(e)
    else:
        raise AssertionError("expected a zero-mass atom to be rejected")


def test_draw_spans_components_and_k_below_component_count_raises():
    g, mass = two_blocks()
    res = atom_draw.draw(g, mass, 4, seed=0, restarts=8)
    assert res["n_components"] == 2
    assert sum(res["seats_per_component"]) == 4
    for part in _members(res, 4):
        assert nx.is_connected(g.subgraph(part))
    try:
        atom_draw.draw(g, mass, 1, restarts=2)
    except ValueError as e:
        assert "components" in str(e)
    else:
        raise AssertionError("expected k below the component count to be rejected")


def test_allocate_splits_seats_by_mass():
    g, mass = two_blocks()                                      # 18 vs 6, so 3:1
    comps = sorted(nx.connected_components(g), key=lambda c: -sum(mass[a] for a in c))
    assert atom_draw.allocate(mass, comps, 8) == [6, 2]
    assert atom_draw.allocate(mass, comps, 2) == [1, 1]
    assert sum(atom_draw.allocate(mass, comps, 7)) == 7


# ---------------------------------------------------------------------------- the stateless
def test_stateless_mass_lands_in_the_lightest_district():
    """The documented placeholder rule: it goes to the lightest district, then all re-sort."""
    g, mass = path_atoms([10, 1, 1, 1, 10])
    plain = atom_draw.draw(g, mass, 2, seed=0, restarts=20)
    assert sorted(plain["masses"], reverse=True) == [12.0, 11.0]
    res = atom_draw.draw(g, mass, 2, seed=0, restarts=20, stateless_mass=5.0)
    assert res["masses"] == [16.0, 12.0], res["masses"]          # 11 + 5, then re-ordered
    assert res["stateless_district"] == 0
    assert math.isclose(res["nash"], math.log(16) + math.log(12), rel_tol=0, abs_tol=1e-12)


# ------------------------------------------------------------------------- bound / reference
def test_ceiling_bounds_the_draw():
    """The Jensen ceiling bounds every partition, so the draw can never exceed it."""
    g, mass = grid_atoms(4, 4, heavy="R1C1")
    res = atom_draw.draw(g, mass, 4, seed=0, restarts=10)
    cert = cert_draw.cert_balance_ceiling(np.array(res["masses"], float), np.arange(4), 4)
    assert res["nash"] <= cert["ceiling_nash"] + 1e-9
    assert cert["gap_nats"] >= -1e-9
    for seed in range(4):                                       # and every other draw too
        other = atom_draw.draw(g, mass, 4, seed=seed, restarts=4)
        assert other["nash"] <= cert["ceiling_nash"] + 1e-9


def test_free_search_warm_start_never_loses_to_the_draw():
    """Dropping a constraint cannot lower the optimum, so the warm-started search must not."""
    g, mass = grid_atoms(4, 4, heavy="R2C3")
    res = atom_draw.draw(g, mass, 4, seed=0, restarts=10)
    ref = atom_draw.free_search(mass, 4, init=_members(res, 4), restarts=2, rounds=2000)
    assert ref >= res["nash"] - 1e-9


def test_free_search_is_not_asserted_to_bound():
    """Cold-started, the relaxed search can come in BELOW the contiguous draw.

    It is a local search over the relaxation, so it returns a feasible relaxed value, which
    orders against the contiguous optimum not at all.  This test does not demand that it lose
    -- it asserts only that nothing in the code claims otherwise, by checking the one guarantee
    that does hold: the ceiling bounds both.
    """
    g, mass = path_atoms([10, 1, 1, 1, 10])
    res = atom_draw.draw(g, mass, 2, seed=0, restarts=20)
    cold = atom_draw.free_search(mass, 2, restarts=1, rounds=500)
    ceiling = 2 * math.log(sum(mass.values()) / 2)
    assert cold <= ceiling + 1e-9
    assert res["nash"] <= ceiling + 1e-9


# ------------------------------------------------------------------------------ to_district
def test_to_district_expands_atoms_to_zips():
    g, mass = path_atoms([2, 2, 2, 2])
    res = atom_draw.draw(g, mass, 2, seed=0, restarts=6)
    zips_of = {a: [f"{a}-z{i}" for i in range(3)] for a in mass}
    out = atom_draw.to_district(zips_of, res["atom_district"])
    assert len(out) == 12
    for a, zs in zips_of.items():
        assert {out[z] for z in zs} == {res["atom_district"][a]}


def test_to_district_requires_a_district_for_stateless_zips():
    g, mass = path_atoms([2, 2])
    res = atom_draw.draw(g, mass, 2, seed=0, restarts=4)
    zips_of = {a: [f"{a}-z"] for a in mass}
    out = atom_draw.to_district(zips_of, res["atom_district"], ["orphan"], 1)
    assert out["orphan"] == 1
    try:
        atom_draw.to_district(zips_of, res["atom_district"], ["orphan"], None)
    except ValueError as e:
        assert "stateless" in str(e)
    else:
        raise AssertionError("expected stateless zips with no district to be rejected")
