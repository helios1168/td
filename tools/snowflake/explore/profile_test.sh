#!/bin/sh
# Runs profile.sql in DuckDB on made-up tables with the real column names, one planted case per outcome, and checks
# the answers.  Prints "profile_test: ok" or stops at the first failed check.  Run from anywhere: sh profile_test.sh
set -e
here=$(cd "$(dirname "$0")" && pwd)
{
cat <<'SQL'
ATTACH ':memory:' AS life_prod; CREATE SCHEMA life_prod.lif_murkylake;
ATTACH ':memory:' AS ssdb_integration; CREATE SCHEMA ssdb_integration.lr_strategy;
CREATE TABLE life_prod.lif_murkylake.wc_market_metrics_opportunity (fiscal_yr TEXT, quarter TEXT, cbd_id TEXT,
  client_firm_id TEXT, firm_crd TEXT, broker_name TEXT, dist_ch TEXT, channel TEXT, product_line TEXT,
  va_product_type TEXT, zip_code TEXT, global_sales DECIMAL(18,2));
INSERT INTO life_prod.lif_murkylake.wc_market_metrics_opportunity VALUES
  ('2025','Q1','10',NULL,'1000','BD ONE','IFA','X','VA','IOVA','2134',500),
  ('2025','Q1','0',NULL,'3000','BD THREE','WH','X','IA',NULL,'10001',300),
  ('2025','Q2','11',NULL,'1000',' bd one','fi','X','VA',NULL,'02134',200),
  ('2025','Q2','20',NULL,'','BD TWO','FI','X','RILA',NULL,'10001',100),
  ('2024','Q4','10',NULL,'1000','BD ONE','IFA','X','VA','IOVA','2134',9999);
CREATE TABLE ssdb_integration.lr_strategy.s1_terr_t (whslr_id TEXT, whslr_nm TEXT, zip TEXT, state_cd TEXT,
  new_dist_channel TEXT);
INSERT INTO ssdb_integration.lr_strategy.s1_terr_t VALUES
  ('W1','N1','02134','MA','IFA'), ('W3','N3','2134','MA','IFA'), ('W2','N2','10001','NY','WH');
CREATE TABLE life_prod.lif_murkylake.geographic_region (rgn_cd TEXT, start_zip TEXT, end_zip TEXT, cbd INTEGER,
  expir_dt TIMESTAMP);
INSERT INTO life_prod.lif_murkylake.geographic_region VALUES
  ('R1','02134','02134',0,'9999-12-31'), ('R2','10001','10099',0,'9999-12-31'), ('R3','99999','99999',0,'2020-01-01');
CREATE TABLE life_prod.lif_murkylake.rgn_whslr (whslr_id TEXT, rgn_cd TEXT, expir_dt TIMESTAMP);
INSERT INTO life_prod.lif_murkylake.rgn_whslr VALUES ('W1','R1','9999-12-31'), ('W2','R2','9999-12-31');
CREATE TABLE ssdb_integration.lr_strategy.s2_opp_t (channel DOUBLE, dist_ch TEXT, zip_code DECIMAL(38,0),
  firm_crd DECIMAL(38,0), broker_name TEXT, product_line TEXT, va_product_type TEXT, opp DOUBLE);
INSERT INTO ssdb_integration.lr_strategy.s2_opp_t VALUES
  (NULL,'IND',2134,1000,'BD ONE','VA','X',40), (NULL,'WIRE',10001,3000,'BD THREE','IA',NULL,60),
  (NULL,'IND',30301,4000,'BD FOUR','IA',NULL,25), (NULL,'NO CHANNEL',12345,NULL,'X','IA',NULL,5);
CREATE TABLE ssdb_integration.lr_strategy.crd_dist_override (firm_crd VARCHAR, broker_name VARCHAR, dist_ch VARCHAR);
INSERT INTO ssdb_integration.lr_strategy.crd_dist_override VALUES ('1000', NULL, 'IFA');
CREATE TABLE ssdb_integration.lr_strategy.s2_terr_t (rvp TEXT, territory_id TEXT, zipcode TEXT, state TEXT,
  channel TEXT, channel_name TEXT);
INSERT INTO ssdb_integration.lr_strategy.s2_terr_t VALUES
  ('RVP1','T1','02134','MA','IND','Independent'), ('RVP2','T2','10001','NY','WIRE','Wirehouse');
SQL
sed -e '/^use secondary roles all;$/d' -e 's/TEMPORARY TABLE/TABLE/' \
    -e 's/<S1_TERRITORIES>/s1_terr_t/g' -e 's/<S2_OPP>/s2_opp_t/g' -e 's/<S2_TERRITORIES>/s2_terr_t/g' \
    -e '/^--8\./,$d' "$here/profile.sql"
cat <<'SQL'
CREATE TABLE r AS
SELECT * FROM ssdb_integration.lr_strategy.tmp_prof_cols
UNION ALL SELECT * FROM ssdb_integration.lr_strategy.tmp_prof_pairs
UNION ALL SELECT * FROM ssdb_integration.lr_strategy.tmp_prof_matches
UNION ALL SELECT * FROM ssdb_integration.lr_strategy.tmp_prof_labels
UNION ALL SELECT * FROM ssdb_integration.lr_strategy.tmp_prof_checks;
CREATE MACRO chk(name, got, want) AS CASE WHEN got IS NOT DISTINCT FROM want THEN 'ok'
  ELSE error(name || ': got ' || COALESCE(CAST(got AS VARCHAR), 'NULL') || ', want ' || CAST(want AS VARCHAR)) END;
CREATE MACRO m(d, c, c2, i) AS (SELECT amt FROM r WHERE part = 'MATCHES' AND ds = d AND col = c AND col2 = c2 AND item = i);
SELECT
 chk('fiscal year 2025 only', (SELECT amt FROM r WHERE part='COLUMNS' AND ds='S1_OPP_FIRM' AND col='FIRM_CRD'), 1100),
 chk('blank CRD is missing', (SELECT pct_amt FROM r WHERE part='COLUMNS' AND ds='S1_OPP_FIRM' AND col='FIRM_CRD'), 9.09),
 chk('company 0 is missing', (SELECT pct_amt FROM r WHERE part='COLUMNS' AND ds='S1_OPP_FIRM' AND col='CBD_ID'), 27.27),
 chk('firm on 2 channels', (SELECT amt FROM r WHERE part='PAIRS' AND ds='S1_OPP_FIRM' AND col='DIST_CH' AND col2='FIRM_CRD' AND item='many DIST_CH, one FIRM_CRD'), 700),
 chk('CRD on 2 company IDs', (SELECT amt FROM r WHERE part='PAIRS' AND ds='S1_OPP_FIRM' AND col='CBD_ID' AND col2='FIRM_CRD' AND item='many CBD_ID, one FIRM_CRD'), 700),
 chk('broker name variants merge', (SELECT n_values FROM r WHERE part='COLUMNS' AND ds='S1_OPP_FIRM' AND col='BROKER_NAME'), 3),
 chk('opp cell with 2 holders', m('S1_OPP_GEO', 'CH_ZIP', 'S1_TERR.CH_ZIP', '2+'), 500),
 chk('opp cell with 1 holder', m('S1_OPP_GEO', 'CH_ZIP', 'S1_TERR.CH_ZIP', '1'), 300),
 chk('opp cell with no holder', m('S1_OPP_GEO', 'CH_ZIP', 'S1_TERR.CH_ZIP', '0'), 300),
 chk('padded ZIP meets territory ZIP', m('S1_OPP_GEO', 'ZIP', 'S1_TERR.ZIP', '2+'), 700),
 chk('s2 firm with 2 source 1 channels', m('S2_OPP_FIRM', 'FIRM_CRD', 'S1_CRD_CH.FIRM_CRD', '2+'), 40),
 chk('s2 firm with 1 source 1 channel', m('S2_OPP_FIRM', 'FIRM_CRD', 'S1_CRD_CH.FIRM_CRD', '1'), 60),
 chk('s2 firm not in source 1', m('S2_OPP_FIRM', 'FIRM_CRD', 'S1_CRD_CH.FIRM_CRD', '0'), 25),
 chk('s2 row with no CRD', m('S2_OPP_FIRM', 'FIRM_CRD', 'S1_CRD_CH.FIRM_CRD', 'no value'), 5),
 chk('override covers its CRD', m('S2_OPP_FIRM', 'FIRM_CRD', 'S2_OVERRIDE.FIRM_CRD', '1'), 40),
 chk('s1 firm also in source 2', m('S1_OPP_FIRM', 'FIRM_CRD', 'S2_OPP_FIRM.FIRM_CRD', '1'), 1000),
 chk('numeric ZIP padded, meets s2 territory', m('S2_OPP_GEO', 'CH_ZIP', 'S2_TERR.CH_ZIP', '1'), 100),
 chk('s2 cell with no holder', m('S2_OPP_GEO', 'CH_ZIP', 'S2_TERR.CH_ZIP', '0'), 30),
 chk('IOVA label', (SELECT amt FROM r WHERE part='LABELS' AND ds='S1_OPP_FIRM' AND col='VA_PRODUCT_TYPE' AND item='IOVA'), 500),
 chk('channel labels upper-cased', (SELECT amt FROM r WHERE part='LABELS' AND ds='S1_OPP_FIRM' AND col='DIST_CH' AND item='FI'), 300),
 chk('s2 channel label', (SELECT amt FROM r WHERE part='LABELS' AND ds='S2_OPP_FIRM' AND col='DIST_CH' AND item='IND'), 65),
 chk('region ZIP range', (SELECT n_rows FROM r WHERE part='CHECKS' AND col='START_ZIP_VS_END_ZIP' AND item='range'), 1),
 chk('territory table vs regions', (SELECT string_agg(item || '=' || n_rows, ' ' ORDER BY item) FROM r WHERE part='CHECKS' AND col='WHSLR_ZIP_VS_REGIONS'), 'both=2 table only=1'),
 chk('ZIP lost its zero', (SELECT amt FROM r WHERE part='CHECKS' AND ds='S1_OPP' AND col='ZIP_FORM' AND item='under 5 digits'), 500),
 chk('s2 ZIP stored as a number', (SELECT amt FROM r WHERE part='CHECKS' AND ds='S2_OPP' AND col='ZIP_FORM' AND item='under 5 digits'), 40),
 chk('label x firm channel: one', (SELECT amt FROM r WHERE part='CHECKS' AND col='S2 DIST_CH -> S1 CHANNEL OF THE CRD' AND item='WIRE -> WH'), 60),
 chk('label x firm channel: 2+, override', (SELECT amt FROM r WHERE part='CHECKS' AND col='S2 DIST_CH -> S1 CHANNEL OF THE CRD' AND item='IND -> 2+ CHANNELS (OVERRIDE)'), 40),
 chk('label x firm channel: absent', (SELECT amt FROM r WHERE part='CHECKS' AND col='S2 DIST_CH -> S1 CHANNEL OF THE CRD' AND item='IND -> NO SOURCE 1 ROWS'), 25),
 chk('label x firm channel: no CRD', (SELECT amt FROM r WHERE part='CHECKS' AND col='S2 DIST_CH -> S1 CHANNEL OF THE CRD' AND item='NO CHANNEL -> NO CRD'), 5),
 chk('periods', (SELECT amt FROM r WHERE part='CHECKS' AND col='FISCAL_YR | QUARTER' AND item='2025 | Q2'), 300),
 chk('no renamed duplicate column', (SELECT COUNT(*) FROM duckdb_columns() WHERE table_name LIKE 'tmp_prof%' AND regexp_matches(column_name, '_[0-9]+$')), 0);
SELECT 'profile_test: ok';
SQL
} | duckdb -bail -noheader -list
