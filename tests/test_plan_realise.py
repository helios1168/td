"""test_plan_realise.py: tools/plan_realise.py on a hand-built plan run.

A six-zip path over three states, two used slots in the one bundle `N`, and the three cases
level 2 has to tell apart: a whole state (A, all of it to the first slot), a split state (B,
half to each slot) and a state the plan only half covers (C, half to the second slot and half
uncovered).  The uncovered half is what the residual pseudo-district `other` exists for.

Every zip carries the same national mass, so the slot masses are exact rather than a tolerance,
and the gazetteer is monkeypatched away (`run_draw.coordinates`) the way
`tests/test_state_splits_cli.py` monkeypatches `borders_report.load_committed`: the run then
needs no cache, no shapefile and no network.  The contiguity graph is written straight into the
`projections/N/cell_graph.json` cache for the same reason -- the driver reads the cache when its
key set matches, so no test here builds a Voronoi diagram.

`repair` is exercised on hand-built graphs rather than through the driver: the four cases that
decide whether it is right (a detached piece one move fixes, no admissible move, the band, an
off-plan zip) are three-node graphs, and a CLI run would bury them.
"""
from __future__ import annotations

import csv
import gzip
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
for _p in (HERE, os.path.join(ROOT, "tools"), ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import networkx as nx                               # noqa: E402

from td import channels                             # noqa: E402
from td import instance as td_instance              # noqa: E402
import plan_realise as cli                          # noqa: E402
import run_draw                                     # noqa: E402

ZIPS = [f"{10000 + i:05d}" for i in range(6)]
STATES = ["A", "A", "B", "B", "C", "C"]
REPS = ["rep0", "rep1", "rep2"]
XY = {z: (float(i), 0.0) for i, z in enumerate(ZIPS)}

# A whole to slot 0; B split; C half to slot 1, half uncovered
SHARES = [("A", "D01", 1.0), ("B", "D01", 0.5), ("B", "D02", 0.5), ("C", "D02", 0.5)]


def _base_instance(path: str) -> None:
    """A format-1 file: six unit-mass zips on a path, two reps holding book on each."""
    share = {z: {REPS[i % 3]: 0.3, REPS[(i + 1) % 3]: 0.2} for i, z in enumerate(ZIPS)}
    obj = dict(
        format=td_instance.FORMAT,
        nodes=dict(z=ZIPS, m_rel=[1.0] * 6, share=[share[z] for z in ZIPS], state=STATES,
                   share_free=[0.1] * 6),
        edges=dict(u=ZIPS[:-1], v=ZIPS[1:]),
    )
    with gzip.open(path, "wt", encoding="utf-8") as fh:
        json.dump(obj, fh)


def _write_cell_graph(run_dir: str) -> None:
    """The path graph as `plan_realise.cell_graph`'s own cache, so the run needs no geometry."""
    with open(os.path.join(run_dir, "projections", "N", "cell_graph.json"), "w",
              encoding="utf-8") as fh:
        json.dump(dict(graph=cli.GRAPH, keys=ZIPS, zips=ZIPS,
                       edges=[[ZIPS[i], ZIPS[i + 1]] for i in range(5)],
                       state_borders=[["A", "B"], ["B", "C"]]), fh)


def _build_run(run_dir: str):
    """The four things `tools/full_plan.py` leaves behind, for this toy plan."""
    os.makedirs(os.path.join(run_dir, "projections", "N"), exist_ok=True)
    base = os.path.join(run_dir, "base.json.gz")
    _base_instance(base)
    d = channels.synthesize_channels(td_instance.load_descaled(base), seed=0)
    channels.write_v2(d, os.path.join(run_dir, "instance_v2.json.gz"))

    fine = channels.fine_split(d)
    proj = channels.project(fine, "N", states=["A", "B", "C"])
    channels.write_v1(proj, os.path.join(run_dir, "projections", "N",
                                         "instance_descaled.json.gz"))
    with open(os.path.join(run_dir, "projections", "N", "state_shares.csv"), "w",
              encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["state", "district", "share", "target_mass"])
        for st, did, sh in SHARES:
            w.writerow([st, did, sh, 2.0 * sh])

    slots = [dict(id="P001", bundle="N", used=True, mass=3.0, contacts=2,
                  y={"A": 1.0, "B": 0.5}),
             dict(id="P002", bundle="N", used=True, mass=2.0, contacts=2,
                  y={"B": 0.5, "C": 0.5})]
    plan = dict(state_list=["A", "B", "C"], bundles=["N"], slots=slots,
                per_state={}, passes=[], moves=[])
    with open(os.path.join(run_dir, "plan.json"), "w", encoding="utf-8") as fh:
        json.dump(plan, fh)
    staffing = dict(assignment={"0": "rep0", "1": "rep1"}, gains={}, value=0.0,
                    criterion="nash", reps=REPS, districts=[0, 1], unmatched_reps=["rep2"],
                    unstaffed_districts=[], balance={})
    with open(os.path.join(run_dir, "staffing.json"), "w", encoding="utf-8") as fh:
        json.dump(staffing, fh)
    with open(os.path.join(run_dir, "params.json"), "w", encoding="utf-8") as fh:
        json.dump(dict(instance=base), fh)
    _write_cell_graph(run_dir)
    return fine


def _run(run_dir: str) -> None:
    orig = run_draw.coordinates
    run_draw.coordinates = lambda zips, cache=None: ({z: XY[z] for z in zips if z in XY},
                                                     [z for z in zips if z not in XY])
    try:
        assert cli.main([run_dir, "--geo-cache", "unused"]) == 0
    finally:
        run_draw.coordinates = orig


def _tables(run_dir: str):
    def read(name):
        with open(os.path.join(run_dir, name), encoding="utf-8", newline="") as fh:
            return list(csv.DictReader(fh))
    with open(os.path.join(run_dir, "realise.json"), encoding="utf-8") as fh:
        rec = json.load(fh)
    return read("assignment.csv"), read("districts.csv"), read("wholesalers.csv"), rec


def test_every_cell_is_assigned_exactly_once():
    """One row per (zip, fine channel), no cell twice and none missing: `assignment.csv` is a
    partition of the instance's cells, which is what makes its mass column sum to the plan's."""
    with tempfile.TemporaryDirectory() as run_dir:
        _build_run(run_dir)
        _run(run_dir)
        rows, _, _, _ = _tables(run_dir)

        cells = [(r["zip"], r["channel"]) for r in rows]
        assert len(cells) == len(ZIPS) * len(channels.CHANNELS) == 24
        assert len(set(cells)) == len(cells)
        assert {c for _, c in cells} == set(channels.CHANNELS)


def test_whole_states_land_whole_and_the_split_state_is_divided():
    """A is whole to the first slot; B, the only split state, gives one zip to each.  The
    uncovered half of C reads `other`, and every WH and FI cell does too: no slot serves them."""
    with tempfile.TemporaryDirectory() as run_dir:
        _build_run(run_dir)
        _run(run_dir)
        rows, _, _, _ = _tables(run_dir)

        nat = {r["zip"]: r for r in rows if r["channel"] == "N_WH"}
        assert nat[ZIPS[0]]["district"] == nat[ZIPS[1]]["district"] == "N_01"
        assert sorted(nat[z]["district"] for z in ZIPS[2:4]) == ["N_01", "N_02"]
        assert sorted(nat[z]["district"] for z in ZIPS[4:6]) == ["N_02", "other"]
        assert nat[ZIPS[0]]["bundle"] == "N" and nat[ZIPS[0]]["wholesaler"] == "rep0"

        other = [r for r in rows if r["district"] == "other"]
        assert {r["channel"] for r in other} == {"N_WH", "N_FI", "WH", "FI"}
        assert all(r["bundle"] == "" and r["wholesaler"] == "" for r in other)
        assert len([r for r in other if r["channel"] == "WH"]) == len(ZIPS)


def test_district_masses_match_the_plan_and_the_residual_is_not_folded_in():
    """Equal zip masses make level 2's answer exact: the slots keep the 3.0 and 2.0 the plan
    gave them, so the uncovered half of C stayed out rather than inflating a slot."""
    with tempfile.TemporaryDirectory() as run_dir:
        _build_run(run_dir)
        _run(run_dir)
        rows, districts, _, rec = _tables(run_dir)

        by_id = {r["district"]: r for r in districts}
        assert float(by_id["N_01"]["mass"]) == 3.0
        assert float(by_id["N_02"]["mass"]) == 2.0
        assert [r["n_zips"] for r in districts] == ["3", "2"]
        assert all(r["contiguous"] == "1" and r["staffed"] == "1" for r in districts)
        assert all(r["pieces"] == "1" for r in districts)
        assert by_id["N_01"]["states"] == "A:1,B:0.5"

        # the district mass column is the assignment table's own sum, per district
        for name in ("N_01", "N_02"):
            cells = sum(float(r["M_cell"]) for r in rows if r["district"] == name)
            assert abs(cells - float(by_id[name]["mass"])) < 1e-9

        n = rec["bundles"]["N"]
        assert n["pseudo_column"] is True and n["residual_zips"] == 1
        assert abs(n["residual_mass"] - 1.0) < 1e-9
        assert n["split_states"] == ["B", "C"] and n["status"] == "ok"

        # the graph is the cell rook graph read off the cache, not the instance's own edges
        assert n["graph"] == cli.GRAPH and n["graph_zips"] == 6 and n["graph_edges"] == 5
        assert n["components"] == 1 and n["no_cell_zips"] == 0
        assert n["pieces_before"] == n["pieces_after"] == {"N_01": 1, "N_02": 1}
        assert n["moved"] == 0 and n["off_plan"]["zips"] == 0 and n["unrepaired"] == []
        assert n["state_borders"] == 2 and n["state_borders_missing"] == []


def test_wholesaler_books_are_the_cell_books_of_the_district_they_hold():
    """`book_in_district` is `S_c` summed over the district's own cells and `book_total` over
    the whole instance, so `share_of_book_kept` is a ratio of the run's own numbers.  A rep the
    match retained nothing for still gets a row, with no district."""
    with tempfile.TemporaryDirectory() as run_dir:
        _build_run(run_dir)
        _run(run_dir)
        rows, _, whole, _ = _tables(run_dir)
        # the driver's own source of book, `instance_v2.json.gz`, whose shares are rounded to
        # six significant figures by `channels.write_v2`
        fine = cli.cell_instance(run_dir, {})

        by_rep = {r["wholesaler"]: r for r in whole}
        assert sorted(by_rep) == REPS
        assert by_rep["rep2"]["district"] == "" and float(by_rep["rep2"]["book_in_district"]) == 0

        for rep in REPS:
            total = sum(float(v) for z in fine.G
                        for v in (fine.G.nodes[z]["S_c"].get(rep) or {}).values())
            assert abs(float(by_rep[rep]["book_total"]) - total) < 1e-9

        held = {r["zip"] for r in rows if r["district"] == "N_01" and r["channel"] == "N_WH"}
        book = sum(float((fine.G.nodes[z]["S_c"].get("rep0") or {}).get(c, 0.0))
                   for z in held for c in ("N_WH", "N_FI"))
        assert abs(float(by_rep["rep0"]["book_in_district"]) - book) < 1e-9
        assert abs(float(by_rep["rep0"]["share_of_book_kept"])
                   - book / float(by_rep["rep0"]["book_total"])) < 1e-9


def test_a_rounding_size_shortfall_is_folded_back_rather_than_opening_the_column():
    """`plan.json` keeps six decimals, so a whole state can read 0.999999.  Opening `other` for
    that would cost the state a whole zip: `centers.assign` repairs every positive-target
    district into non-emptiness.  Below `RESIDUAL_TOL` the shortfall is recorded and dropped."""
    with tempfile.TemporaryDirectory() as run_dir:
        _build_run(run_dir)
        path = os.path.join(run_dir, "projections", "N", "state_shares.csv")
        with open(path, "w", encoding="utf-8", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["state", "district", "share", "target_mass"])
            for st, did, sh in SHARES:
                sh = 0.999999 if (st, did) == ("A", "D01") else sh
                w.writerow([st, did, sh, 2.0 * sh])
        _run(run_dir)
        rows, _, _, rec = _tables(run_dir)

        n = rec["bundles"]["N"]
        assert list(n["folded_states"]) == ["A"]
        assert abs(n["folded_states"]["A"] - 1e-06) < 1e-12
        assert n["pseudo_column"] is True and n["residual_zips"] == 1
        nat = {r["zip"]: r["district"] for r in rows if r["channel"] == "N_WH"}
        assert nat[ZIPS[0]] == nat[ZIPS[1]] == "N_01"


def test_bundle_channels_reads_a_named_bundle_and_a_catch_all_channel_list():
    """`channels.project` writes the name for a bundle `td.channels` knows and the channel list
    for a catch-all one, so the projection file says which cells it summed either way."""
    class _Proj:
        def __init__(self, meta):
            self.meta = meta

    assert cli.bundle_channels(_Proj({"bundle": "WH_PLUS"}), "WH_PLUS") == ("WH", "N_WH")
    assert cli.bundle_channels(_Proj({"bundle": ["N_WH"]}), "other_N_WH") == ("N_WH",)
    try:
        cli.bundle_channels(_Proj({"bundle": "nonsense"}), "nonsense")
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError for a meta['bundle'] naming no channel")


def test_district_name_is_the_bundle_and_the_slot_position():
    assert cli.district_name("WH", 2) == "WH_03"
    assert cli.wholesaler_of({"assignment": {"0": "r", "13": "s"}}) == {0: "r", 13: "s"}


# ---------------------------------------------------------------- repair, on hand-built graphs

PATH = ["p0", "p1", "p2", "p3"]


def _path_graph(n=4):
    G = nx.Graph()
    G.add_nodes_from(PATH[:n])
    G.add_edges_from((PATH[i], PATH[i + 1]) for i in range(n - 1))
    return G


def test_a_detached_piece_that_one_move_fixes_is_moved():
    """`p0 - p1 - p2`, all of split state B: the power diagram left D1 holding p0 and p2 with
    D2's p1 between them.  p2 is the lighter piece, its only settled neighbour is p1, and D2
    holds a share of B, so p2 joins D2 and both districts come back in one piece."""
    G = _path_graph(3)
    labels = {"p0": "D1", "p1": "D2", "p2": "D1"}
    M = {"p0": 2.0, "p1": 1.0, "p2": 1.0}
    states = {z: "B" for z in labels}
    out = cli.repair(G, labels, M, states, {"B": {"D1", "D2"}}, None)

    assert out["labels"] == {"p0": "D1", "p1": "D2", "p2": "D2"}
    assert out["moved"] == 1 and out["stuck"] == {}
    assert all(len(v) == 1 for v in cli.district_pieces(G, out["labels"]).values())


def test_a_piece_with_no_admissible_neighbour_stays_and_is_reported():
    """Same shape, but p2 sits in state C and the plan gives C only to D1.  Moving it would
    hand D2 territory level 0 never gave it, so it stays put and the report says why."""
    G = _path_graph(3)
    labels = {"p0": "D1", "p1": "D2", "p2": "D1"}
    M = {"p0": 2.0, "p1": 1.0, "p2": 1.0}
    states = {"p0": "B", "p1": "B", "p2": "C"}
    out = cli.repair(G, labels, M, states, {"B": {"D1", "D2"}, "C": {"D1"}}, None)

    assert out["labels"] == labels and out["moved"] == 0
    assert out["stuck"]["D1"]["zips"] == 1
    assert out["stuck"]["D1"]["reasons"] == ["neighbours hold no share of 'C'"]

    after = cli.district_pieces(G, out["labels"])
    still = cli.unrepaired(after, {"D1": {"B", "C"}, "D2": {"B"}},
                           cli.state_adjacency(G, states), out["stuck"], [])
    assert [r["district"] for r in still] == ["D1"]
    assert still[0]["pieces"] == 2 and "no share of 'C'" in still[0]["reason"]


def test_a_move_that_would_push_a_district_out_of_the_band_is_refused():
    """The same detached p2, but D2 is already at the top of the band: taking p2 would put it
    over U, so the piece stays and the masses keep the band the plan set."""
    G = _path_graph(3)
    labels = {"p0": "D1", "p1": "D2", "p2": "D1"}
    M = {"p0": 9.0, "p1": 10.0, "p2": 1.0}
    states = {z: "B" for z in labels}
    band = (8.0, 10.0)
    out = cli.repair(G, labels, M, states, {"B": {"D1", "D2"}}, band)

    assert out["labels"] == labels and out["moved"] == 0
    assert out["stuck"]["D1"]["reasons"] == [
        "the band: every admissible neighbour would rise above U"]
    assert all(cli._excess(m, band) == 0.0 for m in out["mass"].values())


def test_a_whole_state_district_is_never_opened_by_the_repair():
    """State A is unsplit, so `admissible` names one district there and no zip of A can move --
    level 0 decided that state and the repair does not reopen it.  D2's stray p3 in B does move,
    which is what makes the assertion about A worth something."""
    G = _path_graph(4)
    labels = {"p0": "D1", "p1": "D1", "p2": "D2", "p3": "D1"}
    M = {z: 1.0 for z in PATH}
    states = {"p0": "A", "p1": "A", "p2": "B", "p3": "B"}
    out = cli.repair(G, labels, M, states, {"A": {"D1"}, "B": {"D1", "D2"}}, None)

    assert out["labels"]["p0"] == out["labels"]["p1"] == "D1"
    assert out["labels"]["p3"] == "D2" and out["moved"] == 1


def test_an_off_plan_zip_is_moved_to_a_district_the_plan_admits():
    """`centers.assign` leaves a zero-mass zip unconstrained and parks it in the first column,
    so a district can come back holding a zip in a state the plan gave it no share of.  The
    repair frees those and grows them back; the zip carries no mass, so no band moves."""
    G = _path_graph(3)
    labels = {"p0": "D1", "p1": "D1", "p2": "D2"}
    M = {"p0": 1.0, "p1": 0.0, "p2": 1.0}
    states = {"p0": "A", "p1": "B", "p2": "B"}
    out = cli.repair(G, labels, M, states, {"A": {"D1"}, "B": {"D2"}}, None)

    assert out["labels"]["p1"] == "D2" and out["moved"] == 1
    assert out["off_plan"] == dict(zips=1, mass=0.0, by_district={"D1": 1})
    assert out["stuck"] == {}


def test_a_district_holding_nothing_but_off_plan_zips_keeps_them():
    """Freeing every zip a district holds would leave the plan with an empty district, which is
    worse than an off-plan one, so `off_plan` skips it."""
    G = _path_graph(2)
    labels = {"p0": "D1", "p1": "D2"}
    assert cli.off_plan(G, labels, {"p0": "A", "p1": "A"}, {"A": {"D2"}}) == {}
