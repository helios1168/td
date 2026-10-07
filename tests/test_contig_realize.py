"""tools/exp/contig/draw.py (td#109), the contiguity-aware realizer, on toys: a U-shaped split unit
the power diagram draws in two pieces and the realizer draws connected, a share too thin to join
its units proved infeasible, the fixed-target rows, and a zero-opportunity exclave owned by the
district it touches."""
from __future__ import annotations

import dataclasses
import importlib.util
import os
import sys

from td import audit, master, realize

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


def test_a_child_of_a_diagnostic_folder_is_diagnostic():
    """Sol's review of #121 (P1): `run.write_manifest` marks a run whose parent is diagnostic
    diagnostic too, so a repair of a `--diag-final-delta` folder is never a deliverable."""
    import json
    import tempfile
    from td import audit
    run = _repair_module().run
    with tempfile.TemporaryDirectory() as tmp:
        spec = os.path.join(tmp, "spec.toml")
        with open(spec, "w") as fh:
            fh.write("")
        parent, plain, child = (os.path.join(tmp, n) for n in ("diag", "plain", "child"))
        run.write_manifest(parent, "contig_repair", spec, spec, {}, diagnostic=True,
                           diagnostic_band=0.15, diagnostic_label="diagnostic band ±15%")
        run.write_manifest(plain, "contig_repair", spec, spec, {})
        run.write_manifest(child, "contig_repair", spec, spec, {}, parent=parent)
        assert audit.diagnostic(parent) == {"band": 0.15, "label": "diagnostic band ±15%"}
        assert audit.diagnostic(plain) is None
        assert audit.diagnostic(child) == {"band": 0.15, "label": f"child of the diagnostic folder {parent}"}
        assert audit.diagnostic(os.path.join(tmp, "grandchild")) is None
        run.write_manifest(os.path.join(tmp, "grandchild"), "contig_repair", spec, spec, {}, parent=child)
        assert audit.diagnostic(os.path.join(tmp, "grandchild"))["band"] == 0.15
        with open(os.path.join(child, "manifest.json")) as fh:
            assert json.load(fh)["diagnostic"] is True


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


def _bridge_toy():
    """CT's a0 and NJ's b0 (mass 2 each) and NY's f and g (mass 1, free); every ZCTA 1 km², the
    final band (2.55, 3.45) gives each district one of f, g.  Borders: a0-f 1 km, a0-g 30, f-g 5,
    f-b0 12, g-b0 50.  CT with f is the least border (47 km against 56) but reaches f through
    1 km, a neck; CT with g has none."""
    edges = [("a0", "f"), ("a0", "g"), ("f", "g"), ("b0", "f"), ("b0", "g")]
    km = {("a0", "f"): 1.0, ("a0", "g"): 30.0, ("f", "g"): 5.0, ("b0", "f"): 12.0, ("b0", "g"): 50.0}
    xy = {"a0": (0.0, 0.0), "f": (1.0, 1.0), "g": (1.0, -1.0), "b0": (2.0, 0.0)}
    mass = {"a0": 2.0, "b0": 2.0, "f": 1.0, "g": 1.0}
    inst, xym = tr._toy({"NY": ["f", "g"], "CT": ["a0"], "NJ": ["b0"]}, edges, mass, xy,
                        {"NY": "free"}, k=2, delta=0.15, final_delta=0.15)
    plan = tr._plan(inst, [({"CT", "NY"}, {"CT": 1.0, "NY": 0.5}),
                           ({"NJ", "NY"}, {"NJ": 1.0, "NY": 0.5})])
    ct, nj = sorted(cp.name for cp in plan.copies)
    polygon = {"vertices": sorted(xy), "edges": edges, "state": dict(inst.units.unit_of),
               "border": {e: 1000.0 * x for e, x in km.items()}, "connectors": [],
               "aland": dict.fromkeys(xy, 1e6)}
    owner = {"a0": ct, "f": ct, "b0": nj, "g": nj}
    return inst, xym, plan, owner, polygon, ct, nj


def test_a_neck_cut_removes_the_neck_the_border_term_keeps():
    """#121: on the bridge toy the window's border-term optimum is CT through the 1 km edge, a
    neck; the neck-aware window (`ng`) cuts it (`draw.NeckCut`) and its optimum, over the
    cut-augmented model, is CT with g: no neck, in the band."""
    repair = _repair_module()
    inst, xy, plan, owner, polygon, ct, nj = _bridge_toy()
    m = inst.channels["X"].m
    ng = audit.NeckGraph(polygon)
    [(j, _, nk)] = repair.necks(owner, m, ng)
    assert (j, nk.width_km) == (ct, 1.0)
    p = {z: (x / 1000.0, y / 1000.0) for z, (x, y) in xy.items()}
    border = repair.draw.border_km(polygon)
    W = {"f", "g"}
    plain = repair.solve_window(inst, plan, owner, W, p, 30.0, True, log=lambda *_: None,
                                keep_support=True, repairing={ct}, border=border)
    assert plain.status == "optimal" and plain.owner == {"f": ct, "g": nj}, plain.owner
    assert plain.neck_cuts == 0
    aware = repair.solve_window(inst, plan, owner, W, p, 30.0, True, log=lambda *_: None,
                                keep_support=True, repairing={ct}, border=border, ng=ng)
    assert aware.status == "optimal" and aware.owner == {"f": nj, "g": ct}, (aware.owner, aware.note)
    assert aware.neck_cuts >= 1 and aware.neck_exempt == []
    assert repair.necks({**owner, **aware.owner}, m, ng) == []
    assert abs(aware.border_km - 56.0) < 1e-9 and abs(plain.border_km - 47.0) < 1e-9


def test_a_neck_cut_holds_for_every_drawing_without_a_neck():
    """#121: every `draw.NeckCut` built from a necked drawing of the finger toy's 12 free ZCTAs,
    its borders drawn in 3-30 km and its land in 0.3-3 km² (seeded), holds on every drawing in
    which both districts are connected and have no neck (the cut's validity, by enumeration), and
    each is broken by the drawing it was built from."""
    import random
    repair = _repair_module()
    inst, _, plan, owner, polygon, ct = _finger_toy()
    rnd = random.Random(121)
    polygon["border"] = {e: 1000.0 * rnd.uniform(3.0, 30.0) for e in sorted(polygon["border"])}
    polygon["aland"] = {z: 1e6 * rnd.uniform(0.3, 3.0) for z in sorted(polygon["aland"])}
    nj = next(cp.name for cp in plan.copies if cp.name != ct)
    m = inst.channels["X"].m
    ng = audit.NeckGraph(polygon)
    W = sorted(z for z in owner if z.startswith("v"))
    adj = {z: repair._nbrs(ng, z) for z in owner}
    cuts, clean = [], []
    for mask in range(1, 2 ** len(W) - 1):
        own = {z: ct if mask >> i & 1 else nj for i, z in enumerate(W)}
        full = {**owner, **own}
        sides = [{z for z, k in full.items() if k == j} for j in (ct, nj)]
        if any(len(repair.draw.components(s, adj)) > 1 for s in sides):
            continue
        built, labels = repair.neck_cuts("X", owner, set(W), m, ng, own, {ct, nj})
        if labels:
            assert built and not any(c.holds(own) for c in built), labels
            cuts += built
        else:
            clean.append(own)
    assert len(cuts) > 100 and len(clean) > 30, (len(cuts), len(clean))
    for c in cuts:
        assert all(c.holds(own) for own in clean), c.label


def test_replan_bans_a_pair_in_a_copy_of_the_spec():
    """#122: `replan.banned_text` adds the banned pairs to each channel's forbid_pairs, moves only
    the listed channels' δ, leaves the other sections alone and refuses a second forbid_pairs."""
    import tomllib
    spec = importlib.util.spec_from_file_location(
        "contig_replan", os.path.join(HERE, "..", "tools", "exp", "contig", "replan.py"))
    replan = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(replan)
    src = ('[scenario]\nname = "toy"\n\n[channels.A]\nmargin = false\nk = 2\ndelta = 0.02\n\n'
           '[channels.B]\nmargin = false\nk = 3\ndelta = 0.03\n\n[national]\nchannel = "A"\n')
    pairs = [replan.pair("NJ-CT"), replan.pair("MA-NJ")]
    assert pairs == [("CT", "NJ"), ("MA", "NJ")]
    doc = tomllib.loads(replan.banned_text(src, pairs, deltas={"B": 0.0612}))
    assert doc["channels"]["A"]["forbid_pairs"] == [["CT", "NJ"], ["MA", "NJ"]]
    assert doc["channels"]["B"]["forbid_pairs"] == [["CT", "NJ"], ["MA", "NJ"]]
    assert (doc["channels"]["A"]["delta"], doc["channels"]["B"]["delta"]) == (0.02, 0.0612)
    assert doc["national"] == {"channel": "A"} and doc["scenario"]["name"] == "toy"
    only = tomllib.loads(replan.banned_text(src, pairs, channels=["B"]))
    assert "forbid_pairs" not in only["channels"]["A"] and only["channels"]["B"]["forbid_pairs"]
    try:
        replan.banned_text(replan.banned_text(src, pairs), pairs)
    except ValueError:
        pass
    else:
        raise AssertionError("a second forbid_pairs was accepted")
    assert replan.pair("FI:UT-AZ") == ("FI", ("AZ", "UT"))
    one = tomllib.loads(replan.banned_text(src, pairs, extra={"A": [("AZ", "UT")]}))
    assert one["channels"]["A"]["forbid_pairs"] == [["AZ", "UT"], ["CT", "NJ"], ["MA", "NJ"]]
    assert one["channels"]["B"]["forbid_pairs"] == [["CT", "NJ"], ["MA", "NJ"]]


def test_replan_replaces_a_channel_split_list_in_a_copy_of_the_spec():
    """#122 round 3: `--free A=CA,NY` replaces A's split list, adds one to a section without it,
    drops it for an empty list, leaves B's alone and refuses a channel with no section; `--widen`
    (`final_deltas`) sets or replaces a channel's final_delta and leaves the others alone."""
    import tomllib
    spec = importlib.util.spec_from_file_location(
        "contig_replan", os.path.join(HERE, "..", "tools", "exp", "contig", "replan.py"))
    replan = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(replan)
    src = ('[scenario]\nname = "toy"\n\n[channels.A]\nk = 2\nfree = ["CA", "FL", "NY", "PA"]\n'
           'delta = 0.02\n\n[channels.B]\nk = 3\nfree = ["OH"]\n\n[channels.C]\nk = 1\n\n'
           '[national]\nchannel = "A"\n')
    assert replan.free_list("A=CA,NY") == ("A", ("CA", "NY"))
    assert replan.free_list("C=") == ("C", ())
    doc = tomllib.loads(replan.banned_text(src, [], free={"A": ("CA", "NY"), "C": ("TX",)}))
    assert doc["channels"]["A"] == {"k": 2, "free": ["CA", "NY"], "delta": 0.02}
    assert doc["channels"]["B"]["free"] == ["OH"] and doc["channels"]["C"]["free"] == ["TX"]
    assert "forbid_pairs" not in doc["channels"]["A"] and doc["national"] == {"channel": "A"}
    none = tomllib.loads(replan.banned_text(src, [replan.pair("CT-NJ")], free={"B": ()}))
    assert "free" not in none["channels"]["B"]
    assert none["channels"]["B"]["forbid_pairs"] == [["CT", "NJ"]]
    try:
        replan.banned_text(src, [], free={"D": ("CA",)})
    except ValueError:
        pass
    else:
        raise AssertionError("a split list for a channel with no section was accepted")
    wide = tomllib.loads(replan.banned_text(src, [], deltas={"A": 0.1272},
                                            final_deltas={"A": replan.WIDE_FINAL_DELTA, "C": 0.15}))
    assert (wide["channels"]["A"]["delta"], wide["channels"]["A"]["final_delta"]) == (0.1272, 0.15)
    assert wide["channels"]["C"]["final_delta"] == 0.15 and "final_delta" not in wide["channels"]["B"]
    lined = src.replace("delta = 0.02\n", "delta = 0.02\nfinal_delta = 0.1\n")
    assert tomllib.loads(replan.banned_text(lined, [], final_deltas={"A": 0.15})
                         )["channels"]["A"]["final_delta"] == 0.15


def test_an_opened_unit_lets_the_repair_split_a_whole_unit():
    """#122: a neck inside a unit held whole (a1 hangs off a0 by 1 km) is out of every arm-1
    window's reach; `--open-units CT` lets the window give a1 to Q, across 30 km, one more split.
    a0 holds two thirds of P's land, so a1 is the smaller side, the part M1 cuts off."""
    repair = _repair_module()
    edges = [("a0", "a1"), ("a0", "b0"), ("a1", "b0")]
    km = {("a0", "a1"): 1.0, ("a0", "b0"): 20.0, ("a1", "b0"): 30.0}
    xy = {"a0": (0.0, 0.0), "a1": (1.0, 0.0), "b0": (0.5, 1.0)}
    mass = {"a0": 2.0, "a1": 1.0, "b0": 2.0}
    inst, xym = tr._toy({"CT": ["a0", "a1"], "NJ": ["b0"]}, edges, mass, xy, {}, k=2, delta=0.2,
                        final_delta=0.2)
    plan = tr._plan(inst, [({"CT"}, {"CT": 1.0}), ({"NJ"}, {"NJ": 1.0})])
    pa, qb = sorted(cp.name for cp in plan.copies)
    polygon = {"vertices": sorted(xy), "edges": edges, "state": dict(inst.units.unit_of),
               "border": {e: 1000.0 * x for e, x in km.items()}, "connectors": [],
               "aland": {"a0": 2e6, "a1": 1e6, "b0": 1e6}}
    owner = {"a0": pa, "a1": pa, "b0": qb}
    m, ng = inst.channels["X"].m, audit.NeckGraph(polygon)
    assert [(j, set(s)) for j, s, _ in repair.necks(owner, m, ng)] == [(pa, {"a1"})]
    p = {z: (x / 1000.0, y / 1000.0) for z, (x, y) in xym.items()}
    kw = dict(h0=1, max_zctas=100, time_limit=60.0, log=lambda *_: None, keep_support=True,
              border=repair.draw.border_km(polygon), ng=ng)
    same, _ = repair.repair_channel(inst, plan, owner, p, dict(inst.units.unit_of), **kw)
    assert same == owner
    fixed, _ = repair.repair_channel(inst, plan, owner, p, dict(inst.units.unit_of),
                                     open_units=("CT",), **kw)
    assert fixed == {"a0": pa, "a1": qb, "b0": qb} and repair.necks(fixed, m, ng) == []


def test_a_neck_in_an_opened_unit_tries_the_districts_own_window_first():
    """#122: a neck whose side lies in an opened unit is repaired before the others, and its first
    window is the district's own ZCTAs in that unit (`own_window`), here wider than the ball at
    h0 = 1 ({a0, a1}): a2 hangs off a0 by 20 km, so a1 (by 1 km) is P's only neck, and the own
    window hands a1 to Q.  R (unit AL, first by name) has a neck too, by 1 km, that no window
    can lose (no one else may hold AL); it comes second."""
    repair = _repair_module()
    edges = [("a0", "a1"), ("a0", "b0"), ("a1", "b0"), ("a0", "a2"), ("c0", "c1"), ("c0", "b0")]
    km = {("a0", "a1"): 1.0, ("a0", "b0"): 20.0, ("a1", "b0"): 30.0, ("a0", "a2"): 20.0,
          ("c0", "c1"): 1.0, ("b0", "c0"): 20.0}
    xy = {"a0": (0.0, 0.0), "a1": (1.0, 0.0), "a2": (-1.0, 0.0), "b0": (0.5, 1.0),
          "c0": (0.5, 2.0), "c1": (0.5, 3.0)}
    mass = {"a0": 2.0, "a1": 1.0, "a2": 0.5, "b0": 2.0, "c0": 2.0, "c1": 1.0}
    inst, xym = tr._toy({"CT": ["a0", "a1", "a2"], "NJ": ["b0"], "AL": ["c0", "c1"]}, edges,
                        mass, xy, {}, k=3, delta=0.2, final_delta=0.2)
    plan = tr._plan(inst, [({"CT"}, {"CT": 1.0}), ({"NJ"}, {"NJ": 1.0}), ({"AL"}, {"AL": 1.0})])
    ra, pa, qb = sorted(cp.name for cp in plan.copies)
    polygon = {"vertices": sorted(xy), "edges": edges, "state": dict(inst.units.unit_of),
               "border": {e: 1000.0 * x for e, x in km.items()}, "connectors": [],
               "aland": {"a0": 2e6, "a1": 1e6, "a2": 1e6, "b0": 1e6, "c0": 2e6, "c1": 1e6}}
    owner = {"a0": pa, "a1": pa, "a2": pa, "b0": qb, "c0": ra, "c1": ra}
    m, ng = inst.channels["X"].m, audit.NeckGraph(polygon)
    assert [(j, set(s)) for j, s, _ in repair.necks(owner, m, ng)] == [(ra, {"c1"}), (pa, {"a1"})]
    unit_of = inst.units.unit_of
    assert repair.own_window(owner, pa, {"a1"}, frozenset(("a0", "a1", "a2")), unit_of) \
        == {"a0", "a1", "a2"}
    assert repair.own_window(owner, pa, {"a1"}, frozenset(), unit_of) == set()
    p = {z: (x / 1000.0, y / 1000.0) for z, (x, y) in xym.items()}
    fixed, tried = repair.repair_channel(inst, plan, owner, p, dict(unit_of), h0=1, max_zctas=100,
                                         time_limit=60.0, log=lambda *_: None, keep_support=True,
                                         border=repair.draw.border_km(polygon), ng=ng,
                                         open_units=("CT",))
    assert {z: fixed[z] for z in ("a0", "a1", "a2", "b0")} == {"a0": pa, "a1": qb, "a2": pa, "b0": qb}
    assert [(j, set(s)) for j, s, _ in repair.necks(fixed, m, ng)] == [(ra, {"c1"})]
    assert (tried[0]["shape"], tried[0]["zctas"], tried[0]["kept"]) == ("own", 3, True)
    assert tried[0]["cluster"][0].startswith(pa) and tried[1]["cluster"][0].startswith(ra)


def _replan_module():
    spec = importlib.util.spec_from_file_location(
        "contig_replan", os.path.join(HERE, "..", "tools", "exp", "contig", "replan.py"))
    replan = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(replan)
    return replan


def test_replan_refuses_a_copy_or_report_that_is_the_stored_toml_by_a_link():
    """Sol's review of #122 (P1): `--out-spec` or `--report` naming the source through a symlink
    or a hard link, or `--report` naming it outright, stops replan before anything is written."""
    import tempfile
    replan = _replan_module()
    with tempfile.TemporaryDirectory() as d:
        src = os.path.join(d, "src.toml")
        body = '[scenario]\nname = "toy"\n\n[channels.A]\nk = 2\n'
        with open(src, "w") as fh:
            fh.write(body)
        os.symlink(src, os.path.join(d, "soft.toml"))
        os.link(src, os.path.join(d, "hard.toml"))
        copy = os.path.join(d, "copy.toml")
        for out, report in ((os.path.join(d, "soft.toml"), None),
                            (os.path.join(d, "hard.toml"), None), (copy, src),
                            (copy, os.path.join(d, "soft.toml")),
                            (copy, os.path.join(d, "hard.toml"))):
            argv = [src, "--out-spec", out, "--plans", d, "--forbid", "CT-NJ"]
            try:
                replan.main(argv + (["--report", report] if report else []))
            except SystemExit as e:
                assert "stored TOML" in str(e), e
            else:
                raise AssertionError(f"replan wrote over the source via {out}, {report}")
            with open(src) as fh:
                assert fh.read() == body
            assert not os.path.exists(copy)
        assert replan.same_file(copy, copy) and not replan.same_file(copy, src)


def test_replan_writes_a_delta_for_a_channel_that_inherits_the_scenario_delta():
    """Sol's review of #122 (P2): the smallest-δ fallback for a channel with no `delta` line of its
    own (it inherits `[scenario].delta`) adds one, and a channel with its own line has it
    replaced, not doubled."""
    import tomllib
    replan = _replan_module()
    src = ('[scenario]\nname = "toy"\ndelta = 0.02\n\n[channels.A]\nk = 2\n\n'
           '[channels.B]\nk = 3\ndelta = 0.03\n\n[national]\nchannel = "A"\n')
    doc = tomllib.loads(replan.banned_text(src, [], deltas={"A": 0.1273, "B": 0.0612}))
    assert (doc["channels"]["A"]["delta"], doc["channels"]["B"]["delta"]) == (0.1273, 0.0612)
    assert doc["scenario"]["delta"] == 0.02 and doc["national"] == {"channel": "A"}


def test_replan_report_lists_each_channels_effective_bans():
    """Sol's review of #122 (P2): `effective_bans` (the report's `bans`) gives each channel the
    pairs `banned_text` adds to it: the `--channels` restriction and a channel's own bans."""
    import tomllib
    replan = _replan_module()
    src = '[scenario]\nname = "toy"\n\n[channels.A]\nk = 2\n\n[channels.B]\nk = 3\n'
    pairs, extra = [("CT", "NJ")], {"A": [("AZ", "UT")]}
    bans = replan.effective_bans(["A", "B"], pairs, ["B"], extra)
    assert bans == {"A": ["AZ-UT"], "B": ["CT-NJ"]}
    doc = tomllib.loads(replan.banned_text(src, pairs, ["B"], extra=extra))
    assert {c: ["-".join(p) for p in doc["channels"][c].get("forbid_pairs", [])]
            for c in ("A", "B")} == bans
    assert replan.effective_bans(["A", "B"], pairs) == {"A": ["CT-NJ"], "B": ["CT-NJ"]}


def test_two_opened_units_may_each_gain_one_holder_not_one_unit_two():
    """Sol's review of #122 (P2): with CT and NJ opened, the window may not give CT's two outer
    ZCTAs to Q and R (CT from one holder to three) on NJ's allowance; each opened unit gains one
    holder at most.  P holds c0 (2) and c1, c2 (1 each), Q b0 (1), R d0 (1); τ = 2, band ±0.2, so
    Q and R each need a ZCTA of CT: no drawing but the one with three CT holders is in band."""
    repair = _repair_module()
    edges = [("c0", "c1"), ("c0", "c2"), ("c1", "b0"), ("c2", "d0")]
    xy = {"c0": (0.0, 0.0), "c1": (-1.0, 0.0), "c2": (1.0, 0.0), "b0": (-2.0, 0.0),
          "d0": (2.0, 0.0)}
    mass = {"c0": 2.0, "c1": 1.0, "c2": 1.0, "b0": 1.0, "d0": 1.0}
    inst, xym = tr._toy({"CT": ["c0", "c1", "c2"], "NJ": ["b0"], "NY": ["d0"]}, edges, mass, xy,
                        {}, k=3, delta=0.2, final_delta=0.2)
    plan = tr._plan(inst, [({"CT"}, {"CT": 1.0}), ({"NJ"}, {"NJ": 1.0}), ({"NY"}, {"NY": 1.0})])
    pc, qj, ry = (next(cp.name for cp in plan.copies if v in cp.support) for v in ("CT", "NJ", "NY"))
    owner = {"c0": pc, "c1": pc, "c2": pc, "b0": qj, "d0": ry}
    p = {z: (x / 1000.0, y / 1000.0) for z, (x, y) in xym.items()}
    W = set(owner)

    def solve(opened):
        return repair.solve_window(inst, plan, owner, W, p, 60.0, True, lambda *_: None,
                                   keep_support=True, repairing={pc, qj, ry},
                                   opened=frozenset(z for v in opened for z in inst.units.zips[v]))
    g = solve(("CT", "NJ"))
    holders = {g.owner[z] for z in ("c0", "c1", "c2")} if g.owner else set()
    assert len(holders) <= 2, (g.status, g.owner)
    assert g.status not in ("optimal", "connected"), (g.status, g.owner)


def test_an_opened_neck_comes_first_within_its_district():
    """Sol's review of #122 (P2): P (AL+CT) is one piece on the contiguity graph but two on the
    polygons (a0-c0 shares no border), each with a neck, {a0} in CT and {c0} in AL, so the district
    has two necks; the one whose side lies in the opened unit is repaired first, whichever it is."""
    repair = _repair_module()
    edges = [("a0", "a1"), ("a0", "c0"), ("c0", "c1"), ("a0", "b0"), ("a1", "b0"), ("c1", "b0"),
             ("c0", "b0")]
    km = {("a0", "a1"): 1.0, ("c0", "c1"): 1.0, ("a0", "b0"): 20.0, ("a1", "b0"): 30.0,
          ("c1", "b0"): 30.0, ("c0", "b0"): 20.0}
    xy = {"a0": (0.0, 0.0), "a1": (1.0, 0.0), "c0": (0.0, -1.0), "c1": (1.0, -1.0),
          "b0": (2.0, -0.5)}
    mass = {"a0": 2.0, "a1": 1.0, "c0": 2.0, "c1": 1.0, "b0": 5.0}
    inst, xym = tr._toy({"CT": ["a0", "a1"], "AL": ["c0", "c1"], "NJ": ["b0"]}, edges, mass, xy,
                        {}, k=2, delta=0.2, final_delta=0.2)
    plan = tr._plan(inst, [({"AL", "CT"}, {"CT": 1.0, "AL": 1.0}), ({"NJ"}, {"NJ": 1.0})])
    pa, qb = sorted(cp.name for cp in plan.copies)
    polygon = {"vertices": sorted(xy), "edges": [e for e in edges if e != ("a0", "c0")],
               "state": dict(inst.units.unit_of), "border": {e: 1000.0 * x for e, x in km.items()},
               "connectors": [], "aland": {"a0": 2e6, "a1": 1e6, "c0": 2e6, "c1": 1e6, "b0": 1e6}}
    owner = {"a0": pa, "a1": pa, "c0": pa, "c1": pa, "b0": qb}
    m, ng = inst.channels["X"].m, audit.NeckGraph(polygon)
    assert [(j, set(s)) for j, s, _ in repair.necks(owner, m, ng)] == [(pa, {"a0"}), (pa, {"c0"})]
    p = {z: (x / 1000.0, y / 1000.0) for z, (x, y) in xym.items()}
    for unit, side in (("AL", "c0"), ("CT", "a0")):
        _, tried = repair.repair_channel(inst, plan, owner, p, dict(inst.units.unit_of), h0=1,
                                         max_zctas=100, time_limit=60.0, log=lambda *_: None,
                                         keep_support=True, border=repair.draw.border_km(polygon),
                                         ng=ng, open_units=(unit,))
        assert (tried[0]["shape"], tried[0]["cluster"]) == ("own", [f"{pa} {side} (1 ZCTAs)"]), \
            (unit, tried[0]["shape"], tried[0]["cluster"])


# ------------------------------------------------------------------------------ #124 plancheck.py
def _plancheck_module():
    if "contig_plancheck" not in sys.modules:
        spec = importlib.util.spec_from_file_location(
            "contig_plancheck", os.path.join(HERE, "..", "tools", "exp", "contig", "plancheck.py"))
        mod = importlib.util.module_from_spec(spec)
        sys.modules["contig_plancheck"] = mod
        spec.loader.exec_module(mod)
    return sys.modules["contig_plancheck"]


def _corridor_toy(k: int):
    """PA (p0, 100 km², mass 1) and NJ (q0, 100 km², mass 1) are joined only through NY, free,
    a path n1-n2-n3 (1 km² and mass 0.01 each) whose inner edges share 1 km of border; p0-n1 and
    n3-q0 share 20 km.  Every district on PA+NY+NJ crosses NY by a 1 km passage between two
    halves of the land: a neck."""
    edges = [("p0", "n1"), ("n1", "n2"), ("n2", "n3"), ("n3", "q0")]
    km = {("n1", "p0"): 20.0, ("n1", "n2"): 1.0, ("n2", "n3"): 1.0, ("n3", "q0"): 20.0}
    xy = {"p0": (0.0, 0.0), "n1": (1.0, 0.0), "n2": (2.0, 0.0), "n3": (3.0, 0.0), "q0": (4.0, 0.0)}
    mass = {"p0": 1.0, "q0": 1.0, "n1": 0.01, "n2": 0.01, "n3": 0.01}
    inst, _ = tr._toy({"PA": ["p0"], "NY": ["n1", "n2", "n3"], "NJ": ["q0"]}, edges, mass, xy,
                      {"NY": "free"}, k=k, delta=0.1, eta=0.05)
    polygon = {"vertices": sorted(xy), "edges": edges, "state": dict(inst.units.unit_of),
               "border": {e: 1000.0 * x for e, x in km.items()}, "connectors": [],
               "aland": {"p0": 1e8, "q0": 1e8, "n1": 1e6, "n2": 1e6, "n3": 1e6}}
    inst.polygon = polygon
    return inst, audit.NeckGraph(polygon)


def test_b_cuts_a_support_no_district_draws_without_a_neck_and_keeps_one_that_can():
    """#124 B: {PA, NY, NJ} has no drawing without a neck (proved infeasible), so with K = 1, where
    it is the only plan, `plan_checked` cuts it and the master has no plan left; {PA, NY} draws
    (PA with n1, whose 1 km² is under 5% of the land) and is kept."""
    pc = _plancheck_module()
    inst, ng = _corridor_toy(1)
    v = pc.drawable(inst, "X", frozenset({"PA", "NY", "NJ"}), 0.1, ng, 60.0, log=lambda *_: None)
    assert v["status"] == "infeasible", v
    p, rep, rec = pc.plan_checked(inst, "X", ng=ng, check_time=60.0, log=lambda *_: None)
    assert p is None and rec["status"] == "infeasible", rec
    assert [b["support"] for b in rec["bans"]] == ["NJ+NY+PA"] and rec["bans"][0]["objective_after"] is None
    two, ng2 = _corridor_toy(2)
    v = pc.drawable(two, "X", frozenset({"PA", "NY"}), 0.1, ng2, 60.0, log=lambda *_: None)
    assert v["status"] == "drawable", v
    p, _, rec = pc.plan_checked(two, "X", ng=ng2, check_time=60.0, log=lambda *_: None)
    assert p is not None and rec["status"] == "passed" and not rec["bans"], rec


def test_b_never_cuts_on_a_timeout():
    """#124 B: out of time the test is unknown, listed, never a cut; the plan stands."""
    pc = _plancheck_module()
    inst, ng = _corridor_toy(1)
    v = pc.drawable(inst, "X", frozenset({"PA", "NY", "NJ"}), 0.1, ng, 0.0, log=lambda *_: None)
    assert v["status"] == "unknown", v
    p, _, rec = pc.plan_checked(inst, "X", ng=ng, check_time=0.0, log=lambda *_: None)
    assert p is not None and rec["status"] == "passed" and not rec["bans"]
    assert [u["support"] for u in rec["unknown"]] == ["NJ+NY+PA"]
    checks = pc.Checks()                # monotone: infeasible at 0.1 stands at 0.05, not at 0.2
    checks.put("X", {"PA"}, 0.1, {"status": "infeasible"})
    assert checks.get("X", {"PA"}, 0.05) and checks.get("X", {"PA"}, 0.2) is None


def test_c_bans_a_support_after_a_proved_infeasible_window_and_leaves_an_unknown_uncut():
    """#124 C: of two districts left in pieces, the one whose last window was proved infeasible
    (outside fixed) gets its support banned, with the window as evidence and the cost before and
    after once the next round is drawn; the one whose window ended unknown is listed, not cut; a
    log line saying a window was not tried makes the cause "budget spent".  The re-plan honours
    the ban (`ban_supports` in the next round's copy, `replan.banned_text`)."""
    pc = _plancheck_module()
    inst, xy, plan = _u_toy()
    ct, nj = sorted(cp.name for cp in plan.copies)
    owner = {z: ct for z in inst.units.unit_of}     # pieces: NJ+NY's v44 and CT+NY's v43
    owner.update(dict.fromkeys(["b0", "v30", "v40", "v41", "v42", "v44"], nj))
    attempts = [{"cluster": [f"{nj} v44 (1 ZCTAs)"], "status": "infeasible", "shape": "ball",
                 "h": 1, "window_zctas": 3, "cap": True},
                {"cluster": [f"{ct} v43 (1 ZCTAs)"], "status": "unknown", "shape": "ball",
                 "h": 1, "window_zctas": 4, "cap": True}]
    ng = audit.NeckGraph({"vertices": sorted(xy), "edges": [(a, b) for a in inst.units.zip_adj
                                                            for b in inst.units.zip_adj[a] if a < b],
                          "state": dict(inst.units.unit_of), "border": {}, "connectors": [],
                          "aland": dict.fromkeys(xy, 1e6)})
    found = [x for x in pc.causes(inst, plan, owner, attempts, "", ng, 1, 100) if x["kind"] == "piece"]
    f, unknown = sorted(found, key=lambda x: x["district"] != nj)
    assert (f["district"], f["cause"], f["window"]["window_zctas"]) == (nj, pc.INFEASIBLE, 3), f
    assert f["window"]["cap_stopped_growth"] is False
    assert (unknown["district"], unknown["cause"]) == (ct, "window unknown at its time limit")
    spent = pc.causes(inst, plan, owner, attempts, f"budget spent: X ball 2 of {nj} not tried\n",
                      ng, 1, 100)
    assert {x["district"]: x["cause"] for x in spent if x["kind"] == "piece"}[nj] == "budget spent"
    ch = inst.channels["X"]
    ch.spec = dataclasses.replace(ch.spec, replan_rounds=1)
    cost0 = {"X": {"delta": 0.1, "objective": 1.0, "splits": 1, "cuts": 1}}
    entry = {"left": [f, unknown], "cost": cost0}
    banned, done = {}, {}
    nb = pc.close_round(entry, None, inst, done, banned, last=False)
    assert [(b["channel"], b["support"], b["evidence"]["cause"]) for b in nb] == \
        [("X", ["NJ", "NY"], pc.INFEASIBLE)] and "stop" not in entry
    assert banned == {"X": {frozenset({"NJ", "NY"})}} and done == {"X": 1}
    cost1 = {"X": {"delta": 0.1, "objective": 2.0, "splits": 2, "cuts": 2}}
    nxt = {"left": [unknown], "cost": cost1}
    assert pc.close_round(nxt, entry, inst, done, banned, last=False) == []
    assert nb[0]["cost"] == {"before": cost0["X"], "after": cost1["X"]}
    assert nxt["stop"].startswith("no window proved infeasible")
    replan = _replan_module()
    text = replan.banned_text("[channels.X]\nk = 2\n", [], keys={"X": {
        "ban_supports": '[["NJ", "NY"]]'}})
    assert 'ban_supports = [["NJ", "NY"]]' in text
    ch.spec = dataclasses.replace(ch.spec, ban_supports=(frozenset({"NJ", "NY"}),))
    p, _ = master.plan(inst, "X", delta=0.6)     # the re-plan: NJ+NY is gone
    assert p is not None and frozenset({"NJ", "NY"}) not in p.n, p and p.n
