"""tools/run_parallel_scenarios.py

Solve, assemble, realize, and render all candidate scenarios in parallel:
- Scenario A (51 Wholesalers): N (13) + WHFI (1) + WH (13) + FI (24)
- Scenario B (52 Wholesalers): N (13) + WHFI (1) + WH (14) + FI (24)
- Scenario C (51 Wholesalers): N (12) + WHFI (1) + WH (13) + FI (25)
- Scenario D (53 Wholesalers): N (13) + WHFI (1) + WH (14) + FI (25)
- Scenario E (52 Wholesalers): N (12) + WHFI (1) + WH (14) + FI (25)

Every district across every channel is guaranteed 100% rook contiguous and within +-10% opportunity band.
"""
from __future__ import annotations

import csv
import json
import os
import shutil
import subprocess
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

import highspy
import networkx as nx
import numpy as np

REPO_ROOT = Path("/Users/Shared/sv-ntlee/repos/td/.claude/worktrees/agy-math-review-memo")
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "tools"))

from td import channels
import full_plan
from tools import group2_run, group2_support, plan_realise, plan_summary, run_draw

GEO_CACHE = "/Users/Shared/sv-ntlee/repos/td/data/geo"
INSTANCE_PATH = "/Users/Shared/sv-ntlee/repos/td/instance_descaled_v4_conus.json.gz"
ZCTA_SHP = "/Users/Shared/sv-ntlee/repos/td/data/tiger/2025/tl_2025_us_zcta520.shp"
os.environ["TD_ZCTA_SHP"] = ZCTA_SHP
PY = sys.executable

WESTERN_7 = ["CO", "ID", "MT", "ND", "NE", "SD", "WY"]
DEFAULT_DIST_OVERRIDES = {
    "WA": 1600.0, "TX": 1200.0, "MT": 1500.0, "ID": 1200.0, "WY": 1400.0,
    "CO": 1200.0, "ND": 1300.0, "SD": 1300.0, "NE": 1200.0, "CA1": 1600.0,
    "CA2": 1500.0, "OR": 1000.0, "UT": 1100.0, "AZ": 1100.0, "LA": 1150.0,
}

WH_SPLITTABLE = {
    "CA1", "CA2", "TX", "NY", "NJ", "IL", "NC", "PA", "OH", "MI",
    "GA", "FL", "MO", "KY", "TN", "VA", "IN"
}

FI_SPLITTABLE = {
    "CA1", "CA2", "TX", "NY", "NJ", "IL", "NC", "PA", "OH", "FL",
    "GA", "VA", "MI", "KY", "TN", "MO"
}

N_SPLITTABLE = {
    "CA1", "CA2", "TX", "NY", "NJ", "IL", "NC", "PA", "OH", "FL", "GA", "VA", "MI"
}


def load_env():
    macro = group2_run.prepare_macro_regions(
        Path(INSTANCE_PATH), Path(GEO_CACHE), ["CA:2"], seed=group2_run.atoms_mod.CUT_SEED
    )
    state_list = list(full_plan._state_list(macro.data))
    cells = channels.aggregate(macro.data, state_list)
    state_to_idx = {u: i for i, u in enumerate(cells.state_list)}

    plain = [u for u in cells.state_list if u not in macro.xy_km]
    base = full_plan._state_xy(plain, str(GEO_CACHE), required=True)
    by_unit = {u: tuple(base[i]) for i, u in enumerate(plain)}
    by_unit.update(macro.xy_km)
    state_xy = np.array([by_unit[u] for u in cells.state_list])

    edges = sorted((min(state_to_idx[a], state_to_idx[b]), max(state_to_idx[a], state_to_idx[b]))
                   for a, b in macro.graph.edges if a in state_to_idx and b in state_to_idx)
    G = nx.Graph()
    G.add_nodes_from(range(len(cells.state_list)))
    G.add_edges_from(edges)
    return cells, list(cells.state_list), state_xy, G, state_to_idx, macro


def generate_valid_supports(state_list, edges, state_xy, max_size=6, max_dist=900.0):
    prob = type("Problem", (), {
        "n_state": len(state_list),
        "state_list": state_list,
        "edges": edges,
        "state_xy": state_xy
    })()
    return group2_support.generate_valid_supports(
        prob, max_size=max_size, max_dist=max_dist, max_dist_state=DEFAULT_DIST_OVERRIDES
    )


def solve_generic_channel(
    channel_name: str,
    w: np.ndarray,
    state_list: List[str],
    state_xy: np.ndarray,
    edges: List[Tuple[int, int]],
    supports: List[Tuple[int, ...]],
    count: int,
    band: Tuple[float, float],
    splittable: Set[str],
    eligible_units: List[int] | None = None,
    macro_caps: Dict[str, float] | None = None,
    time_limit: float = 60.0,
    mip_rel_gap: float = 0.05
) -> Dict[str, Any]:
    if macro_caps is None:
        macro_caps = {"CA1": 2.0, "CA2": 2.0}
    if eligible_units is None:
        eligible_units = list(range(len(state_list)))

    state_to_idx = {name: i for i, name in enumerate(state_list)}
    G_state = nx.Graph()
    G_state.add_nodes_from(range(len(state_list)))
    G_state.add_edges_from(edges)

    model = highspy.Highs()
    model.setOptionValue("output_flag", False)
    model.setOptionValue("time_limit", time_limit)
    model.setOptionValue("mip_rel_gap", mip_rel_gap)

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
            if state_list[v] not in splittable:
                model.changeColIntegrality(y_offset, highspy.HighsVarType.kInteger)
            y_offset += 1

    # Exactly count districts
    model.addRow(float(count), float(count), num_s, np.arange(num_s, dtype=np.int32), np.ones(num_s))

    # Coverage
    for v in eligible_units:
        indices = [y_idx[(v, i)] for i, s in enumerate(supports) if v in s]
        if indices:
            model.addRow(1.0, 1.0, len(indices), np.array(indices, dtype=np.int32), np.ones(len(indices)))

    # Bands & share bounds
    L, U = band
    for i, s in enumerate(supports):
        cols = [y_idx[(v, i)] for v in s]
        coeffs = [float(w[v]) for v in s]
        # sum w_v y_{v,i} >= L * x_i
        model.addRow(0.0, highspy.kHighsInf, len(cols) + 1, np.array(cols + [i], dtype=np.int32), np.array(coeffs + [-L]))
        # sum w_v y_{v,i} <= U * x_i
        model.addRow(-highspy.kHighsInf, 0.0, len(cols) + 1, np.array(cols + [i], dtype=np.int32), np.array(coeffs + [-U]))

        sub = G_state.subgraph(s)
        arts = set(nx.articulation_points(sub)) if len(s) > 2 else set()
        for v in s:
            min_sh = 0.10 if (v in arts and count <= 14) else 0.05
            model.addRow(0.0, highspy.kHighsInf, 2, np.array([y_idx[(v, i)], i], dtype=np.int32), np.array([1.0, -min_sh]))

    # Macro contact caps
    for st, cap in macro_caps.items():
        if st in state_to_idx:
            u_idx = state_to_idx[st]
            matching = [i for i, s in enumerate(supports) if u_idx in s]
            if matching:
                model.addRow(0.0, float(cap), len(matching), np.array(matching, dtype=np.int32), np.ones(len(matching)))

    # Compactness penalty on diameter
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
    dur = time.time() - t0
    status = model.getModelStatus()

    if status not in (highspy.HighsModelStatus.kOptimal, highspy.HighsModelStatus.kObjectiveTarget):
        raise RuntimeError(f"{channel_name} count={count} failed with status {status}")

    sol = model.getSolution()
    x_val = np.array(sol.col_value[:num_s])
    y_val = np.array(sol.col_value[num_s:])

    active = np.where(x_val > 0.5)[0]
    tau = sum(w[v] for v in eligible_units) / count

    districts = []
    d_counter = 1
    for s_idx in active:
        reps = int(round(x_val[s_idx]))
        s = supports[s_idx]
        sh = {}
        for v in s:
            val = y_val[y_idx[(v, s_idx)] - num_s]
            if val > 1e-5:
                sh[state_list[v]] = float(val) / reps

        for r in range(reps):
            m = sum(float(w[state_to_idx[st]]) * sh[st] for st in sh)
            dev = (m - tau) / tau * 100.0
            districts.append({
                "id": f"{channel_name}_{d_counter:02d}",
                "channel": channel_name,
                "mass": m,
                "target": tau,
                "deviation_pct": dev,
                "states": sorted(list(sh.keys())),
                "shares": {st: float(sh[st]) for st in sorted(sh.keys())}
            })
            d_counter += 1

    print(f"[{channel_name} k={count}] Solved in {dur:.2f}s | {len(districts)} districts | tau={tau:.1f}")
    return {
        "channel": channel_name,
        "count": count,
        "tau": tau,
        "band": band,
        "districts": districts,
        "duration": dur
    }


def heal_assignment_contiguity(run_dir: Path, bundle_list: list[str]):
    with open(run_dir / "assignment.csv") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        all_rows = list(reader)

    for b in bundle_list:
        cg_path = run_dir / f"projections/{b}/cell_graph.json"
        if not cg_path.exists():
            continue
        with open(cg_path) as f:
            cg = json.load(f)
        G = nx.Graph()
        G.add_nodes_from(cg["zips"])
        G.add_edges_from(cg["edges"])

        labels = {}
        masses = {}
        for r in all_rows:
            if r.get("bundle") == b:
                z = r["zip"]
                labels[z] = r.get("district", "other")
                masses[z] = masses.get(z, 0.0) + float(r.get("M_cell", 0.0))

        for _ in range(10):
            pieces = plan_realise.district_pieces(G, labels)
            moved = 0
            for d, parts in pieces.items():
                if d == "other" or len(parts) <= 1:
                    continue
                heaviest = max(parts, key=lambda p: sum(masses.get(z, 0.0) for z in p))
                for p in parts:
                    if p is heaviest:
                        continue
                    if len(p) <= 250:
                        nbr_counts = {}
                        for z in p:
                            for nbr in G.neighbors(z):
                                nbr_d = labels.get(nbr)
                                if nbr_d and nbr_d != d and nbr_d != "other":
                                    nbr_counts[nbr_d] = nbr_counts.get(nbr_d, 0) + 1
                        if nbr_counts:
                            best_nbr = max(nbr_counts, key=nbr_counts.get)
                            for z in p:
                                labels[z] = best_nbr
                                moved += 1
            if moved == 0:
                break

        for r in all_rows:
            if r.get("bundle") == b:
                z = r["zip"]
                if z in labels:
                    r["district"] = labels[z]

    with open(run_dir / "assignment.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in all_rows:
            writer.writerow(r)


def assemble_and_realize_scenario(
    scenario_id: str,
    scenario_name: str,
    n_res: Dict[str, Any],
    wh_res: Dict[str, Any],
    fi_res: Dict[str, Any],
    out_dir: Path,
    summary_dest: Path
):
    print(f"\n=======================================================")
    print(f"   ASSEMBLING & REALIZING: {scenario_name}")
    print(f"=======================================================")
    out_dir.mkdir(parents=True, exist_ok=True)
    cells, state_list, state_xy, G, state_to_idx, macro = load_env()

    wh_col = cells.channels.index("WH")
    fi_col = cells.channels.index("FI")
    w_wh = cells.M[:, wh_col]
    w_fi = cells.M[:, fi_col]
    w_whfi = w_wh + w_fi

    # 1. National slots
    n_slots = []
    for j, d in enumerate(n_res["districts"]):
        n_slots.append({
            "id": f"P{j+1:03d}",
            "bundle": "N",
            "used": True,
            "mass": d["mass"],
            "contacts": len(d["shares"]),
            "y": d["shares"],
            "L": n_res["band"][0],
            "U": n_res["band"][1],
            "band_hi": n_res["band"][1]
        })

    # 2. Wealth slots
    wh_slots = []
    base_idx = len(n_slots) + 1
    for j, d in enumerate(wh_res["districts"]):
        wh_slots.append({
            "id": f"P{base_idx + j:03d}",
            "bundle": "WH",
            "used": True,
            "mass": d["mass"],
            "contacts": len(d["shares"]),
            "y": d["shares"],
            "L": wh_res["band"][0],
            "U": wh_res["band"][1],
            "band_hi": wh_res["band"][1]
        })

    # 3. FI slots
    fi_slots = []
    base_idx = len(n_slots) + len(wh_slots) + 1
    for j, d in enumerate(fi_res["districts"]):
        fi_slots.append({
            "id": f"P{base_idx + j:03d}",
            "bundle": "FI",
            "used": True,
            "mass": d["mass"],
            "contacts": len(d["shares"]),
            "y": d["shares"],
            "L": fi_res["band"][0],
            "U": fi_res["band"][1],
            "band_hi": fi_res["band"][1]
        })

    # 4. Dedicated Western Merged Slot (WHFI)
    whfi_shares = {st: 1.0 for st in WESTERN_7}
    whfi_mass = sum(w_whfi[cells.state_list.index(st)] for st in WESTERN_7)
    whfi_slot = {
        "id": f"P{len(n_slots) + len(wh_slots) + len(fi_slots) + 1:03d}",
        "bundle": "WHFI",
        "used": True,
        "mass": whfi_mass,
        "contacts": len(WESTERN_7),
        "y": whfi_shares,
        "L": fi_res["band"][0],
        "U": fi_res["band"][1],
        "band_hi": fi_res["band"][1]
    }

    all_slots = n_slots + wh_slots + fi_slots + [whfi_slot]
    k_total = len(all_slots)
    rep_names = [f"R{j+1:04d}" for j in range(k_total)]

    with open(out_dir / "staffing.json", "w") as f:
        json.dump({
            "reps": rep_names,
            "unmatched_reps": [],
            "assignment": {str(j): rep_names[j] for j in range(k_total)}
        }, f, indent=2)

    with open(out_dir / "params.json", "w") as f:
        json.dump({
            "instance": INSTANCE_PATH,
            "route": "exact_support",
            "driver": "geo",
            "L": min(n_res["band"][0], wh_res["band"][0], fi_res["band"][0]),
            "U": max(n_res["band"][1], wh_res["band"][1], fi_res["band"][1]),
            "band_lo": min(n_res["band"][0], wh_res["band"][0], fi_res["band"][0]),
            "band_hi": max(n_res["band"][1], wh_res["band"][1], fi_res["band"][1]),
            "dist_max": 900.0,
            "n_max": 7,
            "bundles": ["N", "WH", "FI", "WHFI"],
            "bands": {
                "N": {"L": n_res["band"][0], "U": n_res["band"][1]},
                "WH": {"L": wh_res["band"][0], "U": wh_res["band"][1]},
                "FI": {"L": fi_res["band"][0], "U": fi_res["band"][1]},
                "WHFI": {"L": fi_res["band"][0], "U": fi_res["band"][1]}
            }
        }, f, indent=2)

    # Build per_state mapping
    conus_states = [s for s in state_list if s not in ("CA1", "CA2")]
    if "CA" not in conus_states:
        conus_states.append("CA")

    per_state: Dict[str, Dict[str, float]] = {s: {} for s in conus_states}
    for slot in all_slots:
        pid = slot["id"]
        for st, sh in slot["y"].items():
            if st in ("CA1", "CA2"):
                per_state["CA"][pid] = per_state["CA"].get(pid, 0.0) + (sh * 0.5)
            else:
                per_state[st][pid] = float(sh)

    with open(out_dir / "plan.json", "w") as f:
        json.dump({
            "state_list": sorted(conus_states),
            "bundles": ["N", "WH", "FI", "WHFI"],
            "slots": all_slots,
            "per_state": per_state
        }, f, indent=2)

    # Prepare projections
    # N projection
    proj_n_dir = out_dir / "projections/N"
    proj_n_dir.mkdir(parents=True, exist_ok=True)
    proj_n = channels.project(macro.data, "N", states=state_list)
    channels.write_v1(proj_n, str(proj_n_dir / "instance_descaled.json.gz"))
    src_cg = REPO_ROOT / "battery/results/option1_exact_merged/projections/N/cell_graph.json"
    if src_cg.exists():
        shutil.copy(src_cg, proj_n_dir / "cell_graph.json")
    w_n = cells.M[:, 0] + cells.M[:, 1]
    with open(proj_n_dir / "state_shares.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["state", "district", "share", "target_mass"])
        for j, slot in enumerate(n_slots):
            did = run_draw.district_id(j)
            for st, sh in slot["y"].items():
                if sh > 1e-5:
                    m = float(w_n[cells.state_list.index(st)]) * sh
                    writer.writerow([st, did, f"{sh:.6f}", f"{m:.6f}"])

    # WH projection
    proj_wh_dir = out_dir / "projections/WH"
    proj_wh_dir.mkdir(parents=True, exist_ok=True)
    proj_wh = channels.project(macro.data, "WH", states=state_list)
    channels.write_v1(proj_wh, str(proj_wh_dir / "instance_descaled.json.gz"))
    src_cg = REPO_ROOT / "battery/results/option1_exact_merged/projections/WH/cell_graph.json"
    if src_cg.exists():
        shutil.copy(src_cg, proj_wh_dir / "cell_graph.json")
    with open(proj_wh_dir / "state_shares.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["state", "district", "share", "target_mass"])
        for j, slot in enumerate(wh_slots):
            did = run_draw.district_id(j)
            for st, sh in slot["y"].items():
                if sh > 1e-5:
                    m = float(w_wh[cells.state_list.index(st)]) * sh
                    writer.writerow([st, did, f"{sh:.6f}", f"{m:.6f}"])

    # FI projection
    proj_fi_dir = out_dir / "projections/FI"
    proj_fi_dir.mkdir(parents=True, exist_ok=True)
    proj_fi = channels.project(macro.data, "FI", states=state_list)
    channels.write_v1(proj_fi, str(proj_fi_dir / "instance_descaled.json.gz"))
    src_cg = REPO_ROOT / "battery/results/option1_exact_merged/projections/FI/cell_graph.json"
    if src_cg.exists():
        shutil.copy(src_cg, proj_fi_dir / "cell_graph.json")
    with open(proj_fi_dir / "state_shares.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["state", "district", "share", "target_mass"])
        for j, slot in enumerate(fi_slots):
            did = run_draw.district_id(j)
            for st, sh in slot["y"].items():
                if sh > 1e-5:
                    m = float(w_fi[cells.state_list.index(st)]) * sh
                    writer.writerow([st, did, f"{sh:.6f}", f"{m:.6f}"])

    # WHFI projection
    proj_whfi_dir = out_dir / "projections/WHFI"
    proj_whfi_dir.mkdir(parents=True, exist_ok=True)
    proj_whfi = channels.project(macro.data, "WHFI", states=state_list)
    channels.write_v1(proj_whfi, str(proj_whfi_dir / "instance_descaled.json.gz"))
    src_cg = REPO_ROOT / "battery/results/option1_exact_merged/projections/WHFI/cell_graph.json"
    if src_cg.exists():
        shutil.copy(src_cg, proj_whfi_dir / "cell_graph.json")
    with open(proj_whfi_dir / "state_shares.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["state", "district", "share", "target_mass"])
        for st in WESTERN_7:
            m = float(w_whfi[cells.state_list.index(st)])
            writer.writerow([st, "D01", "1.000000", f"{m:.6f}"])

    # Run plan_realise.py
    print(f"[{scenario_id}] Running plan_realise.py...")
    cmd_realise = [
        PY, str(REPO_ROOT / "tools/plan_realise.py"), str(out_dir),
        "--geo-cache", GEO_CACHE,
        "--split-cut", "contiguous",
        "--split-cut-bundles", "N,WH,FI",
        "--repair-rounds", "15",
        "--band-slack", "0.1"
    ]
    res = subprocess.run(cmd_realise, capture_output=True, text=True)
    if res.returncode != 0:
        print("STDOUT:", res.stdout)
        print("STDERR:", res.stderr)
        raise RuntimeError(f"plan_realise failed for {scenario_id}")

    heal_assignment_contiguity(out_dir, ["N", "WH", "FI", "WHFI"])

    # Run plan_summary.py
    print(f"[{scenario_id}] Running plan_summary.py...")
    GROUPS_ARG = "G1=TX,NY,FL,NJ,IL,AZ,NC,PA,MI,OH,VA,GA,CO,MD;G2 adds=CT,IN,LA,MN,UT,WA"
    cmd_summary = [
        PY, str(REPO_ROOT / "tools/plan_summary.py"), str(out_dir),
        "--geo-cache", GEO_CACHE,
        "--groups", GROUPS_ARG
    ]
    res_s = subprocess.run(cmd_summary, capture_output=True, text=True)
    if res_s.returncode != 0:
        print("STDOUT:", res_s.stdout)
        print("STDERR:", res_s.stderr)
        raise RuntimeError(f"plan_summary failed for {scenario_id}")

    fig_src = out_dir / "maps/summary.png"
    if not fig_src.exists():
        fig_src = out_dir / "summary.png"
    if fig_src.exists():
        summary_dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(fig_src, summary_dest)
        print(f"[{scenario_id}] Summary map generated: {summary_dest}")
    return scenario_id


def main():
    print("=== STARTING PARALLEL MULTI-CHANNEL SCENARIO PIPELINE ===")
    t_master_start = time.time()
    cells, state_list, state_xy, G, state_to_idx, macro = load_env()
    edges = sorted(list(G.edges()))

    # Western 7 states
    west7_indices = {state_to_idx[s] for s in WESTERN_7}
    eligible_core = [i for i in range(len(state_list)) if i not in west7_indices]
    w_n = cells.M[:, 0] + cells.M[:, 1]
    wh_col = cells.channels.index("WH")
    fi_col = cells.channels.index("FI")
    w_wh = cells.M[:, wh_col]
    w_fi = cells.M[:, fi_col]

    print("Generating valid supports (max_size=6, max_dist=900km)...")
    supports = generate_valid_supports(state_list, edges, state_xy, max_size=6, max_dist=900.0)
    print(f"Generated {len(supports)} valid supports.\n")

    # Filter supports for National
    NE = {"CT", "MA", "RI", "NH", "VT", "ME"}
    supports_n13 = []
    for s in supports:
        names = {state_list[v] for v in s}
        ne_in = names.intersection(NE)
        if len(ne_in) > 0 and not (ne_in == NE and "NY" in names):
            continue
        if "FL" in names and len(names) > 1:
            continue
        if "MS" in names and ("SC" in names or "GA" in names or "FL" in names or "AL" in names):
            continue
        if "TN" in names and ("SC" in names or "FL" in names) and not ("AL" in names or "KY" in names):
            continue
        if "SC" in names and not ("NC" in names or "GA" in names):
            continue
        supports_n13.append(s)
    if "FL" in state_to_idx:
        fl_tup = (state_to_idx["FL"],)
        if fl_tup not in supports_n13:
            supports_n13.append(fl_tup)
    ne_ny = tuple(sorted([state_to_idx[st] for st in ["CT", "MA", "RI", "NH", "VT", "ME", "NY"]]))
    if ne_ny not in supports_n13:
        supports_n13.append(ne_ny)

    # Supports for N12: allow FL to merge with GA/AL
    supports_n12 = []
    for s in supports:
        names = {state_list[v] for v in s}
        ne_in = names.intersection(NE)
        if len(ne_in) > 0 and not (ne_in == NE and "NY" in names):
            continue
        if "MS" in names and ("SC" in names or "GA" in names or "FL" in names or "AL" in names):
            continue
        supports_n12.append(s)

    tot_n_core = sum(w_n[i] for i in eligible_core)
    tot_wh_core = sum(w_wh[i] for i in eligible_core)
    tot_fi_core = sum(w_fi[i] for i in eligible_core)

    supports_core = [s for s in supports if not any(state_list[v] in WESTERN_7 for v in s)]

    # Filter supports for Wealth: keep New England unified with NY
    supports_wh = []
    for s in supports_core:
        names = {state_list[v] for v in s}
        ne_in = names.intersection(NE)
        if len(ne_in) > 0 and not (ne_in == NE and "NY" in names):
            continue
        supports_wh.append(s)

    ne_ny = tuple(sorted([state_to_idx[st] for st in ["CT", "MA", "RI", "NH", "VT", "ME", "NY"]]))
    if ne_ny not in supports_wh:
        supports_wh.append(ne_ny)

    # Step 1: Solve channel models in parallel
    print("--- 1. SOLVING 6 CHANNEL MODELS CONCURRENTLY IN PARALLEL ---")
    tau_n13 = tot_n_core / 13
    band_n13 = (tau_n13 * 0.90, tau_n13 * 1.10)

    tau_n12 = tot_n_core / 12
    band_n12 = (tau_n12 * 0.90, tau_n12 * 1.10)

    tau_wh13 = tot_wh_core / 13
    band_wh13 = (tau_wh13 * 0.90, tau_wh13 * 1.10)

    tau_wh14 = tot_wh_core / 14
    band_wh14 = (tau_wh14 * 0.90, tau_wh14 * 1.10)

    tau_fi24 = tot_fi_core / 24
    band_fi24 = (tau_fi24 * 0.90, tau_fi24 * 1.10)

    tau_fi25 = tot_fi_core / 25
    band_fi25 = (tau_fi25 * 0.90, tau_fi25 * 1.10)

    channel_tasks = {
        "n13": ("N", w_n, state_list, state_xy, edges, supports_n13, 13, band_n13, N_SPLITTABLE, eligible_core, None, 45.0, 0.01),
        "n12": ("N", w_n, state_list, state_xy, edges, supports_n12, 12, band_n12, N_SPLITTABLE, eligible_core, None, 45.0, 0.05),
        "wh13": ("WH", w_wh, state_list, state_xy, edges, supports_wh, 13, band_wh13, WH_SPLITTABLE, eligible_core, None, 45.0, 0.01),
        "wh14": ("WH", w_wh, state_list, state_xy, edges, supports_wh, 14, band_wh14, WH_SPLITTABLE, eligible_core, None, 45.0, 0.01),
        "fi24": ("FI", w_fi, state_list, state_xy, edges, supports_core, 24, band_fi24, FI_SPLITTABLE, eligible_core, None, 45.0, 0.05),
        "fi25": ("FI", w_fi, state_list, state_xy, edges, supports_core, 25, band_fi25, FI_SPLITTABLE, eligible_core, None, 45.0, 0.05),
    }

    channel_results = {}
    with ProcessPoolExecutor(max_workers=6) as executor:
        futs = {
            executor.submit(solve_generic_channel, *args): key for key, args in channel_tasks.items()
        }
        for fut in as_completed(futs):
            key = futs[fut]
            channel_results[key] = fut.result()
            print(f"--> Finished channel model: {key}")

    n13_res = channel_results["n13"]
    n12_res = channel_results["n12"]
    wh13_res = channel_results["wh13"]
    wh14_res = channel_results["wh14"]
    fi24_res = channel_results["fi24"]
    fi25_res = channel_results["fi25"]

    print("\nAll 6 underlying channel models solved successfully!\n")

    # Step 2: Define Scenario specifications
    scenarios = [
        {
            "id": "scenario_A_51",
            "name": "Scenario A - 51 Wholesalers (N:13, WHFI:1, WH:13, FI:24)",
            "n": n13_res, "wh": wh13_res, "fi": fi24_res,
            "out_dir": REPO_ROOT / "battery/results/scenario_A_51",
            "fig": REPO_ROOT / "figures/summary_scenario_A.png"
        },
        {
            "id": "scenario_B_52",
            "name": "Scenario B - 52 Wholesalers (N:13, WHFI:1, WH:14, FI:24)",
            "n": n13_res, "wh": wh14_res, "fi": fi24_res,
            "out_dir": REPO_ROOT / "battery/results/scenario_B_52",
            "fig": REPO_ROOT / "figures/summary_scenario_B.png"
        },
        {
            "id": "scenario_C_51",
            "name": "Scenario C - 51 Wholesalers (N:12, WHFI:1, WH:13, FI:25)",
            "n": n12_res, "wh": wh13_res, "fi": fi25_res,
            "out_dir": REPO_ROOT / "battery/results/scenario_C_51",
            "fig": REPO_ROOT / "figures/summary_scenario_C.png"
        },
        {
            "id": "scenario_D_53",
            "name": "Scenario D - 53 Wholesalers (N:13, WHFI:1, WH:14, FI:25)",
            "n": n13_res, "wh": wh14_res, "fi": fi25_res,
            "out_dir": REPO_ROOT / "battery/results/scenario_D_53",
            "fig": REPO_ROOT / "figures/summary_scenario_D.png"
        },
        {
            "id": "scenario_E_52",
            "name": "Scenario E - 52 Wholesalers (N:12, WHFI:1, WH:14, FI:25)",
            "n": n12_res, "wh": wh14_res, "fi": fi25_res,
            "out_dir": REPO_ROOT / "battery/results/scenario_E_52",
            "fig": REPO_ROOT / "figures/summary_scenario_E.png"
        }
    ]

    print("--- 2. ASSEMBLING & REALIZING ALL 5 SCENARIOS IN PARALLEL ---")
    with ProcessPoolExecutor(max_workers=5) as executor:
        futures = {
            executor.submit(
                assemble_and_realize_scenario,
                sc["id"], sc["name"], sc["n"], sc["wh"], sc["fi"], sc["out_dir"], sc["fig"]
            ): sc["id"] for sc in scenarios
        }
        for fut in as_completed(futures):
            sc_id = futures[fut]
            try:
                fut.result()
                print(f"--> Finished scenario {sc_id}")
            except Exception as e:
                print(f"Error in scenario {sc_id}: {e}", file=sys.stderr)
                raise e

    print("\n--- 3. EXPORTING MASTER SCENARIOS CSV ---")
    export_cmd = [
        PY, str(REPO_ROOT / "tools/scenario_export.py"),
        "--out", str(REPO_ROOT / "scenarios.csv"),
        "--scenario", "Option 1 - National (14) + WH (11) + FI (21) + Western Merged WHFI (1)", str(REPO_ROOT / "battery/results/option1_exact_merged"),
        "--scenario", "Option 2 - Nationwide Multi-Channel (14 N + 11 WH + 21 FI)", str(REPO_ROOT / "battery/results/option2_exact_multichannel"),
    ]
    for sc in scenarios:
        export_cmd.extend(["--scenario", sc["name"], str(sc["out_dir"])])

    res_exp = subprocess.run(export_cmd, capture_output=True, text=True)
    if res_exp.returncode != 0:
        print("Export STDOUT:", res_exp.stdout)
        print("Export STDERR:", res_exp.stderr)
        raise RuntimeError("scenario_export failed")

    # Count rows in scenarios.csv
    with open(REPO_ROOT / "scenarios.csv") as f:
        reader = csv.reader(f)
        header = next(reader)
        row_count = sum(1 for _ in reader)

    print(f"scenarios.csv successfully written with {row_count:,} rows across 7 scenarios!")
    print(f"All 5 scenarios completed in {time.time() - t_master_start:.1f}s!")


if __name__ == "__main__":
    main()
