-- Main maps, six scenarios (999,000 rows = 6 x 33,300 CONUS ZCTAs x 5 fine channels), 12-column schema of
-- archive/pre-support-2026-09:exports/database/all_scenarios_nationwide_zcta_long.csv.gz.
-- Table DDL: results/ifa_snowflake_2026-10-22/ddl.sql (ALL_SCENARIOS_NATIONWIDE_ZCTA_LONG).
-- Includes nw34-50: do not also load the earlier nw34-50 file.
PUT file://main_6_nationwide_zcta_long.csv.gz @%ALL_SCENARIOS_NATIONWIDE_ZCTA_LONG AUTO_COMPRESS=FALSE;
COPY INTO ssdb_integration.lr_strategy.ALL_SCENARIOS_NATIONWIDE_ZCTA_LONG
  FILES=('main_6_nationwide_zcta_long.csv.gz')
  FILE_FORMAT=(TYPE=CSV COMPRESSION=GZIP SKIP_HEADER=1 FIELD_OPTIONALLY_ENCLOSED_BY='"');
-- Check: SELECT scenario, COUNT(*) FROM ssdb_integration.lr_strategy.ALL_SCENARIOS_NATIONWIDE_ZCTA_LONG GROUP BY 1;  -- 166,500 each
