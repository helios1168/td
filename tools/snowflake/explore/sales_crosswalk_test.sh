#!/bin/sh
# Runs 01_opportunity_sales.sql, then sales_crosswalk.sql, in DuckDB on 02_sales_test.sh's made-up tables (its fixture
# block, read from that file), and checks sales_crosswalk.sql's result set, its own last statement (answers worked out
# by hand from that fixture).  DuckDB has no LISTAGG ... WITHIN GROUP: sed maps it to string_agg(... ORDER BY ...).
# Prints "sales_crosswalk_test: ok" or stops at the first failed check.  Run from anywhere: sh sales_crosswalk_test.sh
set -e
here=$(cd "$(dirname "$0")" && pwd)
top=$(cd "$here/.." && pwd)
{
awk '/^cat <<.SQL.$/ && !s {s=1; next} s && /^SQL$/ {exit} s' "$top/02_sales_test.sh"
cat <<'SQL'
-- this test's own rows: a firm 2 firm whose CRD equals firm 1's company 10, so the two sources' IDs overlap; and a
-- one-name firm 2 cell labelled REGIONAL (BD, R2) whose firm 1 route is IFA (FP, R1), with a sale by R2 in it
INSERT INTO ssdb_integration.lr_strategy.s2_opp_t VALUES (NULL,'INDEPENDENT',2134,10,'TEN BD','IA',NULL,1),
  (NULL,'REGIONAL',10001,100,'ALPHA','IA',NULL,5);
INSERT INTO ssdb_integration.lr_strategy.s2_sales_t VALUES
  ('P','Alpha Inc',100.0,'REGIONAL','NY','A','x','R2','D1',2025,2,2,'10001','IA');
-- and a firm 1 row with no product bucket: outside the window, and it must be listed there
INSERT INTO ssdb_integration.lr_strategy.s1_sales_t VALUES
  (2025,3,3,'INDEX','IFA','ALPHA BD',10,'P','','02134','MA','W1','N1',NULL,1,1,1);
SQL
sed -e '/^use secondary roles all;$/d' -e '/^SET s[12]_/d' -e 's/TEMPORARY TABLE/TABLE/' \
    -e 's/IDENTIFIER(\$s1_territories)/ssdb_integration.lr_strategy.s1_terr_t/g' \
    -e 's/IDENTIFIER(\$s2_opp)/ssdb_integration.lr_strategy.s2_opp_t/g' \
    -e 's/IDENTIFIER(\$s2_territories)/ssdb_integration.lr_strategy.s2_terr_t/g' \
    -e 's/IDENTIFIER(\$s1_sales)/ssdb_integration.lr_strategy.s1_sales_t/g' \
    -e 's/IDENTIFIER(\$s2_sales)/ssdb_integration.lr_strategy.s2_sales_t/g' \
    -e '/^--15\./,$d' "$top/01_opportunity_sales.sql"
sed -E -e '/^use secondary roles all;$/d' -e 's/TEMPORARY TABLE/TABLE/' \
    -e 's/IDENTIFIER\(\$s1_sales\)/ssdb_integration.lr_strategy.s1_sales_t/g' \
    -e 's/IDENTIFIER\(\$s2_sales\)/ssdb_integration.lr_strategy.s2_sales_t/g' \
    -e "s/LISTAGG\(DISTINCT ([a-z_]+), ('[^']*')\) WITHIN GROUP \(ORDER BY [a-z_]+\)/string_agg(DISTINCT \1, \2 ORDER BY \1)/g" \
    -e 's/^SELECT \* FROM ssdb_integration.lr_strategy.tmp_xw$/CREATE TABLE r AS SELECT * FROM ssdb_integration.lr_strategy.tmp_xw/' \
    "$here/sales_crosswalk.sql"
cat <<'SQL'
CREATE MACRO chk(name, got, want) AS CASE WHEN got IS NOT DISTINCT FROM want THEN 'ok'
  ELSE error(name || ': got ' || COALESCE(CAST(got AS VARCHAR), 'NULL') || ', want ' || CAST(want AS VARCHAR)) END;
CREATE MACRO x(s, f, ch, pr) AS (SELECT CAST(sales AS INTEGER) || ' ' || n_sellers || ' ' || firm_basis || ' '
  || COALESCE(broker_name, '-') || ' ' || new_channel || ' ' || COALESCE(match_channel, '-') || ' ' || COALESCE(n_candidates, 0)
  FROM r WHERE part = 'CROSSWALK' AND source = s AND sales_firm = f AND raw_channel = ch AND raw_product = pr);
SELECT
 chk('crosswalk keys per source', (SELECT string_agg(source || '=' || n, ' ' ORDER BY source) FROM (SELECT source, COUNT(*) AS n FROM r WHERE part = 'CROSSWALK' GROUP BY ALL) z), 'S1=12 S2=11'),
 chk('crosswalk $ = the 2025 window', (SELECT string_agg(source || '=' || CAST(a AS INTEGER), ' ' ORDER BY source) FROM (SELECT source, SUM(sales) AS a FROM r WHERE part = 'CROSSWALK' GROUP BY ALL) z), 'S1=63 S2=26'),
 chk('out of window', (SELECT string_agg(source || ' ' || item || '=' || CAST(sales AS INTEGER), '; ' ORDER BY source, item) FROM r WHERE part = 'OUT OF WINDOW'), 'S1 FISCAL_YR 2024 | BUCKET ALL=100; S1 FISCAL_YR 2025 | BUCKET (NULL)=3; S1 FISCAL_YR 2025 | BUCKET RIVA=50; S2 YEAR 2024=9'),
 chk('firm 1, one firm, two sellers', x('S1', 'ALPHA BD', 'IFA', 'INDEX'), '15 2 ONE FIRM ALPHA IFA IFA 1'),
 chk('firm 1, the channel keeps its spelling', x('S1', 'ALPHA BD', 'ifa ', 'INDEX'), '2 1 ONE FIRM ALPHA IFA IFA 1'),
 chk('firm 1, split matched by channel', x('S1', 'LPL', 'FI', 'INDEX'), '7 1 SPLIT, MATCHED BY CHANNEL LPL FINANCIAL LLC - BANK FI FI 3'),
 chk('firm 1, IMO on IFA: two IFA names, no firm', x('S1', 'LPL', 'IMO', 'INDEX'), '4 1 SPLIT, 2+ CHANNEL MATCHES - UNMAPPED IFA 3'),
 chk('firm 1, no market metrics firm', x('S1', 'AFS', 'IFA', 'INDEX'), '5 1 NO MARKET METRICS FIRM - UNMAPPED IFA 0'),
 chk('firm 1, the candidates listed with routes', (SELECT candidates FROM r WHERE part = 'CROSSWALK' AND sales_firm = 'LPL' AND raw_channel = 'FI'), '200 LPL FINANCIAL LLC (IFA) | 200 LPL FINANCIAL LLC - BANK (FI) | 200 LPL FINANCIAL LLC - INDEPENDENT (IFA)'),
 chk('firm 2, mixed-case label matched through Q19 and Q39', x('S2', 'LPL Corp', 'Bank', 'IA'), '1 1 SPLIT, MATCHED BY CHANNEL LPL FINANCIAL LLC - BANK FI FI 3'),
 chk('firm 2, product mapped', (SELECT product || ' ' || old_channel_s1 FROM r WHERE part = 'CROSSWALK' AND sales_firm = 'Alpha Inc' AND raw_channel = 'BD'), 'VARIABLE WH'),
 chk('held old, not new (firm 2: the cell moves from R2 to R1)', (SELECT CAST(sales_in_held_cells_old AS INTEGER) || ' ' || CAST(sales_in_held_cells_new AS INTEGER) || ' ' || firm_basis FROM r WHERE part = 'CROSSWALK' AND sales_firm = 'Alpha Inc' AND raw_channel = 'REGIONAL'), '2 0 ONE FIRM'),
 chk('no ZIP', (SELECT CAST(SUM(sales_no_zip) AS INTEGER) FROM r WHERE part = 'CROSSWALK' AND source = 'S1'), 8),
 chk('held old', (SELECT CAST(sales_in_held_cells_old AS INTEGER) FROM r WHERE part = 'CROSSWALK' AND sales_firm = 'ALPHA BD' AND raw_channel = 'IFA'), 10),
 chk('checks: 8 rows, all 0', (SELECT COUNT(*) || ' ' || CAST(SUM(ABS(check_value)) AS INTEGER) FROM r WHERE part = 'CHECKS'), '8 0'),
 chk('map: one row per sales-table key', (SELECT string_agg(source || '=' || n || '/' || k, ' ' ORDER BY source) FROM (SELECT source, COUNT(*) AS n, COUNT(DISTINCT COALESCE(sales_firm_id, '-') || '|' || COALESCE(sales_firm, '-') || '|' || COALESCE(raw_channel, '-') || '|' || COALESCE(raw_product, '-')) AS k FROM ssdb_integration.lr_strategy.tmp_sales_map GROUP BY ALL) z), 'S1=12/12 S2=11/11'),
 chk('map: the documented firm 1 join reproduces every 2025 sale', (SELECT CAST(SUM(b.actual_agent_dollars) AS INTEGER) || ' ' || COUNT(*) FROM ssdb_integration.lr_strategy.s1_sales_t b JOIN ssdb_integration.lr_strategy.tmp_sales_map m ON m.source = 'S1' AND EQUAL_NULL(m.sales_firm_id, NULLIF(CAST(CAST(b.consol_brkr_dlr_id AS DECIMAL(38, 0)) AS VARCHAR), '0')) AND EQUAL_NULL(m.sales_firm, b.consol_broker_nm) AND EQUAL_NULL(m.raw_channel, b.dist_ch) AND EQUAL_NULL(m.raw_product, b.product_line2) WHERE b.fiscal_yr = 2025 AND b.product_bucket = 'ALL'), '63 13'),
 chk('map: the firm 2 join reproduces every 2025 sale', (SELECT CAST(SUM(b.sales_amount) AS INTEGER) || ' ' || COUNT(*) FROM ssdb_integration.lr_strategy.s2_sales_t b JOIN ssdb_integration.lr_strategy.tmp_sales_map m ON m.source = 'S2' AND EQUAL_NULL(m.sales_firm_id, CAST(CAST(b.firm_crd AS DECIMAL(38, 0)) AS VARCHAR)) AND EQUAL_NULL(m.sales_firm, b.firm) AND EQUAL_NULL(m.raw_channel, b.channel) AND EQUAL_NULL(m.raw_product, b.product) WHERE b.year = 2025), '26 11'),
 chk('map: a split resolved', (SELECT firm_basis || ' ' || broker_name || ' ' || new_channel FROM ssdb_integration.lr_strategy.tmp_sales_map WHERE source = 'S1' AND sales_firm = 'LPL' AND raw_channel = 'FI'), 'SPLIT, MATCHED BY CHANNEL LPL FINANCIAL LLC - BANK FI'),
 chk('no renamed duplicate column', (SELECT COUNT(*) FROM duckdb_columns() WHERE table_name IN ('r', 'tmp_xw', 'tmp_xw_checks', 'tmp_xw_cand') AND regexp_matches(column_name, '_[0-9]+$')), 0);
SELECT 'sales_crosswalk_test: ok';
SQL
} | duckdb -bail -noheader -list
