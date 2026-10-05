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
    assert last["shape"] == "ball"
    W = repair.ball(repair.detached(power.owner, adj, m), repair.draw.split_fixed(inst, plan)[1],
                    adj, last["h"], 100 // 2)
    assert all(owner[z] == power.owner[z] for z in owner if z not in W)
    lo, hi = inst.channels["X"].final_band
    mass = {}
    for z, j in owner.items():
        mass[j] = mass.get(j, 0.0) + m.get(z, 0.0)
    assert all(lo - 1e-9 <= x <= hi + 1e-9 for x in mass.values()), mass
    after = repair.map_figures(inst, "X", owner, state)
    assert after["split_states"] <= before["split_states"] and after["cuts"] <= before["cuts"]


def test_the_flow_window_reconnects_the_same_piece():
    """With `flow` the window model also holds each district connected by a single-commodity
    flow from its root body; on the U it reconnects the power diagram's piece as the cut loop does."""
    repair = _repair_module()
    inst, xy, plan = _u_toy()
    power = realize.realize(inst, plan, xy)
    adj, m = inst.units.zip_adj, inst.channels["X"].m
    p = {z: (x / 1000.0, y / 1000.0) for z, (x, y) in xy.items()}
    state = dict(inst.units.unit_of)
    owner, attempts = repair.repair_channel(inst, plan, power.owner, p, state, h0=1,
                                            max_zctas=100, time_limit=60.0, log=lambda *_: None,
                                            flow=True)
    assert repair.detached(owner, adj, m) == []
    assert attempts[-1]["flow"] and attempts[-1]["status"] in ("optimal", "connected")


def _over_band_toy():
    """AL (one ZCTA of 12) | AR (w of 1, r of 8) | CA (one of 9) on a line, K 3, τ 10, final band
    (9, 11): AL#1 is above the band and wholly outside a window {w}."""
    edges = [("a", "w"), ("w", "r"), ("r", "c")]
    xy = {"a": (0.0, 0.0), "w": (1.0, 0.0), "r": (2.0, 0.0), "c": (3.0, 0.0)}
    mass = {"a": 12.0, "w": 1.0, "r": 8.0, "c": 9.0}
    inst, _ = tr._toy({"AL": ["a"], "AR": ["w", "r"], "CA": ["c"]}, edges, mass, xy, k=3,
                      delta=0.1, final_delta=0.1)
    plan = tr._plan(inst, [({"AL"}, {"AL": 1.0}), ({"AR"}, {"AR": 1.0}), ({"CA"}, {"CA": 1.0})])
    owner = {"a": "AL#1", "w": "AR#1", "r": "AR#1", "c": "CA#1"}
    return inst, plan, owner, {z: (x, y) for z, (x, y) in xy.items()}


def test_a_window_is_infeasible_when_a_fixed_district_is_already_above_the_band():
    """Review of 35e038f8, P1: the sequential clamp (a district past the band takes nothing more)
    let a window next to AL#1, fixed at 12 against (9, 11), report "optimal" as if the band held.
    In repair the band row keeps its negative upper residual, so the window is infeasible, and the
    attempt records list the districts outside the band."""
    repair = _repair_module()
    inst, plan, owner, p = _over_band_toy()
    assert inst.channels["X"].final_band == (9.0, 11.0)
    g = repair.solve_window(inst, plan, owner, {"w"}, p, 30.0, True, log=lambda *_: None)
    assert g.status == "infeasible", (g.status, g.note)
    assert "AL#1" in g.note
    state = dict(inst.units.unit_of)
    assert repair.map_figures(inst, "X", owner, state)["outside_band"] == ["AL#1"]


def test_a_source_drawn_by_other_plans_is_rejected():
    """Review of 35e038f8, P1: the ledger's ids read back to copies only when the source's
    districts.csv lists the plan's copies under the same ids, names and supports."""
    import tempfile
    repair = _repair_module()
    inst, plan, _, _ = _over_band_toy()
    rows = ["channel,district,district_name,copy,support,planned_mass,drawn_mass,pieces",
            "X,X_01,,AL#1,AL,12,12,0", "X,X_02,,AR#1,AR,9,9,0", "X,X_03,,CA#1,CA,9,9,0"]
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "districts.csv")
        with open(path, "w") as fh:
            fh.write("\n".join(rows) + "\n")
        assert repair.check_source(path, {"X": plan}) == []
        other = tr._plan(inst, [({"AL", "AR"}, {"AL": 1.0, "AR": 1.0}), ({"CA"}, {"CA": 1.0}),
                                ({"CA"}, {"CA": 0.0})])
        bad = repair.check_source(path, {"X": other})
        assert bad and any("AL+AR#1" in b for b in bad)
        assert repair.check_source(path, {}) == ["X: in districts.csv, not in the plans"]


def test_the_band_remedy_tries_a_wider_band_after_an_infeasible_one():
    """Review of 35e038f8, P2: #7's thin share is infeasible at the plan's δ = 0.3 (CT + NJ + a
    20-ZCTA path through NY is 42 against 40.3) and drawable at 0.4; the joint `band` remedy goes on
    to the wider band instead of stopping at the narrower proof."""
    draw = _draw()
    inst, xy = tr._ct_ny_nj()
    plan = tr._plan(inst, [({"CT", "NY", "NJ"}, {"CT": 1.0, "NJ": 1.0, "NY": 0.05}),
                           ({"NY"}, {"NY": 0.95})])
    res = draw.draw(inst, plan, xy, wider=(0.4,), log=lambda *_: None)
    assert res.connected, [g.tried for g in res.groups]
    tried = res.groups[0].tried
    assert [t["status"] for t in tried if t["delta"] == 0.3 and not t["dag"]] == ["infeasible"]
    assert any(t["delta"] == 0.4 and t["status"] in ("optimal", "connected") for t in tried)


def test_the_report_gives_a_repaired_channel_the_repairs_band():
    """Review of 35e038f8, P1: a channel `repair.py` redrew is reported at the repair's final band
    δ, not the source drawing's δ needed."""
    import json
    import tempfile
    spec = importlib.util.spec_from_file_location(
        "contig_report", os.path.join(HERE, "..", "tools", "exp", "contig", "report.py"))
    report = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(report)
    chan = {"groups": [], "plan_delta": 0.02, "connected": True, "status": "connected",
            "share_only": [], "exclave_splits": [], "single_connector": {}}
    doc = {"scenario": "toy", "arm": "arm1+repair", "m1": {"status": "pass", "summary": ""},
           "channels": {"A": {**chan, "repair": [{"status": "optimal"}],
                              "source_group_delta_needed": 0.02,
                              "repair_band": {"delta": 0.1, "worst_dev": 0.087}},
                        "B": {**chan, "repair": [], "group_delta_needed": 0.05}}}
    with tempfile.TemporaryDirectory() as tmp:
        for name, body in (("contig.json", json.dumps(doc)),
                           ("run.json", json.dumps({"spec": "", "channels": {"A": {"k": 2},
                                                                             "B": {"k": 2}}})),
                           ("ledger.csv", "model_channel,state,district\n"),
                           ("scorecard.md", ""),
                           ("districts.csv", "channel,drawn_mass\nA,9\nA,11\nB,10\nB,10\n")):
            with open(os.path.join(tmp, name), "w") as fh:
                fh.write(body)
        a, b = report.rows(tmp)
        assert (a["delta_needed"], a["repair_delta"]) == (None, 0.1)
        assert (b["delta_needed"], b["repair_delta"]) == (0.05, None)
        assert "| 0.1 (repair) |" in report.table([a]) and "| 0.05 |" in report.table([b])


def _least_border(inst, plan, border) -> float:
    """The least border between the U toy's two districts over every connected drawing in the band,
    by trying every split of NY's 13 ZCTAs (the definition of the border term's optimum)."""
    units, ch = inst.units, inst.channels["X"]
    adj, m = units.zip_adj, ch.m
    ny = sorted(units.zips["NY"])
    names = {cp.support and next(iter(cp.support - {"NY"})): cp.name for cp in plan.copies}
    lo, hi = ch.tau * (1 - plan.delta), ch.tau * (1 + plan.delta)
    best = float("inf")
    for mask in range(2 ** len(ny)):
        owner = {"a0": names["CT"], "b0": names["NJ"]}
        owner.update({z: names["CT"] if mask >> i & 1 else names["NJ"] for i, z in enumerate(ny)})
        mass = {}
        for z, j in owner.items():
            mass[j] = mass.get(j, 0.0) + m.get(z, 0.0)
        if not all(lo - 1e-9 <= x <= hi + 1e-9 for x in mass.values()):
            continue
        if any(len(cs) > 1 for cs in _pieces(owner, inst).values()):
            continue
        best = min(best, sum(border.get((a, b), 1.0) for a in owner for b in adj[a]
                             if a < b and owner[a] != owner[b]))
    return best


def test_the_shape_term_draws_the_least_border_between_districts():
    """#121: the shape tier charges the border between districts (each edge 1 km without a border
    table, the bottom row 5 km with one), so the drawing's reported `border_km` is the least over
    every connected drawing in the band, and the moment tie-break is reported beside it."""
    draw = _draw()
    inst, xy, plan = _u_toy()
    adj = inst.units.zip_adj
    bottom = {(a, b): 5.0 if a[1:] in ("00", "10", "20", "30") and b[1:] in ("10", "20", "30", "40")
              and a[2] == b[2] == "0" else 1.0 for a in adj for b in adj[a] if a < b}
    assert sorted(e for e, x in bottom.items() if x == 5.0) == [
        ("v00", "v10"), ("v10", "v20"), ("v20", "v30"), ("v30", "v40")]
    for border in (None, bottom):
        res = draw.draw(inst, plan, xy, border=border, log=lambda *_: None)
        assert res.status == "optimal" and res.connected
        [g] = res.groups
        assert abs(g.border_km - _least_border(inst, plan, border or {})) < 1e-9, (border, g.owner)
        assert g.moment is not None and g.report()["border_km"] == g.border_km


def _finger_toy():
    """NY is a 4 × 3 grid of free ZCTAs (mass 1, 1 km² each); CT's a0 (mass 2) touches the left
    column and NJ's b0 (4.6) the right one, every edge 6 km of border.  The drawing gives CT the
    two left columns and (2, 0), a finger on one 6 km edge holding 1/8 of CT's land: a neck (#121)."""
    pts = [(x, y) for x in range(4) for y in range(3)]
    name = {q: f"v{q[0]}{q[1]}" for q in pts}
    edges = [(name[a], name[b]) for a in pts for b in pts
             if a < b and abs(a[0] - b[0]) + abs(a[1] - b[1]) == 1]
    edges += [("a0", name[0, y]) for y in range(3)] + [("b0", name[3, y]) for y in range(3)]
    xy = {name[q]: (float(q[0]), float(q[1])) for q in pts}
    xy.update({"a0": (-1.0, 1.0), "b0": (4.0, 1.0)})
    mass = dict.fromkeys(xy, 1.0)
    mass.update({"a0": 2.0, "b0": 4.6})
    inst, xym = tr._toy({"NY": [name[q] for q in pts], "CT": ["a0"], "NJ": ["b0"]}, edges, mass,
                        xy, {"NY": "free"}, k=2, delta=0.15, final_delta=0.15)
    plan = tr._plan(inst, [({"CT", "NY"}, {"CT": 1.0, "NY": 7 / 12}),
                           ({"NJ", "NY"}, {"NJ": 1.0, "NY": 5 / 12})])
    ct, nj = sorted(cp.name for cp in plan.copies)
    owner = {z: nj for z in xy}
    owner.update({z: ct for z in ["a0", "v00", "v01", "v02", "v10", "v11", "v12", "v20"]})
    polygon = {"vertices": sorted(xy), "edges": edges, "state": dict(inst.units.unit_of),
               "border": {tuple(sorted(e)): 6000.0 for e in edges}, "connectors": [],
               "aland": dict.fromkeys(xy, 1e6)}
    return inst, xym, plan, owner, polygon, ct


def test_the_window_repair_removes_a_neck_with_the_border_term():
    """#121: repair treats a neck like a detached piece, a window around the side it cuts off
    re-solved with the border term; the finger goes and no district keeps a neck."""
    repair = _repair_module()
    inst, xy, plan, owner, polygon, ct = _finger_toy()
    m = inst.channels["X"].m
    ng = audit.NeckGraph(polygon)
    [(j, side, nk)] = repair.necks(owner, m, ng)
    assert (j, set(side), nk.width_km) == (ct, {"v20"}, 6.0)
    p = {z: (x / 1000.0, y / 1000.0) for z, (x, y) in xy.items()}
    border = repair.draw.border_km(polygon)
    fixed, attempts = repair.repair_channel(inst, plan, owner, p, dict(inst.units.unit_of), h0=1,
                                            max_zctas=100, time_limit=60.0, log=lambda *_: None,
                                            keep_support=True, border=border, ng=ng)
    assert repair.necks(fixed, m, ng) == [] and repair.detached(fixed, inst.units.zip_adj, m) == []
    kept = [r for r in attempts if r.get("kind") == "neck" and r["kept"]]
    assert kept and kept[0]["necks_before"] > kept[0]["necks_after"]
    assert repair.draw.cut_border(fixed, inst.units.zip_adj, border) \
        < repair.draw.cut_border(owner, inst.units.zip_adj, border)
    lo, hi = inst.channels["X"].final_band
    mass = {}
    for z, k in fixed.items():
        mass[k] = mass.get(k, 0.0) + m.get(z, 0.0)
    assert all(lo - 1e-9 <= x <= hi + 1e-9 for x in mass.values()), mass
