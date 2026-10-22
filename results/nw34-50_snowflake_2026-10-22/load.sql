-- nw34-50 (WIFI 35 + national 15 = 50), gate-verified 2026-10-15. Same 12-column schema as the IFA file
-- and archive/pre-support-2026-09:exports/database/all_scenarios_nationwide_zcta_long.csv.gz.
-- 166,500 rows = 33,300 CONUS ZCTAs x 5 fine channels. Table DDL: results/ifa_snowflake_2026-10-22/ddl.sql.
PUT file://nw34-50_nationwide_zcta_long.csv.gz @%ALL_SCENARIOS_NATIONWIDE_ZCTA_LONG AUTO_COMPRESS=FALSE;
COPY INTO ssdb_integration.lr_strategy.ALL_SCENARIOS_NATIONWIDE_ZCTA_LONG
  FILES=('nw34-50_nationwide_zcta_long.csv.gz')
  FILE_FORMAT=(TYPE=CSV COMPRESSION=GZIP SKIP_HEADER=1 FIELD_OPTIONALLY_ENCLOSED_BY='"');
