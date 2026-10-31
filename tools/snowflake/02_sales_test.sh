#!/bin/sh
# Runs 01_opportunity.sql, then 02_sales.sql, in DuckDB on made-up tables with the real column names, and checks
# 02's tables and its result set, the file's own last statement (answers worked out by hand from the rows below).
# Prints "02_sales_test: ok" or stops at the first failed check.  DuckDB has no TO_DATE: a macro casts to DATE.
# Run from anywhere: sh 02_sales_test.sh
set -e
here=$(cd "$(dirname "$0")" && pwd)
{
cat <<'SQL'
ATTACH ':memory:' AS life_prod; CREATE SCHEMA life_prod.lif_murkylake;
ATTACH ':memory:' AS ssdb_integration; CREATE SCHEMA ssdb_integration.lr_strategy;
CREATE MACRO to_date(x) AS CAST(x AS DATE);
CREATE TABLE life_prod.lif_murkylake.wc_market_metrics_opportunity (fiscal_yr TEXT, quarter TEXT, cbd_id TEXT,
  client_firm_id TEXT, firm_crd TEXT, broker_name TEXT, dist_ch TEXT, channel TEXT, product_line TEXT,
  va_product_type TEXT, zip_code TEXT, global_sales DECIMAL(18,2));
INSERT INTO life_prod.lif_murkylake.wc_market_metrics_opportunity VALUES
  ('2025','Q1','10',NULL,'100','Alpha','IFA','01','IA','-77777','02134',100),
  ('2025','Q1','0',NULL,'200','LPL Financial LLC - INDEPENDENT','IFA','01','IA','-77777','10001',300),
  ('2025','Q1','0',NULL,'200','LPL Financial LLC - BANK','FI','11','IA','-77777','10001',200),
  ('2025','Q1','0',NULL,'200','LPL Financial LLC','IFA','01','IA','-77777','02134',30),
  ('2025','Q2','0','30|31','300','Charlie','IFA','01','FA','-77777','02134',50),
  ('2025','Q2','30',NULL,'400','Delta','WH','11','IA','-77777','10001',40),
  ('2025','Q2','3',NULL,'500','Echo','EDWARD JONES','13','IA','-77777','60601',70),
  ('2025','Q3','60',NULL,'600','Foxtrot','IFA','01','IA','-77777','02134',20),
  ('2025','Q3','60',NULL,'601','Foxtrot 2','FI','11','IA','-77777','10001',10);
CREATE TABLE ssdb_integration.lr_strategy.s1_terr_t (whslr_id TEXT, whslr_nm TEXT, zip TEXT, state_cd TEXT,
  new_dist_channel TEXT);
INSERT INTO ssdb_integration.lr_strategy.s1_terr_t VALUES
  ('W1','N1','02134','MA','IFA'), ('W2','N2','10001','NY','IFA'), ('W5','N5','10001','NY','FI'),
  ('W3','N3','10001','NY','WH'), ('W6','N6','30301','GA','IFA'), ('W4','N4','60601','IL','EDJ'),
  ('W9','N9','02134','MA','IMO');
CREATE TABLE ssdb_integration.lr_strategy.s2_opp_t (channel DOUBLE, dist_ch TEXT, zip_code DECIMAL(38,0),
  firm_crd DECIMAL(38,0), broker_name TEXT, product_line TEXT, va_product_type TEXT, opp DOUBLE);
INSERT INTO ssdb_integration.lr_strategy.s2_opp_t VALUES
  (NULL,'INDEPENDENT',2134,100,'ALPHA','IA',NULL,40),
  (NULL,'BANK',10001,200,'LPL FINANCIAL LLC - BANK','IA',NULL,60),
  (NULL,'REGIONAL',10001,200,'LPL FINANCIAL LLC - INDEPENDENT','IA',NULL,30);
CREATE TABLE ssdb_integration.lr_strategy.s2_terr_t (rvp TEXT, territory_id TEXT, zipcode TEXT, state TEXT,
  channel TEXT, channel_name TEXT);
INSERT INTO ssdb_integration.lr_strategy.s2_terr_t VALUES
  ('R1','T1','02134','MA','FP','x'), ('R3','T3','10001','NY','BK','x'), ('R2','T2','10001','NY','BD','x'),
  ('R1','T7','10001','NY','FP','x');
CREATE TABLE ssdb_integration.lr_strategy.crd_dist_override (firm_crd VARCHAR, broker_name VARCHAR, dist_ch VARCHAR);
INSERT INTO ssdb_integration.lr_strategy.crd_dist_override VALUES ('999', NULL, 'WH');
CREATE TABLE ssdb_integration.lr_strategy.s1_sales_t (fiscal_yr INTEGER, actual_agent_dollars DECIMAL(18,2),
  compd_agent_dollars DECIMAL(18,2), product_line2 TEXT, dist_ch TEXT, consol_broker_nm TEXT,
  consol_brkr_dlr_id DECIMAL(38,0), parent TEXT, firmcrd TEXT, zip_cd TEXT, state_cd TEXT, whslr_id TEXT, whslr_nm TEXT,
  product_bucket TEXT, true_ticket_count DOUBLE, true_ticket_count_act DOUBLE, distinct_agents INTEGER);
INSERT INTO ssdb_integration.lr_strategy.s1_sales_t VALUES
  (2025,10,11,'INDEX','IFA','ALPHA BD',10,'P','','02134','MA','W1','N1','ALL',1,1,1),
  (2025,5,6,'INDEX','IFA','ALPHA BD',10,'P','','02134','MA','W6','N6','ALL',1,1,1),
  (2025,7,7,'INDEX','FI','LPL',8,'P','','10001','NY','W5','N5','ALL',1,1,1),
  (2025,9,9,'INDEX','IFA','LPL',8,'P','','10001','NY','W2','N2','ALL',1,1,1),
  (2025,4,4,'INDEX','IMO','LPL',8,'P','','02134','MA','W9','N9','ALL',1,1,1),
  (2025,3,3,'FIXED','WH','DELTA',30,'P','','10001','NY','W3','N3','ALL',1,1,1),
  (2025,2,2,'FIXED','IFA','CHARLIE',31,'P','','2134','MA','W1','N1','ALL',1,1,1),
  (2025,6,6,'INDEX','CAPTIVE','ECHO',3,'P','','60601','IL','W4','N4','ALL',1,1,1),
  (2025,1,1,'INDEX','IFA','FOX',60,'P','','02134','MA','W1','N1','ALL',1,1,1),
  (2025,8,8,'INDEX','IFA','NEW BD',77,'P','','BLANK','BLANK','W1','N1','ALL',1,1,1),
  (2025,5,5,'INDEX','IFA','AFS',438,'P','','02134','MA','W1','N1','ALL',1,1,1),
  (2025,1,1,'INDEX','IFA','NONE',NULL,'P','','02134','MA','W1','N1','ALL',1,1,1),
  (2024,100,100,'INDEX','IFA','ALPHA BD',10,'P','','02134','MA','W1','N1','ALL',1,1,1),
  (2025,50,50,'INDEX','IFA','ALPHA BD',10,'P','','02134','MA','W1','N1','RIVA',1,1,1),
  (2025,2,2,'INDEX','ifa ','ALPHA BD',10,'P','','02134','MA','W1','N1','ALL',1,1,1);
CREATE TABLE life_prod.lif_murkylake.sls_rpt_detail (policy_no TEXT, fiscal_yr INTEGER, sales_date TIMESTAMP,
  bonus_rate DECIMAL(9,4), init_pay_in TEXT, consol_brkr_dlr_id DECIMAL(38,0), life70_co_cd TEXT, agent_tax_id TEXT,
  product_line TEXT, actual_sales_amount DECIMAL(18,2), sales_amount DECIMAL(18,2));
INSERT INTO life_prod.lif_murkylake.sls_rpt_detail VALUES
  ('PA',2025,'2025-03-01',1,'Y',10,'AA','T1','INDEX',40,41), ('PB',2025,'2025-06-01',1,'Y',8,'AA','T2','FIXED',21,22),
  ('PC',2025,'2025-06-01',0,'Y',8,'AA','T3','INDEX',500,500), ('PD',2025,'2025-06-01',1,'Y',342,'AA','T4','INDEX',500,500),
  ('PE',2025,'2025-06-01',1,'Y',8,'AA','T5','INDEX',30,20), ('PE',2025,'2025-07-01',1,'Y',8,'AA','T5','INDEX',-10,-20),
  ('PF',2025,'2025-06-01',1,'Y',8,'VV','T6','INDEX',500,500), ('PG',2025,'2025-06-01',1,'Y',8,'AA',NULL,'INDEX',500,500),
  ('PH',2025,'2025-06-01',1,'Y',8,'AA','T7','TERM',500,500), ('PI',2025,'2026-01-15',1,'Y',8,'AA','T8','INDEX',500,500),
  ('PJ',2024,'2024-05-01',1,'Y',8,'AA','T9','INDEX',100,100), ('PK',2025,'2025-06-01',1,'N',8,'AA','T10','INDEX',500,500),
  ('PL',2025,'2025-08-01',1,'Y',10,'AA','T11','INDEX',2,2);
CREATE TABLE ssdb_integration.lr_strategy.s2_sales_t (parent_firm TEXT, firm TEXT, firm_crd DOUBLE, channel TEXT,
  state TEXT, shareclass TEXT, regionids TEXT, rvp TEXT, dvp TEXT, year INTEGER, sales_amount DOUBLE, mm_amount DOUBLE,
  zip_code TEXT, product TEXT);
INSERT INTO ssdb_integration.lr_strategy.s2_sales_t VALUES
  ('P','Alpha Inc',100.0,'INDEPENDENT','MA','A','x','R1','D1',2025,4,5,'02134','IA'),
  ('P','LPL Corp',200.0,'BANK','NY','A','x','R3','D1',2025,6,6,'10001','IA'),
  ('P','LPL Corp',200.0,'INDEPENDENT','NY','A','x','R2','D1',2025,3,3,'10001','IA'),
  ('P','No Crd',NULL,'BANK','NY','A','x','R3','D1',2025,2,2,'10001','IA'),
  ('P','New',888.0,'BANK','NY','A','x','R3','D1',2025,1,1,'10001','IA'),
  ('P','Alpha Inc',100.0,'INDEPENDENT','MA','A','x','R1','D1',2025,2,2,'02134','ANNUITY X'),
  ('P','Alpha Inc',100.0,'BD','MA','A','x','r1 ','D1',2025,1,1,'2134','VA'),
  ('P','Echo',500.0,'REGIONAL','IL','A','x','R2','D1',2025,3,3,'60601','IA'),
  ('P','Alpha Inc',100.0,'INDEPENDENT','MA','A','x','R1','D1',2024,9,9,'02134','IA'),
  ('P','LPL Corp',200.0,'Bank','NY','A','x','R3','D1',2025,1,1,'10001','IA'),
  ('P','Kilo',438.0,'INDEPENDENT','MA','A','x','R1','D1',2025,1,1,'02134','IA');
CREATE TABLE ssdb_integration.lr_strategy.mm_map (dist_ch TEXT, cbd_id INTEGER, channel INTEGER, firm_client_id INTEGER,
  broker_name TEXT, firm_crd INTEGER);
INSERT INTO ssdb_integration.lr_strategy.mm_map VALUES
  ('IFA',10,1,NULL,'Alpha',100), ('FI',0,11,8,'LPL Financial LLC - BANK',200), ('WH',30,11,NULL,'Delta',999),
  ('IFA',60,1,NULL,'Foxtrot',600), ('FI',60,11,NULL,'Foxtrot 2',601);
CREATE TABLE ssdb_integration.lr_strategy.crd_to_cbd (firm TEXT, firm_crd DOUBLE, cbd_id DOUBLE, cbd_nm_best TEXT);
INSERT INTO ssdb_integration.lr_strategy.crd_to_cbd VALUES
  ('Alpha',100.0,10.0,'ALPHA'), ('LPL',200.0,8.0,'LPL'), ('Delta',400.0,30.0,'DELTA');
SQL
sed -e '/^use secondary roles all;$/d' -e '/^SET s[12]_/d' -e 's/TEMPORARY TABLE/TABLE/' \
    -e 's/IDENTIFIER(\$s1_territories)/ssdb_integration.lr_strategy.s1_terr_t/g' \
    -e 's/IDENTIFIER(\$s2_opp)/ssdb_integration.lr_strategy.s2_opp_t/g' \
    -e 's/IDENTIFIER(\$s2_territories)/ssdb_integration.lr_strategy.s2_terr_t/g' \
    -e '/^--8\./,$d' "$here/01_opportunity.sql"
sed -e '/^use secondary roles all;$/d' -e '/^SET s[12]_/d' -e 's/TEMPORARY TABLE/TABLE/' \
    -e 's/IDENTIFIER(\$s1_sales)/ssdb_integration.lr_strategy.s1_sales_t/g' \
    -e 's/IDENTIFIER(\$s2_sales)/ssdb_integration.lr_strategy.s2_sales_t/g' \
    -e 's/^SELECT part, source, name, item, n_rows, n_wholesalers, n_firms, amt,$/CREATE TABLE r AS SELECT part, source, name, item, n_rows, n_wholesalers, n_firms, amt,/' \
    "$here/02_sales.sql"
cat <<'SQL'
CREATE MACRO chk(name, got, want) AS CASE WHEN got IS NOT DISTINCT FROM want THEN 'ok'
  ELSE error(name || ': got ' || COALESCE(CAST(got AS VARCHAR), 'NULL') || ', want ' || CAST(want AS VARCHAR)) END;
CREATE MACRO a(p, s, n, i) AS (SELECT CAST(SUM(amt) AS DOUBLE) FROM r WHERE part = p AND source IS NOT DISTINCT FROM s
                                AND name IS NOT DISTINCT FROM n AND item IS NOT DISTINCT FROM i);
CREATE MACRO w(p, s, n, i) AS (SELECT n_wholesalers FROM r WHERE part = p AND source = s AND name = n AND item = i);
CREATE MACRO d(s, k, z, nm, pr) AS (SELECT CAST(SUM(opp_held_old) AS INTEGER) || ' ' || CAST(SUM(opp_held_new) AS INTEGER)
  || ' ' || CAST(SUM(sales) AS INTEGER) || ' ' || CAST(SUM(sales_in_held_cells_old) AS INTEGER) || ' '
  || CAST(SUM(sales_in_held_cells_new) AS INTEGER)
  FROM ssdb_integration.lr_strategy.tmp_o2_dataset WHERE source = s AND wholesaler_key IS NOT DISTINCT FROM k
  AND zip IS NOT DISTINCT FROM z AND broker_name IS NOT DISTINCT FROM nm AND product IS NOT DISTINCT FROM pr);
CREATE MACRO b(s, sk, ch) AS (SELECT firm_basis || ' ' || COALESCE(broker_name, '-') FROM ssdb_integration.lr_strategy.tmp_o2_sales
  WHERE source = s AND seller_key = sk AND old_channel = ch);
CREATE MACRO t(n, i) AS (SELECT CAST(SUM(amt) AS INTEGER) FROM r WHERE part = 'TIE-OUT' AND name LIKE n AND item = i);
SELECT
 chk('s1 basis: one firm', a('SALES FIRM BASIS', 'S1', NULL, 'ONE FIRM'), 28),
 chk('s1 basis: split matched by channel', a('SALES FIRM BASIS', 'S1', NULL, 'SPLIT, MATCHED BY CHANNEL'), 8),
 chk('s1 basis: 2+ matches, IMO sold as IFA', a('SALES FIRM BASIS', 'S1', NULL, 'SPLIT, 2+ CHANNEL MATCHES'), 13),
 chk('s1 basis: no market metrics firm', a('SALES FIRM BASIS', 'S1', NULL, 'NO MARKET METRICS FIRM'), 13),
 chk('s1 basis: no company', a('SALES FIRM BASIS', 'S1', NULL, 'NO COMPANY'), 1),
 chk('s1: LPL bank sale matched by channel', b('S1', 'W5', 'FI'), 'SPLIT, MATCHED BY CHANNEL LPL FINANCIAL LLC - BANK'),
 chk('s1: direct company beats a list', (SELECT broker_name FROM ssdb_integration.lr_strategy.tmp_o2_sales WHERE source = 'S1' AND sales_firm_id = '30'), 'DELTA'),
 chk('s1: company only in a list', (SELECT broker_name FROM ssdb_integration.lr_strategy.tmp_o2_sales WHERE source = 'S1' AND sales_firm_id = '31'), 'CHARLIE'),
 chk('s1 cells', (SELECT string_agg(item || '=' || CAST(amt AS INTEGER), ' ' ORDER BY item) FROM r WHERE part = 'SALES ON CELLS' AND source = 'S1' AND name = 'CELL'), 'NO FIRM=27 NO OPPORTUNITY CELL=3 ON A CELL WITH OPPORTUNITY=33'),
 chk('s1 sold by the holder, old', a('SALES ON CELLS', 'S1', 'SOLD BY THE CELL''S HOLDER, OLD', 'YES'), 28),
 chk('s1 sold by the holder, new', a('SALES ON CELLS', 'S1', 'SOLD BY THE CELL''S HOLDER, NEW', 'YES'), 28),
 chk('s2 basis', (SELECT string_agg(item || '=' || CAST(amt AS INTEGER), ' ' ORDER BY item) FROM r WHERE part = 'SALES FIRM BASIS' AND source = 'S2'), 'NO CRD=2 NO MARKET METRICS FIRM=2 ONE FIRM=10 SPLIT, 2+ CHANNEL MATCHES=3 SPLIT, MATCHED BY CHANNEL=7'),
 chk('s2 cells', (SELECT string_agg(item || '=' || CAST(amt AS INTEGER), ' ' ORDER BY item) FROM r WHERE part = 'SALES ON CELLS' AND source = 'S2' AND name = 'CELL'), 'NO FIRM=7 NO OPPORTUNITY CELL=4 NO PRODUCT=2 ON A CELL WITH OPPORTUNITY=11'),
 chk('s2 sold by the holder (RVP), old', a('SALES ON CELLS', 'S2', 'SOLD BY THE CELL''S HOLDER, OLD', 'YES'), 11),
 chk('s2 products', (SELECT string_agg(item || '=' || CAST(amt AS INTEGER), ' ' ORDER BY item) FROM r WHERE part = 'SALES PRODUCT' AND source = 'S2'), 'ANNUITY X -> UNMAPPED=2 IA -> INDEX=21 VA -> VARIABLE=1'),
 chk('s2 channels: label via Q19, code as is', (SELECT string_agg(item || '=' || CAST(amt AS INTEGER), ' ' ORDER BY item) FROM r WHERE part = 'SALES CHANNEL' AND source = 'S2'), 'BANK -> FI=9 BD -> WH=1 Bank -> FI=1 INDEPENDENT -> IFA=10 REGIONAL -> WH=3'),
 chk('s1 channels', (SELECT string_agg(item || '=' || CAST(amt AS INTEGER), ' ' ORDER BY item) FROM r WHERE part = 'SALES CHANNEL' AND source = 'S1'), 'CAPTIVE -> CAPTIVE=6 FI -> FI=7 IFA -> IFA=41 IMO -> IFA=4 WH -> WH=3 ifa  -> IFA=2'),
 chk('q35 mm_map', (SELECT string_agg(item || '=' || CAST(amt AS INTEGER), ' ' ORDER BY item) FROM r WHERE part = 'Q35' AND name = 'MM_MAP'), 'MAP: 2+ CRDS=1 MAP: ONE CRD, ANOTHER=3 MAP: ONE CRD, NONE FOUND HERE=13 MAP: ONE CRD, THE SAME=24 NOT IN THE MAP=22'),
 chk('q35 crd_to_cbd', (SELECT string_agg(item || '=' || CAST(amt AS INTEGER), ' ' ORDER BY item) FROM r WHERE part = 'Q35' AND name = 'CRD_TO_CBD'), 'MAP: ONE CRD, NONE FOUND HERE=13 MAP: ONE CRD, THE SAME=27 NOT IN THE MAP=23'),
 chk('periods', (SELECT string_agg(source || ' ' || item || '=' || CAST(amt AS INTEGER), ' ' ORDER BY source, item) FROM r WHERE part = 'SALES PERIOD'), 'S1 2024 | ALL=100 S1 2025 | ALL=63 S1 2025 | RIVA=50 S2 2024=9 S2 2025=24'),
 chk('dataset: credited, held, in held cells', d('S1', 'W1', '02134', 'ALPHA', 'INDEX'), '100 100 12 12 12'),
 chk('dataset: a seller with no held opportunity', d('S1', 'W6', '02134', 'ALPHA', 'INDEX'), '0 0 5 0 0'),
 chk('dataset: unresolved firm kept under its seller', d('S1', 'W1', NULL, NULL, 'INDEX'), '0 0 8 0 0'),
 chk('dataset: s2 holder changes, sales stay', d('S2', 'R2', '10001', 'LPL FINANCIAL LLC - INDEPENDENT', 'INDEX'), '30 0 0 0 0'),
 chk('dataset: s2 new holder gains', d('S2', 'R1', '10001', 'LPL FINANCIAL LLC - INDEPENDENT', 'INDEX'), '0 30 0 0 0'),
 chk('dataset: s2 RVP key trimmed and upper-cased', d('S2', 'R1', '02134', 'ALPHA', 'VARIABLE'), '0 0 1 0 0'),
 chk('dataset: every sale', (SELECT string_agg(source || '=' || CAST(sl AS INTEGER), ' ' ORDER BY source) FROM (SELECT source, SUM(sales) AS sl FROM ssdb_integration.lr_strategy.tmp_o2_dataset GROUP BY ALL) x), 'S1=63 S2=24'),
 chk('dataset: EDJ a channel like the others (opportunity, sales)', (SELECT CAST(SUM(opp_held_old) AS INTEGER) || ' ' || CAST(SUM(sales) AS INTEGER) FROM ssdb_integration.lr_strategy.tmp_o2_dataset WHERE new_channel = 'EDJ'), '70 9'),
 chk('dataset: an EDJ wholesaler complete (held, sold, sold in held cells)', d('S1', 'W4', '60601', 'ECHO', 'INDEX'), '70 70 6 6 6'),
 chk('dataset: the owner''s cut', (SELECT CAST(SUM(sales) AS INTEGER) || ' ' || CAST(SUM(sales_alt) AS INTEGER) FROM ssdb_integration.lr_strategy.tmp_o2_dataset WHERE source = 'S1' AND product <> 'FIXED' AND old_channel IN ('WH', 'FI', 'IFA')), '46 48'),
 chk('dataset: old channel as the sales table has it', (SELECT CAST(SUM(sales) AS INTEGER) FROM ssdb_integration.lr_strategy.tmp_o2_dataset WHERE source = 'S1' AND old_channel = 'ifa '), 2),
 chk('dataset: a sale shares its cell''s row where the old channels agree', (SELECT CAST(opp_held_old AS INTEGER) || ' ' || CAST(sales AS INTEGER) FROM ssdb_integration.lr_strategy.tmp_o2_dataset WHERE source = 'S1' AND wholesaler_key = 'W1' AND broker_name = 'ALPHA' AND product = 'INDEX' AND old_channel = 'IFA'), '100 10'),
 chk('dataset: s1 old channel in firm 1 names is itself', (SELECT COUNT(*) FROM ssdb_integration.lr_strategy.tmp_o2_dataset WHERE source = 'S1' AND old_channel_s1 IS DISTINCT FROM old_channel), 0),
 chk('dataset: s2 sales old channel in firm 1 names', (SELECT string_agg(old_channel_s1 || '=' || CAST(sl AS INTEGER), ' ' ORDER BY old_channel_s1) FROM (SELECT old_channel_s1, SUM(sales) AS sl FROM ssdb_integration.lr_strategy.tmp_o2_dataset WHERE source = 'S2' AND sales <> 0 GROUP BY ALL) x), 'FI=10 IFA=10 WH=4'),
 chk('dataset: sales stay exact', (SELECT data_type FROM duckdb_columns() WHERE table_name = 'tmp_o2_dataset' AND column_name = 'sales'), 'DECIMAL(38,6)'),
 chk('tie-out: sales table 2025, actual', t('SALES TABLE%ACTUAL', '2025'), 46),
 chk('tie-out: sales table 2025, comp''d', t('SALES TABLE%COMP''D', '2025'), 48),
 chk('tie-out: sales table 2024 shown', t('SALES TABLE%ACTUAL', '2024'), 100),
 chk('tie-out: dataset', t('DATASET%ACTUAL', '2025'), 46),
 chk('tie-out: dataset comp''d', (SELECT CAST(SUM(amt) AS INTEGER) FROM r WHERE part = 'TIE-OUT' AND name LIKE 'DATASET%COMP''D'), 48),
 chk('wholesalers s1 old', (SELECT string_agg(item || '=' || n_wholesalers || '/' || CAST(amt AS INTEGER), ' ' ORDER BY item) FROM r WHERE part = 'WHOLESALERS' AND source = 'S1' AND name = 'OLD'), 'HOLDS OPPORTUNITY AND SELLS=5/54 SELLS, HOLDS NO OPPORTUNITY=2/9'),
 chk('wholesalers s2 new', (SELECT string_agg(item || '=' || n_wholesalers || '/' || CAST(amt AS INTEGER), ' ' ORDER BY item) FROM r WHERE part = 'WHOLESALERS' AND source = 'S2' AND name = 'NEW'), 'HOLDS OPPORTUNITY AND SELLS=2/18 SELLS, HOLDS NO OPPORTUNITY=1/6'),
 chk('checks all 0', (SELECT COUNT(*) || ' ' || CAST(SUM(ABS(amt)) AS INTEGER) || ' ' || CAST(COALESCE(SUM(n_rows), 0) AS INTEGER) FROM r WHERE part = 'CHECKS'), '10 0 0'),
 chk('no renamed duplicate column', (SELECT COUNT(*) FROM duckdb_columns() WHERE table_name LIKE 'tmp_o2%' AND regexp_matches(column_name, '_[0-9]+$')), 0);
SELECT '02_sales_test: ok';
SQL
} | duckdb -bail -noheader -list
