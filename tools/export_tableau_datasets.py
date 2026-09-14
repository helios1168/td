"""tools/export_tableau_datasets.py
Export datasets for exact map reproduction in Tableau:
1. tableau_state_structure.csv: State-level dataset for the Channel Structure map.
2. tableau_district_reach.geojson: Wall-to-wall territory polygons in WGS84 for all bundles.
"""
import csv
import json
from pathlib import Path
import pickle
import pyproj
import shapely
from shapely.geometry import Polygon, MultiPolygon
from shapely.ops import transform

import sys
import os
from pathlib import Path

REPO_ROOT = Path("/Users/Shared/sv-ntlee/repos/td/.claude/worktrees/agy-math-review-memo")
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "tools"))

from td import geo
from tools.plan_summary import (
    PATTERNS, PATTERN_FILL, PATTERN_TEXT,
    state_patterns, wholesaler_counts, load_assignment, display_id, bundle_title
)
OUT_DIR = REPO_ROOT / "exports/tableau"
BRAIN_DIR = Path("/Users/sandvault-ntlee/.gemini/antigravity-cli/brain/09f078e7-2f55-4c40-9905-5ed9fd054e07")

from tools.update_scenario_naming import SCENARIOS

SCENARIOS_TUPLES = [
    (sc["run_d"], f"{sc['total']}_{sc['n']}_{sc['wh']}_{sc['fi']}_{sc['wifi']}")
    for sc in SCENARIOS
]


def export_state_structure(scenarios_list):
    """Generates state-level CSV for Tableau's built-in State geocoding."""
    rows = []
    for run_rel, sc_id in scenarios_list:
        run_d = REPO_ROOT / run_rel
        with open(run_d / "plan.json") as f:
            plan = json.load(f)
        assign = load_assignment(str(run_d / "assignment.csv"))
        patterns = state_patterns(plan)
        counts = wholesaler_counts(plan)
        split_any = set().union(*assign["splits"].values()) if assign["splits"] else set()

        for state, pattern in patterns.items():
            if state in ("CA1", "CA2"):
                continue
            rows.append({
                "scenario_id": sc_id,
                "state": state,
                "pattern": pattern,
                "pattern_label": PATTERN_TEXT.get(pattern, pattern),
                "pattern_color": PATTERN_FILL.get(pattern, "#e2e2e2"),
                "wholesaler_count": counts.get(state, 0),
                "is_split": state in split_any,
            })

    out_file = OUT_DIR / "tableau_state_structure.csv"
    with open(out_file, "w", newline="") as f:
        fieldnames = ["scenario_id", "state", "pattern", "pattern_label", "pattern_color", "wholesaler_count", "is_split"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Exported {len(rows)} state structure rows to {out_file}")
    if BRAIN_DIR.exists():
        import shutil
        shutil.copy(out_file, BRAIN_DIR / out_file.name)

    # Export scenario-specific 51_13_11_24_3 file
    rows_51 = [r for r in rows if r["scenario_id"] == "51_13_11_24_3"]
    out_51 = OUT_DIR / "51_13_11_24_3_state_structure.csv"
    with open(out_51, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows_51)
    print(f"Exported {len(rows_51)} state structure rows to {out_51}")
    if BRAIN_DIR.exists():
        import shutil
        shutil.copy(out_51, BRAIN_DIR / out_51.name)


def export_district_geojson(scenarios_list):
    """Converts district_reach LAEA polygons to WGS84 GeoJSON for Tableau Spatial File import."""
    wgs84 = pyproj.CRS("EPSG:4326")
    laea = pyproj.CRS(geo.LAEA)
    proj = pyproj.Transformer.from_crs(laea, wgs84, always_xy=True).transform

    features = []
    for run_rel, sc_id in scenarios_list:
        run_d = REPO_ROOT / run_rel
        cache_d = run_d / "maps/cache"
        if not cache_d.exists():
            continue

        # Load districts meta
        dist_meta = {}
        if (run_d / "districts.csv").exists():
            with open(run_d / "districts.csv") as f:
                dist_meta = {r["district"]: r for r in csv.DictReader(f)}

        for bundle_f in cache_d.glob("*_geom.pkl"):
            b_name = bundle_f.stem.replace("_geom", "")
            with open(bundle_f, "rb") as f:
                data = pickle.load(f)
            polys = data["polys"]
            reach = polys.get("district_reach", {})
            for d, info in reach.items():
                rings = info.get("rings", [])
                parts = [Polygon(r) for r in rings if len(r) >= 4]
                if not parts:
                    continue
                geom_laea = parts[0] if len(parts) == 1 else MultiPolygon(parts)
                geom_wgs = transform(proj, geom_laea)

                meta = dist_meta.get(d, {})
                features.append({
                    "type": "Feature",
                    "geometry": shapely.geometry.mapping(geom_wgs),
                    "properties": {
                        "scenario_id": sc_id,
                        "bundle": b_name,
                        "bundle_title": bundle_title(b_name),
                        "district_raw": d,
                        "district": display_id(d),
                        "wholesaler": meta.get("wholesaler", ""),
                        "mass": float(meta.get("mass", 0.0) or 0.0),
                        "color": info.get("color", "#888888")
                    }
                })

    geojson_obj = {
        "type": "FeatureCollection",
        "features": features
    }
    out_file = OUT_DIR / "tableau_district_reach.geojson"
    with open(out_file, "w") as f:
        json.dump(geojson_obj, f)
    print(f"Exported {len(features)} district polygons to {out_file}")
    if BRAIN_DIR.exists():
        import shutil
        shutil.copy(out_file, BRAIN_DIR / out_file.name)

    # Export scenario-specific 51_13_11_24_3 file
    feat_51 = [f for f in features if f["properties"]["scenario_id"] == "51_13_11_24_3"]
    out_51 = OUT_DIR / "51_13_11_24_3_district_reach.geojson"
    with open(out_51, "w") as f:
        json.dump({"type": "FeatureCollection", "features": feat_51}, f)
    print(f"Exported {len(feat_51)} district polygons to {out_51}")
    if BRAIN_DIR.exists():
        import shutil
        shutil.copy(out_51, BRAIN_DIR / out_51.name)


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    export_state_structure(SCENARIOS_TUPLES)
    export_district_geojson(SCENARIOS_TUPLES)


if __name__ == "__main__":
    main()
