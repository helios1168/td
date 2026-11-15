"""states_csv.py -- geo/cb_2025_us_state_500k.zip (Census cartographic states, as downloaded) to the CSV beside it,
in the layout of the census tables already in Snowflake: GEO_ID, FULLY_QUALIFIED_ID, GEO_NAME, GEO_BOUNDARY (WKT,
lon lat), plus STUSPS to join a ZIP's state.  Snowflake has no shapefile loader; a WKT column loads as GEOGRAPHY.

    .venv/bin/python3 -I tools/snowflake/states_csv.py

ponytail: coordinates are written as they are (NAD83 read as WGS 84, about a metre apart, the same as loading the
Census file directly); reproject here if a use ever needs better.
"""
import csv
import os

import pyogrio
import shapely

GEO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "geo")
NAME = "cb_2025_us_state_500k"

if __name__ == "__main__":
    g = pyogrio.read_dataframe(f"zip://{os.path.join(GEO, NAME + '.zip')}").sort_values("GEOID")
    assert len(g) == 56 and g["GEOID"].is_unique and g.geometry.is_valid.all(), "not the 56 valid state rows"
    wkt = shapely.to_wkt(g.geometry.values, rounding_precision=6)
    # six decimals are the file's own precision: every shape comes back valid and within 1e-6 degrees
    back = shapely.from_wkt(wkt)
    assert shapely.is_valid(back).all() and (shapely.hausdorff_distance(back, g.geometry.values) < 1e-6).all()
    with open(os.path.join(GEO, NAME + ".csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, quoting=csv.QUOTE_ALL)
        w.writerow(["GEO_ID", "FULLY_QUALIFIED_ID", "GEO_NAME", "STUSPS", "GEO_BOUNDARY"])
        w.writerows(zip(g["GEOID"], g["GEOIDFQ"], g["NAME"], g["STUSPS"], wkt))
    print(len(g), "states,", int(shapely.get_num_coordinates(back).sum()), "points, largest field", max(map(len, wkt)), "chars")
