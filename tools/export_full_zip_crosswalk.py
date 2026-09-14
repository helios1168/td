"""tools/export_full_zip_crosswalk.py
Generate complete nationwide ZCTA-to-district crosswalks across all 33,791 US Census ZCTAs.
Fills every rural, unpopulated, or zero-opportunity ZIP code using the exact district_reach boundaries,
so Tableau renders 100% solid, contiguous maps with zero holes, zero Swiss-cheese, and clean border splits.
"""
import csv
import json
import os
import sys
from pathlib import Path

import geopandas as gpd
import pandas as pd
from shapely.geometry import Point

REPO_ROOT = Path("/Users/Shared/sv-ntlee/repos/td/.claude/worktrees/agy-math-review-memo")
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "tools"))

from td import geo
from tools.plan_summary import (
    PATTERNS, PATTERN_FILL, PATTERN_TEXT,
    state_patterns, wholesaler_counts, load_assignment, display_id
)

OUT_DIR = REPO_ROOT / "exports/tableau"
BRAIN_DIR = Path("/Users/sandvault-ntlee/.gemini/antigravity-cli/brain/09f078e7-2f55-4c40-9905-5ed9fd054e07")
ZCTA_SHP = Path("/Users/Shared/sv-ntlee/repos/td/data/tiger/2025/tl_2025_us_zcta520.shp")


def generate_crosswalk_for_scenario(run_dir: Path, scenario_id: str):
    print(f"\n--- Generating Complete ZCTA Crosswalk for {scenario_id} ---")
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Load all 33,791 Census ZCTAs
    print("Loading US Census 2025 ZCTA geometry...")
    gdf_zcta = gpd.read_file(ZCTA_SHP, columns=["ZCTA5CE20", "INTPTLAT20", "INTPTLON20"])
    gdf_zcta["lat"] = gdf_zcta["INTPTLAT20"].astype(float)
    gdf_zcta["lon"] = gdf_zcta["INTPTLON20"].astype(float)
    gdf_pts = gpd.GeoDataFrame(
        gdf_zcta[["ZCTA5CE20"]].rename(columns={"ZCTA5CE20": "zip_code"}),
        geometry=[Point(xy) for xy in zip(gdf_zcta["lon"], gdf_zcta["lat"])],
        crs="EPSG:4326"
    )

    # 2. State assignment
    print("Assigning CONUS states to ZCTAs...")
    states_gdf = geo.states_outline()
    states_wgs = states_gdf.to_crs("EPSG:4326")
    pts_state = gpd.sjoin(gdf_pts, states_wgs[["STUSPS", "geometry"]], how="left", predicate="within")
    pts_state = pts_state.rename(columns={"STUSPS": "state"})
    
    missing_st = pts_state[pts_state["state"].isna()]
    if len(missing_st) > 0:
        nearest_st = gpd.sjoin_nearest(
            missing_st[["zip_code", "geometry"]].to_crs(geo.LAEA),
            states_gdf[["STUSPS", "geometry"]],
            how="left"
        )
        pts_state.loc[missing_st.index, "state"] = nearest_st["STUSPS"].values

    pts_laea = pts_state.to_crs(geo.LAEA)

    # 3. Load plan structure and commercial assignment
    with open(run_dir / "plan.json") as f:
        plan = json.load(f)
    patterns = state_patterns(plan)
    counts = wholesaler_counts(plan)

    commercial_zips = set()
    commercial_map = {}
    with open(run_dir / "assignment.csv") as f:
        for r in csv.DictReader(f):
            if r["district"] != "other":
                commercial_zips.add(r["zip"])
                commercial_map[(r["zip"], r["bundle"])] = (display_id(r["district"]), r["wholesaler"])

    # 4. Load reach GeoJSON for spatial territory extension
    reach_path = OUT_DIR / f"{scenario_id}_district_reach.geojson"
    if not reach_path.exists():
        reach_path = OUT_DIR / "tableau_district_reach.geojson"
    
    gdf_reach = gpd.read_file(reach_path)
    if "scenario_id" in gdf_reach.columns:
        gdf_reach = gdf_reach[gdf_reach["scenario_id"] == scenario_id]
    gdf_reach_laea = gdf_reach.to_crs(geo.LAEA)

    # 5. Spatial join for each bundle
    bundles = [
        ("N", "national_district", "national_wholesaler"),
        ("WH", "wealth_district", "wealth_wholesaler"),
        ("FI", "fi_district", "fi_wholesaler"),
        ("WHFI", "wifi_district", "wifi_wholesaler"),
    ]

    bundle_assignments = {}
    for b_code, dist_col, rep_col in bundles:
        b_reach = gdf_reach_laea[gdf_reach_laea["bundle"] == b_code]
        if len(b_reach) == 0:
            bundle_assignments[b_code] = pd.DataFrame({
                "zip_code": pts_laea["zip_code"],
                dist_col: "Unserved",
                rep_col: "None"
            })
            continue

        joined = gpd.sjoin_nearest(
            pts_laea[["zip_code", "geometry"]],
            b_reach[["district", "wholesaler", "geometry"]],
            how="left",
            max_distance=150000  # 150 km tolerance for coastal points
        )
        joined = joined.drop_duplicates(subset=["zip_code"])

        # Override with exact commercial assignment where present
        final_dist = []
        final_rep = []
        for z, d_join, w_join in zip(joined["zip_code"], joined["district"], joined["wholesaler"]):
            if (z, b_code) in commercial_map:
                d_comm, w_comm = commercial_map[(z, b_code)]
                final_dist.append(d_comm)
                final_rep.append(w_comm)
            elif pd.notna(d_join):
                final_dist.append(d_join)
                final_rep.append(w_join if pd.notna(w_join) else "None")
            else:
                final_dist.append("Unserved")
                final_rep.append("None")

        bundle_assignments[b_code] = pd.DataFrame({
            "zip_code": joined["zip_code"],
            dist_col: final_dist,
            rep_col: final_rep
        })

    # 6. Build Wide Table (1 row per ZIP)
    df_wide = pd.DataFrame({
        "zip_code": pts_laea["zip_code"].values,
        "state": pts_laea["state"].values,
    })
    for b_code, dist_col, rep_col in bundles:
        df_wide = df_wide.merge(bundle_assignments[b_code], on="zip_code", how="left")

    df_wide["structure_pattern"] = df_wide["state"].map(lambda s: PATTERN_TEXT.get(patterns.get(s), "Unserved"))
    df_wide["wholesalers_in_state"] = df_wide["state"].map(lambda s: counts.get(s, 0))
    df_wide["has_commercial_opportunity"] = df_wide["zip_code"].isin(commercial_zips)

    wide_path = OUT_DIR / f"{scenario_id}_all_zips_wide.csv"
    df_wide.sort_values(by="zip_code").to_csv(wide_path, index=False)
    print(f"Exported Wide Crosswalk: {len(df_wide):,} rows -> {wide_path}")

    # 7. Build Long Table (1 row per ZIP per Channel)
    long_rows = []
    channel_names = {
        "N": "National",
        "WH": "Wealth",
        "FI": "FI",
        "WHFI": "WIFI Merged"
    }
    for _, row in df_wide.iterrows():
        z = row["zip_code"]
        st = row["state"]
        comm = row["has_commercial_opportunity"]
        for b_code, dist_col, rep_col in bundles:
            d = row[dist_col]
            w = row[rep_col]
            if d != "Unserved":
                long_rows.append({
                    "scenario": scenario_id,
                    "zip_code": z,
                    "state": st,
                    "channel": channel_names[b_code],
                    "bundle": b_code,
                    "district": d,
                    "wholesaler": w,
                    "has_commercial_opportunity": comm
                })

    df_long = pd.DataFrame(long_rows)
    long_path = OUT_DIR / f"{scenario_id}_all_zips_long.csv"
    df_long.sort_values(by=["zip_code", "channel"]).to_csv(long_path, index=False)
    print(f"Exported Long Crosswalk: {len(df_long):,} rows -> {long_path}")

    # Copy to brain artifacts
    if BRAIN_DIR.exists():
        import shutil
        shutil.copy(wide_path, BRAIN_DIR / wide_path.name)
        shutil.copy(long_path, BRAIN_DIR / long_path.name)


def main():
    scenario_id = "51_total_13n_11wh_24fi_3wifi"
    run_dir = REPO_ROOT / "battery/results/grid_W3_A_51"
    generate_crosswalk_for_scenario(run_dir, scenario_id)


if __name__ == "__main__":
    main()
