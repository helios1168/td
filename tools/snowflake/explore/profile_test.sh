#!/bin/sh
# Runs profile.sql in DuckDB on made-up tables with the real column names, one planted case per outcome, and checks
# the answers.  Prints "profile_test: ok" or stops at the first failed check.  Run from anywhere: sh profile_test.sh
set -e
here=$(cd "$(dirname "$0")" && pwd)
{
cat <<'SQL'
ATTACH ':memory:' AS life_prod; CREATE SCHEMA life_prod.lif_murkylake;
ATTACH ':memory:' AS ssdb_integration; CREATE SCHEMA ssdb_integration.lr_strategy;
CREATE MACRO to_date(x) AS CAST(x AS DATE);
CREATE TABLE life_prod.lif_murkylake.sls_rpt_detail (policy_no TEXT, agent_tax_id TEXT, product_line TEXT,
  actual_sales_amount DECIMAL(18,2), consol_brkr_dlr_id DECIMAL(38,0), consol_broker_nm TEXT, mga_agent_cd TEXT,
  whslr_id TEXT, duplicate_entry_in TEXT, src_delete_ind TEXT, reversal_cd TEXT, credit_type TEXT, trans_type TEXT,
  fiscal_yr INTEGER, sales_date TIMESTAMP, bonus_rate DECIMAL(9,4), init_pay_in TEXT, life70_co_cd TEXT);
INSERT INTO life_prod.lif_murkylake.sls_rpt_detail VALUES
  ('P1','A1','INDEX',100,10,'FIRM A','MGA1','W1','N',NULL,NULL,'C','T',2025,'2025-03-01',1,'Y','AA'),
  ('P1','A1','FIXED',50,10,'FIRM A','MGA1','W1','N',NULL,NULL,'C','T',2025,'2025-03-01',1,'Y','AA'),
  ('P2','A2','RILA',200,20,'FIRM B','MGA2','W2','N',NULL,NULL,'C','T',2025,'2025-04-01',1,'Y','AA'),
  ('P3','A3','RILA',70,342,'FIRM X','MGA2','W2','N',NULL,NULL,'C','T',2025,'2025-04-01',1,'Y','AA'),
  ('P4','A2','VARIABLE',30,20,' firm b ','MGA3','W9','Y',NULL,NULL,'C','T',2025,'2025-05-01',1,'Y','AA'),
  ('P5','A2','RILA',999,20,'FIRM B','MGA2','W2','N',NULL,NULL,'C','T',2024,'2024-05-01',1,'Y','AA');
CREATE TABLE ssdb_integration.lr_strategy.mga_map (mga_agent_cd TEXT, channel TEXT, channel_calc TEXT,
  channel_override TEXT, dollars_total DECIMAL(18,2));
INSERT INTO ssdb_integration.lr_strategy.mga_map VALUES
  ('MGA1','BANK','BANK',NULL,5), ('MGA1','BANK','WIREHOUSE',NULL,6), ('MGA2','INDEPENDENT','INDEPENDENT','IMO',7);
CREATE TABLE life_prod.lif_murkylake.wc_edw_consol_brkr_dealer_mga_master (consol_brkr_dealer_id DECIMAL(38,0),
  master_consol_brkr_dealer_id TEXT, consol_brkr_dealer_name TEXT, master_consol_brkr_dealer_name TEXT,
  expiration_dte TIMESTAMP);
INSERT INTO life_prod.lif_murkylake.wc_edw_consol_brkr_dealer_mga_master VALUES
  (10,'M1','FIRM A','PARENT 1','9999-12-31'), (10,'M2','FIRM A','PARENT 2','9999-12-31'),
  (20,'M3','FIRM B','PARENT 3','9999-12-31'), (20,'M3','FIRM B','PARENT 3','9999-12-31'),
  (20,'M4','FIRM B','PARENT 4','2020-01-01');
CREATE TABLE life_prod.lif_murkylake.whslr (whslr_id TEXT, sales_district_id TEXT, distch TEXT, status_cd TEXT);
INSERT INTO life_prod.lif_murkylake.whslr VALUES ('W1','D1','IND','A'), ('W2','D2','BANK','A');
CREATE TABLE ssdb_integration.lr_strategy.mm_map (dist_ch TEXT, cbd_id DECIMAL(38,0), channel DECIMAL(38,0),
  firm_client_id DECIMAL(38,0), broker_name TEXT, firm_crd DECIMAL(38,0));
INSERT INTO ssdb_integration.lr_strategy.mm_map VALUES
  ('IFA',10,1,501,'BD ONE',1000), ('FI',20,2,502,'BD TWO',2000), ('FI',20,2,503,'BD TWO B',2001);
CREATE TABLE ssdb_integration.lr_strategy.crd_to_cbd (firm TEXT, firm_crd DOUBLE, cbd_id DOUBLE, cbd_nm_best TEXT);
INSERT INTO ssdb_integration.lr_strategy.crd_to_cbd VALUES ('BD ONE',1000.0,10.0,'FIRM A');
CREATE TABLE life_prod.lif_murkylake.wc_market_metrics_opportunity (fiscal_yr TEXT, cbd_id TEXT, client_firm_id TEXT,
  firm_crd TEXT, broker_name TEXT, dist_ch TEXT, channel TEXT, product_line TEXT, va_product_type TEXT,
  zip_code TEXT, state TEXT, territory TEXT, global_sales DECIMAL(18,2));
INSERT INTO life_prod.lif_murkylake.wc_market_metrics_opportunity VALUES
  ('2025','10',NULL,'1000','BD ONE','IFA','X','VA','IOVA','2134','MA','W1',500),
  ('2025','0',NULL,'3000','BD THREE','WH','X','IA',NULL,'10001','NY','W2',300),
  ('2024','10',NULL,'1000','BD ONE','IFA','X','VA','IOVA','2134','MA','W1',9999);
CREATE TABLE ssdb_integration.lr_strategy.s1_terr_t (whslr_id TEXT, whslr_nm TEXT, zip TEXT, state_cd TEXT,
  new_dist_channel TEXT);
INSERT INTO ssdb_integration.lr_strategy.s1_terr_t VALUES ('W1','N1','02134','MA','IFA'), ('W3','N3','2134','MA','IFA');
CREATE TABLE life_prod.lif_murkylake.geographic_region (rgn_cd TEXT, start_zip TEXT, end_zip TEXT, cbd INTEGER,
  expir_dt TIMESTAMP);
INSERT INTO life_prod.lif_murkylake.geographic_region VALUES
  ('R1','02134','02134',0,'9999-12-31'), ('R2','10001','10099',0,'9999-12-31'), ('R3','99999','99999',0,'2020-01-01');
CREATE TABLE life_prod.lif_murkylake.rgn_whslr (whslr_id TEXT, rgn_cd TEXT, expir_dt TIMESTAMP);
INSERT INTO life_prod.lif_murkylake.rgn_whslr VALUES ('W1','R1','9999-12-31'), ('W2','R2','9999-12-31');
CREATE TABLE life_prod.lif_murkylake.wc_sbl_contact (contact_ssn TEXT);
INSERT INTO life_prod.lif_murkylake.wc_sbl_contact VALUES ('A1'), ('A2'), ('A2');
CREATE TABLE life_prod.lif_murkylake.wc_sbl_addr (zip_cd TEXT);
INSERT INTO life_prod.lif_murkylake.wc_sbl_addr VALUES ('02134-1234'), ('02134');
CREATE TABLE ssdb_integration.lr_strategy.s2_opp_t (channel DOUBLE, dist_ch TEXT, zip_code DECIMAL(38,0),
  firm_crd DECIMAL(38,0), broker_name TEXT, product_line TEXT, va_product_type TEXT, opp DOUBLE);
INSERT INTO ssdb_integration.lr_strategy.s2_opp_t VALUES (1.0,'IFA',2134,1000,'BD ONE','VA','X',40);
CREATE TABLE ssdb_integration.lr_strategy.s2_sales_t (parent_firm TEXT, firm TEXT, firm_crd DOUBLE, channel TEXT,
  shareclass TEXT, product TEXT, year INTEGER, sales_amount DOUBLE, mm_amount DOUBLE, zip_code TEXT);
INSERT INTO ssdb_integration.lr_strategy.s2_sales_t VALUES
  ('PF','F1',1000.0,'IFA','A','VA',2025,10,5,'02134'), ('PF','F1',1000.0,'IFA','A','VA',2024,20,6,'02134');
CREATE TABLE ssdb_integration.lr_strategy.s2_crd_t (firm_crd DECIMAL(38,0), firm TEXT);
INSERT INTO ssdb_integration.lr_strategy.s2_crd_t VALUES (1000,'BD ONE'), (1000,'BD ONE - BANK');
CREATE TABLE ssdb_integration.lr_strategy.s2_terr_t (rvp TEXT, territory_id TEXT, zipcode TEXT, state TEXT,
  channel TEXT, channel_name TEXT);
INSERT INTO ssdb_integration.lr_strategy.s2_terr_t VALUES ('RVP1','T1','02134','MA','IFA','Independent');
SQL
sed -e '/^use secondary roles all;$/d' -e 's/TEMPORARY TABLE/TABLE/' \
    -e 's/<S1_TERRITORIES>/s1_terr_t/g' -e 's/<S2_OPP>/s2_opp_t/g' -e 's/<S2_SALES>/s2_sales_t/g' \
    -e 's/<S2_CRD_MAP>/s2_crd_t/g' -e 's/<S2_TERRITORIES>/s2_terr_t/g' -e 's/<S1_PRODUCT_4>/P4/g' \
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
SELECT
 chk('sales rows in scope', (SELECT n_rows FROM r WHERE part='COLUMNS' AND ds='S1_SALES' AND col='CBD_ID'), 4),
 chk('sales $ in scope', (SELECT amt FROM r WHERE part='COLUMNS' AND ds='S1_SALES' AND col='CBD_ID'), 380),
 chk('MGA code on 2 map rows', (SELECT amt FROM r WHERE part='MATCHES' AND ds='S1_SALES' AND col='MGA_AGENT_CD' AND item='2+'), 150),
 chk('MGA code not in map', (SELECT amt FROM r WHERE part='MATCHES' AND ds='S1_SALES' AND col='MGA_AGENT_CD' AND item='0'), 30),
 chk('company with 2 masters', (SELECT amt FROM r WHERE part='MATCHES' AND ds='S1_SALES' AND col='CBD_ID' AND col2='S1_MASTER.CBD_ID' AND item='2+'), 150),
 chk('exact repeat in master kept once', (SELECT amt FROM r WHERE part='MATCHES' AND ds='S1_SALES' AND col='CBD_ID' AND col2='S1_MASTER.CBD_ID' AND item='1'), 230),
 chk('company on 2 mm_map rows', (SELECT amt FROM r WHERE part='MATCHES' AND ds='S1_SALES' AND col='CBD_ID' AND col2='MM_MAP.CBD_ID' AND item='2+'), 230),
 chk('float CRD_TO_CBD ids match', (SELECT amt FROM r WHERE part='MATCHES' AND ds='S1_SALES' AND col='CBD_ID' AND col2='CRD_TO_CBD.CBD_ID' AND item='1'), 150),
 chk('wholesaler missing', (SELECT amt FROM r WHERE part='MATCHES' AND ds='S1_SALES' AND col='WHSLR_ID' AND item='0'), 30),
 chk('name variants merge', (SELECT n_values FROM r WHERE part='COLUMNS' AND ds='S1_SALES' AND col='CBD_NAME'), 2),
 chk('company 0 is missing', (SELECT pct_amt FROM r WHERE part='COLUMNS' AND ds='S1_OPP_FIRM' AND col='CBD_ID'), 37.5),
 chk('opp CRD not in mm_map', (SELECT amt FROM r WHERE part='MATCHES' AND ds='S1_OPP_FIRM' AND col='FIRM_CRD' AND item='0'), 300),
 chk('opp cell with 2 holders', (SELECT amt FROM r WHERE part='MATCHES' AND ds='S1_OPP_GEO' AND col='CH_ZIP' AND item='2+'), 500),
 chk('opp cell with no holder', (SELECT amt FROM r WHERE part='MATCHES' AND ds='S1_OPP_GEO' AND col='CH_ZIP' AND item='0'), 300),
 chk('holders per cell shape', (SELECT n_values FROM r WHERE part='PAIRS' AND ds='S1_TERR' AND col='CH_ZIP' AND col2='WHSLR_ID' AND item='one CH_ZIP, many WHSLR_ID'), 2),
 chk('mm_map company splits to 2 CRDs', (SELECT n_values FROM r WHERE part='PAIRS' AND ds='MM_MAP' AND col='CBD_ID' AND col2='FIRM_CRD' AND item='one CBD_ID, many FIRM_CRD'), 2),
 chk('IOVA label', (SELECT amt FROM r WHERE part='LABELS' AND ds='S1_OPP_FIRM' AND col='VA_PRODUCT_TYPE' AND item='IOVA'), 500),
 chk('numeric ZIP padded, matches territory', (SELECT amt FROM r WHERE part='MATCHES' AND ds='S2_OPP_GEO' AND col='CH_ZIP' AND item='1'), 40),
 chk('float CRD in sales meets numeric CRD', (SELECT amt FROM r WHERE part='MATCHES' AND ds='S2_SALES' AND col='FIRM_CRD' AND col2='S2_OPP_FIRM.FIRM_CRD' AND item='1'), 10),
 chk('CRD map cannot choose', (SELECT amt FROM r WHERE part='MATCHES' AND ds='S2_SALES' AND col='FIRM_CRD' AND col2='S2_CRD_MAP.FIRM_CRD' AND item='2+'), 10),
 chk('shared CRD across sources', (SELECT amt FROM r WHERE part='MATCHES' AND ds='S2_OPP_FIRM' AND col='FIRM_CRD' AND col2='S1_OPP_FIRM.FIRM_CRD' AND item='1'), 40),
 chk('policy on 2 product lines', (SELECT amt FROM r WHERE part='CHECKS' AND col='POLICY_PRODUCT_LINES' AND item='2+'), 150),
 chk('agent on 2 contacts', (SELECT amt FROM r WHERE part='CHECKS' AND col='AGENT_CONTACT_ROWS' AND item='2+'), 230),
 chk('region ZIP range', (SELECT n_rows FROM r WHERE part='CHECKS' AND col='START_ZIP_VS_END_ZIP' AND item='range'), 1),
 chk('territory table vs regions', (SELECT string_agg(item || '=' || n_rows, ' ' ORDER BY item) FROM r WHERE part='CHECKS' AND col='WHSLR_ZIP_VS_REGIONS'), 'both=1 regions only=1 table only=1'),
 chk('ZIP lost its zero', (SELECT amt FROM r WHERE part='CHECKS' AND ds='S1_OPP' AND col='ZIP_FORM' AND item='under 5 digits'), 500),
 chk('ZIP+4', (SELECT n_rows FROM r WHERE part='CHECKS' AND ds='S1_ADDR' AND col='ZIP_FORM' AND item='non-digit'), 1),
 chk('source 2 opp ZIP stored as a number', (SELECT n_rows FROM r WHERE part='CHECKS' AND ds='S2_OPP' AND col='ZIP_FORM' AND item='under 5 digits'), 1),
 chk('s2 sales 2024 kept apart', (SELECT amt FROM r WHERE part='CHECKS' AND col='YEAR: MM_AMOUNT' AND item='2024'), 6),
 chk('no renamed duplicate column', (SELECT COUNT(*) FROM duckdb_columns() WHERE table_name LIKE 'tmp_prof%' AND regexp_matches(column_name, '_[0-9]+$')), 0);
SELECT 'profile_test: ok';
SQL
} | duckdb -bail -noheader -list
