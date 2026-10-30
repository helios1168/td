#!/bin/sh
# Runs 01_opportunity.sql in DuckDB on made-up tables with the real column names, one planted case per outcome, and
# checks the answers (worked out by hand from the rows below); first checks that its four decision tables are
# explore/profile.sql's, row for row.  Prints "01_opportunity_test: ok" or stops at the first failed check.
# Run from anywhere: sh 01_opportunity_test.sh
set -e
here=$(cd "$(dirname "$0")" && pwd)
block() { sed -n "/^CREATE OR REPLACE TEMPORARY TABLE ssdb_integration.lr_strategy.$2 AS\$/,/ AS v (/p" "$1"; }
for t in tmp_s1_channel_rule tmp_s2_label_terr tmp_s1ch_s2terr tmp_scope_out; do
  [ -n "$(block "$here/01_opportunity.sql" $t)" ] && [ "$(block "$here/01_opportunity.sql" $t)" = "$(block "$here/explore/profile.sql" $t)" ] \
    || { echo "01_opportunity_test: $t differs from explore/profile.sql's"; exit 1; }
done
{
cat <<'SQL'
ATTACH ':memory:' AS life_prod; CREATE SCHEMA life_prod.lif_murkylake;
ATTACH ':memory:' AS ssdb_integration; CREATE SCHEMA ssdb_integration.lr_strategy;
CREATE TABLE life_prod.lif_murkylake.wc_market_metrics_opportunity (fiscal_yr TEXT, quarter TEXT, cbd_id TEXT,
  client_firm_id TEXT, firm_crd TEXT, broker_name TEXT, dist_ch TEXT, channel TEXT, product_line TEXT,
  va_product_type TEXT, zip_code TEXT, global_sales DECIMAL(18,2));
INSERT INTO life_prod.lif_murkylake.wc_market_metrics_opportunity VALUES
  ('2025','Q1','10',NULL,'100','Alpha','IFA','01','VA','IOVA','2134',100),
  ('2025','Q1','10',NULL,'100','ALPHA','','01','FA','-77777','02134',20),
  ('2025','Q2','10',NULL,'100','ALPHA','IFA','01','FA','-77777','02134',30),
  ('2025','Q2','10',NULL,'100','ALPHA','IFA','01','VA','TRVA','02134',60),
  ('2025','Q2','10',NULL,'100','ALPHA','IFA','01','XX',NULL,'02134',2),
  ('2025','Q1','0',NULL,'200','Wells Fargo Clearing Services, LLC','FI','11','IA','-77777','10001',300),
  ('2025','Q1','0',NULL,'200','Wells Fargo Clearing Services, LLC - BANK','FI','11','IA','-77777','10001',200),
  ('2025','Q3','57',NULL,'300','CHASE','FI','11','VA','RILA','60601',150),
  ('2025','Q3','0','14','400','DELTA','WH','11','FA','-77777','10001',50),
  ('2025','Q3','3',NULL,'500','ECHO','EDWARD JONES','13','IA','-77777','60601',70),
  ('2025','Q4','438',NULL,'600','FOX','IFA','01','IA','-77777','02134',40),
  ('2025','Q4','600',NULL,'600','FOX','IFA','01','FA','-77777','02134',10),
  ('2025','Q4','700',NULL,'700','GOLF','','10','IA','-77777','30301',25),
  ('2025','Q4','800',NULL,'800','HOTEL',NULL,'10','IA','-77777','02134',15),
  ('2025','Q4','900',NULL,'','INDIA','FI','11','FA','-77777','10001',5),
  ('2025','Q4','805',NULL,'900','JULIET','IFA','08','IA','-77777','02134',35),
  ('2024','Q4','10',NULL,'100','ALPHA','IFA','01','VA','IOVA','02134',9999);
CREATE TABLE ssdb_integration.lr_strategy.s1_terr_t (whslr_id TEXT, whslr_nm TEXT, zip TEXT, state_cd TEXT,
  new_dist_channel TEXT);
INSERT INTO ssdb_integration.lr_strategy.s1_terr_t VALUES
  ('W1','N1','02134','MA','IFA'), ('W3','N3','2134','MA','IFA'), ('W2','N2','10001','NY','WH'),
  ('W2','N2','10001','NY','WH'), ('W5','N5','10001','NY','FI'), ('W6','N6','30301','GA','IFA'),
  ('W4','N4','60601','IL','EDJ');
CREATE TABLE ssdb_integration.lr_strategy.s2_opp_t (channel DOUBLE, dist_ch TEXT, zip_code DECIMAL(38,0),
  firm_crd DECIMAL(38,0), broker_name TEXT, product_line TEXT, va_product_type TEXT, opp DOUBLE);
INSERT INTO ssdb_integration.lr_strategy.s2_opp_t VALUES
  (NULL,'INDEPENDENT',2134,100,'ALPHA','IA',NULL,40),
  (NULL,'REGIONAL',10001,200,'WELLS FARGO CLEARING SERVICES, LLC','IA',NULL,60),
  (NULL,'BANK',10001,200,'WELLS FARGO CLEARING SERVICES, LLC - BANK','IA',NULL,30),
  (NULL,'REGIONAL',60601,300,'CHASE','IA',NULL,20),
  (NULL,'NO CHANNEL',30301,700,'GOLF','FA',NULL,9),
  (NULL,'INDEPENDENT',12345,999,'ZULU','FA',NULL,7),
  (NULL,'REGIONAL',60601,500,'ECHO','IA',NULL,13),
  (NULL,'INDEPENDENT',2134,100,'ALPHA - OTHER','VA','RILA',11),
  (NULL,'REGIONAL AGENCY',30301,NULL,'NONAME','IA',NULL,3),
  (NULL,'BANK',10001,1000,'KILO','IA',NULL,5),
  (NULL,'BANK',60601,300,'CHASE BANK','IA',NULL,8);
CREATE TABLE ssdb_integration.lr_strategy.crd_dist_override (firm_crd VARCHAR, broker_name VARCHAR, dist_ch VARCHAR);
INSERT INTO ssdb_integration.lr_strategy.crd_dist_override VALUES
  ('700', NULL, 'IFA'), ('700', NULL, 'IFA'), ('999', NULL, 'WH'), ('200', 'Wells Fargo Clearing Services, LLC', 'FI');
CREATE TABLE ssdb_integration.lr_strategy.s2_terr_t (rvp TEXT, territory_id TEXT, zipcode TEXT, state TEXT,
  channel TEXT, channel_name TEXT);
INSERT INTO ssdb_integration.lr_strategy.s2_terr_t VALUES
  ('R1','T1','02134','MA','FP','x'), ('R2','T2','10001','NY','BD','x'), ('R2','T2','60601','IL','BD','x'),
  ('R3','T3','10001','NY','BK','x'), ('R7','T7','10001','NY','BK','x'), ('R8','T8','60601','IL','BK','x'),
  ('R6','T6','30301','GA','FP','x'), ('R4','T4','30301','GA','RA','x');
SQL
sed -e '/^use secondary roles all;$/d' -e '/^SET s[12]_/d' -e 's/TEMPORARY TABLE/TABLE/' \
    -e 's/IDENTIFIER(\$s1_territories)/ssdb_integration.lr_strategy.s1_terr_t/g' \
    -e 's/IDENTIFIER(\$s2_opp)/ssdb_integration.lr_strategy.s2_opp_t/g' \
    -e 's/IDENTIFIER(\$s2_territories)/ssdb_integration.lr_strategy.s2_terr_t/g' \
    -e '/^--8\./,$d' "$here/01_opportunity.sql"
cat <<'SQL'
CREATE TABLE r AS SELECT * FROM ssdb_integration.lr_strategy.tmp_o1_out;
CREATE MACRO chk(name, got, want) AS CASE WHEN got IS NOT DISTINCT FROM want THEN 'ok'
  ELSE error(name || ': got ' || COALESCE(CAST(got AS VARCHAR), 'NULL') || ', want ' || CAST(want AS VARCHAR)) END;
CREATE MACRO a(p, s, n, i) AS (SELECT SUM(amt) FROM r WHERE part = p AND source IS NOT DISTINCT FROM s
                                AND name IS NOT DISTINCT FROM n AND item IS NOT DISTINCT FROM i);
CREATE MACRO h(p, s, n, i) AS (SELECT n_holders FROM r WHERE part = p AND source = s AND name = n AND item = i);
SELECT
 chk('s1 source total = cells', a('CHECKS', 'S1', 'SOURCE MINUS CELLS (MUST BE 0)', NULL), 0),
 chk('s2 source total = cells', a('CHECKS', 'S2', 'SOURCE MINUS CELLS (MUST BE 0)', NULL), 0),
 chk('s1 I4', a('CHECKS', 'S1', 'CURRENT MINUS NEW, DROPPED COUNTED (MUST BE 0)', NULL), 0),
 chk('firm keys unique', (SELECT n_firms FROM r WHERE name = 'FIRM KEYS REPEATED (MUST BE 0)'), 0),
 chk('one listed label per firm', (SELECT n_firms FROM r WHERE name = 'FIRMS WITH 2+ NEW LABELS (MUST BE 0)'), 0),
 chk('firm table: both sources, CRD only', (SELECT COUNT(*) FROM ssdb_integration.lr_strategy.tmp_o1_firm), 14),
 chk('scope in, s1', a('SCOPE', 'S1', NULL, 'IN'), 957),
 chk('scope EDJ by route', a('SCOPE', 'S1', NULL, 'OUT: EDJ'), 70),
 chk('scope AFS by company takes the whole firm', a('SCOPE', 'S1', NULL, 'OUT: AFS'), 50),
 chk('scope AMER by company rule', a('SCOPE', 'S1', NULL, 'OUT: AMER'), 35),
 chk('scope s2 by firm 1 route', a('SCOPE', 'S2', NULL, 'OUT: EDJ'), 13),
 chk('V1 s1 current IFA, ZIP padded, upper-cased name', a('V1 CHANNEL', 'S1', 'CURRENT', 'IFA'), 192),
 chk('V1 s1 current blank', a('V1 CHANNEL', 'S1', 'CURRENT', '(BLANK)'), 60),
 chk('V1 s1 current WH by name rule', a('V1 CHANNEL', 'S1', 'CURRENT', 'WH'), 350),
 chk('V1 s1 new IFA: blank rows take the route, override fills', a('V1 CHANNEL', 'S1', 'NEW', 'IFA'), 237),
 chk('V1 s1 new Wells WH: name and company 14 via client firm', a('V1 CHANNEL', 'S1', 'NEW', 'Wells WH'), 350),
 chk('V1 s1 new Wells FI', a('V1 CHANNEL', 'S1', 'NEW', 'Wells FI'), 200),
 chk('V1 s1 new National', a('V1 CHANNEL', 'S1', 'NEW', 'National (Chase)'), 150),
 chk('V1 s1 new UNMAPPED: no channel, no CRD', a('V1 CHANNEL', 'S1', 'NEW', 'UNMAPPED'), 20),
 chk('V1 s2 current NO CHANNEL kept', a('V1 CHANNEL', 'S2', 'CURRENT', 'NO CHANNEL'), 9),
 chk('V1 s2 new IFA', a('V1 CHANNEL', 'S2', 'NEW', 'IFA'), 60),
 chk('V1 s2 new WH: override fills a firm source 1 lacks', a('V1 CHANNEL', 'S2', 'NEW', 'WH'), 7),
 chk('V1 s2 new FI: CRD route for a name source 1 lacks', a('V1 CHANNEL', 'S2', 'NEW', 'FI'), 8),
 chk('V1 s2 new UNMAPPED', a('V1 CHANNEL', 'S2', 'NEW', 'UNMAPPED'), 8),
 chk('V2A s1 same', (SELECT SUM(amt) FROM r WHERE part = 'V2A RECLASSIFIED' AND source = 'S1' AND item2 = 'SAME'), 192),
 chk('V2A s1 WH -> Wells WH', a('V2A RECLASSIFIED', 'S1', NULL, 'WH -> Wells WH'), 350),
 chk('V2A s1 blank -> IFA', a('V2A RECLASSIFIED', 'S1', NULL, '(BLANK) -> IFA'), 45),
 chk('V2A s2 label -> new', a('V2A RECLASSIFIED', 'S2', NULL, 'BANK -> Wells FI'), 30),
 chk('V2B s1 same holder', a('V2B HOLDER MOVES', 'S1', NULL, 'SAME HOLDER'), 742),
 chk('V2B s1 gains', a('V2B HOLDER MOVES', 'S1', NULL, 'GAINS A HOLDER'), 45),
 chk('V2B s1 none in either', a('V2B HOLDER MOVES', 'S1', NULL, 'NO HOLDER IN EITHER'), 165),
 chk('V2B s1 loses', a('V2B HOLDER MOVES', 'S1', NULL, 'LOSES ITS HOLDER'), 5),
 chk('V2B s2 same (Q29: Wells FI stays with FI -> BK)', a('V2B HOLDER MOVES', 'S2', NULL, 'SAME HOLDER'), 149),
 chk('V2B s2 other holder (Chase: BD -> BK)', a('V2B HOLDER MOVES', 'S2', NULL, 'OTHER HOLDER'), 20),
 chk('V2B s2 gains (NO CHANNEL routed)', a('V2B HOLDER MOVES', 'S2', NULL, 'GAINS A HOLDER'), 9),
 chk('V2B s2 loses', a('V2B HOLDER MOVES', 'S2', NULL, 'LOSES ITS HOLDER'), 8),
 chk('V2B s2 none', a('V2B HOLDER MOVES', 'S2', NULL, 'NO HOLDER IN EITHER'), 7),
 chk('V3 s1 current one holder', a('V3 COVERAGE', 'S1', 'CURRENT', 'ONE HOLDER'), 555),
 chk('V3 s1 current one holder: holders', h('V3 COVERAGE', 'S1', 'CURRENT', 'ONE HOLDER'), 2),
 chk('V3 s1 current lowest of 2', a('V3 COVERAGE', 'S1', 'CURRENT', 'LOWEST OF 2+ HOLDERS'), 192),
 chk('V3 s1 current no channel', a('V3 COVERAGE', 'S1', 'CURRENT', 'NO HOLDER: NO TERRITORY CHANNEL'), 60),
 chk('V3 s1 current none at ZIP', a('V3 COVERAGE', 'S1', 'CURRENT', 'NO HOLDER: NONE AT THE ZIP'), 150),
 chk('V3 s1 new one holder', a('V3 COVERAGE', 'S1', 'NEW', 'ONE HOLDER'), 575),
 chk('V3 s1 new one holder: holders', h('V3 COVERAGE', 'S1', 'NEW', 'ONE HOLDER'), 3),
 chk('V3 s1 new no channel', a('V3 COVERAGE', 'S1', 'NEW', 'NO HOLDER: NO TERRITORY CHANNEL'), 20),
 chk('V3 s2 current lowest of 2', a('V3 COVERAGE', 'S2', 'CURRENT', 'LOWEST OF 2+ HOLDERS'), 35),
 chk('V3 s2 current one: holders', h('V3 COVERAGE', 'S2', 'CURRENT', 'ONE HOLDER'), 4),
 chk('V3 s2 new one holder', a('V3 COVERAGE', 'S2', 'NEW', 'ONE HOLDER'), 148),
 chk('V3 s2 new no channel', a('V3 COVERAGE', 'S2', 'NEW', 'NO HOLDER: NO TERRITORY CHANNEL'), 8),
 chk('route basis s1 name', a('CHECKS', 'S1', 'ROUTE BASIS', 'NAME'), 1067),
 chk('route basis s1 override fills', a('CHECKS', 'S1', 'ROUTE BASIS', 'OVERRIDE FILLS NO CHANNEL'), 25),
 chk('route basis s1 unmapped', a('CHECKS', 'S1', 'ROUTE BASIS', 'UNMAPPED: NO CHANNEL'), 15),
 chk('route basis s1 no CRD', a('CHECKS', 'S1', 'ROUTE BASIS', 'NO CRD'), 5),
 chk('route basis s2 CRD', a('CHECKS', 'S2', 'ROUTE BASIS', 'CRD'), 19),
 chk('route basis s2 override, no source 1 rows', a('CHECKS', 'S2', 'ROUTE BASIS', 'OVERRIDE FILLS NO SOURCE 1 ROWS'), 7),
 chk('route basis s2 unmapped', a('CHECKS', 'S2', 'ROUTE BASIS', 'UNMAPPED: NO SOURCE 1 ROWS'), 5),
 chk('override disagrees, route kept, s1', a('CHECKS', 'S1', 'OVERRIDE <> ROUTE, ROUTE KEPT', 'FI <> WH'), 300),
 chk('override disagrees, route kept, s2', a('CHECKS', 'S2', 'OVERRIDE <> ROUTE, ROUTE KEPT', 'FI <> WH'), 60),
 chk('listed: Wells WH', a('CHECKS', 'S1', 'LISTED FIRMS: LABEL | HOLDER CHANNEL | ROUTE', 'Wells WH | WH | WH'), 350),
 chk('listed: Wells WH firms', (SELECT n_firms FROM r WHERE item = 'Wells WH | WH | WH' AND source = 'S1'), 2),
 chk('listed: AFS', a('CHECKS', 'S1', 'LISTED FIRMS: LABEL | HOLDER CHANNEL | ROUTE', 'AFS | (NONE) | IFA'), 50),
 chk('listed s2: National', a('CHECKS', 'S2', 'LISTED FIRMS: LABEL | HOLDER CHANNEL | ROUTE', 'National (Chase) | FI | FI'), 20),
 chk('another name of the CRD listed', a('CHECKS', 'S2', 'NO LISTED LABEL, ANOTHER NAME OF THE CRD HAS ONE', 'FI'), 8),
 chk('cells with 2 current labels', (SELECT n_cells || ' ' || amt FROM r WHERE name = 'CELLS WITH 2+ CURRENT LABELS'), '1 50.0'),
 chk('product unmapped', a('CHECKS', 'S1', 'PRODUCT UNMAPPED', 'NO PRODUCT'), 2),
 chk('product map', (SELECT string_agg(product || '=' || amt, ' ' ORDER BY product) FROM ssdb_integration.lr_strategy.tmp_o1_cells_s2 WHERE firm_crd = '100'), 'INDEX=40.0 RILA=11.0'),
 chk('s1 holder: the lowest ID of two', (SELECT cur_holder FROM ssdb_integration.lr_strategy.tmp_o1_cells_s1 WHERE product = 'IOVA'), 'W1'),
 chk('s2 holder: the lowest ID of two', (SELECT cur_holder FROM ssdb_integration.lr_strategy.tmp_o1_cells_s2 WHERE broker_name = 'KILO'), 'T3'),
 chk('dataset: in-scope cells, both sources', (SELECT COUNT(*) || ' ' || SUM(opportunity) FROM ssdb_integration.lr_strategy.tmp_o1_dataset), '22 1150.0'),
 chk('dataset: out of scope left out', (SELECT COUNT(*) FROM ssdb_integration.lr_strategy.tmp_o1_dataset WHERE broker_name IN ('ECHO', 'FOX', 'JULIET')), 0),
 chk('dataset: s1 wholesaler names, lowest ID', (SELECT old_wholesaler || ' ' || new_wholesaler FROM ssdb_integration.lr_strategy.tmp_o1_dataset WHERE product = 'IOVA'), 'N1 N1'),
 chk('dataset: s2 RVPs, Chase moves', (SELECT old_wholesaler || ' ' || new_wholesaler || ' ' || old_channel || ' ' || new_channel FROM ssdb_integration.lr_strategy.tmp_o1_dataset WHERE broker_name = 'CHASE' AND source = 'S2'), 'R2 R8 REGIONAL National (Chase)'),
 chk('dataset: s1 by new channel', (SELECT SUM(opportunity) FROM ssdb_integration.lr_strategy.tmp_o1_dataset WHERE source = 'S1' AND new_channel = 'Wells WH'), 350),
 chk('old channel in firm 1 terms, s2 (option a)', (SELECT string_agg(COALESCE(old_channel_s1, '(BLANK)') || '=' || amt, ' ' ORDER BY old_channel_s1 NULLS LAST) FROM (SELECT old_channel_s1, SUM(opportunity) AS amt FROM ssdb_integration.lr_strategy.tmp_o1_dataset WHERE source = 'S2' GROUP BY ALL) x), 'FI=43.0 IFA=58.0 PRI=3.0 WH=80.0 (BLANK)=9.0'),
 chk('old channel in firm 1 terms, s1 = its own', (SELECT COUNT(*) FROM ssdb_integration.lr_strategy.tmp_o1_dataset WHERE source = 'S1' AND old_channel_s1 IS DISTINCT FROM old_channel), 0),
 chk('Q39 pairs one to one', (SELECT n_firms FROM r WHERE name = 'Q39 TERRITORY CHANNELS ON 2+ FIRM 1 CHANNELS (MUST BE 0)'), 0),
 chk('no renamed duplicate column', (SELECT COUNT(*) FROM duckdb_columns() WHERE table_name LIKE 'tmp_o1%' AND regexp_matches(column_name, '_[0-9]+$')), 0);
SELECT '01_opportunity_test: ok';
SQL
} | duckdb -bail -noheader -list
