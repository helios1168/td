"""td.supports: the closed support family and the drawability terms c_v(S), b_{uv} and μ_S (#67).

The council's counterexamples are regression tests: the five-ZIP path whose three components
make the pairwise corridor floor unnecessary (C6), and the singleton-u supports the printed
border cap counted against v (C7).  Brute force checks the enumeration, the closure and the
corridor floor on small random graphs, and the corridor floor on the fixture's small units (with
TIGER/Line 2025 state polygons present; SKIP without).
"""
from __future__ import annotations

import itertools
import math
import random

from td import spec, supports

from tests import test_spec as ts

S51 = ts.S51


def _instance(unit_zips: dict, edges, mass: dict, modes=None, max_size=6, **channel):
    """A one-channel toy instance; `mass` is {zip: m_z}, `modes` {unit: mode}."""
    modes = modes or {}
    raw = ts._toy_raw(max_size=max_size, max_dist_km=1e9, **channel)
    for m in ("clipped", "free"):
        listed = [u for u, v in modes.items() if v == m]
        if listed:
            raw["channels"]["X"][m] = listed
    s = spec.parse(raw)
    unit_of = {z: u for u, zs in unit_zips.items() for z in zs}
    xy = {z: (1000.0 * i, 0.0) for i, z in enumerate(sorted(unit_of))}
    units = spec.Units.from_graph(unit_of, edges, xy)
    return spec.assemble(s, units, {(z, "f"): m for z, m in mass.items()})


def _connected(nodes, adj):
    return supports.connected(nodes, adj) if nodes else False


def _brute_connected_sets(nodes, adj, cap, ok):
    out = set()
    for r in range(1, cap + 1):
        for c in itertools.combinations(sorted(nodes), r):
            if _connected(c, adj) and all(ok(a, b) for a, b in itertools.combinations(c, 2)):
                out.add(frozenset(c))
    return out


def _random_graph(rng, n, p):
    nodes = [f"n{i}" for i in range(n)]
    adj = {v: set() for v in nodes}
    for a, b in itertools.combinations(nodes, 2):
        if rng.random() < p:
            adj[a].add(b)
            adj[b].add(a)
    return nodes, adj


def _legacy_generate(nodes, adj, max_size, ok):
    """`generate_valid_supports` at the tag (`tools/group2_support.py:27–63`): grow every
    connected set from each vertex, then drop sets with a pair over the distance cap."""
    found = set()

    def extend(cur, nb):
        key = frozenset(cur)
        if key in found:
            return
        found.add(key)
        if len(cur) < max_size:
            for v in nb:
                extend(cur | {v}, (nb | adj[v]) - (cur | {v}))

    for i in nodes:
        extend({i}, set(adj[i]))
    return {s for s in found if all(ok(a, b) for a, b in itertools.combinations(sorted(s), 2))}


# ------------------------------------------------------------------------------ enumeration
def test_connected_sets_match_brute_force_and_are_each_found_once():
    rng = random.Random(7)
    for trial in range(40):
        nodes, adj = _random_graph(rng, rng.randint(1, 9), rng.choice((0.2, 0.35, 0.6)))
        far = {frozenset(p) for p in itertools.combinations(nodes, 2) if rng.random() < 0.2}
        ok = lambda a, b: frozenset((a, b)) not in far
        cap = rng.randint(1, 5)
        got = supports.connected_sets(nodes, adj, cap, ok)
        assert len(got) == len(set(got)), trial
        assert set(got) == _brute_connected_sets(nodes, adj, cap, ok), trial
        assert set(got) == _legacy_generate(nodes, adj, cap, ok), trial


def test_closure_check_finds_a_missing_connected_subset():
    adj = {"a": {"b"}, "b": {"a", "c"}, "c": {"b"}}
    full = supports.connected_sets("abc", adj, 3)
    assert supports.closure_violations(full, adj) == []
    broken = [s for s in full if s != frozenset("ab")]
    assert supports.closure_violations(broken, adj) == [(frozenset("abc"), frozenset("ab"))]
    # {a, c} is not connected, so {a, b, c} without b is not a violation
    assert supports.closure_violations([s for s in full if s != frozenset("ac")], adj) == []


def test_forbidden_pairs_keep_random_families_closed():
    rng = random.Random(11)
    for trial in range(40):
        nodes, adj = _random_graph(rng, rng.randint(2, 9), 0.4)
        fam = supports.connected_sets(nodes, adj, 5)
        pairs = [frozenset(p) for p in itertools.combinations(nodes, 2) if rng.random() < 0.25]
        kept = [s for s in fam if not any(p <= s for p in pairs)]
        assert supports.closure_violations(kept, adj) == [], trial


def _brute_closed(fam: supports.Family) -> bool:
    have = set(fam.supports)
    return all(t in have for s in have for t in _brute_connected_sets(s, fam.adj, len(s),
                                                                        lambda a, b: True))


def test_every_final_family_of_the_51_scenario_is_closed():
    s = spec.load(S51)
    inst = spec.build(s, ts._all_conus(s), ts._reference())
    for c in inst.channels:
        fam = supports.family(inst, c)
        assert _brute_closed(fam), c
        assert set(inst.channels[c].units) == set().union(*fam.supports)
    nat = supports.family(inst, "national")
    ne_ny = frozenset(["CT", "MA", "ME", "NH", "RI", "VT", "NY"])
    assert ne_ny in nat and frozenset(["CT"]) in nat and frozenset(["CT", "NY"]) in nat
    assert not any("FL" in x and len(x) > 1 for x in nat.supports)
    assert not any({"MS", "AL"} <= x or {"CT", "NJ"} <= x for x in nat.supports)
    assert nat.removed > 0
    wifi = supports.family(inst, "WIFI")
    assert len(wifi) == 16 and wifi.enumerated == 0
    assert max(wifi.supports, key=len) in {frozenset(["ND", "SD", "NE"]),
                                           frozenset(["ID", "MT", "WY"])}


def test_the_51_family_sizes_at_caps_6_and_7_on_the_committed_graph():
    s = spec.load(S51)
    inst = spec.build(s, ts._all_conus(s), ts._reference())
    sizes = {cap: {c: len(supports.family(inst, c, max_size=cap)) for c in inst.channels}
             for cap in (6, 7)}
    print(f"      U32 family sizes on the committed 2025 graph: {sizes}")
    for c in ("national", "WH", "FI"):
        assert sizes[7][c] > sizes[6][c]
    assert sizes[6]["WH"] == sizes[6]["FI"] and sizes[6]["WIFI"] == sizes[7]["WIFI"] == 16


def test_a_filter_that_removes_an_extra_support_is_refused():
    inst = _instance({"AL": ["a"], "AR": ["b"], "AZ": ["c"]}, [("a", "b"), ("b", "c")],
                     {"a": 1.0, "b": 1.0, "c": 1.0}, extra_supports=[["AL", "AR"]],
                     forbid_pairs=[["AL", "AR"]])
    ts._raises(lambda: supports.family(inst, "X"), "removes the extra support")


def test_listed_supports_are_their_closure_only():
    inst = _instance({"AL": ["a"], "AR": ["b"], "AZ": ["c"]}, [("a", "b"), ("b", "c")],
                     {"a": 1.0, "b": 1.0, "c": 1.0}, supports="listed",
                     extra_supports=[["AL", "AR", "AZ"]])
    fam = supports.family(inst, "X")
    assert set(fam.supports) == {frozenset(x) for x in (["AL"], ["AR"], ["AZ"], ["AL", "AR"],
                                                        ["AR", "AZ"], ["AL", "AR", "AZ"])}


# ------------------------------------------------------------------------------ corridor floor
def _c6():
    """C6: v's ZIPs are the unit-mass path z1–z5; A touches z1, B touches z5, C touches both."""
    return _instance({"CA": ["z1", "z2", "z3", "z4", "z5"], "AZ": ["a"], "AR": ["b"],
                      "AL": ["c"]},
                     [("z1", "z2"), ("z2", "z3"), ("z3", "z4"), ("z4", "z5"), ("a", "z1"),
                      ("b", "z5"), ("c", "z1"), ("c", "z5")],
                     {z: 1.0 for z in ("z1", "z2", "z3", "z4", "z5", "a", "b", "c")},
                     modes={"CA": "free"})


def _least_need(inst, s, v):
    """The least mass in v of a connected district with footprint S, one ZIP per other unit."""
    units, m = inst.units, inst.channels["X"].m
    others = [z for u in s if u != v for z in units.zips[u]]
    best = math.inf
    for r in range(1, len(units.zips[v]) + 1):
        for p in itertools.combinations(units.zips[v], r):
            if supports.connected(set(p) | set(others), units.zip_adj):
                best = min(best, sum(m[z] for z in p))
    return best


def test_c6_the_three_component_path_gets_the_component_versus_rest_floor():
    inst = _c6()
    s = frozenset(["CA", "AZ", "AR", "AL"])
    adj = supports.unit_graph(inst, "X")
    assert supports.cut_vertices(s, adj) == ["CA"]
    assert supports.corridor_floor(inst, "X", s, "CA") == 1.0
    # the printed pairwise floor, the lightest chain from A's border to B's, is 5
    bd = supports.borders(inst, "CA")
    printed = supports.lightest_path(inst.units.zips["CA"], inst.units.zip_adj,
                                     inst.channels["X"].m, bd["AZ"], bd["AR"])
    assert printed == 5.0
    # {z1, z5} with C connects the district: it needs 2 in v, below the printed 5
    assert _least_need(inst, s, "CA") == 2.0
    assert supports.corridor_floor(inst, "X", s, "CA") <= _least_need(inst, s, "CA") < printed


def test_the_two_component_floor_is_the_pairwise_chain():
    inst = _c6()
    s = frozenset(["CA", "AZ", "AR"])
    assert supports.corridor_floor(inst, "X", s, "CA") == 5.0 == _least_need(inst, s, "CA")


def _brute_floor(inst, s, v):
    """max_i of the least mass of a connected set of v's ZIPs meeting ∂_i and ∂_{−i}."""
    units, m = inst.units, inst.channels["X"].m
    adj = supports.unit_graph(inst, "X")
    bd = supports.borders(inst, v)
    sides = [set().union(*(bd.get(u, set()) for u in a))
             for a in supports.cut_components(s, v, adj)]
    floor = 0.0
    for i, side in enumerate(sides):
        rest = set().union(*(t for j, t in enumerate(sides) if j != i))
        best = math.inf
        for r in range(1, len(units.zips[v]) + 1):
            for p in itertools.combinations(units.zips[v], r):
                if set(p) & side and set(p) & rest and supports.connected(p, units.zip_adj):
                    best = min(best, sum(m[z] for z in p))
        floor = max(floor, best)
    return floor


def test_corridor_floor_matches_brute_force_on_random_units():
    rng = random.Random(3)
    checked = 0
    for trial in range(60):
        n = rng.randint(2, 8)
        vz = [f"v{i}" for i in range(n)]
        edges = [(vz[i], vz[rng.randrange(i)]) for i in range(1, n)]
        edges += [p for p in itertools.combinations(vz, 2) if rng.random() < 0.15]
        others = {"AZ": ["a"], "AR": ["b"], "AL": ["c"]}
        for z in ("a", "b", "c"):
            edges += [(z, y) for y in rng.sample(vz, rng.randint(1, min(2, n)))]
        mass = {z: rng.choice((0.0, 0.5, 1.0, 2.0, 7.0)) for z in vz}
        mass.update(a=1.0, b=1.0, c=1.0)
        if not any(mass[z] for z in vz):
            mass[vz[0]] = 1.0
        inst = _instance({"CA": vz, **others}, edges, mass, modes={"CA": "free"})
        for s in ([["CA", "AZ", "AR"], ["CA", "AZ", "AR", "AL"]]):
            s = frozenset(s)
            got = supports.corridor_floor(inst, "X", s, "CA")
            assert got == _brute_floor(inst, s, "CA"), trial
            assert got <= _least_need(inst, s, "CA") + 1e-12, trial
            checked += 1
    assert checked == 120


def test_corridor_floor_matches_brute_force_on_the_fixtures_small_units():
    s = spec.load(S51)
    fx = ts._fixture(tuple(s.fine_channels))
    if fx is None:
        return
    inst = spec.build(s, fx.extract, ts._reference(), fx.graph)
    fam = supports.family(inst, "national")
    ch, zip_adj = inst.channels["national"], inst.units.zip_adj
    small = sorted({(len(inst.units.zips[v]), v) for (_, v) in supports.corridor_floors(inst, fam)
                    if len(inst.units.zips[v]) <= 14})
    assert small, "no small cut unit on the fixture"
    checked = 0
    for _, v in small[:2]:
        zs = inst.units.zips[v]
        pieces = [(set(p), sum(ch.m[z] for z in p))
                  for r in range(1, len(zs) + 1) for p in itertools.combinations(zs, r)
                  if supports.connected(p, zip_adj)]
        bd = supports.borders(inst, v)
        for x in [x for x in fam.supports if v in supports.cut_vertices(x, fam.adj)][:4]:
            sides = [set().union(*(bd.get(u, set()) for u in a))
                     for a in supports.cut_components(x, v, fam.adj)]
            want = max(min((m for p, m in pieces
                            if p & side and p & set().union(*(t for t in sides if t is not side))),
                           default=math.inf)
                       for side in sides)
            assert math.isclose(supports.corridor_floor(inst, "national", x, v), want,
                                rel_tol=1e-12), (v, sorted(x))
            checked += 1
    assert checked > 0


# ------------------------------------------------------------------------------ border cap, μ_S
def test_c7_a_singleton_u_support_is_not_counted_against_v():
    # free v (CA) with one ZIP y, adjacent only to u (AZ) through x1; b_uv = 1
    inst = _instance({"AZ": ["x1", "x2", "x3"], "CA": ["y"]},
                     [("x1", "x2"), ("x2", "x3"), ("x1", "y")],
                     {"x1": 1.0, "x2": 1.0, "x3": 1.0, "y": 1.0}, modes={"CA": "free"},
                     max_size=2)
    fam = supports.family(inst, "X")
    b, rows = supports.border_rows(inst, fam)["AZ", "CA"]
    assert b == 1 == supports.border_count(inst, "AZ", "CA")
    assert rows == [frozenset(["AZ", "CA"])]
    # a connected drawing: {x2}, {x3} on {u}, and {x1, y} on {u, v}; its read-back
    drawing = [{"x2"}, {"x3"}, {"x1", "y"}]
    assert all(supports.connected(d, inst.units.zip_adj) for d in drawing)
    n = {}
    for d in drawing:
        foot = frozenset(inst.units.unit_of[z] for z in d)
        n[foot] = n.get(foot, 0) + 1
    corrected = sum(n.get(x, 0) for x in rows)
    printed = sum(k for x, k in n.items() if fam.adj["CA"] & x == {"AZ"})
    assert corrected == 1 <= b < printed == 3


def test_border_rows_cover_only_free_units():
    inst = _c6()
    fam = supports.family(inst, "X")
    rows = supports.border_rows(inst, fam)
    assert {v for _, v in rows} == {"CA"}
    assert {u for u, _ in rows} == {"AZ", "AR", "AL"}
    assert rows["AL", "CA"][0] == 2      # z1 and z5 both touch C


def test_margin_sums_the_heaviest_zip_of_splittable_units():
    inst = _instance({"AL": ["a1", "a2"], "AR": ["b1", "b2"], "AZ": ["c1"]},
                     [("a1", "a2"), ("a2", "b1"), ("b1", "b2"), ("b2", "c1")],
                     {"a1": 3.0, "a2": 1.0, "b1": 2.0, "b2": 5.0, "c1": 4.0},
                     modes={"AL": "free", "AR": "clipped"})
    assert supports.margin(inst, "X", ["AL", "AR", "AZ"]) == 8.0
    assert supports.margin(inst, "X", ["AZ"]) == 0.0
    assert supports.diameter(inst, ["AL"]) == 0.0
