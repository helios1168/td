"""tools/exp/contig/draw.py (td#109), the contiguity-aware realizer, on toys: a U-shaped split unit
the power diagram draws in two pieces and the realizer draws connected, a share too thin to join
its units proved infeasible, the fixed-target rows, and a zero-opportunity exclave owned by the
district it touches."""
from __future__ import annotations

import importlib.util
import os
import sys

from td import audit, realize

from tests import test_realize as tr

HERE = os.path.dirname(os.path.abspath(__file__))


def _draw():
    if "contig_draw" not in sys.modules:
        spec = importlib.util.spec_from_file_location(
            "contig_draw", os.path.join(HERE, "..", "tools", "exp", "contig", "draw.py"))
        mod = importlib.util.module_from_spec(spec)
        sys.modules["contig_draw"] = mod
        spec.loader.exec_module(mod)
    return sys.modules["contig_draw"]


def _pieces(owner: dict, inst) -> dict:
    """{district: components} of `owner` on the instance's graph, as `td.audit` counts them."""
    return audit.district_pieces(owner, inst.units.zip_adj, {})


def _u_toy(share=0.6, delta=0.1):
    """NY is a U of 13 unit ZCTAs: arms x = 0 and x = 4 (y = 0..4) joined by the bottom row.  CT
    (one ZCTA of mass 2) hangs off the top of the left arm, NJ (one of 4.6) under (3, 0).  The plan
    gives CT+NY `share` of NY and NJ+NY the rest."""
    pts = [(0, y) for y in range(5)] + [(4, y) for y in range(5)] + [(x, 0) for x in (1, 2, 3)]
    name = {q: f"v{q[0]}{q[1]}" for q in pts}
    edges = [(name[a], name[b]) for a in pts for b in pts
             if a < b and abs(a[0] - b[0]) + abs(a[1] - b[1]) == 1]
    xy = {name[q]: (float(q[0]), float(q[1])) for q in pts}
    xy.update({"a0": (0.0, 5.0), "b0": (3.0, -1.0)})
    edges += [("a0", "v04"), ("b0", "v30")]
    mass = dict.fromkeys(xy, 1.0)
    mass.update({"a0": 2.0, "b0": 4.6})
    inst, xym = tr._toy({"NY": [name[q] for q in pts], "CT": ["a0"], "NJ": ["b0"]}, edges, mass,
                        xy, {"NY": "free"}, k=2, delta=delta)
    plan = tr._plan(inst, [({"CT", "NY"}, {"CT": 1.0, "NY": share}),
                           ({"NJ", "NY"}, {"NJ": 1.0, "NY": 1 - share})])
    return inst, xym, plan


def test_the_realizer_draws_connected_where_the_power_diagram_does_not():
    """The issue's fixture: `td.realize` leaves CT+NY a detached piece at the top of NY's right arm;
    the realizer draws both districts connected, every ZCTA owned, masses in the band, optimal."""
    draw = _draw()
    inst, xy, plan = _u_toy()
    power = realize.realize(inst, plan, xy)
    assert any(len(cs) > 1 for cs in _pieces(power.owner, inst).values()), power.owner
    res = draw.draw(inst, plan, xy, log=lambda *_: None)
    assert res.status == "optimal" and res.connected
    d = draw.drawing(inst, plan, res)
    assert set(d.owner) == set(inst.units.unit_of)
    assert all(len(cs) == 1 for cs in _pieces(d.owner, inst).values()), d.owner
    assert d.pieces == []
    lo, hi = inst.channels["X"].band
    assert all(lo - 1e-9 <= x <= hi + 1e-9 for x in d.mass.values()), d.mass
    assert all(g.gap is not None and g.gap <= 1e-9 for g in res.groups)


def test_a_share_too_thin_to_join_its_units_is_proved_infeasible():
    """#7's plan (CT + NJ + 5% of a 20 × 2 NY): joining CT and NJ through NY costs 20 ZCTAs, more
    than the band leaves, so no connected drawing exists under the plan's support; the realizer
    says so as a proof, not a time-out, and the run keeps the ZCTAs undrawn."""
    draw = _draw()
    inst, xy = tr._ct_ny_nj()
    plan = tr._plan(inst, [({"CT", "NY", "NJ"}, {"CT": 1.0, "NJ": 1.0, "NY": 0.05}),
                           ({"NY"}, {"NY": 0.95})])
    res = draw.draw(inst, plan, xy, log=lambda *_: None)
    assert res.status == "infeasible" and not res.connected
    assert res.undrawn


def test_fixed_targets_keep_each_share_within_one_zcta_of_the_plan():
    """With fixed targets each district's mass in NY stays within NY's heaviest ZCTA (1) of its
    planned share, as Claim 3 bounds the power diagram, and the drawing is still connected."""
    draw = _draw()
    inst, xy, plan = _u_toy()
    res = draw.draw(inst, plan, xy, fixed_targets=True, log=lambda *_: None)
    assert res.status == "optimal"
    d = draw.drawing(inst, plan, res)
    for (v, j), a in d.planned.items():
        assert abs(d.drawn[v, j] - a) <= 1.0 + 1e-9, (v, j, d.drawn[v, j], a)
    assert all(len(cs) == 1 for cs in _pieces(d.owner, inst).values())


def test_a_zero_opportunity_exclave_goes_to_the_district_it_touches():
    """A zero-opportunity ZCTA of NJ joined to NJ only through NY (D2's exclave) is owned by a
    district holding NY next to it, never by NJ's own district across the gap: it is free, demands
    connectivity like any ZCTA, and is reported as an exclave split."""
    draw, run = _draw(), _run_module()
    pts = [(0, y) for y in range(5)] + [(4, y) for y in range(5)] + [(x, 0) for x in (1, 2, 3)]
    name = {q: f"v{q[0]}{q[1]}" for q in pts}
    edges = [(name[a], name[b]) for a in pts for b in pts
             if a < b and abs(a[0] - b[0]) + abs(a[1] - b[1]) == 1]
    xy_km = {name[q]: (float(q[0]), float(q[1])) for q in pts}
    xy_km.update({"a0": (0.0, 5.0), "b0": (3.0, -1.0), "bx": (4.0, 5.0)})
    edges += [("a0", "v04"), ("b0", "v30"), ("bx", "v44")]
    mass = dict.fromkeys(xy_km, 1.0)
    mass.update({"a0": 2.0, "b0": 4.6, "bx": 0.0})
    inst, xy = tr._toy({"NY": [name[q] for q in pts], "CT": ["a0"], "NJ": ["b0", "bx"]}, edges,
                       mass, xy_km, {"NY": "free", "NJ": "free"}, k=2, delta=0.1)
    plan = tr._plan(inst, [({"CT", "NY"}, {"CT": 1.0, "NY": 0.6}),
                           ({"NJ", "NY"}, {"NJ": 1.0, "NY": 0.4})])
    res = draw.draw(inst, plan, xy, log=lambda *_: None)
    assert res.connected
    d = draw.drawing(inst, plan, res)
    assert all(len(cs) == 1 for cs in _pieces(d.owner, inst).values()), d.owner
    assert d.owner["bx"] == d.owner["v44"]
    _, _, exclave = draw.split_fixed(inst, plan)
    assert exclave == {"bx"}
    if d.owner["bx"] != "NJ+NY#1":
        assert run.exclave_splits(inst, plan, d.owner, exclave) == [("NJ", d.owner["bx"])]
    # fixed targets count NJ's fixed ZCTA b0 towards NJ+NY's target in NJ: still drawable
    assert draw.draw(inst, plan, xy, fixed_targets=True, log=lambda *_: None).connected


def _run_module():
    if "contig_run" not in sys.modules:
        spec = importlib.util.spec_from_file_location(
            "contig_run", os.path.join(HERE, "..", "tools", "exp", "contig", "run.py"))
        mod = importlib.util.module_from_spec(spec)
        sys.modules["contig_run"] = mod
        spec.loader.exec_module(mod)
    return sys.modules["contig_run"]


def test_single_connector_dependence_is_found():
    """U63: a district whose only link between two halves is a connector edge is listed with it."""
    run = _run_module()
    adj = {"a": {"b"}, "b": {"a", "c"}, "c": {"b", "d"}, "d": {"c"}}
    owner = dict.fromkeys(adj, "J")
    assert run.single_connector(owner, adj, {("b", "c")}) == {"J": ["b-c"]}
    adj["a"].add("d")
    adj["d"].add("a")
    assert run.single_connector(owner, adj, {("b", "c")}) == {}


def test_the_sequential_restriction_draws_the_u_connected_and_never_claims_optimal():
    """`sequential=True` draws one split unit at a time: on the U it is connected, and the channel
    is reported "connected", never "optimal", since a per-unit optimum proves nothing jointly."""
    draw = _draw()
    inst, xy, plan = _u_toy()
    res = draw.draw(inst, plan, xy, sequential=True, log=lambda *_: None)
    assert res.connected and res.status == "connected"
    d = draw.drawing(inst, plan, res)
    assert all(len(cs) == 1 for cs in _pieces(d.owner, inst).values()), d.owner


def _repair_module():
    if "contig_repair" not in sys.modules:
        spec = importlib.util.spec_from_file_location(
            "contig_repair", os.path.join(HERE, "..", "tools", "exp", "contig", "repair.py"))
        mod = importlib.util.module_from_spec(spec)
        sys.modules["contig_repair"] = mod
        spec.loader.exec_module(mod)
    return sys.modules["contig_repair"]


def test_a_window_solve_reconnects_the_power_diagrams_detached_piece():
    """`repair.py`'s window repair: the power diagram's U map, where CT+NY holds a detached piece
    at the top of NY's right arm, is repaired by an exact solve on a window around the piece, the
    rest fixed: every district one piece, masses in the final band, split units and cuts not above
    the drawn map's, and the window's status kept apart from any claim about the map."""
    repair = _repair_module()
    inst, xy, plan = _u_toy()
    power = realize.realize(inst, plan, xy)
    adj, m = inst.units.zip_adj, inst.channels["X"].m
    assert repair.detached(power.owner, adj, m)
    p = {z: (x / 1000.0, y / 1000.0) for z, (x, y) in xy.items()}
    state = dict(inst.units.unit_of)
    before = repair.map_figures(inst, "X", power.owner, state)
    owner, attempts = repair.repair_channel(inst, plan, power.owner, p, state, h0=1,
                                            max_zctas=100, time_limit=60.0, log=lambda *_: None)
    assert repair.detached(owner, adj, m) == []
    assert all(len(cs) == 1 for cs in _pieces(owner, inst).values()), owner
    last = attempts[-1]
    assert last["status"] in ("optimal", "connected") and last["pieces_after"] == 0
    assert last["window_zctas"] < len(owner)
    assert set(owner) == set(power.owner)
    assert all(owner[z] == power.owner[z] for z in owner if z not in repair.window(
        set().union(*(cc for _, cc in repair.detached(power.owner, adj, m))),
        repair.draw.split_fixed(inst, plan)[1], adj, last["h"]))
    lo, hi = inst.channels["X"].final_band
    mass = {}
    for z, j in owner.items():
        mass[j] = mass.get(j, 0.0) + m.get(z, 0.0)
    assert all(lo - 1e-9 <= x <= hi + 1e-9 for x in mass.values()), mass
    after = repair.map_figures(inst, "X", owner, state)
    assert after["split_states"] <= before["split_states"] and after["cuts"] <= before["cuts"]
