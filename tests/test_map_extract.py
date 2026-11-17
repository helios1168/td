"""
test_map_extract.py -- `tools/snowflake/map_extract.py`: 06_map_extract.sql's CSV split into one file per layer.

A tiny made-up CSV (the SQL's columns): each layer lands in its own file with its own columns and rows, a leading-zero ZIP stays
a string, NULL is an empty cell, and a nonzero MUST_BE_ZERO check refuses with nothing written.
"""
from __future__ import annotations

import contextlib
import csv
import io
import os
import sys
import tempfile

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.join(ROOT, "tools", "snowflake"))
import map_extract  # noqa: E402

HEAD = ("layer source est_source holder kept role assigned_states zip_code state terr_channel piece_in_role in_assigned_state dist_ch "
        "new_dist channel new_terr_channel fit_channel mm_opp n_holders holder_status n_role_holders n_role_firms n_zips n_zips_in_role "
        "states opp_main opp_in_role opp_out_of_role opp_overlap opp_in_assigned_states name value must_be_zero").upper().split()


def _row(**kw):
    return [kw.get(c.lower(), "") for c in HEAD]


def _csv(path, value="0"):
    rows = [_row(layer="PIECE", source="A", holder="R5", kept="Y", role="WIFI", zip_code="02134", state="MA", terr_channel="WH",
                 piece_in_role="1", n_role_holders="2", n_role_firms="2"),
            _row(layer="CELL", est_source="A", zip_code="02134", state="MA", dist_ch="WH", new_dist="WH", channel="WH",
                 fit_channel="WH", mm_opp="100", n_holders="1", holder_status="KEPT IN ROLE"),
            _row(layer="ZIP", zip_code="02134", role="WIFI", n_role_holders="2", n_role_firms="2"),
            _row(layer="WHOLESALER", source="A", holder="R5", kept="Y", role="WIFI", est_source="A", n_zips="1", n_zips_in_role="1",
                 states="MA", opp_main="100", opp_in_role="100", opp_out_of_role="0", opp_overlap="50"),
            _row(layer="CHECKS", source="A", name="WHOLESALERS WITH NO KEY ROW (RUN 02_model_extract.sql FIRST)", value=value,
                 must_be_zero="1"),
            _row(layer="CHECKS", source="A", name="ROWS IN THE ZIP LAYER", value="1", must_be_zero="0")]
    with open(path, "w", newline="", encoding="utf-8") as fh:
        csv.writer(fh, lineterminator="\n").writerows([HEAD] + rows)


def _run(path, out):
    with contextlib.redirect_stdout(io.StringIO()):
        map_extract.main([path, "--out", out])


def test_layers_split():
    with tempfile.TemporaryDirectory() as tmp:
        src, out = os.path.join(tmp, "result.csv"), os.path.join(tmp, "out")
        _csv(src)
        _run(src, out)
        assert sorted(os.listdir(out)) == ["cell.csv", "piece.csv", "wholesaler.csv", "zip.csv"], os.listdir(out)
        rd = lambda n: open(os.path.join(out, n + ".csv")).read()
        assert rd("piece") == ("SOURCE,HOLDER,KEPT,ROLE,ZIP_CODE,STATE,TERR_CHANNEL,PIECE_IN_ROLE,IN_ASSIGNED_STATE,N_ROLE_HOLDERS,N_ROLE_FIRMS\n"
                               "A,R5,Y,WIFI,02134,MA,WH,1,,2,2\n"), rd("piece")
        assert rd("zip") == "ZIP_CODE,ROLE,N_ROLE_HOLDERS,N_ROLE_FIRMS\n02134,WIFI,2,2\n"
        assert rd("cell").splitlines()[1] == "A,02134,MA,WH,WH,WH,,WH,100,1,KEPT IN ROLE", rd("cell")
        assert rd("wholesaler").splitlines()[1] == "A,R5,Y,WIFI,,A,1,1,MA,100,100,0,50,", rd("wholesaler")


def test_must_be_zero_refuses():
    with tempfile.TemporaryDirectory() as tmp:
        src, out = os.path.join(tmp, "result.csv"), os.path.join(tmp, "out")
        _csv(src, value="1")
        try:
            _run(src, out)
        except SystemExit as e:
            assert "NO KEY ROW" in str(e.code), e.code
        else:
            raise AssertionError("a nonzero MUST_BE_ZERO check did not refuse")
        assert not os.path.exists(out)
