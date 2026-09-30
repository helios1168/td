"""td.data: the v3 loader, the CONUS rule and the seeded sparse fixture (#66).

Every extract here is synthetic: the fixture's masses are drawn from a seeded RNG and the
exporter test writes made-up book, so no real row enters a test.  The fixture's ZIP graph needs
TIGER/Line 2025 state polygons (`tl_2025_us_state.zip` in `data/public/`, or `$TD_REPO`'s); with
neither, the graph tests print SKIP and return, and the rest still run.
"""
from __future__ import annotations

import functools
import gzip
import importlib.util
import json
import os
import sys
import tempfile

import numpy as np

from td import data, geo

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

ZIP_RANGE = (3900, 4100)
# a lognormal fixture at the v2 mean/median of 2.28 sits mid-band; the fixture ZIPs' own
# populations (Gini 0.55, top 10% 0.41) fall below it, so the bands say "heavier than people"
GINI_BAND = (0.58, 0.70)
TOP10_BAND = (0.44, 0.58)
TOP1_BAND = (0.10, 0.22)


@functools.cache
def _reference():
    return geo.read_reference()


@functools.cache
def _state_file():
    for public in (geo.PUBLIC_DIR, os.path.join(os.environ.get("TD_REPO", ""), "data", "public")):
        path = os.path.join(public, "tl_2025_us_state.zip")
        if os.path.exists(path) and geo._valid_download(path):
            return public
    print("SKIP  test_data.py: no tl_2025_us_state.zip in data/public or $TD_REPO/data/public; "
          "the fixture graph tests did not run", file=sys.stderr)
    return None


@functools.cache
def _states():
    public = _state_file()
    return None if public is None else data.state_polygons(public)


@functools.cache
def _fixture(seed=0):
    return data.fixture(seed, reference=_reference(), state_polys=_states())


def _bytes(extract):
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "x.json.gz")
        data.write(extract, path)
        with open(path, "rb") as fh:
            return fh.read()


def _concentration(masses):
    m = np.sort(np.asarray(list(masses), dtype=float))
    n, total = len(m), m.sum()
    gini = float((2 * np.arange(1, n + 1) - n - 1) @ m / (n * total))
    return {"gini": gini, "top10": float(m[-(n // 10):].sum() / total),
            "top1": float(m[-max(1, n // 100):].sum() / total)}


def _in_bands(c):
    return (GINI_BAND[0] <= c["gini"] <= GINI_BAND[1]
            and TOP10_BAND[0] <= c["top10"] <= TOP10_BAND[1]
            and TOP1_BAND[0] <= c["top1"] <= TOP1_BAND[1])


# ------------------------------------------------------------------------------ the fixture
def test_sample_is_deterministic_for_a_seed_and_differs_across_seeds():
    a = data.sample(0, reference=_reference())
    assert _bytes(a) == _bytes(data.sample(0, reference=_reference()))
    b = data.sample(1, reference=_reference())
    assert a.z != b.z and a.m_rel != b.m_rel


def test_sample_is_population_weighted_conus_and_median_one():
    ref = _reference().set_index("zcta")
    ext = data.sample(0, reference=_reference())
    assert len(ext.zips) == data.FIXTURE_ZIPS == len(ext.z)
    assert set(ext.zips) <= set(ref.index) and (ref.loc[ext.zips, "state"] != "").all()
    pop = ref["pop2025"].astype(float)
    assert pop.loc[ext.zips].mean() > 2 * pop.mean()
    assert 0.99 <= float(np.median(ext.m_rel)) <= 1.01


def test_sample_mass_concentration_is_in_the_stated_bands():
    for seed in (0, 1, 2):
        c = _concentration(data.sample(seed, reference=_reference()).masses().values())
        assert _in_bands(c), (seed, c)


def test_population_and_uniform_masses_fall_outside_the_bands():
    ext = data.sample(0, reference=_reference())
    pop = _reference().set_index("zcta").loc[ext.zips, "pop2025"].astype(float)
    assert not _in_bands(_concentration(pop))
    assert not _in_bands(_concentration(np.ones(len(ext.zips))))


def test_sample_carries_every_channel_on_every_zip():
    ext = data.sample(0, n_zips=50, channels=("national", "wifi"), reference=_reference())
    assert ext.channels == ("national", "wifi") and len(ext.z) == 100
    assert set(ext.masses("wifi")) == set(ext.masses("national")) == set(ext.zips)


def test_fixture_zip_count_is_in_range_after_the_vertex_rule():
    if _states() is None:
        return
    fx = _fixture()
    assert ZIP_RANGE[0] <= len(fx.extract.zips) <= ZIP_RANGE[1], len(fx.extract.zips)
    assert fx.extract.zips == fx.graph["vertices"] == sorted(fx.zip_state)
    assert not set(fx.graph["missing"]) & set(fx.extract.zips)
    assert fx.graph["edges"] and all(a in fx.zip_state and b in fx.zip_state
                                     for a, b, *_ in fx.graph["edges"])


def test_fixture_is_byte_identical_for_a_seed():
    if _states() is None:
        return
    a = _fixture()
    b = data.fixture(0, reference=_reference(), state_polys=_states())
    assert _bytes(a.extract) == _bytes(b.extract)
    assert a.graph == b.graph


def test_fixture_drops_a_zip_whose_cell_vanishes():
    import pandas as pd
    import shapely
    ref = pd.DataFrame({"zcta": ["00001", "00002", "00003", "00004"],
                        "state": ["A", "A", "A", "B"],
                        "x": ["2", "8", "40", "15"], "y": ["5", "5", "5", "5"],
                        "pop2025": ["10", "10", "10", "10"]})
    polys = {"A": shapely.box(0, 0, 10, 10), "B": shapely.box(10, 0, 20, 10)}
    fx = data.fixture(0, n_zips=4, reference=ref, state_polys=polys)
    assert fx.graph["missing"] == {"00003": "cell clipped away"}
    assert fx.extract.zips == fx.graph["vertices"] == ["00001", "00002", "00004"]
    assert {(a, b) for a, b, *_ in fx.graph["edges"]} == {("00001", "00002"),
                                                          ("00002", "00004")}


# ------------------------------------------------------------------------------ the loader
def test_loader_round_trips_a_fixture_file():
    ext = data.sample(0, n_zips=200, channels=("national", "wh"), reference=_reference())
    ext.share[0] = {"R0000": 0.25, "R0001": 0.5}
    ext.share_free[1] = 0.125
    ext.firm = {"R0000": "F0", "R0001": "F1"}
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "instance_descaled.json.gz")
        data.write(ext, path)
        back = data.load(path)
    assert back == ext


def _exporter():
    spec = importlib.util.spec_from_file_location(
        "export_instance", os.path.join(ROOT, "export", "export_instance.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_loader_reads_what_the_exporter_writes():
    ex = _exporter()
    inst = ex.Instance()
    inst.channels = ("national", "wells_wh")
    inst.m_rel = {("10001", "national"): 1.0, ("10001", "wells_wh"): 3.5,
                  ("10002", "national"): 0.4, ("10003", "wells_wh"): 1.0 / 3}
    inst.share[("10001", "national")] = {"R0000": 0.6, "R0001": 0.1}
    inst.share[("10003", "wells_wh")] = {"R0001": 1.0 / 7}
    inst.free = {("10002", "national"): 0.2}
    inst.firm = {"R0000": "F0", "R0001": "F1"}
    inst.report = {"channels": list(inst.channels), "n_zips": 3}
    with tempfile.TemporaryDirectory() as tmp:
        path = ex.write(inst, tmp, theta=0.4, lam=0.3, verbose=False)
        ext = data.load(path)
    assert ext.channels == ("national", "wells_wh")
    assert list(zip(ext.z, ext.channel)) == [("10001", "national"), ("10001", "wells_wh"),
                                             ("10002", "national"), ("10003", "wells_wh")]
    assert ext.m_rel == [1.0, 3.5, 0.4, data.rsig(1.0 / 3)]
    assert ext.share == [{"R0000": 0.6, "R0001": 0.1}, {}, {}, {"R0001": data.rsig(1.0 / 7)}]
    assert ext.share_free == [0.0, 0.0, 0.2, 0.0]
    assert ext.firm == inst.firm and ext.meta["theta"] == 0.4
    assert ext.masses("wells_wh") == {"10001": 3.5, "10003": data.rsig(1.0 / 3)}


def _payload(**nodes):
    base = {"z": ["10001", "10002"], "channel": ["national", "national"], "m_rel": [1.0, 2.0],
            "share": [{}, {}], "share_free": [0.0, 0.0]}
    return {"format": data.FORMAT, "nodes": {**base, **nodes}, "firm": {},
            "meta": {"channels": ["national"]}}


def _raises(payload):
    try:
        data.from_payload(payload)
    except ValueError as e:
        return str(e)
    raise AssertionError("accepted")


def test_loader_rejects_another_format_tag():
    for tag in ("td_instance_descaled/2", None):
        p = _payload()
        p["format"] = tag
        assert "format" in _raises(p)
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "v2.json.gz")
        p = _payload()
        p["format"] = "td_instance_descaled/2"
        with gzip.open(path, "wt") as fh:
            json.dump(p, fh)
        try:
            data.load(path)
        except ValueError:
            pass
        else:
            raise AssertionError("loaded a v2 file")


def test_loader_rejects_malformed_nodes_with_counts_not_values():
    msg = _raises(_payload(z=["10001", "10001"], m_rel=[1.0, -7.25]))
    assert "1 duplicate cells" in msg and "1 m_rel" in msg
    assert "10001" not in msg and "7.25" not in msg
    assert "1 ZIP ids" in _raises(_payload(z=["10001", "1002"]))
    assert "1 channels" in _raises(_payload(channel=["national", "wifi"]))
    assert "1 shares" in _raises(_payload(share=[{"R0000": 1.5}, {}]))
    assert "length" in _raises(_payload(m_rel=[1.0]))
    p = _payload()
    del p["nodes"]["share_free"]
    assert "share_free" in _raises(p)


# ------------------------------------------------------------------------------ the CONUS rule
def test_conus_rule_drops_and_counts_by_reason():
    import pandas as pd
    kept = data.sample(0, n_zips=3, reference=_reference()).zips
    ref = pd.concat([_reference(), pd.DataFrame({"zcta": ["00009"], "state": [""]})],
                    ignore_index=True).fillna("")
    z = kept + ["99501", "96813", "99501", "00009"]      # AK twice (two channels), HI, blank
    ch = ["national"] * 5 + ["wh", "national"]
    ext = data.Extract(("national", "wh"), z, ch, [1.0, 1.0, 1.0, 2.0, 3.0, 1.0, 2.0],
                       [{}] * 7, [0.0] * 7)
    out = data.conus(ext, ref)
    assert out.zips == sorted(kept) and out.z == kept and out.m_rel == [1.0] * 3
    assert out.dropped == {
        "no state": {"zips": 1, "cells": 1, "m_rel_share": data.rsig(2 / 11)},
        "not a CONUS ZCTA": {"zips": 2, "cells": 3, "m_rel_share": data.rsig(6 / 11)},
    }
    assert data.conus(out).dropped == {}
