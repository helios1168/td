"""
test_instance_v2.py: the (zip, channel) node table of `td_instance_descaled/2`.

The fixtures are hand-written JSON rather than exporter output: the loader's contract is the
file format, and this module has to stay readable when the exporter changes underneath it.
The pair `V1_NODES` / `V2_NODES` is the same instance twice, the v1 rows being the v2 rows
summed over channels, with every magnitude a binary fraction so the two arithmetics agree
exactly.  On a real export the two forms agree only to the exporter's 6-significant-figure
rounding, the same bound `test_instance.py::test_descaling_is_division_by_one_constant`
states.
"""
from __future__ import annotations

import gzip
import json
import os
import tempfile

from td import instance as descaled              # noqa: E402

CONUS = "/Users/ntlee/projects/td/instance_descaled_v2_conus.json.gz"

EDGES = {"u": ["10001", "10002", "10003"], "v": ["10002", "10003", "10004"]}

# zip-major, channels in the order national, wh, fi:
#   10001  all three channels, three reps, filler book in wh   -> contested
#   10002  wh only                                             -> uncontested
#   10003  national only, filler book and no rep               -> vacant
#   10004  fi only, nothing at all                             -> untapped
V2_NODES = {
    "z":          ["10001", "10001", "10001", "10002", "10003", "10004"],
    "channel":    ["national", "wh", "fi", "wh", "national", "fi"],
    "m_rel":      [2.0, 1.0, 1.0, 1.0, 2.0, 1.0],
    "share":      [{"R1": 0.25, "R2": 0.5}, {"R1": 0.5}, {"R3": 0.25},
                   {"R2": 0.5}, {}, {}],
    "share_free": [0.0, 0.25, 0.0, 0.0, 0.5, 0.0],
    "state":      ["NY", "NY", "NY", "NY", "NJ", "NJ"],
}

# the same instance with each zip's cells already summed: M = sum m_rel, and every share
# re-expressed as a fraction of that sum (R1 at 10001: (0.25*2 + 0.5*1)/4 = 0.25)
V1_NODES = {
    "z":          ["10001", "10002", "10003", "10004"],
    "m_rel":      [4.0, 1.0, 2.0, 1.0],
    "share":      [{"R1": 0.25, "R2": 0.25, "R3": 0.0625}, {"R2": 0.5}, {}, {}],
    "share_free": [0.0625, 0.0, 0.5, 0.0],
    "state":      ["NY", "NY", "NJ", "NJ"],
}


def _write(tmp, fmt, nodes, **extra):
    path = os.path.join(tmp, "instance_descaled.json.gz")
    obj = {"format": fmt, "nodes": nodes, "edges": EDGES,
           "firm": {"R1": "F_A", "R2": "F_A", "R3": "F_B"},
           "meta": {"scale_stripped": True, **extra}}
    with gzip.open(path, "wt", encoding="utf-8") as fh:
        json.dump(obj, fh)
    return path


def _v1(tmp):
    return descaled.load_descaled(_write(tmp, descaled.FORMAT, V1_NODES))


def _v2(tmp, nodes=None):
    nodes = nodes or V2_NODES
    return descaled.load_descaled(
        _write(tmp, descaled.FORMAT_V2, nodes,
               channels=list(dict.fromkeys(nodes["channel"]))))


# ------------------------------------------------------------------------------ format 1
def test_v1_is_unchanged_and_carries_no_channels():
    with tempfile.TemporaryDirectory() as tmp:
        d = _v1(tmp)
        assert d.channels == ()
        assert d.G.number_of_nodes() == 4 and d.G.number_of_edges() == 3
        assert d.contested == ["10001"]
        assert d.uncontested == {"10002": "R2"}
        assert d.vacant == ["10003"] and d.untapped == ["10004"]
        n = d.G.nodes["10001"]
        assert n["M"] == 4.0 and n["S_free"] == 0.25 and n["state"] == "NY"
        assert n["S"] == {"R1": 1.0, "R2": 1.0, "R3": 0.25}
        for z in d.G:
            assert not {"M_c", "S_c", "S_free_c"} & set(d.G.nodes[z])


# ------------------------------------------------------------------------------ format 2
def test_v2_totals_are_the_sum_over_channels():
    with tempfile.TemporaryDirectory() as tmp:
        d = _v2(tmp)
        assert d.channels == ("national", "wh", "fi")
        assert d.meta["channels"] == ["national", "wh", "fi"]
        assert d.G.number_of_nodes() == 4 and d.G.number_of_edges() == 3
        assert d.contested == ["10001"]
        assert d.uncontested == {"10002": "R2"}
        assert d.vacant == ["10003"] and d.untapped == ["10004"]

        n = d.G.nodes["10001"]
        assert n["M"] == sum(n["M_c"].values()) == 4.0
        assert n["S_free"] == sum(n["S_free_c"].values()) == 0.25
        assert n["cand"] == ("R1", "R2", "R3")
        for rep, tot in n["S"].items():
            assert tot == sum(n["S_c"][rep].values())
        assert n["S"] == {"R1": 1.0, "R2": 1.0, "R3": 0.25}


def test_v2_per_channel_attrs():
    with tempfile.TemporaryDirectory() as tmp:
        n = _v2(tmp).G.nodes["10001"]
        assert n["M_c"] == {"national": 2.0, "wh": 1.0, "fi": 1.0}
        assert n["S_free_c"] == {"national": 0.0, "wh": 0.25, "fi": 0.0}
        # a rep appears only under the channels where it has book
        assert n["S_c"] == {"R1": {"national": 0.5, "wh": 0.5},
                            "R2": {"national": 1.0},
                            "R3": {"fi": 0.25}}


def test_v2_zip_in_one_channel_only():
    """Nothing assumes a zip carries every channel."""
    with tempfile.TemporaryDirectory() as tmp:
        d = _v2(tmp)
        wh_only, nat_only = d.G.nodes["10002"], d.G.nodes["10003"]
        assert wh_only["M_c"] == {"wh": 1.0}
        assert wh_only["S_c"] == {"R2": {"wh": 0.5}}
        assert wh_only["M"] == 1.0 and wh_only["S"] == {"R2": 0.5}
        assert nat_only["M_c"] == {"national": 2.0}
        assert nat_only["S_c"] == {} and nat_only["S_free_c"] == {"national": 1.0}
        assert nat_only["S_free"] == 1.0 and nat_only["state"] == "NJ"


def test_v2_channel_order_comes_from_the_file():
    with tempfile.TemporaryDirectory() as tmp:
        flipped = {k: list(reversed(v)) for k, v in V2_NODES.items()}
        d = _v2(tmp, flipped)
        assert d.channels == ("fi", "national", "wh")
        assert d.G.nodes["10001"]["M"] == 4.0          # folding is order-independent


def test_v2_matches_v1_on_the_summed_instance():
    """Same numbers either way: the totals are all the model reads."""
    with tempfile.TemporaryDirectory() as tmp:
        one, two = _v1(tmp), _v2(tmp)
        assert set(one.G) == set(two.G)
        assert one.contested == two.contested and one.uncontested == two.uncontested
        assert one.vacant == two.vacant and one.untapped == two.untapped
        for z in one.G:
            got = dict(two.G.nodes[z])
            for key in ("M_c", "S_c", "S_free_c"):
                got.pop(key)
            assert got == dict(one.G.nodes[z]), z


def test_v2_rejects_a_duplicated_cell():
    with tempfile.TemporaryDirectory() as tmp:
        dup = {k: v + [v[0]] for k, v in V2_NODES.items()}     # 10001/national twice
        try:
            _v2(tmp, dup)
            raise AssertionError("expected ValueError")
        except ValueError as e:
            assert "channel 'national' twice" in str(e)


def test_unknown_format_names_both():
    with tempfile.TemporaryDirectory() as tmp:
        try:
            descaled.load_descaled(_write(tmp, "td_instance_descaled/9", V1_NODES))
            raise AssertionError("expected ValueError")
        except ValueError as e:
            assert descaled.FORMAT in str(e) and descaled.FORMAT_V2 in str(e)


# --------------------------------------------------------------- the hub's real instance
def test_real_conus_instance_still_loads():
    """The live instance is format 1; loading it must not have moved (CLAUDE.md: hub only)."""
    if not os.path.exists(CONUS):
        return
    d = descaled.load_descaled(CONUS)
    assert d.G.number_of_nodes() == 3713
    assert d.channels == ()
