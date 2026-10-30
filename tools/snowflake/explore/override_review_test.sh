#!/bin/sh
# Runs override_review.sql in DuckDB on made-up tables with the real column names and checks the answers (worked out
# by hand from the rows below); first checks that its rule rows are profile.sql's.  Prints "override_review_test: ok" or
# stops at the first failed check.  DuckDB has no LISTAGG ... WITHIN GROUP: sed maps it to string_agg(... ORDER BY ...).
# Run from anywhere: sh override_review_test.sh
set -e
here=$(cd "$(dirname "$0")" && pwd)
rules() { sed -n '/^CREATE OR REPLACE TEMPORARY TABLE ssdb_integration.lr_strategy.tmp_s1_channel_rule AS$/,/^) AS v (rule_order/p' "$1"; }
[ -n "$(rules "$here/profile.sql")" ] && [ "$(rules "$here/profile.sql")" = "$(rules "$here/override_review.sql")" ] \
  || { echo "override_review_test: the rule rows differ from profile.sql's"; exit 1; }
{
cat <<'SQL'
ATTACH ':memory:' AS life_prod; CREATE SCHEMA life_prod.lif_murkylake;
ATTACH ':memory:' AS ssdb_integration; CREATE SCHEMA ssdb_integration.lr_strategy;
CREATE TABLE life_prod.lif_murkylake.wc_market_metrics_opportunity (fiscal_yr TEXT, cbd_id TEXT, firm_crd TEXT,
  broker_name TEXT, dist_ch TEXT, channel TEXT, global_sales DECIMAL(18,2));
INSERT INTO life_prod.lif_murkylake.wc_market_metrics_opportunity VALUES
  ('2025','1822','3000','BD THREE','WH','11',300), ('2025','1823','3000','BD THREE - BANK','FI','11',200),
  ('2025','10','1000','BD ONE','IFA','01',500), ('2025','685','6000','MERCER ALLIED COMPANY, L.P.','IFA','01',40),
  ('2025','80','8000','BD EIGHT','','10',10), ('2024','1822','3000','BD THREE','FI','11',9999);
CREATE TABLE ssdb_integration.lr_strategy.s2_opp_t (firm_crd DECIMAL(38,0), broker_name TEXT, dist_ch TEXT, opp DOUBLE);
INSERT INTO ssdb_integration.lr_strategy.s2_opp_t VALUES
  (3000,'BD THREE','REGIONAL',60), (3000,'BD THREE - BANK','BANK',30), (3000,'BD THREE - NEW','BANK',5),
  (1000,'BD ONE','INDEPENDENT',40), (6000,'MERCER ALLIED COMPANY, L.P.','INDEPENDENT',7), (8000,'BD EIGHT','REGIONAL AGENCY',9);
CREATE TABLE ssdb_integration.lr_strategy.crd_dist_override (firm_crd VARCHAR, broker_name VARCHAR, dist_ch VARCHAR);
INSERT INTO ssdb_integration.lr_strategy.crd_dist_override VALUES
  ('3000','BD THREE','FI'), ('3000','BD THREE','FI'), ('3000','BD THREE - BANK','FI'), ('3000','BD THREE - NEW','FI'),
  ('1000','BD ONE','IFA'), ('8000','BD EIGHT','IFA');
SQL
sed -E -e '/^use secondary roles all;$/d' -e '/^SET s2_opp/d' -e 's/TEMPORARY TABLE/TABLE/' \
    -e 's/IDENTIFIER\(\$s2_opp\)/ssdb_integration.lr_strategy.s2_opp_t/g' \
    -e "s/LISTAGG\(DISTINCT ([a-z_]+), ('[^']*')\) WITHIN GROUP \(ORDER BY [a-z_]+\)/string_agg(DISTINCT \1, \2 ORDER BY \1)/g" \
    -e "s/LISTAGG\(([a-z_]+), ('[^']*')\) WITHIN GROUP \(ORDER BY ([^)]+)\)/string_agg(\1, \2 ORDER BY \3)/g" \
    -e '/^--2\. The review/{n;s/^WITH$/CREATE TABLE rv AS WITH/;}' "$here/override_review.sql"
cat <<'SQL'
CREATE MACRO chk(name, got, want) AS CASE WHEN got IS NOT DISTINCT FROM want THEN 'ok'
  ELSE error(name || ': got ' || COALESCE(CAST(got AS VARCHAR), 'NULL') || ', want ' || CAST(want AS VARCHAR)) END;
SELECT
 chk('only the CRD with a disagreement, all its names', (SELECT COUNT(*) FROM rv), 3),
 chk('the disputed name first', (SELECT broker_name FROM rv WHERE rowid = 0), 'BD THREE'),
 chk('disputed: status', (SELECT status FROM rv WHERE broker_name = 'BD THREE'), 'OVERRIDE <> ROUTE'),
 chk('disputed: override', (SELECT override_dist_ch FROM rv WHERE broker_name = 'BD THREE'), 'FI'),
 chk('disputed: route', (SELECT route_dist_ch FROM rv WHERE broker_name = 'BD THREE'), 'WH'),
 chk('disputed: firm 1 mix', (SELECT s1_channel_mix FROM rv WHERE broker_name = 'BD THREE'), 'WH 100.0%'),
 chk('disputed: company ID', (SELECT s1_company_ids FROM rv WHERE broker_name = 'BD THREE'), '1822'),
 chk('disputed: fiscal year 2025 only', (SELECT s1_opp FROM rv WHERE broker_name = 'BD THREE'), 300),
 chk('disputed: source 2 label', (SELECT s2_own_dist_ch FROM rv WHERE broker_name = 'BD THREE'), 'REGIONAL'),
 chk('disputed: share of source 2', (SELECT pct_s2_opp FROM rv WHERE broker_name = 'BD THREE'), 39.735),
 chk('disputed: repeated override rows', (SELECT override_rows FROM rv WHERE broker_name = 'BD THREE'), 2),
 chk('sibling agrees', (SELECT status FROM rv WHERE broker_name = 'BD THREE - BANK'), 'OVERRIDE = ROUTE'),
 chk('sibling before the smaller one', (SELECT broker_name FROM rv WHERE rowid = 1), 'BD THREE - BANK'),
 chk('name firm 1 lacks: CRD route', (SELECT route_from || ' ' || route_dist_ch FROM rv WHERE broker_name = 'BD THREE - NEW'), 'CRD 2+'),
 chk('name firm 1 lacks: override fills', (SELECT status FROM rv WHERE broker_name = 'BD THREE - NEW'), 'OVERRIDE FILLS'),
 chk('no renamed duplicate column', (SELECT COUNT(*) FROM duckdb_columns() WHERE table_name IN ('rv', 'tmp_rv_s1', 'tmp_rv_s2') AND regexp_matches(column_name, '_[0-9]+$')), 0);
SELECT 'override_review_test: ok';
SQL
} | duckdb -bail -noheader -list
