"""tests/test_solve_global_multichannel.py

Unit tests for Global Support-Based Multi-Channel Partitioning.
"""
from __future__ import annotations

from pathlib import Path
import sys
import networkx as nx
import numpy as np

WT = Path("/Users/Shared/sv-ntlee/repos/td/.claude/worktrees/agy-math-review-memo")
ROOT = Path(__file__).resolve().parents[1]
for p in [WT / "tools", WT, ROOT / "tools", ROOT]:
    if p.exists():
        p_str = str(p)
        while p_str in sys.path:
            sys.path.remove(p_str)
        sys.path.insert(0, p_str)

from tools.solve_global_multichannel import (
    generate_supports,
    solve_channel_model,
    verify_solution,
    DEFAULT_DIST_OVERRIDES,
    WESTERN_7
)


def test_generate_supports_line_graph():
    state_list = ["S0", "S1", "S2", "S3"]
    edges = [(0, 1), (1, 2), (2, 3)]
    state_xy = np.array([[0.0, 0.0], [50.0, 0.0], [100.0, 0.0], [150.0, 0.0]])
    # max_size=3, max_dist=100
    sups = generate_supports(state_list, edges, state_xy, max_size=3, max_dist=100.0)
    # Size 1: 4
    # Size 2: 3 (all <= 50 distance)
    # Size 3: (0,1,2) has dist 100 <= 100, (1,2,3) has dist 100 <= 100
    assert (0, 1, 2) in sups
    assert (1, 2, 3) in sups
    # (0, 1, 2, 3) exceeds max_size
    assert (0, 1, 2, 3) not in sups


def test_solve_channel_model_toy():
    state_list = ["A", "B", "C", "D"]
    edges = [(0, 1), (1, 2), (2, 3)]
    state_xy = np.array([[0.0, 0.0], [50.0, 0.0], [100.0, 0.0], [150.0, 0.0]])
    w = np.array([50.0, 50.0, 50.0, 50.0])  # total 200, 2 districts of target 100
    sups = generate_supports(state_list, edges, state_xy, max_size=3, max_dist=100.0)

    # Solve for 2 districts, band [90, 110]
    res = solve_channel_model(
        channel_name="TOY",
        w=w,
        state_list=state_list,
        state_xy=state_xy,
        edges=edges,
        supports=sups,
        count=2,
        band=(90.0, 110.0),
        splittable=set(),
        macro_caps={},
        time_limit=10.0
    )
    assert res["solved"]
    assert len(res["districts"]) == 2
    for d in res["districts"]:
        assert 90.0 <= d["mass"] <= 110.0

    G = nx.Graph()
    G.add_nodes_from(range(4))
    G.add_edges_from(edges)
    ok, errs = verify_solution(res["districts"], w, state_list, G, (90.0, 110.0), {})
    assert ok, f"Verification errors: {errs}"


def test_verify_solution_catches_disconnected():
    state_list = ["A", "B", "C"]
    w = np.array([50.0, 50.0, 50.0])
    edges = [(0, 1), (1, 2)]  # A-B-C
    G = nx.Graph()
    G.add_nodes_from(range(3))
    G.add_edges_from(edges)

    bad_districts = [
        {
            "id": "T_01",
            "channel": "T",
            "mass": 100.0,
            "target": 100.0,
            "deviation_pct": 0.0,
            "states": ["A", "C"],  # Disconnected!
            "shares": {"A": 1.0, "C": 1.0},
            "support_indices": [0, 2]
        },
        {
            "id": "T_02",
            "channel": "T",
            "mass": 50.0,
            "target": 100.0,
            "deviation_pct": -50.0,
            "states": ["B"],
            "shares": {"B": 1.0},
            "support_indices": [1]
        }
    ]
    ok, errs = verify_solution(bad_districts, w, state_list, G, (40.0, 120.0), {})
    assert not ok
    assert any("NOT connected" in e for e in errs)


def test_verify_solution_catches_articulation_corridor_violation():
    state_list = ["A", "B", "C"]
    w = np.array([50.0, 50.0, 50.0])
    edges = [(0, 1), (1, 2)]  # B is articulation point for {A, B, C}
    G = nx.Graph()
    G.add_nodes_from(range(3))
    G.add_edges_from(edges)

    # District has B with only 0.10 share (< 0.25 articulation bound)
    bad_districts = [
        {
            "id": "T_01",
            "channel": "T",
            "mass": 105.0,
            "target": 100.0,
            "deviation_pct": 5.0,
            "states": ["A", "B", "C"],
            "shares": {"A": 1.0, "B": 0.10, "C": 1.0},
            "support_indices": [0, 1, 2]
        },
        {
            "id": "T_02",
            "channel": "T",
            "mass": 45.0,
            "target": 100.0,
            "deviation_pct": -55.0,
            "states": ["B"],
            "shares": {"B": 0.90},
            "support_indices": [1]
        }
    ]
    ok, errs = verify_solution(bad_districts, w, state_list, G, (40.0, 120.0), {})
    assert not ok
    assert any("Articulation state B share" in e for e in errs)


if __name__ == "__main__":
    test_generate_supports_line_graph()
    test_solve_channel_model_toy()
    test_verify_solution_catches_disconnected()
    test_verify_solution_catches_articulation_corridor_violation()
    print("All solve_global_multichannel tests passed successfully!")
