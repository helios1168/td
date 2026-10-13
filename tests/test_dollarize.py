"""tools/exp/contig/dollarize.py and export_long.py's reversal (main-map overnight grid, G5/B1) on
a hand-made extract: the $M scale is E1 as coded, the file round-trips through `td.data`, the
scorer's rates on it are 1e6 per $M, and the export gives back the `m_rel` the scale started
from.  Every value is made up; no real row enters a test."""
from __future__ import annotations

import importlib.util
import math
import os
import sys
import tempfile

from td import data

HERE = os.path.dirname(os.path.abspath(__file__))
CONTIG = os.path.join(HERE, "..", "tools", "exp", "contig")


def _load(name: str, path: str):
    if name not in sys.modules:
        spec = importlib.util.spec_from_file_location(name, path)
        mod = importlib.util.module_from_spec(spec)
        sys.modules[name] = mod
        spec.loader.exec_module(mod)
    return sys.modules[name]


dollarize = _load("contig_dollarize", os.path.join(CONTIG, "dollarize.py"))
export_long = _load("contig_export_long", os.path.join(CONTIG, "export_long.py"))
score = dollarize._score()

CELLS = [("10001", "national_chase", 2.0), ("10001", "wh", 1.0), ("10001", "fi", 0.5),
         ("10002", "national_chase", 3.0), ("10002", "fi", 1.5), ("10002", "edj", 4.0),
         ("10003", "wh", 0.25)]


def _toy() -> data.Extract:
    chans = ("national_chase", "wh", "fi", "edj")
    return data.Extract(chans, [z for z, _, _ in CELLS], [c for _, c, _ in CELLS],
                        [m for _, _, m in CELLS], [{"R0000": 0.5} if i == 0 else {} for i in range(len(CELLS))],
                        [0.25 if i == 1 else 0.0 for i in range(len(CELLS))], {"R0000": "F0"},
                        {"channels": list(chans)})


def test_scale_is_e1_in_millions_and_drops_channels_without_a_total():
    ext = _toy()
    usd = dollarize.scale(ext, "instance_descaled.json.gz", "ab" * 32)
    total = {"national_chase": 5.0, "wh": 1.25, "fi": 2.0}
    want = {f: score.DOLLARS[f] / total[f] / 1e6 for f in total}
    info = usd.meta["dollar_scale"]
    assert info["unit"] == "$M" and info["dropped_channels"] == ["edj"]
    assert info["source"] == "instance_descaled.json.gz" and info["source_sha256"] == "ab" * 32
    assert set(info["rates"]) == set(want)
    assert all(math.isclose(info["rates"][f], want[f], rel_tol=1e-12) for f in want)
    assert usd.channels == ("national_chase", "wh", "fi") and usd.meta["channels"] == list(usd.channels)
    assert "edj" not in usd.channel and len(usd.z) == len(CELLS) - 1
    for z, c, m, x in zip(usd.z, usd.channel, usd.m_rel, (r for r in CELLS if r[1] != "edj")):
        assert (z, c) == x[:2] and math.isclose(m, x[2] * want[c], rel_tol=1e-12)
    assert usd.share[0] == {"R0000": 0.5} and usd.share_free[1] == 0.25 and usd.firm == {"R0000": "F0"}


def test_scale_refuses_an_extract_already_in_dollars():
    usd = dollarize.scale(_toy())
    try:
        dollarize.scale(usd)
    except ValueError as e:
        assert "already in dollars" in str(e)
    else:
        raise AssertionError("a dollar extract was scaled twice")


def test_file_round_trip_and_reversal():
    ext = _toy()
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "instance_descaled_usd.json.gz")
        usd = dollarize.scale(ext)
        data.write(usd, path)
        back = data.load(path)
        rates = dollarize.rates_of(path)
    assert back == usd
    assert rates == usd.meta["dollar_scale"]["rates"]
    kept = [r for r in CELLS if r[1] != "edj"]
    for (z, c, m), x in zip(kept, back.m_rel):
        assert math.isclose(dollarize.to_m_rel(x, c, rates), m, rel_tol=1e-12)
    assert dollarize.to_m_rel(1.5, "wh", None) == 1.5


def test_scorer_rates_on_a_dollar_extract_are_a_million_per_unit():
    usd = dollarize.scale(_toy())
    got = score.dollar_rates(usd)
    assert set(got) == {"national_chase", "wh", "fi"}
    assert all(math.isclose(r, 1e6, rel_tol=1e-12) for r in got.values())


def test_export_rows_reverse_dollars_and_keep_m_rel_runs():
    usd = dollarize.scale(_toy())
    rates = usd.meta["dollar_scale"]["rates"]
    rows = [{"zip_code": z, "current_channel": c, "state": "NY", "model_channel": "national" if c == "national_chase" else c.upper(),
             "district": "d1", "district_channels": "", "m_rel": repr(m)} for z, c, m in zip(usd.z, usd.channel, usd.m_rel)]
    rows.append({"zip_code": "10004", "current_channel": "wh", "state": "NY", "model_channel": "WH",
                 "district": "d1", "district_channels": "", "m_rel": ""})
    got = list(export_long.rows_long(rows, "s", rates))
    kept = [m for _, c, m in CELLS if c != "edj"] + [0.0]
    assert [r["m_rel"] for r in got] == [f"{m:.6f}" for m in kept]
    assert [r["has_commercial_opportunity"] for r in got] == [m > 0 for m in kept]
    assert got[0]["canonical_channel"] == "national_chase" and got[0]["bundle"] == "N"
    assert got[1]["canonical_channel"] == "wh" and got[1]["bundle"] == "WH"
    assert all(r["rep"] == "" for r in got)
    plain = list(export_long.rows_long(rows[:1], "s", None))
    assert plain[0]["m_rel"] == f"{usd.m_rel[0]:.6f}"


def test_main_refuses_a_name_gitignore_misses():
    with tempfile.TemporaryDirectory() as tmp:
        src = os.path.join(tmp, "instance_descaled.json.gz")
        data.write(_toy(), src)
        for name in ("usd.json.gz", "instance_usd.json.gz"):
            try:
                dollarize.main([src, os.path.join(tmp, name)])
            except SystemExit as e:
                assert "must match" in str(e.code)
            else:
                raise AssertionError(f"{name} was written")
        assert dollarize.main([src, os.path.join(tmp, "instance_descaled_usd.json.gz")]) == 0
        assert dollarize.rates_of(os.path.join(tmp, "instance_descaled_usd.json.gz")) is not None
