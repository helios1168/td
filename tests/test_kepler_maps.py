"""Saved-map contract checks; run with python3 tests/test_kepler_maps.py."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "data" / "kepler"


def test_census_saved_maps():
    for view in ("regions", "divisions"):
        saved = json.loads((ROOT / f"census_{view}.kepler.gl.json").read_text())
        datasets = {d["data"]["id"]: d["data"] for d in saved["datasets"]}
        assert {k: len(d["allData"]) for k, d in datasets.items()} == {"regions": 4, "divisions": 9, "states": 51}
        for key, d in datasets.items():
            source = json.loads((ROOT / {"regions": "census_regions.geojson", "divisions": "census_divisions.geojson", "states": "states_region_division.geojson"}[key]).read_text())
            assert [r[0] for r in d["allData"]] == source["features"]
            assert all(len(r) == len(d["fields"]) for r in d["allData"])
        layers = saved["config"]["config"]["visState"]["layers"]
        for layer in layers:
            fields = {f["name"] for f in datasets[layer["config"]["dataId"]]["fields"]}
            assert layer["config"]["columns"]["geojson"] in fields
            field = layer["visualChannels"]["colorField"]
            assert not field or field["name"] in fields
        assert [l["config"]["dataId"] for l in layers if l["config"]["isVisible"] and l["config"]["visConfig"]["filled"]] == [view]


if __name__ == "__main__":
    test_census_saved_maps()
    print("Census saved-map checks passed")
