"""tools/maps/draft_assign.py (issue #152): the draft (ZCTA -> person) assignment and its M1 audit, on a made-up graph of 18 ZCTAs in 3
states (no reference needed), and on the real graph with one person per state (skipped, with a SKIP line, without $TD_REPO/reference).

AA (a1-a4, a path) and BB (b1 b2 b3 / b4 b5 b6, a grid) and CC (c1-c8) touch only by a1-c7 and b3-c8.
NATIONAL: R1 AA and CC (no seed in CC), R2 BB, R3 BB and CC, R4 CC, R6 CC.  WH: R9 AA and BB (they do not touch).  WIFI: R10 AA.
Expected, by hand (the seeds are in `cells()`):
  AA whole to R1.  BB: seeds R2 b1, R3 b3, and b6 seen COVERED for R2 ($4 CRBG) and R3 ($2 CRBG + $9 EQH): R3 (more over both
  estimates, though R2 has the lower key and the CRBG $); b2 tie between R2 and R3: R2 (lowest key); R2 b1 b2 b4, R3 b3 b5 b6 (b5 is next to the seed b6 only).
  CC: seeds R3 c1 and c5 (an island), R4 c3, R6 c4; c2 and c6 tie three ways: R3.  R3 has {c1 c2} and {c5 c6}; the island ($10) goes to
  the neighbour it touches most: R6 (c4 twice) over R4 (c3 once, the lower key).  c8 sees b3 only: R3 'cut off' (R3 has a seed in
  CC); c7 sees a1 only, R1 has no seed in CC: 'unreachable'."""
import csv
import gzip
import importlib.util
import os
import pathlib
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("draft_assign", ROOT / "tools" / "maps" / "draft_assign.py")
da = importlib.util.module_from_spec(_spec)
sys.modules["draft_assign"] = da
_spec.loader.exec_module(da)

ZIPS = {"AA": [f"a{i}" for i in range(1, 5)], "BB": [f"b{i}" for i in range(1, 7)], "CC": [f"c{i}" for i in range(1, 9)]}
EDGES = ([("a1", "a2"), ("a2", "a3"), ("a3", "a4"), ("a1", "c7"), ("b3", "c8")]
         + [("b1", "b2"), ("b2", "b3"), ("b4", "b5"), ("b5", "b6"), ("b1", "b4"), ("b2", "b5"), ("b3", "b6")]
         + [("c1", "c2"), ("c2", "c3"), ("c2", "c4"), ("c5", "c6"), ("c6", "c3"), ("c6", "c4"), ("c5", "c4")])
GRAPH = {"vertices": sorted(z for zs in ZIPS.values() for z in zs), "edges": EDGES,
         "state": {z: s for s, zs in ZIPS.items() for z in zs}}
B = 1e9


def cell(scn, est, z, ch, usd, cls="OVERLAP", holders="", assigned="", state=None, dist="D1"):
    return {"SCENARIO": scn, "EST_SOURCE": est, "ZIP_CODE": z, "STATE": state or GRAPH["state"].get(z, "ZZ"), "NEW_DIST": dist,
            "MM_OPP": str(usd), "CHANNEL": ch, "ASSIGNED": assigned, "CLASS": cls, "N_HOLDERS": str(len(holders.split())), "HOLDERS": holders}


def person(scn, key, role, states, est="CRBG"):
    return {"SCENARIO": scn, "EST_SOURCE": est, "HOLDER": key, "SOURCE": "", "ROLE": role, "ASSIGNED_STATES": states}


def cells(scn="S"):
    cov = lambda z, p, usd, est="CRBG": cell(scn, est, z, "NATIONAL", usd, "COVERED", p, p)
    return [cov("b1", "R2", 10), cov("b3", "R3", 10), cov("b6", "R2", 4), cov("b6", "R3", 2), cov("b6", "R3", 9, "EQH"),
            cov("c1", "R3", 100), cov("c5", "R3", 10), cov("c3", "R4", 50), cov("c4", "R6", 50),
            cell(scn, "CRBG", "b2", "NATIONAL", 5, "OVERLAP", "R2 R3", "R2 R3"),
            cell(scn, "CRBG", "a1", "WH", 3 * B, "COVERED", "R9", "R9"), cell(scn, "CRBG", "b1", "WH", 9 * B, "COVERED", "R9", "R9"),
            cell(scn, "CRBG", "a2", "REGIONAL", 0.125 * B, "COVERED", "R10", "R10"),
            cell(scn, "CRBG", "b2", "OPEN", 7, "OPEN SEAT UNHELD"), cell(scn, "CRBG", "99999", "NATIONAL", 4, "GAP (UNHELD)", state="ZZ")]


def people(scn="S"):
    return [person(scn, "R1", "NATIONAL", "AA CC"), person(scn, "R2", "NATIONAL", "BB"), person(scn, "R3", "NATIONAL", "BB CC"),
            person(scn, "R4", "NATIONAL", "CC"), person(scn, "R6", "NATIONAL", "CC"), person(scn, "R9", "WH", "AA BB"),
            person(scn, "R10", "WIFI", "AA"), person(scn, "R2", "NATIONAL", "BB", "EQH")]


def built(scn="S"):
    ledger, out, m1, rep = da.one_scenario(GRAPH, da.audit.adjacency(GRAPH), cells(scn), people(scn))
    return ({(r, z): (p, why) for r, z, _, p, why in ledger}, out, {(r, p, i): rest for r, p, n, i, *rest in m1}, rep, m1)


def test_whole_state_and_roles():
    T, *_ = built()
    assert all(T["NATIONAL", z] == ("R1", "whole state") for z in ZIPS["AA"])
    assert all(T["WIFI", z] == ("R10", "whole state") for z in ZIPS["AA"])
    assert all(T["WH", z][0] == "R9" for z in ZIPS["AA"] + ZIPS["BB"])
    assert ("WH", "c1") not in T and ("WIFI", "b1") not in T           # a state with no role-r assignee is not in T_r


def test_split_state_seeds_meet_and_ties():
    T, *_ = built()
    assert {z: T["NATIONAL", z] for z in ZIPS["BB"]} == {
        "b1": ("R2", "seed"), "b2": ("R2", "grown"), "b3": ("R3", "seed"), "b4": ("R2", "grown"), "b5": ("R3", "grown"), "b6": ("R3", "seed")}


def test_seed_island_repaired_to_the_neighbour_touched_most():
    T, *_ = built()
    assert T["NATIONAL", "c1"] == ("R3", "seed") and T["NATIONAL", "c2"] == ("R3", "grown")
    assert T["NATIONAL", "c3"] == ("R4", "seed") and T["NATIONAL", "c4"] == ("R6", "seed")
    assert T["NATIONAL", "c5"] == ("R6", "repaired") and T["NATIONAL", "c6"] == ("R6", "repaired")


def test_cut_off_and_unreachable():
    T, _, _, rep, _ = built()
    assert T["NATIONAL", "c8"] == ("R3", "cut off")
    assert T["NATIONAL", "c7"] == ("", "unreachable") and rep["NATIONAL"]["unreachable"] == ["c7"]


def test_assignee_with_no_seed():
    *_, rep, rows = built()
    assert rep["NATIONAL"]["no_seed"] == [("CC", "R1")]
    r1 = [r for r in rows if r[:2] == ("NATIONAL", "R1")]
    assert len(r1) == 1 and r1[0][2] == 1 and r1[0][4] == 4 and r1[0][7] == "PASS" and r1[0][8] == "no seed in CC"   # no territory in CC


def test_m1_pieces_and_verdicts():
    *_, rows = built()
    nat = {(r[1], r[3]): r for r in rows if r[0] == "NATIONAL"}
    assert nat["R2", 1][2] == 1 and nat["R2", 1][7] == "PASS" and nat["R2", 1][4] == 3
    assert nat["R6", 1][4] == 3 and nat["R6", 1][7] == "PASS"             # c4 c5 c6
    assert nat["R4", 1][4] == 1
    # R3: {c1 c2} $100 beats {b3 b5 b6 c8} $16; the verdict is FAIL; tau = NATIONAL CRBG $ / 11
    chan = 10 + 10 + 2 + 4 + 100 + 10 + 50 + 50 + 5 + 4
    assert nat["R3", 1][2] == 2 and nat["R3", 1][4] == 2 and nat["R3", 1][5] == 100.0 and nat["R3", 1][7] == "FAIL"
    assert nat["R3", 2][4] == 4 and nat["R3", 2][5] == 16.0
    assert abs(nat["R3", 1][6] - 100 / (chan / 11)) < 1e-5


def test_two_states_that_do_not_touch_fail_with_two_pieces_and_tau_share():
    *_, rows = built()
    wh = [r for r in rows if r[:2] == ("WH", "R9")]
    assert [(r[2], r[3], r[4], r[5], r[6], r[7]) for r in wh] == [(2, 1, 6, 9 * B, 9.0, "FAIL"), (2, 2, 4, 3 * B, 3.0, "FAIL")]   # tau = 12 B / 12
    ifa = [r for r in rows if r[0] == "WIFI"]
    assert ifa[0][5] == 0.125 * B and ifa[0][6] == 0.1 and ifa[0][7] == "PASS"                                                   # tau = $1.25B


def test_cells_ledger_open_and_missing():
    T, out, *_ = built()
    got = {(e, z, ch): who for e, z, _, ch, who, _ in out}
    assert got["CRBG", "b2", "OPEN"] == "OPEN BB"
    assert got["CRBG", "99999", "NATIONAL"] == "no ZCTA"
    assert got["CRBG", "b6", "NATIONAL"] == "R3" and got["EQH", "b6", "NATIONAL"] == "R3"
    assert got["CRBG", "a1", "WH"] == "R9" and got["CRBG", "a2", "REGIONAL"] == "R10"


def test_rows_shared_across_scenarios_are_written_once():
    cs = [dict(c, SCENARIO="S1 S2") for c in cells()]
    ps = [dict(p, SCENARIO="S1 S2") for p in people()]
    ps[6]["SCENARIO"] = "S2"                                           # R10 (WIFI) only in S2
    with tempfile.TemporaryDirectory() as d:
        out = os.path.join(d, "x")
        paths = da.write(out, "x", da.run(GRAPH, cs, ps))
        assert [os.path.basename(p) for p in paths] == ["x_ledger.csv.gz", "x_cells.csv.gz", "x_m1.csv"]
        with gzip.open(paths[0], "rt", newline="") as f:
            ledger = list(csv.DictReader(f))
        with gzip.open(paths[1], "rt", newline="") as f:
            cell_rows = list(csv.DictReader(f))
        with open(paths[2], newline="") as f:
            m1 = list(csv.DictReader(f))
    assert list(ledger[0]) == da.LEDGER_COLS and list(cell_rows[0]) == da.CELL_COLS and list(m1[0]) == da.M1_COLS
    nat = [r for r in ledger if r["ROLE"] == "NATIONAL" and r["ZIP_CODE"] == "b1"]
    assert [r["SCENARIO"] for r in nat] == ["S1 S2"]
    assert [r["SCENARIO"] for r in ledger if r["ROLE"] == "WIFI" and r["ZIP_CODE"] == "a1"] == ["S2"]    # WIFI has a person only in S2
    assert not [r for r in ledger if r["ROLE"] == "WIFI" and "S1" in r["SCENARIO"]]
    assert sum(r["ZIP_CODE"] == "b1" and r["CHANNEL"] == "WH" for r in cell_rows) == 1
    assert [r["SCENARIO"] for r in m1 if r["PERSON"] == "R6"] == ["S1 S2"]


def test_conflicting_assigned_states_fail_loudly():
    bad = people() + [person("S", "R2", "NATIONAL", "BB CC", "EQH")]
    try:
        da.one_scenario(GRAPH, da.audit.adjacency(GRAPH), cells(), bad)
    except ValueError:
        return
    raise AssertionError("two different ASSIGNED_STATES for one person must raise")


def test_real_graph_one_person_per_state_is_one_piece():
    ref = os.path.join(os.environ.get("TD_REPO", str(ROOT)), "reference", "2025")
    if not os.path.exists(os.path.join(ref, "zcta_reference.csv.gz")):
        print("SKIP  test_real_graph_one_person_per_state_is_one_piece: no reference at", ref)
        return
    g = da.geo.polygon_graph(ref)
    states = sorted(set(g["state"].values()))
    ps = [person("S", f"R{i}", "NATIONAL", s) for i, s in enumerate(states, 1)]
    got = da.run(g, [], ps)
    m1 = got["S"][2]
    bad = [r for r in m1 if r[8] != "PASS"]
    assert not bad, bad[:10]
    assert len(m1) == len(states) and len(got["S"][0]) == len(g["vertices"])


def test_m1_adjacency_joins_an_approved_land_gap_of_one_state_as_m1_does():
    g = {"vertices": ["a", "b", "c"], "edges": [], "state": {"a": "AA", "b": "AA", "c": "BB"},
         "gaps": {("a", "b"): 5.0, ("a", "c"): 5.0}}
    adj = da.m1_adjacency(g)
    assert "b" in adj["a"] and "c" not in adj["a"], adj               # same-state gap joins, a gap across states does not
