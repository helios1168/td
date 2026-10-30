#!/bin/sh
# Runs profile.sql in DuckDB on made-up tables with the real column names, one planted case per outcome, and checks
# the answers (worked out by hand from the rows below).  Prints "profile_test: ok" or stops at the first failed check.
# Run from anywhere: sh profile_test.sh
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
  ('2025','Q1','10',NULL,'1000','BD ONE','IFA','01','VA','IOVA','2134',500),
  ('2025','Q1','0',NULL,'3000','BD THREE','WH','11','IA',NULL,'10001',300),
  ('2025','Q2','11',NULL,'1000',' bd one','fi','11','VA',NULL,'02134',200),
  ('2025','Q2','20',NULL,'','BD TWO','FI','11','RILA',NULL,'10001',100),
  ('2025','Q3','50',NULL,'5000','BD FIVE','IFA','01','IA',NULL,'90210',50),
  ('2025','Q3','51',NULL,'5000','BD FIVE','FI','11','IA',NULL,'90211',50),
  ('2025','Q4','685',NULL,'6000','BD SIX','IFA','01','IA',NULL,'60601',40),
  ('2025','Q4','70',NULL,'7000','BD SEVEN','EDWARD JONES','13','IA',NULL,'60601',30),
  ('2025','Q4','30',NULL,'3000','BD THREE','','08','IA',NULL,'10002',20),
  ('2025','Q4','80',NULL,'8000','BD EIGHT','','10','IA',NULL,'30301',10),
  ('2024','Q4','10',NULL,'1000','BD ONE','IFA','01','VA','IOVA','2134',9999);
CREATE TABLE ssdb_integration.lr_strategy.s1_channel_rule (rule_order INTEGER, cbd_id VARCHAR, broker_name VARCHAR,
  dist_ch VARCHAR, channel VARCHAR);
INSERT INTO ssdb_integration.lr_strategy.s1_channel_rule VALUES
  (1, '685', NULL, NULL, 'PRI'), (3, NULL, 'BD SIX', NULL, 'WH'), (6, NULL, NULL, 'EDWARD JONES', 'EDJ');
CREATE TABLE ssdb_integration.lr_strategy.s1_terr_t (whslr_id TEXT, whslr_nm TEXT, zip TEXT, state_cd TEXT,
  new_dist_channel TEXT);
INSERT INTO ssdb_integration.lr_strategy.s1_terr_t VALUES
  ('W1','N1','02134','MA','IFA'), ('W3','N3','2134','MA','IFA'), ('W2','N2','10001','NY','WH'), ('W4','N4','60601','IL','EDJ');
CREATE TABLE life_prod.lif_murkylake.geographic_region (rgn_cd TEXT, start_zip TEXT, end_zip TEXT, cbd INTEGER,
  expir_dt TIMESTAMP);
INSERT INTO life_prod.lif_murkylake.geographic_region VALUES
  ('R1','02134','02134',0,'9999-12-31'), ('R2','10001','10099',0,'9999-12-31'), ('R3','99999','99999',0,'2020-01-01'),
  ('R4','021340000','021349999',0,'9999-12-31');
CREATE TABLE life_prod.lif_murkylake.rgn_whslr (whslr_id TEXT, rgn_cd TEXT, expir_dt TIMESTAMP);
INSERT INTO life_prod.lif_murkylake.rgn_whslr VALUES ('W1','R1','9999-12-31'), ('W2','R2','9999-12-31');
CREATE TABLE ssdb_integration.lr_strategy.s2_opp_t (channel DOUBLE, dist_ch TEXT, zip_code DECIMAL(38,0),
  firm_crd DECIMAL(38,0), broker_name TEXT, product_line TEXT, va_product_type TEXT, opp DOUBLE);
INSERT INTO ssdb_integration.lr_strategy.s2_opp_t VALUES
  (NULL,'IND',2134,1000,'BD ONE','VA','X',40), (NULL,'WIRE',10001,3000,'BD THREE','IA',NULL,60),
  (NULL,'IND',30301,4000,'BD FOUR','IA',NULL,25), (NULL,'NO CHANNEL',12345,NULL,'X','IA',NULL,5),
  (NULL,'WIRE',99999,3000,'BD THREE','IA',NULL,7), (NULL,'BANK',10001,3000,'BD THREE - BANK','IA',NULL,3),
  (NULL,'RA',30301,8000,'BD EIGHT','IA',NULL,9);
CREATE TABLE ssdb_integration.lr_strategy.crd_dist_override (firm_crd VARCHAR, broker_name VARCHAR, dist_ch VARCHAR);
INSERT INTO ssdb_integration.lr_strategy.crd_dist_override VALUES
  ('1000', NULL, 'IFA'), ('1000', NULL, 'IFA'), ('3000', 'BD THREE', 'FI'), ('9999', NULL, 'WH');
CREATE TABLE ssdb_integration.lr_strategy.s2_terr_t (rvp TEXT, territory_id TEXT, zipcode TEXT, state TEXT,
  channel TEXT, channel_name TEXT);
INSERT INTO ssdb_integration.lr_strategy.s2_terr_t VALUES
  ('RVP1','T1','02134','MA','IND','Independent'), ('RVP2','T2','10001','NY','WIRE','Wirehouse');
SQL
sed -e '/^use secondary roles all;$/d' -e '/^SET s[12]_/d' -e 's/TEMPORARY TABLE/TABLE/' \
    -e 's/IDENTIFIER(\$s1_territories)/ssdb_integration.lr_strategy.s1_terr_t/g' \
    -e 's/IDENTIFIER(\$s2_opp)/ssdb_integration.lr_strategy.s2_opp_t/g' \
    -e 's/IDENTIFIER(\$s2_territories)/ssdb_integration.lr_strategy.s2_terr_t/g' \
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
CREATE MACRO k(c, i) AS (SELECT amt FROM r WHERE part = 'CHECKS' AND col = c AND item = i);
CREATE MACRO kn(c, i) AS (SELECT n_rows FROM r WHERE part = 'CHECKS' AND col = c AND item = i);
CREATE MACRO lab(d, c, i) AS (SELECT amt FROM r WHERE part = 'LABELS' AND ds = d AND col = c AND item = i);
SELECT
 chk('fiscal year 2025 only', (SELECT amt FROM r WHERE part='COLUMNS' AND ds='S1_OPP_FIRM' AND col='FIRM_CRD'), 1300),
 chk('blank CRD is missing', (SELECT pct_amt FROM r WHERE part='COLUMNS' AND ds='S1_OPP_FIRM' AND col='FIRM_CRD'), 7.69),
 chk('company 0 is missing', (SELECT pct_amt FROM r WHERE part='COLUMNS' AND ds='S1_OPP_FIRM' AND col='CBD_ID'), 23.08),
 chk('broker name variants merge', (SELECT n_values FROM r WHERE part='COLUMNS' AND ds='S1_OPP_FIRM' AND col='BROKER_NAME'), 7),
 chk('firms on 2 channels', (SELECT amt FROM r WHERE part='PAIRS' AND ds='S1_OPP_FIRM' AND col='DIST_CH' AND col2='FIRM_CRD' AND item='many : many'), 800),
 chk('CRD on 2 company IDs', (SELECT amt FROM r WHERE part='PAIRS' AND ds='S1_OPP_FIRM' AND col='CBD_ID' AND col2='FIRM_CRD' AND item='many CBD_ID, one FIRM_CRD'), 800),
 chk('rule by company ID beats rule by name', lab('S1_OPP_FIRM', 'DIST_CH', 'PRI'), 40),
 chk('rule by feed label', lab('S1_OPP_FIRM', 'DIST_CH', 'EDJ'), 30),
 chk('feed label kept', lab('S1_OPP_FIRM', 'FEED_DIST_CH', 'EDWARD JONES'), 30),
 chk('channel labels upper-cased', lab('S1_OPP_FIRM', 'DIST_CH', 'FI'), 350),
 chk('IOVA label', lab('S1_OPP_FIRM', 'VA_PRODUCT_TYPE', 'IOVA'), 500),
 chk('s2 channel label', lab('S2_OPP_FIRM', 'DIST_CH', 'IND'), 65),
 chk('opp cell with 2 holders', m('S1_OPP_GEO', 'CH_ZIP', 'S1_TERR.CH_ZIP', '2+'), 500),
 chk('opp cell with 1 holder, renamed label meets territory', m('S1_OPP_GEO', 'CH_ZIP', 'S1_TERR.CH_ZIP', '1'), 330),
 chk('opp cell with no holder', m('S1_OPP_GEO', 'CH_ZIP', 'S1_TERR.CH_ZIP', '0'), 440),
 chk('blank channel has no cell', m('S1_OPP_GEO', 'CH_ZIP', 'S1_TERR.CH_ZIP', 'no value'), 30),
 chk('padded ZIP meets territory ZIP', m('S1_OPP_GEO', 'ZIP', 'S1_TERR.ZIP', '2+'), 700),
 chk('s2 CRD on 2+ source 1 channels (blank counts)', m('S2_OPP_FIRM', 'FIRM_CRD', 'S1_CRD_CH.FIRM_CRD', '2+'), 110),
 chk('s2 CRD on 1 source 1 channel', m('S2_OPP_FIRM', 'FIRM_CRD', 'S1_CRD_CH.FIRM_CRD', '1'), 9),
 chk('s2 CRD not in source 1', m('S2_OPP_FIRM', 'FIRM_CRD', 'S1_CRD_CH.FIRM_CRD', '0'), 25),
 chk('s2 row with no CRD', m('S2_OPP_FIRM', 'FIRM_CRD', 'S1_CRD_CH.FIRM_CRD', 'no value'), 5),
 chk('override on one row of the CRD', m('S2_OPP_FIRM', 'FIRM_CRD', 'S2_OVERRIDE.FIRM_CRD', '1'), 70),
 chk('override repeated', m('S2_OPP_FIRM', 'FIRM_CRD', 'S2_OVERRIDE.FIRM_CRD', '2+'), 40),
 chk('s1 firm also in source 2', m('S1_OPP_FIRM', 'FIRM_CRD', 'S2_OPP_FIRM.FIRM_CRD', '1'), 710),
 chk('s1 firm not in source 2', m('S1_OPP_FIRM', 'FIRM_CRD', 'S2_OPP_FIRM.FIRM_CRD', '0'), 170),
 chk('numeric ZIP padded, meets s2 territory', m('S2_OPP_GEO', 'CH_ZIP', 'S2_TERR.CH_ZIP', '1'), 100),
 chk('s2 cell with no holder', m('S2_OPP_GEO', 'CH_ZIP', 'S2_TERR.CH_ZIP', '0'), 49),
 chk('s1 split within a ZIP', k('S1 CHANNELS PER ZIP X CRD X NAME, PER CRD X NAME', 'ZIP CELL 2+'), 700),
 chk('s1 split across ZIPs (blank counts)', k('S1 CHANNELS PER ZIP X CRD X NAME, PER CRD X NAME', 'ZIP CELL 1, FIRM 2+'), 420),
 chk('s1 unsplit', k('S1 CHANNELS PER ZIP X CRD X NAME, PER CRD X NAME', 'ZIP CELL 1, FIRM 1'), 80),
 chk('route level 1', k('S2 ROUTE LEVEL', '1 SAME ZIP X CRD X NAME: ONE CHANNEL (OVERRIDE)'), 60),
 chk('route level 1, blank cell', k('S2 ROUTE LEVEL', '1 SAME ZIP X CRD X NAME: ONE CHANNEL'), 9),
 chk('route level 2', k('S2 ROUTE LEVEL', '2 SAME ZIP X CRD X NAME: 2+ CHANNELS (OVERRIDE)'), 40),
 chk('route level 4', k('S2 ROUTE LEVEL', '4 SAME CRD X NAME: 2+ CHANNELS (OVERRIDE)'), 7),
 chk('route level 6', k('S2 ROUTE LEVEL', '6 SAME CRD, OTHER NAME: 2+ CHANNELS (OVERRIDE)'), 3),
 chk('route level 7', k('S2 ROUTE LEVEL', '7 NO SOURCE 1 ROWS'), 25),
 chk('route level 0', k('S2 ROUTE LEVEL', '0 NO CRD'), 5),
 chk('label x firm channel', k('S2 DIST_CH -> S1 CHANNEL OF THE CRD', 'WIRE -> 2+ CHANNELS (OVERRIDE)'), 67),
 chk('label x firm channel: blank', k('S2 DIST_CH -> S1 CHANNEL OF THE CRD', 'RA -> (BLANK)'), 9),
 chk('label x firm channel: absent', k('S2 DIST_CH -> S1 CHANNEL OF THE CRD', 'IND -> NO SOURCE 1 ROWS'), 25),
 chk('s1 firm route: one channel', k('S1 ROUTE (CRD X NAME)', 'ONE CHANNEL'), 370),
 chk('s1 firm route: row blank, firm has a channel', k('S1 ROUTE (CRD X NAME)', 'ONE CHANNEL, ROW BLANK'), 20),
 chk('s1 firm route: 2+', k('S1 ROUTE (CRD X NAME)', '2+'), 800),
 chk('s1 firm route: unmapped', k('S1 ROUTE (CRD X NAME)', 'UNMAPPED'), 10),
 chk('s2 firm route WH, name then CRD', k('S2 ROUTE (CRD X NAME)', 'WH'), 70),
 chk('s2 firm route unmapped', k('S2 ROUTE (CRD X NAME)', 'UNMAPPED'), 9),
 chk('s2 firm route 2+', k('S2 ROUTE (CRD X NAME)', '2+'), 40),
 chk('override fills a split firm', k('S2 ROUTE (CRD X NAME) VS OVERRIDE', 'OVERRIDE FILLS 2+: IFA'), 40),
 chk('override disagrees', k('S2 ROUTE (CRD X NAME) VS OVERRIDE', 'OVERRIDE FI <> ROUTE WH'), 67),
 chk('no override, route found', k('S2 ROUTE (CRD X NAME) VS OVERRIDE', 'NO OVERRIDE | ROUTE ONE CHANNEL'), 3),
 chk('no override, unmapped', k('S2 ROUTE (CRD X NAME) VS OVERRIDE', 'NO OVERRIDE | ROUTE UNMAPPED'), 9),
 chk('no override, no CRD', k('S2 ROUTE (CRD X NAME) VS OVERRIDE', 'NO OVERRIDE | ROUTE NO CRD'), 5),
 chk('override key repeated', kn('OVERRIDE TABLE KEYS', 'CRD ONLY, REPEATED'), 1),
 chk('override key by name', kn('OVERRIDE TABLE KEYS', 'CRD X NAME'), 1),
 chk('override key not in s2', kn('OVERRIDE TABLE KEYS', 'CRD ONLY, NOT IN S2'), 1),
 chk('region range within a ZIP', kn('START_ZIP_VS_END_ZIP', 'range within one ZIP'), 1),
 chk('region range across ZIPs', kn('START_ZIP_VS_END_ZIP', 'range across ZIPs'), 1),
 chk('territory table vs regions', (SELECT string_agg(item || '=' || n_rows, ' ' ORDER BY item) FROM r WHERE part='CHECKS' AND col='WHSLR_ZIP_VS_REGIONS'), 'both=2 table only=2'),
 chk('ZIP lost its zero', (SELECT amt FROM r WHERE part='CHECKS' AND ds='S1_OPP' AND col='ZIP_FORM' AND item='under 5 digits'), 500),
 chk('s2 ZIP stored as a number', (SELECT amt FROM r WHERE part='CHECKS' AND ds='S2_OPP' AND col='ZIP_FORM' AND item='under 5 digits'), 40),
 chk('periods', k('FISCAL_YR | QUARTER', '2025 | Q2'), 300),
 chk('no renamed duplicate column', (SELECT COUNT(*) FROM duckdb_columns() WHERE table_name LIKE 'tmp_prof%' AND regexp_matches(column_name, '_[0-9]+$')), 0);
SELECT 'profile_test: ok';
SQL
} | duckdb -bail -noheader -list
