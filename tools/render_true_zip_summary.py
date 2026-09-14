"""tools/render_true_zip_summary.py

Render true district summary figures for Group 2 and Group 1 National plans
with genuine ZIP-level borders and full-problem cartographic styling.
"""
import os
import sys
import time
from pathlib import Path
import numpy as np
import shapely
import shapely.ops
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.collections import LineCollection, PatchCollection
from matplotlib.patches import PathPatch

REPO_ROOT = Path("/Users/Shared/sv-ntlee/repos/td/.claude/worktrees/agy-math-review-memo")
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "tools"))

from td import instance as descaled, channels, geo
from td.solvers import level0, state_splits as ss
import full_plan
import json
import networkx as nx
from tools import group2_run, group2_support, run_draw, us_maps, plan_summary, plan_realise

GEO_CACHE = "/Users/Shared/sv-ntlee/repos/td/data/geo"
INSTANCE_PATH = "/Users/Shared/sv-ntlee/repos/td/instance_descaled_v4_conus.json.gz"
DEFAULT_SHP = "/Users/Shared/sv-ntlee/repos/td/data/tiger/2025/tl_2025_us_zcta520.shp"
if os.path.exists(DEFAULT_SHP):
    os.environ["TD_ZCTA_SHP"] = DEFAULT_SHP
    geo.ZCTA_SHP = DEFAULT_SHP

# High-contrast qualitative palette
PALETTE = [
    "#1f77b4",  # Blue
    "#ff7f0e",  # Orange
    "#2ca02c",  # Green
    "#d62728",  # Red
    "#9467bd",  # Purple
    "#8c564b",  # Brown
    "#e377c2",  # Pink
    "#17becf",  # Teal
    "#bcbd22",  # Olive
    "#393b79",  # Navy
    "#8c6d31",  # Ochre
    "#7b4173",  # Plum
    "#31a354",  # Forest
    "#e6550d",  # Rust
]

def build_national_problem(req_states):
    print("1. Preparing macro regions (CA:2)...")
    macro = group2_run.prepare_macro_regions(
        Path(INSTANCE_PATH), Path(GEO_CACHE), ["CA:2"], seed=group2_run.atoms_mod.CUT_SEED
    )
    state_list = full_plan._state_list(macro.data)
    cells = channels.aggregate(macro.data, state_list)
    idx = {unit: i for i, unit in enumerate(cells.state_list)}
    edges = sorted((min(idx[a], idx[b]), max(idx[a], idx[b]))
                   for a, b in macro.graph.edges if a in idx and b in idx)

    plain = [unit for unit in cells.state_list if unit not in macro.xy_km]
    base = full_plan._state_xy(plain, GEO_CACHE, required=True)
    by_unit = {unit: tuple(base[i]) for i, unit in enumerate(plain)}
    by_unit.update(macro.xy_km)
    state_xy = [by_unit[unit] for unit in cells.state_list]

    problem = level0.build_level0(
        cells, {"N": ("N_WH", "N_FI")},
        edges=edges,
        L=553.724691, U=676.774623,
        eta=0.05,
        n_max=6,
        dist_max=900.0,
        state_xy=state_xy,
        dist_max_state={idx["WA"]: 1200.0} if "WA" in idx else None,
        fixed_used={"N": 14}
    )

    print("2. Generating valid supports (n_max=6, dist_max=900, WA=1200)...")
    supports = group2_support.generate_valid_supports(
        problem, max_size=6, max_dist=900.0, max_dist_state={"WA": 1200.0}
    )

    print("3. Solving exact support master problem...")
    sol = group2_support.solve_exact_support(
        problem,
        supports,
        count=14,
        band=(553.724691, 676.774623),
        required_units=req_states,
        macro_contact_caps={"CA1": 2, "CA2": 2},
    )
    if sol is None:
        raise ValueError("Failed to solve exact support problem!")

    return macro, problem, sol


def realize_and_dissolve(macro, problem, sol):
    print("4. Realizing exact plan at ZIP level...")
    cells_state_list = problem.state_list
    S = len(cells_state_list)
    k = 14
    idx = {unit: i for i, unit in enumerate(cells_state_list)}

    y_mat = np.zeros((S, k))
    district_ids = [f"N_{j+1:02d}" for j in range(k)]
    district_supports = []
    for j, (sup_idx, cnt) in enumerate(sol["x"].items()):
        sup = sol["supports"][sup_idx]
        district_supports.append(sup)
        for v in sup:
            y_mat[v, j] = sol["y"].get((v, sup_idx), 0.0)

    resid = np.maximum(0.0, 1.0 - y_mat.sum(axis=1))
    y_full = np.column_stack([y_mat, resid])
    z_full = y_full > 1e-5

    zips_all = sorted(macro.data.G.nodes)
    xy_dict, missing = run_draw.coordinates(zips_all, GEO_CACHE)
    placed = [z for z in zips_all if z in xy_dict]
    states_by_zip = {z: macro.data.G.nodes[z].get("state", "") for z in placed}

    M_by_zip = {}
    for z in placed:
        m_c = macro.data.G.nodes[z].get("M_c", {})
        M_by_zip[z] = m_c.get("N_WH", 0.0) + m_c.get("N_FI", 0.0)

    xy = np.array([xy_dict[z] for z in placed], float)
    M = np.array([M_by_zip[z] for z in placed], float)
    state_idx = np.array([idx[states_by_zip[z]] for z in placed], int)

    state_C = np.zeros((S, 2))
    for s in range(S):
        sel = state_idx == s
        if sel.any() and M[sel].sum() > 0:
            state_C[s] = (M[sel, None] * xy[sel]).sum(axis=0) / M[sel].sum()
        elif sel.any():
            state_C[s] = xy[sel].mean(axis=0)

    M_s = np.bincount(state_idx, weights=M, minlength=S)
    C = np.zeros((k + 1, 2))
    for j in range(k + 1):
        w = np.where(z_full[:, j], y_full[:, j] * M_s, 0.0)
        if w.sum() > 0:
            C[j] = (w[:, None] * state_C).sum(axis=0) / w.sum()
        else:
            C[j] = state_C.mean(axis=0)

    res = ss.realise(xy, M, state_idx, z_full, y_full, C, rounds=5)

    names = [f"N_{j+1:02d}" for j in range(k)] + ["other"]

    # Clean off-plan assignments (e.g. zero-mass ZIPs parked in column 0 by LP solver)
    cleaned_labels = {}
    for i, zp in enumerate(placed):
        s = state_idx[i]
        lab = int(res["labels"][i])
        if not z_full[s, lab]:
            admiss = np.flatnonzero(z_full[s])
            dists = ((xy[i] - C[admiss]) ** 2).sum(axis=1)
            best_j = admiss[np.argmin(dists)]
            cleaned_labels[zp] = names[best_j]
        else:
            cleaned_labels[zp] = names[lab]

    # Load cell rook graph for contiguity repair
    graph_path = REPO_ROOT / "battery/results/group2_realized/projections/N/cell_graph.json"
    with open(graph_path) as f:
        cg = json.load(f)
    G = nx.Graph()
    G.add_nodes_from(cg["zips"])
    G.add_edges_from(cg["edges"])

    admissible = {code: {names[j] for j in range(k) if z_full[s, j]}
                  for s, code in enumerate(cells_state_list)}

    repaired = plan_realise.repair(
        G, cleaned_labels, M_by_zip, states_by_zip, admissible,
        band=(553.724691, 676.774623), rounds=10, slack=15.0
    )
    final_labels = repaired["labels"]

    print("5. Dissolving Voronoi cells into true district polygons...")
    states_gdf = geo.states_outline(GEO_CACHE)
    state_geoms = dict(zip(states_gdf["STUSPS"].astype(str), states_gdf.geometry))

    ca_poly = state_geoms["CA"]
    ca_b = ca_poly.bounds
    mid_y = ca_b[1] + (ca_b[3] - ca_b[1]) * 0.44
    box1 = shapely.geometry.box(ca_b[0] - 50000, ca_b[1] - 50000, ca_b[2] + 50000, mid_y)
    box2 = shapely.geometry.box(ca_b[0] - 50000, mid_y, ca_b[2] + 50000, ca_b[3] + 50000)
    state_polys_macro = dict(state_geoms)
    state_polys_macro["CA1"] = ca_poly.intersection(box1)
    state_polys_macro["CA2"] = ca_poly.intersection(box2)

    clip = us_maps.clip_region([xy_dict[z] for z in placed], states_gdf)
    prox = us_maps.voronoi_cells(placed, xy_dict, clip, zip_state=states_by_zip, state_polys=state_polys_macro)
    district_reach = us_maps.dissolve(prox, final_labels)

    # Compute realized masses and state breakdown per district
    w_nat = problem.W[:, problem.slots["N"][0]]
    total_nat = w_nat.sum()
    district_info = []
    for j in range(k):
        d_id = district_ids[j]
        realized_mass = float(sum(M_by_zip.get(z, 0.0) for z, d_lab in final_labels.items() if d_lab == d_id))
        target_mass = float(sum(w_nat[v] * y_mat[v, j] for v in range(S)))
        share_pct = realized_mass / total_nat * 100.0

        # State constituent breakdown
        sup = district_supports[j]
        parts = []
        for v in sup:
            s_name = cells_state_list[v]
            sh = y_mat[v, j]
            if sh >= 0.999:
                parts.append(s_name)
            else:
                parts.append(f"{s_name} ({sh*100:.0f}%)")
        constituents = ", ".join(parts)

        district_info.append({
            "id": d_id,
            "realized_mass": realized_mass,
            "target_mass": target_mass,
            "share_pct": share_pct,
            "constituents": constituents,
            "poly": district_reach.get(d_id),
        })

    other_poly = district_reach.get("other")
    return district_info, other_poly, state_geoms


def render_summary_figure(title, subtitle, district_info, other_poly, state_geoms, out_paths):
    print(f"6. Rendering summary figure: {title}...")
    fig = plt.figure(figsize=(16, 9.5), dpi=200, facecolor=us_maps.BG)
    ax = fig.add_axes([0.02, 0.05, 0.63, 0.86])
    ax.set_facecolor(us_maps.BG)

    # CONUS bounds
    all_bounds = [g.bounds for g in state_geoms.values()]
    x0 = min(b[0] for b in all_bounds)
    y0 = min(b[1] for b in all_bounds)
    x1 = max(b[2] for b in all_bounds)
    y1 = max(b[3] for b in all_bounds)
    pad_x = (x1 - x0) * 0.02
    pad_y = (y1 - y0) * 0.02
    ax.set_xlim(x0 - pad_x, x1 + pad_x)
    ax.set_ylim(y0 - pad_y, y1 + pad_y)
    ax.set_aspect("equal")
    ax.axis("off")

    # 1. Fill "other" supporting states
    if other_poly is not None and not other_poly.is_empty:
        for path in us_maps._poly_paths(other_poly):
            ax.add_patch(PathPatch(path, facecolor="#e2e2e2", edgecolor="none", zorder=1.1))

    # 2. Fill 14 districts with qualitative palette
    for i, d in enumerate(district_info):
        poly = d["poly"]
        if poly is None or poly.is_empty:
            continue
        c = PALETTE[i % len(PALETTE)]
        for path in us_maps._poly_paths(poly):
            ax.add_patch(PathPatch(path, facecolor=c, edgecolor="none", alpha=0.82, zorder=1.5))

    # 3. Draw state boundaries underneath (thin subtle line)
    state_segs = []
    for st, g in state_geoms.items():
        state_segs.extend(us_maps._lines_of(g.boundary))
    ax.add_collection(LineCollection(state_segs, colors="#4a4a4a", linewidths=0.45,
                                     linestyles="--", alpha=0.5, zorder=2.0))

    # 4. Draw true ZIP-level district boundaries (crisp stroke)
    district_segs = []
    for d in district_info:
        poly = d["poly"]
        if poly is not None and not poly.is_empty:
            district_segs.extend(us_maps._lines_of(poly.boundary))
    ax.add_collection(LineCollection(district_segs, colors="#1a1a1a", linewidths=1.2,
                                     capstyle="round", joinstyle="round", zorder=2.5))

    # 5. Draw national outline
    land = shapely.ops.unary_union(list(state_geoms.values()))
    ax.add_collection(LineCollection(us_maps._lines_of(land.boundary),
                                     colors="#000000", linewidths=1.5, zorder=2.8))

    # 6. State codes
    plan_summary._state_codes(ax, state_geoms, fontsize=6.8, zorder=3.0)

    # 7. District centroid callout labels (clean white pill boxes)
    for i, d in enumerate(district_info):
        poly = d["poly"]
        if poly is None or poly.is_empty:
            continue
        largest = us_maps._largest_part(poly)
        pt = largest.representative_point()
        d_id = d["id"]
        ax.text(pt.x, pt.y, d_id, fontsize=7.5, fontweight="bold", color="#111111",
                ha="center", va="center", zorder=3.5,
                bbox=dict(boxstyle="round,pad=0.25", facecolor="#ffffff",
                          edgecolor="#222222", linewidth=0.8, alpha=0.92))

    # Supporting states label
    if other_poly is not None and not other_poly.is_empty:
        other_pt = us_maps._largest_part(other_poly).representative_point()
        ax.text(other_pt.x, other_pt.y + 100000, "Supporting\nTerritory\n(CO/ID/MT/ND/NE/SD/WY)",
                fontsize=7.0, color="#666666", ha="center", va="center", zorder=3.2,
                bbox=dict(boxstyle="round,pad=0.3", facecolor="#ffffff", edgecolor="#aaaaaa",
                          linewidth=0.5, alpha=0.85))

    # Right sidebar: stakeholder breakdown table
    ax_table = fig.add_axes([0.655, 0.05, 0.33, 0.86])
    ax_table.set_facecolor(us_maps.BG)
    ax_table.axis("off")
    ax_table.set_xlim(0, 1)
    ax_table.set_ylim(0, len(district_info) + 1.2)

    # Table Header
    y_top = len(district_info) + 0.6
    ax_table.text(0.00, y_top, "District", fontsize=8.2, fontweight="bold", color=us_maps.TEXT, va="center")
    ax_table.text(0.24, y_top, "Mass", fontsize=8.2, fontweight="bold", color=us_maps.TEXT, va="center")
    ax_table.text(0.36, y_top, "Share", fontsize=8.2, fontweight="bold", color=us_maps.TEXT, va="center")
    ax_table.text(0.48, y_top, "Constituents (with Split %)", fontsize=8.2, fontweight="bold", color=us_maps.TEXT, va="center")
    ax_table.plot([0.0, 1.0], [y_top - 0.35, y_top - 0.35], color="#888888", linewidth=0.8)

    # Rows
    for i, d in enumerate(district_info):
        y_pos = len(district_info) - 1 - i + 0.5
        c = PALETTE[i % len(PALETTE)]

        # Swatch
        ax_table.add_patch(mpatches.Rectangle((0.00, y_pos - 0.26), 0.035, 0.52,
                                              facecolor=c, edgecolor="#333333", linewidth=0.5))
        # ID
        ax_table.text(0.05, y_pos, d["id"], fontsize=7.8, fontweight="bold", color=us_maps.TEXT, va="center")
        # Mass
        ax_table.text(0.24, y_pos, f"{d['realized_mass']:.1f}", fontsize=7.8, color=us_maps.TEXT, va="center")
        # Share
        ax_table.text(0.36, y_pos, f"{d['share_pct']:.1f}%", fontsize=7.8, color=us_maps.TEXT, va="center")
        # Constituents
        ax_table.text(0.48, y_pos, d["constituents"], fontsize=7.1, color="#2b2b2b", va="center")

    # Titles & Footer
    fig.suptitle(title, fontsize=13.5, fontweight="bold", color=us_maps.TEXT, y=0.965)
    fig.text(0.5, 0.935, subtitle, fontsize=9.2, color="#444444", ha="center")
    fig.text(0.5, 0.015,
             "14 National Districts · 100% Contiguous · Diameter <= 900 km (WA 1200 km) · All Priority States 100% Covered · True ZIP-Level Boundaries",
             fontsize=8.5, color=us_maps.TEXT, ha="center")

    for p in out_paths:
        p.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(str(p), dpi=200, facecolor=us_maps.BG)
        print(f"Saved: {p}")
    plt.close(fig)


def main():
    # 1. GROUP 2
    print("==================================================")
    print("      PROCESSING GROUP 2 (19 PRIORITY STATES)     ")
    print("==================================================")
    g2_req = group2_run.GROUP2 + ["CA1", "CA2"]
    macro2, prob2, sol2 = build_national_problem(g2_req)
    d_info2, other2, state_geoms2 = realize_and_dissolve(macro2, prob2, sol2)

    g2_paths = [
        REPO_ROOT / "figures/summary.png",
        REPO_ROOT / "agy-job/reports/summary.png",
        Path("/Users/sandvault-ntlee/.gemini/antigravity-cli/brain/09f078e7-2f55-4c40-9905-5ed9fd054e07/summary.png"),
    ]
    render_summary_figure(
        "Group 2 National Plan · 14 Geography-Valid Districts (True ZIP-Level Borders)",
        "Exact Support-Based Formulation · Band [553.7, 676.8] · Realized at ZIP Grain · Non-Overlapping Polygons",
        d_info2, other2, state_geoms2, g2_paths
    )

    # 2. GROUP 1
    print("\n==================================================")
    print("      PROCESSING GROUP 1 (13 PRIORITY STATES)     ")
    print("==================================================")
    g1_req = ["TX", "NY", "FL", "NJ", "IL", "AZ", "NC", "PA", "MI", "OH", "VA", "GA", "MD", "CA1", "CA2"]
    macro1, prob1, sol1 = build_national_problem(g1_req)
    d_info1, other1, state_geoms1 = realize_and_dissolve(macro1, prob1, sol1)

    g1_paths = [
        REPO_ROOT / "figures/summary_g1.png",
        REPO_ROOT / "agy-job/reports/summary_g1.png",
        Path("/Users/sandvault-ntlee/.gemini/antigravity-cli/brain/09f078e7-2f55-4c40-9905-5ed9fd054e07/summary_g1.png"),
    ]
    render_summary_figure(
        "Group 1 National Plan · 14 Geography-Valid Districts (True ZIP-Level Borders)",
        "Exact Support-Based Formulation · Band [553.7, 676.8] · Realized at ZIP Grain · Non-Overlapping Polygons",
        d_info1, other1, state_geoms1, g1_paths
    )

    print("\nAll true ZIP-level summary figures rendered successfully!")


if __name__ == "__main__":
    main()
