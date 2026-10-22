-- IFA K48-K54 (sealed 2026-10-14; maps rendered 2026-10-17). Target schema: confirm before running.
CREATE OR REPLACE TABLE ssdb_integration.lr_strategy.IFA_MAP_LEDGER (
  MAP_ID            VARCHAR(32)  NOT NULL,  -- IFA_K<k>_sealed_2026-10-14
  K                 NUMBER(3,0)  NOT NULL,  -- district count, 48..54
  SCENARIO          VARCHAR(32)  NOT NULL,  -- ifa_conus_merge
  ZIP_CODE          VARCHAR(5)   NOT NULL,  -- 2025 ZCTA, keep leading zeros
  CURRENT_CHANNEL   VARCHAR(8)   NOT NULL,  -- ifa
  STATE             VARCHAR(2)   NOT NULL,
  MODEL_CHANNEL     VARCHAR(8)   NOT NULL,  -- IFA
  DISTRICT          VARCHAR(8)   NOT NULL,  -- IFA_01..IFA_54 (ids are per K, not stable across K)
  DISTRICT_CHANNELS VARCHAR(16)  NOT NULL,
  REP               VARCHAR(16),            -- empty in every row
  COUNTY            VARCHAR(5)   NOT NULL,  -- county FIPS
  CBSA              VARCHAR(5),
  PLACE             VARCHAR(7),             -- place FIPS
  DISTRICT_NAME     VARCHAR(128) NOT NULL,
  M_REL             FLOAT        NOT NULL,  -- descaled opportunity
  REASON            VARCHAR(128),
  PRIMARY KEY (K, ZIP_CODE, MODEL_CHANNEL)
);
CREATE OR REPLACE TABLE ssdb_integration.lr_strategy.IFA_MAP_DISTRICTS (
  MAP_ID          VARCHAR(32)  NOT NULL,
  K               NUMBER(3,0)  NOT NULL,
  CHANNEL         VARCHAR(8)   NOT NULL,
  DISTRICT        VARCHAR(8)   NOT NULL,
  DISTRICT_NAME   VARCHAR(128) NOT NULL,
  COPY            VARCHAR(32)  NOT NULL,
  SUPPORT         VARCHAR(32)  NOT NULL,  -- states the district spans, e.g. CT+RI
  PLANNED_MASS    FLOAT        NOT NULL,  -- m_rel units
  DRAWN_MASS      FLOAT        NOT NULL,  -- m_rel units
  PIECES          NUMBER(3,0)  NOT NULL,
  SOURCE_RUN      VARCHAR(32)  NOT NULL,
  SOURCE_DISTRICT VARCHAR(8)   NOT NULL,
  "WINDOW"        VARCHAR(8)   NOT NULL,  -- reserved word: keep quoted
  PRIMARY KEY (K, DISTRICT)
);
CREATE OR REPLACE FILE FORMAT ssdb_integration.lr_strategy.IFA_CSV
  TYPE=CSV SKIP_HEADER=1 FIELD_OPTIONALLY_ENCLOSED_BY='"' EMPTY_FIELD_AS_NULL=TRUE NULL_IF=('');
-- Snowsight: Load data into table, or SnowSQL:
-- PUT file://ifa_ledger_k48_k54.csv    @%IFA_MAP_LEDGER;    COPY INTO ssdb_integration.lr_strategy.IFA_MAP_LEDGER    FILE_FORMAT=(FORMAT_NAME='ssdb_integration.lr_strategy.IFA_CSV');
-- PUT file://ifa_districts_k48_k54.csv @%IFA_MAP_DISTRICTS; COPY INTO ssdb_integration.lr_strategy.IFA_MAP_DISTRICTS FILE_FORMAT=(FORMAT_NAME='ssdb_integration.lr_strategy.IFA_CSV');
-- Checks: 233,100 ledger rows (33,300 per K); 357 district rows (sum 48..54).

-- ===== Same 12-column schema as exports/database/all_scenarios_nationwide_zcta_long.csv.gz =====
-- File: ifa_k48_k54_nationwide_zcta_long.csv.gz (233,100 rows = 7 scenarios x 33,300 CONUS ZCTAs; gzip, header row)
-- To append to the existing table instead, skip CREATE and COPY INTO that table.
CREATE TABLE IF NOT EXISTS ssdb_integration.lr_strategy.ALL_SCENARIOS_NATIONWIDE_ZCTA_LONG (
  SCENARIO                   VARCHAR(64) NOT NULL,
  ZIP_CODE                   VARCHAR(5)  NOT NULL,
  CURRENT_CHANNEL            VARCHAR(32) NOT NULL,
  CANONICAL_CHANNEL          VARCHAR(32) NOT NULL,
  STATE                      VARCHAR(2)  NOT NULL,
  MODEL_CHANNEL              VARCHAR(8)  NOT NULL,
  BUNDLE                     VARCHAR(8)  NOT NULL,
  DISTRICT                   VARCHAR(16) NOT NULL,
  DISTRICT_CHANNELS          VARCHAR(16),
  REP                        VARCHAR(16),
  M_REL                      FLOAT       NOT NULL,
  HAS_COMMERCIAL_OPPORTUNITY BOOLEAN     NOT NULL,
  PRIMARY KEY (SCENARIO, ZIP_CODE, CANONICAL_CHANNEL)
);
-- PUT file://ifa_k48_k54_nationwide_zcta_long.csv.gz @%ALL_SCENARIOS_NATIONWIDE_ZCTA_LONG AUTO_COMPRESS=FALSE;
-- COPY INTO ssdb_integration.lr_strategy.ALL_SCENARIOS_NATIONWIDE_ZCTA_LONG
--   FILE_FORMAT=(TYPE=CSV COMPRESSION=GZIP SKIP_HEADER=1 FIELD_OPTIONALLY_ENCLOSED_BY='"');
