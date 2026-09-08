"""test_override_b.py -- tools/override.py Mode B: translate the edits into the engine
ancestor's own flags, rerun it, and report what held.

The draw half runs end to end on the synthetic instance and fake gazetteer cache of
tests/test_run_draw_locks.py (imported, not copied): a real `run_draw.main` makes the parent
table, then `override.main` reruns `run_draw.py` as a subprocess through the parent run's own
argv.  The clip half is the translation only -- `clip_bounds` is a pure function on the 8-zip
table of tests/test_override_a.py, so it needs no MILP and no instance to be decidable.

`geo.state_rook` reads the state shapefile, which the fake cache has no business holding, so the
two tests that reach the metrics stand a hand-built rook in for it.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
for _p in (ROOT, HERE, os.path.join(ROOT, "tools")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from td import ziptable                                                        # noqa: E402
import override                                                                # noqa: E402
import run_draw                                                                # noqa: E402
from test_override_a import _base_rows                                         # noqa: E402
from test_run_draw_locks import NY_ZIPS, TX_ZIPS, _write_geo_cache, _write_instance  # noqa: E402

TOY_ROOK = {"TX": ("NY",), "NY": ("TX",)}


# --------------------------------------------------------------------------------- draw ancestor
def _draw_parent(root: str, inst: str, cache: str) -> tuple[str, str]:
    """A `draw` run directory the way `app/steps.py` writes one, with its table actually drawn.

    The argv in `step.json` is the command that produced the table, which is exactly what Mode B
    reruns; running it here in process rather than as a subprocess only saves an interpreter
    start, the arguments are the same ones.
    """
    run = os.path.join(root, "draw_toy_20260101_000000")
    os.makedirs(run)
    argv = [sys.executable, os.path.join(ROOT, "tools", "run_draw.py"), inst,
            "--k", "3", "--seeds", "0", "--workers", "1", "--geo-cache", cache, "--out", run]
    step = dict(kind="draw", parent=None,
                params=dict(k=3, seeds="0", workers=1, geo_cache=cache, instance=inst, pins=None),
                argv=argv, pid=None, started=None,
                outputs={"table": "k03/draw.csv", "metrics": "k03/metrics.json"})
    with open(os.path.join(run, "step.json"), "w", encoding="utf-8") as fh:
        json.dump(step, fh, indent=2)

    assert run_draw.main(argv[2:]) == 0
    return run, os.path.join(run, "k03", "draw.csv")


def test_mode_b_draw_reruns_the_ancestor_with_the_edits_locked():
    """Move all of TX into a district of its own and hold one NY zip where the parent put it.
    Both are locks, so both must survive a rerun that re-seeds and renames everything else."""
    with tempfile.TemporaryDirectory() as tmp:
        inst = os.path.join(tmp, "instance_descaled.json.gz")
        cache = os.path.join(tmp, "geo")
        root = os.path.join(tmp, "runs")
        out = os.path.join(tmp, "override")
        _write_instance(inst)
        _write_geo_cache(cache)
        os.makedirs(root)

        run, table = _draw_parent(root, inst, cache)
        parent = {r["zip"]: r["district"] for r in ziptable.read(table)}
        # the one free district of the rerun is named D01 (run_draw.relabel counts from the
        # lock names), so holding a zip labelled D01 would be a name collision, not a test
        held = next(z for z in NY_ZIPS if parent[z] != "D01")

        edits = os.path.join(tmp, "edits.json")
        with open(edits, "w", encoding="utf-8") as fh:
            json.dump({"moves": [{"unit": "state", "id": "TX", "to": "EAST"}],
                       "hold": {"states": [], "zips": [held]}}, fh)

        real_rook = override.geo.state_rook
        override.geo.state_rook = lambda dest=None: (TOY_ROOK, {})
        try:
            rc = override.main([inst, "--table", table, "--edits", edits, "--mode", "B",
                                "--parent", run, "--geo-cache", cache, "--out", out])
        finally:
            override.geo.state_rook = real_rook
        assert rc == 0, rc

        with open(os.path.join(out, "locks.json"), encoding="utf-8") as fh:
            locks = json.load(fh)
        assert locks == {**{z: "EAST" for z in TX_ZIPS}, held: parent[held]}

        after = {r["zip"]: r["district"] for r in ziptable.read(os.path.join(out, "draw.csv"))}
        assert all(after[z] == "EAST" for z in TX_ZIPS), after
        assert after[held] == parent[held]

        with open(os.path.join(out, "metrics.json"), encoding="utf-8") as fh:
            metrics = json.load(fh)
        assert metrics["mode"] == "B" and metrics["engine"] == "draw"
        assert metrics["engine_run"] == os.path.basename(run)
        assert metrics["engine_out"] == "engine" and metrics["k"] == 3
        assert metrics["locks"] == locks
        honoured = metrics["edits_honoured"]
        assert [m["honoured"] for m in honoured["moves"]] == [True]
        assert honoured["hold"]["zips"] == {held: True}
        assert metrics["balance"]["k"] == 3


# --------------------------------------------------------------------------- clip translation
def _split_rows() -> list[dict]:
    """The 8-zip table with state C cut in half, so a hold on C has a two-district set to keep."""
    rows = _base_rows()
    for r in rows:
        if r["zip"] == "00005":
            r["district"] = "D01"
    return rows


def test_clip_bounds_translates_moves_into_fix_and_force_and_holds_into_fix_and_freeze():
    edits = {"moves": [{"unit": "state", "id": "A", "to": "D02"},
                       {"unit": "zip", "id": "00007", "to": "D01"}],
             "hold": {"states": ["C", "B"], "zips": ["00008"]}}
    got = override.clip_bounds(_split_rows(), edits, 0.01)

    assert got["fix"]["A"] == ["D02"]                     # a state move is a bound, exactly
    assert got["force"] == [["D", "D01"]]                 # a zip move only opens the contact
    assert got["pull"] == {"00007": "D01"}                # and prefers the zip at level 2
    assert got["fix"]["C"] == ["D01", "D02"]              # the held split state keeps both
    assert got["fix"]["B"] == ["D01"]                     # a whole held state, one district
    assert got["freeze"] == {"00005": "D01", "00006": "D02", "00008": "D02"}
    assert "forbid" not in got                            # empty keys never reach --bounds


def test_a_hold_on_a_state_that_is_also_moved_keeps_the_move():
    """The move is the edit the user just made; a stale hold on the same state must not undo it
    by fixing the state back to where it was."""
    edits = {"moves": [{"unit": "state", "id": "C", "to": "D02"}],
             "hold": {"states": ["C"], "zips": []}}
    got = override.clip_bounds(_split_rows(), edits, 0.01)
    assert got["fix"] == {"C": ["D02"]} and "freeze" not in got


def test_draw_locks_lets_a_move_win_over_a_hold_on_the_same_zip():
    edits = {"moves": [{"unit": "zip", "id": "00001", "to": "D02"}],
             "hold": {"states": [], "zips": ["00001"]}}
    assert override.draw_locks(_base_rows(), edits) == {"00001": "D02"}


# ------------------------------------------------------------------------------- refusals
def _fails(argv) -> None:
    try:
        code = override.main(argv)
    except SystemExit as exc:
        assert exc.code not in (0, None), exc.code
    else:
        assert code != 0, code


def _fixture(tmp: str) -> tuple[str, str]:
    """A parent table and an edits document, both real, so a refusal is about the lineage."""
    table = ziptable.write(os.path.join(tmp, "draw.csv"), _base_rows())
    edits = os.path.join(tmp, "edits.json")
    with open(edits, "w", encoding="utf-8") as fh:
        json.dump({"moves": [{"unit": "state", "id": "A", "to": "D02"}]}, fh)
    return table, edits


def test_mode_b_without_a_parent_is_refused():
    with tempfile.TemporaryDirectory() as tmp:
        table, edits = _fixture(tmp)
        out = os.path.join(tmp, "out")
        _fails([os.path.join(tmp, "instance.json.gz"), "--table", table, "--edits", edits,
                "--mode", "B", "--out", out])
        assert not os.path.exists(os.path.join(out, "draw.csv"))


def test_a_lineage_with_no_engine_is_refused():
    """An imported table (the shipped cell) was never solved for here, so there is no driver and
    no argv to rerun it with; Mode A is the only override such a map can take."""
    with tempfile.TemporaryDirectory() as tmp:
        table, edits = _fixture(tmp)
        out = os.path.join(tmp, "out")
        root = os.path.join(tmp, "runs")
        relabel = os.path.join(root, "override_a_20260101_000001")
        shipped = os.path.join(root, "import_shipped_20260101_000000")
        for run, step in ((shipped, dict(kind="import", parent=None)),
                          (relabel, dict(kind="override", parent=os.path.basename(shipped)))):
            os.makedirs(run)
            with open(os.path.join(run, "step.json"), "w", encoding="utf-8") as fh:
                json.dump(dict(params={}, argv=[], pid=None, started=None, outputs={}, **step), fh)

        _fails([os.path.join(tmp, "instance.json.gz"), "--table", table, "--edits", edits,
                "--mode", "B", "--parent", relabel, "--out", out])
        assert not os.path.exists(os.path.join(out, "draw.csv"))
