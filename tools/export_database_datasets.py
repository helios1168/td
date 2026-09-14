"""tools/export_database_datasets.py
Generate complete nationwide ZCTA-to-district datasets across all 18 scenarios
in both Wide format and Long format, and package them into compressed .zip and .gz archives
for high-performance database ingestion (Snowflake, BigQuery, Postgres, Redshift, etc.) and Tableau.
"""
import csv
import json
import os
import shutil
import sys
import zipfile
import gzip
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
from tools.update_scenario_naming import SCENARIOS

OUT_DIR = REPO_ROOT / "exports/database"
TABLEAU_DIR = REPO_ROOT / "exports/tableau"
BRAIN_DIR = Path("/Users/sandvault-ntlee/.gemini/antigravity-cli/brain/09f078e7-2f55-4c40-9905-5ed9fd054e07")
ZCTA_SHP = Path("/Users/Shared/sv-ntlee/repos/td/data/tiger/2025/tl_2025_us_zcta520.shp")


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    TABLEAU_DIR.mkdir(parents=True, exist_ok=True)

    print("=== 1. LOADING US CENSUS 2025 ZCTA GEOMETRY & CONUS STATES ===")
    gdf_zcta = gpd.read_file(ZCTA_SHP, columns=["ZCTA5CE20", "INTPTLAT20", "INTPTLON20"])
    gdf_zcta["lat"] = gdf_zcta["INTPTLAT20"].astype(float)
    gdf_zcta["lon"] = gdf_zcta["INTPTLON20"].astype(float)
    gdf_pts = gpd.GeoDataFrame(
        gdf_zcta[["ZCTA5CE20"]].rename(columns={"ZCTA5CE20": "zip_code"}),
        geometry=[Point(xy) for xy in zip(gdf_zcta["lon"], gdf_zcta["lat"])],
        crs="EPSG:4326"
    )

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
    print(f"Loaded {len(pts_laea):,} ZCTAs assigned across {pts_laea['state'].nunique()} states.")

    # Load master reach GeoJSON for spatial territory assignments
    reach_path = TABLEAU_DIR / "tableau_district_reach.geojson"
    gdf_reach_all = gpd.read_file(reach_path)
    gdf_reach_all_laea = gdf_reach_all.to_crs(geo.LAEA)

    all_wide_dfs = []
    all_long_rows = []

    bundles = [
        ("N", "national_district", "national_wholesaler"),
        ("WH", "wealth_district", "wealth_wholesaler"),
        ("FI", "fi_district", "fi_wholesaler"),
        ("WHFI", "wifi_district", "wifi_wholesaler"),
    ]
    channel_names = {
        "N": "National",
        "WH": "Wealth",
        "FI": "FI",
        "WHFI": "WIFI Merged"
    }

    print("\n=== 2. PROCESSING ALL 18 SCENARIOS ===")
    for idx, sc in enumerate(SCENARIOS, 1):
        tot = sc["total"]
        n = sc["n"]
        wh = sc["wh"]
        fi = sc["fi"]
        wifi = sc["wifi"]
        scenario_id = f"{tot}_total_{n}n_{wh}wh_{fi}fi_{wifi}wifi"
        run_dir = REPO_ROOT / sc["run_d"]
        print(f"[{idx}/18] Processing {scenario_id}...")

        # Load plan structure and commercial assignment
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

        gdf_reach_sc = gdf_reach_all_laea[gdf_reach_all_laea["scenario_id"] == scenario_id]

        bundle_assignments = {}
        for b_code, dist_col, rep_col in bundles:
            b_reach = gdf_reach_sc[gdf_reach_sc["bundle"] == b_code]
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
                max_distance=150000
            )
            joined = joined.drop_duplicates(subset=["zip_code"])

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

        # Wide DF for this scenario
        df_wide_sc = pd.DataFrame({
            "scenario": scenario_id,
            "zip_code": pts_laea["zip_code"].values,
            "state": pts_laea["state"].values,
        })
        for b_code, dist_col, rep_col in bundles:
            df_wide_sc = df_wide_sc.merge(bundle_assignments[b_code], on="zip_code", how="left")

        df_wide_sc["structure_pattern"] = df_wide_sc["state"].map(lambda s: PATTERN_TEXT.get(patterns.get(s), "Unserved"))
        df_wide_sc["wholesalers_in_state"] = df_wide_sc["state"].map(lambda s: counts.get(s, 0))
        df_wide_sc["has_commercial_opportunity"] = df_wide_sc["zip_code"].isin(commercial_zips)
        all_wide_dfs.append(df_wide_sc)

        # Long rows for this scenario
        for _, row in df_wide_sc.iterrows():
            z = row["zip_code"]
            st = row["state"]
            comm = row["has_commercial_opportunity"]
            for b_code, dist_col, rep_col in bundles:
                d = row[dist_col]
                w = row[rep_col]
                if d != "Unserved":
                    all_long_rows.append({
                        "scenario": scenario_id,
                        "zip_code": z,
                        "state": st,
                        "channel": channel_names[b_code],
                        "bundle": b_code,
                        "district": d,
                        "wholesaler": w,
                        "has_commercial_opportunity": comm
                    })

    print("\n=== 3. COMBINING & EXPORTING MASTER DATASETS ===")
    df_wide_all = pd.concat(all_wide_dfs, ignore_index=True)
    df_wide_all = df_wide_all.sort_values(by=["scenario", "zip_code"])
    wide_csv = OUT_DIR / "all_scenarios_zips_wide.csv"
    df_wide_all.to_csv(wide_csv, index=False)
    print(f"Master Wide CSV: {len(df_wide_all):,} rows ({wide_csv.stat().st_size / 1e6:.1f} MB) -> {wide_csv}")

    df_long_all = pd.DataFrame(all_long_rows)
    df_long_all = df_long_all.sort_values(by=["scenario", "zip_code", "channel"])
    long_csv = OUT_DIR / "all_scenarios_zips_long.csv"
    df_long_all.to_csv(long_csv, index=False)
    print(f"Master Long CSV: {len(df_long_all):,} rows ({long_csv.stat().st_size / 1e6:.1f} MB) -> {long_csv}")

    print("\n=== 4. PACKAGING INTO COMPRESSED ZIP & GZ ARCHIVES FOR DATABASE IMPORT ===")
    # 1. Combined ZIP containing both files
    combined_zip = OUT_DIR / "all_scenarios_zips.zip"
    with zipfile.ZipFile(combined_zip, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(wide_csv, arcname=wide_csv.name)
        zf.write(long_csv, arcname=long_csv.name)
    print(f"Combined ZIP Archive: {combined_zip.stat().st_size / 1e6:.1f} MB -> {combined_zip}")

    # 2. Individual ZIP archives
    wide_zip = OUT_DIR / "all_scenarios_zips_wide.zip"
    with zipfile.ZipFile(wide_zip, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(wide_csv, arcname=wide_csv.name)
    print(f"Wide ZIP Archive: {wide_zip.stat().st_size / 1e6:.1f} MB -> {wide_zip}")

    long_zip = OUT_DIR / "all_scenarios_zips_long.zip"
    with zipfile.ZipFile(long_zip, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(long_csv, arcname=long_csv.name)
    print(f"Long ZIP Archive: {long_zip.stat().st_size / 1e6:.1f} MB -> {long_zip}")

    # 3. GZ versions for direct Snowflake/BigQuery/Redshift COPY INTO
    wide_gz = OUT_DIR / "all_scenarios_zips_wide.csv.gz"
    with open(wide_csv, "rb") as f_in, gzip.open(wide_gz, "wb") as f_out:
        shutil.copyfileobj(f_in, f_out)
    print(f"Wide GZIP: {wide_gz.stat().st_size / 1e6:.1f} MB -> {wide_gz}")

    long_gz = OUT_DIR / "all_scenarios_zips_long.csv.gz"
    with open(long_csv, "rb") as f_in, gzip.open(long_gz, "wb") as f_out:
        shutil.copyfileobj(f_in, f_out)
    print(f"Long GZIP: {long_gz.stat().st_size / 1e6:.1f} MB -> {long_gz}")

    # Copy to brain artifacts
    if BRAIN_DIR.exists():
        for p in [combined_zip, wide_zip, long_zip, wide_gz, long_gz]:
            shutil.copy(p, BRAIN_DIR / p.name)
            print(f"Copied to artifacts: {BRAIN_DIR / p.name}")

    print("\nDatabase export completed successfully!")


if __name__ == "__main__":
    main()
