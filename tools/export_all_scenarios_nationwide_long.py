"""tools/export_all_scenarios_nationwide_long.py

Export nationwide long-format ZCTA dataset across all 36 scenarios at the 5-subchannel grain
matching the original instance_export.py schema:
- 33,791 US Census ZCTAs (all 50 states + PR + DC)
- 5 sub-channels: National (Chase), Wells WH, Wells FI, WH, FI
- All 36 realized scenarios (K=46 through K=53)
- 33,791 * 5 * 36 = 6,082,380 rows total
- Includes exact commercial assignments, spatial reach extensions, descaled opportunity mass (m_rel),
  and channel mapping back to instance_export.py.
- Exports to .csv, .zip, and .csv.gz in exports/database/ and brain artifacts.
"""

from __future__ import annotations

import csv
import gzip
import json
import os
import shutil
import sys
import time
import zipfile
from pathlib import Path

import geopandas as gpd
import pandas as pd
from shapely.geometry import Point

REPO_ROOT = Path("/Users/Shared/sv-ntlee/repos/td/.claude/worktrees/agy-math-review-memo")
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "tools"))

from td import geo
from tools.plan_summary import display_id

ZCTA_SHP = Path("/Users/Shared/sv-ntlee/repos/td/data/tiger/2025/tl_2025_us_zcta520.shp")
INSTANCE_PATH = Path("/Users/Shared/sv-ntlee/repos/td/instance_descaled_v4_conus.json.gz")
OUT_DIR = REPO_ROOT / "exports/database"
TABLEAU_DIR = REPO_ROOT / "exports/tableau"
BRAIN_DIR = Path("/Users/sandvault-ntlee/.gemini/antigravity-cli/brain/09f078e7-2f55-4c40-9905-5ed9fd054e07")

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

SUBCHANNELS = [
    {
        "current_channel": "National (Chase)",
        "canonical_channel": "national_chase",
        "model_channel": "N_FI",
        "bundle": "N",
    },
    {
        "current_channel": "Wells WH",
        "canonical_channel": "national_wells_wh",
        "model_channel": "N_WH",
        "bundle": "N",
    },
    {
        "current_channel": "Wells FI",
        "canonical_channel": "national_wells_fi",
        "model_channel": "N_FI",
        "bundle": "N",
    },
    {
        "current_channel": "WH",
        "canonical_channel": "wh",
        "model_channel": "WH",
        "bundle": "WH",
    },
    {
        "current_channel": "FI",
        "canonical_channel": "fi",
        "model_channel": "FI",
        "bundle": "FI",
    },
]

MIX = {
    "N": "N",
    "WH": "WH",
    "FI": "FI",
    "WH_PLUS": "WH+",
    "FI_PLUS": "FI+",
    "WHFI": "WHFI",
    "WHFI_PLUS": "WIFI",
}


def load_zctas():
    print("Loading 2025 US Census ZCTA points & boundaries...")
    gdf_zcta = gpd.read_file(ZCTA_SHP, columns=["ZCTA5CE20", "INTPTLAT20", "INTPTLON20"])
    gdf_pts = gpd.GeoDataFrame(
        gdf_zcta[["ZCTA5CE20"]].rename(columns={"ZCTA5CE20": "zip_code"}),
        geometry=[Point(xy) for xy in zip(gdf_zcta["INTPTLON20"].astype(float), gdf_zcta["INTPTLAT20"].astype(float))],
        crs="EPSG:4326",
    )
    states_gdf = geo.states_outline()
    states_wgs = states_gdf.to_crs("EPSG:4326")
    pts_state = gpd.sjoin(gdf_pts, states_wgs[["STUSPS", "geometry"]], how="left", predicate="within").rename(
        columns={"STUSPS": "state"}
    )
    missing_st = pts_state[pts_state["state"].isna()]
    if len(missing_st) > 0:
        nearest_st = gpd.sjoin_nearest(
            missing_st[["zip_code", "geometry"]].to_crs(geo.LAEA),
            states_gdf[["STUSPS", "geometry"]],
            how="left",
        )
        pts_state.loc[missing_st.index, "state"] = nearest_st["STUSPS"].values
    pts_laea = pts_state.to_crs(geo.LAEA)
    print(f"Loaded {len(pts_laea):,} ZCTAs across {pts_laea['state'].nunique()} state codes.")
    return pts_laea


def load_cell_masses():
    print("Loading descaled opportunity cell masses from instance_descaled_v4_conus.json.gz...")
    with gzip.open(INSTANCE_PATH, "rt") as f:
        inst = json.load(f)
    nodes = inst["nodes"]
    cell_mass = {}
    for z, ch, m in zip(nodes["z"], nodes["channel"], nodes["m_rel"]):
        cell_mass[(z, ch)] = float(m)
    print(f"Loaded {len(cell_mass):,} non-zero commercial opportunity cells.")
    return cell_mass


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    pts_laea = load_zctas()
    cell_mass = load_cell_masses()

    # Load master reach GeoJSON
    reach_path = TABLEAU_DIR / "tableau_district_reach.geojson"
    print(f"Loading master district reach GeoJSON from {reach_path}...")
    gdf_reach_all = gpd.read_file(reach_path)
    gdf_reach_all_laea = gdf_reach_all.to_crs(geo.LAEA)

    # Load scenario catalog
    with open(REPO_ROOT / "summary.csv") as f:
        scenarios = list(csv.DictReader(f))
    print(f"Found {len(scenarios)} scenarios in summary.csv.")

    bundles = [
        ("N", "national_district", "national_wholesaler"),
        ("WH", "wealth_district", "wealth_wholesaler"),
        ("FI", "fi_district", "fi_wholesaler"),
        ("WHFI", "wifi_district", "wifi_wholesaler"),
    ]

    out_csv = OUT_DIR / "all_scenarios_nationwide_zcta_long.csv"
    print(f"\nStreaming master nationwide dataset to {out_csv}...")
    t_start = time.time()
    total_written = 0

    fieldnames = [
        "scenario",
        "zip_code",
        "current_channel",
        "canonical_channel",
        "state",
        "model_channel",
        "bundle",
        "district",
        "district_channels",
        "rep",
        "m_rel",
        "has_commercial_opportunity",
    ]

    with open(out_csv, "w", newline="", encoding="utf-8") as f_out:
        writer = csv.DictWriter(f_out, fieldnames=fieldnames)
        writer.writeheader()

        for s_idx, sc in enumerate(scenarios, 1):
            sc_id = sc["scenario_id"]
            run_rel = DIR_MAP.get(sc_id, f"battery/results/{sc_id}")
            run_d = REPO_ROOT / run_rel
            t0 = time.time()

            # 1. Load commercial assignment
            comm_map = {}
            with open(run_d / "assignment.csv") as f:
                for r in csv.DictReader(f):
                    if r["district"] != "other":
                        comm_map[(r["zip"], r["channel"])] = {
                            "district": display_id(r["district"]),
                            "bundle": r["bundle"],
                            "wholesaler": r["wholesaler"],
                        }

            # 2. Spatial join for non-commercial ZCTAs across bundles
            gdf_reach_sc = gdf_reach_all_laea[gdf_reach_all_laea["scenario_id"] == sc_id]
            bundle_assignments = {}
            for b_code, dist_col, rep_col in bundles:
                b_reach = gdf_reach_sc[gdf_reach_sc["bundle"] == b_code]
                if len(b_reach) == 0:
                    bundle_assignments[b_code] = pd.DataFrame({
                        "zip_code": pts_laea["zip_code"],
                        dist_col: "Unserved",
                        rep_col: "None",
                    })
                    continue
                joined = gpd.sjoin_nearest(
                    pts_laea[["zip_code", "geometry"]],
                    b_reach[["district", "wholesaler", "geometry"]],
                    how="left",
                    max_distance=250000,
                ).drop_duplicates(subset=["zip_code"])
                bundle_assignments[b_code] = (
                    joined[["zip_code", "district", "wholesaler"]]
                    .rename(columns={"district": dist_col, "wholesaler": rep_col})
                    .fillna({dist_col: "Unserved", rep_col: "None"})
                )

            # Combine spatial assignments into a single lookup per zip
            df_geo = pd.DataFrame({
                "zip_code": pts_laea["zip_code"].values,
                "state": pts_laea["state"].values,
            })
            for b_code, dist_col, rep_col in bundles:
                df_geo = df_geo.merge(bundle_assignments[b_code], on="zip_code", how="left")

            geo_lookup = df_geo.set_index("zip_code").to_dict(orient="index")

            # Load plan.json to know which bundles exist in each state
            st_bundles = {}
            with open(run_d / "plan.json") as f:
                plan_data = json.load(f)
            slot_bundle = {s["id"]: s["bundle"] for s in plan_data["slots"]}
            for st_name, pids in plan_data.get("per_state", {}).items():
                st_bundles[st_name] = {slot_bundle[pid] for pid in pids if pid in slot_bundle}

            # 3. Build 5 sub-channel rows for each of the 33,791 ZCTAs
            sc_rows = []
            for z, g_info in geo_lookup.items():
                st = g_info["state"]
                has_n = "N" in st_bundles.get(st, set())
                has_wh = "WH" in st_bundles.get(st, set())
                has_fi = "FI" in st_bundles.get(st, set())
                has_wifi = "WHFI" in st_bundles.get(st, set())

                for ch_cfg in SUBCHANNELS:
                    src_ch = ch_cfg["current_channel"]
                    canon_ch = ch_cfg["canonical_channel"]
                    model_ch = ch_cfg["model_channel"]

                    # Check commercial assignment first
                    if (z, model_ch) in comm_map:
                        c_info = comm_map[(z, model_ch)]
                        dist = c_info["district"]
                        bndl = c_info["bundle"]
                        rep = c_info["wholesaler"]
                    else:
                        # Fallback to spatial reach based on channel and state validity
                        if st in ("AK", "HI", "PR", ""):
                            dist = "Unserved"
                            bndl = ""
                            rep = "None"
                        elif src_ch in ("National (Chase)", "Wells FI"):
                            if has_n and g_info.get("national_district") != "Unserved":
                                dist = g_info.get("national_district", "Unserved")
                                rep = g_info.get("national_wholesaler", "None")
                                bndl = "N"
                            elif has_wifi and g_info.get("wifi_district") != "Unserved":
                                dist = g_info.get("wifi_district", "Unserved")
                                rep = g_info.get("wifi_wholesaler", "None")
                                bndl = "WHFI"
                            elif has_fi and g_info.get("fi_district") != "Unserved":
                                dist = g_info.get("fi_district", "Unserved")
                                rep = g_info.get("fi_wholesaler", "None")
                                bndl = "FI"
                            else:
                                dist = "Unserved"
                                bndl = ""
                                rep = "None"
                        elif src_ch == "Wells WH":
                            if has_n and g_info.get("national_district") != "Unserved":
                                dist = g_info.get("national_district", "Unserved")
                                rep = g_info.get("national_wholesaler", "None")
                                bndl = "N"
                            elif has_wifi and g_info.get("wifi_district") != "Unserved":
                                dist = g_info.get("wifi_district", "Unserved")
                                rep = g_info.get("wifi_wholesaler", "None")
                                bndl = "WHFI"
                            elif has_wh and g_info.get("wealth_district") != "Unserved":
                                dist = g_info.get("wealth_district", "Unserved")
                                rep = g_info.get("wealth_wholesaler", "None")
                                bndl = "WH"
                            else:
                                dist = "Unserved"
                                bndl = ""
                                rep = "None"
                        elif src_ch == "WH":
                            # In WIFI states where all channels merged, use wifi
                            if has_wifi and not has_wh:
                                dist = g_info.get("wifi_district", "Unserved")
                                rep = g_info.get("wifi_wholesaler", "None")
                                bndl = "WHFI"
                            elif has_wh and g_info.get("wealth_district") != "Unserved":
                                dist = g_info.get("wealth_district", "Unserved")
                                rep = g_info.get("wealth_wholesaler", "None")
                                bndl = "WH"
                            elif has_wifi and g_info.get("wifi_district") != "Unserved":
                                dist = g_info.get("wifi_district", "Unserved")
                                rep = g_info.get("wifi_wholesaler", "None")
                                bndl = "WHFI"
                            else:
                                dist = "Unserved"
                                bndl = ""
                                rep = "None"
                        elif src_ch == "FI":
                            if has_wifi and not has_fi:
                                dist = g_info.get("wifi_district", "Unserved")
                                rep = g_info.get("wifi_wholesaler", "None")
                                bndl = "WHFI"
                            elif has_fi and g_info.get("fi_district") != "Unserved":
                                dist = g_info.get("fi_district", "Unserved")
                                rep = g_info.get("fi_wholesaler", "None")
                                bndl = "FI"
                            elif has_wifi and g_info.get("wifi_district") != "Unserved":
                                dist = g_info.get("wifi_district", "Unserved")
                                rep = g_info.get("wifi_wholesaler", "None")
                                bndl = "WHFI"
                            else:
                                dist = "Unserved"
                                bndl = ""
                                rep = "None"

                    dist_channels = MIX.get(bndl, bndl)
                    m = cell_mass.get((z, canon_ch), 0.0)
                    has_comm = m > 0.0

                    sc_rows.append({
                        "scenario": sc_id,
                        "zip_code": z,
                        "current_channel": src_ch,
                        "canonical_channel": canon_ch,
                        "state": st,
                        "model_channel": model_ch,
                        "bundle": bndl,
                        "district": dist,
                        "district_channels": dist_channels,
                        "rep": rep,
                        "m_rel": f"{m:.6f}" if has_comm else "0.000000",
                        "has_commercial_opportunity": "True" if has_comm else "False",
                    })

            writer.writerows(sc_rows)
            total_written += len(sc_rows)
            print(f"[{s_idx:2d}/{len(scenarios)}] {sc_id:<35} -> {len(sc_rows):,} rows ({time.time()-t0:.2f}s)")

    print(f"\nSuccessfully wrote {total_written:,} rows to {out_csv} ({out_csv.stat().st_size / 1e6:.1f} MB) in {time.time()-t_start:.1f}s.")

    # Compress to .zip and .csv.gz
    zip_path = OUT_DIR / "all_scenarios_nationwide_zcta_long.zip"
    print(f"\nCompressing to {zip_path}...")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(out_csv, arcname=out_csv.name)
    print(f"ZIP Archive: {zip_path.stat().st_size / 1e6:.1f} MB -> {zip_path}")

    gz_path = OUT_DIR / "all_scenarios_nationwide_zcta_long.csv.gz"
    print(f"Compressing to {gz_path}...")
    with open(out_csv, "rb") as f_in, gzip.open(gz_path, "wb") as f_out:
        shutil.copyfileobj(f_in, f_out)
    print(f"GZ Archive: {gz_path.stat().st_size / 1e6:.1f} MB -> {gz_path}")

    # Copy to brain artifacts
    if BRAIN_DIR.exists():
        print(f"\nCopying archives to brain artifacts directory...")
        for p in [zip_path, gz_path]:
            dest = BRAIN_DIR / p.name
            shutil.copy(p, dest)
            print(f"Copied to: {dest}")

    print("\n=== EXPORT COMPLETED SUCCESSFULLY ===")


if __name__ == "__main__":
    main()
