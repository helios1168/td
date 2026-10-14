#!/usr/bin/env python3
"""Build editable Kepler saved maps from existing Census GeoJSON extracts.

Run from any directory: python3 tools/kepler/build.py
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2] / "data" / "kepler"
SOURCES = {
    "regions": ("census_regions.geojson", "Census regions", 4),
    "divisions": ("census_divisions.geojson", "Census divisions", 9),
    "states": ("states_region_division.geojson", "States and DC", 51),
}
COLORS = ["#4477AA", "#EE6677", "#228833", "#CCBB44", "#66CCEE", "#AA3377", "#BBBBBB", "#EE9933", "#9944AA"]


def dataset(key, filename, label, count):
    features = json.loads((ROOT / filename).read_text())["features"]
    assert len(features) == count, (filename, len(features))
    assert all(f["geometry"]["type"] in ("Polygon", "MultiPolygon") for f in features)
    names = list(features[0]["properties"])
    fields = [{"name": "_geojson", "type": "geojson", "format": "", "analyzerType": "GEOMETRY"}]
    fields += [{"name": n, "type": "string", "format": "", "analyzerType": "STRING"} for n in names]
    return {"version": "v1", "data": {
        "id": key, "label": label, "color": [68, 119, 170], "fields": fields,
        "allData": [[f] + [f["properties"].get(n) for n in names] for f in features],
    }}


def layer(key, label, *, filled=False, field=None, visible=True, thickness=1):
    return {
        "id": label.lower().replace(" ", "-"), "type": "geojson",
        "config": {"dataId": key, "label": label, "color": [55, 65, 80],
            "columns": {"geojson": "_geojson"}, "isVisible": visible,
            "visConfig": {"filled": filled, "stroked": not filled, "opacity": 0.7 if filled else 0.9,
                "thickness": thickness, "strokeColor": [55, 65, 80], "enable3d": False,
                "colorRange": {"name": "Census categories", "type": "qualitative", "category": "Custom",
                    "colors": COLORS[:4] if key == "regions" else COLORS}}},
        "visualChannels": {"colorField": {"name": field, "type": "string"} if field else None,
            "colorScale": "ordinal"},
    }


def build():
    datasets = [dataset(k, *v) for k, v in SOURCES.items()]
    for view in ("regions", "divisions"):
        config = {"version": "v1", "config": {
            "visState": {"filters": [], "layers": [
                layer("states", "State outlines", thickness=0.6),
                layer("divisions", "Division outlines", thickness=2),
                layer("divisions", "Division colours", filled=True, field="division_name", visible=view == "divisions"),
                layer("regions", "Region colours", filled=True, field="region_name", visible=view == "regions"),
            ], "interactionConfig": {"tooltip": {"enabled": True, "fieldsToShow": {
                d["data"]["id"]: [{"name": f["name"], "format": None} for f in d["data"]["fields"][1:]]
                for d in datasets}}, "brush": {"enabled": False, "size": 0.5}},
                "layerBlending": "normal", "splitMaps": []},
            "mapState": {"latitude": 38.5, "longitude": -97, "zoom": 3.3, "pitch": 0,
                "bearing": 0, "dragRotate": False, "isSplit": False},
            "mapStyle": {"styleType": "positron", "topLayerGroups": {},
                "visibleLayerGroups": {"label": True, "road": False, "border": False,
                    "building": False, "water": True, "land": True}},
        }}
        saved = {"datasets": datasets, "config": config, "info": {"app": "kepler.gl",
            "title": f"2025 Census {view}", "description": "50 states + DC, including AK/HI at actual locations. Display geometry simplified 0.002 degrees; no opportunity or sales data."}}
        # ponytail: native saved-map format; no Python/React dependencies in the generator.
        path = ROOT / f"census_{view}.kepler.gl.json"
        path.write_text(json.dumps(saved, separators=(",", ":")))
        print(f"{path.name}: {path.stat().st_size:,} bytes")


if __name__ == "__main__":
    build()
