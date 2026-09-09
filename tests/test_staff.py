"""test_staff.py -- releasing reps (`td.model.release_reps`) and the staffing driver
(`tools/staff.py`): the fold into `S_free`, the candidate rule, and the files a run writes.

The toy is six zips in two states, three reps and two districts, with dyadic books and masses
so `share = S/M` round-trips through the `td_instance_descaled/1` file exactly:

    D01 = CA  R1 10, R2 2, R3 3, free 0.75, M 64
    D02 = NY  R1 0.0625, R2 0, R3 1, free 0.5, M 32

R2 sells nowhere in D02, which is what makes the candidate rule bite: with R3 released the
unrestricted Nash matching hands D01 to R1 and D02 to R2, and the rule forces the other way
round.  Release R1 as well and D02 has no candidate at all.
"""
from __future__ import annotations

import gzip
import json
import math
import os
import sys
import tempfile

import networkx as nx

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
for _p in (ROOT, os.path.join(ROOT, "tools")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from td import channel, model, ziptable                                      # noqa: E402
from td import instance as descaled                                          # noqa: E402
import staff                                                                 # noqa: E402

THETA, LAM = 0.40, 0.30

# zip -> (state, district, M, {rep: S}, S_free)
TOY = {
    "90001": ("CA", "D01", 32.0, {"R1": 6.0, "R2": 1.0, "R3": 1.0}, 0.5),
    "90002": ("CA", "D01", 16.0, {"R1": 3.0, "R2": 0.5, "R3": 1.0}, 0.0),
    "90003": ("CA", "D01", 16.0, {"R1": 1.0, "R2": 0.5, "R3": 1.0}, 0.25),
    "10001": ("NY", "D02", 16.0, {"R1": 0.0625, "R3": 0.5}, 0.25),
    "10002": ("NY", "D02", 8.0, {"R3": 0.25}, 0.0),
    "10003": ("NY", "D02", 8.0, {"R3": 0.25}, 0.25),
}
LABELS = {z: v[1] for z, v in TOY.items()}


def _graph() -> "nx.Graph":
    """The toy as `load_descaled` would leave it: `cand`, `S`, `M`, `S_free`, `state`."""
    G = nx.Graph()
    for z, (st, _d, M, S, free) in TOY.items():
        G.add_node(z, cand=tuple(sorted(S)), S=dict(S), M=M, S_free=free, state=st)
    return G


def _write_instance(path: str) -> str:
    """The `td_instance_descaled/1` file, shares exact because every book is dyadic."""
    zips = sorted(TOY)
    obj = dict(format=descaled.FORMAT,
               nodes=dict(z=zips,
                          m_rel=[TOY[z][2] for z in zips],
                          share=[{r: s / TOY[z][2] for r, s in TOY[z][3].items()} for z in zips],
                          state=[TOY[z][0] for z in zips],
                          share_free=[TOY[z][4] / TOY[z][2] for z in zips]),
               edges=dict(u=zips[:-1], v=zips[1:]), firm={}, meta={})
    with gzip.open(path, "wt", encoding="utf-8") as fh:
        json.dump(obj, fh)
    return path


def _run(tmp: str, out: str, *flags, reps: dict | None = None) -> tuple[dict, list[dict]]:
    """A whole driver run in `tmp`; returns `(staffing.json, the written table's rows)`.

    `reps` seeds the input table's `rep` column (`{zip: rep}`), the input a scoped run leaves
    untouched outside its scope.
    """
    inst = _write_instance(os.path.join(tmp, "instance_descaled.json.gz"))
    d = descaled.load_descaled(inst)
    table = ziptable.write(os.path.join(tmp, "draw.csv"), ziptable.build(d, {}, LABELS, reps))
    out_dir = os.path.join(tmp, out)
    assert staff.main([inst, "--table", table, "--out", out_dir, *flags]) == 0
    with open(os.path.join(out_dir, "staffing.json"), encoding="utf-8") as fh:
        return json.load(fh), ziptable.read(os.path.join(out_dir, "draw.csv"))


# ------------------------------------------------------------------------------- the fold
def test_releasing_a_rep_moves_their_book_into_the_free_book():
    G = _graph()
    H = model.release_reps(G, ["R3"])

    for z, (_st, _d, _M, S, free) in TOY.items():
        assert "R3" not in model.candidates(H, z)
        assert "R3" not in model.books(H, z)
        assert model.free_book(H, z) == free + S.get("R3", 0.0)
        assert {r: s for r, s in S.items() if r != "R3"} == model.books(H, z)
        # G itself is untouched, attribute objects included
        assert model.free_book(G, z) == free
        assert model.books(G, z) == S
        assert model.candidates(G, z) == tuple(sorted(S))


def test_releasing_nobody_changes_nothing():
    G, H = _graph(), model.release_reps(_graph(), [])
    for z in TOY:
        assert (model.books(H, z), model.free_book(H, z), model.candidates(H, z)) == \
               (model.books(G, z), model.free_book(G, z), model.candidates(G, z))


def test_a_kept_rep_values_the_released_book_at_c1_under_full_capture():
    """`u_i(z) = c1*S_i + c2*(T - S_i - S_R3) + c1*(S_free + S_R3) + lam*M`, the whole point of
    folding: at `filler_capture="full"` the vacated book is worth what the rep's own is."""
    H = model.release_reps(_graph(), ["R3"])
    kept = ["R1", "R2"]
    nodes = sorted(TOY)
    U, R = model.utilities(H, nodes, reps_order=kept, theta=THETA, lam=LAM,
                           filler_capture="full")
    c1, c2 = 1.0 - LAM, THETA * (1.0 - LAM)

    assert R == kept
    for j, z in enumerate(nodes):
        _st, _d, M, S, free = TOY[z]
        T = sum(S.values())
        for i, rep in enumerate(kept):
            if rep not in S:                     # not a candidate: held at 0 by `utilities`
                assert U[i, j] == 0.0
                continue
            s = S[rep]
            want = c1 * s + c2 * (T - s - S.get("R3", 0.0)) + \
                c1 * (free + S.get("R3", 0.0)) + LAM * M
            assert abs(U[i, j] - want) < 1e-12, (z, rep, U[i, j], want)


# -------------------------------------------------------------------------- candidate rule
def test_a_district_goes_to_a_rep_who_sells_in_it_not_to_the_best_unrestricted_match():
    """R2 has no book in D02, so the candidate rule forbids the pairing the plain Nash
    matching prefers -- `channel.stage2` gives D02 to R2, the driver gives it to R1."""
    with tempfile.TemporaryDirectory() as tmp:
        rec, rows = _run(tmp, "out", "--release", "R3", "--filler-capture", "full")

    H = model.release_reps(_graph(), ["R3"])
    free_run = channel.stage2(H, LABELS, ["R1", "R2"], theta=THETA, lam=LAM,
                              filler_capture="full")
    assert free_run["assignment"] == {"D01": "R1", "D02": "R2"}          # what Nash alone wants
    assert rec["assignment"] == {"D01": "R2", "D02": "R1"}               # what candidacy allows
    assert rec["kept"] == ["R1", "R2"] and rec["released"] == ["R3"] and rec["k"] == 2
    assert rec["unmatched_reps"] == [] and rec["unstaffed_districts"] == []

    g, R, D = channel.gain_matrix(H, LABELS, reps_order=["R1", "R2"], theta=THETA, lam=LAM,
                                  filler_capture="full")
    ir, jd = {r: i for i, r in enumerate(R)}, {d: j for j, d in enumerate(D)}
    want = {d: float(g[ir[rec["assignment"][d]], jd[d]]) for d in ("D01", "D02")}
    assert all(abs(rec["gains"][d] - want[d]) < 1e-9 for d in want)
    assert abs(rec["value"] - sum(math.log(v) for v in want.values())) < 1e-9
    # the restriction costs something: R1 would have been worth more on D01 than R2 is
    assert rec["gains"]["D01"] < float(g[ir["R1"], jd["D01"]])
    assert {r["rep"] for r in rows} == {"R1", "R2"}


def test_the_contest_table_reports_candidates_and_shares_that_sum_to_one():
    with tempfile.TemporaryDirectory() as tmp:
        rec, _rows = _run(tmp, "out", "--release", "R3", "--filler-capture", "full")

    d01, d02 = rec["contest"]["D01"], rec["contest"]["D02"]
    assert d01["candidates"] == ["R1", "R2"] and d02["candidates"] == ["R1"]
    # D01 after the fold: R1 10, R2 2, free 0.75 + 3 = 3.75, total 15.75
    assert abs(d01["share"]["R1"] - 10.0 / 15.75) < 1e-12
    assert abs(d01["share"]["R2"] - 2.0 / 15.75) < 1e-12
    assert abs(d01["free_share"] - 3.75 / 15.75) < 1e-12
    assert abs(sum(d01["share"].values()) + d01["free_share"] - 1.0) < 1e-12
    # D02: R1 0.0625, free 0.5 + 1 = 1.5, total 1.5625
    assert abs(d02["share"]["R1"] - 0.0625 / 1.5625) < 1e-12
    assert abs(d02["free_share"] - 1.5 / 1.5625) < 1e-12
    assert set(d02["g"]) == {"R1"}


# ----------------------------------------------------------------------------- the run itself
def test_the_run_writes_a_table_whose_rep_column_is_the_assignment():
    with tempfile.TemporaryDirectory() as tmp:
        rec, rows = _run(tmp, "out", "--release", "R3", "--filler-capture", "full")
        assert os.path.exists(os.path.join(tmp, "out", "timings.json"))

    assert len(rows) == len(TOY)
    for r in rows:
        assert r["rep"] == rec["assignment"].get(r["district"], "")
        assert r["district"] == LABELS[r["zip"]]                # labels are untouched
        assert r["opportunity"] == TOY[r["zip"]][2]
    assert rec["balance"]["k"] == 2 and rec["balance"]["n_districts"] == 2
    assert abs(rec["balance"]["total"] - 96.0) < 1e-9           # 64 + 32


def test_a_district_with_no_candidate_is_unstaffed_and_the_run_still_succeeds():
    """R2 is the only rep left and sells only in D01, so D02 has nobody who may take it."""
    with tempfile.TemporaryDirectory() as tmp:
        rec, rows = _run(tmp, "out", "--release", "R1,R3")

    assert rec["kept"] == ["R2"] and rec["released"] == ["R1", "R3"]
    assert rec["assignment"] == {"D01": "R2"}
    assert rec["unstaffed_districts"] == ["D02"] and rec["unmatched_reps"] == []
    assert rec["contest"]["D02"]["candidates"] == []
    assert {r["rep"] for r in rows if r["district"] == "D02"} == {""}
    assert {r["rep"] for r in rows if r["district"] == "D01"} == {"R2"}


def test_keep_and_release_name_the_same_two_splits():
    with tempfile.TemporaryDirectory() as tmp:
        by_keep, _ = _run(tmp, "keep", "--keep", "R1,R2", "--filler-capture", "full")
        by_release, _ = _run(tmp, "release", "--release", "R3", "--filler-capture", "full")
    assert by_keep == by_release


def test_an_unknown_rep_name_is_refused():
    with tempfile.TemporaryDirectory() as tmp:
        try:
            _run(tmp, "out", "--release", "R9")
        except SystemExit as e:
            assert "R9" in str(e)
        else:
            raise AssertionError("expected SystemExit for a rep the instance does not have")


# ------------------------------------------------------------------------------ --districts
def test_scoping_to_one_district_staffs_only_that_district():
    with tempfile.TemporaryDirectory() as tmp:
        rec, rows = _run(tmp, "out", "--release", "R3", "--filler-capture", "full",
                         "--districts", "D01")

    assert rec["districts"] == ["D01"]
    assert set(rec["assignment"]) == {"D01"}                # D02 never entered the matching
    assert rec["contest"].keys() == {"D01"}
    assert {r["rep"] for r in rows if r["district"] == "D01"} == {rec["assignment"]["D01"]}


def test_out_of_scope_rows_keep_the_rep_they_arrived_with():
    preset = {z: "R9" for z in TOY if TOY[z][1] == "D02"}
    with tempfile.TemporaryDirectory() as tmp:
        rec, rows = _run(tmp, "out", "--release", "R3", "--filler-capture", "full",
                         "--districts", "D01", reps=preset)

    assert rec["districts"] == ["D01"]
    assert {r["rep"] for r in rows if r["district"] == "D02"} == {"R9"}
    assert {r["rep"] for r in rows if r["district"] == "D01"} == {rec["assignment"]["D01"]}


def test_an_unknown_district_name_is_refused():
    with tempfile.TemporaryDirectory() as tmp:
        try:
            _run(tmp, "out", "--districts", "D99")
        except SystemExit as e:
            assert "D99" in str(e)
        else:
            raise AssertionError("expected SystemExit for a district the table does not have")


def test_no_districts_flag_gives_every_district_of_the_table():
    with tempfile.TemporaryDirectory() as tmp:
        rec, _rows = _run(tmp, "out", "--release", "R3", "--filler-capture", "full")

    assert rec["districts"] == ["D01", "D02"]
