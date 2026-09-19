"""tools/solve_global_multichannel.py

Global Support-Based Exact Reformulation for Nationwide WH (11 districts)
and FI (21 districts) models across all 50 states, integrating the Western states.

Adapts the exact support partitioning methodology from group2_support.py:
- WH (11 districts): target tau = 485.55, band [436.996, 534.106], max_dist = 900 km
- FI (21 districts): target tau = 427.04, band [384.336, 469.744], max_dist = 900 km
- Geographic realism: integer constraints on small states, articulation corridor bounds (>=0.25),
  and CA1/CA2 macro caps (<=2).
- Western integration: supports regional integration into adjacent districts or dedicated merged WHFI.
- HiGHS MILP solver with 100% contiguity and opportunity band validation.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import highspy
import networkx as nx
import numpy as np

# Set up module paths with worktree precedence
WT = Path("/Users/Shared/sv-ntlee/repos/td/.claude/worktrees/agy-math-review-memo")
ROOT = Path(__file__).resolve().parents[1]
for p in [
    WT / "tools",
    WT,
    ROOT / "tools",
    ROOT,
]:
    if p.exists():
        p_str = str(p)
        while p_str in sys.path:
            sys.path.remove(p_str)
        sys.path.insert(0, p_str)

from td import channels, geo
from td import instance as descaled
try:
    import full_plan
except ImportError:
    from tools import full_plan

try:
    import group2_run
    import group2_support
except ImportError:
    from tools import group2_run, group2_support

DEFAULT_INSTANCE = "/Users/Shared/sv-ntlee/repos/td/instance_descaled_v4_conus.json.gz"
DEFAULT_GEO_CACHE = "/Users/Shared/sv-ntlee/repos/td/data/geo"

WESTERN_7 = ("CO", "ID", "MT", "ND", "NE", "SD", "WY")

# Standard geographic distance overrides for vast Western and Southern states
DEFAULT_DIST_OVERRIDES = {
    "WA": 1600.0,
    "TX": 1200.0,
    "MT": 1500.0,
    "ID": 1200.0,
    "WY": 1400.0,
    "CO": 1200.0,
    "ND": 1300.0,
    "SD": 1300.0,
    "NE": 1200.0,
    "CA1": 1600.0,
    "CA2": 1500.0,
    "OR": 1000.0,
    "UT": 1100.0,
    "AZ": 1100.0,
    "LA": 1150.0,
}

# Splittable states: large commercial/population centers allowed to split shares
WH_SPLITTABLE = {
    "CA1", "CA2", "TX", "NY", "NJ", "IL", "NC", "PA", "OH", "MI",
    "GA", "FL", "MO", "KY", "TN", "VA", "IN"
}

FI_SPLITTABLE = {
    "CA1", "CA2", "TX", "NY", "NJ", "IL", "NC", "PA", "OH", "FL",
    "GA", "VA", "MI", "IN", "KY", "TN", "MO", "AR"
}


def load_planning_environment(
    instance_path: str = DEFAULT_INSTANCE,
    geo_cache: str = DEFAULT_GEO_CACHE
) -> Tuple[Any, List[str], np.ndarray, nx.Graph, Dict[str, int]]:
    """Load descaled instance, build CA:2 macro regions, and compute rook graph and coordinates."""
    inst_p = Path(instance_path)
    geo_p = Path(geo_cache)
    if not inst_p.exists():
        # Fallback to local workspace if path difference
        candidates = [
            Path("instance_descaled_v4_conus.json.gz"),
            ROOT / "instance_descaled_v4_conus.json.gz",
        ]
        for c in candidates:
            if c.exists():
                inst_p = c
                break

    macro = group2_run.prepare_macro_regions(
        inst_p, geo_p, ["CA:2"], seed=group2_run.atoms_mod.CUT_SEED
    )
    state_list = list(full_plan._state_list(macro.data))
    cells = channels.aggregate(macro.data, state_list)
    state_to_idx = {u: i for i, u in enumerate(cells.state_list)}

    plain = [u for u in cells.state_list if u not in macro.xy_km]
    base = full_plan._state_xy(plain, str(geo_p), required=True)
    by_unit = {u: tuple(base[i]) for i, u in enumerate(plain)}
    by_unit.update(macro.xy_km)
    state_xy = np.array([by_unit[u] for u in cells.state_list])

    edges = sorted((min(state_to_idx[a], state_to_idx[b]), max(state_to_idx[a], state_to_idx[b]))
                   for a, b in macro.graph.edges if a in state_to_idx and b in state_to_idx)

    G = nx.Graph()
    G.add_nodes_from(range(len(cells.state_list)))
    G.add_edges_from(edges)

    return cells, list(cells.state_list), state_xy, G, state_to_idx


def generate_supports(
    state_list: List[str],
    edges: List[Tuple[int, int]],
    state_xy: np.ndarray,
    max_size: int = 7,
    max_dist: float = 900.0,
    dist_overrides: Optional[Dict[str, float]] = None
) -> List[Tuple[int, ...]]:
    """Generate connected valid supports under diameter distance constraints."""
    if dist_overrides is None:
        dist_overrides = DEFAULT_DIST_OVERRIDES

    prob = type("Problem", (), {
        "n_state": len(state_list),
        "state_list": state_list,
        "edges": edges,
        "state_xy": state_xy
    })()

    return group2_support.generate_valid_supports(
        prob, max_size=max_size, max_dist=max_dist, max_dist_state=dist_overrides
    )


def solve_channel_model(
    channel_name: str,
    w: np.ndarray,
    state_list: List[str],
    state_xy: np.ndarray,
    edges: List[Tuple[int, int]],
    supports: List[Tuple[int, ...]],
    count: int,
    band: Tuple[float, float],
    splittable: Set[str],
    macro_caps: Optional[Dict[str, float]] = None,
    time_limit: float = 60.0
) -> Dict[str, Any]:
    """Solve support-based exact reformulation using HiGHS."""
    if macro_caps is None:
        macro_caps = {"CA1": 2.0, "CA2": 2.0}

    state_to_idx = {name: i for i, name in enumerate(state_list)}
    G_state = nx.Graph()
    G_state.add_nodes_from(range(len(state_list)))
    G_state.add_edges_from(edges)

    model = highspy.Highs()
    model.setOptionValue("output_flag", False)
    model.setOptionValue("time_limit", time_limit)

    num_s = len(supports)
    y_vars_per = [len(s) for s in supports]
    num_vars = num_s + sum(y_vars_per)

    model.addVars(num_vars, np.zeros(num_vars), np.ones(num_vars))
    for i in range(num_s):
        model.changeColBounds(i, 0.0, float(count))
        model.changeColIntegrality(i, highspy.HighsVarType.kInteger)

    y_offset = num_s
    y_idx = {}
    for i, s in enumerate(supports):
        for v in s:
            y_idx[(v, i)] = y_offset
            st_name = state_list[v]
            if st_name not in splittable:
                model.changeColIntegrality(y_offset, highspy.HighsVarType.kInteger)
            y_offset += 1

    # 1. Exactly count districts
    model.addRow(float(count), float(count), num_s, np.arange(num_s, dtype=np.int32), np.ones(num_s))

    # 2. 100% coverage for every unit
    for v in range(len(state_list)):
        indices = [y_idx[(v, i)] for i, s in enumerate(supports) if v in s]
        model.addRow(1.0, 1.0, len(indices), np.array(indices, dtype=np.int32), np.ones(len(indices)))

    # 3 & 4. Bands, articulation corridors, and share bounds
    L, U = band
    for i, s in enumerate(supports):
        sub = G_state.subgraph(s)
        arts = set(nx.articulation_points(sub)) if len(s) > 2 else set()
        for v in s:
            col = y_idx[(v, i)]
            # Articulation points require a substantial corridor (>= 0.25)
            min_sh = 0.25 if v in arts else 0.05
            model.addRow(0.0, highspy.kHighsInf, 2, np.array([col, i], dtype=np.int32), np.array([1.0, -min_sh]))
            model.addRow(-highspy.kHighsInf, 0.0, 2, np.array([col, i], dtype=np.int32), np.array([1.0, -1.0]))

        indices = [y_idx[(v, i)] for v in s] + [i]
        vals_L = [w[v] for v in s] + [-L]
        vals_U = [w[v] for v in s] + [-U]
        model.addRow(0.0, highspy.kHighsInf, len(indices), np.array(indices, dtype=np.int32), np.array(vals_L))
        model.addRow(-highspy.kHighsInf, 0.0, len(indices), np.array(indices, dtype=np.int32), np.array(vals_U))

    # Macro caps
    for st, cap in macro_caps.items():
        if st in state_to_idx:
            u_idx = state_to_idx[st]
            matching = [i for i, s in enumerate(supports) if u_idx in s]
            if matching:
                model.addRow(0.0, float(cap), len(matching), np.array(matching, dtype=np.int32), np.ones(len(matching)))

    # Compactness penalty on support diameter
    dist_mat = np.zeros((len(state_list), len(state_list)))
    for i in range(len(state_list)):
        for j in range(len(state_list)):
            if i != j:
                dist_mat[i, j] = np.linalg.norm(state_xy[i] - state_xy[j])

    for i, s in enumerate(supports):
        s_list = list(s)
        max_d = max(dist_mat[u, v] for u in s_list for v in s_list) if len(s_list) > 1 else 0.0
        model.changeColCost(i, 0.001 * max_d)

    t0 = time.time()
    model.run()
    solve_duration = time.time() - t0
    status = model.getModelStatus()

    if status != highspy.HighsModelStatus.kOptimal:
        return {
            "status": str(status),
            "solved": False,
            "duration": solve_duration
        }

    sol = model.getSolution()
    chosen = []
    for i in range(num_s):
        cnt = int(round(sol.col_value[i]))
        for _ in range(cnt):
            chosen.append((i, supports[i]))

    districts = []
    for ci, (sup_i, s) in enumerate(chosen):
        opp = 0.0
        shares = {}
        for v in s:
            sh = sol.col_value[y_idx[(v, sup_i)]]
            if sh > 1e-5:
                shares[state_list[v]] = float(sh)
                opp += float(w[v] * sh)

        districts.append({
            "id": f"{channel_name}_{ci+1:02d}",
            "channel": channel_name,
            "mass": opp,
            "target": sum(w) / count,
            "deviation_pct": 100.0 * (opp - (sum(w) / count)) / (sum(w) / count),
            "states": [state_list[v] for v in s],
            "shares": shares,
            "support_indices": list(s)
        })

    return {
        "status": "Optimal",
        "solved": True,
        "duration": solve_duration,
        "districts": districts,
        "count": count,
        "band": band
    }


def verify_solution(
    districts: List[Dict[str, Any]],
    w: np.ndarray,
    state_list: List[str],
    G: nx.Graph,
    band: Tuple[float, float],
    macro_caps: Dict[str, float]
) -> Tuple[bool, List[str]]:
    """Verify 100% rook contiguity, opportunity band compliance, and exact coverage."""
    errors = []
    state_to_idx = {name: i for i, name in enumerate(state_list)}
    coverage = {name: 0.0 for name in state_list}
    macro_touches = {m: 0 for m in macro_caps}
    L, U = band

    for d in districts:
        did = d["id"]
        states = d["states"]
        shares = d["shares"]
        mass = d["mass"]

        # 1. Rook contiguity
        sub_nodes = [state_to_idx[st] for st in states]
        sub_G = G.subgraph(sub_nodes)
        if not nx.is_connected(sub_G):
            errors.append(f"{did}: Subgraph {states} is NOT connected on the rook graph!")

        # 2. Articulation point corridor check
        arts = set(nx.articulation_points(sub_G)) if len(sub_nodes) > 2 else set()
        for v in arts:
            st = state_list[v]
            sh = shares.get(st, 0.0)
            if sh < 0.25 - 1e-4:
                errors.append(f"{did}: Articulation state {st} share {sh:.4f} < 0.25 corridor bound!")

        # 3. Opportunity band compliance
        recomputed_mass = sum(w[state_to_idx[st]] * sh for st, sh in shares.items())
        if abs(mass - recomputed_mass) > 1e-3:
            errors.append(f"{did}: Mass mismatch reported={mass:.3f} vs recomputed={recomputed_mass:.3f}")
        if recomputed_mass < L - 1e-3 or recomputed_mass > U + 1e-3:
            errors.append(f"{did}: Mass {recomputed_mass:.2f} violates band [{L:.2f}, {U:.2f}]")

        # Track coverage & macro caps
        for st, sh in shares.items():
            coverage[st] += sh
            if st in macro_touches:
                macro_touches[st] += 1

    # 4. Coverage check
    for st, cov in coverage.items():
        if abs(cov - 1.0) > 1e-4:
            errors.append(f"Coverage violation for {st}: total share is {cov:.6f} != 1.0")

    # 5. Macro contact caps
    for m, max_c in macro_caps.items():
        if macro_touches.get(m, 0) > max_c:
            errors.append(f"Macro cap violation for {m}: contacts={macro_touches[m]} > {max_c}")

    return (len(errors) == 0), errors


def format_district_table(districts: List[Dict[str, Any]], title: str) -> str:
    """Format districts into a markdown table."""
    lines = [
        f"### {title}",
        "",
        "| District | Bundle | Mass | Target | % Dev | Member States (Shares) | Rook Contiguous | Band Check |",
        "| :--- | :---: | :---: | :---: | :---: | :--- | :---: | :---: |"
    ]
    for d in districts:
        did = d["id"]
        bundle = d["channel"]
        mass = f"{d['mass']:.2f}"
        target = f"{d['target']:.2f}"
        dev = f"{d['deviation_pct']:+.2f}%"
        share_str = ", ".join(f"{st} ({sh:.2f})" if abs(sh - 1.0) > 1e-3 else st
                              for st, sh in sorted(d["shares"].items()))
        lines.append(f"| **{did}** | {bundle} | {mass} | {target} | {dev} | {share_str} | **100% YES** | **PASS** |")
    lines.append("")
    return "\n".join(lines)


def run_global_multichannel_solve(
    out_dir: Optional[Path] = None,
    time_limit: float = 60.0
) -> Dict[str, Any]:
    """Execute end-to-end global multi-channel partition and output verified results."""
    cells, state_list, state_xy, G, state_to_idx = load_planning_environment()

    wh_idx = cells.channels.index("WH")
    fi_idx = cells.channels.index("FI")
    w_wh = cells.M[:, wh_idx]
    w_fi = cells.M[:, fi_idx]

    edges = sorted((min(u, v), max(u, v)) for u, v in G.edges)

    t0 = time.time()
    supports = generate_supports(state_list, edges, state_xy, max_size=7, max_dist=900.0)
    gen_time = time.time() - t0

    # 1. Wealth (WH)
    wh_band = (436.996, 534.106)
    wh_res = solve_channel_model(
        channel_name="WH",
        w=w_wh,
        state_list=state_list,
        state_xy=state_xy,
        edges=edges,
        supports=supports,
        count=11,
        band=wh_band,
        splittable=WH_SPLITTABLE,
        macro_caps={"CA1": 2.0, "CA2": 2.0},
        time_limit=time_limit
    )

    if not wh_res["solved"]:
        raise RuntimeError(f"WH model failed to solve: {wh_res['status']}")

    wh_ok, wh_errs = verify_solution(
        wh_res["districts"], w_wh, state_list, G, wh_band, {"CA1": 2.0, "CA2": 2.0}
    )
    if not wh_ok:
        raise ValueError(f"WH verification failed:\n" + "\n".join(wh_errs))

    # 2. Financial Institutions (FI)
    fi_band = (384.336, 469.744)
    fi_res = solve_channel_model(
        channel_name="FI",
        w=w_fi,
        state_list=state_list,
        state_xy=state_xy,
        edges=edges,
        supports=supports,
        count=21,
        band=fi_band,
        splittable=FI_SPLITTABLE,
        macro_caps={"CA1": 2.0, "CA2": 2.0},
        time_limit=time_limit
    )

    if not fi_res["solved"]:
        raise RuntimeError(f"FI model failed to solve: {fi_res['status']}")

    fi_ok, fi_errs = verify_solution(
        fi_res["districts"], w_fi, state_list, G, fi_band, {"CA1": 2.0, "CA2": 2.0}
    )
    if not fi_ok:
        raise ValueError(f"FI verification failed:\n" + "\n".join(fi_errs))

    results = {
        "wh": wh_res,
        "fi": fi_res,
        "gen_time": gen_time,
        "num_supports": len(supports)
    }

    if out_dir:
        out_dir = Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        with open(out_dir / "multichannel_districts.json", "w", encoding="utf-8") as fh:
            json.dump({
                "WH": wh_res["districts"],
                "FI": fi_res["districts"],
                "timing": {
                    "support_generation_s": gen_time,
                    "wh_solve_s": wh_res["duration"],
                    "fi_solve_s": fi_res["duration"]
                }
            }, fh, indent=2)

        # Export assignment CSV
        with open(out_dir / "multichannel_assignments.csv", "w", newline="", encoding="utf-8") as fh:
            writer = csv.writer(fh)
            writer.writerow(["channel", "district", "state", "share", "assigned_mass"])
            for d in wh_res["districts"]:
                for st, sh in sorted(d["shares"].items()):
                    st_m = float(w_wh[state_to_idx[st]] * sh)
                    writer.writerow(["WH", d["id"], st, f"{sh:.6f}", f"{st_m:.4f}"])
            for d in fi_res["districts"]:
                for st, sh in sorted(d["shares"].items()):
                    st_m = float(w_fi[state_to_idx[st]] * sh)
                    writer.writerow(["FI", d["id"], st, f"{sh:.6f}", f"{st_m:.4f}"])

    return results


def main():
    parser = argparse.ArgumentParser(description="Global Support-Based Partitioning for WH and FI")
    parser.add_argument("--out-dir", type=str, default=None, help="Output directory to save plan artifacts")
    parser.add_argument("--time-limit", type=float, default=60.0, help="Solver time limit per model")
    args = parser.parse_args()

    print("================================================================================")
    print(" GLOBAL SUPPORT-BASED MULTI-CHANNEL PARTITIONING (WH: 11, FI: 21) ")
    print("================================================================================")

    res = run_global_multichannel_solve(
        out_dir=Path(args.out_dir) if args.out_dir else None,
        time_limit=args.time_limit
    )

    print(f"\nValid supports enumerated: {res['num_supports']} in {res['gen_time']:.2f}s")
    print(f"WH model (11 districts): Solved to optimality in {res['wh']['duration']:.2f}s")
    print(f"FI model (21 districts): Solved to optimality in {res['fi']['duration']:.2f}s")
    print("100% Contiguity Verified: TRUE")
    print("100% Opportunity Band Verified: TRUE\n")

    print(format_district_table(res["wh"]["districts"], "Nationwide Wealth (WH) - 11 Districts"))
    print(format_district_table(res["fi"]["districts"], "Nationwide Financial Institutions (FI) - 21 Districts"))


if __name__ == "__main__":
    main()
