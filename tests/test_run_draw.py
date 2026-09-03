"""
test_run_draw.py -- the stage-1 scenario runner (tools/run_draw.py): parsers, scenario
merge/validation, and the (k, seed) sweep.

Pure-function tests only: no instance file, no gazetteer, no network.  `run_sweep`'s
process-pool path is exercised on the tiny `heavy_cluster` fixture from `test_centers.py`, kept
small (k in {2, 3}, two seeds) since macOS `spawn` forks a fresh interpreter per worker.
"""
from __future__ import annotations

import contextlib
import io
import json
import os
import sys
import tempfile

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
if os.path.join(ROOT, "tools") not in sys.path:
    sys.path.insert(0, os.path.join(ROOT, "tools"))

import run_draw                              # noqa: E402
from test_centers import heavy_cluster       # noqa: E402


# ------------------------------------------------------------------------------- parse_k/seeds
def test_parse_k_ranges_and_lists():
    assert run_draw.parse_k(["8-16"]) == list(range(8, 17))
    assert run_draw.parse_k(["8", "10", "8"]) == [8, 10]
    for bad in (["3-2"], ["x"], ["0"]):
        try:
            run_draw.parse_k(bad)
        except ValueError:
            pass
        else:
            raise AssertionError(f"expected ValueError for {bad!r}")


def test_parse_seeds_range():
    assert run_draw.parse_seeds(["0-4"]) == [0, 1, 2, 3, 4]


# ------------------------------------------------------------------------------------ parse_pin
def test_parse_pin():
    assert run_draw.parse_pin("SOUTHWEST=TX,OK") == ("SOUTHWEST", ("TX", "OK"))
    assert run_draw.parse_pin("x=tx,ok") == ("x", ("TX", "OK"))
    for bad in ("SOUTHWEST TX,OK", "NAME=", "NAME=TEX"):
        try:
            run_draw.parse_pin(bad)
        except ValueError:
            pass
        else:
            raise AssertionError(f"expected ValueError for {bad!r}")


# -------------------------------------------------------------------------------- load_scenario
def _write_json(payload) -> str:
    fh = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False)
    json.dump(payload, fh)
    fh.close()
    return fh.name


def test_load_scenario_merges_file_and_flags():
    path = _write_json({"fix": {"A": ["TX"]}})
    try:
        sc = run_draw.load_scenario(path, [], ["B=FL"])
        assert sc.fix == {"A": ("TX",)}
        assert sc.anchor == {"B": ("FL",)}
    finally:
        os.remove(path)


def test_load_scenario_rejects_duplicate_name():
    path = _write_json({"fix": {"A": ["TX"]}})
    try:
        try:
            run_draw.load_scenario(path, ["A=OK"], [])
        except ValueError as e:
            assert "A" in str(e)
        else:
            raise AssertionError("expected ValueError for a duplicate district name")
    finally:
        os.remove(path)


def test_load_scenario_rejects_duplicate_state():
    path = _write_json({"fix": {"A": ["TX"]}, "anchor": {"B": ["TX"]}})
    try:
        try:
            run_draw.load_scenario(path, [], [])
        except ValueError as e:
            assert "TX" in str(e)
        else:
            raise AssertionError("expected ValueError for a state pinned twice")
    finally:
        os.remove(path)


def test_load_scenario_rejects_solver_id_collision():
    path = _write_json({"fix": {"D07": ["TX"]}})
    try:
        try:
            run_draw.load_scenario(path, [], [])
        except ValueError as e:
            assert "D07" in str(e)
        else:
            raise AssertionError("expected ValueError for a name colliding with a solver id")
    finally:
        os.remove(path)


def test_load_scenario_rejects_unknown_key():
    path = _write_json({"foo": {}})
    try:
        try:
            run_draw.load_scenario(path, [], [])
        except ValueError as e:
            assert "foo" in str(e)
        else:
            raise AssertionError("expected ValueError for an unknown top-level key")
    finally:
        os.remove(path)


# ------------------------------------------------------------------------------- expand_states
def test_expand_states_maps_pinned_states_only():
    sc = run_draw.Scenario(fix={"A": ("TX",)}, anchor={"B": ("FL",)})
    states = {"z1": "TX", "z2": "FL", "z3": "NY", "z4": "TX"}
    out = run_draw.expand_states(sc, states)
    assert out == {"z1": "A", "z4": "A", "z2": "B"}


def test_expand_states_warns_on_uncovered_state():
    sc = run_draw.Scenario(fix={"A": ("TX",)}, anchor={"C": ("GA",)})
    states = {"z1": "TX"}
    err = io.StringIO()
    with contextlib.redirect_stderr(err):
        run_draw.expand_states(sc, states)
    assert "GA" in err.getvalue() and "C" in err.getvalue()


# ------------------------------------------------------------------------------------ solver_k
def test_solver_k():
    sc = run_draw.Scenario(fix={"A": ("TX",), "B": ("OK",)},
                           anchor={f"C{i}": ("ST",) for i in range(6)})
    assert run_draw.solver_k(8, sc) == 6

    sc2 = run_draw.Scenario(fix={"A": ("TX",), "B": ("OK",), "C": ("NM",)},
                            anchor={f"D{i}": ("ST",) for i in range(6)})
    try:
        run_draw.solver_k(8, sc2)
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError: too few solver slots for the anchors")


# ------------------------------------------------------------------------------------- relabel
def test_relabel_anchors_and_solver_ids():
    zips = ["z1", "z2", "z3", "z4"]
    labels = np.array([0, 1, 2, 2])
    out = run_draw.relabel(labels, zips, ["NYC"])
    assert out == {"z1": "NYC", "z2": "D01", "z3": "D02", "z4": "D02"}


# ------------------------------------------------------------------------------------- complete
def test_complete_places_missing_among_non_fixed_districts():
    placed_zips = ["z1", "z2", "z3", "z4"]
    labels = np.array([0, 1, 1, 2])                    # anchor NYC, D01, D01, D02
    anchor_names = ["NYC"]
    pinned = {"f1": "SOUTH"}                            # a fixed district's own zip
    missing = ["m1"]
    states = {"z1": "NY", "z2": "TX", "z3": "TX", "z4": "FL", "f1": "GA", "m1": "TX"}
    M = {"z1": 10.0, "z2": 20.0, "z3": 20.0, "z4": 15.0, "f1": 5.0, "m1": 8.0}

    out = run_draw.complete(labels, placed_zips, states, missing, M,
                            pinned=pinned, anchor_names=anchor_names)
    assert out["f1"] == "SOUTH"
    # m1 is TX, and D01 holds both TX zips (z2, z3): plurality places it there
    assert out["m1"] == "D01"
    assert out["m1"] != "SOUTH"


# --------------------------------------------------------------------------------- summary_rows
def test_summary_rows_new_columns():
    completed = {"z1": "D01", "z2": "D01", "z3": "D02"}
    M_by_zip = {"z1": 10.0, "z2": 30.0, "z3": 20.0}
    states = {"z1": "TX", "z2": "TX", "z3": "FL"}
    assignment = {"D01": "Alice", "D02": "Bob"}
    modes = {"D01": "anchor"}
    gains = {"D01": 5.0}

    rows = run_draw.summary_rows(completed, M_by_zip, states, assignment,
                                 modes=modes, gains=gains, target=30.0)
    by_d = {r["district"]: r for r in rows}

    d1 = by_d["D01"]
    assert d1["mode"] == "anchor"
    assert d1["M"] == 40.0
    assert d1["vs_target"] == 40.0 / 30.0 - 1
    assert d1["n_states"] == 1
    assert d1["max_zip_M"] == 30.0
    assert d1["max_zip_share"] == 0.75
    assert d1["median_zip_M"] == 20.0
    assert d1["gain"] == 5.0

    d2 = by_d["D02"]
    assert d2["mode"] == "solver"
    assert d2["gain"] is None
    assert d2["vs_target"] == 20.0 / 30.0 - 1

    for r in rows:
        assert r["max_zip_share"] <= 1.0


# ------------------------------------------------------------------------------------ sweep_row
def test_sweep_row_columns_and_no_hand_drawn():
    # target = 306/3 = 102; vs_target = -1.96%, -7.84%, +9.80% -- one within 5%, all within 10%
    rows = [
        dict(district="D01", M=100.0, mode="solver", vs_target=0.0),
        dict(district="D02", M=94.0, mode="solver", vs_target=0.0),
        dict(district="D03", M=112.0, mode="solver", vs_target=0.0),
    ]
    per_draw = [dict(seed=7)]
    best = dict(draw=0, value=12.3, unstaffed_districts=[])
    sc = run_draw.Scenario(fix={}, anchor={})

    row = run_draw.sweep_row(3, rows, per_draw, best, sc)
    for col in run_draw._SWEEP_COLS:
        assert col in row, col
    assert row["n_within_10pct"] == 3
    assert row["n_within_5pct"] == 1
    assert row["cv"] > 0
    assert row["worst_hand_drawn_vs_target"] is None
    assert row["winner_seed"] == 7
    assert row["n_unstaffed"] == 0
    assert row["n_fixed"] == 0 and row["n_anchor"] == 0


# ------------------------------------------------------------------------------------ run_sweep
def test_run_sweep_serial_matches_pooled():
    xy, M = heavy_cluster()
    ks, seeds = [2, 3], [0, 1]
    serial = run_draw.run_sweep(ks, seeds, xy, M, None, workers=1)
    pooled = run_draw.run_sweep(ks, seeds, xy, M, None, workers=2)
    for k in ks:
        s_by_seed = {r["seed"]: np.asarray(r["labels"]).tolist() for r in serial[k]}
        p_by_seed = {r["seed"]: np.asarray(r["labels"]).tolist() for r in pooled[k]}
        assert s_by_seed == p_by_seed, k
        for group in (serial[k], pooled[k]):
            nashes = [r["nash"] for r in group]
            assert nashes == sorted(nashes, reverse=True), (k, nashes)
