"""td.audit: the §9 checks on a toy plan, each planted defect, and the tagged catalog (#70).

The toy plan is one channel, K = 4, over three units on a ring of ten ZIPs: A whole, B clipped
and split between two districts inside it, C free and shared.  It is clean; each planted defect
changes one thing and must fail its own check.  The catalog tests read the tag's `scenarios.csv`
through git and print SKIP without the tag; the fragment test also needs TIGER/Line 2025 state
polygons (`tl_2025_us_state.zip` in `data/public/`, or `$TD_REPO`'s).
"""
from __future__ import annotations

import collections
import dataclasses
import functools
import json
import math
import os
import subprocess
import sys
import tempfile

from td import audit, geo, output
from td.audit import Cell, Channel, Run

UNIT = {"a1": "A", "a2": "A", "a3": "A", "b1": "B", "b2": "B", "b3": "B", "b4": "B",
        "c1": "C", "c2": "C", "c3": "C"}
MODE = {"A": "whole", "B": "clipped", "C": "free"}
RING = ["a1", "a2", "a3", "b1", "b2", "b3", "b4", "c1", "c2", "c3"]
OWNER = {"a1": "d1", "a2": "d1", "a3": "d1", "c3": "d1", "b1": "d2", "b2": "d2",
         "b3": "d3", "b4": "d3", "c1": "d4", "c2": "d4"}
MASS = {z: 1.5 if z.startswith("b") else 1.0 for z in UNIT}


def _drawn(owner, mass):
    unit = collections.Counter()
    held = collections.Counter()
    for z, j in owner.items():
        unit[UNIT[z]] += mass[z]
        held[UNIT[z], j] += mass[z]
    return {("X", v, j): m / unit[v] for (v, j), m in held.items()}


def _run(owner=None, mass=None, **over):
    """The clean toy run; `owner` and `mass` change the drawing, and the run's reported shares
    follow it, as a realizer's diagnostics would."""
    owner = dict(OWNER, **(owner or {}))
    mass = dict(MASS, **(mass or {}))
    with open(os.path.join(geo.REFERENCE_DIR, "MANIFEST.json"), encoding="utf-8") as fh:
        manifest = json.load(fh)
    kw = dict(
        cells=[Cell(z, "f", "X", owner[z], mass[z]) for z in RING],
        channels={"X": Channel(4, 2.0, 4.0)},
        expected={(z, "f") for z in RING},
        unit_of=UNIT,
        mode={("X", v): m for v, m in MODE.items()},
        planned=_drawn(OWNER, MASS),
        reported=_drawn(owner, mass),
        graph={"vertices": RING, "edges": list(zip(RING, RING[1:] + RING[:1]))},
        polygon={"vertices": RING, "edges": list(zip(RING, RING[1:] + RING[:1])), "state": UNIT},
        manifest=manifest,
        solver={"X": {"status": "optimal", "objective": 7.0, "bound": 7.0, "gap": 0.0,
                      "mip_rel_gap": 0.0}},
        names={"d1": "Alpha", "d2": "Beta", "d3": "Gamma", "d4": "Delta"},
        fine=("f",),
        route={(v, "f"): "X" for v in MODE},
    )
    kw.update(over)
    return Run(**kw)


def _checks(run):
    return {c.name: c for c in audit.audit(run)}


def _fails(run):
    return sorted(n for n, c in _checks(run).items() if c.status == "fail")


# ------------------------------------------------------------------------------ the toy plan
def test_clean_plan_passes_every_check():
    checks = audit.audit(_run())
    assert audit.verdict(checks) == "pass"
    assert {c.status for c in checks} <= {"pass", "listed"}
    assert [c.name for c in checks if c.status == "unverified"] == []
    tier = _checks(_run())["certificate tier"]
    assert tier.summary == "weakest tier: exact"


def test_m1_fails_a_detached_piece_and_an_unowned_zcta_and_is_unverified_without_a_polygon_graph():
    run = _run()
    run.polygon["edges"] = [e for e in run.polygon["edges"] if e != ("c3", "a1")]
    m1 = _checks(run)[audit.M1_CHECK]                # d1's c3 now meets d1 only across the cut
    assert _fails(run) == [audit.M1_CHECK] and m1.counts["pieces"] == 1
    assert m1.items == [f"X/d1: detached piece of 1 ZIPs (c3...), 0.333 τ, cause {audit.M1_CUT}"]
    run = _run()
    run.polygon = dict(run.polygon, vertices=RING + ["z9"], state=dict(UNIT, z9="Z"))
    run.unit_of = dict(UNIT, z9="C")
    m1 = _checks(run)[audit.M1_CHECK]              # z9 has no row in fine channel f (#116)
    assert _fails(run) == [audit.M1_CHECK] and m1.counts["no_row"] == 1
    assert m1.counts["no_owner"] == 0
    assert m1.items == ["fine channel f: 1 of 11 CONUS ZCTAs have no row",
                        "fine channel f: 1 ZCTAs of Z have no row"]
    assert _checks(_run(polygon=None))[audit.M1_CHECK].status == "unverified"


def test_m1_owns_each_conus_zcta_once_per_fine_channel():
    """#116: a channel owns the ZCTAs it has rows for, here Y every ZCTA in fine channel g at zero
    opportunity (`NO_CELL` rows the extract lacks, which `check_cells` takes as territory); the
    same (ZCTA, fine channel) owned in two channels fails M1, and a `NO_CELL` row with
    opportunity fails `check_cells`."""
    clean = _run()
    territory = [Cell(z, "g", "Y", "e1", 0.0, reason=audit.NO_CELL) for z in RING]
    kw = dict(cells=clean.cells + territory,
              channels={"X": Channel(4, 2.0, 4.0), "Y": Channel(1, 0.0, 0.0)},
              solver=dict(clean.solver, Y=clean.solver["X"]), names=dict(clean.names, e1="Epsilon"),
              fine=("f", "g"), route={**clean.route, **{(v, "g"): "Y" for v in MODE}})
    run = _run(**kw)
    assert _fails(run) == [], {n: c.items for n, c in _checks(run).items() if c.status == "fail"}
    m1 = _checks(run)[audit.M1_CHECK]
    assert m1.status == "pass" and (m1.counts["no_owner"], m1.counts["no_row"], m1.counts["double"]) == (0, 0, 0)
    twice = _run(**dict(kw, cells=kw["cells"] + [Cell("a1", "g", "Z", "z1", 0.0, reason=audit.NO_CELL)],
                        names=dict(kw["names"], z1="Zeta")))
    m1 = _checks(twice)[audit.M1_CHECK]
    assert m1.counts["double"] == 1 and "fine channel g: ZCTA a1 owned in Y, Z" in m1.items
    assert "fine channel g: ZCTA a1 has a row in Z, held by Y" in m1.items
    assert "cell a1/g: 2 owners" in audit.check_cells(twice).items
    heavy = _run(**dict(kw, cells=clean.cells + [territory[0]._replace(m=0.5)] + territory[1:]))
    assert f"cell a1/g: {audit.NO_CELL} with opportunity 0.5" in audit.check_cells(heavy).items


def _two_fine(**over):
    """The toy run with a second fine channel g in X, every ZCTA owned there as in f at zero
    opportunity (`NO_CELL`)."""
    clean = _run()
    g = [Cell(z, "g", "X", OWNER[z], 0.0, reason=audit.NO_CELL) for z in RING]
    kw = dict(cells=clean.cells + g, fine=("f", "g"), route={**clean.route, **{(v, "g"): "X" for v in MODE}})
    kw.update(over)
    return _run(**kw)


def test_m1_checks_each_fine_channel_of_a_dropped_unit_apart():
    """Review of #116 (P1-1): z9 is a ZCTA of unit D, dropped for zero opportunity in the solved
    channel X.  Its g row is owned; its f row is blank.  Ownership is not pooled across fine
    channels, and a blank row is excused only in a dropped channel, so M1 and the cell check fail."""
    clean = _two_fine()
    polygon = dict(clean.polygon, vertices=RING + ["z9"], edges=clean.polygon["edges"] + [("z9", "a1")],
                   state=dict(UNIT, z9="D"))
    z9 = [Cell("z9", "f", "X", "d1", 0.0, reason=audit.DROPPED),
          Cell("z9", "g", "X", "d1", 0.0, reason=audit.DROPPED)]
    owned = _two_fine(cells=clean.cells + z9, polygon=polygon, unit_of=dict(UNIT, z9="D"),
                      route={**clean.route, ("D", "f"): "X", ("D", "g"): "X"})
    assert _fails(owned) == [], {n: c.items for n, c in _checks(owned).items() if c.status == "fail"}
    blank = dataclasses.replace(owned, cells=clean.cells + [z9[0]._replace(district=""), z9[1]])
    m1 = _checks(blank)[audit.M1_CHECK]
    assert m1.status == "fail" and m1.counts["no_owner"] == 1 and "X: 1 of 11 ZCTAs have no owner" in m1.items
    assert "cell z9/f: no owner" in _checks(blank)["one owner per cell"].items
    assert audit.check_m1(dataclasses.replace(blank, route=None)).counts["no_owner"] == 1


def test_m1_takes_its_fine_channels_and_footprints_from_the_scenario():
    """Review of #116 (P1-2): the cells M1 checks come from the scenario (`Run.fine`, `Run.route`),
    so a fine channel with no row at all, a solved channel emptied from the ledger, and a row with
    a blank fine channel each fail, with or without the routing."""
    clean = _two_fine()
    assert _fails(clean) == []
    no_g = dataclasses.replace(clean, cells=[c for c in clean.cells if c.fine != "g"])
    for run in (no_g, dataclasses.replace(no_g, route=None)):
        m1 = audit.check_m1(run)
        assert m1.status == "fail" and m1.counts["no_row"] == 10, m1.items
        assert "fine channel g: 10 of 10 CONUS ZCTAs have no row" in m1.items
    # without the scenario's fine channels, the ledger's are all M1 can read, and it says so
    fallback = audit.check_m1(dataclasses.replace(no_g, fine=None, route=None))
    assert fallback.status == "pass" and fallback.summary.endswith("(fine channels from the ledger)")
    y = [Cell(z, "g", "Y", "e1", 0.0, reason=audit.NO_CELL) for z in RING]
    two = _run(cells=_run().cells + y,
               channels={"X": Channel(4, 2.0, 4.0), "Y": Channel(1, 0.0, 0.0)},
               solver=dict(_run().solver, Y=_run().solver["X"]), names=dict(_run().names, e1="Epsilon"),
               fine=("f", "g"), route={**_run().route, **{(v, "g"): "Y" for v in MODE}})
    assert _fails(two) == []
    emptied = dataclasses.replace(two, cells=_run().cells)
    for run in (emptied, dataclasses.replace(emptied, route=None)):
        m1 = audit.check_m1(run)
        assert m1.status == "fail" and m1.counts["no_row"] == 10, m1.items
    blank = dataclasses.replace(clean, cells=clean.cells[:-1] + [clean.cells[-1]._replace(fine="")])
    m1 = audit.check_m1(blank)
    assert m1.status == "fail" and "X: a row of ZIP c3 has no fine channel" in m1.items
    stray = dataclasses.replace(clean, cells=clean.cells + [Cell("a1", "h", "X", "d1", 0.0)])
    assert "fine channel h: has rows but is not a fine channel of the scenario" in audit.check_m1(stray).items


def test_m1_never_excuses_a_double_owner():
    """Review of #116 (P1-3): X and Y both own every cell of f, and a dropped channel D adds a
    blank row to each: owned rows are counted, so each cell is owned twice.  Two districts of one
    planning channel owning one ZCTA in two fine channels fail too, whichever row comes last."""
    clean = _run()
    y = [Cell(z, "f", "Y", "e1", 0.0, reason=audit.NO_CELL) for z in RING]
    d = [Cell(z, "f", "D", "", 0.0, reason=audit.DROPPED) for z in RING]
    run = _run(cells=clean.cells + y + d,
               channels={"X": Channel(4, 2.0, 4.0), "Y": Channel(1, 0.0, 0.0)},
               solver=dict(clean.solver, Y=clean.solver["X"]), names=dict(clean.names, e1="Epsilon"))
    for r in (run, dataclasses.replace(run, route=None)):
        m1 = audit.check_m1(r)
        assert m1.status == "fail" and m1.counts["double"] == 10, m1.items
        assert "fine channel f: ZCTA a1 owned in X, Y" in m1.items
    two = _two_fine()
    clash = dataclasses.replace(two, cells=[Cell("a1", "g", "X", "d2", 0.0, reason=audit.NO_CELL)]
                                + [c for c in two.cells if (c.zip, c.fine) != ("a1", "g")])
    m1 = audit.check_m1(clash)
    assert m1.status == "fail" and "X: ZCTA a1 owned by d1, d2" in m1.items and m1.counts["double"] == 1


def test_a_whole_unit_violation_with_unknown_mass_still_fails():
    """Review of #116 (P2-5): only a cell known to hold no opportunity is left out of the mode
    check; a ledger with no masses still fails a whole unit with two owners."""
    for mass in (MASS, dict.fromkeys(UNIT)):
        run = _run(owner={"a1": "d4"})
        run.cells = [c._replace(m=mass[c.zip]) for c in run.cells]
        modes = audit.check_modes(run)
        assert modes.status == "fail" and "X/A: whole unit with 2 owners (d1, d4)" in modes.items


def test_planted_phantom_share_fails():
    run = _run()
    run.reported[("X", "B", "d1")] = 0.1            # d1 owns no ZIP of B
    assert _fails(run) == ["phantom shares"]
    run = _run()
    run.reported[("X", "C", "d4")] += 0.05          # reported, not what the ledger draws
    assert _fails(run) == ["phantom shares"]


def test_nonfinite_reported_share_is_a_phantom_share():
    """#72 B5: NaN fails both the ownership and the difference comparison, so it passed."""
    for bad in (float("nan"), float("inf"), None):
        run = _run()
        run.reported[("X", "B", "d1")] = bad         # d1 owns no ZIP of B
        assert _fails(run) == ["phantom shares"], bad
        run = _run()
        run.reported[("X", "C", "d4")] = bad         # d4 does own ZIPs of C
        assert _fails(run) == ["phantom shares"], bad


def test_cell_of_a_pseudo_district_is_a_phantom_share():
    run = _run(owner={"c2": "other"})
    fails = _fails(run)
    assert "phantom shares" in fails
    assert any("pseudo-district 'other'" in i for i in _checks(run)["phantom shares"].items)


def test_planted_out_of_tolerance_mass_fails():
    run = _run(mass={"c3": 2.5})                    # d1 draws 5.5 > 4
    assert _fails(run) == ["final bands on drawn mass"]
    item, = _checks(run)["final bands on drawn mass"].items
    assert item.startswith("X/d1: drawn 5.5 outside [2, 4]")


def test_band_breach_names_the_undrawn_share():
    run = _run(owner={"c3": "d4"}, channels={"X": Channel(4, 3.5, 5.0)})   # d1 keeps only A
    items = _checks(run)["final bands on drawn mass"].items
    assert "X/d1: drawn 3 outside [3.5, 5]; undrawn share of C" in items
    assert "X/d2: drawn 3 outside [3.5, 5]" in items


def test_planted_owner_outside_a_clipped_unit_fails():
    run = _run(owner={"b4": "d4"}, channels={"X": Channel(4, 1.0, 5.0)})
    assert _fails(run) == ["mode compliance"]
    item, = _checks(run)["mode compliance"].items
    assert item == "X/B/d4: owner outside the clipped unit, also in C (C16)"


def test_whole_unit_with_two_owners_fails():
    run = _run(owner={"a1": "d4"}, channels={"X": Channel(4, 1.0, 5.0)})
    assert "mode compliance" in _fails(run)
    assert any("whole unit with 2 owners" in i for i in _checks(run)["mode compliance"].items)


def test_vanished_share_and_extra_free_owner_are_listed_not_failed():
    run = _run(owner={"c3": "d4"}, channels={"X": Channel(4, 1.0, 5.0)})
    check = _checks(run)["planned against drawn owners"]
    assert check.status == "listed"
    assert check.items == ["X/C/d1: planned share 0.333333 drawn as no ZIPs (C8)"]
    run = _run(owner={"c1": "d3"}, channels={"X": Channel(4, 1.0, 5.0)},
               mode={("X", "A"): "whole", ("X", "B"): "free", ("X", "C"): "free"})
    check = _checks(run)["planned against drawn owners"]
    assert "X/C/d3: extra owner from repair in a free unit" in check.items
    assert _fails(run) == []


def test_pieces_and_graph_gaps_are_listed_with_cause():
    graph = {"vertices": [z for z in RING if z != "c1"],
             "edges": [(a, b) for a, b in zip(RING, RING[1:] + RING[:1]) if "c1" not in (a, b)]}
    run = _run(owner={"a2": "d4"}, graph=graph, causes={("d1", "a3"): "shape"},
               channels={"X": Channel(4, 1.0, 5.0)})
    check = _checks(run)["ZIP contiguity"]
    assert check.status == "listed"
    assert check.counts == {"split": 2, "pieces": 2, "gaps": 1}
    assert "X/d4: ZIP c1 not in the graph (graph gap)" in check.items
    assert "X/d1: piece of 1 ZIPs, 0.333 of the district's mass, cause shape" in check.items
    assert "X/d4: piece of 1 ZIPs, 0.333 of the district's mass, cause unreported" in check.items


def test_cells_count_names_manifest_and_solver_fail_when_broken():
    run = _run()
    run.cells.append(Cell("a1", "f", "X", "d2", 1.0))
    assert "one owner per cell" in _fails(run)
    run = _run(expected={(z, "f") for z in RING} | {("zz", "f")})
    assert _fails(run) == ["one owner per cell"]
    assert _fails(_run(channels={"X": Channel(5, 2.0, 4.0)})) == ["district count per channel"]
    assert _fails(_run(names={"d1": "Alpha", "d2": "Alpha", "d3": "Gamma"})) == ["one name per district"]
    manifest = json.loads(json.dumps(_run().manifest))
    manifest["sources"][0]["vintage"] = "2020"
    assert _fails(_run(manifest=manifest)) == ["geography manifest is 2025"]
    assert _fails(_run(solver={"X": {"status": "time limit"}})) == [
        "certificate tier", "solver status, bound and gap"]


def test_ledger_cell_outside_the_expected_cells_fails():
    assert _checks(_run())["one owner per cell"].status == "pass"
    run = _run()
    run.cells.append(Cell("c1", "invented", "X", "d4", 0.0))
    check = audit.check_cells(run)
    assert check.status == "fail"
    assert check.items == ["cell c1/invented: not expected"]
    # M1 too (#116): a fine channel of the ledger needs a row at every CONUS ZCTA
    assert _fails(run) == [audit.M1_CHECK, "one owner per cell"]


def test_a_domain_cell_missing_from_the_ledger_fails_by_name():
    """#89: a cell of the domain the ledger lacks fails, as ZIP 13027's FI cell should have."""
    run = _run(cells=[c for c in _run().cells if c.zip != "b2"])
    check = audit.check_cells(run)
    assert check.status == "fail" and check.items == ["cell b2/f: not in the ledger"]
    assert "one owner per cell" in _fails(run)


def test_a_not_placed_cell_passes_only_when_its_zip_has_no_opportunity():
    """#89 (owner, 2026-10-04): a NOT_PLACED cell is listed when it has no owner, its ZIP no unit,
    and its whole ZIP no opportunity; otherwise it fails `check_cells`."""
    clean = _run()
    off = [Cell("z9", "f", "X", "", 0.0, reason=audit.NOT_PLACED),
           Cell("z9", "g", "Y", "", 0.0, reason=audit.NOT_PLACED)]
    run = _run(cells=clean.cells + off, expected=clean.expected | {("z9", "f"), ("z9", "g")},
               fine=None, route=None)           # g is a fine channel of z9's rows only
    assert _fails(run) == []
    check = _checks(run)["one owner per cell"]
    assert check.status == "listed"
    assert check.items == [f"cell z9/{f} ({c}): {audit.NOT_PLACED}, ZIP has no opportunity"
                           for f, c in (("f", "X"), ("g", "Y"))]
    heavy = dataclasses.replace(run, cells=clean.cells + [off[0], off[1]._replace(m=1.6e-8)])
    assert audit.check_cells(heavy).items == [f"cell z9/{f}: not placed, ZIP z9 has opportunity 1.6e-08"
                                              for f in "fg"]
    assert _fails(heavy) == ["one owner per cell"]
    owned = dataclasses.replace(run, cells=clean.cells + [off[0]._replace(district="d1"), off[1]])
    assert "cell z9/f: not placed but owned by d1" in audit.check_cells(owned).items
    placed = dataclasses.replace(run, unit_of=dict(UNIT, z9="A"))
    assert audit.check_cells(placed).items == [f"cell z9/{f}: not placed but ZIP z9 is in unit A"
                                               for f in "fg"]
    unknown = dataclasses.replace(run, cells=clean.cells + [off[0]._replace(m=None), off[1]])
    assert audit.check_cells(unknown).status == "fail"


def test_a_sub_tolerance_cell_is_owned_not_missing():
    """#86 with #89: a `SUB_TOLERANCE` cell (ZIP 13027's FI cell) has an owner, so `check_cells`
    counts it as owned and does not treat it as `NOT_PLACED`."""
    run = _run(cells=[c._replace(m=1e-8, reason=output.SUB_TOLERANCE) if c.zip == "b2" else c
                      for c in _run().cells])
    check = audit.check_cells(run)
    assert check.status == "pass" and check.items == []
    unowned = dataclasses.replace(run, cells=[c._replace(district="") if c.zip == "b2" else c
                                              for c in run.cells])
    assert audit.check_cells(unowned).items == ["cell b2/f: no owner"]


def test_certificate_tiers_follow_od3():
    exact = {"status": "optimal", "objective": 1.0, "bound": 1.0, "gap": 0.0, "mip_rel_gap": 0.0}
    assert audit.tier(exact) == "exact"
    assert audit.tier(dict(exact, mip_rel_gap=1e-4)) == "bounded"
    assert audit.tier(dict(exact, status="time limit", bound=0.9, gap=0.1)) == "bounded"
    assert audit.tier(dict(exact, bound=None, gap=None)) == "feasible only"
    assert audit.tier({"status": "time limit"}) == "none"


def test_invalid_solver_reports_get_no_tier_and_fail():
    exact = {"status": "optimal", "objective": 1.0, "bound": 2.0, "gap": 0.0, "mip_rel_gap": 0.0}
    nan = {"objective": 1.0, "bound": float("nan"), "gap": None}
    for report, why in ((exact, "bound 2.0 above the incumbent 1.0"),
                        (nan, "bound nan is not a finite number")):
        assert audit.tier(report) == "invalid"
        checks = _checks(_run(solver={"X": report}))
        assert checks["certificate tier"].status == "fail"
        assert checks["certificate tier"].items == ["X: invalid"]
        assert f"X: invalid report, {why}" in checks["solver status, bound and gap"].items
    wrong_gap = {"status": "time limit", "objective": 1.0, "bound": 0.9, "gap": 0.0}
    assert audit.tier(wrong_gap) == "invalid"
    assert audit.tier({"objective": 1.0, "gap": 0.0}) == "invalid"      # a gap needs a bound


def test_valid_solver_reports_keep_their_tier():
    exact = {"status": "optimal", "objective": 7.0, "bound": 7.0, "gap": 0.0, "mip_rel_gap": 0.0}
    assert _checks(_run(solver={"X": exact}))["certificate tier"].summary == "weakest tier: exact"
    bounded = {"status": "time limit", "objective": 8.0, "bound": 6.0, "gap": 0.25}
    assert audit.tier(bounded) == "bounded"
    checks = _checks(_run(solver={"X": bounded}))
    assert checks["certificate tier"].status == "pass"
    assert checks["certificate tier"].summary == "weakest tier: bounded"


def test_solver_row_shows_the_actual_gap():
    for bounded in ({"status": "time limit", "objective": 8.0, "bound": 6.0},
                    {"status": "time limit", "objective": 8.0, "bound": 6.0, "gap": 0.25}):
        check, = [c for c in audit.check_solver(Run(cells=[], channels={"X": Channel(1)},
                                                         solver={"X": bounded}))
                  if c.name == "solver status, bound and gap"]
        assert check.items == ["X: status time limit, objective 8.0, bound 6.0, gap 0.25, tier bounded"]
    feasible = {"status": "time limit", "objective": 8.0}
    check = audit.check_solver(Run(cells=[], channels={"X": Channel(1)}, solver={"X": feasible}))[0]
    assert check.items == ["X: status time limit, objective 8.0, bound None, gap None, tier feasible only"]


def test_exact_allowance_is_mixed_absolute_and_relative():
    assert audit.allowance(1e6) == 1e-3 and audit.allowance(0.001) == 1e-9 and audit.allowance(0) == 1e-9
    exact = {"status": "optimal", "mip_rel_gap": 0.0, "gap": 0.0}
    big = dict(exact, objective=1e6)
    assert audit.tier(dict(big, bound=1e6 - 5e-4)) == "exact"          # 5e-4 within 1e-3
    assert audit.tier(dict(big, bound=1e6 - 5e-2, gap=None)) == "bounded"
    assert audit.tier(dict(big, bound=1e6 - 5e-2, gap=5e-8)) == "bounded"
    assert audit.tier(dict(big, bound=1e6 - 5e-2)) == "invalid"         # a gap of 0 misreports it
    assert audit.solver_problems(dict(big, bound=1e6 + 5e-4)) == []
    assert audit.tier(dict(big, bound=1e6 + 5e-4)) == "exact"
    assert audit.solver_problems(dict(big, bound=1e6 + 5e-2)) != []
    assert audit.tier(dict(big, bound=1e6 + 5e-2)) == "invalid"
    small = dict(exact, objective=0.001)
    assert audit.tier(dict(small, bound=0.001 + 5e-10)) == "exact"
    assert audit.tier(dict(small, bound=0.001 + 5e-9)) == "invalid"
    # Below |objective| = 1 the allowance is absolute: 5e-10 is a relative gap of 5e-7.
    assert audit.tier(dict(small, bound=0.001 - 5e-10)) == "exact"
    assert audit.tier(dict(small, bound=0.001 - 5e-9)) == "invalid"
    assert audit.tier(dict(exact, objective=0.0, bound=-5e-10)) == "exact"
    assert audit.tier(dict(exact, objective=0.0, bound=-1.0)) == "invalid"
    assert audit.tier({"status": "time limit", "objective": 0.0, "bound": -1.0, "gap": math.inf}) == "bounded"
    assert audit.tier({"status": "time limit", "objective": 0.0, "bound": 0.0, "gap": 5.0}) == "invalid"


def test_band_allows_od1_slack_at_both_boundaries():
    # τ_c = 12 / 4 = 3, so OD1 allows 3e-9 past each end of [2, 4].
    assert _fails(_run(mass={"c3": 1.0 + 1e-10})) == []                 # d1 draws 4 + 1e-10
    assert _fails(_run(mass={"c3": 1.0 + 2e-9})) == []
    assert _fails(_run(mass={"c3": 1.0 + 1e-6})) == ["final bands on drawn mass"]
    assert _fails(_run(mass={"c1": 1.0 - 2e-9})) == []                 # d4 draws 2 - 2e-9
    assert _fails(_run(mass={"c1": 1.0 - 1e-6})) == ["final bands on drawn mass"]


def test_undeclared_channel_fails_the_audit_without_raising():
    run = _run()
    run.cells[0] = run.cells[0]._replace(channel="Y")
    checks = _checks(run)
    assert checks["district count per channel"].status == "fail"
    assert "Y: not a declared channel" in checks["district count per channel"].items
    assert "Y/d1: drawn 1 in an undeclared channel, no band" in checks["final bands on drawn mass"].items
    assert audit.verdict(checks.values()) == "fail"


def test_conflicting_rep_labels_fail_and_blank_labels_pass():
    assert _checks(_run())["rep labels"].status == "pass"
    run = _run()
    run.cells[0] = run.cells[0]._replace(rep="R1")
    run.cells[1] = run.cells[1]._replace(rep="R2")
    assert _fails(run) == ["rep labels"]


def test_missing_inputs_are_unverified_not_passed():
    run = Run(cells=[Cell(z, "f", "X", OWNER[z]) for z in RING], channels={"X": Channel(4)})
    checks = _checks(run)
    for name in ("final bands on drawn mass", "planned against drawn owners", "mode compliance",
                 "ZIP contiguity", "geography manifest is 2025", "certificate tier",
                 "one name per district"):
        assert checks[name].status == "unverified", name
    assert audit.verdict(checks.values()) == "pass"


def test_scorecard_is_written_with_verdict_and_items():
    run = _run(mass={"c3": 2.5})
    with tempfile.TemporaryDirectory() as tmp:
        path = audit.write_scorecard(tmp, audit.audit(run), "toy")
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
    assert text.startswith("# Scorecard: toy\n\n**Verdict: fail**")
    assert "| final bands on drawn mass | fail |" in text
    assert "- X/d1: drawn 5.5 outside [2, 4]" in text


def test_catalog_k_reads_the_scenario_name():
    assert audit.catalog_k("51_total_13n_11wh_24fi_3wifi") == {"N": 13, "WH": 11, "FI": 24, "WHFI": 3}



def test_dropped_zero_opportunity_cells_are_listed_not_failed():
    """MODEL §1 and §9 (#65 F1): a cell of a channel dropped for zero opportunity, not among the
    run's channels, keeps a blank district, carries the reason, and is listed; a blank owner
    without it, a drop where there is opportunity, or a blank dropped row in a solved channel,
    which the territory pass owns (#116), fails."""
    clean = _run()
    zero = Cell("z0", "f", "Y", "", 0.0, reason=audit.DROPPED)
    run = _run(cells=clean.cells + [zero], expected=clean.expected | {("z0", "f")},
               unit_of=dict(UNIT, z0="Zero"))
    assert _fails(run) == []
    dropped = _checks(run)["dropped for zero opportunity"]
    assert dropped.status == "listed" and dropped.items == ["cell z0/f (Y): dropped: zero opportunity"]
    blank = dataclasses.replace(run, cells=clean.cells + [zero._replace(reason="")])
    assert _fails(blank) == ["one owner per cell"]
    heavy = dataclasses.replace(run, cells=clean.cells + [zero._replace(m=1.0)])
    assert "dropped for zero opportunity" in _fails(heavy)
    solved = dataclasses.replace(run, cells=clean.cells + [zero._replace(channel="X")])
    assert "cell z0/f: no owner" in _checks(solved)["one owner per cell"].items


def test_a_channel_dropped_whole_is_not_counted_against_k():
    clean = _run()
    dropped = [Cell(z, "g", "Y", "", 0.0, reason=audit.DROPPED) for z in RING]
    run = _run(cells=clean.cells + dropped,
               channels={"X": Channel(4, 2.0, 4.0), "Y": Channel(2, 0.0, 1.0)},
               expected=clean.expected | {(z, "g") for z in RING},
               fine=("f", "g"), route={**clean.route, **{(v, "g"): "Y" for v in MODE}})
    assert _checks(run)["district count per channel"].status == "pass"
    # M1: a channel the run declares owns every ZCTA of its footprint (#116), and its blank rows
    # are not excused in `check_cells` either
    assert _fails(run) == [audit.M1_CHECK, "one owner per cell"]
    assert _checks(run)[audit.M1_CHECK].items[0] == "Y: 10 of 10 ZCTAs have no owner"
    # a channel dropped for zero opportunity is not among the run's channels and has no districts:
    # its rows keep the blank district and are excused
    run = dataclasses.replace(run, channels={"X": Channel(4, 2.0, 4.0)})
    assert _fails(run) == [], _checks(run)[audit.M1_CHECK].items


def test_a_ledger_zip_without_a_unit_fails_and_the_audit_completes():
    clean = _run()
    run = dataclasses.replace(clean, cells=clean.cells + [Cell("zz", "f", "X", "d4", 0.0)])
    cells = _checks(run)["one owner per cell"]
    assert cells.status == "fail" and "cell zz/f: ZIP has no unit" in cells.items


def test_a_zip_has_one_owner_per_planning_channel():
    run = Run(cells=[Cell("z", "f1", "X", "d1", 1.0), Cell("z", "f2", "X", "d2", 1.0)],
              channels={"X": Channel(2, 1.0, 1.0)}, expected={("z", "f1"), ("z", "f2")}, unit_of={"z": "U"})
    cells = _checks(run)["one owner per cell"]
    assert cells.status == "fail" and "ZIP z in X: 2 owners (d1, d2)" in cells.items


def test_an_edge_does_not_add_a_vertex():
    run = Run(cells=[Cell("a", "f", "X", "d1", 1.0), Cell("b", "f", "X", "d1", 1.0)],
              channels={"X": Channel(1, 2.0, 2.0)}, graph={"vertices": ["a"], "edges": [("a", "b")]})
    contiguity = audit.check_contiguity(run)
    assert contiguity.counts["gaps"] == 1 and "X/d1: ZIP b not in the graph (graph gap)" in contiguity.items

def test_scorecard_lists_every_item():
    many = audit.Check("final bands on drawn mass", "fail", "51 breaches", [f"breach {i}" for i in range(51)])
    text = audit.scorecard([many], "toy")
    assert "- breach 50" in text and "more" not in text

# ------------------------------------------------------------------------------ the tagged catalog
@functools.cache
def _catalog():
    tag = subprocess.run(["git", "rev-parse", "--verify", "-q", f"{audit.TAG}^{{}}"], cwd=geo.ROOT,
                         capture_output=True)
    if tag.returncode != 0:
        print(f"SKIP  test_audit.py: no tag {audit.TAG}; the catalog tests did not run",
              file=sys.stderr)
        return None
    return audit.read_catalog()


@functools.cache
def _public():
    for public in (geo.PUBLIC_DIR, os.path.join(os.environ.get("TD_REPO", ""), "data", "public")):
        path = os.path.join(public, "tl_2025_us_state.zip")
        if os.path.exists(path) and geo._valid_download(path):
            return public
    print("SKIP  test_audit.py: no tl_2025_us_state.zip in data/public or $TD_REPO/data/public; "
          "the catalog fragment test did not run", file=sys.stderr)
    return None


def test_catalog_finds_the_rep_label_conflicts():
    frame = _catalog()
    if frame is None:
        return
    per = {}
    for scenario, run in audit.catalog_runs(frame):
        checks = _checks(run)
        assert checks["one owner per cell"].status == "pass", scenario
        assert checks["district count per channel"].status == "pass", scenario
        assert checks["phantom shares"].status == "pass", scenario
        assert checks["final bands on drawn mass"].status == "unverified", scenario
        per[scenario] = len(checks["rep labels"].items)
    assert len(per) == 36
    # MATH_REVIEW.md §3.6 reports 235 district-scenario pairs across all 36 scenarios
    assert sum(per.values()) == 235 and all(per.values())


def test_catalog_finds_unguarded_fragments():
    frame, public = _catalog(), _public()
    if frame is None or public is None:
        return
    graph = audit.catalog_graph(frame, public)
    assert graph["excluded"] == [] and graph["missing"] == {}
    split = sum(_checks(run)["ZIP contiguity"].counts["split"]
                for _, run in audit.catalog_runs(frame, graph))
    assert split > 0


def test_m1_excuses_a_blank_row_only_as_a_zero_opportunity_drop_of_a_dropped_channel():
    """Re-review of #116 (P1): a blank row in a channel the run does not declare excuses its cell
    only when it is a zero-opportunity DROPPED row; one with opportunity, or with no DROPPED
    reason, leaves the cell unowned.  One cell owned twice in one channel counts once."""
    p = {"vertices": ["z"], "edges": []}
    for cell, status in ((Cell("z", "f", "Y", "", 1.0), "fail"),
                         (Cell("z", "f", "Y", "", 0.0), "fail"),
                         (Cell("z", "f", "Y", "", 1.0, reason=audit.DROPPED), "fail"),
                         (Cell("z", "f", "Y", "", 0.0, reason=audit.DROPPED), "pass")):
        m1 = audit.check_m1(audit.Run([cell], {"X": Channel(1)}, polygon=p, fine=("f",)))
        assert m1.status == status, (cell, m1.items)
        assert m1.counts["no_owner"] == (status == "fail"), m1.counts
    two = audit.Run([Cell("z", "f", "X", "D1", 0.0), Cell("z", "f", "X", "D2", 0.0)],
                    {"X": Channel(2)}, polygon=p, fine=("f",))
    m1 = audit.check_m1(two)
    assert m1.status == "fail" and m1.counts["double"] == 1, m1.items
