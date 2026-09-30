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

from td import audit, geo
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
        manifest=manifest,
        solver={"X": {"status": "optimal", "objective": 7.0, "bound": 7.0, "gap": 0.0,
                      "mip_rel_gap": 0.0}},
        names={"d1": "Alpha", "d2": "Beta", "d3": "Gamma", "d4": "Delta"},
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


def test_planted_phantom_share_fails():
    run = _run()
    run.reported[("X", "B", "d1")] = 0.1            # d1 owns no ZIP of B
    assert _fails(run) == ["phantom shares"]
    run = _run()
    run.reported[("X", "C", "d4")] += 0.05          # reported, not what the ledger draws
    assert _fails(run) == ["phantom shares"]


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
    assert _fails(run) == ["one owner per cell"]


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
    """MODEL §1 and §9 (#65 F1): a zero-opportunity unit's cells keep a blank district, carry the
    reason, and are listed; a blank owner without it, or a drop where there is opportunity, fails."""
    clean = _run()
    zero = Cell("z0", "f", "X", "", 0.0, reason=audit.DROPPED)
    run = _run(cells=clean.cells + [zero], expected=clean.expected | {("z0", "f")},
               unit_of=dict(UNIT, z0="Zero"))
    assert _fails(run) == []
    dropped = _checks(run)["dropped for zero opportunity"]
    assert dropped.status == "listed" and dropped.items == ["cell z0/f (X): dropped: zero opportunity"]
    blank = dataclasses.replace(run, cells=clean.cells + [zero._replace(reason="")])
    assert _fails(blank) == ["one owner per cell"]
    heavy = dataclasses.replace(run, cells=clean.cells + [zero._replace(m=1.0)])
    assert "dropped for zero opportunity" in _fails(heavy)


def test_a_channel_dropped_whole_is_not_counted_against_k():
    clean = _run()
    run = _run(cells=clean.cells + [Cell("y0", "f", "Y", "", 0.0, reason=audit.DROPPED)],
               channels={"X": Channel(4, 2.0, 4.0), "Y": Channel(2, 0.0, 1.0)},
               expected=clean.expected | {("y0", "f")}, unit_of=dict(UNIT, y0="Ynit"))
    assert _checks(run)["district count per channel"].status == "pass"
    assert _fails(run) == []


def test_a_ledger_zip_without_a_unit_fails_and_the_audit_completes():
    clean = _run()
    run = dataclasses.replace(clean, cells=clean.cells + [Cell("zz", "f", "X", "d4", 0.0)])
    cells = _checks(run)["one owner per cell"]
    assert cells.status == "fail" and "cell zz/f: ZIP has no unit" in cells.items


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
