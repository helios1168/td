"""td.realize: transport, tree rounding along the forest, one guarded repair pass (#69).

Toy plans are built from `master.Copy` directly, so a test can hand the realizer a plan the master
would refuse (#7's thin corridor) or pin every share.  The fixture test realizes the 51 scenario on
the seed-0 sparse fixture and runs the audit on it (TIGER/Line 2025 state polygons needed; SKIP
without).  #1, #7 and #11 are the regressions named in their tests.
"""
from __future__ import annotations

import collections
import dataclasses
import math
import random
import tomllib

from td import audit, master, realize, spec, supports

from tests import test_master as tm
from tests import test_spec as ts


def _toy(unit_zips, edges, mass, xy_km, modes=None, **channel):
    """(instance, xy in metres) for a one-channel toy; `xy_km` gives each ZIP's point in km."""
    inst = tm._toy(unit_zips, edges, mass, xy_km, modes, **channel)
    return inst, {z: (1000.0 * x, 1000.0 * y) for z, (x, y) in xy_km.items()}


def _plan(inst, copies, channel="X"):
    """A decoded plan from [(support, {unit: share})], copies numbered per support."""
    ch, count, out = inst.channels[channel], collections.Counter(), []
    for s, share in copies:
        s = frozenset(s)
        count[s] += 1
        out.append(master.Copy(s, count[s], dict(share), {v: ch.M[v] * y for v, y in share.items()}))
    return master.Plan(channel, ch.spec.delta, {}, {}, out, 0.0, {})


def _claim3(m, flow, owner, a):
    """Every district within Claim 3's bound: exact without a split ZIP, else below m*_j."""
    split = {z for z, _ in flow if sum(1 for y, _ in flow if y == z) > 1}
    drawn = collections.Counter()
    for z, j in owner.items():
        drawn[j] += m[z]
    for j, target in a.items():
        touched = [m[z] for z in split if (z, j) in flow]
        slack = 1e-7 * max(1.0, sum(a.values()))
        bound = max(touched) if touched else 0.0
        assert abs(drawn[j] - target) < bound + slack, (j, drawn[j], target, bound)
        if not touched:
            assert abs(drawn[j] - target) <= slack


# ------------------------------------------------------------------------------ Claim 3
def test_tree_rounding_keeps_every_district_within_the_claim_3_bound_on_random_units():
    rng = random.Random(69)
    for _ in range(150):
        n, k = rng.randint(5, 40), rng.randint(2, 7)
        zs = [f"z{i:02d}" for i in range(n)]
        m = {z: 0.0 if rng.random() < 0.2 else rng.lognormvariate(0.0, 1.5) for z in zs}
        m[zs[0]] = max(m[zs[0]], 0.5)
        p = {z: (rng.uniform(0, 100), rng.uniform(0, 100)) for z in zs}
        w = [rng.expovariate(1.0) + 0.05 for _ in range(k)]
        pos = [z for z in zs if m[z] > 0]
        total = math.fsum(m[z] for z in pos)
        a = {f"j{i}": total * wi / sum(w) for i, wi in enumerate(w)}
        c = {j: (rng.uniform(0, 100), rng.uniform(0, 100)) for j in a}
        flow = realize.transport(pos, m, p, c, a)
        split = {z for z, _ in flow if sum(1 for y, _ in flow if y == z) > 1}
        assert len(split) <= k - 1                                  # Lemma 3a
        owner = realize.round_forest(m, flow, lambda z, j: m[z] * realize._d2(p[z], c[j]))
        assert set(owner) == set(pos)
        _claim3(m, flow, owner, a)


def _argmax_star(s):
    """District c holds 0.45 of each of s unit-mass ZIPs, district d_i the other 0.55 of z_i."""
    m = {f"z{i}": 1.0 for i in range(1, s + 1)}
    flow = {**{(z, "c"): 0.45 for z in m}, **{(z, f"d{z[1:]}"): 0.55 for z in m}}
    a = {"c": 0.45 * s, **{f"d{i}": 0.55 for i in range(1, s + 1)}}
    return m, flow, a


def test_tree_rounding_holds_where_per_zip_argmax_fails_at_s_3_and_6():
    for s in (3, 6):
        m, flow, a = _argmax_star(s)
        argmax = {z: max((j for y, j in flow if y == z), key=lambda j: flow[z, j]) for z in m}
        assert all(j != "c" for j in argmax.values())
        assert 0.45 * s > 1.0                                       # argmax misses c by 0.45 s
        for cost in (lambda z, j: 0.0, lambda z, j: 0.0 if j != "c" else 1.0):
            owner = realize.round_forest(m, flow, cost)
            _claim3(m, flow, owner, a)


def test_a_fractional_graph_that_is_not_a_forest_stops_the_run():
    flow = {("a", "j1"): 0.5, ("a", "j2"): 0.5, ("b", "j1"): 0.5, ("b", "j2"): 0.5}
    for call in (lambda: realize.check_forest(flow),
                 lambda: realize.round_forest({"a": 1.0, "b": 1.0}, flow, lambda z, j: 0.0)):
        try:
            call()
        except realize.RealizeError as e:
            assert "not a forest" in str(e)
        else:
            raise AssertionError("a cycle did not stop the run")


def test_transport_ships_every_zip_at_any_mass_scale():
    """#72 B1: HiGHS's absolute tolerances once let a unit of masses near 1e-9 ship nothing."""
    rng = random.Random(7202)
    for scale in (1e-12, 1e-9, 1.0, 1e9):
        for _ in range(20):
            zs = [f"z{i}" for i in range(8)]
            m = {z: rng.uniform(0.1, 3.0) * scale for z in zs}
            p = {z: (rng.random() * 10, rng.random() * 10) for z in zs}
            c = {"a": (0.0, 0.0), "b": (10.0, 10.0), "c": (0.0, 10.0)}
            w = [rng.uniform(0.1, 1.0) for _ in c]
            a = {j: math.fsum(m.values()) * wi / sum(w) for j, wi in zip(c, w)}
            flow = realize.transport(zs, m, p, c, a)
            for z in zs:
                assert abs(math.fsum(x for (y, _), x in flow.items() if y == z) - m[z]) <= 1e-6 * m[z]
            for j in a:
                assert abs(math.fsum(x for (_, k), x in flow.items() if k == j) - a[j]) <= 1e-6 * a[j]
            owner = realize.round_forest(m, flow, lambda z, j: 0.0)
            assert set(owner) == set(zs)
            _claim3(m, flow, owner, a)


def test_a_small_scale_unit_is_drawn_like_its_unit_scale_twin():
    """#72 B1's repro: the same clipped unit at scale 1 and 1e-9 gets the same map, every ZIP."""
    rng = random.Random(7202)
    zs = [f"z{i}" for i in range(8)]
    base = {z: rng.uniform(0.1, 3.0) for z in zs}
    p = {z: (rng.random() * 10, rng.random() * 10) for z in zs}
    maps = []
    for scale in (1.0, 1e-9):
        inst, xy = _toy({"AL": zs}, list(zip(zs, zs[1:])), {z: base[z] * scale for z in zs}, p,
                        {"AL": "clipped"}, k=3, delta=1.0)
        plan, rep = master.plan(inst, "X")
        d = realize.realize(inst, plan, xy)
        assert set(d.owner) == set(zs)
        assert [c.name for c in audit.audit(realize.to_run(inst, {"X": d}, {"X": rep}))
                if c.status == "fail"] == []
        maps.append(d.owner)
    assert maps[0] == maps[1]


def test_the_tiny_share_example_of_model_md_draws_none_of_v_for_a():
    """MODEL.md §7: z1 whole to B, z2 split A 0.1 / B 0.9, z3 split A 0.1 / C 0.9, centres 0,
    −1.5 and 1.  Rounding from A passes both split ZIPs to the cheaper child: A draws none of v."""
    p = {"z1": (-2.0, 0.0), "z2": (-1.0, 0.0), "z3": (1.0, 0.0)}
    c = {"A": (0.0, 0.0), "B": (-1.5, 0.0), "C": (1.0, 0.0)}
    m = dict.fromkeys(p, 1.0)
    flow = {("z1", "B"): 1.0, ("z2", "A"): 0.1, ("z2", "B"): 0.9, ("z3", "A"): 0.1, ("z3", "C"): 0.9}
    owner = realize.round_forest(m, flow, lambda z, j: m[z] * realize._d2(p[z], c[j]))
    assert owner == {"z1": "B", "z2": "B", "z3": "C"}
    _claim3(m, flow, owner, {"A": 0.2, "B": 1.9, "C": 0.9})


# ------------------------------------------------------------------------------ centres
def test_centres_are_deterministic_and_follow_the_f6_policy():
    """k = 1 is the weighted centroid; k ≥ 2 starts from the heaviest ZIP and reproduces; a copy
    of a multi-unit support takes its border's weighted centroid."""
    zs = [f"v{i}" for i in range(6)]
    p = {z: (float(i), 0.0) for i, z in enumerate(zs)}
    m = {"v0": 1.0, "v1": 0.0, "v2": 2.0, "v3": 1.0, "v4": 5.0, "v5": 1.0}
    assert realize.kmeans(zs, m, p, 1) == [realize.centroid(zs, m, p)]
    two = realize.kmeans(zs, m, p, 2)
    assert two == realize.kmeans(list(reversed(zs)), m, p, 2)
    assert len(set(two)) == 2
    inst, xy = _toy({"AL": zs, "AR": ["a0"]}, list(zip(zs, zs[1:])) + [("v5", "a0")],
                    {**m, "a0": 3.0}, {**p, "a0": (6.0, 0.0)}, {"AL": "free"}, k=2)
    km = {z: (x / 1000.0, y / 1000.0) for z, (x, y) in xy.items()}
    c = realize.centres(inst, "X", "AL", {"AL#1": frozenset({"AL"}),
                                          "AL+AR#1": frozenset({"AL", "AR"})}, km)
    assert c["AL+AR#1"] == (5.0, 0.0)                               # the border is v5 alone
    assert c["AL#1"] == realize.centroid(zs, m, km)


# ------------------------------------------------------------------------------ the map
def _grid(prefix, nx, ny, x0=0.0, mass=1.0):
    zs = {(i, j): f"{prefix}{i:02d}{j}" for i in range(nx) for j in range(ny)}
    edges = [(zs[i, j], zs[i + 1, j]) for i in range(nx - 1) for j in range(ny)]
    edges += [(zs[i, j], zs[i, j + 1]) for i in range(nx) for j in range(ny - 1)]
    return zs, edges, {z: mass for z in zs.values()}, {z: (x0 + i, j) for (i, j), z in zs.items()}


def test_1_no_district_is_starved_of_its_share_of_a_split_unit():
    """#1: the old border-aware seed let one share grow through the whole state and left another
    district 12 of its 370.  Transport and tree rounding keep every district's mass in v within
    one ZIP of its target, however the centres fall."""
    v, ve, vm, vp = _grid("v", 10, 3)
    u, ue, um, up = _grid("u", 3, 3, x0=-3.0)
    w, we, wm, wp = _grid("w", 3, 3, x0=10.0)
    edges = ve + ue + we + [(u[2, j], v[0, j]) for j in range(3)] + [(v[9, j], w[0, j]) for j in range(3)]
    inst, xy = _toy({"AL": list(v.values()), "AR": list(u.values()), "AZ": list(w.values())},
                    edges, {**vm, **um, **wm}, {**vp, **up, **wp}, {"AL": "free"}, k=3, delta=0.9)
    plan = _plan(inst, [({"AR", "AL"}, {"AR": 1.0, "AL": 0.15}), ({"AL"}, {"AL": 0.6}),
                        ({"AZ", "AL"}, {"AZ": 1.0, "AL": 0.25})])
    d = realize.realize(inst, plan, xy)
    for (unit, j), a in d.planned.items():
        assert abs(d.drawn[unit, j] - a) < 1.0 + 1e-6, (unit, j, d.drawn[unit, j], a)
    assert not d.pieces and not d.vanished


def _ct_ny_nj():
    """CT (5 ZIPs of 2) touches NY's east end, NJ (6 of 2) its west end; NY is 20 × 2 unit ZIPs."""
    ny, ne, nm, npt = _grid("ny", 20, 2)
    ct, ce, cm, cp = _grid("ct", 5, 1, x0=20.0, mass=2.0)
    nj, je, jm, jp = _grid("nj", 6, 1, x0=-6.0, mass=2.0)
    edges = ne + ce + je + [(ny[19, 0], ct[0, 0]), (ny[19, 1], ct[0, 0]),
                            (ny[0, 0], nj[5, 0]), (ny[0, 1], nj[5, 0])]
    return _toy({"NY": list(ny.values()), "CT": list(ct.values()), "NJ": list(nj.values())},
                edges, {**nm, **cm, **jm}, {**npt, **cp, **jp}, {"NY": "free"}, k=2, delta=0.3)


def test_7_a_share_too_thin_to_link_its_units_is_a_corridor_piece_not_a_bridge():
    """#7: WH_03 = CT + NJ + 5% of NY.  The master's corridor floor refuses this plan (§4.2); given
    it anyway, the realizer keeps NY's other district whole in its share and reports the end the
    thin share does not reach, CT or NJ, as a corridor piece, rather than bridging it at that
    district's expense."""
    inst, xy = _ct_ny_nj()
    plan = _plan(inst, [({"CT", "NY", "NJ"}, {"CT": 1.0, "NJ": 1.0, "NY": 0.05}),
                        ({"NY"}, {"NY": 0.95})])
    d = realize.realize(inst, plan, xy)
    thin = "CT+NJ+NY#1"
    assert d.drawn["NY", "NY#1"] >= d.planned["NY", "NY#1"] - 1.0 - 1e-9
    cut = [pc for pc in d.pieces if pc.district == thin]
    assert len(cut) == 1 and cut[0].cause == "corridor"
    assert {z[:2] for z in cut[0].zips} in ({"ct"}, {"nj"})         # a whole unit, cut off
    lo, hi = inst.channels["X"].final_band
    assert all(lo - 1e-9 <= x <= hi + 1e-9 for x in d.mass.values()), d.mass


def test_11_contiguity_is_read_on_the_declared_graph_and_a_missing_edge_is_a_graph_gap():
    """#11: the old check read the instance graph, not the declared one.  Here the pieces are
    those `td.audit` finds on the declared graph, and a ZIP the graph leaves without an edge is
    listed as a graph gap."""
    zs = [f"v{i}" for i in range(6)]
    xy_km = {z: (float(i), 0.0) for i, z in enumerate(zs)}
    edges = list(zip(zs[:4], zs[1:4]))                              # v4 and v5 have no edge
    edges.append(("v5", "v3"))                                      # v4 alone is a gap
    inst, xy = _toy({"AL": zs}, edges, dict.fromkeys(zs, 1.0), xy_km, {"AL": "free"}, k=2,
                    delta=0.5)
    plan = _plan(inst, [({"AL"}, {"AL": 0.5}), ({"AL"}, {"AL": 0.5})])
    d = realize.realize(inst, plan, xy)
    gap = [pc for pc in d.pieces if "v4" in pc.zips]
    assert len(gap) == 1 and gap[0].cause == "graph gap"
    graph = {"vertices": zs, "edges": edges}
    run = realize.to_run(inst, {"X": d}, graph=graph)
    contiguity = audit.check_contiguity(run)
    assert contiguity.counts["pieces"] == len(d.pieces)
    assert contiguity.counts["split"] == len({pc.district for pc in d.pieces})
    assert all("unreported" not in item for item in contiguity.items)


def test_zero_mass_zips_are_placed_next_to_their_district():
    """Lemma 3a: a zero-mass ZIP is never in the LP; C4 places it by search from the rounded ZIPs."""
    zs = [f"v{i}" for i in range(9)]
    mass = {z: (0.0 if i % 3 == 1 else 1.0) for i, z in enumerate(zs)}
    inst, xy = _toy({"AL": zs}, list(zip(zs, zs[1:])), mass,
                    {z: (float(i), 0.0) for i, z in enumerate(zs)}, {"AL": "free"}, k=2, delta=0.5)
    d = realize.realize(inst, _plan(inst, [({"AL"}, {"AL": 0.5}), ({"AL"}, {"AL": 0.5})]), xy)
    assert set(d.owner) == set(zs) and not d.pieces


# ------------------------------------------------------------------------------ repair and C10
def _guard_toy(mode):
    """v0–v1–v2–v3 in unit AL, v3 next to u0–u1 in AR (whole).  AL#1 holds v0 and v3, so {v3} is
    detached; AL#2 holds v1, v2 and cannot take it (3 + 1 > 3.5); AR#1 can (2 + 1 ≤ 3.5)."""
    zs = ["v0", "v1", "v2", "v3", "u0", "u1"]
    mass = {"v0": 1.5, "v1": 1.5, "v2": 1.5, "v3": 1.0, "u0": 1.0, "u1": 1.0}
    edges = [("v0", "v1"), ("v1", "v2"), ("v2", "v3"), ("v3", "u0"), ("u0", "u1")]
    inst, _ = _toy({"AL": zs[:4], "AR": zs[4:]}, edges, mass,
                   {z: (float(i), 0.0) for i, z in enumerate(zs)}, {"AL": mode}, k=3, delta=0.4)
    owner = {"v0": "AL#1", "v3": "AL#1", "v1": "AL#2", "v2": "AL#2", "u0": "AR#1", "u1": "AR#1"}
    support = {"AL#1": frozenset({"AL"}), "AL#2": frozenset({"AL"}), "AR#1": frozenset({"AR"})}
    return inst, owner, support


def test_repair_never_moves_a_piece_of_a_clipped_unit_out_of_it():
    inst, owner, support = _guard_toy("clipped")
    assert inst.channels["X"].final_band == (1.5, 3.5)
    assert realize.repair(inst, "X", owner, support) == []
    assert owner["v3"] == "AL#1"
    inst, owner, support = _guard_toy("free")                       # the guard is what stops it
    assert realize.repair(inst, "X", owner, support) == [(("v3",), "AL#1", "AR#1")]
    assert owner["v3"] == "AR#1"


def test_repair_never_moves_a_piece_of_a_whole_unit():
    """A piece holding a ZIP of a whole unit stays, whoever could take it (C16)."""
    inst, owner, support = _guard_toy("clipped")
    owner["u1"] = "AL#2"                    # AL#2 = {AL, AR} holds u1 apart from its main part
    support["AL#2"] = frozenset({"AL", "AR"})
    lo, hi = inst.channels["X"].final_band
    assert lo <= 1.5 + 1.5 <= hi and lo <= 1.0 + 1.0 <= hi          # the band would allow it
    assert realize.repair(inst, "X", owner, support) == [] and owner["u1"] == "AL#2"


def test_repair_skips_a_neighbour_outside_the_channel():
    """A ZIP next to a piece may belong to a unit outside the channel's domain, as a western
    ZIP beside a national unit does: it owns nothing here and is no target."""
    inst, owner, support = _guard_toy("free")
    del owner["u0"], owner["u1"], support["AR#1"]
    assert realize.repair(inst, "X", owner, support) == [] and owner["v3"] == "AL#1"


def _mixed_toy():
    """The #69 round-1 review's case A2: free AL = v0–v1–v2–v3 (mass 2 each), clipped AR =
    u0…u5 (mass 1 each), v3–u0 the only link.  The master's equal-share plan puts v0 and v3 in
    AL#1 apart, and AR#1, which owns part of the clipped AR, is the band-feasible neighbour."""
    v, u = ["v0", "v1", "v2", "v3"], [f"u{i}" for i in range(6)]
    mass = {**dict.fromkeys(v, 2.0), **dict.fromkeys(u, 1.0)}
    edges = list(zip(v, v[1:])) + list(zip(u, u[1:])) + [("v3", "u0")]
    xy_km = {"v0": (0.0, 0.0), "v3": (1.0, 0.0), "v1": (10.0, 0.0), "v2": (11.0, 0.0),
             **{z: (20.0 + i, 0.0) for i, z in enumerate(u)}}
    inst, xy = _toy({"AL": v, "AR": u}, edges, mass, xy_km, {"AL": "free", "AR": "clipped"},
                    k=4, delta=1.0)
    model = master.build(inst, "X")
    x = [0.0] * len(model.cost)
    for s in (frozenset({"AL"}), frozenset({"AR"})):
        x[model.n_col[s]] = 2
        x[model.t_col[next(iter(s)), s]] = 1
    assert master.violations(model, x) == []
    n, t, copies = master.decode(inst, model, x)
    return inst, xy, master.Plan("X", 1.0, n, t, copies, 0.0, {})


def test_repair_gives_no_zip_outside_a_clipped_unit_to_a_district_owning_part_of_it():
    """C16 on the recipient's side: a free piece may not join a district that holds part of a
    clipped unit, or that district owns ZIPs outside its clip.  AR#1 is nearest τ after the move
    (5 against AL#2's 6, τ = 3.5), so only the guard sends {v3} to AL#2 instead."""
    inst, xy, plan = _mixed_toy()
    d = realize.realize(inst, plan, xy)
    assert d.moved == [(("v3",), "AL#1", "AL#2")] and d.owner["v3"] == "AL#2"
    assert audit.check_modes(realize.to_run(inst, {"X": d})).status == "pass"


def test_the_detached_piece_is_the_one_the_audit_detaches_on_a_mass_tie():
    """Isolated a (mass 2) against connected {b, c} (mass 2): the audit keeps the component with
    the smallest ZIP id, so {b, c} is the piece, and its contiguity item names a cause."""
    xy_km = {"a": (0.0, 0.0), "b": (1.0, 0.0), "c": (2.0, 0.0)}
    inst, xy = _toy({"AL": ["a", "b", "c"]}, [("b", "c")], {"a": 2.0, "b": 1.0, "c": 1.0},
                    xy_km, {"AL": "free"}, k=1, delta=1.0)
    d = realize.realize(inst, _plan(inst, [({"AL"}, {"AL": 1.0})]), xy)
    assert [pc.zips for pc in d.pieces] == [("b", "c")]
    item = audit.check_contiguity(realize.to_run(inst, {"X": d})).items
    assert len(item) == 1 and "cause unreported" not in item[0], item


def test_the_expected_cells_come_from_the_input_not_the_map():
    inst, xy, plan = _mixed_toy()
    d = realize.realize(inst, plan, xy)
    assert audit.check_cells(realize.to_run(inst, {"X": d})).status == "pass"
    owner = dict(d.owner)
    del owner["v0"]
    cells = audit.check_cells(realize.to_run(inst, {"X": dataclasses.replace(d, owner=owner)}))
    assert cells.status == "fail" and "cell v0/X: not in the ledger" in cells.items, cells.items


def test_c10_the_clipped_star_is_listed_with_a_cause_and_keeps_both_masses_in_band():
    """C10: a six-ZIP star of unit masses, clipped, K = 2, band [2, 4], μ = 1.  No connected
    in-band split exists; both masses stay inside the final band and the piece has a cause."""
    zs = [f"s{i}" for i in range(6)]
    xy_km = {"s0": (0.0, 0.0), **{f"s{i}": (math.cos(2 * math.pi * i / 5),
                                             math.sin(2 * math.pi * i / 5)) for i in range(1, 6)}}
    inst, xy = _toy({"AL": zs}, [("s0", f"s{i}") for i in range(1, 6)], dict.fromkeys(zs, 1.0),
                    xy_km, {"AL": "clipped"}, k=2, delta=1.0 / 3.0)
    ch = inst.channels["X"]
    assert abs(ch.tau - 3.0) < 1e-12 and supports.margin(inst, "X", frozenset({"AL"})) == 1.0
    d = realize.realize(inst, _plan(inst, [({"AL"}, {"AL": 0.5}), ({"AL"}, {"AL": 0.5})]), xy)
    lo, hi = ch.final_band
    assert all(lo - 1e-9 <= x <= hi + 1e-9 for x in d.mass.values()), d.mass
    assert d.pieces and all(pc.cause in realize.CAUSES for pc in d.pieces)
    assert set(d.owner.values()) <= {"AL#1", "AL#2"}


# ------------------------------------------------------------------------------ the fixture
FIXTURE_DELTA = {"national": 0.27, "WH": 0.19, "FI": 0.29}   # just above the smallest δ with μ_S


def _fixture_51():
    """The 51 scenario on the seed-0 fixture, each channel planned at a δ it can meet (#68 found
    0.10 infeasible there: smallest δ 0.266, 0.181 and 0.283), with the final band at that δ."""
    raw = tomllib.load(open(ts.S51, "rb"))
    for c, dl in FIXTURE_DELTA.items():
        raw["channels"][c]["delta"] = raw["channels"][c]["final_delta"] = dl
    s = spec.parse(raw, ts.S51)
    fx = ts._fixture(tuple(s.fine_channels))
    if fx is None:
        return None
    inst = spec.build(s, fx.extract, ts._reference(), fx.graph)
    ref = ts._reference().set_index("zcta").loc[sorted(inst.units.unit_of)]
    xy = dict(zip(ref.index, zip(ref["x"].astype(float), ref["y"].astype(float))))
    return inst, xy, fx.graph


def test_the_fixture_map_is_connected_or_listed_and_passes_the_audit():
    got = _fixture_51()
    if got is None:
        return
    inst, xy, graph = got
    drawings, reports = {}, {}
    for c in inst.channels:
        p, reports[c] = master.plan(inst, c)
        drawings[c] = realize.realize(inst, p, xy)
    run = realize.to_run(inst, drawings, reports, graph)
    checks = {ck.name: ck for ck in audit.audit(run)}
    assert not [ck.name for ck in checks.values() if ck.status == "fail"], \
        [(ck.name, ck.items[:3]) for ck in checks.values() if ck.status == "fail"]
    pieces = [pc for d in drawings.values() for pc in d.pieces]
    assert all(pc.cause in realize.CAUSES for pc in pieces)
    assert checks["ZIP contiguity"].counts["pieces"] == len(pieces)
    assert all("unreported" not in item for item in checks["ZIP contiguity"].items)
    for c, d in drawings.items():
        print(f"      fixture 51, {c}: {d.counts()}, {len(d.moved)} moved, "
              f"{len(d.vanished)} vanished")


def test_the_module_is_at_most_about_400_lines():
    with open(realize.__file__, encoding="utf-8") as fh:
        assert sum(1 for _ in fh) <= 400
