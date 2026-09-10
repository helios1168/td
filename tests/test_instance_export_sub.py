"""
test_instance_export_sub.py -- national's three sub-channels (2026-09-10).

The business calls "national" three sub-channels: National (Chase), Wells (WH) and
Wells (FI). An extract may carry those three instead of one `national` column, on both
tables, never both at once. `canonical_channel` normalises whatever spelling a column
carries to one of five names plus legacy `national`; when the three are present, kappa
(and everything pinned to the national channel) is taken over their per-zip sum instead
of a single `national` cell.
"""
from __future__ import annotations

import contextlib
import csv
import gzip
import importlib.util
import io
import json
import os
import tempfile

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))


def _exporter():
    path = os.path.join(ROOT, "tools", "instance_export", "export_instance.py")
    spec = importlib.util.spec_from_file_location("export_instance", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _csv(tmp, name, header, rows):
    path = os.path.join(tmp, name)
    with open(path, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(header)
        w.writerows(rows)
    return path


def _export(mod, tmp, sales, opp, edges, out="out", extra=()):
    out_dir = os.path.join(tmp, out)
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        rc = mod.main(["export", "--sales", sales, "--opportunity", opp, "--graph", edges,
                       "--out", out_dir, "--yes", *extra])
    path = os.path.join(out_dir, "instance_descaled.json.gz")
    payload = None
    if os.path.exists(path):
        with gzip.open(path, "rt", encoding="utf-8") as fh:
            payload = json.load(fh)
    return rc, payload, buf.getvalue(), path


def _cells(payload):
    n = payload["nodes"]
    chan = n.get("channel") or [""] * len(n["z"])
    return {(z, c): dict(m_rel=m, share=s)
            for z, c, m, s in zip(n["z"], chan, n["m_rel"], n["share"])}


# ------------------------------------------------------------------- the toy extract
# 3 zips, national's three sub-channels spelled in mixed case, chosen so every m_rel and
# share lands on a clean decimal -- 6-sig-fig rounding must not perturb the comparison.
SUB_SALES = [
    ("40001", "r_a", "FA", "National (Chase)", 4.0),
    ("40001", "r_b", "FB", "Wells (WH)", 2.0),
    ("40002", "r_a", "FA", "chase", 8.0),
    ("40002", "r_c", "FC", "WELLS_FI", 6.0),
    ("40003", "r_b", "FB", "national_chase", 12.0),
    ("40003", "r_d", "FD", "wells_wh", 18.0),
    ("40003", "r_e", "FE", "Wells (FI)", 9.0),
]
SUB_OPP = [
    ("40001", "National (Chase)", 20.0), ("40001", "Wells (WH)", 20.0),
    ("40001", "Wells (FI)", 10.0),
    ("40002", "chase", 40.0), ("40002", "wells_wh", 40.0), ("40002", "wells_fi", 20.0),
    ("40003", "national_chase", 60.0), ("40003", "national_wells_wh", 60.0),
    ("40003", "national_wells_fi", 30.0),
]
SUB_EDGES = [("40001", "40002"), ("40002", "40003")]
KAPPA = 100.0   # median of the per-zip sums 50, 100, 150


def _sub_inputs(tmp, sales=None, opp=None):
    return (_csv(tmp, "sales.csv", ["zip_code", "rep_id", "firm", "current_channel", "sales"],
                 sales if sales is not None else SUB_SALES),
            _csv(tmp, "opp.csv", ["zip_code", "current_channel", "M"],
                 opp if opp is not None else SUB_OPP),
            _csv(tmp, "edges.csv", ["u", "v"], SUB_EDGES))


def test_subchannels_export_canonical_names_and_channel_groups_and_kappa():
    mod = _exporter()
    with tempfile.TemporaryDirectory() as tmp:
        sp, op, gp = _sub_inputs(tmp)
        rc, payload, txt, _ = _export(mod, tmp, sp, op, gp)
    assert rc == 0, txt
    assert payload["format"] == "td_instance_descaled/2"
    assert payload["meta"]["channels"] == \
        ["national_chase", "national_wells_wh", "national_wells_fi"]
    assert payload["meta"]["kappa_channel"] == "national"
    assert payload["meta"]["channel_groups"] == \
        {"national": ["national_chase", "national_wells_wh", "national_wells_fi"]}

    cells = _cells(payload)
    m_of = {("40001", "national_chase"): 20.0, ("40001", "national_wells_wh"): 20.0,
            ("40001", "national_wells_fi"): 10.0,
            ("40002", "national_chase"): 40.0, ("40002", "national_wells_wh"): 40.0,
            ("40002", "national_wells_fi"): 20.0,
            ("40003", "national_chase"): 60.0, ("40003", "national_wells_wh"): 60.0,
            ("40003", "national_wells_fi"): 30.0}
    assert set(cells) == set(m_of)
    for cell, M in m_of.items():
        assert abs(cells[cell]["m_rel"] - M / KAPPA) < 1e-9, cell

    # book is a fraction of that sub-channel's own M, not of the zip or of national's sum.
    # rep ids: mask_reps ranks by total book weighted by m_rel -- r_d (0.18) > r_b (0.14) >
    # r_a (0.12) > r_e (0.09) > r_c (0.06) -> R0000..R0004 in that order.
    assert cells[("40001", "national_chase")]["share"] == {"R0002": 4.0 / 20.0}, "r_a"
    assert cells[("40001", "national_wells_wh")]["share"] == {"R0001": 2.0 / 20.0}, "r_b"
    assert cells[("40001", "national_wells_fi")]["share"] == {}, "no fi sale at 40001"
    assert cells[("40002", "national_wells_wh")]["share"] == {}, "no wh sale at 40002"
    assert cells[("40003", "national_wells_fi")]["share"]["R0003"] == 9.0 / 30.0, "r_e"


def test_national_and_a_subchannel_together_is_refused():
    mod = _exporter()
    with tempfile.TemporaryDirectory() as tmp:
        sp = _csv(tmp, "sales.csv", ["zip_code", "rep_id", "firm", "current_channel", "sales"],
                  [("50001", "r_a", "FA", "national", 10.0)])
        op = _csv(tmp, "opp.csv", ["zip_code", "current_channel", "M"],
                  [("50001", "national", 100.0), ("50001", "chase", 50.0)])
        gp = _csv(tmp, "edges.csv", ["u", "v"], [("50001", "50002")])
        rc, payload, txt, _ = _export(mod, tmp, sp, op, gp)
    assert rc == 4 and payload is None
    assert "ambiguous" in txt
    assert "national_chase" in txt


def test_unknown_channel_value_is_refused_with_accepted_spellings():
    mod = _exporter()
    with tempfile.TemporaryDirectory() as tmp:
        sp = _csv(tmp, "sales.csv", ["zip_code", "rep_id", "firm", "current_channel", "sales"],
                  [("60001", "r_a", "FA", "national", 5.0)])
        op = _csv(tmp, "opp.csv", ["zip_code", "current_channel", "M"],
                  [("60001", "mystery", 100.0)])
        gp = _csv(tmp, "edges.csv", ["u", "v"], [("60001", "60002")])
        rc, payload, txt, _ = _export(mod, tmp, sp, op, gp)
    assert rc == 4 and payload is None
    assert "unknown channel" in txt and "accepted spellings" in txt
    assert "national_chase" in txt and "wells_wh" in txt


def test_canonical_channel_spellings():
    mod = _exporter()
    c = mod.canonical_channel
    assert c("National (Chase)") == "national_chase"
    assert c("NATIONAL_CHASE") == "national_chase"
    assert c("chase") == "national_chase"
    assert c("Wells (WH)") == "national_wells_wh"
    assert c("wells wh") == "national_wells_wh"
    assert c("WELLS-FI") == "national_wells_fi"
    assert c("wells.fi") == "national_wells_fi"
    assert c(" wh ") == "wh"
    assert c("FI") == "fi"
    assert c("National") == "national"

    try:
        c("mystery", label="opportunity")
        raise AssertionError("expected InputError")
    except mod.InputError as e:
        assert "mystery" in str(e) and "opportunity" in str(e) \
            and "accepted spellings" in str(e)
