"""tools/exp/region_arith.py (regional sealing arithmetic) on a five-state toy with hand values,
the partitions, the division-coarsening enumerator, and §10's feasible K on the dollar extract (SKIP without it)."""
from __future__ import annotations

import importlib.util
import math
import os

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location(
    "exp_region_arith", os.path.join(HERE, "..", "tools", "exp", "region_arith.py"))
region_arith = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(region_arith)

# a path A-B-C-D-E in $M, window 10-20: C alone is over the window top
M = {"A": 4.0, "B": 6.0, "C": 25.0, "D": 3.0, "E": 12.0}
ADJ = {"A": {"B"}, "B": {"A", "C"}, "C": {"B", "D"}, "D": {"C", "E"}, "E": {"D"}}
LO, HI = 10.0, 20.0


def test_region_analysis_by_hand():
    r = region_arith.region_analysis(M, ADJ, LO, HI)
    # $50M: k 3 ($16.67M) and 4 ($12.5M) are strictly inside; k 5 is on the edge, k 2 is $25M
    assert sorted(r["k"]) == [3, 4] and r["usd"] == 50.0 and len(r["components"]) == 1
    assert r["k"][3]["forced_top"] == {"C": 1}
    # k 3: δ = 0.2, the band top 20.0; k 4: δ = 0.2, the band top 15.0; C is over both
    assert math.isclose(r["k"][3]["delta"], 0.2) and r["k"][3]["forced_band"] == {"C": 1}
    assert math.isclose(r["k"][4]["delta"], 0.2) and r["k"][4]["forced_band"] == {"C": 1}
    assert all(v["ok_band"] and v["ok_win"] for v in r["k"].values())


def test_parts_check_on_two_components():
    # two islands of $30M and $20M: k 5 gives 2 + 3 districts at $15M and $6.7M: the second misses
    two = {"A": 30.0, "B": 20.0}
    r = region_arith.region_analysis(two, {"A": set(), "B": set()}, LO, HI)
    assert len(r["components"]) == 2
    assert r["k"][3]["ok_win"] is True       # 30 / 2 = 15 and 20 / 1 = 20
    assert r["k"][3]["parts_floor"] > 0
    assert not region_arith.parts_in_window([30.0, 20.0], 2, LO, HI)
    assert not region_arith.parts_in_window([5.0, 20.0], 3, LO, HI)


def test_sumset_adds_regions_and_counts_forced():
    a = region_arith.region_analysis({"A": 30.0, "B": 14.0}, {"A": {"B"}, "B": {"A"}}, LO, HI)
    b = region_arith.region_analysis(M, ADJ, LO, HI)
    reach = region_arith.sumset([region_arith.pass_k(a), region_arith.pass_k(b)])
    # a: $44M, k 3 ($14.67M, band top 19.33: A over by 1 cut) and 4 ($11M, band top 12: A 2 cuts,
    # B 1); b: k 3 and 4 (C over by 1 cut either way): totals 6 to 8
    assert sorted(a["k"]) == [3, 4] and sorted(reach) == [6, 7, 8]
    assert reach[6][:2] == (2, 2) and reach[7][:2] == (2, 2) and reach[8][:2] == (3, 4)
    assert reach[7][2] == (3, 4)
    assert region_arith.sumset([region_arith.pass_k(a), {}]) == {}


def test_headroom_by_hand():
    # §10: 2 min(avg - L, U - avg) / (U - L)
    assert math.isclose(region_arith.headroom(1206.9, 1000.0, 1437.5), 2 * 206.9 / 437.5)
    assert region_arith.headroom(15.0, LO, HI) == 1.0


def test_groups_cover_and_core():
    reg = region_arith.Region(M, ADJ, LO, HI)
    groups = {tuple(reg.states(g[0])) for g in reg.groups()}
    assert groups == {("A", "B"), ("E",), ("D", "E")}
    g = region_arith.grouping(reg)
    assert g["small"] == ["A", "B", "D"] and g["counts"] == {"4": 3, "6": 3, "none": 3}
    assert g["cover"]["4"]["ok"] and sorted(map(sorted, g["cover"]["4"]["groups"])) == [["A", "B"], ["D", "E"]]
    # without E, D has no group: the core is D and the carving job is C's
    sub = {s: M[s] for s in "ABCD"}
    g = region_arith.grouping(region_arith.Region(sub, ADJ, LO, HI))
    assert not g["cover"]["4"]["ok"] and g["cover"]["4"]["zero_group"] == ["D"]
    assert g["cover"]["4"]["core"] == ["D"]
    job = g["jobs"][0]
    assert (job["state"], job["kind"], job["k"], job["alone_ok"]) == ("C", "must", [2], True)
    # attach sets of C: {B}, {D}, {A, B}; each leaves room for a piece of C
    assert job["attach"] == 3 and job["attach_usable"] == 3
    assert g["orphans"] == [] and g["orphans_any"] == []    # D rides on C's piece


def test_orphan_with_no_split_neighbour():
    alone = {"A": 4.0, "B": 6.0, "G": 3.0}
    adj = {"A": {"B"}, "B": {"A"}, "G": set()}
    g = region_arith.grouping(region_arith.Region(alone, adj, LO, HI))
    # A + B ($10M) is a group; G has no group and no split neighbour to ride on
    assert g["orphans"] == ["G"] and g["orphans_usable"] == ["G"] and g["orphans_any"] == ["G"]
    assert not g["cover"]["6"]["ok"] and g["cover"]["6"]["core"] == ["G"]


def test_partitions_cover_the_49_units():
    parts = region_arith.partitions()
    assert list(parts) == ["P0", "P1", "P2", "P3"]
    assert [len(p) for p in parts.values()] == [1, 6, 9, 4]
    for p in parts.values():
        assert sum(len(s) for s in p.values()) == 49
    assert parts["P3"]["Northeast"] == ["CT", "ME", "MA", "NH", "RI", "VT", "NJ", "NY", "PA"]
    assert "DC" in parts["P1"]["SouthAtlantic"] and "CO" in parts["P1"]["Midwest"]


def test_section10_k_on_the_extract():
    """P0 reproduces the research note's §10 feasible K; IFA's six regions reach K 48-54.  SKIP
    without the dollar extract."""
    if not os.path.exists(region_arith.overnight.EXTRACT):
        print(f"SKIP  test_region_arith.py: no {region_arith.overnight.EXTRACT}; "
              "the §10 check did not run", flush=True)
        return
    cells = region_arith.overnight.state_cells(region_arith.overnight.EXTRACT)
    adj = region_arith.state_graph()
    parts = region_arith.partitions()
    sts = region_arith.structures(cells)
    tr = region_arith.total_rows("ne_plains", sts["ne_plains"], {"P0": parts["P0"]}, adj, range(48, 53))
    assert {c: (min(k), max(k)) for c, k in tr["f0"].items()} == region_arith.SECTION10_K["ne_plains"]
    tr = region_arith.total_rows("ifa", sts["ifa"], {"P1": parts["P1"]}, adj, region_arith.IFA_TOTALS)
    reach = tr["partitions"]["P1"]["tracks"]["band"]["reach"]["IFA"]
    assert all(t in reach for t in region_arith.IFA_TOTALS)


def test_coarsenings_are_connected_unions():
    # path A-B-C-D-E; divisions X = A B, Y = C, Z = D E, W has no footprint state (dropped)
    divs = {"X": ["A", "B"], "Y": ["C"], "Z": ["D", "E"], "W": []}
    got = region_arith.coarsenings(divs, ADJ)
    assert sorted(got) == sorted([[("X",), ("Y",), ("Z",)], [("X", "Y"), ("Z",)],
                                  [("X",), ("Y", "Z")], [("X", "Y", "Z")]])
    # X + Z alone is not connected (Y is the bridge): no coarsening has that block
    assert all(("X", "Z") not in c for c in got)
    # a division with two apart states cannot be a region alone: only the union with its bridge
    far = {"P": ["A", "E"], "Q": ["B", "C", "D"]}
    assert region_arith.coarsenings(far, ADJ) == [[("P", "Q")]]
    assert len(list(region_arith.set_partitions(list("abcd")))) == 15       # Bell(4)


def test_coarsening_k_sums_and_ranking():
    # window 10-20; the dollars of M: X = A+B is $10M (k 1, headroom 0), Y = C is $25M (k 2),
    # Z = D+E is $15M (k 1); X + Y is $35M (k 2, 3), Y + Z $40M (k 3), all five $50M (k 3, 4)
    divs = {"X": ["A", "B"], "Y": ["C"], "Z": ["D", "E"]}
    found = region_arith.search_channel(M, divs, ADJ, LO, HI)
    assert found["n"] == 4
    k3 = region_arith.feasible_at(found, 3, "win")
    assert [r["divisions"] for r in k3] == [[("X", "Y"), ("Z",)], [("X", "Y", "Z")]]
    # the best has most regions; its K per region sum to 3 and the headroom is the smaller one
    assert k3[0]["ks"] == (2, 1) and sum(k3[0]["ks"]) == 3
    assert math.isclose(k3[0]["head"], min(region_arith.headroom(35 / 2, LO, HI),
                                            region_arith.headroom(15.0, LO, HI)))
    # K 4: X, Y, Z alone take 1 + 2 + 1 (most regions), then X+Y with Z (3 + 1, headroom 1/3), then
    # X with Y+Z (1 + 3, headroom 0), then all three together
    k4 = region_arith.feasible_at(found, 4, "win")
    assert [r["divisions"] for r in k4] == [[("X",), ("Y",), ("Z",)], [("X", "Y"), ("Z",)],
                                           [("X",), ("Y", "Z")], [("X", "Y", "Z")]]
    assert [r["ks"] for r in k4] == [(1, 2, 1), (3, 1), (1, 3), (4,)]
    assert region_arith.feasible_at(found, 2, "win") == []     # no region set sums to 2
    # every feasible coarsening: regional K add up to the K asked, each region inside its own set
    for k in (3, 4):
        for r in region_arith.feasible_at(found, k, "win"):
            assert sum(r["ks"]) == k
            assert all(kk in region_arith.pass_k(info, "win") for kk, info in zip(r["ks"], r["infos"]))


def test_corridor_blocks_restrict_to_footprint():
    foot = {"NY", "PA", "VA", "OH", "CT"}
    v = region_arith.CORRIDOR_VARIANTS["B2 NY,NJ,PA,NE / DE,MD,DC,VA"]
    assert region_arith.corridor_blocks(v, foot) == [["CT", "NY", "PA"], ["VA"]]
    assert region_arith.corridor_blocks([["DE", "MD"]], foot) == []


def test_report_header_carries_arithmetic_notice():
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        for fn in ("7b_ifa_combos.md", "4_summary.md"):
            path = os.path.join(d, fn)
            region_arith.write_report(path, ["# a pass table", "", "| K | pass |", "|---|---|", "| 50 | yes |"])
            head = open(path, encoding="utf-8").read().splitlines()
            assert head[0] == region_arith.ARITH_NOTICE and head[2] == "# a pass table"
            assert "Arithmetic only; no feasibility certificate" in head[0]
    # no generated report bypasses the helper
    src = open(os.path.join(HERE, "..", "tools", "exp", "region_arith.py"), encoding="utf-8").read()
    assert "fh.write(" not in src.replace('fh.write("\\n".join([ARITH_NOTICE', "")
