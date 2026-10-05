"""tools/exp/split_floor.py (td#94) on toys: forced splits by hand, the parts floor against brute
force, the $-rule K range, and the layouts as scenarios."""
from __future__ import annotations

import importlib.util
import itertools
import math
import os
import random

from td import spec as tdspec

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location(
    "exp_split_floor", os.path.join(HERE, "..", "tools", "exp", "split_floor.py"))
split_floor = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(split_floor)


def test_forced_splits_by_hand():
    # τ = 1 at ±15%: the cap is 1.15; C sits on it and stays whole
    M = {"A": 1.2, "B": 2.4, "C": 1.15, "D": 3.46, "E": 0.5}
    assert split_floor.forced_splits(M, 1.0, 0.15) == {"A": 1, "B": 2, "D": 3}
    assert split_floor.forced_splits(M, 1.0, 0.10) == {"A": 1, "B": 2, "C": 1, "D": 3}


def _brute(masses, k):
    tau = sum(masses) / k
    best = math.inf
    for alloc in itertools.product(range(1, k + 1), repeat=len(masses)):
        if sum(alloc) == k:
            best = min(best, max(abs(m / (a * tau) - 1) for m, a in zip(masses, alloc)))
    return best


def test_parts_floor_matches_brute_force():
    rng = random.Random(94)
    for _ in range(200):
        masses = [rng.uniform(0.2, 6.0) for _ in range(rng.randint(1, 4))]
        k = rng.randint(1, 9)
        d, alloc = split_floor.parts_floor(masses, k)
        b = _brute(masses, k)
        assert d == b if math.isinf(b) else math.isclose(d, b, abs_tol=1e-12)
        if alloc is not None:
            tau = sum(masses) / k
            assert sum(alloc) == k and min(alloc) >= 1
            assert math.isclose(d, max(abs(m / (a * tau) - 1) for m, a in zip(masses, alloc)))


def test_parts_floor_by_hand():
    # parts 1.615 and 9.385 at K 11 (τ 1): the island takes 1 or 2, the rest 10 or 9
    d, alloc = split_floor.parts_floor([9.385, 1.615], 11)
    assert alloc == (9, 2) and math.isclose(d, 0.1925)
    assert split_floor.parts_floor([1.0, 1.0, 1.0], 2) == (math.inf, None)


def test_k_range():
    # $10,140M at a $1,000M target: 10 ($1,014M) and 11 ($922M) are within ±10%, 12 ($845M) not
    assert list(split_floor.k_range(10140.0, [1000.0])) == [10, 11]
    # several targets: the union of their ranges
    assert list(split_floor.k_range(3370.0, [1250.0, 1000.0, 900.0])) == [3, 4]


def test_components():
    adj = {"A": {"B"}, "B": {"A", "C"}, "C": {"B", "D"}, "D": {"C"}, "E": set()}
    assert split_floor.components(["A", "B", "D", "E"], adj) == [["A", "B"], ["D"], ["E"]]


def test_channel_rows_on_a_toy():
    # two parts: {A, B} with 3.0 and {D} with 1.0; K 4, τ 1
    M = {"A": 2.5, "B": 0.5, "D": 1.0}
    adj = {"A": {"B"}, "B": {"A", "C"}, "C": {"B", "D"}, "D": {"C"}}
    (row,) = split_floor.channel_rows("WH", M, adj, 4000.0, [4], [0.10])
    assert row["usd_per_district_m"] == 1000.0 and row["usd_ok"]
    assert row["parts"] == ["A+1", "D"]
    b = row["bands"][0.10]
    assert b["forced"] == {"A": 2} and b["n_forced"] == 1 and b["cuts"] == 2
    assert b["allocation"] == (3, 1) and b["parts_floor"] == 0.0 and b["feasible"]


def test_layouts_partition_the_units():
    for layout, combined in split_floor.LAYOUTS.items():
        s = tdspec.parse(split_floor.layout_raw(combined))
        assert set(s.channels) == {"national", "WH", "FI"} | ({"combined"} if combined else set())
        rest = set(s.units) - set(combined)
        for c in ("national", "WH", "FI"):
            assert set(s.channels[c].domain) == rest
        if combined:
            assert set(s.channels["combined"].domain) == set(combined)
            assert all(s.channel_of(u, "wells_fi") == "combined" for u in combined)


def test_s13_forced_splits_on_the_extract():
    """The 11 mass-forced splits at s13's K (national 15, WH 12, FI 20) on NE + plains at ±10%
    (docs/memory/facts/scenario-sweeps-2026-10.md); SKIP without `$TD_REPO`'s extract."""
    if not os.path.exists(split_floor.EXTRACT):
        print(f"SKIP  test_split_floor.py: no {split_floor.EXTRACT}; the s13 check did not run",
              flush=True)
        return
    from td import data, geo
    ref = geo.read_reference()
    raw = data.load(split_floor.EXTRACT)
    baseline = split_floor.BASELINE_K["ne_plains"]
    rows, _ = split_floor.layout_tables(split_floor.layout_raw(split_floor.LAYOUTS["ne_plains"]),
                                        data.conus(raw, ref), ref, split_floor.usd_factors(raw),
                                        [0.10], baseline)
    forced = {r["channel"]: sorted(r["bands"][0.10]["forced"]) for r in rows
              if baseline[r["channel"]] == r["k"]}
    assert forced == {"national": ["CA", "FL", "NY", "TX"], "WH": ["CA", "FL"],
                      "FI": ["CA", "FL", "NY", "OH", "PA"], "combined": []}


def test_ifa_usd_on_the_whole_extract():
    """IFA's $ rule is on the whole extract's $62.14B (owner, 2026-10-04): K 46-55 pass and the
    listed K 45 fails; SKIP without `$TD_REPO`'s extract and 2025 downloads."""
    if not (os.path.exists(split_floor.EXTRACT) and os.path.isdir(split_floor.PUBLIC)):
        print(f"SKIP  test_split_floor.py: no {split_floor.EXTRACT} or {split_floor.PUBLIC}; "
              "the IFA $ check did not run", flush=True)
        return
    from td import data, geo
    ref = geo.read_reference()
    raw = data.load(split_floor.EXTRACT)
    rows, _ = split_floor.layout_tables(split_floor.ifa_raw(), data.conus(raw, ref), ref,
                                        split_floor.usd_factors(raw), [0.15], {})
    assert [r["k"] for r in rows] == list(range(45, 56))
    assert [r["k"] for r in rows if r["usd_ok"]] == list(range(46, 56))
    assert all(math.isclose(r["usd_per_district_m"] * r["k"], 62140.0) for r in rows)
