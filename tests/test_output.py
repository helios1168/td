"""td.output: the ledger, its schema, the district names, the maps and the run's stops (#71).

The toy run uses real 2025 ZCTAs (Manhattan, Newark, Philadelphia, Greenwich) from the committed
reference table on a hand-drawn ZIP graph, so its CBSAs, names and principal cities are real and
it needs no download: NY holds one district, NJ + PA the other, CT has no opportunity and is
dropped, channel Y has none and is dropped whole, and one Philadelphia ZIP is not a graph vertex.
The schema test reads the tagged `scenarios.csv` header with git (SKIP without the tag).
"""
from __future__ import annotations

import contextlib
import csv
import functools
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile

from td import audit, data, geo, output, spec

from tests import test_spec as ts

NY, NJ, PA, CT = ("10001", "10002", "10003", "10004"), ("07102", "07103", "07104", "07105"), \
    ("19103", "19104", "19106", "19107"), ("06830", "06831")
OFF = "19108"                   # in the extract, not a vertex of the toy graph
MASS = {**dict.fromkeys(NY, 1.0), **dict.fromkeys(NJ, 0.375), **dict.fromkeys(PA, 0.625),
        **dict.fromkeys(CT, 0.0), OFF: 0.5}


def _toy_spec(**channel):
    raw = {"scenario": {"name": "toy", "fine_channels": ["f", "g"]},
           "channels": {"X": {"k": 2, "domain": [{"units": "all", "fine": ["f"]}], "eta": 0.1,
                              "max_dist_km": 1e9, **channel},
                        "Y": {"k": 1, "domain": [{"units": "all", "fine": ["g"]}], "eta": 0.1}}}
    return spec.parse(raw)


def _toy_inputs():
    """(extract, graph): every ZIP in f with MASS and in g with 0; chains inside each state and
    the edges NY-NJ, NJ-PA, NY-CT."""
    zs = sorted(MASS)
    extract = data.Extract(("f", "g"), [z for z in zs for _ in "fg"], [f for _ in zs for f in "fg"],
                           [m for z in zs for m in (MASS[z], 0.0)], [{}] * 2 * len(zs),
                           [0.0] * 2 * len(zs))
    edges = [(a, b) for st in (NY, NJ, PA, CT) for a, b in zip(st, st[1:])]
    edges += [(NY[-1], NJ[0]), (NJ[-1], PA[0]), (NY[0], CT[0])]
    return extract, {"vertices": sorted(set(zs) - {OFF}), "edges": edges}


@functools.cache
def _toy_run():
    out = tempfile.mkdtemp(prefix="td-output-")
    extract, graph = _toy_inputs()
    res = output.run(_toy_spec(), extract, out, graph, ts._reference(), source="toy")
    return res, output.read_ledger(res.paths["ledger"])


def _tag_header():
    try:
        p = subprocess.Popen(["git", "show", f"{audit.TAG}:scenarios.csv"], cwd=geo.ROOT,
                             stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
        line = p.stdout.readline()
        p.kill()
        p.wait()
    except OSError:
        line = ""
    if not line:
        print(f"SKIP  test_output.py: no {audit.TAG}:scenarios.csv; the schema test did not run",
              file=sys.stderr)
        return None
    return line.strip().split(",")


# ------------------------------------------------------------------------------ the ledger
def test_the_ledger_keeps_the_tagged_scenarios_csv_columns_in_order():
    head = _tag_header()
    if head is None:
        return
    assert head == list(output.LEGACY_COLUMNS), head
    res, _ = _toy_run()
    with open(res.paths["ledger"], encoding="utf-8") as fh:
        written = next(csv.reader(fh))
    assert written[:len(head)] == head and written == list(output.COLUMNS), written


def test_a_toy_run_passes_the_audit_and_writes_every_output():
    res, rows = _toy_run()
    assert res.verdict == "pass", [(c.name, c.items[:3]) for c in res.checks if c.status == "fail"]
    checks = {c.name: c for c in res.checks}
    assert checks["dropped for zero opportunity"].status == "listed"
    assert checks["certificate tier"].status == "pass"
    assert checks["geography manifest is 2025"].status == "pass"
    for key in ("solver", "ledger", "scorecard", "districts", "run"):
        assert os.path.exists(res.paths[key]), key
    assert set(res.paths["maps"]) == {"X"} and os.path.exists(res.paths["maps"]["X"])
    report = json.load(open(res.paths["run"], encoding="utf-8"))
    assert report["not_placed_zips"] == 1 and report["dropped_channels"] == ["Y"]
    assert report["dropped_units"]["X"] and "CT" in report["dropped_units"]["X"]


def test_every_cell_has_one_row_and_a_blank_district_says_why():
    _, rows = _toy_run()
    assert sorted((r["zip_code"], r["current_channel"]) for r in rows) == \
        sorted((z, f) for z in MASS for f in "fg")
    by = {(r["zip_code"], r["current_channel"]): r for r in rows}
    for z in set(MASS) - {OFF}:
        g = by[z, "g"]
        assert (g["model_channel"], g["district"], g["reason"]) == ("Y", "", output.DROPPED)
    for z in CT:
        assert (by[z, "f"]["district"], by[z, "f"]["reason"]) == ("", output.DROPPED)
    assert {(by[OFF, f]["district"], by[OFF, f]["reason"]) for f in "fg"} == {("", output.NOT_PLACED)}
    owned = [r for r in rows if r["district"]]
    assert {r["zip_code"] for r in owned} == set(NY + NJ + PA)
    assert len({by[z, "f"]["district"] for z in NY}) == 1
    assert len({by[z, "f"]["district"] for z in NJ + PA}) == 1
    assert all(r["rep"] == "" for r in rows)
    assert all(r["district_channels"] == (r["model_channel"] if r["district"] else "") for r in rows)
    assert {r["cbsa"] for r in rows if r["zip_code"] in PA} == {"37980"}
    assert all(r["county"] and r["state"] for r in rows)


def test_districts_are_named_after_their_heaviest_cbsa():
    _, rows = _toy_run()
    names = {r["district"]: r["district_name"] for r in rows if r["district"]}
    assert sorted(names.values()) == ["X New York-Newark-Jersey City, NY-NJ",
                                      "X Philadelphia-Camden-Wilmington, PA-NJ-DE-MD"], names


def test_names_that_collide_take_their_next_cbsa_then_an_ordinal():
    def row(j, cbsa, m, state="NY"):
        return {"district": j, "model_channel": "WH", "state": state, "cbsa": cbsa, "m_rel": m}
    titles = {"1": "Big, NY", "2": "Next, NY", "3": "Other, NJ"}
    rows = [row("a", "1", 5.0), row("a", "2", 1.0), row("b", "1", 4.0), row("b", "3", 2.0),
            row("c", "1", 3.0), row("d", "1", 2.0), row("e", "", 1.0, "WY"),
            {**row("f", "1", 9.0), "model_channel": "FI"}]
    names = output.name_districts(rows, titles)
    assert names == {"a": "WH Big, NY / Next, NY", "b": "WH Big, NY / Other, NJ",
                     "c": "WH Big, NY (1)", "d": "WH Big, NY (2)", "e": "WH rural WY",
                     "f": "FI Big, NY"}, names
    assert len(set(names.values())) == len(names)


# ------------------------------------------------------------------------------ the maps
def test_maps_are_drawn_only_from_the_ledger_file():
    res, _ = _toy_run()
    tmp = tempfile.mkdtemp(prefix="td-maps-")
    path = os.path.join(tmp, "ledger.csv")
    with open(res.paths["ledger"], encoding="utf-8") as src, open(path, "w", encoding="utf-8") as dst:
        r = csv.DictReader(src)
        w = csv.DictWriter(dst, fieldnames=r.fieldnames, lineterminator="\n")
        w.writeheader()
        for row in r:
            if row["district"]:
                row["district"], row["district_name"] = "X_09", "X one"
            w.writerow(row)
    drawn = output.draw_maps(path, os.path.join(tmp, "maps"), ts._reference(),
                             public=os.path.join(tmp, "none"))
    assert list(drawn) == ["X"] and drawn["X"]["districts"] == ["X_09"]
    assert os.path.exists(drawn["X"]["path"])
    assert {"New York", "Newark", "Jersey City", "Philadelphia"} <= set(drawn["X"]["labels"])
    shutil.rmtree(tmp)


def test_principal_cities_are_the_ones_the_2025_cbsa_title_names():
    areas = output.read_areas()
    titles, places = output.cbsa_titles(areas), output._places(areas, ts._reference())
    want = {"35620": ["New York", "Newark", "Jersey City"], "49180": ["Winston-Salem"],
            "34980": ["Nashville-Davidson", "Murfreesboro", "Franklin"],
            "31140": ["Louisville/Jefferson County"],
            "26420": ["Houston", "Pasadena", "The Woodlands"]}
    for code, cities in want.items():
        got = output.principal_cities(titles[code], places)
        assert [c for c, _, _ in got] == cities, (titles[code], got)
    ny = output.principal_cities(titles["35620"], places)[0]
    x, y = ts._reference().set_index("zcta").loc["10001", ["x", "y"]].astype(float)
    assert abs(ny[1] - x) < 20_000 and abs(ny[2] - y) < 20_000     # Manhattan, in EPSG:5070 m


def test_top_metros_rank_by_2025_population():
    pop = output.cbsa_population(ts._reference())
    top = sorted(pop, key=lambda c: -pop[c])[:3]
    assert top[0] == "35620" and pop["35620"] > pop["31080"] > pop["16980"], top


def test_a_full_extract_is_drawn_on_the_committed_graph():
    ref = ts._reference()
    vertices = sorted(ref.loc[ref["graph_vertex"].astype(int) == 1, "zcta"])
    extract = data.Extract(("f",), vertices, ["f"] * len(vertices), [1.0] * len(vertices),
                           [{}] * len(vertices), [0.0] * len(vertices))
    g = output.declared_graph(extract, ref, public=tempfile.mkdtemp())   # no polygons needed
    report = json.load(open(os.path.join(geo.REFERENCE_DIR, "REPORT.json"), encoding="utf-8"))
    assert g["vertices"] == vertices and len(g["edges"]) == report["graph"]["edges"]


# ------------------------------------------------------------------------------ the stops
def test_a_channel_with_no_plan_stops_the_run_after_writing_the_solver_report():
    out = tempfile.mkdtemp(prefix="td-output-")
    extract, graph = _toy_inputs()
    try:
        output.run(_toy_spec(k=3, delta=0.0, final_delta=0.0), extract, out, graph,
                   ts._reference(), maps=False)
    except output.RunError as e:
        assert "no plan for X" in str(e) and "infeasible" in str(e), str(e)
    else:
        raise AssertionError("no RunError")
    assert json.load(open(os.path.join(out, "solver.json")))["X"]["solver"]["status"] == "infeasible"
    shutil.rmtree(out)


def test_a_hook_that_td_hooks_lacks_stops_the_run_before_solving():
    import td.hooks as hooks
    assert not [k for k, v in vars(hooks).items() if callable(v) and not k.startswith("_")]
    extract, graph = _toy_inputs()
    try:
        output.run(_toy_spec(hook="split_metro"), extract, tempfile.mkdtemp(), graph,
                   ts._reference(), maps=False)
    except spec.SpecError as e:
        assert "split_metro" in str(e)
    else:
        raise AssertionError("no SpecError")


def test_the_cli_lists_run_and_maps():
    from td import __main__ as cli
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        assert cli.main(["--help"]) == 0
    assert "run <spec>" in buf.getvalue() and "maps <run dir>" in buf.getvalue()
    with contextlib.redirect_stderr(io.StringIO()):
        try:
            cli.main(["run", "no.toml"])
        except SystemExit as e:
            assert e.code == 2                  # --extract or --fixture is required
        else:
            raise AssertionError("argparse accepted a run with no extract")
