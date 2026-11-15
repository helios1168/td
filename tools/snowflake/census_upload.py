"""census_upload.py -- a Census cartographic shapefile zip into a Snowflake table CENSUS_<LAYER>, in the layout of
the census tables already there: GEO_ID, FULLY_QUALIFIED_ID, GEO_NAME, GEO_BOUNDARY (GEOGRAPHY), plus a layer's
extra columns.  The owner's upload script (2026-11-15), set up for the state outlines.

    pip install "snowflake-connector-python[pandas]" geopandas
    export SNOWFLAKE_ACCOUNT=... SNOWFLAKE_USER=... SNOWFLAKE_WAREHOUSE=...     (Windows: set NAME=value)
    python census_upload.py [folder holding the zips, default: geo/ beside this file]

Signs in through the browser.  The account, user and warehouse come from the environment so that they are not in
the repo; the role, database and schema are the session header's.  CREATE OR REPLACE: an existing CENSUS_<LAYER> is
replaced.  Stops with an error unless every row of the file is in the table with a valid shape.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

# layer -> the zip, its ID and name columns, and columns kept beside the four (STUSPS: the two-letter state code,
# to join a ZIP's state).  The cartographic state file has no "20" suffix: GEOID and NAME, not GEOID20 and NAME20.
CENSUS_LAYERS = {
    "states": {"zip": "cb_2025_us_state_500k.zip", "id_col": "GEOID", "name_col": "NAME", "extra": ["STUSPS"]},
}


def frame(zip_path, meta):
    """The layer as the rows to load: GEO_ID, FULLY_QUALIFIED_ID, GEO_NAME, the extra columns, WKT_GEOM (WGS 84)."""
    import geopandas as gpd
    import pandas as pd
    from shapely.wkt import dumps

    gdf = gpd.read_file(f"zip://{zip_path}").to_crs(epsg=4326)
    # the fully qualified ID was AFFGEOID in older files
    fq = next((c for c in ("GEOIDFQ", "AFFGEOID") if c in gdf.columns), meta["id_col"])
    cols = {"GEO_ID": meta["id_col"], "FULLY_QUALIFIED_ID": fq, "GEO_NAME": meta["name_col"],
            **{c: c for c in meta.get("extra", [])}}
    df = pd.DataFrame({k: gdf[v].astype(str) for k, v in cols.items()})
    df["WKT_GEOM"] = gdf["geometry"].apply(lambda g: dumps(g, rounding_precision=6))
    return df


def main(folder):
    import snowflake.connector
    from snowflake.connector.pandas_tools import write_pandas

    for meta in CENSUS_LAYERS.values():  # before signing in
        if not os.path.exists(os.path.join(folder, meta["zip"])):
            raise FileNotFoundError(os.path.abspath(os.path.join(folder, meta["zip"])))
    ctx = snowflake.connector.connect(
        account=os.environ["SNOWFLAKE_ACCOUNT"], user=os.environ["SNOWFLAKE_USER"],
        warehouse=os.environ["SNOWFLAKE_WAREHOUSE"], database="SSDB_INTEGRATION", schema="LR_STRATEGY",
        role="RL_SSDB_INTEGRATION_LR_STRATEGY_RW", client_store_temporary_credential=True,
        authenticator="externalbrowser")
    cs = ctx.cursor()
    try:
        for layer, meta in CENSUS_LAYERS.items():
            target, tmp = f"CENSUS_{layer.upper()}", f"TMP_CENSUS_{layer.upper()}"
            df = frame(os.path.join(folder, meta["zip"]), meta)
            print(f"{meta['zip']}: {len(df)} rows -> {tmp}")
            write_pandas(conn=ctx, df=df, table_name=tmp, auto_create_table=True, overwrite=True)
            extra = "".join(f"{c}::VARCHAR AS {c.lower()}, " for c in meta.get("extra", []))
            cs.execute(f"""
                CREATE OR REPLACE TABLE {target} AS
                SELECT GEO_ID::VARCHAR AS geo_id, FULLY_QUALIFIED_ID::VARCHAR AS fully_qualified_id,
                       GEO_NAME::VARCHAR AS geo_name, {extra}TO_GEOGRAPHY(WKT_GEOM) AS geo_boundary
                FROM {tmp}""")
            cs.execute(f"DROP TABLE IF EXISTS {tmp}")
            n, bad = cs.execute(f"SELECT COUNT(*), COUNT_IF(geo_boundary IS NULL OR NOT ST_ISVALID(geo_boundary)) "
                                f"FROM {target}").fetchone()
            if (n, bad) != (len(df), 0):
                raise RuntimeError(f"{target}: {n} rows, {bad} invalid or missing shapes, expected {len(df)} and 0")
            print(f"{target}: {n} rows, every shape valid")
    finally:
        cs.close()
        ctx.close()


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "geo"))
