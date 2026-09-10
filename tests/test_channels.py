"""
test_channels.py -- cells, bundles and projections (td/channels.py).

The load-bearing properties are conservation and exactness: `synthesize_channels` multiplies
`M`, every `S_i` and `S_free` at a zip by one number per channel, so per-cell headroom holds
wherever it held on the input; `fine_split` moves national mass between two labels and changes
no total; `project` sums a bundle's cells into an instance the existing drivers can read.
"""
from __future__ import annotations

import gzip
import json
import os
import tempfile

import networkx as nx
import numpy as np

from td import channels, instance, model        # noqa: E402

THETA = 0.40
ZIPS = ["10000", "10001", "10002", "10003", "10004", "10005"]
STATES = ["MA", "MA", "MA", "NY", "NY", "NY"]
BOOKS = [{"R0": 4.0, "R1": 3.0}, {"R1": 5.0}, {}, {}, {"R2": 6.0, "R0": 2.0}, {"R2": 1.0}]
MASS = [100.0, 80.0, 60.0, 0.0, 120.0, 50.0]
FREE = [0.0, 0.0, 2.0, 0.0, 0.0, 1.0]


def v1_fixture() -> instance.Descaled:
    """Six zips on a path, two states, three reps, one of each node class."""
    G = nx.Graph()
    for z, st, S, M, fr in zip(ZIPS, STATES, BOOKS, MASS, FREE):
        G.add_node(z, cand=tuple(sorted(S)), S=dict(S), M=M, S_free=fr, state=st)
    G.add_edges_from((ZIPS[i], ZIPS[i + 1]) for i in range(len(ZIPS) - 1))
    contested = [z for z in ZIPS if len(G.nodes[z]["cand"]) >= 2]
    uncontested = {z: G.nodes[z]["cand"][0] for z in ZIPS if len(G.nodes[z]["cand"]) == 1}
    vacant = [z for z in ZIPS if not G.nodes[z]["cand"] and G.nodes[z]["S_free"] > 0]
    untapped = [z for z in ZIPS if not G.nodes[z]["cand"] and G.nodes[z]["S_free"] == 0]
    return instance.Descaled(G=G, contested=contested, uncontested=uncontested,
                             vacant=vacant, untapped=untapped,
                             firm={"R0": "F_A", "R1": "F_A", "R2": "F_B"},
                             meta={"exporter": "test"})


def cells_fixture() -> instance.Descaled:
    """A hand-built file-channel instance covering both fine-split fallbacks.

    zA has WH and FI mass (its own ratio), zB has none but its state does (state ratio),
    zC is in a state with no WH or FI mass at all (50/50).
    """
    rows = [
        ("zA", "MA", {"national": 100.0, "wh": 30.0, "fi": 10.0},
         {"R0": {"national": 8.0, "wh": 3.0, "fi": 1.0}}, {"national": 2.0, "wh": 0.0,
                                                           "fi": 0.0}),
        ("zB", "MA", {"national": 40.0, "wh": 0.0, "fi": 0.0},
         {"R1": {"national": 4.0, "wh": 0.0, "fi": 0.0}}, {"national": 0.0, "wh": 0.0,
                                                           "fi": 0.0}),
        ("zC", "NY", {"national": 20.0, "wh": 0.0, "fi": 0.0},
         {"R2": {"national": 2.0, "wh": 0.0, "fi": 0.0}}, {"national": 1.0, "wh": 0.0,
                                                           "fi": 0.0}),
    ]
    G = nx.Graph()
    for z, st, M_c, S_c, F_c in rows:
        S = {i: sum(per.values()) for i, per in S_c.items()}
        G.add_node(z, state=st, M_c=M_c, S_c=S_c, S_free_c=F_c,
                   M=sum(M_c.values()), S=S, S_free=sum(F_c.values()),
                   cand=tuple(sorted(S)))
    G.add_edges_from([("zA", "zB"), ("zB", "zC")])
    return instance.Descaled(G=G, contested=[],
                             uncontested={"zA": "R0", "zB": "R1", "zC": "R2"},
                             vacant=[], untapped=[], firm={}, meta={},
                             channels=channels.FILE_CHANNELS)


# ------------------------------------------------------------------- synthesize_channels
def test_synthesize_keeps_the_national_cell():
    d = v1_fixture()
    s = channels.synthesize_channels(d, seed=0)
    assert channels.channels_of(s) == channels.FILE_CHANNELS
    for z in ZIPS:
        a, b = d.G.nodes[z], s.G.nodes[z]
        assert b["M_c"]["national"] == a["M"]
        assert b["S_free_c"]["national"] == a["S_free"]
        assert {i: per["national"] for i, per in b["S_c"].items()} == a["S"]
    assert s.G.number_of_edges() == d.G.number_of_edges()


def test_synthesize_totals_are_the_cell_sums_and_multipliers_are_exact():
    d = v1_fixture()
    s = channels.synthesize_channels(d, seed=0)
    for z in ZIPS:
        a, b = d.G.nodes[z], s.G.nodes[z]
        assert b["M"] == sum(b["M_c"].values())
        assert b["S_free"] == sum(b["S_free_c"].values())
        for i, per in b["S_c"].items():
            assert b["S"][i] == sum(per.values())
        # the same multiplier on M, every S_i and S_free, exactly (float equality)
        al, be = channels._alpha_beta(0, z)
        assert 0.15 <= al <= 0.55 and 0.15 <= be <= 0.55
        for c, mult in (("wh", al), ("fi", be)):
            assert b["M_c"][c] == mult * a["M"]
            assert b["S_free_c"][c] == mult * a["S_free"]
            for i, v in a["S"].items():
                assert b["S_c"][i][c] == mult * v


def test_synthesize_per_cell_headroom_holds():
    """Headroom on each channel's own graph, and on the totals."""
    s = channels.synthesize_channels(v1_fixture(), seed=0)
    assert model.headroom_violations(s.G, theta=THETA) == []
    for c in channels.FILE_CHANNELS:
        H = nx.Graph()
        for z in s.G:
            a = s.G.nodes[z]
            H.add_node(z, M=a["M_c"][c], S_free=a["S_free_c"][c],
                       S={i: per[c] for i, per in a["S_c"].items()},
                       cand=a["cand"])
        assert model.headroom_violations(H, theta=THETA) == [], c


def test_synthesize_is_deterministic_and_seed_dependent():
    d = v1_fixture()
    a = channels.synthesize_channels(d, seed=0)
    b = channels.synthesize_channels(d, seed=0)
    c = channels.synthesize_channels(d, seed=1)
    for z in ZIPS:
        assert a.G.nodes[z]["M_c"] == b.G.nodes[z]["M_c"]
    assert any(a.G.nodes[z]["M_c"]["wh"] != c.G.nodes[z]["M_c"]["wh"] for z in ZIPS)
    assert a.meta["synthetic"] == {"seed": 0, "alpha": [0.15, 0.55], "beta": [0.15, 0.55]}


# --------------------------------------------------------------------------- fine_split
def test_fine_split_uses_the_zips_own_ratio():
    f = channels.fine_split(cells_fixture())
    assert channels.channels_of(f) == channels.CHANNELS
    a = f.G.nodes["zA"]
    assert a["M_c"] == {"N_WH": 75.0, "N_FI": 25.0, "WH": 30.0, "FI": 10.0}
    assert a["S_c"]["R0"] == {"N_WH": 6.0, "N_FI": 2.0, "WH": 3.0, "FI": 1.0}
    assert a["S_free_c"] == {"N_WH": 1.5, "N_FI": 0.5, "WH": 0.0, "FI": 0.0}


def test_fine_split_state_and_even_fallbacks():
    f = channels.fine_split(cells_fixture())
    assert f.meta["fine_split_fallback"] == {"zB": "state", "zC": "even"}
    # MA's ratio is 30:10 from zA, so zB's national mass splits 75/25
    b = f.G.nodes["zB"]
    assert (b["M_c"]["N_WH"], b["M_c"]["N_FI"]) == (30.0, 10.0)
    assert b["S_c"]["R1"] == {"N_WH": 3.0, "N_FI": 1.0, "WH": 0.0, "FI": 0.0}
    c = f.G.nodes["zC"]                      # NY has no WH or FI mass anywhere: 50/50
    assert (c["M_c"]["N_WH"], c["M_c"]["N_FI"]) == (10.0, 10.0)
    assert c["S_free_c"]["N_WH"] == c["S_free_c"]["N_FI"] == 0.5


def test_fine_split_conserves_totals():
    d = cells_fixture()
    f = channels.fine_split(d)
    for z in d.G:
        a, b = d.G.nodes[z], f.G.nodes[z]
        assert b["M"] == a["M"] and b["S"] == a["S"] and b["S_free"] == a["S_free"]
        assert b["cand"] == a["cand"]
        assert abs(sum(b["M_c"].values()) - a["M"]) < 1e-12
        for i, per in b["S_c"].items():
            assert abs(sum(per.values()) - a["S"][i]) < 1e-12
        assert abs(sum(b["S_free_c"].values()) - a["S_free"]) < 1e-12


def test_fine_split_refuses_an_instance_with_no_national_channel():
    """A channel-less instance has no `M_c`, so every cell would split to zero and the result
    would read as a four-channel instance carrying no mass.  It must raise instead."""
    try:
        channels.fine_split(v1_fixture())            # channels == ()
    except ValueError as e:
        assert "national" in str(e)
    else:
        raise AssertionError("fine_split accepted a channel-less instance")

    # and a file that carries wh/fi but no national row: there is nothing to split
    d = cells_fixture()
    for z in d.G:
        for key in ("M_c", "S_free_c"):
            d.G.nodes[z][key].pop("national", None)
        for per in d.G.nodes[z]["S_c"].values():
            per.pop("national", None)
    d.channels = ("wh", "fi")
    try:
        channels.fine_split(d)
    except ValueError as e:
        assert "national" in str(e)
    else:
        raise AssertionError("fine_split accepted an instance with no national channel")


def test_fine_split_on_a_synthetic_instance_needs_no_fallback():
    """wh and fi are positive multiples of national, so every zip has its own ratio."""
    f = channels.fine_split(channels.synthesize_channels(v1_fixture(), seed=0))
    assert f.meta["fine_split_fallback"] == {}


# ---------------------------------------------------------------------------- aggregate
def test_aggregate_sums_by_state_and_channel():
    f = channels.fine_split(channels.synthesize_channels(v1_fixture(), seed=0))
    cells = channels.aggregate(f, ["MA", "NY"])
    assert cells.channels == channels.CHANNELS
    assert cells.reps == ("R0", "R1", "R2")
    assert cells.M.shape == (2, 4) and cells.S.shape == (3, 2, 4)
    for k, st in enumerate(("MA", "NY")):
        zs = [z for z, s in zip(ZIPS, STATES) if s == st]
        for j, c in enumerate(channels.CHANNELS):
            assert abs(cells.M[k, j] - sum(f.G.nodes[z]["M_c"][c] for z in zs)) < 1e-9
            assert abs(cells.S_free[k, j]
                       - sum(f.G.nodes[z]["S_free_c"][c] for z in zs)) < 1e-9
            for r, rep in enumerate(cells.reps):
                want = sum(f.G.nodes[z]["S_c"].get(rep, {}).get(c, 0.0) for z in zs)
                assert abs(cells.S[r, k, j] - want) < 1e-9
    assert abs(cells.M.sum() - sum(f.G.nodes[z]["M"] for z in f.G)) < 1e-9


def test_aggregate_refuses_file_channels_and_unknown_states():
    s = channels.synthesize_channels(v1_fixture(), seed=0)
    try:
        channels.aggregate(s, ["MA", "NY"])
    except ValueError as e:
        assert "fine_split" in str(e)
    else:
        raise AssertionError("aggregate accepted the file channels")
    f = channels.fine_split(s)
    try:
        channels.aggregate(f, ["MA"])        # NY carries mass and is not in the list
    except ValueError as e:
        assert "state_list" in str(e)
    else:
        raise AssertionError("aggregate accepted a state outside state_list")


def test_slot_weights_sums_the_bundle_masses():
    f = channels.fine_split(channels.synthesize_channels(v1_fixture(), seed=0))
    cells = channels.aggregate(f, ["MA", "NY"])
    W = channels.slot_weights(cells, ["N", "WH_PLUS"])
    assert W.shape == (2, 2)
    c = {name: k for k, name in enumerate(cells.channels)}
    assert np.allclose(W[:, 0], cells.M[:, c["N_WH"]] + cells.M[:, c["N_FI"]])
    assert np.allclose(W[:, 1], cells.M[:, c["WH"]] + cells.M[:, c["N_WH"]])
    # a channel tuple is accepted in place of a bundle name
    assert np.allclose(channels.slot_weights(cells, [("FI",)])[:, 0], cells.M[:, c["FI"]])


# ------------------------------------------------------------------------------ project
def test_project_sums_the_bundles_cells():
    f = channels.fine_split(channels.synthesize_channels(v1_fixture(), seed=0))
    p = channels.project(f, "WHFI")
    assert channels.channels_of(p) == () and p.meta["bundle"] == "WHFI"
    for z in ZIPS:
        a, b = f.G.nodes[z], p.G.nodes[z]
        assert abs(b["M"] - (a["M_c"]["WH"] + a["M_c"]["FI"])) < 1e-12
        assert abs(b["S_free"] - (a["S_free_c"]["WH"] + a["S_free_c"]["FI"])) < 1e-12
        for i, v in b["S"].items():
            assert abs(v - (a["S_c"][i]["WH"] + a["S_c"][i]["FI"])) < 1e-12
    # the whole national bundle reproduces the input instance's masses
    n = channels.project(f, "N")
    for z in ZIPS:
        assert abs(n.G.nodes[z]["M"] - MASS[ZIPS.index(z)]) < 1e-12
    assert "channels" not in p.meta


def test_project_recomputes_cand_and_the_node_classes():
    """A rep with no book in the bundle is not a candidate for the projection."""
    d = cells_fixture()
    f = channels.fine_split(d)
    p = channels.project(f, "WH")            # only zA has WH book
    assert p.G.nodes["zA"]["cand"] == ("R0",)
    assert p.G.nodes["zB"]["cand"] == () and p.G.nodes["zC"]["cand"] == ()
    assert p.uncontested == {"zA": "R0"}
    assert p.untapped == ["zB", "zC"]        # no book and no filler in WH
    assert p.vacant == []
    q = channels.project(f, "N")
    assert q.uncontested == {"zA": "R0", "zB": "R1", "zC": "R2"}


def test_project_induces_edges_and_filters_states():
    f = channels.fine_split(channels.synthesize_channels(v1_fixture(), seed=0))
    p = channels.project(f, "FI", states=["MA"])
    assert sorted(p.G) == ZIPS[:3]
    assert sorted(tuple(sorted(e)) for e in p.G.edges()) == [(ZIPS[0], ZIPS[1]),
                                                             (ZIPS[1], ZIPS[2])]
    # a zero-mass zip of a kept state stays, as it does on load
    q = channels.project(f, "FI", states=["NY"])
    assert ZIPS[3] in q.G and q.G.nodes[ZIPS[3]]["M"] == 0.0


def test_project_refuses_a_missing_channel_or_bundle():
    s = channels.synthesize_channels(v1_fixture(), seed=0)
    for bad in ("WH", ("N_WH",)):             # fine labels are absent before fine_split
        try:
            channels.project(s, bad)
        except ValueError:
            pass
        else:
            raise AssertionError(f"project accepted {bad!r} on file channels")
    try:
        channels.project(channels.fine_split(s), "NOPE")
    except ValueError as e:
        assert "unknown bundle" in str(e)
    else:
        raise AssertionError("project accepted an unknown bundle name")


def test_bundles_table():
    assert channels.BUNDLES["N"] == ("N_WH", "N_FI")
    assert set(channels.BUNDLES) - set(channels.DEFAULT_BUNDLES) == {"WHFI_PLUS"}
    assert all(c in channels.CHANNELS for b in channels.BUNDLES.values() for c in b)


# ------------------------------------------------------------------------------- writers
def test_write_v2_payload():
    """The file layout, checked directly: A1's v2 loader is not needed for this."""
    s = channels.synthesize_channels(v1_fixture(), seed=0)
    with tempfile.TemporaryDirectory() as tmp:
        path = channels.write_v2(s, os.path.join(tmp, "cells.json.gz"))
        with gzip.open(path, "rt", encoding="utf-8") as fh:
            obj = json.load(fh)
    assert obj["format"] == "td_instance_descaled/2"
    assert obj["meta"]["channels"] == list(channels.FILE_CHANNELS)
    n = obj["nodes"]
    assert set(n) == {"z", "channel", "m_rel", "share", "share_free", "state"}
    assert len(n["z"]) == len(ZIPS) * len(channels.FILE_CHANNELS)
    assert sorted(set(n["z"])) == ZIPS              # zero cells are emitted too
    assert len(obj["edges"]["u"]) == len(ZIPS) - 1
    # share is the fraction of that cell's m_rel, so share*m_rel sums back to S_i
    got = {}
    for z, m, sh in zip(n["z"], n["m_rel"], n["share"]):
        for rep, v in sh.items():
            got[(z, rep)] = got.get((z, rep), 0.0) + v * m
    for z in ZIPS:
        for rep, v in s.G.nodes[z]["S"].items():
            assert abs(got[(z, rep)] - v) <= 1e-5 * max(v, 1e-9)


def test_write_v2_round_trip():
    s = channels.synthesize_channels(v1_fixture(), seed=0)
    with tempfile.TemporaryDirectory() as tmp:
        path = channels.write_v2(s, os.path.join(tmp, "cells.json.gz"))
        got = instance.load_descaled(path)
    assert channels.channels_of(got) == channels.FILE_CHANNELS
    assert sorted(got.G) == ZIPS and got.G.number_of_edges() == len(ZIPS) - 1
    for z in ZIPS:
        a, b = s.G.nodes[z], got.G.nodes[z]
        assert abs(b["M"] - a["M"]) <= 1e-5 * max(a["M"], 1e-9)
        assert set(b["S"]) == set(a["S"])
        for i, v in a["S"].items():
            assert abs(b["S"][i] - v) <= 1e-5 * max(v, 1e-9)
        assert abs(b["S_free"] - a["S_free"]) <= 1e-5 * max(a["S_free"], 1e-9)


def test_write_v2_round_trips_into_the_same_cells():
    """The seam the three writers share: `write_v2` -> `load_descaled` -> `aggregate`.

    Two states, the fine labels, every cell totalled by state and channel.  The bound is the
    file's own 6-significant-figure rounding on `m_rel` and on `share`, which `S = share*m_rel`
    carries twice; the channel order survives because `write_v2` declares it in
    `meta["channels"]` and emits every (zip, channel) pair.
    """
    f = channels.fine_split(channels.synthesize_channels(v1_fixture(), seed=0))
    want = channels.aggregate(f, ["MA", "NY"])
    with tempfile.TemporaryDirectory() as tmp:
        path = channels.write_v2(f, os.path.join(tmp, "cells.json.gz"))
        back = instance.load_descaled(path)
    assert back.channels == channels.CHANNELS
    got = channels.aggregate(back, ["MA", "NY"])
    assert got.channels == want.channels and got.reps == want.reps
    assert got.state_list == want.state_list
    for name in ("M", "S", "S_free"):
        a, b = getattr(want, name), getattr(got, name)
        assert a.shape == b.shape, name
        assert np.allclose(b, a, rtol=1e-5, atol=1e-9), name
    # and the national total is still the input instance's, cell by cell
    assert abs(got.M.sum() - sum(f.G.nodes[z]["M"] for z in f.G)) <= 1e-5 * got.M.sum()


def test_write_v1_of_a_projection_loads_back():
    f = channels.fine_split(channels.synthesize_channels(v1_fixture(), seed=0))
    p = channels.project(f, "WH_PLUS")
    with tempfile.TemporaryDirectory() as tmp:
        path = channels.write_v1(p, os.path.join(tmp, "instance_descaled.json.gz"))
        got = instance.load_descaled(path)
    assert sorted(got.G) == sorted(p.G)
    assert got.G.number_of_edges() == p.G.number_of_edges()
    assert got.contested == p.contested and got.uncontested == p.uncontested
    assert got.vacant == p.vacant and got.untapped == p.untapped
    assert got.meta["bundle"] == "WH_PLUS"
    for z in p.G:
        a, b = p.G.nodes[z], got.G.nodes[z]
        assert b["cand"] == a["cand"] and b["state"] == a["state"]
        assert abs(b["M"] - a["M"]) <= 1e-5 * max(a["M"], 1e-9)
        for i, v in a["S"].items():
            assert abs(b["S"][i] - v) <= 1e-5 * max(v, 1e-9)
