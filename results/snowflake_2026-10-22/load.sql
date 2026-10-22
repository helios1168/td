-- WIFI (main) and IFA territory scenarios in one long table: 1,232,100 rows, 13 scenarios.
-- 12-column schema of archive/pre-support-2026-09:exports/database/all_scenarios_nationwide_zcta_long.csv.gz.
-- SCENARIO: WIFI_K<total>_<channel><k>... (N, WH, FI, WIFI order; empty channels left out), IFA_K<k>.
-- Two maps share K48 counts: ne-48-bal is WIFI_K48_N14_WH10_FI21_WIFI3, ne-48-bal-r2 adds _R2.
CREATE TABLE IF NOT EXISTS ssdb_integration.lr_strategy.ALL_SCENARIOS_NATIONWIDE_ZCTA_LONG (
  SCENARIO                   VARCHAR(64) NOT NULL,
  ZIP_CODE                   VARCHAR(5)  NOT NULL,  -- keep leading zeros
  CURRENT_CHANNEL            VARCHAR(32) NOT NULL,
  CANONICAL_CHANNEL          VARCHAR(32) NOT NULL,
  STATE                      VARCHAR(2)  NOT NULL,
  MODEL_CHANNEL              VARCHAR(8)  NOT NULL,
  BUNDLE                     VARCHAR(8)  NOT NULL,
  DISTRICT                   VARCHAR(16) NOT NULL,  -- ids are per scenario; join on (SCENARIO, DISTRICT)
  DISTRICT_CHANNELS          VARCHAR(16),
  REP                        VARCHAR(16),
  M_REL                      FLOAT       NOT NULL,
  HAS_COMMERCIAL_OPPORTUNITY BOOLEAN     NOT NULL,
  PRIMARY KEY (SCENARIO, ZIP_CODE, CANONICAL_CHANNEL)
);
CREATE TABLE IF NOT EXISTS ssdb_integration.lr_strategy.ALL_SCENARIOS_DISTRICTS (
  SCENARIO VARCHAR(64) NOT NULL, CHANNEL VARCHAR(8) NOT NULL, DISTRICT VARCHAR(16) NOT NULL,
  DISTRICT_NAME VARCHAR(128), COPY VARCHAR(32), SUPPORT VARCHAR(32), PLANNED_MASS FLOAT, DRAWN_MASS FLOAT,
  PIECES NUMBER(3,0), SOURCE_RUN VARCHAR(64), SOURCE_DISTRICT VARCHAR(64),
  PRIMARY KEY (SCENARIO, DISTRICT)
);
PUT file://all_scenarios_nationwide_zcta_long.csv.gz @%ALL_SCENARIOS_NATIONWIDE_ZCTA_LONG AUTO_COMPRESS=FALSE;
COPY INTO ssdb_integration.lr_strategy.ALL_SCENARIOS_NATIONWIDE_ZCTA_LONG
  FILE_FORMAT=(TYPE=CSV COMPRESSION=GZIP SKIP_HEADER=1 FIELD_OPTIONALLY_ENCLOSED_BY='"');
PUT file://all_scenarios_districts.csv @%ALL_SCENARIOS_DISTRICTS;   -- PUT gzips it
COPY INTO ssdb_integration.lr_strategy.ALL_SCENARIOS_DISTRICTS
  FILE_FORMAT=(TYPE=CSV SKIP_HEADER=1 FIELD_OPTIONALLY_ENCLOSED_BY='"' EMPTY_FIELD_AS_NULL=TRUE);
-- Check: SELECT SCENARIO, COUNT(*) FROM ssdb_integration.lr_strategy.ALL_SCENARIOS_NATIONWIDE_ZCTA_LONG GROUP BY 1 ORDER BY 1;
--   WIFI_* 166,500 each (33,300 ZCTAs x 5 fine channels); IFA_K* 33,300 each.
