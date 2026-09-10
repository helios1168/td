"""test_instance_conus.py: tools/instance_conus.py on a toy v2 instance with a non-CONUS state.

Five zips, one of them in AK (outside the 49 CONUS+DC state list) and connected to a CONUS zip
by an edge; the filter must drop the AK row, drop the edge that touched it, and record both in
`meta["conus_filter"]`.  The toy carries the three sub-channels plus wh/fi (the v4 shape) so the
CLI's report step (`fine_split`, `aggregate`) is exercised on exactly the file this tool exists
for.
"""
from __future__ import annotations

import gzip
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
for _p in (HERE, os.path.join(ROOT, "tools"), ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from td import channels                             # noqa: E402
from td import instance as td_instance              # noqa: E402
import instance_conus as cli                        # noqa: E402

ZIPS = ["10000", "10001", "20000", "20001", "99500"]
STATES = ["MA", "MA", "NY", "NY", "AK"]
SUB = channels.SUB_CHANNELS + ("wh", "fi")


def _toy_raw() -> dict:
    z, chan, m_rel, share, share_free, state = [], [], [], [], [], []
    for zp, st in zip(ZIPS, STATES):
        for c in SUB:
            z.append(zp); chan.append(c); m_rel.append(1.0)
            share.append({"rep0": 0.2}); share_free.append(0.1); state.append(st)
    return dict(
        format=td_instance.FORMAT_V2,
        nodes=dict(z=z, channel=chan, m_rel=m_rel, share=share, share_free=share_free,
                  state=state),
        edges=dict(u=["10000", "20000", "20001"], v=["10001", "20001", "99500"]),
        meta=dict(channels=list(SUB)),
    )


def _write(path: str, raw: dict) -> None:
    with gzip.open(path, "wt", encoding="utf-8") as fh:
        json.dump(raw, fh)


def test_filter_conus_drops_the_non_conus_state_and_its_edge():
    raw = _toy_raw()
    out = cli.filter_conus(raw, "toy.json.gz")
    assert set(out["nodes"]["z"]) == {"10000", "10001", "20000", "20001"}
    assert len(out["nodes"]["z"]) == 4 * len(SUB)     # one row per (kept zip, sub-channel)
    edges = list(zip(out["edges"]["u"], out["edges"]["v"]))
    assert ("20001", "99500") not in edges
    assert edges == [("10000", "10001"), ("20000", "20001")]

    rec = out["meta"]["conus_filter"]
    assert rec["dropped_states"] == ["AK"]
    assert rec["dropped_zips"] == ["99500"]
    assert rec["source"] == "toy.json.gz"
    assert "date" in rec


def test_main_writes_a_conus_file_and_reports_the_v4_shape():
    with tempfile.TemporaryDirectory() as tmp:
        src = os.path.join(tmp, "src.json.gz")
        dst = os.path.join(tmp, "dst.json.gz")
        _write(src, _toy_raw())
        assert cli.main([src, dst, "--k", "1"]) == 0

        d = td_instance.load_descaled(dst)
        assert sorted(d.G) == ["10000", "10001", "20000", "20001"]
        assert d.G.number_of_edges() == 2
        f = channels.fine_split(d)
        assert f.meta["fine_split"] == "sub-channels"
        assert f.meta["fine_split_fallback"] == {}
        with gzip.open(dst, "rt", encoding="utf-8") as fh:
            written = json.load(fh)
        assert written["meta"]["conus_filter"]["dropped_states"] == ["AK"]
