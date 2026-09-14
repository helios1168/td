"""tests/test_solve_western_merged.py

Unit and regression tests for tools/solve_western_merged.py.
Verifies exact data loading, mass totals, contiguity on cell graph G,
pairwise distance calculations, and 1-district vs 2-district optimization.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
import networkx as nx
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

from tools import solve_western_merged


def test_western_mass_totals():
    """Verify exact live channel mass sums match formulation expectations."""
    data = solve_western_merged.load_western_instance(solve_western_merged.DEFAULT_INSTANCE)
    summary = data["state_summary"]

    assert len(summary) == 7
    expected_states = {"CO", "ID", "MT", "ND", "NE", "SD", "WY"}
    assert set(summary.keys()) == expected_states

    tot_zips = sum(s["n_zips"] for s in summary.values())
    tot_nat = sum(s["national"] for s in summary.values())
    tot_wh = sum(s["wh"] for s in summary.values())
    tot_fi = sum(s["fi"] for s in summary.values())
    tot_whfi = sum(s["whfi"] for s in summary.values())
    tot_plus = sum(s["whfi_plus"] for s in summary.values())

    assert tot_zips == 223
    # WHFI total is 431.26 descaled units
    assert abs(tot_whfi - 431.2570) < 1e-3
    assert round(tot_whfi, 2) == 431.26

    # WHFI_PLUS total is 689.01 descaled units
    assert abs(tot_plus - 689.0125) < 1e-3
    assert round(tot_plus, 2) == 689.01

    # National mass is 257.76
    assert abs(tot_nat - 257.7555) < 1e-3


def test_cell_graph_rook_contiguity():
    """Verify all 223 western zips form exactly 1 connected component on cell graph G."""
    data = solve_western_merged.load_western_instance(solve_western_merged.DEFAULT_INSTANCE)
    geo_data = solve_western_merged.load_geo_and_graph(
        solve_western_merged.DEFAULT_GEO_CACHE, zip_state=data["zip_state"]
    )
    G_cell = geo_data["G_cell"]

    assert G_cell.number_of_nodes() == 223
    assert G_cell.number_of_edges() == 608
    comps = list(nx.connected_components(G_cell))
    assert len(comps) == 1, f"Expected 1 component, got {len(comps)}"

    # Each individual state must also be internally contiguous
    for st in solve_western_merged.WESTERN_STATES:
        st_zips = [z for z, s in data["zip_state"].items() if s == st]
        st_sub = G_cell.subgraph(st_zips)
        st_comps = list(nx.connected_components(st_sub))
        assert len(st_comps) == 1, f"State {st} has {len(st_comps)} disconnected components!"


def test_pairwise_distances_and_infeasibility():
    """Verify exact pairwise distances and 900 km threshold exceedances."""
    data = solve_western_merged.load_western_instance(solve_western_merged.DEFAULT_INSTANCE)
    geo_data = solve_western_merged.load_geo_and_graph(
        solve_western_merged.DEFAULT_GEO_CACHE, zip_state=data["zip_state"]
    )
    coords = geo_data["state_coords"]
    pw_records = solve_western_merged.compute_pairwise_distances(
        coords, sorted(solve_western_merged.WESTERN_STATES)
    )

    assert len(pw_records) == 21
    violating = [r for r in pw_records if r["exceeds_900km"]]
    assert len(violating) == 7

    # Max distance is between ID and NE
    max_rec = max(pw_records, key=lambda r: r["distance_km"])
    assert {max_rec["state_a"], max_rec["state_b"]} == {"ID", "NE"}
    assert abs(max_rec["distance_km"] - 1242.75) < 1.0


def test_mass_weighted_centroid_radius():
    """Verify that from mass-weighted centers, all states are within 850 km (< 900 km)."""
    data = solve_western_merged.load_western_instance(solve_western_merged.DEFAULT_INSTANCE)
    geo_data = solve_western_merged.load_geo_and_graph(
        solve_western_merged.DEFAULT_GEO_CACHE, zip_state=data["zip_state"]
    )
    res_whfi = solve_western_merged.analyze_1district(
        "WHFI", data["state_summary"], geo_data["state_coords"], geo_data["G_cell"], data["zip_state"]
    )
    res_plus = solve_western_merged.analyze_1district(
        "WHFI_PLUS", data["state_summary"], geo_data["state_coords"], geo_data["G_cell"], data["zip_state"]
    )

    assert res_whfi["max_radius_from_center_km"] < 850.0
    assert res_whfi["radius_within_900km"] is True
    assert res_plus["max_radius_from_center_km"] < 850.0
    assert res_plus["radius_within_900km"] is True


def test_two_district_connected_partitions():
    """Verify all 21 connected 2-partitions preserve 100% rook contiguity at zip level."""
    data = solve_western_merged.load_western_instance(solve_western_merged.DEFAULT_INSTANCE)
    geo_data = solve_western_merged.load_geo_and_graph(
        solve_western_merged.DEFAULT_GEO_CACHE, zip_state=data["zip_state"]
    )
    parts = solve_western_merged.solve_2district_partitions(
        "WHFI", data["state_summary"], geo_data["state_coords"], geo_data["G_state"], geo_data["G_cell"], data["zip_state"]
    )

    assert len(parts) == 21
    assert all(p["both_cell_contiguous"] for p in parts)

    # Rank 1 partition by min-max distance is {ND, NE, SD} vs {CO, ID, MT, WY}
    parts.sort(key=lambda p: (p["overall_max_distance_km"], p["mass_diff"]))
    best = parts[0]
    assert set(best["d1_states"]) == {"ND", "NE", "SD"}
    assert set(best["d2_states"]) == {"CO", "ID", "MT", "WY"}
    assert abs(best["overall_max_distance_km"] - 959.78) < 1.0


def test_split_wyoming_realization():
    """Verify that splitting Wyoming along natural boundaries yields two 100% contiguous districts."""
    data = solve_western_merged.load_western_instance(solve_western_merged.DEFAULT_INSTANCE)
    geo_data = solve_western_merged.load_geo_and_graph(
        solve_western_merged.DEFAULT_GEO_CACHE, zip_state=data["zip_state"]
    )
    G = geo_data["G_cell"]
    nat_zips = data["zip_state"]

    wy_nw = {"83001", "82414", "82801"}
    wy_se = {"82001", "82009", "82070", "82072", "82601", "82604", "82716"}

    # D1: ID, MT, ND + wy_nw
    z1 = [z for z, st in nat_zips.items() if st in ("ID", "MT", "ND") or z in wy_nw]
    # D2: CO, NE, SD + wy_se
    z2 = [z for z, st in nat_zips.items() if st in ("CO", "NE", "SD") or z in wy_se]

    assert len(z1) + len(z2) == 223
    assert len(set(z1) & set(z2)) == 0

    assert nx.number_connected_components(G.subgraph(z1)) == 1
    assert nx.number_connected_components(G.subgraph(z2)) == 1
