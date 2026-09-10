"""test_staff_and_split.py -- `resolve_rosters` (pure) and the composed staffing/split driver
(`tools/staff_and_split.py`): one `channel.gain_matrix` call over N=1 and N>1 districts alike,
multi-rep rosters resolved and excluded from the Hungarian match before it runs, and a
contiguous split for every 2+-rep district.

The end-to-end toy mirrors `tests/test_staff.py`'s instance-building style: two districts,
D01 single-rep (R1 dominates its book) and D02 split between R2 and R3, whose books are
geographically separated -- the same shape `tests/test_district_split.py`'s geographic-split
test uses -- along a four-zip line so the split lands cleanly on the book boundary.
"""
from __future__ import annotations

import gzip
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
for _p in (ROOT, os.path.join(ROOT, "tools")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from td import ziptable                                                      # noqa: E402
from td import instance as descaled                                          # noqa: E402
import staff_and_split                                                       # noqa: E402
from staff_and_split import resolve_rosters                                  # noqa: E402


# ------------------------------------------------------------------------- resolve_rosters
def test_resolve_rosters_takes_the_top_n_candidates_by_gain():
    out = resolve_rosters(["D01"], {"D01": 2}, {"D01": ["R1", "R2", "R3"]},
                          {"D01": {"R1": 5.0, "R2": 9.0, "R3": 1.0}})
    assert out["D01"]["roster"] == ["R2", "R1"]
    assert out["D01"]["requested"] == 2 and out["D01"]["resolved"] == 2


def test_resolve_rosters_skips_a_rep_claimed_by_an_earlier_district():
    """D01 resolves to a real (2+-rep) split, so it genuinely claims both its reps; D02 must
    skip R1 even though R1 is D02's higher-gain candidate."""
    out = resolve_rosters(
        ["D01", "D02"], {"D01": 2, "D02": 1},
        {"D01": ["R1", "R4"], "D02": ["R1", "R2"]},
        {"D01": {"R1": 5.0, "R4": 4.0}, "D02": {"R1": 9.0, "R2": 3.0}})
    assert out["D01"]["roster"] == ["R1", "R4"]
    assert out["D02"]["roster"] == ["R2"]          # R1 already claimed by D01, though it
                                                    # is D02's higher-gain candidate


def test_resolve_rosters_reports_a_shortfall_without_blocking():
    out = resolve_rosters(["D01"], {"D01": 3}, {"D01": ["R1", "R2"]},
                          {"D01": {"R1": 5.0, "R2": 2.0}})
    assert out["D01"]["roster"] == ["R1", "R2"]
    assert out["D01"]["requested"] == 3 and out["D01"]["resolved"] == 2


def test_resolve_rosters_a_district_with_no_positive_gain_candidate_resolves_to_zero():
    out = resolve_rosters(["D01"], {"D01": 2}, {"D01": ["R1", "R2"]},
                          {"D01": {"R1": 0.0, "R2": -1.0}})
    assert out["D01"]["roster"] == [] and out["D01"]["resolved"] == 0


def test_resolve_rosters_only_reports_districts_named_in_multi():
    out = resolve_rosters(["D01", "D02"], {"D02": 2},
                          {"D01": ["R1"], "D02": ["R1", "R2"]},
                          {"D02": {"R1": 1.0, "R2": 1.0}})
    assert set(out) == {"D02"}


def test_resolve_rosters_only_reserves_a_roster_that_actually_becomes_a_split():
    """D01 resolves to a single rep (never becomes a real split), so it must not remove R1
    from D02's pool: a district that never actually splits must not steal a candidate from one
    that does."""
    out = resolve_rosters(
        ["D01", "D02"], {"D01": 1, "D02": 3},
        {"D01": ["R1"], "D02": ["R1", "R2", "R3"]},
        {"D01": {"R1": 5.0}, "D02": {"R1": 9.0, "R2": 8.0, "R3": 7.0}})
    assert out["D01"]["roster"] == ["R1"] and out["D01"]["resolved"] == 1
    assert out["D02"]["roster"] == ["R1", "R2", "R3"] and out["D02"]["resolved"] == 3


# ------------------------------------------------------------------------------- the driver
# zip -> (state, district, M, {rep: S})
TOY = {
    "90001": ("CA", "D01", 10.0, {"R1": 8.0, "R2": 1.0}),
    "90002": ("CA", "D01", 10.0, {"R1": 8.0, "R2": 1.0}),
    "10001": ("NY", "D02", 5.0, {"R2": 4.0}),
    "10002": ("NY", "D02", 5.0, {"R2": 4.0}),
    "10003": ("NY", "D02", 5.0, {"R3": 4.0}),
    "10004": ("NY", "D02", 5.0, {"R3": 4.0}),
}
LABELS = {z: v[1] for z, v in TOY.items()}
XY = {"90001": (0.0, 100.0), "90002": (1.0, 100.0),
     "10001": (0.0, 0.0), "10002": (1.0, 0.0), "10003": (2.0, 0.0), "10004": (3.0, 0.0)}


def _write_instance(path: str) -> str:
    zips = sorted(TOY)
    obj = dict(format=descaled.FORMAT,
               nodes=dict(z=zips,
                          m_rel=[TOY[z][2] for z in zips],
                          share=[{r: s / TOY[z][2] for r, s in TOY[z][3].items()} for z in zips],
                          state=[TOY[z][0] for z in zips],
                          share_free=[0.0] * len(zips)),
               edges=dict(u=zips[:-1], v=zips[1:]), firm={}, meta={})
    with gzip.open(path, "wt", encoding="utf-8") as fh:
        json.dump(obj, fh)
    return path


def _geom(zips: list[str]) -> dict:
    """A chain: `zips[0]`-`zips[1]`-...-`zips[-1]`, the shape `test_district_split.py`'s own
    geographic-split fixture uses."""
    return dict(cells={z: {"rings": []} for z in zips},
               proximity_zips=list(zips),
               proximity_edges=[[zips[j], zips[j + 1]] for j in range(len(zips) - 1)])


def _run(tmp: str, *flags):
    inst = _write_instance(os.path.join(tmp, "instance_descaled.json.gz"))
    d = descaled.load_descaled(inst)
    table = ziptable.write(os.path.join(tmp, "draw.csv"), ziptable.build(d, XY, LABELS))
    out_dir = os.path.join(tmp, "out")
    rc = staff_and_split.main([inst, "--table", table, "--out", out_dir, *flags])
    with open(os.path.join(out_dir, "staffing.json"), encoding="utf-8") as fh:
        staffing = json.load(fh)
    rows = ziptable.read(os.path.join(out_dir, "draw.csv"))
    return rc, staffing, rows


def test_single_rep_district_and_a_two_rep_split_together():
    with tempfile.TemporaryDirectory() as tmp:
        geom_path = os.path.join(tmp, "geom.json")
        with open(geom_path, "w", encoding="utf-8") as fh:
            json.dump(_geom(["10001", "10002", "10003", "10004"]), fh)

        rc, staffing, rows = _run(
            tmp, "--keep", "R1,R2,R3", "--districts", "D01,D02",
            "--multi", "D02:2", "--geom", geom_path)

    assert rc == 0
    # D01 goes to R1 (the dominant book); R2 is excluded from D01's candidacy because the
    # split below claims it, exactly the correctness point this driver exists for.
    assert staffing["assignment"] == {"D01": "R1"}
    assert staffing["unstaffed_districts"] == []
    assert set(staffing["split_districts"]) == {"D02"}

    d02 = staffing["split_districts"]["D02"]
    assert sorted(d02["reps"]) == ["R2", "R3"]
    assert d02["contiguous"] is True
    assert d02["pieces"] == {"R2": 1, "R3": 1}
    assert abs(sum(d02["shares"].values()) - 1.0) < 1e-9

    assert staffing["requested_multi"] == {"D02": {"requested_n": 2, "resolved_n": 2}}

    by_zip = {r["zip"]: r["rep"] for r in rows}
    assert by_zip["90001"] == "R1" and by_zip["90002"] == "R1"
    assert by_zip["10001"] == "R2" and by_zip["10002"] == "R2"
    assert by_zip["10003"] == "R3" and by_zip["10004"] == "R3"


def test_a_district_requesting_more_reps_than_it_has_candidates_never_blocks():
    with tempfile.TemporaryDirectory() as tmp:
        geom_path = os.path.join(tmp, "geom.json")
        with open(geom_path, "w", encoding="utf-8") as fh:
            json.dump(_geom(["10001", "10002", "10003", "10004"]), fh)

        # D02 has only two reps with any book (R2, R3); asking for 3 must report a shortfall,
        # not fail, and the run still writes a usable split with what it found.
        rc, staffing, rows = _run(
            tmp, "--keep", "R1,R2,R3", "--districts", "D02",
            "--multi", "D02:3", "--geom", geom_path)

    assert rc == 0
    assert staffing["requested_multi"] == {"D02": {"requested_n": 3, "resolved_n": 2}}
    assert set(staffing["split_districts"]) == {"D02"}
    assert sorted(staffing["split_districts"]["D02"]["reps"]) == ["R2", "R3"]


def test_multi_needs_geom():
    with tempfile.TemporaryDirectory() as tmp:
        try:
            _run(tmp, "--keep", "R1,R2,R3", "--multi", "D02:2")
        except SystemExit as e:
            assert "geom" in str(e)
        else:
            raise AssertionError("expected SystemExit: --multi with no --geom")


def test_multi_count_below_two_is_refused():
    with tempfile.TemporaryDirectory() as tmp:
        try:
            _run(tmp, "--keep", "R1,R2,R3", "--multi", "D02:1", "--geom", "/nonexistent.json")
        except SystemExit as e:
            assert "2 or more" in str(e)
        else:
            raise AssertionError("expected SystemExit: --multi count < 2")


def test_multi_names_a_district_outside_scope():
    with tempfile.TemporaryDirectory() as tmp:
        geom_path = os.path.join(tmp, "geom.json")
        with open(geom_path, "w", encoding="utf-8") as fh:
            json.dump(_geom(["10001", "10002"]), fh)
        try:
            _run(tmp, "--keep", "R1,R2,R3", "--districts", "D01",
                "--multi", "D02:2", "--geom", geom_path)
        except SystemExit as e:
            assert "D02" in str(e)
        else:
            raise AssertionError("expected SystemExit: --multi district outside --districts")


def test_multi_with_a_geom_that_has_no_proximity_graph_is_a_hard_failure():
    """A geom.json from before the graph was exported would silently run the unguarded greedy --
    contiguity is the whole point of `--multi`, so this must fail loudly instead, the same way
    `tools/split_district.py` fails on the same input."""
    with tempfile.TemporaryDirectory() as tmp:
        geom_path = os.path.join(tmp, "geom.json")
        with open(geom_path, "w", encoding="utf-8") as fh:
            json.dump({"districts": {}}, fh)             # no "proximity_edges" key

        inst = _write_instance(os.path.join(tmp, "instance_descaled.json.gz"))
        d = descaled.load_descaled(inst)
        table = ziptable.write(os.path.join(tmp, "draw.csv"), ziptable.build(d, XY, LABELS))
        out_dir = os.path.join(tmp, "out")
        rc = staff_and_split.main(
            [inst, "--table", table, "--keep", "R1,R2,R3", "--districts", "D01,D02",
             "--multi", "D02:2", "--geom", geom_path, "--out", out_dir])

        assert rc != 0
        assert not os.path.exists(os.path.join(out_dir, "staffing.json"))
        with open(os.path.join(out_dir, "failure.json"), encoding="utf-8") as fh:
            failure = json.load(fh)
        assert "proximity_edges" in failure["reason"]


def test_a_roster_larger_than_its_district_s_zip_count_is_capped_not_crashed():
    """`district_split.split` refuses a roster bigger than the district's own zip count
    outright (`ValueError`); the driver must cap the roster first, report the capped size, and
    never even reach that exception for this, the common trigger."""
    zips = {
        "30001": ("TX", "D03", 5.0, {"R1": 2.0, "R2": 1.0, "R3": 1.0}),
        "30002": ("TX", "D03", 5.0, {"R1": 1.0, "R2": 2.0, "R3": 1.0}),
    }
    labels = {z: v[1] for z, v in zips.items()}
    xy = {"30001": (0.0, 0.0), "30002": (1.0, 0.0)}

    with tempfile.TemporaryDirectory() as tmp:
        z_sorted = sorted(zips)
        obj = dict(format=descaled.FORMAT,
                   nodes=dict(z=z_sorted,
                              m_rel=[zips[z][2] for z in z_sorted],
                              share=[{r: s / zips[z][2] for r, s in zips[z][3].items()}
                                    for z in z_sorted],
                              state=[zips[z][0] for z in z_sorted],
                              share_free=[0.0] * len(z_sorted)),
                   edges=dict(u=[], v=[]), firm={}, meta={})
        inst = os.path.join(tmp, "inst.json.gz")
        with gzip.open(inst, "wt", encoding="utf-8") as fh:
            json.dump(obj, fh)

        d = descaled.load_descaled(inst)
        table = ziptable.write(os.path.join(tmp, "draw.csv"), ziptable.build(d, xy, labels))
        geom_path = os.path.join(tmp, "geom.json")
        with open(geom_path, "w", encoding="utf-8") as fh:
            json.dump(_geom(z_sorted), fh)

        out_dir = os.path.join(tmp, "out")
        rc = staff_and_split.main(
            [inst, "--table", table, "--keep", "R1,R2,R3", "--multi", "D03:3",
             "--geom", geom_path, "--out", out_dir])
        assert rc == 0
        with open(os.path.join(out_dir, "staffing.json"), encoding="utf-8") as fh:
            staffing = json.load(fh)

    assert staffing["requested_multi"]["D03"] == {"requested_n": 3, "resolved_n": 2}
    assert set(staffing["split_districts"]) == {"D03"}
    assert len(staffing["split_districts"]["D03"]["reps"]) == 2


def test_a_failing_split_does_not_lose_the_rest_of_the_run():
    """A split that raises must not cost the whole run its output.  The split phase now runs
    before the Hungarian match, so the failing district is not stranded either: it falls
    through and gets staffed as an ordinary single-rep district, its `requested_multi` entry
    carries the error, and every other district comes out unaffected."""
    with tempfile.TemporaryDirectory() as tmp:
        geom_path = os.path.join(tmp, "geom.json")
        with open(geom_path, "w", encoding="utf-8") as fh:
            json.dump(_geom(["10001", "10002", "10003", "10004"]), fh)

        real_split = staff_and_split.district_split.split
        staff_and_split.district_split.split = lambda *a, **kw: (_ for _ in ()).throw(
            ValueError("synthetic failure"))
        try:
            rc, staffing, rows = _run(
                tmp, "--keep", "R1,R2,R3", "--districts", "D01,D02",
                "--multi", "D02:2", "--geom", geom_path)
        finally:
            staff_and_split.district_split.split = real_split

    assert rc == 0
    assert staffing["assignment"]["D01"] == "R1"           # D01 is unaffected by D02's failure
    assert staffing["split_districts"] == {}
    assert staffing["unstaffed_districts"] == []
    assert staffing["assignment"]["D02"] in ("R2", "R3")    # staffed, not stranded
    assert "synthetic failure" in staffing["requested_multi"]["D02"]["error"]
    assert {r["rep"] for r in rows if r["district"] == "D02"} == {staffing["assignment"]["D02"]}
    assert {r["rep"] for r in rows if r["district"] == "D01"} == {"R1"}


def test_a_failing_split_frees_its_roster_to_staff_a_different_district():
    """The roster reps of a district whose split raised must be genuinely available to staff
    *any* district in the run, not only the one that failed -- the defect this guards against
    left them excluded from the whole Hungarian match."""
    zips = {
        # D01: R1 is the only book here.
        "90001": ("CA", "D01", 10.0, {"R1": 8.0}),
        "90002": ("CA", "D01", 10.0, {"R1": 8.0}),
        # D02: the multi target (R2, R3), split forced to fail.
        "10001": ("NY", "D02", 5.0, {"R2": 4.0}),
        "10002": ("NY", "D02", 5.0, {"R2": 4.0}),
        "10003": ("NY", "D02", 5.0, {"R3": 4.0}),
        "10004": ("NY", "D02", 5.0, {"R3": 4.0}),
        # D05: R2 is the *only* book here -- it can only be staffed by a rep D02's failed
        # split would otherwise have kept exclusively claimed.
        "40001": ("TX", "D05", 10.0, {"R2": 8.0}),
        "40002": ("TX", "D05", 10.0, {"R2": 8.0}),
    }
    labels = {z: v[1] for z, v in zips.items()}
    xy = {z: (float(i), 0.0) for i, z in enumerate(sorted(zips))}

    with tempfile.TemporaryDirectory() as tmp:
        z_sorted = sorted(zips)
        obj = dict(format=descaled.FORMAT,
                   nodes=dict(z=z_sorted,
                              m_rel=[zips[z][2] for z in z_sorted],
                              share=[{r: s / zips[z][2] for r, s in zips[z][3].items()}
                                    for z in z_sorted],
                              state=[zips[z][0] for z in z_sorted],
                              share_free=[0.0] * len(z_sorted)),
                   edges=dict(u=[], v=[]), firm={}, meta={})
        inst = os.path.join(tmp, "inst.json.gz")
        with gzip.open(inst, "wt", encoding="utf-8") as fh:
            json.dump(obj, fh)

        d = descaled.load_descaled(inst)
        table = ziptable.write(os.path.join(tmp, "draw.csv"), ziptable.build(d, xy, labels))
        geom_path = os.path.join(tmp, "geom.json")
        with open(geom_path, "w", encoding="utf-8") as fh:
            json.dump(_geom(["10001", "10002", "10003", "10004"]), fh)

        real_split = staff_and_split.district_split.split
        staff_and_split.district_split.split = lambda *a, **kw: (_ for _ in ()).throw(
            ValueError("synthetic failure"))
        try:
            out_dir = os.path.join(tmp, "out")
            rc = staff_and_split.main(
                [inst, "--table", table, "--keep", "R1,R2,R3", "--multi", "D02:2",
                 "--geom", geom_path, "--out", out_dir])
        finally:
            staff_and_split.district_split.split = real_split

        assert rc == 0
        with open(os.path.join(out_dir, "staffing.json"), encoding="utf-8") as fh:
            staffing = json.load(fh)

    # D05 has no book but R2's, so it can only be staffed at all if R2 -- part of D02's failed
    # roster -- is genuinely free to be matched elsewhere.
    assert staffing["assignment"] == {"D01": "R1", "D05": "R2", "D02": "R3"}
    assert staffing["unstaffed_districts"] == []
    assert staffing["split_districts"] == {}
