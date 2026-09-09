"""app.staffdiff: before/after arithmetic on a small inline fixture.

Runs under the solver venv (no plotly, no streamlit): `app.staffdiff` imports only the
standard library.
"""
from __future__ import annotations

from app import staffdiff

TOL = 1e-9


def _reps() -> dict:
    return dict(
        reps=["R1", "R2", "R3"],
        book_share={"R1": 0.3, "R2": 0.3, "R3": 0.2},
        free_share=0.2,
        zips={
            "z1": {"top": "R1", "shares": {"R1": 1.0}, "free": 0.0, "n": 1, "weight": 0.2},
            "z2": {"top": "R1", "shares": {"R1": 0.6, "R2": 0.4}, "free": 0.0, "n": 2,
                  "weight": 0.2},
            "z3": {"top": "R2", "shares": {"R2": 1.0}, "free": 0.0, "n": 1, "weight": 0.2},
            "z4": {"top": "", "shares": {}, "free": 1.0, "n": 0, "weight": 0.1},
            "z5": {"top": "R3", "shares": {"R3": 1.0}, "free": 0.0, "n": 1, "weight": 0.15},
            "z6": {"top": "R3", "shares": {"R3": 1.0}, "free": 0.0, "n": 1, "weight": 0.15},
        },
    )


def _row(z, state, district, rep) -> dict:
    return dict(zip=z, state=state, x=0.0, y=0.0, opportunity=1.0, district=district, rep=rep)


def _rows_staffed() -> list[dict]:
    """D1 (z1, z2, z3) staffed to R1, D2 (z4, z5, z6) staffed to R3: every row in a district
    takes the district's assigned rep, as `tools/staff.py` writes it."""
    return [
        _row("z1", "S1", "D1", "R1"), _row("z2", "S1", "D1", "R1"),
        _row("z3", "S1", "D1", "R1"), _row("z4", "S2", "D2", "R3"),
        _row("z5", "S2", "D2", "R3"), _row("z6", "S2", "D2", "R3"),
    ]


def _staffing() -> dict:
    return dict(assignment={"D1": "R1", "D2": "R3"}, unstaffed_districts=[])


def test_per_rep_sums():
    result = staffdiff.per_rep(_reps(), _rows_staffed(), _staffing())
    by_rep = {row["rep"]: row for row in result}
    assert set(by_rep) == {"R1", "R2", "R3"}
    assert abs(by_rep["R1"]["after"] - 0.6) < TOL
    assert abs(by_rep["R2"]["after"] - 0.0) < TOL
    assert abs(by_rep["R3"]["after"] - 0.4) < TOL
    assert by_rep["R1"]["districts"] == ["D1"]
    assert by_rep["R2"]["districts"] == []
    assert by_rep["R3"]["districts"] == ["D2"]
    for row in result:
        assert abs(row["change"] - (row["after"] - row["before"])) < TOL
    assert abs(sum(row["after"] for row in result) - 1.0) < TOL
    assert abs(sum(row["before"] for row in result) - 0.8) < TOL


def test_summary_counts():
    s = staffdiff.summary(_reps(), _rows_staffed(), _staffing())
    assert s["reps_with_territory_before"] == 3
    assert s["reps_with_territory_after"] == 2
    assert abs(s["contested_weight_before"] - 0.2) < TOL
    assert abs(s["contested_weight_after"] - 0.0) < TOL
    assert abs(s["free_weight_before"] - 0.2) < TOL
    assert abs(s["unstaffed_weight_after"] - 0.0) < TOL


def test_district_view_sides_sum_to_one():
    view = staffdiff.district_view(_reps(), _rows_staffed(), _staffing(), "D1")
    assert abs(sum(view["before"].values()) - 1.0) < TOL
    assert abs(sum(view["after"].values()) - 1.0) < TOL
    assert abs(view["before"]["contested"] - 1 / 3) < TOL

    view2 = staffdiff.district_view(_reps(), _rows_staffed(), _staffing(), "D2")
    assert abs(sum(view2["before"].values()) - 1.0) < TOL
    assert abs(sum(view2["after"].values()) - 1.0) < TOL


def test_split_moves_weight_inside_one_district_only():
    """z2 splits off from R1 to R2 inside D1; D2 is untouched."""
    split_rows = _rows_staffed()
    split_rows[1] = _row("z2", "S1", "D1", "R2")

    before = staffdiff.district_view(_reps(), _rows_staffed(), _staffing(), "D1")
    after = staffdiff.district_view(_reps(), split_rows, _staffing(), "D1")
    assert abs(before["after"].get("R2", 0.0) - 0.0) < TOL
    assert abs(after["after"]["R2"] - 1 / 3) < TOL
    assert abs(after["after"]["R1"] - 2 / 3) < TOL

    d2_before = staffdiff.district_view(_reps(), _rows_staffed(), _staffing(), "D2")
    d2_after = staffdiff.district_view(_reps(), split_rows, _staffing(), "D2")
    assert d2_before["after"] == d2_after["after"]

    per_rep_split = {row["rep"]: row for row in staffdiff.per_rep(_reps(), split_rows,
                                                                  _staffing())}
    assert abs(per_rep_split["R1"]["after"] - 0.4) < TOL
    assert abs(per_rep_split["R2"]["after"] - 0.2) < TOL
    assert abs(per_rep_split["R3"]["after"] - 0.4) < TOL
