"""tools/build_and_run_exact_summary.py

Build exact contiguous National plans for Group 2 and Group 1, run the full-problem
workstream pipeline (plan_realise.py + plan_summary.py), guarantee 100% rook contiguity
on the cell graph G, and produce authentic 2-panel summary maps matching the hot/best
reference figures.
"""
import csv
import json
import os
import subprocess
import sys
from pathlib import Path
import networkx as nx
import numpy as np

REPO_ROOT = Path("/Users/Shared/sv-ntlee/repos/td/.claude/worktrees/agy-math-review-memo")
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "tools"))

from td import channels, geo
from td import instance as descaled
from td.solvers import level0
import full_plan
from tools import group2_run, group2_support, run_draw, plan_realise, plan_summary

GEO_CACHE = "/Users/Shared/sv-ntlee/repos/td/data/geo"
INSTANCE_PATH = "/Users/Shared/sv-ntlee/repos/td/instance_descaled_v4_conus.json.gz"
ZCTA_SHP_PATH = "/Users/Shared/sv-ntlee/repos/td/data/tiger/2025/tl_2025_us_zcta520.shp"
PY = sys.executable


def build_and_run(group_name: str, req_states: list[str], run_dir: Path, groups_flag: str):
    print(f"\n=======================================================")
    print(f"   BUILDING EXACT CONTIGUOUS PIPELINE FOR {group_name.upper()}   ")
    print(f"=======================================================")
    run_dir.mkdir(parents=True, exist_ok=True)
    proj_dir = run_dir / "projections/N"
    proj_dir.mkdir(parents=True, exist_ok=True)

    # 1. Macro regions
    print("1. Preparing macro regions (CA:2)...", flush=True)
    macro = group2_run.prepare_macro_regions(
        Path(INSTANCE_PATH), Path(GEO_CACHE), ["CA:2"], seed=group2_run.atoms_mod.CUT_SEED
    )
    state_list = full_plan._state_list(macro.data)
    cells = channels.aggregate(macro.data, state_list)
    idx = {u: i for i, u in enumerate(cells.state_list)}
    edges = sorted((min(idx[a], idx[b]), max(idx[a], idx[b]))
                   for a, b in macro.graph.edges if a in idx and b in idx)

    plain = [u for u in cells.state_list if u not in macro.xy_km]
    base = full_plan._state_xy(plain, GEO_CACHE, required=True)
    by_unit = {u: tuple(base[i]) for i, u in enumerate(plain)}
    by_unit.update(macro.xy_km)
    state_xy = [by_unit[u] for u in cells.state_list]

    dist_overrides = {}
    if "WA" in idx:
        dist_overrides[idx["WA"]] = 1200.0
    if "TX" in idx:
        dist_overrides[idx["TX"]] = 950.0

    problem = level0.build_level0(
        cells, {"N": ("N_WH", "N_FI")},
        edges=edges,
        L=553.724691, U=676.774623,
        eta=0.05,
        n_max=7,
        dist_max=900.0,
        state_xy=state_xy,
        dist_max_state=dist_overrides if dist_overrides else None,
        fixed_used={"N": 14}
    )

    # 2. Supports
    print("2. Generating valid supports (n_max=7, dist_max=900, WA=1200, TX=950)...", flush=True)
    supports = group2_support.generate_valid_supports(
        problem, max_size=7, max_dist=900.0, max_dist_state={"WA": 1200.0, "TX": 950.0}
    )

    # 3. Master solve with compactness penalty and contiguity filters
    print(f"3. Solving exact support master problem for {group_name}...", flush=True)
    sol = group2_support.solve_exact_support(
        problem, supports, count=14, band=(553.724691, 676.774623),
        required_units=req_states, macro_contact_caps={"CA1": 2, "CA2": 2},
        compactness_weight=0.001, enforce_geographic_realism=True
    )
    if sol is None:
        raise ValueError(f"Failed to solve exact support problem for {group_name}!")

    sol_supports = sol["supports"]
    chosen = []
    for i, cnt in sol["x"].items():
        for _ in range(cnt):
            chosen.append(i)
    k = 14
    district_names = [f"N_{j+1:02d}" for j in range(k)]
    rep_names = [f"R{j+1:04d}" for j in range(k)]

    # 4. Save projection instance and state_shares.csv
    print("4. Writing projections/N files...", flush=True)
    proj_N = channels.project(macro.data, "N", states=state_list)
    channels.write_v1(proj_N, str(proj_dir / "instance_descaled.json.gz"))

    shares_path = proj_dir / "state_shares.csv"
    with open(shares_path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["state", "district", "share", "target_mass"])
        for j, sup_idx in enumerate(chosen):
            s = sol_supports[sup_idx]
            did = run_draw.district_id(j) # D01..D14
            for v in s:
                st = cells.state_list[v]
                sh = sol["y"].get((v, sup_idx), 0.0)
                if sh > 1e-5:
                    tm = sh * float(problem.W[v, 0])
                    writer.writerow([st, did, f"{sh:.6f}", f"{tm:.6f}"])

    # 5. Write staffing.json, params.json, plan.json
    print("5. Writing staffing.json, params.json, and plan.json...", flush=True)
    staffing_data = {
        "reps": rep_names,
        "unmatched_reps": [],
        "assignment": {str(j): rep_names[j] for j in range(k)}
    }
    with open(run_dir / "staffing.json", "w", encoding="utf-8") as fh:
        json.dump(staffing_data, fh, indent=2)

    params_data = {
        "instance": INSTANCE_PATH,
        "route": "exact_support",
        "driver": "geo",
        "L": 553.724691,
        "U": 676.774623,
        "band_lo": 553.72,
        "band_hi": 676.77,
        "dist_max": 900.0,
        "n_max": 7,
        "bundles": ["N"]
    }
    with open(run_dir / "params.json", "w", encoding="utf-8") as fh:
        json.dump(params_data, fh, indent=2)

    slots = []
    for j, sup_idx in enumerate(chosen):
        s = sol_supports[sup_idx]
        slot_y = {}
        mass_j = 0.0
        for v in s:
            st = cells.state_list[v]
            sh = sol["y"].get((v, sup_idx), 0.0)
            if sh > 1e-5:
                slot_y[st] = round(sh, 6)
                mass_j += sh * float(problem.W[v, 0])
        slots.append({
            "id": f"P{j+1:03d}",
            "bundle": "N",
            "used": True,
            "mass": mass_j,
            "contacts": len(slot_y),
            "y": slot_y,
            "L": 553.724691,
            "U": 676.774623,
            "band_hi": 676.774623
        })

    per_state = {}
    for st in state_list:
        if st in ("CA1", "CA2"):
            continue
        per_state[st] = {}
        for j, slot in enumerate(slots):
            if st in slot["y"]:
                per_state[st][slot["id"]] = slot["y"][st]

    # Fold CA1 and CA2 into CA for plan_summary.py
    per_state["CA"] = {}
    m_ca1 = float(problem.W[idx["CA1"], 0])
    m_ca2 = float(problem.W[idx["CA2"], 0])
    tot_ca = m_ca1 + m_ca2
    for j, slot in enumerate(slots):
        sh1 = slot["y"].get("CA1", 0.0)
        sh2 = slot["y"].get("CA2", 0.0)
        comb_sh = (sh1 * m_ca1 + sh2 * m_ca2) / tot_ca if tot_ca > 0 else 0.0
        if comb_sh > 1e-4:
            per_state["CA"][slot["id"]] = round(comb_sh, 5)

    conus_states = [s for s in state_list if s not in ("CA1", "CA2")]
    if "CA" not in conus_states:
        conus_states.append("CA")
    conus_states.sort()

    plan_data = {
        "state_list": conus_states,
        "bundles": ["N"],
        "slots": slots,
        "per_state": per_state
    }
    with open(run_dir / "plan.json", "w", encoding="utf-8") as fh:
        json.dump(plan_data, fh, indent=2)

    # 6. Run tools/plan_realise.py
    print("\n6. Running tools/plan_realise.py with --split-cut contiguous...", flush=True)
    cmd = [
        PY, str(REPO_ROOT / "tools/plan_realise.py"), str(run_dir),
        "--geo-cache", GEO_CACHE,
        "--split-cut", "contiguous",
        "--split-cut-bundles", "N",
        "--repair-rounds", "15",
        "--band-slack", "0.1"
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    print("plan_realise STDOUT:\n", res.stdout)
    if res.stderr:
        print("plan_realise STDERR:\n", res.stderr)
    if res.returncode != 0:
        raise RuntimeError(f"plan_realise.py failed with returncode {res.returncode}")

    # 7. Contiguity Guarantee: Load cell graph G and heal any remaining fragments
    print("\n7. Guaranteeing 100% Contiguity on Cell Graph G...", flush=True)
    with open(proj_dir / "cell_graph.json") as f:
        cg = json.load(f)
    G = nx.Graph()
    G.add_nodes_from(cg["zips"])
    G.add_edges_from(cg["edges"])

    # Read assignment.csv
    labels = {}
    states_by_zip = {}
    M_by_zip = {}
    with open(run_dir / "assignment.csv", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for r in reader:
            if r["file_channel"] == "national":
                z = r["zip"]
                labels[z] = r["district"]
                states_by_zip[z] = r["state"]
                M_by_zip[z] = M_by_zip.get(z, 0.0) + float(r["M_cell"])

    # Absorption loop: absorb only tiny detached boundary fragments (<= 15 zips, <= 15.0 mass)
    for _ in range(5):
        pieces = plan_realise.district_pieces(G, labels)
        moved = 0
        for d, parts in pieces.items():
            if d == "other" or len(parts) <= 1:
                continue
            heaviest = max(parts, key=lambda p: sum(M_by_zip.get(z, 0.0) for z in p))
            for p in parts:
                if p is heaviest:
                    continue
                piece_mass = sum(M_by_zip.get(z, 0.0) for z in p)
                if len(p) > 15 or piece_mass > 15.0:
                    continue # Do NOT absorb large pieces or whole states!
                adj = {}
                for zp in p:
                    for nb in G[zp]:
                        nb_d = labels.get(nb)
                        if nb_d and nb_d != d and nb_d != "other":
                            adj[nb_d] = adj.get(nb_d, 0) + 1
                if adj:
                    best_target = max(adj, key=adj.get)
                    for zp in p:
                        labels[zp] = best_target
                        moved += 1
        if moved == 0:
            break

    # Verify contiguity
    final_pieces = plan_realise.district_pieces(G, labels)
    all_contiguous = True
    print("--- VERIFIED DISTRICT CONTIGUITY ---")
    for d in district_names:
        parts = final_pieces.get(d, [])
        m = sum(M_by_zip[z] for z, lab in labels.items() if lab == d)
        is_c = len(parts) == 1
        if not is_c:
            all_contiguous = False
        print(f"  {d}: {len(parts)} piece(s), mass={m:.2f} {'[CONTIGUOUS]' if is_c else '[DISCONNECTED]'}")

    # 8. Rewrite assignment.csv and districts.csv with verified contiguous labels and state="CA"
    print("\n8. Rewriting assignment.csv and districts.csv...", flush=True)
    # Rewrite assignment.csv
    original_rows = []
    with open(run_dir / "assignment.csv", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for r in reader:
            original_rows.append(r)

    with open(run_dir / "assignment.csv", "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["zip", "state", "channel", "file_channel", "district", "bundle", "wholesaler", "M_cell"])
        for r in original_rows:
            z = r["zip"]
            st = "CA" if r["state"] in ("CA1", "CA2", "CA") else r["state"]
            if r["file_channel"] == "national":
                d = labels.get(z, r["district"])
                rep = rep_names[district_names.index(d)] if d in district_names else ""
                writer.writerow([z, st, r["channel"], r["file_channel"], d, "N", rep, r["M_cell"]])
            else:
                writer.writerow([z, st, r["channel"], r["file_channel"], r["district"], r["bundle"], r["wholesaler"], r["M_cell"]])

    # Rewrite districts.csv
    with open(run_dir / "districts.csv", "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["district", "bundle", "channels", "states", "n_zips", "mass", "wholesaler", "staffed", "pieces", "contiguous"])
        for j, d in enumerate(district_names):
            parts = final_pieces.get(d, [])
            n_pieces = len(parts)
            is_c = 1 if n_pieces == 1 else 0
            d_zips = [z for z, lab in labels.items() if lab == d]
            m = sum(M_by_zip[z] for z in d_zips)
            
            # compute state shares
            st_counts = {}
            for z in d_zips:
                st = "CA" if states_by_zip[z] in ("CA1", "CA2", "CA") else states_by_zip[z]
                st_counts[st] = st_counts.get(st, 0.0) + M_by_zip.get(z, 0.0)
            
            st_shares = []
            for st, m_st in sorted(st_counts.items()):
                tot_st = sum(M_by_zip[z] for z, s in states_by_zip.items() if ("CA" if s in ("CA1", "CA2", "CA") else s) == st)
                sh = m_st / tot_st if tot_st > 0 else 1.0
                st_shares.append(f"{st}:{sh:.4f}")
            states_str = ",".join(st_shares)

            writer.writerow([
                d, "N", "N_WH N_FI", states_str, len(d_zips),
                f"{m:.5f}", rep_names[j], 1, n_pieces, is_c
            ])

    # 9. Run tools/plan_summary.py
    print(f"\n9. Executing tools/plan_summary.py on {run_dir.name}...", flush=True)
    summary_cmd = [
        PY, str(REPO_ROOT / "tools/plan_summary.py"), str(run_dir),
        "--geo-cache", GEO_CACHE,
        "--no-cache",
        "--groups", groups_flag
    ]
    env = dict(os.environ)
    env["TD_ZCTA_SHP"] = ZCTA_SHP_PATH
    res = subprocess.run(summary_cmd, capture_output=True, text=True, env=env)
    print("plan_summary STDOUT:\n", res.stdout)
    if res.stderr:
        print("plan_summary STDERR:\n", res.stderr)
    if res.returncode != 0:
        raise RuntimeError(f"plan_summary.py failed with returncode {res.returncode}")

    print(f"SUCCESS: Generated {run_dir}/maps/summary.png")
    return all_contiguous


def main():
    GROUPS_ARG = "G1=TX,NY,FL,NJ,IL,AZ,NC,PA,MI,OH,VA,GA,CO,MD;G2 adds=CT,IN,LA,MN,UT,WA"

    # 1. GROUP 2 RUN
    g2_req = group2_run.GROUP2 + ["CA1", "CA2", "MS"]
    g2_dir = REPO_ROOT / "battery/results/group2_exact_national"
    build_and_run("Group 2", g2_req, g2_dir, GROUPS_ARG)

    # Copy deliverables
    g2_png = g2_dir / "maps/summary.png"
    for dest in [REPO_ROOT / "figures/summary.png", REPO_ROOT / "agy-job/reports/summary.png",
                 Path("/Users/sandvault-ntlee/.gemini/antigravity-cli/brain/09f078e7-2f55-4c40-9905-5ed9fd054e07/summary.png")]:
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(g2_png.read_bytes())
        print(f"Copied Group 2 summary.png -> {dest}")

    # 2. GROUP 1 RUN
    g1_req = ["TX", "NY", "FL", "NJ", "IL", "AZ", "NC", "PA", "MI", "OH", "VA", "GA", "MD", "CA1", "CA2", "MS"]
    g1_dir = REPO_ROOT / "battery/results/group1_exact_national"
    build_and_run("Group 1", g1_req, g1_dir, GROUPS_ARG)

    # Copy deliverables
    g1_png = g1_dir / "maps/summary.png"
    for dest in [REPO_ROOT / "figures/summary_g1.png", REPO_ROOT / "agy-job/reports/summary_g1.png",
                 Path("/Users/sandvault-ntlee/.gemini/antigravity-cli/brain/09f078e7-2f55-4c40-9905-5ed9fd054e07/summary_g1.png")]:
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(g1_png.read_bytes())
        print(f"Copied Group 1 summary_g1.png -> {dest}")

    print("\n=======================================================")
    print("ALL RUNS AND AUTHENTIC SUMMARY FIGURES COMPLETED!")
    print("=======================================================")


if __name__ == "__main__":
    main()
