"""End to end on the seed-0 sparse fixture (#71): spec, master, realizer, ledger, audit, names, maps.

The 51 scenario runs at the δ each channel can meet on the fixture (`test_realize.FIXTURE_DELTA`;
its own 0.10 is infeasible there, #68), and its scorecard's hard checks must pass.  The CLI runs
the disconnected-whole fixture spec to its stop, and redraws the 51 run's maps from its ledger.
TIGER/Line 2025 state polygons are needed (`data/public/` or `$TD_REPO`'s); SKIP without.
"""
from __future__ import annotations

import collections
import contextlib
import csv
import functools
import io
import json
import os
import tempfile
import tomllib

from td import output, spec
from td.__main__ import main

from tests import test_realize as tr
from tests import test_spec as ts


@functools.cache
def _run_51():
    public = ts._state_file()
    if public is None:
        return None
    raw = tomllib.load(open(ts.S51, "rb"))
    for c, dl in tr.FIXTURE_DELTA.items():
        raw["channels"][c]["delta"] = raw["channels"][c]["final_delta"] = dl
    s = spec.parse(raw, ts.S51)
    fx = ts._fixture(tuple(s.fine_channels))
    out = tempfile.mkdtemp(prefix="td-e2e-")
    res = output.run(s, fx.extract, out, fx.graph, ts._reference(), public, source="fixture seed 0")
    return res, fx, public


def test_the_51_scenario_runs_end_to_end_on_the_fixture_and_passes_its_hard_checks():
    got = _run_51()
    if got is None:
        return
    res, fx, _ = got
    fails = [(c.name, c.items[:3]) for c in res.checks if c.status == "fail"]
    assert res.verdict == "pass" and not fails, fails
    checks = {c.name: c for c in res.checks}
    for name in ("one owner per cell", "district count per channel", "final bands on drawn mass",
                 "phantom shares", "mode compliance", "one name per district", "rep labels",
                 "geography manifest is 2025", "certificate tier"):
        assert checks[name].status == "pass", (name, checks[name].summary)
    assert all("unreported" not in i for i in checks["ZIP contiguity"].items)
    with open(res.paths["scorecard"], encoding="utf-8") as fh:
        assert "**Verdict: pass**" in fh.read()
    solver = json.load(open(res.paths["solver"], encoding="utf-8"))
    assert set(solver) == {"national", "WH", "FI", "WIFI"}


def test_the_51_ledger_has_every_cell_once_and_unique_district_names():
    got = _run_51()
    if got is None:
        return
    res, fx, _ = got
    rows = output.read_ledger(res.paths["ledger"])
    cells = collections.Counter((r["zip_code"], r["current_channel"]) for r in rows)
    assert set(cells) == set(zip(fx.extract.z, fx.extract.channel)) and max(cells.values()) == 1
    assert all(r["district"] and not r["reason"] and r["rep"] == "" for r in rows)
    k = {"national": 13, "WH": 11, "FI": 24, "WIFI": 3}
    districts = collections.defaultdict(set)
    names = {}
    for r in rows:
        districts[r["model_channel"]].add(r["district"])
        assert names.setdefault(r["district"], r["district_name"]) == r["district_name"]
    assert {c: len(js) for c, js in districts.items()} == k
    assert len(set(names.values())) == len(names) == 51 and all(names.values())
    with open(res.paths["districts"], encoding="utf-8") as fh:
        assert {r["district"]: r["district_name"] for r in csv.DictReader(fh)} == names


def test_the_51_maps_are_drawn_for_every_channel_and_the_maps_command_redraws_them():
    got = _run_51()
    if got is None:
        return
    res, _, public = got
    assert set(res.paths["maps"]) == {"national", "WH", "FI", "WIFI"}
    for path in res.paths["maps"].values():
        os.remove(path)
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        assert main(["maps", res.out, "--public", public]) == 0
    assert all(os.path.exists(p) for p in res.paths["maps"].values())
    assert "national: " in buf.getvalue() and "13 districts" in buf.getvalue()


def test_the_cli_stops_the_disconnected_whole_fixture_spec_and_names_the_piece():
    public = ts._state_file()
    if public is None:
        return
    out = tempfile.mkdtemp(prefix="td-e2e-")
    err = io.StringIO()
    with contextlib.redirect_stderr(err):
        code = main(["run", os.path.join(ts.SCENARIOS, "fixture_disconnected_whole.toml"),
                     "--fixture", "0", "--public", public, "--out", out, "--no-maps"])
    assert code == 1
    assert "run stopped" in err.getvalue() and "TX_harris_el_paso" in err.getvalue(), err.getvalue()
    assert not os.listdir(out)          # it stops before solving, so nothing is written
