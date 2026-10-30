#!/bin/sh
# Runs amer_holder.sql in DuckDB on made-up tables with the real column names and checks the answers (worked out by
# hand from the rows below).  Prints "amer_holder_test: ok" or stops at the first failed check.  sed maps
# $company_id to '805' and LISTAGG ... WITHIN GROUP to string_agg(... ORDER BY ...).  Run from anywhere.
set -e
here=$(cd "$(dirname "$0")" && pwd)
{
cat <<'SQL'
ATTACH ':memory:' AS life_prod; CREATE SCHEMA life_prod.lif_murkylake;
ATTACH ':memory:' AS ssdb_integration; CREATE SCHEMA ssdb_integration.lr_strategy;
CREATE TABLE life_prod.lif_murkylake.geographic_region (rgn_cd TEXT, start_zip TEXT, end_zip TEXT, cbd INTEGER,
  distch_channel TEXT, sales_team_id TEXT, expir_dt TIMESTAMP);
INSERT INTO life_prod.lif_murkylake.geographic_region VALUES
  ('R1','02134','02134',0,'IFA','T1','9999-12-31'), ('R2','021340000','021349999',805,'IFA','T2','9999-12-31'),
  ('R3','10001','10001',805,'IFA','T2','9999-12-31'), ('R4','60601','60601',3,'EDWARD JONES','T3','9999-12-31'),
  ('R5','30301','30301',805,'IFA','T2','2020-01-01'), ('R6','10001','10001',0,'FI','T4','9999-12-31');
CREATE TABLE life_prod.lif_murkylake.rgn_whslr (whslr_id TEXT, rgn_cd TEXT, expir_dt TIMESTAMP);
INSERT INTO life_prod.lif_murkylake.rgn_whslr VALUES
  ('W1','R1','9999-12-31'), ('W5','R2','9999-12-31'), ('W5','R3','9999-12-31'), ('W3','R4','9999-12-31'),
  ('W6','R5','9999-12-31'), ('W8','R6','9999-12-31'), ('W7','R3','2020-01-01');
CREATE TABLE life_prod.lif_murkylake.wc_sales_team (sales_team_id TEXT, sales_team_name TEXT);
INSERT INTO life_prod.lif_murkylake.wc_sales_team VALUES
  ('T1','INDEPENDENT FA'), ('T2','NATIONAL ACCOUNTS'), ('T3','EDJ TEAM'), ('T4','WIFI');
CREATE TABLE life_prod.lif_murkylake.whslr (whslr_id TEXT, distch TEXT, sales_district_id TEXT);
INSERT INTO life_prod.lif_murkylake.whslr VALUES ('W1','IFA','D1'), ('W5','WH','D2'), ('W5','WH','D2'), ('W3','EDJ','D3');
CREATE TABLE life_prod.lif_murkylake.wc_sales_district (sales_district_id TEXT, sales_team_id TEXT);
INSERT INTO life_prod.lif_murkylake.wc_sales_district VALUES ('D1','T1'), ('D2','T2'), ('D3','T3');
CREATE TABLE life_prod.lif_murkylake.wc_market_metrics_opportunity (fiscal_yr TEXT, cbd_id TEXT, zip_code TEXT,
  global_sales DECIMAL(18,2));
INSERT INTO life_prod.lif_murkylake.wc_market_metrics_opportunity VALUES
  ('2025','805','02134',60), ('2025',' 805','10001',30), ('2025','805','99999',10), ('2024','805','02134',999),
  ('2025','10','02134',500);
CREATE TABLE life_prod.lif_murkylake.sls_rpt_detail (fiscal_yr INTEGER, consol_brkr_dlr_id DECIMAL(38,0), whslr_id TEXT,
  actual_sales_amount DECIMAL(18,2), bonus_rate DECIMAL(9,4), init_pay_in TEXT, agent_tax_id TEXT);
INSERT INTO life_prod.lif_murkylake.sls_rpt_detail VALUES
  (2025,805,'W5',70,1,'Y','A1'), (2025,805,'W1',30,1,'Y','A2'), (2025,805,'W1',999,0,'Y','A3'),
  (2025,10,'W1',500,1,'Y','A4'), (2024,805,'W5',999,1,'Y','A5');
SQL
sed -E -e '/^use secondary roles all;$/d' -e '/^SET company_id/d' -e 's/TEMPORARY TABLE/TABLE/' \
    -e "s/\\\$company_id/'805'/g" \
    -e "s/LISTAGG\(DISTINCT ([a-z_]+), ('[^']*')\) WITHIN GROUP \(ORDER BY [a-z_]+\)/string_agg(DISTINCT \1, \2 ORDER BY \1)/g" \
    -e '/^--5\./,$d' "$here/amer_holder.sql"
cat <<'SQL'
CREATE TABLE r AS
SELECT * FROM ssdb_integration.lr_strategy.tmp_aq_regions
UNION ALL SELECT * FROM ssdb_integration.lr_strategy.tmp_aq_cov
UNION ALL SELECT * FROM ssdb_integration.lr_strategy.tmp_aq_sellers;
CREATE MACRO chk(name, got, want) AS CASE WHEN got IS NOT DISTINCT FROM want THEN 'ok'
  ELSE error(name || ': got ' || COALESCE(CAST(got AS VARCHAR), 'NULL') || ', want ' || CAST(want AS VARCHAR)) END;
CREATE MACRO g(p, i) AS (SELECT pct FROM r WHERE part = p AND item = i);
SELECT
 chk('own regions, current only', (SELECT n_regions || ' ' || n_zips || ' ' || n_whslr FROM r WHERE part='COMPANY REGIONS' AND item='805'), '2 2 1'),
 chk('own regions: label and team', (SELECT labels || ' / ' || teams FROM r WHERE part='COMPANY REGIONS' AND item='805'), 'IFA / NATIONAL ACCOUNTS'),
 chk('channel-level regions', (SELECT labels || ' / ' || n_regions FROM r WHERE part='COMPANY REGIONS' AND item='0 (CHANNEL-LEVEL)'), 'FI | IFA / 2'),
 chk('company 3 listed', (SELECT n_zips FROM r WHERE part='COMPANY REGIONS' AND item='3'), 1),
 chk('coverage: own region (ZIP+4 range read as its ZIP)', g('COMPANY OPPORTUNITY COVERAGE', 'OWN REGION'), 90.0),
 chk('coverage: channel-level IFA', g('COMPANY OPPORTUNITY COVERAGE', 'CHANNEL-LEVEL IFA'), 60.0),
 chk('coverage: channel-level FI', g('COMPANY OPPORTUNITY COVERAGE', 'CHANNEL-LEVEL FI'), 30.0),
 chk('coverage: neither', g('COMPANY OPPORTUNITY COVERAGE', 'NO OWN OR CHANNEL-LEVEL REGION'), 10.0),
 chk('coverage: total, fiscal year 2025, company only', (SELECT n_zips || ' ' || pct FROM r WHERE part='COMPANY OPPORTUNITY COVERAGE' AND item='TOTAL'), '3 100.0'),
 chk('sellers by channel, repeated WHSLR row once', g('WHO SELLS TO THE COMPANY', 'SELLER CHANNEL WH'), 70.0),
 chk('sellers by team', g('WHO SELLS TO THE COMPANY', 'SELLER TEAM INDEPENDENT FA'), 30.0),
 chk('seller holds an own region', g('WHO SELLS TO THE COMPANY', 'SELLER HOLDS AN OWN REGION: YES'), 70.0),
 chk('filtered sale left out', (SELECT n_whslr FROM r WHERE part='WHO SELLS TO THE COMPANY' AND item='SELLER HOLDS AN OWN REGION: NO'), 1),
 chk('no renamed duplicate column', (SELECT COUNT(*) FROM duckdb_columns() WHERE table_name LIKE 'tmp_aq%' AND regexp_matches(column_name, '_[0-9]+$')), 0);
SELECT 'amer_holder_test: ok';
SQL
} | duckdb -bail -noheader -list
