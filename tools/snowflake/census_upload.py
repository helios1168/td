import os
import geopandas as gpd
from shapely.wkt import dumps
import pandas as pd
import snowflake.connector
from snowflake.connector.pandas_tools import write_pandas

# ==========================================
# 1. PATH & SCHEMA CONFIGURATION
# ==========================================
# UPDATE THIS: Set the path to the folder where your file lives
# ==========================================
# 1. PATH & SCHEMA CONFIGURATION
# ==========================================
DOWNLOAD_DIR = "./"

# Target the exact verified cartographic shapefile archive you downloaded
GEOPACKAGE_ZIP = "cb_2025_us_state_500k.zip"
FULL_LOCAL_PATH = os.path.join(DOWNLOAD_DIR, GEOPACKAGE_ZIP)

CENSUS_LAYERS = {
    "states": {
        "layer_name": "cb_2025_us_state_500k.zip", 
        "id_col": "GEOID", 
        "name_col": "NAME"
    }
}
# Snowflake Credentials Configuration
SNOWFLAKE_CREDS = {
    "account": "YOUR_ACCOUNT_LOCATOR",
    "user": "YOUR_USERNAME",
    "password": "YOUR_PASSWORD",
    "role": "SYSADMIN",
    "warehouse": "YOUR_WAREHOUSE",
    "database": "YOUR_DATABASE",
    "schema": "YOUR_SCHEMA"
}

# ==========================================
# 2. LOCAL PROCESSING & LOADING ENGINE
# ==========================================
# ==========================================
# 2. LOCAL PROCESSING & LOADING ENGINE
# ==========================================
def ingest_local_geopackage():
    # Verify the file actually exists before starting database channels
    if not os.path.exists(FULL_LOCAL_PATH):
        raise FileNotFoundError(
            f"Could not find the file at: {os.path.abspath(FULL_LOCAL_PATH)}. "
            f"Please verify your DOWNLOAD_DIR variable."
        )
        
    print(f"Targeting local archive: {FULL_LOCAL_PATH}")
    print("--- Initializing Snowflake Native DB Connection ---")
    ctx = snowflake.connector.connect(
        user='<user>',
        account='<account>',
        warehouse='WH_LIFE_GP_XS',
        database='SSDB_INTEGRATION',
        schema='LR_STRATEGY',
        role='RL_SSDB_INTEGRATION_LR_STRATEGY_RW',
        client_store_temporary_credential=True,
        authenticator='externalbrowser'
    )

    cs = ctx.cursor()
    
    try:
        for layer_key, meta in CENSUS_LAYERS.items():
            target_table = f"CENSUS_{layer_key.upper()}"
            tmp_table = f"TMP_{target_table}"
            
            print(f"\n[Ingesting Shapefile Archive: {FULL_LOCAL_PATH}]")
            
            # Form virtual pointer path inside the compressed zip shapefile bundle natively
            shapefile_uri = f"zip://{FULL_LOCAL_PATH}"
            
            print(f"Reading zipped shapefile layers via spatial engine...")
            try:
                # Read the zipped shapefile directly and instantly project to standard WGS84 coordinates
                gdf = gpd.read_file(shapefile_uri).to_crs(epsg=4326)
            except Exception as layer_err:
                print(f"❌ Error loading shapefile layer: {layer_err}")
                print("Skipping layout layer definition block.")
                continue
                
            # Safely capture any newly retired/renamed ID headers (GEOIDFQ vs AFFGEOID)
            fq_id_col = "GEOIDFQ" if "GEOIDFQ" in gdf.columns else (
                "AFFGEOID" if "AFFGEOID" in gdf.columns else meta["id_col"]
            )
            
            print("Serializing high-precision vectors to string structures...")
            gdf['WKT_GEOM'] = gdf['geometry'].apply(lambda g: dumps(g, rounding_precision=6))
            
            # Map into a clean Pandas dataframe structure
            pandas_df = pd.DataFrame({
                'GEO_ID': gdf[meta['id_col']].astype(str),
                'FULLY_QUALIFIED_ID': gdf[fq_id_col].astype(str),
                'GEO_NAME': gdf[meta['name_col']].astype(str),
                'WKT_GEOM': gdf['WKT_GEOM'].astype(str)
            })
            
            print(f"Streaming data elements to staging array table: {tmp_table}...")
            write_pandas(
                conn=ctx,
                df=pandas_df,
                table_name=tmp_table,
                auto_create_table=True,
                overwrite=True
            )
            
            print(f"Materializing permanent Snowflake GEOGRAPHY object layer: {target_table}")
            cs.execute(f"""
                CREATE OR REPLACE TABLE {target_table} AS
                SELECT 
                    GEO_ID::VARCHAR AS geo_id,
                    FULLY_QUALIFIED_ID::VARCHAR AS fully_qualified_id,
                    GEO_NAME::VARCHAR AS geo_name,
                    TO_GEOGRAPHY(WKT_GEOM) AS geo_boundary
                FROM {tmp_table};
            """)
            
            cs.execute(f"DROP TABLE IF EXISTS {tmp_table};")
            print(f"✅ Layer {target_table} is fully loaded and structurally indexed.")
            
    finally:
        cs.close()
        ctx.close()
        print("\nAll database channels closed. Ingestion pipeline complete.")

if __name__ == "__main__":
    ingest_local_geopackage()

