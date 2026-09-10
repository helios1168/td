"""test_instance_split_national.py: tools/instance_split_national.py on a toy national/wh/fi
instance.

The load-bearing properties: the three sub-channels sum back to exactly the input's `national`
cell (mass, every rep's book, and free book alike), `wh` and `fi` pass through untouched, and
`fine_split` on the result takes the exact sub-channel rule with no fallback.
"""
from __future__ import annotations

import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
for _p in (HERE, os.path.join(ROOT, "tools"), ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from td import channels                             # noqa: E402
import instance_split_national as cli               # noqa: E402


def _toy():
    """A v2 instance carrying national, wh, fi: reuse `td.channels.synthesize_channels` on a
    hand-built v1 fixture, the same route `tests/test_channels.py` takes."""
    import networkx as nx
    from td import instance as td_instance

    zips = ["z0", "z1"]
    G = nx.Graph()
    G.add_node("z0", cand=("R0", "R1"), S={"R0": 40.0, "R1": 10.0}, M=100.0, S_free=5.0,
              state="MA")
    G.add_node("z1", cand=("R1",), S={"R1": 20.0}, M=40.0, S_free=0.0, state="NY")
    G.add_edge("z0", "z1")
    d = td_instance.Descaled(G=G, contested=["z0"], uncontested={"z1": "R1"}, vacant=[],
                             untapped=[], firm={"R0": "F_A", "R1": "F_B"}, meta={})
    return channels.synthesize_channels(d, seed=0)


def test_split_national_sums_back_to_the_input_and_leaves_wh_fi_untouched():
    d = _toy()
    out = cli.split_national(d, chase=0.5, wells_wh=0.3, wells_fi=0.2)
    assert channels.channels_of(out) == channels.SUB_CHANNELS + ("wh", "fi")
    assert out.meta["channel_groups"] == {"national": list(channels.SUB_CHANNELS)}
    assert out.meta["synthetic_split"] == {"chase": 0.5, "wells_wh": 0.3, "wells_fi": 0.2}
    for z in d.G:
        a, b = d.G.nodes[z], out.G.nodes[z]
        total = sum(b["M_c"][c] for c in channels.SUB_CHANNELS)
        assert abs(total - a["M_c"]["national"]) < 1e-9
        assert b["M_c"]["wh"] == a["M_c"]["wh"] and b["M_c"]["fi"] == a["M_c"]["fi"]
        assert abs(b["M_c"]["national_chase"] - 0.5 * a["M_c"]["national"]) < 1e-9
        assert abs(b["M_c"]["national_wells_wh"] - 0.3 * a["M_c"]["national"]) < 1e-9
        assert abs(b["M_c"]["national_wells_fi"] - 0.2 * a["M_c"]["national"]) < 1e-9
        for i, per in b["S_c"].items():
            nat_total = sum(per[c] for c in channels.SUB_CHANNELS)
            assert abs(nat_total - a["S_c"][i]["national"]) < 1e-9
        f_total = sum(b["S_free_c"][c] for c in channels.SUB_CHANNELS)
        assert abs(f_total - a["S_free_c"]["national"]) < 1e-9
        # totals unchanged: only national's own mass moved
        assert b["M"] == a["M"] and b["S"] == a["S"] and b["S_free"] == a["S_free"]


def test_split_national_fine_split_is_exact_with_no_fallback():
    out = cli.split_national(_toy(), chase=0.5, wells_wh=0.3, wells_fi=0.2)
    f = channels.fine_split(out)
    assert f.meta["fine_split"] == "sub-channels"
    assert f.meta["fine_split_fallback"] == {}


def test_split_national_rejects_shares_not_summing_to_one():
    try:
        cli.split_national(_toy(), chase=0.5, wells_wh=0.3, wells_fi=0.3)
    except ValueError as e:
        assert "sum to 1" in str(e)
    else:
        raise AssertionError("split_national accepted shares that do not sum to 1")


def test_split_national_rejects_an_instance_already_carrying_sub_channels():
    d = channels.synthesize_channels(_toy(), seed=0, sub_channels=True)
    # _toy() already synthesized once; re-synthesizing sub-channels replaces its channel set,
    # so this instance no longer carries plain 'national'
    try:
        cli.split_national(d, chase=0.5, wells_wh=0.3, wells_fi=0.2)
    except ValueError as e:
        assert "national" in str(e)
    else:
        raise AssertionError("split_national accepted an instance with no plain national channel")


def test_main_round_trips_through_write_v2():
    from td import instance as td_instance

    with tempfile.TemporaryDirectory() as tmp:
        src = os.path.join(tmp, "src.json.gz")
        dst = os.path.join(tmp, "dst.json.gz")
        channels.write_v2(_toy(), src)
        assert cli.main([src, dst]) == 0
        got = td_instance.load_descaled(dst)
        assert channels.channels_of(got) == channels.SUB_CHANNELS + ("wh", "fi")
        assert got.meta["channel_groups"] == {"national": list(channels.SUB_CHANNELS)}
        f = channels.fine_split(got)
        assert f.meta["fine_split"] == "sub-channels"
