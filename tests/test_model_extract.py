"""
test_model_extract.py -- `tools/snowflake/model_extract.py`: 02_model_extract.sql's CSV to td_instance_descaled/3 files.

A synthetic CSV (the SQL's columns, made-up values): the files load, m_rel has median 1, a cell's M is the sum of its CSV
rows once (kappa_usd x m_rel adds back to the CSV), a blank label is the fine channel `blank` and stays, a ZIP outside CONUS
is kept in the file and counted by `conus`, a nonzero MUST_BE_ZERO check refuses with nothing written.
"""
from __future__ import annotations

import contextlib
import csv
import io
import json
import os
import statistics
import sys
import tempfile

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.join(ROOT, "tools", "snowflake"))
import model_extract  # noqa: E402
from td import data  # noqa: E402

HEAD = ["LAYER", "SOURCE", "NAME", "ZIP_CODE", "STATE", "DIST_CH", "NEW_DIST", "CHANNEL", "HOLDER", "MM_OPP", "N_CELLS",
        "VALUE", "MUST_BE_ZERO"]
# (source, zip, dist_ch, new_dist, channel, mm_opp): 'Wells (WH)' and 'wells wh' are one fine channel, '' and None a blank one
OPP = [("A", "02134", "IFA", "IFA", "ifa", 100.0), ("A", "02134", "IFA", "IFA", "ifa", 50.0),
       ("A", "10001", "Wells (WH)", "IFA", "ifa", 300.0), ("A", "10001", "wells wh", "WH", "ifa", 10.0),
       ("A", "60601", "", "FP", "ifa", 40.0), ("A", "99501", "IFA", "IFA", "ifa", 5.0),
       ("B", "02134", "IFA", "IFA", "ifa", 7.0)]


def _csv(path, checks=()):
    rows = [["OPP", s, "", z, "", d, n, c, "", m, 1, "", ""] for s, z, d, n, c, m in OPP]
    rows += [["TERR", "A", "", "02134", "MA", "", "", "ifa", "R1", "", "", "", ""]]
    rows += [["CHECKS", s, nm, "", "", "", "", "", "", "", "", v, z] for s, nm, v, z in checks]
    with open(path, "w", newline="", encoding="utf-8") as fh:
        csv.writer(fh, lineterminator="\n").writerows([HEAD] + rows)


def _run(path, out):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        model_extract.main([path, "--out", out])
    return buf.getvalue()


def test_files_load_and_add_back():
    with tempfile.TemporaryDirectory() as tmp:
        src = os.path.join(tmp, "result.csv")
        _csv(src, [("A", "OPP RAW SUM(MM_OPP)", "0", "0"), ("A", "CELL KEYS WITH UNEQUAL POSITIVE MM_OPP, THEIR OPP", "0", "1")])
        printed = _run(src, os.path.join(tmp, "out"))
        d = os.path.join(tmp, "out", "a_dist_ch")
        ex = data.load(os.path.join(d, "instance_descaled.json.gz"))
        assert ex.channels == ("blank", "ifa", "wells_wh"), ex.channels
        assert dict(zip(zip(ex.z, ex.channel), ex.m_rel)).keys() >= {("02134", "ifa"), ("60601", "blank")}
        assert abs(statistics.median(ex.m_rel) - 1.0) < 1e-5, ex.m_rel   # the middle two, 6 significant figures
        assert abs(ex.meta["kappa_usd"] * sum(ex.m_rel) - 505.0) < 1e-3          # A's rows once: 150+310+40+5
        assert ex.meta["source"] == "A" and ex.meta["input"] == "result.csv" and ex.meta["column"] == "DIST_CH"
        assert all(s == {} for s in ex.share) and ex.firm == {} and set(ex.share_free) == {0.0}
        chans = {c["channel"]: c for c in json.load(open(os.path.join(d, "channels.json")))["channels"]}
        assert chans["wells_wh"]["spellings"] == ["Wells (WH)", "wells wh"] and chans["blank"]["cells"] == 1
        assert open(os.path.join(d, "incumbent.csv")).read() == "zip,channel,holder\n02134,ifa,R1\n"
        assert "1 `blank` cells" in printed and "not a CONUS ZCTA" in printed, printed
        assert os.path.exists(os.path.join(tmp, "out", "b_new_dist", "instance_descaled.json.gz"))
        b = data.load(os.path.join(tmp, "out", "b_channel", "instance_descaled.json.gz"))
        assert b.m_rel == [1.0], b.m_rel                                              # sources stay apart


def test_must_be_zero_refuses():
    with tempfile.TemporaryDirectory() as tmp:
        src, out = os.path.join(tmp, "result.csv"), os.path.join(tmp, "out")
        _csv(src, [("A", "CELL KEYS WITH UNEQUAL POSITIVE MM_OPP, THEIR OPP", "2", "1")])
        try:
            _run(src, out)
        except SystemExit as e:
            assert "UNEQUAL" in str(e.code), e.code
        else:
            raise AssertionError("a nonzero MUST_BE_ZERO check did not refuse")
        assert not os.path.exists(out)
