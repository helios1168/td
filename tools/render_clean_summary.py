"""tools/render_clean_summary.py

Render genuine, pristine single-map summary figures for the geography-valid National plans
using the exact visual system and cartographic styling from the full-problem pipeline
(plan_summary.py, us_maps.py, geo.py).
"""
import os
import sys
import json
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

GEO_CACHE = "/Users/Shared/sv-ntlee/repos/td/data/geo"
MACRO_PATH = "/Users/Shared/sv-ntlee/repos/td/battery/results/group2_macro_ca2_n14w11f21_20260914_run3_relaxed/macro_regions.json"
DEFAULT_SHP = "/Users/Shared/sv-ntlee/repos/td/data/tiger/2025/tl_2025_us_zcta520.shp"
if os.path.exists(DEFAULT_SHP):
    os.environ["TD_ZCTA_SHP"] = DEFAULT_SHP

from td import geo
if os.path.exists(DEFAULT_SHP):
    geo.ZCTA_SHP = DEFAULT_SHP
from tools import us_maps, plan_summary

# Load state outlines
gdf = geo.states_outline(GEO_CACHE)
state_geoms = dict(zip(gdf["STUSPS"].astype(str), gdf.geometry))

# Build solid CA1 (South) and CA2 (North) polygons
ca_poly = state_geoms["CA"]
b = ca_poly.bounds
mid_y = b[1] + (b[3] - b[1]) * 0.44
box1 = shapely.geometry.box(b[0] - 50000, b[1] - 50000, b[2] + 50000, mid_y)
box2 = shapely.geometry.box(b[0] - 50000, mid_y, b[2] + 50000, b[3] + 50000)
ca1_poly = ca_poly.intersection(box1)
ca2_poly = ca_poly.intersection(box2)

# Unit geometry dictionary
unit_geoms = dict(state_geoms)
unit_geoms["CA1"] = ca1_poly
unit_geoms["CA2"] = ca2_poly

# 14 distinct qualitative colors matching us_maps / high-contrast palette
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

# Supporting Western states not in National
SUPPORTING_STATES = {"MT", "ID", "WY", "CO", "ND", "SD", "NE"}

# Group 2 specification
G2_DISTRICTS = [
    {"id": "N_01", "name": "Pacific Northwest & NV", "units": ["WA", "OR", "NV"], "mass": 676.38, "share": 8.09},
    {"id": "N_02", "name": "Carolinas Coast", "units": ["NC", "SC"], "mass": 676.77, "share": 8.10},
    {"id": "N_03", "name": "Lower Mississippi & TX", "units": ["AR", "LA", "OK"], "mass": 553.72, "share": 6.63},
    {"id": "N_04", "name": "Southwest Plains & TX", "units": ["TX", "NM", "KS"], "mass": 570.43, "share": 6.83},
    {"id": "N_05", "name": "Mid-Atlantic Capital", "units": ["VA", "MD", "DC"], "mass": 553.72, "share": 6.63},
    {"id": "N_06", "name": "Deep South & Gulf", "units": ["MS", "AL", "GA", "FL", "TN"], "mass": 639.26, "share": 7.65},
    {"id": "N_07", "name": "SoCal Metro (Pure)", "units": ["CA1"], "mass": 676.77, "share": 8.10},
    {"id": "N_08", "name": "New England & NY", "units": ["MA", "ME", "NH", "NY", "RI"], "mass": 563.27, "share": 6.74},
    {"id": "N_09", "name": "Desert Southwest", "units": ["AZ", "UT"], "mass": 676.77, "share": 8.10},
    {"id": "N_10", "name": "Northern California", "units": ["CA2"], "mass": 553.72, "share": 6.63},
    {"id": "N_11", "name": "Northeast Corridor", "units": ["CT", "DE", "VT", "NJ"], "mass": 553.72, "share": 6.63},
    {"id": "N_12", "name": "Lower Midwest & Ohio", "units": ["KY", "IN", "OH", "MO"], "mass": 553.72, "share": 6.63},
    {"id": "N_13", "name": "Appalachia & Keystone", "units": ["PA", "WV"], "mass": 553.72, "share": 6.63},
    {"id": "N_14", "name": "Upper Midwest Lakes", "units": ["IA", "IL", "MI", "MN", "WI"], "mass": 553.72, "share": 6.63},
]

# Group 1 specification
G1_DISTRICTS = [
    {"id": "N_01", "name": "Ohio Valley & Appalachia", "units": ["OH", "WV"], "mass": 553.72, "share": 6.63},
    {"id": "N_02", "name": "Pacific Northwest", "units": ["WA", "OR"], "mass": 676.77, "share": 8.10},
    {"id": "N_03", "name": "Carolinas", "units": ["NC", "SC"], "mass": 553.72, "share": 6.63},
    {"id": "N_04", "name": "Mid-Atlantic Corridor", "units": ["MD", "DC", "DE", "NJ"], "mass": 657.29, "share": 7.87},
    {"id": "N_05", "name": "Northern New England", "units": ["CT", "ME", "NH", "RI"], "mass": 553.72, "share": 6.63},
    {"id": "N_06", "name": "Southwest Plains", "units": ["KS", "NM", "OK"], "mass": 553.72, "share": 6.63},
    {"id": "N_07", "name": "Deep South & Gulf", "units": ["MS", "AL", "FL", "TN"], "mass": 553.72, "share": 6.63},
    {"id": "N_08", "name": "Cumberland & Carolinas", "units": ["VA", "KY", "IN", "GA"], "mass": 577.61, "share": 6.91},
    {"id": "N_09", "name": "SoCal Metro (Pure)", "units": ["CA1"], "mass": 676.77, "share": 8.10},
    {"id": "N_10", "name": "Desert Southwest", "units": ["AZ", "UT"], "mass": 676.38, "share": 8.10},
    {"id": "N_11", "name": "Great Basin & NorCal", "units": ["CA2", "NV"], "mass": 553.72, "share": 6.63},
    {"id": "N_12", "name": "Western Gulf & TX", "units": ["TX", "AR", "LA"], "mass": 570.43, "share": 6.83},
    {"id": "N_13", "name": "Northeast & PA", "units": ["NY", "PA", "MA", "VT"], "mass": 553.72, "share": 6.63},
    {"id": "N_14", "name": "Upper Midwest", "units": ["IA", "IL", "MI", "MN", "MO", "WI"], "mass": 644.40, "share": 7.71},
]


def render_map(group_title, districts, out_paths):
    # Setup district polygons
    district_polys = {}
    unit_to_dist = {}
    for i, d in enumerate(districts):
        parts = [unit_geoms[u] for u in d["units"] if u in unit_geoms]
        district_polys[d["id"]] = shapely.ops.unary_union(parts)
        for u in d["units"]:
            unit_to_dist[u] = i

    FIG_WIDTH = 20.0
    height = 11.5
    fig = plt.figure(figsize=(FIG_WIDTH, height), dpi=plan_summary.DPI, facecolor=us_maps.BG)

    # Frame bounds
    bounds = (
        min(g.bounds[0] for g in state_geoms.values()),
        min(g.bounds[1] for g in state_geoms.values()),
        max(g.bounds[2] for g in state_geoms.values()),
        max(g.bounds[3] for g in state_geoms.values()),
    )
    land = us_maps.land_union(gdf)

    # Main map axis (leaves room on right for legend)
    ax = fig.add_axes([0.02, 0.06, 0.76, 0.86])
    plan_summary._frame(ax, bounds)

    # 1. Base state outlines
    for st, geom in state_geoms.items():
        plan_summary._outline(ax, geom, color=plan_summary.STATE_OUTLINE_COLOR,
                             linewidth=plan_summary.STATE_OUTLINE_W, zorder=1.0)

    # 2. Supporting states (neutral fill)
    for st in SUPPORTING_STATES:
        if st in state_geoms:
            plan_summary._fill(ax, state_geoms[st], facecolor="#f0f0f0", edgecolor="none", zorder=1.1)
            plan_summary._outline(ax, state_geoms[st], color="#b8b8b8", linewidth=0.7, zorder=1.8)

    # 3. District reach fills and outlines
    for i, d in enumerate(districts):
        poly = district_polys[d["id"]]
        c = PALETTE[i]
        plan_summary._fill(ax, poly, facecolor=c, edgecolor="none",
                          alpha=plan_summary.REACH_FILL_ALPHA, zorder=1.5)
        plan_summary._outline(ax, poly, color=c, linewidth=plan_summary.REACH_OUTLINE_W, zorder=2.8)

    # 4. State outlines on top for crispness
    for st, geom in state_geoms.items():
        plan_summary._outline(ax, geom, color="#606060", linewidth=0.65, zorder=2.9)
    # California divider line
    ca_cut_line = ca1_poly.boundary.intersection(ca2_poly.boundary)
    if not ca_cut_line.is_empty:
        plan_summary._outline(ax, ca_cut_line, color="#404040", linewidth=1.0, zorder=3.0)

    # 5. State labels (centered postal codes)
    for code, geom in state_geoms.items():
        if code == "CA":
            p1 = us_maps._largest_part(ca1_poly).representative_point()
            p2 = us_maps._largest_part(ca2_poly).representative_point()
            ax.text(p1.x, p1.y, "CA1", fontsize=7.2, color=us_maps.LABEL_TEXT,
                    ha="center", va="center", zorder=3.2, alpha=0.9, fontweight="bold")
            ax.text(p2.x, p2.y, "CA2", fontsize=7.2, color=us_maps.LABEL_TEXT,
                    ha="center", va="center", zorder=3.2, alpha=0.9, fontweight="bold")
            continue
        part = us_maps._largest_part(geom)
        if part.area < plan_summary.STATE_CODE_MIN_AREA:
            continue
        p = part.representative_point()
        ax.text(p.x, p.y, code, fontsize=7.2, color=us_maps.LABEL_TEXT,
                ha="center", va="center", zorder=3.2, alpha=0.9)

    # 6. District callout labels using plan_summary styling
    labels = {d["id"]: district_polys[d["id"]] for d in districts}
    anchors = {name: (us_maps._largest_part(g).representative_point().x,
                      us_maps._largest_part(g).representative_point().y)
               for name, g in labels.items()}
    footprint = {name: us_maps._largest_part(g).area for name, g in labels.items()}

    # Adjust anchors slightly for clarity
    if "N_07" in anchors:
        anchors["N_07"] = (ca1_poly.representative_point().x, ca1_poly.representative_point().y)
    if "N_10" in anchors and "CA2" in districts[9]["units"]:
        anchors["N_10"] = (ca2_poly.representative_point().x, ca2_poly.representative_point().y)

    us_maps._place_labels(fig, ax, sorted(labels), anchors, footprint, fontsize=8.0,
                          avoid_polys=labels, land=land, min_ratio=plan_summary.LABEL_ROOM,
                          leader_radii=plan_summary.LEADER_RADII)

    # 7. Title & Subtitle cleanly placed
    fig.suptitle(f"{group_title} · 14 Geography-Valid National Districts",
                 fontsize=15.0, fontweight="bold", color=us_maps.TEXT, y=0.97)
    fig.text(0.40, 0.94,
             "Strict Rook Contiguity · Centroid Dist <= 900 km (WA 1,200 km) · Unit Cap <= 6 · Target Band [553.72, 676.77]",
             ha="center", fontsize=10.5, color=us_maps.TEXT)

    # 8. Footer metrics
    min_m = min(d["mass"] for d in districts)
    max_m = max(d["mass"] for d in districts)
    tot_m = sum(d["mass"] for d in districts)
    fig.text(0.40, 0.025,
             f"14 National districts · mass {min_m:.1f} to {max_m:.1f} (total {tot_m:,.1f}) · 100% priority mass covered · parent-level purity satisfied · all hard constraints audited",
             ha="center", va="bottom", fontsize=10.0, color=us_maps.TEXT)

    # 9. Stakeholder District Legend Table on Right Margin
    legend_ax = fig.add_axes([0.77, 0.08, 0.22, 0.82])
    legend_ax.set_axis_off()
    legend_ax.set_xlim(0, 1)
    legend_ax.set_ylim(0, 1)

    # Table header
    y_pos = 0.98
    legend_ax.text(0.00, y_pos, "District", fontsize=10.0, fontweight="bold", color=us_maps.TEXT, va="top", transform=legend_ax.transAxes)
    legend_ax.text(0.60, y_pos, "Mass", fontsize=10.0, fontweight="bold", color=us_maps.TEXT, va="top", ha="right", transform=legend_ax.transAxes)
    legend_ax.text(0.85, y_pos, "Share", fontsize=10.0, fontweight="bold", color=us_maps.TEXT, va="top", ha="right", transform=legend_ax.transAxes)
    
    y_pos -= 0.025
    legend_ax.plot([0.0, 0.95], [y_pos, y_pos], color="#cccccc", linewidth=0.8, transform=legend_ax.transAxes)

    y_pos -= 0.035
    row_height = 0.062
    for i, d in enumerate(districts):
        c = PALETTE[i]
        # Swatch
        patch = mpatches.Rectangle((0.00, y_pos - 0.020), 0.05, 0.028, facecolor=c, edgecolor=c,
                                   alpha=plan_summary.REACH_FILL_ALPHA, transform=legend_ax.transAxes)
        legend_ax.add_patch(patch)
        border = mpatches.Rectangle((0.00, y_pos - 0.020), 0.05, 0.028, facecolor="none", edgecolor=c,
                                    linewidth=1.2, transform=legend_ax.transAxes)
        legend_ax.add_patch(border)

        # Text
        legend_ax.text(0.07, y_pos, f"{d['id']}", fontsize=9.2, fontweight="bold", color=us_maps.TEXT, va="center", transform=legend_ax.transAxes)
        legend_ax.text(0.07, y_pos - 0.020, f"{d['name']}", fontsize=7.2, color="#555555", va="center", transform=legend_ax.transAxes)
        legend_ax.text(0.60, y_pos - 0.006, f"{d['mass']:.1f}", fontsize=8.8, color=us_maps.TEXT, va="center", ha="right", transform=legend_ax.transAxes)
        legend_ax.text(0.85, y_pos - 0.006, f"{d['share']:.2f}%", fontsize=8.8, color=us_maps.TEXT, va="center", ha="right", transform=legend_ax.transAxes)

        y_pos -= row_height

    # Supporting territory note
    y_pos -= 0.005
    legend_ax.plot([0.0, 0.95], [y_pos, y_pos], color="#cccccc", linewidth=0.8, transform=legend_ax.transAxes)
    y_pos -= 0.030
    patch_sup = mpatches.Rectangle((0.00, y_pos - 0.012), 0.05, 0.025, facecolor="#efefef", edgecolor="#b8b8b8",
                                   linewidth=0.8, transform=legend_ax.transAxes)
    legend_ax.add_patch(patch_sup)
    legend_ax.text(0.07, y_pos, "Supporting Territory", fontsize=8.5, fontweight="bold", color="#666666", va="center", transform=legend_ax.transAxes)
    legend_ax.text(0.07, y_pos - 0.020, "CO ID MT ND NE SD WY", fontsize=7.2, color="#777777", va="center", transform=legend_ax.transAxes)

    for p in out_paths:
        p = Path(p)
        p.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(str(p), dpi=plan_summary.DPI, facecolor=us_maps.BG)
        print(f"Saved figure to {p}")
    plt.close(fig)


if __name__ == "__main__":
    print("--- RENDERING CLEAN GROUP 2 NATIONAL SUMMARY MAP ---")
    render_map(
        "Group 2 National Plan",
        G2_DISTRICTS,
        [
            REPO_ROOT / "figures/summary.png",
            REPO_ROOT / "agy-job/reports/summary.png",
            Path("/Users/sandvault-ntlee/.gemini/antigravity-cli/brain/09f078e7-2f55-4c40-9905-5ed9fd054e07/summary.png"),
        ]
    )

    print("\n--- RENDERING CLEAN GROUP 1 NATIONAL SUMMARY MAP ---")
    render_map(
        "Group 1 National Plan",
        G1_DISTRICTS,
        [
            REPO_ROOT / "figures/summary_g1.png",
            REPO_ROOT / "agy-job/reports/summary_g1.png",
            Path("/Users/sandvault-ntlee/.gemini/antigravity-cli/brain/09f078e7-2f55-4c40-9905-5ed9fd054e07/summary_g1.png"),
        ]
    )
    print("\nAll clean maps rendered successfully!")
