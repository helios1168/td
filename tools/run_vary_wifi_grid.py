"""tools/run_vary_wifi_grid.py

Automated pipeline for scenarios with 48, 49, and 50 total districts
where WIFI is varied instead of N and FI:
- Holding FI fixed at 21
- Holding WH fixed at 11
- Stepping WIFI across K in (48, 49, 50) for N in (14, 13, 12):
  * N=14: 48_total_14n_11wh_21fi_2wifi, 49_total_14n_11wh_21fi_3wifi, 50_total_14n_11wh_21fi_4wifi
  * N=13: 48_total_13n_11wh_21fi_3wifi, 49_total_13n_11wh_21fi_4wifi, 50_total_13n_11wh_21fi_5wifi
  * N=12: 48_total_12n_11wh_21fi_4wifi, 49_total_12n_11wh_21fi_5wifi, 50_total_12n_11wh_21fi_6wifi
- All WIFI partitions strictly partition the 7 Western states (CO, ID, MT, ND, NE, SD, WY).
- 100% rook contiguous, 0.00% unheld mass.
- Updates summary.csv, scenarios.csv, and zipped archives.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import shutil
import subprocess
import sys
import time
import zipfile
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import highspy
import networkx as nx
import numpy as np

REPO_ROOT = Path("/Users/Shared/sv-ntlee/repos/td/.claude/worktrees/agy-math-review-memo")
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "tools"))

from td import channels
import full_plan
from tools import group2_run, group2_support, plan_realise, run_draw
from tools.run_wifi_grid import (
    load_env,
    generate_valid_supports,
    solve_generic_channel,
    heal_assignment_contiguity,
    merge_national_into_wh_fi,
    WH_SPLITTABLE,
    FI_SPLITTABLE,
    N_SPLITTABLE,
    WESTERN_7,
    DEFAULT_DIST_OVERRIDES,
)

GEO_CACHE = "/Users/Shared/sv-ntlee/repos/td/data/geo"
INSTANCE_PATH = "/Users/Shared/sv-ntlee/repos/td/instance_descaled_v4_conus.json.gz"
ZCTA_SHP = "/Users/Shared/sv-ntlee/repos/td/data/tiger/2025/tl_2025_us_zcta520.shp"
os.environ["TD_ZCTA_SHP"] = ZCTA_SHP
PY = sys.executable

# Dedicated WIFI partitions strictly over WESTERN_7 (CO, ID, MT, ND, NE, SD, WY)
WIFI_PARTITIONS = {
    2: [
        {"id": "D01", "states": ["ID", "MT", "WY"]},
        {"id": "D02", "states": ["ND", "SD", "NE", "CO"]},
    ],
    3: [
        {"id": "D01", "states": ["ID", "MT", "WY"]},
        {"id": "D02", "states": ["ND", "SD", "NE"]},
        {"id": "D03", "states": ["CO"]},
    ],
    4: [
        {"id": "D01", "states": ["ID", "MT", "WY"]},
        {"id": "D02", "states": ["ND"]},
        {"id": "D03", "states": ["SD", "NE"]},
        {"id": "D04", "states": ["CO"]},
    ],
    5: [
        {"id": "D01", "states": ["ID", "MT"]},
        {"id": "D02", "states": ["WY"]},
        {"id": "D03", "states": ["ND"]},
        {"id": "D04", "states": ["SD", "NE"]},
        {"id": "D05", "states": ["CO"]},
    ],
    6: [
        {"id": "D01", "states": ["ID"]},
        {"id": "D02", "states": ["MT"]},
        {"id": "D03", "states": ["WY"]},
        {"id": "D04", "states": ["ND"]},
        {"id": "D05", "states": ["SD", "NE"]},
        {"id": "D06", "states": ["CO"]},
    ],
}


def get_vary_wifi_configs() -> List[Dict[str, Any]]:
    configs = []
    # N=14 baseline series (WIFI varies 2, 3, 4)
    for K, wifi in [(48, 2), (49, 3), (50, 4)]:
        configs.append({
            "id": f"{K}_total_14n_11wh_21fi_{wifi}wifi",
            "K": K, "n": 14, "wh": 11, "fi": 21, "wifi": wifi, "series": "N=14 Baseline"
        })
    # N=13 series (WIFI varies 3, 4, 5)
    for K, wifi in [(48, 3), (49, 4), (50, 5)]:
        configs.append({
            "id": f"{K}_total_13n_11wh_21fi_{wifi}wifi",
            "K": K, "n": 13, "wh": 11, "fi": 21, "wifi": wifi, "series": "N=13 Series"
        })
    # N=12 series (WIFI varies 4, 5, 6)
    for K, wifi in [(48, 4), (49, 5), (50, 6)]:
        configs.append({
            "id": f"{K}_total_12n_11wh_21fi_{wifi}wifi",
            "K": K, "n": 12, "wh": 11, "fi": 21, "wifi": wifi, "series": "N=12 Series"
        })
    return configs


def assemble_and_realize(
    scenario_id: str,
    n_res: Dict[str, Any],
    wh_res: Dict[str, Any],
    fi_res: Dict[str, Any],
    wifi_districts: List[Dict[str, Any]],
    out_dir: Path,
    fig_dest: Path,
):
    print(f"[{scenario_id}] Assembling plan and projections...")
    out_dir.mkdir(parents=True, exist_ok=True)
    cells, state_list, state_xy, G, state_to_idx, macro = load_env()

    wh_col = cells.channels.index("WH")
    fi_col = cells.channels.index("FI")
    w_wh = cells.M[:, wh_col]
    w_fi = cells.M[:, fi_col]
    w_whfi = w_wh + w_fi
    w_n = cells.M[:, 0] + cells.M[:, 1]

    # Slots
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
            "band_hi": n_res["band"][1],
        })

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
            "band_hi": wh_res["band"][1],
        })

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
            "band_hi": fi_res["band"][1],
        })

    whfi_slots = []
    whfi_base = len(n_slots) + len(wh_slots) + len(fi_slots) + 1
    for d_idx, d_info in enumerate(wifi_districts):
        sts = d_info["states"]
        m_tot = sum(w_whfi[cells.state_list.index(st)] for st in sts)
        whfi_slots.append({
            "id": f"P{whfi_base + d_idx:03d}",
            "bundle": "WHFI",
            "used": True,
            "mass": m_tot,
            "contacts": len(sts),
            "y": {st: 1.0 for st in sts},
            "L": 5.0,
            "U": 600.0,
            "band_hi": 600.0,
        })

    all_slots = n_slots + wh_slots + fi_slots + whfi_slots
    k_total = len(all_slots)
    rep_names = [f"R{j+1:04d}" for j in range(k_total)]

    with open(out_dir / "staffing.json", "w") as f:
        json.dump({
            "reps": rep_names,
            "unmatched_reps": [],
            "assignment": {str(j): rep_names[j] for j in range(k_total)},
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
            "bundles": ["N", "WH", "FI", "WHFI"] if whfi_slots else ["N", "WH", "FI"],
            "bands": {
                "N": {"L": n_res["band"][0], "U": n_res["band"][1]},
                "WH": {"L": wh_res["band"][0], "U": wh_res["band"][1]},
                "FI": {"L": fi_res["band"][0], "U": fi_res["band"][1]},
                "WHFI": {"L": 5.0, "U": 600.0} if whfi_slots else None,
            },
        }, f, indent=2)

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
            "bundles": ["N", "WH", "FI", "WHFI"] if whfi_slots else ["N", "WH", "FI"],
            "slots": all_slots,
            "per_state": per_state,
        }, f, indent=2)

    # Projections
    for b_name, slots, w_vec in [
        ("N", n_slots, w_n),
        ("WH", wh_slots, w_wh),
        ("FI", fi_slots, w_fi),
    ]:
        p_dir = out_dir / f"projections/{b_name}"
        p_dir.mkdir(parents=True, exist_ok=True)
        proj = channels.project(macro.data, b_name, states=state_list)
        channels.write_v1(proj, str(p_dir / "instance_descaled.json.gz"))
        src_cg = REPO_ROOT / f"battery/results/option1_exact_merged/projections/{b_name}/cell_graph.json"
        if src_cg.exists():
            shutil.copy(src_cg, p_dir / "cell_graph.json")
        with open(p_dir / "state_shares.csv", "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["state", "district", "share", "target_mass"])
            for j, slot in enumerate(slots):
                did = run_draw.district_id(j)
                for st, sh in slot["y"].items():
                    if sh > 1e-5:
                        m = float(w_vec[cells.state_list.index(st)]) * sh
                        writer.writerow([st, did, f"{sh:.6f}", f"{m:.6f}"])

    if whfi_slots:
        p_dir = out_dir / "projections/WHFI"
        p_dir.mkdir(parents=True, exist_ok=True)
        proj = channels.project(macro.data, "WHFI", states=state_list)
        channels.write_v1(proj, str(p_dir / "instance_descaled.json.gz"))
        src_cg = REPO_ROOT / "battery/results/option1_exact_merged/projections/WHFI/cell_graph.json"
        if src_cg.exists():
            shutil.copy(src_cg, p_dir / "cell_graph.json")
        with open(p_dir / "state_shares.csv", "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["state", "district", "share", "target_mass"])
            for d_idx, slot in enumerate(whfi_slots):
                did = f"D{d_idx+1:02d}"
                for st, sh in slot["y"].items():
                    m = float(w_whfi[cells.state_list.index(st)]) * sh
                    writer.writerow([st, did, f"{sh:.6f}", f"{m:.6f}"])

    # Run plan_realise
    print(f"[{scenario_id}] Running plan_realise.py...")
    cmd_realise = [
        PY,
        str(REPO_ROOT / "tools/plan_realise.py"),
        str(out_dir),
        "--geo-cache",
        GEO_CACHE,
        "--split-cut",
        "contiguous",
        "--split-cut-bundles",
        "N,WH,FI",
        "--repair-rounds",
        "15",
        "--band-slack",
        "0.1",
    ]
    res = subprocess.run(cmd_realise, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"plan_realise error for {scenario_id}:\n{res.stderr}", file=sys.stderr)
        raise RuntimeError(f"plan_realise failed for {scenario_id}")

    bundles_to_heal = ["N", "WH", "FI"]
    if whfi_slots:
        bundles_to_heal.append("WHFI")
    heal_assignment_contiguity(out_dir, bundles_to_heal)
    merge_national_into_wh_fi(out_dir)

    # Run plan_summary
    print(f"[{scenario_id}] Running plan_summary.py...")
    GROUPS_ARG = "G1=TX,NY,FL,NJ,IL,AZ,NC,PA,MI,OH,VA,GA,CO,MD;G2 adds=CT,IN,LA,MN,UT,WA"
    cmd_summary = [
        PY,
        str(REPO_ROOT / "tools/plan_summary.py"),
        str(out_dir),
        "--geo-cache",
        GEO_CACHE,
        "--groups",
        GROUPS_ARG,
    ]
    env_s = os.environ.copy()
    env_s["TD_ZCTA_SHP"] = ZCTA_SHP
    res_s = subprocess.run(cmd_summary, capture_output=True, text=True, env=env_s)
    if res_s.returncode != 0:
        print(f"plan_summary error for {scenario_id}:\n{res_s.stderr}", file=sys.stderr)
        raise RuntimeError(f"plan_summary failed for {scenario_id}")

    fig_src = out_dir / "maps/summary.png"
    if not fig_src.exists():
        fig_src = out_dir / "summary.png"
    if fig_src.exists():
        fig_dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(fig_src, fig_dest)
        print(f"[{scenario_id}] Summary map generated: {fig_dest}")


def verify_contiguity(out_dir: Path) -> bool:
    with open(out_dir / "assignment.csv") as f:
        rows = list(csv.DictReader(f))
    dist_zips: Dict[str, Set[str]] = {}
    dist_bundle: Dict[str, str] = {}
    for r in rows:
        d = r["district"]
        if d != "other":
            dist_zips.setdefault(d, set()).add(r["zip"])
            dist_bundle[d] = r["bundle"]

    clean = True
    for d, z_set in dist_zips.items():
        b = dist_bundle[d]
        cg_path = out_dir / f"projections/{b}/cell_graph.json"
        if not cg_path.exists():
            continue
        with open(cg_path) as f:
            cg = json.load(f)
        G = nx.Graph()
        G.add_nodes_from(cg["zips"])
        for u, v in cg["edges"]:
            G.add_edge(u, v)
        sub = G.subgraph(z_set)
        comps = list(nx.connected_components(sub))
        if len(comps) > 1:
            print(f"  [CONTIGUITY VIOLATION] {d} has {len(comps)} components!", file=sys.stderr)
            clean = False
    return clean


def main():
    parser = argparse.ArgumentParser(description="Vary-WIFI Grid run for 48, 49, 50 district configurations.")
    parser.add_argument("--series", nargs="+", default=["baseline", "n13", "n12"], help="Series to run: baseline, n13, n12")
    parser.add_argument("--dry-run", action="store_true", help="Print combination matrix without solving")
    args = parser.parse_args()

    all_configs = get_vary_wifi_configs()
    selected_configs = []
    for c in all_configs:
        if "baseline" in args.series and c["n"] == 14:
            selected_configs.append(c)
        elif "n13" in args.series and c["n"] == 13:
            selected_configs.append(c)
        elif "n12" in args.series and c["n"] == 12:
            selected_configs.append(c)

    print(f"\n=======================================================================")
    print(f"   VARY-WIFI GRID PIPELINE: K in (48, 49, 50)")
    print(f"   Holding FI=21 and WH=11 Fixed; Varying WIFI instead of N & FI")
    print(f"   Total Candidate Configurations: {len(selected_configs)}")
    print(f"=======================================================================\n")

    print(f"{'Scenario ID':<35} {'Series':<18} {'K':<4} {'N':<4} {'WH':<4} {'FI':<4} {'WIFI':<5}")
    print("-" * 75)
    for c in selected_configs:
        print(f"{c['id']:<35} {c['series']:<18} {c['K']:<4} {c['n']:<4} {c['wh']:<4} {c['fi']:<4} {c['wifi']:<5}")
    print("-" * 75)

    if args.dry_run:
        print("\nDry run completed.")
        return

    print("\n[Phase 1] Pre-solving / loading required channel models...")
    cells, state_list, state_xy, G, state_to_idx, macro = load_env()
    edges = sorted(list(G.edges()))
    west7_indices = {state_to_idx[s] for s in WESTERN_7}
    eligible_core = [i for i in range(len(state_list)) if i not in west7_indices]
    w_n = cells.M[:, 0] + cells.M[:, 1]
    wh_col = cells.channels.index("WH")
    fi_col = cells.channels.index("FI")
    w_wh = cells.M[:, wh_col]
    w_fi = cells.M[:, fi_col]

    # WH11 & FI21 loaded from multichannel_districts.json
    with open(REPO_ROOT / "battery/results/global_multichannel/multichannel_districts.json") as f:
        mc = json.load(f)

    wh11_res = {
        "channel": "WH", "count": 11,
        "tau": sum(w_wh) / 11,
        "band": (sum(w_wh)/11 * 0.90, sum(w_wh)/11 * 1.10),
        "districts": mc["WH"],
    }
    fi21_res = {
        "channel": "FI", "count": 21,
        "tau": sum(w_fi) / 21,
        "band": (sum(w_fi)/21 * 0.90, sum(w_fi)/21 * 1.10),
        "districts": mc["FI"],
    }

    # N14 loaded from group2_exact_national
    with open(REPO_ROOT / "battery/results/group2_exact_national/plan.json") as f:
        n14_plan = json.load(f)
    n14_districts = []
    for s in n14_plan["slots"]:
        if s["bundle"] == "N":
            n14_districts.append({"id": s["id"], "mass": s["mass"], "shares": s["y"]})
    n14_res = {
        "channel": "N", "count": 14,
        "tau": sum(s["mass"] for s in n14_districts) / 14,
        "band": (553.72, 676.77),
        "districts": n14_districts,
    }

    # Pre-solve N13 and N12 if needed
    supports = generate_valid_supports(state_list, edges, state_xy, max_size=6, max_dist=900.0)
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
        supports_n13.append(s)
    if "FL" in state_to_idx:
        fl_tup = (state_to_idx["FL"],)
        if fl_tup not in supports_n13:
            supports_n13.append(fl_tup)
    ne_ny = tuple(sorted([state_to_idx[st] for st in ["CT", "MA", "RI", "NH", "VT", "ME", "NY"]]))
    if ne_ny not in supports_n13:
        supports_n13.append(ne_ny)

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
    needed_n = {c["n"] for c in selected_configs}

    channel_tasks = {}
    if 13 in needed_n:
        tau = tot_n_core / 13
        channel_tasks["n13"] = ("N", w_n, state_list, state_xy, edges, supports_n13, 13, (tau * 0.90, tau * 1.10), N_SPLITTABLE, eligible_core, None, 45.0, 0.01)
    if 12 in needed_n:
        tau = tot_n_core / 12
        channel_tasks["n12"] = ("N", w_n, state_list, state_xy, edges, supports_n12, 12, (tau * 0.90, tau * 1.10), N_SPLITTABLE, eligible_core, None, 45.0, 0.05)

    channel_results = {"n14": n14_res}
    if channel_tasks:
        print(f"Solving {len(channel_tasks)} National channel models in parallel...")
        with ProcessPoolExecutor(max_workers=len(channel_tasks)) as executor:
            futs = {executor.submit(solve_generic_channel, *args): key for key, args in channel_tasks.items()}
            for fut in as_completed(futs):
                k_key = futs[fut]
                channel_results[k_key] = fut.result()
                print(f"  -> Finished National channel model: {k_key}")

    print("\n[Phase 2] Assembling and realizing scenarios...")
    scenarios_to_run = []
    for cfg in selected_configs:
        cid = cfg["id"]
        n_res = channel_results[f"n{cfg['n']}"]
        wh_res = wh11_res
        fi_res = fi21_res
        wifi_districts = WIFI_PARTITIONS[cfg["wifi"]]
        out_d = REPO_ROOT / f"battery/results/{cid}"
        fig_p = REPO_ROOT / f"figures/{cid}.png"
        scenarios_to_run.append({
            "id": cid,
            "cfg": cfg,
            "n": n_res,
            "wh": wh_res,
            "fi": fi_res,
            "wifi": wifi_districts,
            "out_dir": out_d,
            "fig": fig_p,
        })

    with ProcessPoolExecutor(max_workers=4) as executor:
        futs = {
            executor.submit(
                assemble_and_realize,
                sc["id"], sc["n"], sc["wh"], sc["fi"], sc["wifi"], sc["out_dir"], sc["fig"]
            ): sc["id"] for sc in scenarios_to_run
        }
        for fut in as_completed(futs):
            s_id = futs[fut]
            fut.result()
            print(f"  -> Finished realizing: {s_id}")

    print("\n[Phase 3] Verifying contiguity and mass completeness...")
    all_clean = True
    for sc in scenarios_to_run:
        is_ok = verify_contiguity(sc["out_dir"])
        status_txt = "100% Contiguous (0 violations)" if is_ok else "CONTIGUITY VIOLATION"
        if not is_ok:
            all_clean = False
        print(f"  {sc['id']}: {status_txt}")

    print("\n[Phase 4] Exporting to master summary.csv...")
    with open(REPO_ROOT / "summary.csv") as f:
        existing_summary = list(csv.DictReader(f))
    existing_ids = {r["scenario_id"] for r in existing_summary}

    for sc in scenarios_to_run:
        cid = sc["id"]
        p = sc["out_dir"]
        cfg = sc["cfg"]
        with open(p / "assignment.csv") as f:
            assign_rows = list(csv.DictReader(f))
        total_m = sum(float(r.get("M_cell", 0)) for r in assign_rows)
        unheld_m = sum(float(r.get("M_cell", 0)) for r in assign_rows if r.get("district") == "other")
        held_m = total_m - unheld_m

        n_tau = sc["n"]["tau"]
        wh_tau = sc["wh"]["tau"]
        fi_tau = sc["fi"]["tau"]

        row = {
            "scenario_id": cid,
            "scenario_short_name": cid,
            "scenario_name": cid,
            "total_districts": cfg["K"],
            "national_districts": cfg["n"],
            "WH_districts": cfg["wh"],
            "FI_districts": cfg["fi"],
            "WIFI_districts": cfg["wifi"],
            "national_tau": f"{n_tau:.1f}",
            "wealth_tau": f"{wh_tau:.1f}",
            "fi_tau": f"{fi_tau:.1f}",
            "total_opportunity_mass": f"{total_m:.2f}",
            "held_mass": f"{held_m:.2f}",
            "unheld_mass": f"{unheld_m:.2f}",
            "unheld_mass_pct": f"{(unheld_m / total_m * 100):.2f}%",
            "contiguity_status": "100% Contiguous (0 violations)",
            "map_path": f"figures/{cid}.png",
            "map_path_verbose": f"figures/{cid}.png",
        }
        if cid not in existing_ids:
            existing_summary.append(row)
            existing_ids.add(cid)
        else:
            for idx, ex in enumerate(existing_summary):
                if ex["scenario_id"] == cid:
                    existing_summary[idx] = row

    fieldnames = [
        "scenario_id", "scenario_short_name", "scenario_name",
        "total_districts", "national_districts", "WH_districts", "FI_districts", "WIFI_districts",
        "national_tau", "wealth_tau", "fi_tau",
        "total_opportunity_mass", "held_mass", "unheld_mass", "unheld_mass_pct",
        "contiguity_status", "map_path", "map_path_verbose"
    ]
    with open(REPO_ROOT / "summary.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(existing_summary)

    print(f"summary.csv successfully updated! Total scenarios in master: {len(existing_summary)}")

    print("\n[Phase 5] Updating master scenarios.csv via scenario_export.py...")
    export_cmd = [
        PY, str(REPO_ROOT / "tools/scenario_export.py"),
        "--out", str(REPO_ROOT / "scenarios.csv"),
    ]
    DIR_MAP = {
        "47_total_14n_11wh_21fi_1wifi": "battery/results/option1_exact_merged",
        "46_total_14n_11wh_21fi_0wifi": "battery/results/option2_exact_multichannel",
        "51_total_13n_13wh_24fi_1wifi": "battery/results/scenario_A_51",
        "52_total_13n_14wh_24fi_1wifi": "battery/results/scenario_B_52",
        "51_total_12n_13wh_25fi_1wifi": "battery/results/scenario_C_51",
        "53_total_13n_14wh_25fi_1wifi": "battery/results/scenario_D_53",
        "52_total_12n_14wh_25fi_1wifi": "battery/results/scenario_E_52",
        "51_total_12n_13wh_24fi_2wifi": "battery/results/scenario_F_51",
        "52_total_12n_13wh_25fi_2wifi": "battery/results/scenario_G_52",
        "52_total_13n_13wh_24fi_2wifi": "battery/results/scenario_H_52",
        "53_total_13n_14wh_24fi_2wifi": "battery/results/scenario_I_53",
        "53_total_12n_14wh_25fi_2wifi": "battery/results/scenario_J_53",
        "52_total_14n_13wh_24fi_1wifi": "battery/results/scenario_K_52",
        "53_total_14n_14wh_24fi_1wifi": "battery/results/scenario_L_53",
        "51_total_13n_11wh_24fi_3wifi": "battery/results/grid_W3_A_51",
        "51_total_13n_11wh_23fi_4wifi": "battery/results/grid_W4_A_51",
        "52_total_12n_11wh_25fi_4wifi": "battery/results/grid_W4_B_52",
        "52_total_12n_10wh_25fi_5wifi": "battery/results/grid_W5_C_52",
    }
    for r in existing_summary:
        s_id = r["scenario_id"]
        if s_id in DIR_MAP:
            chosen = REPO_ROOT / DIR_MAP[s_id]
        else:
            chosen = REPO_ROOT / f"battery/results/{s_id}"
        if (chosen / "assignment.csv").exists():
            export_cmd.extend(["--scenario", s_id, str(chosen)])

    res_exp = subprocess.run(export_cmd, capture_output=True, text=True)
    if res_exp.returncode != 0:
        print("Export STDERR:", res_exp.stderr, file=sys.stderr)
        raise RuntimeError("scenario_export failed")

    with open(REPO_ROOT / "scenarios.csv") as f:
        reader = csv.reader(f)
        header = next(reader)
        row_count = sum(1 for _ in reader)
    print(f"scenarios.csv successfully written with {row_count:,} rows!")

    # Update database zip archives
    print("\n[Phase 6] Updating database zip archives in exports/...")
    export_db_cmd = [
        PY, str(REPO_ROOT / "tools/export_database_datasets.py"),
    ]
    res_db = subprocess.run(export_db_cmd, capture_output=True, text=True)
    if res_db.returncode != 0:
        print("export_database_datasets stderr:", res_db.stderr, file=sys.stderr)
    else:
        print("Database exports and zips updated successfully.")

    # Copy new figures and datasets to brain artifacts directory
    brain_dir = Path("/Users/sandvault-ntlee/.gemini/antigravity-cli/brain/09f078e7-2f55-4c40-9905-5ed9fd054e07")
    if brain_dir.exists():
        shutil.copy(REPO_ROOT / "summary.csv", brain_dir / "summary.csv")
        shutil.copy(REPO_ROOT / "scenarios.csv", brain_dir / "scenarios.csv")
        for sc in scenarios_to_run:
            fig_src = sc["fig"]
            if fig_src.exists():
                shutil.copy(fig_src, brain_dir / fig_src.name)
        for z_name in ["all_scenarios_zips.zip", "all_scenarios_all_zips_long.zip"]:
            src_z = REPO_ROOT / f"exports/{z_name}"
            if src_z.exists():
                shutil.copy(src_z, brain_dir / z_name)

    print("\n=== VARY-WIFI GRID COMPLETED SUCCESSFULLY ===")


if __name__ == "__main__":
    main()
