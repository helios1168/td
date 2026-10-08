"""tools/exp/contig/merge.py: two tiny single-state ledgers merge into one owner per cell under
namespaced ids, with no cell outside their union, and overlapping ZCTA sets are refused."""
from __future__ import annotations

import importlib.util
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def _merge():
    if "contig_merge" not in sys.modules:
        spec = importlib.util.spec_from_file_location(
            "contig_merge", os.path.join(HERE, "..", "tools", "exp", "contig", "merge.py"))
        mod = importlib.util.module_from_spec(spec)
        sys.modules["contig_merge"] = mod
        spec.loader.exec_module(mod)
    return sys.modules["contig_merge"]


def _row(z, district, m=1.0, f="ifa"):
    return {"scenario": "s", "zip_code": z, "current_channel": f, "state": "", "model_channel": "IFA",
            "district": district, "district_channels": "IFA" if district else "", "rep": "",
            "county": "", "cbsa": "", "place": "", "district_name": "n", "m_rel": m, "reason": ""}


def _sources():
    a = [_row("07001", "IFA_01"), _row("07002", "IFA_02", 2.0), _row("07003", "IFA_01", 0.0)]
    b = [_row("15001", "IFA_01", 3.0), _row("15002", "IFA_02"), _row("15003", "")]
    return [("NJ", a), ("PA", b)]


def test_merge_one_owner_namespaced_ids_no_extra_cell():
    mg = _merge()
    rows, ids = mg.merge_ledgers(_sources(), "merged")
    assert ids == {("NJ", "IFA", "IFA_01"): "IFA_01", ("NJ", "IFA", "IFA_02"): "IFA_02",
                   ("PA", "IFA", "IFA_01"): "IFA_03", ("PA", "IFA", "IFA_02"): "IFA_04"}
    cells = [(r["zip_code"], r["current_channel"]) for r in rows]
    assert len(cells) == len(set(cells)) == 6
    union = {(r["zip_code"], r["current_channel"]) for _, rs in _sources() for r in rs}
    assert set(cells) == union
    owner = {r["zip_code"]: r["district"] for r in rows}
    assert owner == {"07001": "IFA_01", "07002": "IFA_02", "07003": "IFA_01",
                     "15001": "IFA_03", "15002": "IFA_04", "15003": ""}
    assert all(r["scenario"] == "merged" and r["district_name"] == "" for r in rows)


def test_merge_refuses_overlapping_zctas():
    mg = _merge()
    src = _sources()
    src[1][1].append(_row("07002", "IFA_01"))
    try:
        mg.merge_ledgers(src, "merged")
    except mg.MergeError as e:
        assert "07002" in str(e)
    else:
        raise AssertionError("an overlapping ZCTA was merged")
