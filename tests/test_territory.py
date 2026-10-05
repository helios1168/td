"""td.territory: the territory pass after the realizer (#116), on toy maps shaped as #114 builds
the instance, every ZCTA of the footprint a ZIP of a unit whether it has opportunity or not.

Each toy names its ZIPs so that breadth-first growth alone gives the contested ZIP to the wrong
district; the join step must then win it back.  States are the units, so a unit crossing is a
state crossing.
"""
from __future__ import annotations

from td import audit, realize, territory

from tests import test_realize as tr


def _map(inst, plan, owner: dict):
    """A `realize.Drawing` of channel X with `owner`, the plan's masses, and no pieces yet."""
    ch = inst.channels["X"]
    planned = {(v, c.name): c.mass[v] for c in plan.copies for v in c.support}
    drawn = dict.fromkeys(planned, 0.0)
    mass = {c.name: 0.0 for c in plan.copies}
    for z, j in owner.items():
        if (inst.units.unit_of[z], j) in drawn:
            drawn[inst.units.unit_of[z], j] += ch.m.get(z, 0.0)
        mass[j] += ch.m.get(z, 0.0)
    return realize.Drawing("X", dict(owner), mass, planned, drawn, [])


def test_a_zero_opportunity_zcta_joins_two_pieces_of_one_district():
    """b1 and b3 hold J's opportunity in AL, a1 and a2 K's; b2 has none and touches b1, b3 and a1.
    Growth reaches b2 from a1 first (the smallest ID), leaving J in two pieces; the join step gives
    b2 to J, since K keeps one piece without it."""
    zs = ["a1", "a2", "b1", "b2", "b3"]
    mass = {"a1": 1.0, "a2": 1.0, "b1": 1.0, "b2": 0.0, "b3": 1.0}
    xy = {"a1": (1.0, 1.0), "a2": (2.0, 1.0), "b1": (0.0, 0.0), "b2": (1.0, 0.0), "b3": (2.0, 0.0)}
    edges = [("b1", "b2"), ("b2", "b3"), ("b2", "a1"), ("a1", "a2")]
    inst, xy_m = tr._toy({"AL": zs}, edges, mass, xy, {"AL": "free"}, k=2)
    plan = tr._plan(inst, [({"AL"}, {"AL": 0.5}), ({"AL"}, {"AL": 0.5})])
    j, k = (c.name for c in plan.copies)
    d = _map(inst, plan, {"b1": j, "b3": j, "a1": k, "a2": k, "b2": k})
    grown = {z: o for z, o in d.owner.items() if mass[z] > 0}
    territory.grow(grown, {"b2"}, inst.units.zip_adj)
    assert grown["b2"] == k                                 # growth alone splits J
    done = territory.own_territory(inst, plan, d, xy_m, dict.fromkeys(zs, "AL"))
    assert d.owner == {"a1": k, "a2": k, "b1": j, "b2": j, "b3": j}
    assert done["joined"] == ["b2"] and done["zero"] == 1 and d.pieces == []
    assert done["cross_state"] == [] and done["unreached"] == []


def test_a_zero_opportunity_zcta_reached_only_across_a_state_is_held_there_and_listed():
    """r1 is AR's and has no opportunity; its only edge is to J's a2 in AL.  K holds all of AR's
    opportunity, but no path inside AR reaches r1, so J holds it across the state line: a split
    (owner, 2026-10-05), listed by the pass and by the audit's mode check, which it does not fail.
    (AR is free: a whole unit that is not ZIP-connected stops the run before any plan, OQ6.)"""
    unit_zips = {"AL": ["a1", "a2"], "AZ": ["c1", "c2"], "AR": ["r1", "r2"]}
    mass = {"a1": 1.0, "a2": 1.0, "c1": 0.5, "c2": 0.5, "r1": 0.0, "r2": 1.0}
    xy = {"a1": (0.0, 0.0), "a2": (1.0, 0.0), "c1": (2.0, 0.0), "c2": (3.0, 0.0),
          "r1": (1.0, -1.0), "r2": (2.0, -1.0)}
    edges = [("a1", "a2"), ("a2", "c1"), ("c1", "c2"), ("a2", "r1"), ("c1", "r2")]
    inst, xy_m = tr._toy(unit_zips, edges, mass, xy, {"AR": "free"}, k=2)
    plan = tr._plan(inst, [({"AL"}, {"AL": 1.0}), ({"AZ", "AR"}, {"AZ": 1.0, "AR": 1.0})])
    j, k = (c.name for c in plan.copies)
    d = _map(inst, plan, {"a1": j, "a2": j, "c1": k, "c2": k, "r1": k, "r2": k})
    state = {z: u for u, zs in unit_zips.items() for z in zs}
    done = territory.own_territory(inst, plan, d, xy_m, state)
    assert d.owner["r1"] == j and done["cross_state"] == [("r1", j)]
    assert done["by_stage"] == {"unit": 0, "state": 0, "across a state": 1, "nearest, detached": 0}
    assert d.pieces == []
    modes = audit.check_modes(realize.to_run(inst, {"X": d}))
    assert modes.status == "listed", modes.items
    assert modes.items == [f"X/AR: 1 zero-opportunity ZCTAs (r1) owned by X:{j}, which holds no "
                           "opportunity there"]


def test_a_dropped_unit_is_owned_and_an_unreached_zcta_stays_a_detached_piece():
    """AR has no opportunity, so the master drops it, but it is in X's domain: the pass owns it
    from AL.  i1 is AL's with no edge at all: the nearest owned ZCTA's district takes it and it
    stays a detached piece for M1 to fail.  Opportunity never moves."""
    unit_zips = {"AL": ["a1", "a2", "a3", "i1"], "AR": ["r1", "r2"]}
    mass = {"a1": 1.0, "a2": 0.0, "a3": 1.0, "i1": 0.0, "r1": 0.0, "r2": 0.0}
    xy = {"a1": (0.0, 0.0), "a2": (1.0, 0.0), "a3": (2.0, 0.0), "i1": (9.0, 9.0),
          "r1": (3.0, 0.0), "r2": (4.0, 0.0)}
    edges = [("a1", "a2"), ("a2", "a3"), ("a3", "r1"), ("r1", "r2")]
    inst, xy_m = tr._toy(unit_zips, edges, mass, xy, {"AL": "free"}, k=2)
    assert "AR" in inst.channels["X"].dropped_units and "AR" not in inst.channels["X"].units
    assert territory.footprint(inst, "X") == {"a1", "a2", "a3", "i1", "r1", "r2"}
    plan = tr._plan(inst, [({"AL"}, {"AL": 0.5}), ({"AL"}, {"AL": 0.5})])
    j, k = (c.name for c in plan.copies)
    d = _map(inst, plan, {"a1": j, "a3": k})                # the realizer owns only AL's ZIPs
    state = {z: u for u, zs in unit_zips.items() for z in zs}
    done = territory.own_territory(inst, plan, d, xy_m, state)
    assert d.owner["a1"] == j and d.owner["a3"] == k
    assert set(d.owner) == territory.footprint(inst, "X")
    assert d.owner["r1"] == d.owner["r2"] == k and ("r1", k) in done["cross_state"]
    assert done["unreached"] == ["i1"] and d.owner["i1"] == k        # a3 is nearest
    assert [(p.district, p.zips) for p in d.pieces] == [(k, ("i1",))]


def test_a_join_that_cuts_a_donor_in_two_is_refused():
    """Review of #116: J holds c, d and e, three pieces that meet only at z, which K holds at
    zero opportunity between its a and b.  Claiming z joins J (3 pieces to 1) and lowers the
    total (4 to 3), but cuts K in two, so the join step refuses it."""
    adj = {"z": {"a", "b", "c", "d", "e"}, **{y: {"z"} for y in "abcde"}}
    owner = {"a": "K", "b": "K", "z": "K", "c": "J", "d": "J", "e": "J"}
    m = {y: 1.0 for y in "abcde"} | {"z": 0.0}
    before = dict(owner)
    claimed = territory.join(owner, {"z"}, adj, dict.fromkeys(adj, "U"),
                             {"J": {"U"}, "K": {"U"}}, m)
    assert claimed == [] and owner == before
