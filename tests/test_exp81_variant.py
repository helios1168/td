"""tools/exp81/seed_support.py: #81's variant seed on a toy ledger.

Two districts of channel X on a line: D_02 holds z1 (m 1 + 2 over two fine cells, at x = 0) and
z2 (m 1, at x = 4), so its centroid is x = 1; D_01 holds z3 (m 0, at x = 10) and z4 (m 2, at
x = 20), so its centroid is x = 20.  A not-placed cell and another channel's cells are ignored.
"""
from __future__ import annotations

import csv
import math
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                "tools", "exp81"))
import seed_support  # noqa: E402

P = {"z1": (0.0, 0.0), "z2": (4.0, 0.0), "z3": (10.0, 0.0), "z4": (20.0, 0.0), "z5": (99.0, 0.0)}
CELLS = [("X", "z1", "D_02", 1.0), ("X", "z1", "D_02", 2.0), ("X", "z2", "D_02", 1.0),
         ("X", "z3", "D_01", 0.0), ("X", "z4", "D_01", 2.0), ("X", "z5", "", 5.0),
         ("Y", "z1", "Y_01", 7.0), ("Y", "z5", "Y_01", 7.0)]


def _ledger(cells) -> str:
    fd, path = tempfile.mkstemp(suffix=".csv")
    with os.fdopen(fd, "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["scenario", "zip_code", "model_channel", "district", "m_rel", "reason"])
        for ch, z, d, m in cells:
            w.writerow(["toy", z, ch, d, m, "" if d else "not placed"])
    return path


def test_the_seed_is_each_districts_weighted_centroid_in_id_order():
    path = _ledger(CELLS)
    try:
        ids, centres = seed_support.centres(path, "X", P)
        owner, mass = seed_support.read(path, "X")
    finally:
        os.remove(path)
    assert ids == ["D_01", "D_02"]
    assert centres == [(20.0, 0.0), (1.0, 0.0)]
    assert mass == {"z1": 3.0, "z2": 1.0, "z3": 0.0, "z4": 2.0}
    # D_02: 3·1² + 1·3² = 12; D_01: z3 carries no mass, z4 sits on the centre
    assert math.isclose(seed_support.objective(owner, mass, P), 12.0)


def test_a_zip_with_two_districts_in_one_channel_stops():
    path = _ledger(CELLS + [("X", "z2", "D_01", 1.0)])
    try:
        seed_support.read(path, "X")
    except ValueError as e:
        assert "z2" in str(e)
    else:
        raise AssertionError("two districts for one ZIP were accepted")
    finally:
        os.remove(path)
