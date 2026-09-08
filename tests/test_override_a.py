"""test_override_a.py -- tools/override.py Mode A: relabel, balance, contiguity, diff.

Pure-function tests only: no instance file, no gazetteer, no network, matching
tests/test_state_splits_cli.py and tests/test_run_draw.py's own convention for a driver whose
CLI needs a real instance. The table is an 8-zip synthetic over four states A, B, C, D, written
through `ziptable.write`/`read` so the round trip is real; the rook graph is a hand-built path
A-B-C-D (edges A-B, B-C, C-D only), so a district that owns {A, C} without B is disconnected.
"""
from __future__ import annotations

import contextlib
import io
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
if os.path.join(ROOT, "tools") not in sys.path:
    sys.path.insert(0, os.path.join(ROOT, "tools"))

from td import ziptable                      # noqa: E402
import override                              # noqa: E402

# path A-B-C-D: A only touches B, D only touches C, B and C are the middle
ROOK = {"A": ("B",), "B": ("A", "C"), "C": ("B", "D"), "D": ("C",)}


def _base_rows() -> list[dict]:
    """Two states per district, two zips per state, mass 1.0 each: D01 = A+B, D02 = C+D,
    already perfectly balanced (4.0 apiece) and each district's owner set a rook edge."""
    return [
        dict(zip="00001", state="A", x=0.0, y=0.0, opportunity=1.0, district="D01", rep="R1"),
        dict(zip="00002", state="A", x=0.0, y=0.0, opportunity=1.0, district="D01", rep="R2"),
        dict(zip="00003", state="B", x=0.0, y=0.0, opportunity=1.0, district="D01", rep="R3"),
        dict(zip="00004", state="B", x=0.0, y=0.0, opportunity=1.0, district="D01", rep="R4"),
        dict(zip="00005", state="C", x=0.0, y=0.0, opportunity=1.0, district="D02", rep="R5"),
        dict(zip="00006", state="C", x=0.0, y=0.0, opportunity=1.0, district="D02", rep="R6"),
        dict(zip="00007", state="D", x=0.0, y=0.0, opportunity=1.0, district="D02", rep="R7"),
        dict(zip="00008", state="D", x=0.0, y=0.0, opportunity=1.0, district="D02", rep="R8"),
    ]


def _parent(tmp: str) -> list[dict]:
    """Round-trip the base rows through `ziptable.write`/`read`, the real table format."""
    path = ziptable.write(os.path.join(tmp, "draw.csv"), _base_rows())
    return ziptable.read(path)


def _by_zip(rows: list[dict]) -> dict[str, dict]:
    return {r["zip"]: r for r in rows}


# ------------------------------------------------------------------------------- apply_moves
def test_state_move_relabels_only_that_states_rows():
    with tempfile.TemporaryDirectory() as tmp:
        parent = _parent(tmp)
    rows, n = override.apply_moves(parent, [{"unit": "state", "id": "B", "to": "D02"}])
    before, after = _by_zip(parent), _by_zip(rows)

    assert n == 2
    for z in ("00003", "00004"):                                  # state B
        assert after[z]["district"] == "D02" and after[z]["rep"] == ""
    for z in ("00001", "00002", "00005", "00006", "00007", "00008"):
        assert after[z]["district"] == before[z]["district"]
        assert after[z]["rep"] == before[z]["rep"]


def test_zip_move_relabels_one_row():
    with tempfile.TemporaryDirectory() as tmp:
        parent = _parent(tmp)
    rows, n = override.apply_moves(parent, [{"unit": "zip", "id": "00002", "to": "D02"}])
    before, after = _by_zip(parent), _by_zip(rows)

    assert n == 1
    assert after["00002"]["district"] == "D02" and after["00002"]["rep"] == ""
    for z in before:
        if z != "00002":
            assert after[z]["district"] == before[z]["district"]
            assert after[z]["rep"] == before[z]["rep"]


def test_a_move_landing_back_on_the_original_district_is_not_relabelled():
    with tempfile.TemporaryDirectory() as tmp:
        parent = _parent(tmp)
    rows, n = override.apply_moves(parent, [{"unit": "zip", "id": "00001", "to": "D01"}])
    assert n == 0
    assert _by_zip(rows)["00001"]["rep"] == "R1"


def test_unknown_zip_raises_without_writing():
    with tempfile.TemporaryDirectory() as tmp:
        parent = _parent(tmp)
    try:
        override.apply_moves(parent, [{"unit": "zip", "id": "99999", "to": "D01"}])
    except ValueError as exc:
        assert "99999" in str(exc)
    else:
        raise AssertionError("expected ValueError for an unknown zip")


def test_unknown_state_raises_without_writing():
    with tempfile.TemporaryDirectory() as tmp:
        parent = _parent(tmp)
    try:
        override.apply_moves(parent, [{"unit": "state", "id": "ZZ", "to": "D01"}])
    except ValueError as exc:
        assert "ZZ" in str(exc)
    else:
        raise AssertionError("expected ValueError for an unknown state")


# ----------------------------------------------------------------------------------- mode_a
def test_balance_before_and_after_share_k():
    with tempfile.TemporaryDirectory() as tmp:
        parent = _parent(tmp)
    edits = {"moves": [{"unit": "zip", "id": "00002", "to": "D02"}]}
    _, metrics = override.mode_a(parent, edits, ROOK, 0.01)

    assert metrics["k"] == metrics["balance"]["k"] == metrics["balance_before"]["k"] == 2
    assert metrics["balance_before"]["max_dev_rel"] == 0.0        # base is perfectly balanced
    assert metrics["balance"]["max_dev_rel"] > 0.0                # moving a zip unbalances it


def test_disconnected_owner_set_when_the_bridging_state_is_elsewhere():
    """B leaves D01 for D02, C leaves D02 for D01: D01 ends up owning {A, C} with the only
    connector, B, held entirely by D02 -- disconnected in the A-B-C-D path."""
    with tempfile.TemporaryDirectory() as tmp:
        parent = _parent(tmp)
    edits = {"moves": [
        {"unit": "state", "id": "B", "to": "D02"},
        {"unit": "state", "id": "C", "to": "D01"},
    ]}
    rows, metrics = override.mode_a(parent, edits, ROOK, 0.01)

    owners = override.owner_sets(rows, 0.01)
    assert owners["D01"] == {"A", "C"}
    assert metrics["contiguity"]["D01"] is False


def test_a_district_owning_no_state_reads_disconnected():
    assert override.contiguity({"D01": set()}, ROOK) == {"D01": False}


def test_states_split_lists_a_state_a_zip_move_splits():
    with tempfile.TemporaryDirectory() as tmp:
        parent = _parent(tmp)
    edits = {"moves": [{"unit": "zip", "id": "00005", "to": "D01"}]}   # one of C's two zips
    _, metrics = override.mode_a(parent, edits, ROOK, 0.01)
    assert metrics["states_split"] == ["C"]


def test_edits_honoured_is_always_true_in_mode_a():
    with tempfile.TemporaryDirectory() as tmp:
        parent = _parent(tmp)
    _, metrics = override.mode_a(parent, {"moves": []}, ROOK, 0.01)
    assert metrics["edits_honoured"] is True
    assert metrics["mode"] == "A"


def test_mode_a_ignores_hold():
    with tempfile.TemporaryDirectory() as tmp:
        parent = _parent(tmp)
    edits = {"moves": [{"unit": "state", "id": "A", "to": "D02"}],
            "hold": {"states": ["A"], "zips": []}}
    rows, metrics = override.mode_a(parent, edits, ROOK, 0.01)
    assert _by_zip(rows)["00001"]["district"] == "D02"             # A moved despite the hold
    assert metrics["diff"]["zips_relabelled"] == 2


def test_mode_b_stub_exits_with_code_2():
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = override.mode_b()
    assert code == 2
    assert "wave 2" in out.getvalue()
