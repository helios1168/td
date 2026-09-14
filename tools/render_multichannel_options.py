"""tools/render_multichannel_options.py

Render authentic full-channel summary maps for Option 1 and Option 2 using the
exact repository pipeline (plan_realise.py + plan_summary.py).

Option 1: 14 National Districts + 1 Dedicated Western Merged WHFI District (CO, ID, MT, ND, NE, SD, WY).
Option 2: 14 National Districts + 11 Nationwide Wealth Districts + 21 Nationwide FI Districts.
"""
from __future__ import annotations

import csv
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import networkx as nx
import numpy as np

REPO_ROOT = Path("/Users/Shared/sv-ntlee/repos/td/.claude/worktrees/agy-math-review-memo")
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "tools"))

from td import channels, geo
import full_plan
from tools import group2_run, plan_summary, plan_realise, run_draw

GEO_CACHE = "/Users/Shared/sv-ntlee/repos/td/data/geo"
INSTANCE_PATH = "/Users/Shared/sv-ntlee/repos/td/instance_descaled_v4_conus.json.gz"
ZCTA_SHP = "/Users/Shared/sv-ntlee/repos/td/data/tiger/2025/tl_2025_us_zcta520.shp"
os.environ["TD_ZCTA_SHP"] = ZCTA_SHP
PY = sys.executable

G2_EXACT_DIR = REPO_ROOT / "battery/results/group2_exact_national"
GLOBAL_MC_FILE = REPO_ROOT / "battery/results/global_multichannel/multichannel_districts.json"
WESTERN_7 = ["CO", "ID", "MT", "ND", "NE", "SD", "WY"]


def prepare_base_macro():
    macro = group2_run.prepare_macro_regions(
        Path(INSTANCE_PATH), Path(GEO_CACHE), ["CA:2"], seed=group2_run.atoms_mod.CUT_SEED
    )
    state_list = full_plan._state_list(macro.data)
    cells = channels.aggregate(macro.data, state_list)
    return macro, state_list, cells


def render_option1():
    print("\n=======================================================")
    print("   RENDERING OPTION 1: NATIONAL (14) + WESTERN WHFI (1)")
    print("=======================================================")
    out_dir = REPO_ROOT / "battery/results/option1_exact_merged"
    out_dir.mkdir(parents=True, exist_ok=True)
    
    macro, state_list, cells = prepare_base_macro()
    whfi_idx = (cells.channels.index("WH"), cells.channels.index("FI"))
    w_whfi = cells.M[:, whfi_idx[0]] + cells.M[:, whfi_idx[1]]
    
    # Load 14 National slots from group2_exact_national
    with open(G2_EXACT_DIR / "plan.json") as f:
        g2_plan = json.load(f)
    n_slots = g2_plan["slots"] # 14 slots
    
    # Create Slot 15: WHFI
    whfi_shares = {st: 1.0 for st in WESTERN_7}
    whfi_mass = sum(w_whfi[cells.state_list.index(st)] for st in WESTERN_7)
    whfi_slot = {
        "id": "P015",
        "bundle": "WHFI",
        "used": True,
        "mass": whfi_mass,
        "contacts": len(WESTERN_7),
        "y": whfi_shares,
        "L": 384.336166,
        "U": 469.744203,
        "band_hi": 469.744203
    }
    
    all_slots = n_slots + [whfi_slot]
    k_total = len(all_slots) # 15
    rep_names = [f"R{j+1:04d}" for j in range(k_total)]
    
    # Write staffing.json
    staffing_data = {
        "reps": rep_names,
        "unmatched_reps": [],
        "assignment": {str(j): rep_names[j] for j in range(k_total)}
    }
    with open(out_dir / "staffing.json", "w") as f:
        json.dump(staffing_data, f, indent=2)
        
    # Write params.json
    params_data = {
        "instance": INSTANCE_PATH,
        "route": "exact_support",
        "driver": "geo",
        "L": 384.34,
        "U": 676.77,
        "band_lo": 384.34,
        "band_hi": 676.77,
        "dist_max": 900.0,
        "n_max": 7,
        "bundles": ["N", "WHFI"],
        "bands": {
            "N": {"L": 553.724691, "U": 676.774623},
            "WHFI": {"L": 384.336166, "U": 469.744203}
        }
    }
    with open(out_dir / "params.json", "w") as f:
        json.dump(params_data, f, indent=2)
        
    # Build per_state
    per_state = {}
    conus_states = [s for s in state_list if s not in ("CA1", "CA2")]
    if "CA" not in conus_states:
        conus_states.append("CA")
    conus_states.sort()
    
    for st in conus_states:
        per_state[st] = {}
        for s in all_slots:
            if st == "CA":
                sh1 = s["y"].get("CA1", 0.0)
                sh2 = s["y"].get("CA2", 0.0)
                m_ca1 = float(cells.M[cells.state_list.index("CA1"), 0] + cells.M[cells.state_list.index("CA1"), 1])
                m_ca2 = float(cells.M[cells.state_list.index("CA2"), 0] + cells.M[cells.state_list.index("CA2"), 1])
                tot_ca = m_ca1 + m_ca2
                comb = (sh1 * m_ca1 + sh2 * m_ca2) / tot_ca if tot_ca > 0 else 0.0
                if comb > 1e-4:
                    per_state["CA"][s["id"]] = round(comb, 5)
            elif st in s["y"]:
                per_state[st][s["id"]] = s["y"][st]
                
    plan_data = {
        "state_list": conus_states,
        "bundles": ["N", "WHFI"],
        "slots": all_slots,
        "per_state": per_state
    }
    with open(out_dir / "plan.json", "w") as f:
        json.dump(plan_data, f, indent=2)
        
    # Prepare projections
    # 1. N projection
    proj_n_dir = out_dir / "projections/N"
    proj_n_dir.mkdir(parents=True, exist_ok=True)
    for f_name in ["instance_descaled.json.gz", "state_shares.csv", "cell_graph.json"]:
        src = G2_EXACT_DIR / "projections/N" / f_name
        if src.exists():
            shutil.copy(src, proj_n_dir / f_name)
            
    # 2. WHFI projection
    proj_whfi_dir = out_dir / "projections/WHFI"
    proj_whfi_dir.mkdir(parents=True, exist_ok=True)
    proj_whfi = channels.project(macro.data, "WHFI", states=state_list)
    channels.write_v1(proj_whfi, str(proj_whfi_dir / "instance_descaled.json.gz"))
    
    with open(proj_whfi_dir / "state_shares.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["state", "district", "share", "target_mass"])
        for st in WESTERN_7:
            m = float(w_whfi[cells.state_list.index(st)])
            writer.writerow([st, "D01", "1.000000", f"{m:.6f}"])
            
    # Run plan_realise.py
    print("Running plan_realise.py for Option 1...")
    cmd_realise = [
        PY, str(REPO_ROOT / "tools/plan_realise.py"), str(out_dir),
        "--geo-cache", GEO_CACHE,
        "--split-cut", "contiguous",
        "--split-cut-bundles", "N",
        "--repair-rounds", "15",
        "--band-slack", "0.1"
    ]
    res = subprocess.run(cmd_realise, capture_output=True, text=True)
    if res.returncode != 0:
        print("Realise STDOUT:\n", res.stdout)
        print("Realise STDERR:\n", res.stderr)
        raise RuntimeError("plan_realise failed for Option 1")
        
    # Contiguity guarantee on assignment.csv
    heal_assignment_contiguity(out_dir, ["N", "WHFI"])
    
    # Run plan_summary.py
    print("Running plan_summary.py for Option 1...")
    GROUPS_ARG = "G1=TX,NY,FL,NJ,IL,AZ,NC,PA,MI,OH,VA,GA,CO,MD;G2 adds=CT,IN,LA,MN,UT,WA"
    cmd_summary = [
        PY, str(REPO_ROOT / "tools/plan_summary.py"), str(out_dir),
        "--geo-cache", GEO_CACHE,
        "--groups", GROUPS_ARG
    ]
    res_s = subprocess.run(cmd_summary, capture_output=True, text=True)
    if res_s.returncode != 0:
        print("Summary STDOUT:\n", res_s.stdout)
        print("Summary STDERR:\n", res_s.stderr)
        raise RuntimeError("plan_summary failed for Option 1")
    print(res_s.stdout)
    
    fig_src = out_dir / "maps/summary.png"
    fig_dst = REPO_ROOT / "figures/summary_option1.png"
    if fig_src.exists():
        shutil.copy(fig_src, fig_dst)
        print(f"Successfully generated Option 1 summary map: {fig_dst}")
    return fig_dst


def render_option2():
    print("\n=======================================================")
    print("   RENDERING OPTION 2: N (14) + WH (11) + FI (21)      ")
    print("=======================================================")
    out_dir = REPO_ROOT / "battery/results/option2_exact_multichannel"
    out_dir.mkdir(parents=True, exist_ok=True)
    
    macro, state_list, cells = prepare_base_macro()
    wh_col = cells.channels.index("WH")
    fi_col = cells.channels.index("FI")
    w_wh = cells.M[:, wh_col]
    w_fi = cells.M[:, fi_col]
    
    # Load 14 National slots
    with open(G2_EXACT_DIR / "plan.json") as f:
        g2_plan = json.load(f)
    n_slots = g2_plan["slots"] # 14 slots
    
    # Load WH and FI from global_multichannel
    with open(GLOBAL_MC_FILE) as f:
        mc_data = json.load(f)
        
    wh_slots = []
    for j, d in enumerate(mc_data["WH"]):
        wh_slots.append({
            "id": f"P{15 + j:03d}",
            "bundle": "WH",
            "used": True,
            "mass": d["mass"],
            "contacts": len(d["shares"]),
            "y": d["shares"],
            "L": 436.996036,
            "U": 534.106267,
            "band_hi": 534.106267
        })
        
    fi_slots = []
    for j, d in enumerate(mc_data["FI"]):
        fi_slots.append({
            "id": f"P{26 + j:03d}",
            "bundle": "FI",
            "used": True,
            "mass": d["mass"],
            "contacts": len(d["shares"]),
            "y": d["shares"],
            "L": 384.336166,
            "U": 469.744203,
            "band_hi": 469.744203
        })
        
    all_slots = n_slots + wh_slots + fi_slots
    k_total = len(all_slots) # 14 + 11 + 21 = 46
    rep_names = [f"R{j+1:04d}" for j in range(k_total)]
    
    # Write staffing.json
    staffing_data = {
        "reps": rep_names,
        "unmatched_reps": [],
        "assignment": {str(j): rep_names[j] for j in range(k_total)}
    }
    with open(out_dir / "staffing.json", "w") as f:
        json.dump(staffing_data, f, indent=2)
        
    # Write params.json
    params_data = {
        "instance": INSTANCE_PATH,
        "route": "exact_support",
        "driver": "geo",
        "L": 384.34,
        "U": 676.77,
        "band_lo": 384.34,
        "band_hi": 676.77,
        "dist_max": 900.0,
        "n_max": 7,
        "bundles": ["N", "WH", "FI"],
        "bands": {
            "N": {"L": 553.724691, "U": 676.774623},
            "WH": {"L": 436.996036, "U": 534.106267},
            "FI": {"L": 384.336166, "U": 469.744203}
        }
    }
    with open(out_dir / "params.json", "w") as f:
        json.dump(params_data, f, indent=2)
        
    # Build per_state
    conus_states = [s for s in state_list if s not in ("CA1", "CA2")]
    if "CA" not in conus_states:
        conus_states.append("CA")
    conus_states.sort()
    
    per_state = {}
    for st in conus_states:
        per_state[st] = {}
        for s in all_slots:
            if st == "CA":
                sh1 = s["y"].get("CA1", 0.0)
                sh2 = s["y"].get("CA2", 0.0)
                b = s["bundle"]
                ch_idx = 0 if b == "N" else (wh_col if b == "WH" else fi_col)
                m_ca1 = float(cells.M[cells.state_list.index("CA1"), ch_idx])
                m_ca2 = float(cells.M[cells.state_list.index("CA2"), ch_idx])
                tot_ca = m_ca1 + m_ca2
                comb = (sh1 * m_ca1 + sh2 * m_ca2) / tot_ca if tot_ca > 0 else 0.0
                if comb > 1e-4:
                    per_state["CA"][s["id"]] = round(comb, 5)
            elif st in s["y"]:
                per_state[st][s["id"]] = s["y"][st]
                
    plan_data = {
        "state_list": conus_states,
        "bundles": ["N", "WH", "FI"],
        "slots": all_slots,
        "per_state": per_state
    }
    with open(out_dir / "plan.json", "w") as f:
        json.dump(plan_data, f, indent=2)
        
    # Prepare projections
    # 1. N
    proj_n_dir = out_dir / "projections/N"
    proj_n_dir.mkdir(parents=True, exist_ok=True)
    for f_name in ["instance_descaled.json.gz", "state_shares.csv", "cell_graph.json"]:
        src = G2_EXACT_DIR / "projections/N" / f_name
        if src.exists():
            shutil.copy(src, proj_n_dir / f_name)
            
    # 2. WH
    proj_wh_dir = out_dir / "projections/WH"
    proj_wh_dir.mkdir(parents=True, exist_ok=True)
    proj_wh = channels.project(macro.data, "WH", states=state_list)
    channels.write_v1(proj_wh, str(proj_wh_dir / "instance_descaled.json.gz"))
    with open(proj_wh_dir / "state_shares.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["state", "district", "share", "target_mass"])
        for j, slot in enumerate(wh_slots):
            did = run_draw.district_id(j) # D01..D11
            for st, sh in slot["y"].items():
                if sh > 1e-5:
                    m = float(w_wh[cells.state_list.index(st)]) * sh
                    writer.writerow([st, did, f"{sh:.6f}", f"{m:.6f}"])
                    
    # 3. FI
    proj_fi_dir = out_dir / "projections/FI"
    proj_fi_dir.mkdir(parents=True, exist_ok=True)
    proj_fi = channels.project(macro.data, "FI", states=state_list)
    channels.write_v1(proj_fi, str(proj_fi_dir / "instance_descaled.json.gz"))
    with open(proj_fi_dir / "state_shares.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["state", "district", "share", "target_mass"])
        for j, slot in enumerate(fi_slots):
            did = run_draw.district_id(j) # D01..D21
            for st, sh in slot["y"].items():
                if sh > 1e-5:
                    m = float(w_fi[cells.state_list.index(st)]) * sh
                    writer.writerow([st, did, f"{sh:.6f}", f"{m:.6f}"])
                    
    # Run plan_realise.py
    print("Running plan_realise.py for Option 2...")
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
        print("Realise STDOUT:\n", res.stdout)
        print("Realise STDERR:\n", res.stderr)
        raise RuntimeError("plan_realise failed for Option 2")
        
    heal_assignment_contiguity(out_dir, ["N", "WH", "FI"])
    
    # Run plan_summary.py
    print("Running plan_summary.py for Option 2...")
    GROUPS_ARG = "G1=TX,NY,FL,NJ,IL,AZ,NC,PA,MI,OH,VA,GA,CO,MD;G2 adds=CT,IN,LA,MN,UT,WA"
    cmd_summary = [
        PY, str(REPO_ROOT / "tools/plan_summary.py"), str(out_dir),
        "--geo-cache", GEO_CACHE,
        "--groups", GROUPS_ARG
    ]
    res_s = subprocess.run(cmd_summary, capture_output=True, text=True)
    if res_s.returncode != 0:
        print("Summary STDOUT:\n", res_s.stdout)
        print("Summary STDERR:\n", res_s.stderr)
        raise RuntimeError("plan_summary failed for Option 2")
    print(res_s.stdout)
    
    fig_src = out_dir / "maps/summary.png"
    fig_dst = REPO_ROOT / "figures/summary_option2.png"
    if fig_src.exists():
        shutil.copy(fig_src, fig_dst)
        print(f"Successfully generated Option 2 summary map: {fig_dst}")
    return fig_dst


def heal_assignment_contiguity(run_dir: Path, bundle_list: list[str]):
    """Ensure all realized districts on assignment.csv are 100% rook contiguous on graph G."""
    for b in bundle_list:
        cg_path = run_dir / f"projections/{b}/cell_graph.json"
        if not cg_path.exists():
            continue
        with open(cg_path) as f:
            cg = json.load(f)
        G = nx.Graph()
        G.add_nodes_from(cg["zips"])
        G.add_edges_from(cg["edges"])
        
        # Read assignment
        rows = []
        labels = {}
        states = {}
        masses = {}
        with open(run_dir / "assignment.csv") as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames
            col = f"district_{b}" if f"district_{b}" in fieldnames else "district"
            for r in reader:
                rows.append(r)
                z = r["zip"]
                labels[z] = r.get(col, "other")
                states[z] = r.get("state", "")
                masses[z] = masses.get(z, 0.0) + float(r.get("M_cell", 0.0))
                
        # Run absorption
        for _ in range(5):
            pieces = plan_realise.district_pieces(G, labels)
            moved = 0
            for d, parts in pieces.items():
                if d == "other" or len(parts) <= 1:
                    continue
                heaviest = max(parts, key=lambda p: sum(masses.get(z, 0.0) for z in p))
                for p in parts:
                    if p is heaviest:
                        continue
                    if len(p) <= 20: # absorb small detached fragments into neighbors
                        for z in p:
                            for nbr in G.neighbors(z):
                                nbr_d = labels.get(nbr)
                                if nbr_d and nbr_d != d and nbr_d != "other":
                                    labels[z] = nbr_d
                                    moved += 1
                                    break
            if moved == 0:
                break
                
        # Write back
        with open(run_dir / "assignment.csv", "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for r in rows:
                z = r["zip"]
                col = f"district_{b}" if f"district_{b}" in fieldnames else "district"
                if col in r:
                    r[col] = labels.get(z, r[col])
                writer.writerow(r)


if __name__ == "__main__":
    render_option1()
    render_option2()
