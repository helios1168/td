"""The night drivers' small tools (tools/exp/contig): state_extract.py writes no sales data, the
IFA index's pass verdict, warm.py's extracts and stage cleanup, the regional shell scripts."""
from __future__ import annotations

import importlib.util
import os
import sys
import tempfile

from td import data, geo

HERE = os.path.dirname(os.path.abspath(__file__))
CONTIG = os.path.join(HERE, "..", "tools", "exp", "contig")


def _import(name, file):
    spec = importlib.util.spec_from_file_location(name, os.path.join(CONTIG, file))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


state_extract = _import("contig_state_extract", "state_extract.py")


# ------------------------------------------------------------------------------ B1: masking
def _sales_extract() -> data.Extract:
    return data.Extract(("IFA",), ["10001", "10002", "20001"], ["IFA"] * 3, [1.0, 2.0, 3.0],
                        [{"R1": 0.4, "R2": 0.6}, {"R1": 1.0}, {"R2": 0.5}], [0.1, 0.2, 0.3],
                        {"R1": "F1", "R2": "F2"}, {"source": "toy"})


def test_a_state_extract_carries_no_rep_shares_share_free_or_firm_map():
    ref = {"zcta": ["10001", "10002", "20001"], "state": ["NY", "NY", "DC"]}
    real = geo.read_reference
    geo.read_reference = lambda *a, **k: ref
    try:
        with tempfile.TemporaryDirectory() as tmp:
            base, out = os.path.join(tmp, "base.json.gz"), os.path.join(tmp, "x", "ny.json.gz")
            data.write(_sales_extract(), base)
            assert data.load(base).firm and any(data.load(base).share)       # the source does carry them
            assert state_extract.main([out, "NY", "--base", base]) == 0
            got = data.load(out)
    finally:
        geo.read_reference = real
    assert got.z == ["10001", "10002"] and got.m_rel == [1.0, 2.0]           # the model's column is kept
    assert got.share == [{}, {}] and got.share_free == [0.0, 0.0] and got.firm == {}
