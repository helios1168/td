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


def _folder(tmp, name, rows):
    from td import output
    d = os.path.join(tmp, name)
    os.makedirs(d)
    output.write_ledger(os.path.join(d, "ledger.csv"), rows)
    return d


def test_merge_source_tags_join_states_by_comma_or_plus_or_infer_them():
    import tempfile
    mg = _merge()
    assert mg.parse_source("CT,RI=a/b") == ("CT,RI", ("CT", "RI"), "a/b")
    assert mg.parse_source("AR+LA+OK=c") == ("AR+LA+OK", ("AR", "LA", "OK"), "c")
    assert mg.parse_source("TX=d") == ("TX", ("TX",), "d")
    with tempfile.TemporaryDirectory() as tmp:
        rows = [dict(_row("02108", "IFA_01"), state="MA"), dict(_row("06101", "IFA_02"), state="CT"),
                dict(_row("06102", "IFA_02"), state="CT")]
        d = _folder(tmp, "merged", rows)
        assert mg.parse_source(d) == ("CT,MA", ("CT", "MA"), d)
        assert mg.source_run(d) == f"{os.path.basename(tmp)}/merged"
    try:
        mg.parse_source("=x")
    except mg.MergeError:
        pass
    else:
        raise AssertionError("a tag with no state was accepted")


def test_merge_numbers_in_source_order_and_names_both_claimants():
    mg = _merge()
    src = list(reversed(_sources()))
    _, ids = mg.merge_ledgers(src, "merged")
    assert ids[("PA", "IFA", "IFA_01")] == "IFA_01" and ids[("NJ", "IFA", "IFA_02")] == "IFA_04"
    src[1][1].append(_row("15002", ""))
    try:
        mg.merge_ledgers(src, "merged")
    except mg.MergeError as e:
        assert "15002" in str(e) and "PA" in str(e) and "NJ" in str(e)
    else:
        raise AssertionError("a ZCTA claimed by two sources was merged")


def test_merge_window_column():
    mg = _merge()
    w = (798.74, 1148.19)
    assert [mg.window_status(m, w) for m in (798.73, 798.74, 1000.0, 1148.19, 1148.2)] == \
        ["under", "in", "in", "in", "over"]


def test_merge_gap_width_records_both_verdicts_and_lists_flips():
    mg = _merge()
    from td import audit

    def check(items):
        return audit.Check(audit.M1_CHECK, "fail" if items else "pass", "s", items)
    dflt = mg.m1_record([check(["IFA/IFA_02: neck 1", "IFA/IFA_03: neck 2",
                                f"IFA/IFA_04: {audit.MASS_NECK} x"])])
    gap = mg.m1_record([check(["IFA/IFA_03: neck 2"])])
    assert dflt["status"] == "fail" and dflt["necks"] == {"IFA/IFA_02": 1, "IFA/IFA_03": 1}
    assert dflt["failing"] == ["IFA/IFA_02", "IFA/IFA_03"] and gap["failing"] == ["IFA/IFA_03"]
    ds = [f"IFA/IFA_0{i}" for i in range(1, 5)]
    assert mg.gap_width_flips(dflt, gap, ds) == [
        {"district": "IFA/IFA_02", "m1_default": "fail", "m1_gap_width": "pass"}]
    assert mg.gap_width_flips(gap, gap, ds) == []
