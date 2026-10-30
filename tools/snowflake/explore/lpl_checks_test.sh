#!/bin/sh
# Runs lpl_checks.sql in DuckDB on made-up tables with the real column names and checks its result set, the file's own
# last statement (worked out by hand from the rows below).  Prints "lpl_checks_test: ok" or stops at the first failed
# check.  DuckDB has no TO_CHAR: a macro casts to text, as TO_CHAR does on these columns.
# Run from anywhere: sh lpl_checks_test.sh
set -e
here=$(cd "$(dirname "$0")" && pwd)
{
cat <<'SQL'
ATTACH ':memory:' AS life_prod; CREATE SCHEMA life_prod.lif_murkylake;
ATTACH ':memory:' AS ssdb_integration; CREATE SCHEMA ssdb_integration.lr_strategy;
CREATE MACRO to_char(x) AS CAST(x AS VARCHAR);
CREATE TABLE life_prod.lif_murkylake.wc_market_metrics_opportunity (fiscal_yr TEXT, cbd_id TEXT, client_firm_id TEXT,
  firm_crd TEXT, broker_name TEXT, dist_ch TEXT, global_sales DECIMAL(18,2));
INSERT INTO life_prod.lif_murkylake.wc_market_metrics_opportunity VALUES
  ('2025','0',NULL,'6413','LPL Financial LLC','IFA',100),
  ('2025','0',NULL,'6413','LPL Financial LLC - INDEPENDENT','IFA',200),
  ('2025','287',NULL,'6413','LPL Financial LLC - INDEPENDENT','IFA',50),
  ('2025','0',NULL,'6413','LPL FINANCIAL LLC - BANK','FI',30),
  ('2025','0','287|8','6413','LPL Financial LLC - INSURANCE','IFA',20),
  ('2025','956',NULL,'6413','LPL Financial LLC ','IFA',10),
  ('2025','0',NULL,'6413','Some DBA Name','IFA',5),
  ('2025',NULL,NULL,'6413','LPL Financial, LLC','IFA',1),
  ('2025','0',NULL,'','LPL Financial LLC - BANK','FI',7),
  ('2025','10',NULL,'','Blank Crd Firm','IFA',500),
  ('2025','10',NULL,'1111','Other Firm','IFA',999),
  ('2024','0',NULL,'6413','LPL Financial LLC','IFA',777);
CREATE TABLE life_prod.lif_murkylake.geographic_region (rgn_cd TEXT, start_zip TEXT, cbd INTEGER, distch_channel TEXT,
  expir_dt TIMESTAMP);
INSERT INTO life_prod.lif_murkylake.geographic_region VALUES
  ('R1','021340000',0,'IFA','9999-12-31'), ('R2','021340000',8,'IFA','9999-12-31'), ('R3','100010000',8,'ifa ','9999-12-31'),
  ('R4','606010000',3,'EDWARD JONES','9999-12-31'), ('R5','303010000',8,'IFA','2020-01-01'),
  ('R6','021340000',287,'FI','9999-12-31');
CREATE TABLE life_prod.lif_murkylake.rgn_whslr (whslr_id TEXT, rgn_cd TEXT, expir_dt TIMESTAMP);
INSERT INTO life_prod.lif_murkylake.rgn_whslr VALUES
  ('W1','R1','9999-12-31'), ('W5','R2','9999-12-31'), ('W5','R3','9999-12-31'), ('W3','R4','9999-12-31'),
  ('W6','R5','9999-12-31'), ('W7','R2','2020-01-01'), ('W9','R6','2020-01-01');
CREATE TABLE life_prod.lif_murkylake.wc_edw_consol_brkr_dealer_mga_master (consol_brkr_dealer_id INTEGER,
  consol_brkr_dealer_name TEXT, expiration_dte TIMESTAMP);
INSERT INTO life_prod.lif_murkylake.wc_edw_consol_brkr_dealer_mga_master VALUES
  (8,'LPL FINANCIAL LLC','9999-12-31'), (8,'AAA OLD NAME','2020-01-01'), (3,'EDWARD JONES','9999-12-31');
SQL
sed -e '/^use secondary roles all;$/d' -e 's/TEMPORARY TABLE/TABLE/' \
    -e 's/^SELECT \* FROM ssdb_integration.lr_strategy.tmp_lpl_feed$/CREATE TABLE r AS SELECT * FROM ssdb_integration.lr_strategy.tmp_lpl_feed/' \
    "$here/lpl_checks.sql"
cat <<'SQL'
CREATE MACRO chk(name, got, want) AS CASE WHEN got IS NOT DISTINCT FROM want THEN 'ok'
  ELSE error(name || ': got ' || COALESCE(CAST(got AS VARCHAR), 'NULL') || ', want ' || CAST(want AS VARCHAR)) END;
CREATE MACRO f(n) AS (SELECT company_id FROM r WHERE part = 'LPL FEED ROWS' AND name = n);
SELECT
 chk('feed: rows, fiscal year 2025, LPL names and their CRDs only', (SELECT COUNT(*) || ' ' || SUM(opp) FROM r WHERE part = 'LPL FEED ROWS'), '8 423.00'),
 chk('feed: the three exact names -> 8, whatever the row carries', (SELECT n_rows || ' ' || opp FROM r WHERE company_id = '8' AND name = 'LPL Financial LLC - INDEPENDENT'), '2 250.00'),
 chk('feed: on 8 in total', (SELECT SUM(opp) FROM r WHERE company_id = '8'), 357),
 chk('feed: dropped in total', (SELECT SUM(opp) FROM r WHERE company_id = 'DROPPED (:500)'), 36),
 chk('feed: other case misses the list, company 0 dropped', f('LPL FINANCIAL LLC - BANK'), 'DROPPED (:500)'),
 chk('feed: no company dropped', f('LPL Financial, LLC'), 'DROPPED (:500)'),
 chk('feed: trailing space keeps its own company', f('LPL Financial LLC '), '956'),
 chk('feed: a list goes on to :511-594', f('LPL Financial LLC - INSURANCE'), '287|8'),
 chk('feed: same CRD, other name', (SELECT company_id || ' ' || pct_opp_of_part FROM r WHERE name = 'Some DBA Name'), 'DROPPED (:500) 1.18'),
 chk('feed: blank CRD does not pull in other firms', (SELECT COUNT(*) FROM r WHERE name = 'Blank Crd Firm'), 0),
 chk('feed: pct', (SELECT pct_opp_of_part FROM r WHERE name = 'LPL Financial LLC - INDEPENDENT'), 59.10),
 chk('regions: own regions, current only, label cleaned', (SELECT name || ' ' || label || ' ' || n_regions || ' ' || n_zips || ' ' || n_whslr FROM r WHERE part = 'OWN REGIONS' AND company_id = '8'), 'LPL FINANCIAL LLC IFA 2 2 1'),
 chk('regions: company 3', (SELECT name || ' ' || n_zips FROM r WHERE part = 'OWN REGIONS' AND company_id = '3'), 'EDWARD JONES 1'),
 chk('regions: channel-level and no current wholesaler left out', (SELECT COUNT(*) FROM r WHERE part = 'OWN REGIONS'), 2),
 chk('no renamed duplicate column', (SELECT COUNT(*) FROM duckdb_columns() WHERE table_name IN ('r', 'tmp_lpl_feed', 'tmp_lpl_regions') AND regexp_matches(column_name, '_[0-9]+$')), 0);
SELECT 'lpl_checks_test: ok';
SQL
} | duckdb -bail -noheader -list
