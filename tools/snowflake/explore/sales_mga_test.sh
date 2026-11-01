#!/bin/sh
# Runs 01_opportunity_sales.sql, then sales_mga.sql, in DuckDB on 02_sales_test.sh's made-up tables (its fixture
# block, read from that file), and checks sales_mga.sql's result set (answers worked out by hand from those rows).
# Prints "sales_mga_test: ok" or stops at the first failed check.  Run from anywhere: sh sales_mga_test.sh
set -e
here=$(cd "$(dirname "$0")" && pwd)
top=$(cd "$here/.." && pwd)
{
awk '/^cat <<.SQL.$/ && !s {s=1; next} s && /^SQL$/ {exit} s' "$top/02_sales_test.sh"
cat <<'SQL'
-- this test's own row: a sale with no market metrics firm under M1, a code resolved sales put on two firms
INSERT INTO ssdb_integration.lr_strategy.s1_sales_t VALUES
  (2025,2,2,'INDEX','IFA','NEW BD',77,'P','','02134','MA','W1','N1','ALL',1,1,1,'M1');
SQL
sed -e '/^use /d' -e '/^  -- owner routes: begin$/,/^  -- owner routes: end$/d' -e '/^  -- owner rows: begin$/,/^  -- owner rows: end$/d' -e '/^SET s[12]_/d' -e 's/TEMPORARY TABLE/TABLE/' \
    -e 's/IDENTIFIER(\$s1_territories)/ssdb_integration.lr_strategy.s1_terr_t/g' \
    -e 's/IDENTIFIER(\$s2_opp)/ssdb_integration.lr_strategy.s2_opp_t/g' \
    -e 's/IDENTIFIER(\$s2_territories)/ssdb_integration.lr_strategy.s2_terr_t/g' \
    -e 's/IDENTIFIER(\$s1_sales)/ssdb_integration.lr_strategy.s1_sales_t/g' \
    -e 's/IDENTIFIER(\$s2_sales)/ssdb_integration.lr_strategy.s2_sales_t/g' \
    -e '/^--15\./,$d' "$top/01_opportunity_sales.sql"
sed -e '/^use /d' -e 's/TEMPORARY TABLE/TABLE/' \
    -e "s/^SELECT 'SALES_MGA' AS file,/CREATE TABLE full_result AS SELECT 'SALES_MGA' AS file,/" \
    "$here/sales_mga.sql"
echo "CREATE TABLE r AS SELECT * FROM ssdb_integration.lr_strategy.tmp_mga_out;"
cat <<'SQL'
CREATE MACRO chk(name, got, want) AS CASE WHEN got IS NOT DISTINCT FROM want THEN 'ok'
  ELSE error(name || ': got ' || COALESCE(CAST(got AS VARCHAR), 'NULL') || ', want ' || CAST(want AS VARCHAR)) END;
CREATE MACRO code(i) AS (SELECT CAST(amt AS INTEGER) || ' ' || n_companies || ' ' || n_firms || ' ' || n_channels || ' '
  || n_sellers || ' ' || n_zips FROM r WHERE part = 'CODES' AND item = i);
CREATE MACRO span(i) AS (SELECT string_agg(item2 || '=' || COALESCE(n_codes, n_companies) || '/' || CAST(amt AS INTEGER), ' ' ORDER BY item2)
  FROM r WHERE part = 'SPANS' AND item = i);
SELECT
 chk('codes: one code on two companies, firms, channels, three sellers', code('M1'), '16 3 2 2 3 2'),
 chk('codes: a split company''s code, one firm found', code('M3'), '16 1 2 2 2 1'),
 chk('codes: blank and untrimmed-blank together, no company not counted', code('(BLANK)'), '3 1 1 2 1 1'),
 chk('codes: every sale', (SELECT CAST(SUM(amt) AS INTEGER) || ' ' || COUNT(*) FROM r WHERE part = 'CODES'), '65 10'),
 chk('spans: companies', span('CODES ON COMPANIES'), '1=8/46 2+=1/16'),
 chk('spans: firms (0: no firm found)', span('CODES ON FIRMS'), '0=2/13 1=5/17 2+=2/32'),
 chk('spans: channels', span('CODES ON CHANNELS'), '1=7/30 2+=2/32'),
 chk('spans: sellers', span('CODES ON SELLERS'), '1=7/30 2+=2/32'),
 chk('spans: companies by codes', span('COMPANIES BY CODES'), '0=1/1 1=5/17 2+=3/47'),
 chk('unresolved: the split LPL sale''s code is on one firm elsewhere', (SELECT string_agg(item || ' | ' || item2 || '=' || CAST(amt AS INTEGER), ', ' ORDER BY item, item2) FROM r WHERE part = 'UNRESOLVED SALES BY CODE'), 'NO COMPANY | NO CODE=1, NO MARKET METRICS FIRM | CODE ON 2+ FIRMS IN RESOLVED SALES=2, NO MARKET METRICS FIRM | CODE ON NO RESOLVED SALE=13'),
 chk('company x code: LPL by code and basis', (SELECT string_agg(item2 || '=' || CAST(amt AS INTEGER), ', ' ORDER BY item2) FROM r WHERE part = 'COMPANY X CODE' AND item = '8 | LPL'), 'M3 | SPLIT, MATCHED BY CHANNEL | LPL FINANCIAL LLC - BANK=7, M3 | SPLIT, MATCHED BY ZIP | LPL FINANCIAL LLC - INDEPENDENT=9, M4 | SPLIT, MATCHED BY ZIP | LPL FINANCIAL LLC=4'),
 chk('company x code: every sale', (SELECT CAST(SUM(amt) AS INTEGER) FROM r WHERE part = 'COMPANY X CODE'), 65),
 chk('pct: of part, of item in spans', (SELECT CAST(SUM(pct_amt) AS INTEGER) FROM r WHERE part = 'SPANS' AND item = 'CODES ON FIRMS') || ' ' || (SELECT CAST(ROUND(SUM(pct_amt)) AS INTEGER) FROM r WHERE part = 'CODES'), '100 100'),
 chk('one result: this file and all of 01''s', (SELECT string_agg(file || '=' || n, ' ' ORDER BY file) FROM (SELECT file, COUNT(*) AS n FROM full_result GROUP BY ALL) x) = '01 OPPORTUNITY=' || (SELECT COUNT(*) FROM ssdb_integration.lr_strategy.tmp_o1_out) || ' 01 SALES=' || (SELECT COUNT(*) FROM ssdb_integration.lr_strategy.tmp_o2_out) || ' SALES_MGA=' || (SELECT COUNT(*) FROM r), true),
 chk('one result: 01''s checks in it, all 0', (SELECT COUNT(*) || ' ' || CAST(SUM(ABS(amt)) AS INTEGER) FROM full_result WHERE file = '01 SALES' AND part = 'CHECKS'), '11 0'),
 chk('no firm 2 rows', (SELECT CAST(SUM(amt) AS INTEGER) FROM r WHERE part = 'COMPANY X CODE' AND item LIKE '100 |%'), NULL);
SELECT 'sales_mga_test: ok';
SQL
} | duckdb -bail -noheader -list
