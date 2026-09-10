"""test_full_grid.py: tools/full_grid.py, the argv it builds and the table it assembles.

The pool is driven with `--dry-run`, which writes each cell's planned commands to its step logs
and runs none of them.  A real cell needs `tools/full_plan.py` on an instance whose state codes
the rook graph knows, and `tests/test_full_plan_cli.py` gets that by monkeypatching
`td.geo.state_rook` in process, which a subprocess cannot be given.  The row assembly is
covered separately, on hand-made run directories, which is where the columns a reviewer ranks
by actually come from.
"""
from __future__ import annotations

import csv
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
if os.path.join(ROOT, "tools") not in sys.path:
    sys.path.insert(0, os.path.join(ROOT, "tools"))

import full_grid as cli                            # noqa: E402

CELLS = dict(
    defaults=dict(instance="/nowhere/inst.json.gz", engine="scipy", strategy="direct",
                  time_limit=30, k=2),
    cells=[dict(tag="seq", flags=dict(route="sequential", catch_all=True)),
           dict(tag="joint", flags=dict(route="joint", dist_max=600, n_max=None))],
)


def _cells_file(tmp: str) -> str:
    path = os.path.join(tmp, "cells.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(CELLS, fh)
    return path


def _grid_rows(grid_dir: str) -> list[dict]:
    with open(os.path.join(grid_dir, "grid.csv"), encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


# ------------------------------------------------------------------------------ the cell's argv
def test_the_argv_is_full_plan_s_own_long_options():
    """A flag is the option with the dashes back: `True` is a bare flag, `None` is omitted,
    `instance` is the positional, and `--threads 2` is this runner's (trap 18)."""
    argv = cli.plan_argv("PY", dict(instance="inst.json.gz", route="joint", catch_all=True,
                                    band_lo=0.8, n_max=None, k_fixed="N=18,WH=11",
                                    warm="greedy", out="ignored"), "/out")
    assert argv[0] == "PY" and argv[1] == "-u"
    assert argv[2].endswith(os.path.join("tools", "full_plan.py"))
    assert argv[3] == "inst.json.gz"
    rest = argv[4:]
    assert "--catch-all" in rest and rest[rest.index("--catch-all") + 1] != "True"
    assert rest[rest.index("--route") + 1] == "joint"
    assert rest[rest.index("--band-lo") + 1] == "0.8"
    assert rest[rest.index("--k-fixed") + 1] == "N=18,WH=11"
    assert "--n-max" not in rest, "a None flag is omitted, not passed as the string None"
    assert rest[rest.index("--threads") + 1] == "2"
    assert rest[-2:] == ["--out", "/out"], "--out is the runner's, never the cell's"

    # a cell that names its own thread count keeps it
    argv = cli.plan_argv("PY", dict(instance="i", threads=4), "/out")
    assert argv.count("--threads") == 1 and argv[argv.index("--threads") + 1] == "4"


def test_the_three_steps_run_in_order_and_share_the_cell_s_geo_cache():
    steps = cli.step_argvs("PY", dict(instance="i", geo_cache="/geo"), "/out")
    assert [name for name, _ in steps] == list(cli.STEPS)
    realise, maps = steps[1][1], steps[2][1]
    assert realise[2].endswith("plan_realise.py") and realise[3] == "/out"
    assert maps[2].endswith("plan_maps.py") and maps[3] == "/out"
    for argv in (realise, maps):
        assert argv[-2:] == ["--geo-cache", "/geo"]

    # no cache named, no flag invented
    steps = cli.step_argvs("PY", dict(instance="i"), "/out")
    assert "--geo-cache" not in steps[1][1]


def test_defaults_are_folded_into_every_cell_and_a_duplicate_tag_is_refused():
    with tempfile.TemporaryDirectory() as tmp:
        cells = cli.load_cells(_cells_file(tmp))
        assert [c["tag"] for c in cells] == ["seq", "joint"]
        assert cells[0]["flags"]["engine"] == "scipy"        # from defaults
        assert cells[0]["flags"]["route"] == "sequential"    # the cell's own
        assert cells[1]["flags"]["route"] == "joint"

        path = os.path.join(tmp, "dup.json")
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(dict(cells=[dict(tag="a"), dict(tag="a")]), fh)
        try:
            cli.load_cells(path)
        except ValueError as exc:
            assert "duplicate" in str(exc)
        else:
            raise AssertionError("two cells may not share a tag: they share a directory")


# ----------------------------------------------------------------------------------- the pool
def test_two_cells_run_in_the_pool_and_land_one_row_each():
    with tempfile.TemporaryDirectory() as tmp:
        grid_dir = os.path.join(tmp, "grid")
        rc = cli.main([_cells_file(tmp), "--out", grid_dir, "--concurrency", "2",
                       "--geo-cache", "/geo", "--dry-run"])
        assert rc == 0

        rows = _grid_rows(grid_dir)
        assert {r["tag"] for r in rows} == {"seq", "joint"}
        assert list(rows[0]) == list(cli.COLUMNS)
        assert all(r["status"] == "dry_run" for r in rows)

        for tag in ("seq", "joint"):
            for name in cli.STEPS:
                log = os.path.join(grid_dir, tag, f"step_{name}.log")
                with open(log, encoding="utf-8") as fh:
                    text = fh.read()
                assert text.strip(), log
            with open(os.path.join(grid_dir, tag, "step_full_plan.log"),
                      encoding="utf-8") as fh:
                planned = fh.read()
            assert "--geo-cache /geo" in planned, "the runner's cache reaches the cell"
            assert "--threads 2" in planned

        assert os.path.exists(os.path.join(grid_dir, "grid.md"))
        with open(os.path.join(grid_dir, "status.json"), encoding="utf-8") as fh:
            status = json.load(fh)
        assert status["total"] == 2 and status["finished"] == 2
        assert status["running"] == [] and status["failed"] == []


def test_resume_skips_a_cell_that_already_has_a_plan_and_its_metrics():
    with tempfile.TemporaryDirectory() as tmp:
        grid_dir = os.path.join(tmp, "grid")
        cli.main([_cells_file(tmp), "--out", grid_dir, "--concurrency", "2", "--dry-run"])

        for tag in ("seq", "joint"):
            _write_run_dir(os.path.join(grid_dir, tag))
            for name in cli.STEPS:                     # the evidence a cell ran again
                os.remove(os.path.join(grid_dir, tag, f"step_{name}.log"))

        rc = cli.main([_cells_file(tmp), "--out", grid_dir, "--concurrency", "2",
                       "--dry-run", "--resume"])
        assert rc == 0
        rows = _grid_rows(grid_dir)
        assert {r["tag"] for r in rows} == {"seq", "joint"}
        assert all(r["status"] == "cached" for r in rows), rows
        assert all(r["route"] == "sequential" for r in rows), "a cached row is still derived"
        for tag in ("seq", "joint"):
            assert not os.path.exists(os.path.join(grid_dir, tag, "step_full_plan.log"))

        # without --resume the same cells run again
        cli.main([_cells_file(tmp), "--out", grid_dir, "--concurrency", "2", "--dry-run"])
        assert all(r["status"] == "dry_run" for r in _grid_rows(grid_dir))


# ------------------------------------------------------------------------------------ the row
def _write_run_dir(out_dir: str) -> None:
    """A finished cell by hand: what every column of `grid.csv` is read out of."""
    os.makedirs(os.path.join(out_dir, "maps"), exist_ok=True)

    def dump(name, obj):
        with open(os.path.join(out_dir, name), "w", encoding="utf-8") as fh:
            json.dump(obj, fh)

    dump("params.json", dict(route="sequential", band_lo=0.8, band_hi=1.2, dist_max=600,
                             n_max=None, radius_max=None, k_fixed=dict(N=2, WH=1),
                             bundles=["N", "WH", "FI"]))
    dump("timings.json", dict(wall=123.456))
    dump("staffing.json", dict(assignment={"0": "R1", "1": "R2"}, unmatched_reps=["R3"],
                               value=9.75))
    dump("realise.json", dict(bundles=dict(N=dict(residual_mass=1.5),
                                           WH=dict(residual_mass=0.5))))
    dump("plan.json", dict(
        slots=[dict(id="P1", bundle="N", used=True, y={"S0": 1.0, "S1": 0.5}),
               dict(id="P2", bundle="N", used=True, y={"S1": 0.5}),
               dict(id="P3", bundle="WH", used=True, y={"S0": 1.0, "S1": 1.0}),
               dict(id="P4", bundle="FI", used=False, y={})],
        per_state={
            "S0": {"P1": 1.0, "P3": 1.0, "P5": 1.0,
                   "residual_by_channel": {"WH": 0.0, "FI": 0.0}},
            "S1": {"P1": 0.5, "P2": 0.5, "P3": 1.0, "P5": 1.0,
                   "residual_by_channel": {"WH": 0.0, "FI": 0.0}},
            "S2": {"P6": 1.0, "residual_by_channel": {"WH": 0.0, "FI": 0.0}},
            "S3": {"P1": 1.0, "residual_by_channel": {"WH": 0.5, "FI": 0.0}},
        },
        passes=[dict(name="greedy", value={"N": 1.0}, certified=False, status="warm_start"),
                dict(name="cover_N", value=10.0, certified=True, status=0),
                dict(name="cover_WH", value=5.0, certified=False, status="time_limit"),
                dict(name="cover_FI", value=3.0, certified=True, status=0),
                dict(name="cover_merged", value=1.0, certified=True, status=0),
                dict(name="contacts", value=7.0, certified=False, status="time_limit"),
                dict(name="cover_other", value=0.0, certified=True, status="skipped")]))

    with open(os.path.join(out_dir, "maps", "metrics.csv"), "w", encoding="utf-8",
              newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["bundle", "district", "extent_km", "hull_area_km2", "mass_per_hull_area",
                    "pieces"])
        w.writerow(["N", "N_01", 100.0, 10.0, 0.5, 1])
        w.writerow(["N", "N_02", 300.0, 20.0, 0.25, 2])


def test_a_row_is_derived_from_every_artifact_the_cell_left():
    with tempfile.TemporaryDirectory() as tmp:
        _write_run_dir(tmp)
        row = cli.cell_row("cell", "ok", tmp)

        assert set(row) == set(cli.COLUMNS)
        assert row["tag"] == "cell" and row["status"] == "ok" and row["wall_s"] == 123.5
        assert row["route"] == "sequential" and row["band"] == "0.8-1.2"
        assert row["dist_max"] == 600 and row["n_max"] == "" and row["radius_max"] == ""
        assert row["k_fixed"] == "N=2,WH=1" and row["bundles"] == "N,WH,FI"

        assert (row["cover_N"], row["cover_WH"]) == (10.0, 5.0)
        assert (row["cover_FI"], row["cover_merged"]) == (3.0, 1.0)
        # the greedy pseudo-pass and a skipped stage are neither certified nor counted
        assert row["certified_passes"] == "3/5"

        assert row["districts"] == 3
        assert (row["districts_N"], row["districts_WH"], row["districts_FI"]) == (2, 1, 0)
        # S1 sends half of itself to each of two N slots: one split state, counted once
        assert (row["splits_N"], row["splits_WH"], row["splits_FI"]) == (1, 0, 0)

        assert row["states_three"] == 1 and row["states_other"] == 1
        assert row["states_merged"] == 1 and row["states_dropped"] == 1
        assert row["residual_mass"] == 2.0

        assert row["max_extent_km"] == 300.0 and row["mean_extent_km"] == 200.0
        assert row["max_hull_area_km2"] == 20.0 and row["min_mass_per_hull_area"] == 0.25
        assert row["pieces_total"] == 3

        assert row["staffed"] == 2 and row["reps_idle"] == 1
        assert row["staffing_value"] == 9.75


def test_a_cell_that_left_nothing_leaves_blanks_rather_than_raising():
    """An overnight grid outlives its worst cell: a failed one still gets a row."""
    with tempfile.TemporaryDirectory() as tmp:
        row = cli.cell_row("dead", "failed:full_plan:infeasible", tmp)
        assert row["tag"] == "dead" and row["status"] == "failed:full_plan:infeasible"
        assert all(row[c] == "" for c in cli.COLUMNS if c not in ("tag", "status"))


def test_the_ranking_puts_the_widest_coverage_first_and_a_blank_last():
    """states_three descending, then max_extent_km ascending, then the split total."""
    rows = [dict(tag="wide", states_three=40, max_extent_km=3000.0, splits_N=1, splits_WH=1,
                 splits_FI=1),
            dict(tag="tight", states_three=40, max_extent_km=900.0, splits_N=2, splits_WH=0,
                 splits_FI=0),
            dict(tag="fewer", states_three=10, max_extent_km=100.0, splits_N=0, splits_WH=0,
                 splits_FI=0),
            dict(tag="dead", states_three="", max_extent_km="", splits_N="", splits_WH="",
                 splits_FI="")]
    assert [r["tag"] for r in sorted(rows, key=cli.rank_key)] == \
        ["tight", "wide", "fewer", "dead"]
