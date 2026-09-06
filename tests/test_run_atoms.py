"""
test_run_atoms.py -- the state-atom stage-1 driver (tools/run_atoms.py).

Pure-function tests only: no instance file, no gazetteer, no network.  The load-bearing one is
`test_check_hash_seed_refuses_without_the_variable` -- the search tie-breaks on set iteration
over atom names, so a run without `PYTHONHASHSEED=0` is not reproducible and the driver has to
say so rather than quietly produce a different map.
"""
from __future__ import annotations

import csv
import json
import os
import sys
import tempfile

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
if os.path.join(ROOT, "tools") not in sys.path:
    sys.path.insert(0, os.path.join(ROOT, "tools"))

import run_atoms                                # noqa: E402


def test_check_hash_seed_refuses_without_the_variable():
    run_atoms.check_hash_seed({"PYTHONHASHSEED": "0"})          # the only accepted value
    for env in ({}, {"PYTHONHASHSEED": "1"}, {"PYTHONHASHSEED": "random"}):
        try:
            run_atoms.check_hash_seed(env)
        except SystemExit as e:
            assert "PYTHONHASHSEED=0" in str(e)
        else:
            raise AssertionError(f"expected SystemExit for {env!r}")


def test_unit_arrays_appends_the_stateless_bucket():
    """The certificate must cover the same mass the draw was scored on, bucket included."""
    mass = {"AA": 4.0, "BB": 6.0}
    res = dict(atoms=["AA", "BB"], labels=np.array([0, 1]), stateless_mass=0.0,
               stateless_district=None)
    M, lab = run_atoms.unit_arrays(res, mass)
    assert list(M) == [4.0, 6.0] and list(lab) == [0, 1]

    res = dict(res, stateless_mass=2.5, stateless_district=0)
    M, lab = run_atoms.unit_arrays(res, mass)
    assert list(M) == [4.0, 6.0, 2.5] and list(lab) == [0, 1, 0]
    assert M.sum() == 12.5


def test_write_run_lays_out_a_k_directory():
    """The same shapes run_draw.py writes, so us_maps.py and measure/premium.py read them."""
    to_name = {"00002": "D02", "00001": "D01"}
    with tempfile.TemporaryDirectory() as tmp:
        run_atoms.write_run(tmp, 18, to_name, {"engine": "atoms", "k": 18})
        kdir = os.path.join(tmp, "k18")
        with open(os.path.join(kdir, "draw.csv"), encoding="utf-8") as fh:
            rows = list(csv.DictReader(fh))
        with open(os.path.join(kdir, "metrics.json"), encoding="utf-8") as fh:
            metrics = json.load(fh)
    assert [r["zip"] for r in rows] == ["00001", "00002"], "zips written in sorted order"
    assert rows[0]["district"] == "D01"
    assert metrics["engine"] == "atoms" and metrics["k"] == 18
