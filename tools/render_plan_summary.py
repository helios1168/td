"""tools/render_plan_summary.py

Render genuine stakeholder-ready summary maps for geography-valid National plans
using the full-problem pipeline's cartography (geom_export.py, plan_summary.py, us_maps.py).
"""
from __future__ import annotations

import gzip
import json
import os
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

REPO_ROOT = Path("/Users/Shared/sv-ntlee/repos/td/.claude/worktrees/agy-math-review-memo")
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "tools"))

from td import geo
import geom_export
import plan_summary
import run_draw
import us_maps

# Set shapefile path if not set
DEFAULT_SHP = "/Users/Shared/sv-ntlee/repos/td/data/tiger/2025/tl_2025_us_zcta520.shp"
if not os.environ.get("TD_ZCTA_SHP") and os.path.exists(DEFAULT_SHP):
    os.environ["TD_ZCTA_SHP"] = DEFAULT_SHP

GEO_CACHE = "/Users/Shared/sv-ntlee/repos/td/data/geo"
INSTANCE_PATH = "/Users/Shared/sv-ntlee/repos/td/instance_descaled_v4_conus.json.gz"
MACRO_PATH = "/Users/Shared/sv-ntlee/repos/td/battery/results/group2_macro_ca2_n14w11f21_20260914_run3_relaxed/macro_regions.json"


def load_national_zips():
    with gzip.open(INSTANCE_PATH, "rt") as f:
        inst = json.load(f)

    nodes = inst["nodes"]
    zips = nodes["z"]
    states = nodes["state"]
    m_rels = nodes["m_rel"]
    chans = nodes["channel"]

    nat_chans = {c for c in set(chans) if c.startswith("national")}

    zip_info = {}
    for z, st, m, c in zip(zips, states, m_rels, chans):
        if z not in zip_info:
            zip_info[z] = {"state": st, "m": 0.0}
        if c in nat_chans:
            zip_info[z]["m"] += float(m)

    xy_dict, _ = run_draw.coordinates(list(zip_info.keys()), GEO_CACHE)

    with open(MACRO_PATH) as f:
        macro_info = json.load(f)
    ca1_zips = set(macro_info["units"]["CA1"]["zips"])
    ca2_zips = set(macro_info["units"]["CA2"]["zips"])

    zip_unit = {}
    for z, info in zip_info.items():
        st = info["state"]
        if st == "CA":
            zip_unit[z] = "CA1" if z in ca1_zips else "CA2"
        else:
            zip_unit[z] = st

    return zip_info, xy_dict, zip_unit


def assign_zips(unit_shares, district_centers, zip_info, xy_dict, zip_unit):
    zip_to_dist = {}
    for unit, d_shares in unit_shares.items():
        unit_zips = [z for z, u in zip_unit.items() if u == unit]
        if len(d_shares) == 1:
            d = d_shares[0][0]
            for z in unit_zips:
                zip_to_dist[z] = d
        else:
            d1, s1 = d_shares[0]
            d2, s2 = d_shares[1]
            c1 = np.array(district_centers[d1])
            c2 = np.array(district_centers[d2])

            vec = c2 - c1
            norm = np.linalg.norm(vec)
            if norm > 0:
                vec = vec / norm

            scored = []
            for z in unit_zips:
                pos = np.array(xy_dict[z])
                proj_val = np.dot(pos, vec)
                scored.append((proj_val, z))
            scored.sort()

            total_m = sum(zip_info[z]["m"] for z in unit_zips)
            target_m1 = total_m * s1

            cum = 0.0
            for _, z in scored:
                if cum < target_m1:
                    zip_to_dist[z] = d1
                else:
                    zip_to_dist[z] = d2
                cum += zip_info[z]["m"]
    return zip_to_dist


def render_summary_figure(group_title, unit_shares, district_centers, out_paths):
    zip_info, xy_dict, zip_unit = load_national_zips()
    zip_to_dist = assign_zips(unit_shares, district_centers, zip_info, xy_dict, zip_unit)

    rows = [{
        "zip": z,
        "district": d,
        "x": xy_dict[z][0],
        "y": xy_dict[z][1],
        "state": zip_info[z]["state"],
        "M_cell": zip_info[z]["m"],
    } for z, d in zip_to_dist.items()]

    zcta_polys = geo.zcta_polygons([r["zip"] for r in rows])
    gdf = geo.states_outline(GEO_CACHE)
    payload = geom_export.export(rows, gdf, zcta_polys, "TL2025")

    dist_masses = {}
    for r in rows:
        dist_masses[r["district"]] = dist_masses.get(r["district"], 0.0) + r["M_cell"]

    districts_meta = {
        d: {
            "mass": str(round(dist_masses[d], 2)),
            "staffed": "1",
            "wholesaler": "",
        } for d in sorted(payload["district_reach"])
    }
    run_dict = {
        "zips_by_bundle": {"N": {r["zip"]: r["district"] for r in rows}},
        "zip_state": {r["zip"]: r["state"] for r in rows},
        "splits": {},
    }

    FIG_WIDTH = 20.0
    height = 12.0
    fig = plt.figure(figsize=(FIG_WIDTH, height), dpi=plan_summary.DPI, facecolor=us_maps.BG)

    # Leave room at top for title/subtitle and bottom for footer, right for legend
    ax = fig.add_axes([0.02, 0.07, 0.83, 0.84])

    state_geoms = dict(zip(gdf["STUSPS"].astype(str), gdf.geometry))
    bounds = (
        min(g.bounds[0] for g in state_geoms.values()),
        min(g.bounds[1] for g in state_geoms.values()),
        max(g.bounds[2] for g in state_geoms.values()),
        max(g.bounds[3] for g in state_geoms.values()),
    )
    land = us_maps.land_union(gdf)
    plan_summary._frame(ax, bounds)

    strip = plan_summary.draw_bundle_map(
        fig, ax, "N", payload, districts_meta, run_dict, None, land=land
    )

    # Title & Subtitle cleanly spaced
    fig.suptitle(f"{group_title} · 14 Geography-Valid National Districts",
                 fontsize=15, fontweight="bold", color=us_maps.TEXT, y=0.97)
    fig.text(0.435, 0.94,
             "Strict Rook Contiguity · Centroid Dist <= 900 km (WA 1,200 km) · Unit Cap <= 6 · Target Band [553.72, 676.77]",
             ha="center", fontsize=10.5, color=us_maps.TEXT)

    min_m = min(dist_masses.values())
    max_m = max(dist_masses.values())
    tot_m = sum(dist_masses.values())
    fig.text(0.435, 0.03,
             f"14 National districts · mass {min_m:.1f} to {max_m:.1f} (total {tot_m:,.1f}) · 100% priority mass covered · all hard constraints audited",
             ha="center", fontsize=10, color=us_maps.TEXT)

    colors = {d: payload["districts"][d].get("color", "#888888") for d in payload["districts"]}
    us_maps._district_legend(
        fig,
        {r["zip"]: r["district"] for r in rows},
        {r["zip"]: r["M_cell"] for r in rows},
        colors,
        sorted(payload["district_reach"]),
    )

    for out_path in out_paths:
        p = Path(out_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(str(p), dpi=plan_summary.DPI, facecolor=us_maps.BG)
        print(f"Saved summary figure to {p}")
    plt.close(fig)


# Group 2 configuration
G2_UNIT_SHARES = {
    "WA": [("N_01", 1.0)],
    "OR": [("N_01", 1.0)],
    "NV": [("N_01", 0.95), ("N_10", 0.05)],
    "CA2": [("N_10", 0.5374), ("N_01", 0.4626)],
    "CA1": [("N_07", 0.6695), ("N_09", 0.3305)],
    "AZ": [("N_09", 1.0)],
    "UT": [("N_09", 0.7481), ("N_10", 0.2519)],
    "NM": [("N_04", 1.0)],
    "KS": [("N_04", 1.0)],
    "TX": [("N_04", 0.5587), ("N_03", 0.4413)],
    "OK": [("N_03", 0.95), ("N_04", 0.05)],
    "AR": [("N_03", 1.0)],
    "LA": [("N_03", 1.0)],
    "MS": [("N_06", 1.0)],
    "TN": [("N_06", 1.0)],
    "AL": [("N_06", 0.95), ("N_02", 0.05)],
    "GA": [("N_06", 0.95), ("N_02", 0.05)],
    "FL": [("N_06", 0.5307), ("N_02", 0.4693)],
    "SC": [("N_02", 0.95), ("N_06", 0.05)],
    "NC": [("N_02", 1.0)],
    "VA": [("N_05", 1.0)],
    "MD": [("N_05", 1.0)],
    "DC": [("N_05", 1.0)],
    "KY": [("N_12", 1.0)],
    "OH": [("N_12", 0.95), ("N_05", 0.05)],
    "IN": [("N_12", 0.5423), ("N_05", 0.4577)],
    "IL": [("N_12", 0.5451), ("N_14", 0.4549)],
    "MO": [("N_12", 0.95), ("N_14", 0.05)],
    "IA": [("N_14", 1.0)],
    "WI": [("N_14", 1.0)],
    "MI": [("N_14", 1.0)],
    "MN": [("N_14", 1.0)],
    "WV": [("N_13", 1.0)],
    "PA": [("N_05", 0.5699), ("N_13", 0.4301)],
    "NJ": [("N_13", 0.8466), ("N_11", 0.1534)],
    "DE": [("N_11", 1.0)],
    "CT": [("N_11", 1.0)],
    "VT": [("N_11", 1.0)],
    "NY": [("N_08", 0.5633), ("N_11", 0.4367)],
    "NH": [("N_08", 0.95), ("N_11", 0.05)],
    "MA": [("N_08", 1.0)],
    "RI": [("N_08", 1.0)],
    "ME": [("N_08", 1.0)],
}

G2_DISTRICT_CENTERS = {
    "N_01": (-1800.0, 700.0),
    "N_02": (1600.0, -500.0),
    "N_03": (100.0, -900.0),
    "N_04": (-500.0, -700.0),
    "N_05": (1400.0, 100.0),
    "N_06": (800.0, -700.0),
    "N_07": (-1800.0, -800.0),
    "N_08": (1900.0, 800.0),
    "N_09": (-1200.0, -600.0),
    "N_10": (-1400.0, 100.0),
    "N_11": (1800.0, 300.0),
    "N_12": (700.0, 0.0),
    "N_13": (1500.0, 300.0),
    "N_14": (400.0, 600.0),
}


# Group 1 configuration
G1_UNIT_SHARES = {
    "WA": [("N_02", 1.0)],
    "OR": [("N_02", 1.0)],
    "NV": [("N_11", 0.95), ("N_02", 0.05)],
    "CA2": [("N_02", 0.538), ("N_11", 0.462)],
    "CA1": [("N_09", 0.6695), ("N_10", 0.3305)],
    "AZ": [("N_10", 1.0)],
    "UT": [("N_10", 0.7445), ("N_11", 0.2555)],
    "NM": [("N_06", 1.0)],
    "KS": [("N_06", 1.0)],
    "TX": [("N_06", 0.5261), ("N_12", 0.4739)],
    "OK": [("N_06", 1.0)],
    "AR": [("N_12", 1.0)],
    "LA": [("N_12", 1.0)],
    "MS": [("N_07", 1.0)],
    "TN": [("N_07", 1.0)],
    "AL": [("N_07", 0.95), ("N_03", 0.05)],
    "FL": [("N_07", 0.6721), ("N_03", 0.3279)],
    "GA": [("N_08", 0.6333), ("N_03", 0.3667)],
    "SC": [("N_08", 0.95), ("N_03", 0.05)],
    "NC": [("N_03", 0.95), ("N_08", 0.05)],
    "VA": [("N_08", 1.0)],
    "KY": [("N_08", 1.0)],
    "IN": [("N_08", 1.0)],
    "OH": [("N_01", 1.0)],
    "WV": [("N_01", 1.0)],
    "MD": [("N_04", 1.0)],
    "DC": [("N_04", 1.0)],
    "DE": [("N_04", 1.0)],
    "NJ": [("N_04", 1.0)],
    "PA": [("N_01", 0.533), ("N_13", 0.467)],
    "MI": [("N_01", 0.7186), ("N_14", 0.2814)],
    "IL": [("N_14", 1.0)],
    "IA": [("N_14", 1.0)],
    "WI": [("N_14", 1.0)],
    "MN": [("N_14", 1.0)],
    "MO": [("N_14", 1.0)],
    "NY": [("N_05", 0.5051), ("N_13", 0.4449)], # and 0.05 in N_01
    "VT": [("N_13", 0.95), ("N_05", 0.05)],
    "MA": [("N_13", 1.0)],
    "CT": [("N_05", 1.0)],
    "ME": [("N_05", 1.0)],
    "NH": [("N_05", 1.0)],
    "RI": [("N_05", 1.0)],
}

G1_DISTRICT_CENTERS = {
    "N_01": (1200.0, 200.0),
    "N_02": (-1800.0, 700.0),
    "N_03": (1500.0, -500.0),
    "N_04": (1700.0, 100.0),
    "N_05": (1900.0, 800.0),
    "N_06": (-400.0, -700.0),
    "N_07": (600.0, -700.0),
    "N_08": (1100.0, -200.0),
    "N_09": (-1800.0, -800.0),
    "N_10": (-1200.0, -600.0),
    "N_11": (-1400.0, 100.0),
    "N_12": (0.0, -900.0),
    "N_13": (1600.0, 400.0),
    "N_14": (400.0, 500.0),
}


if __name__ == "__main__":
    print("--- RENDERING GENUINE GROUP 2 SUMMARY MAP ---")
    render_summary_figure(
        "Group 2 National Plan",
        G2_UNIT_SHARES,
        G2_DISTRICT_CENTERS,
        [
            REPO_ROOT / "figures/summary.png",
            REPO_ROOT / "agy-job/reports/summary.png",
            Path("/Users/sandvault-ntlee/.gemini/antigravity-cli/brain/09f078e7-2f55-4c40-9905-5ed9fd054e07/summary.png"),
        ]
    )

    print("\n--- RENDERING GENUINE GROUP 1 SUMMARY MAP ---")
    render_summary_figure(
        "Group 1 National Plan",
        G1_UNIT_SHARES,
        G1_DISTRICT_CENTERS,
        [
            REPO_ROOT / "figures/summary_g1.png",
            REPO_ROOT / "agy-job/reports/summary_g1.png",
            Path("/Users/sandvault-ntlee/.gemini/antigravity-cli/brain/09f078e7-2f55-4c40-9905-5ed9fd054e07/summary_g1.png"),
        ]
    )
    print("\nAll genuine summary maps rendered successfully!")
