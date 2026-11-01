#!/bin/sh
# Runs all of 01_opportunity_sales.sql in DuckDB on 02_sales_test.sh's made-up tables (its fixture block) plus the
# rows below, and checks its UNMAPPED layer, statements 15-16 (answers worked out by hand).
# Prints "sales_unmapped_test: ok" or stops at the first failed check.  Run from anywhere: sh sales_unmapped_test.sh
set -e
here=$(cd "$(dirname "$0")" && pwd)
{
awk '/^cat <<.SQL.$/ && !s {s=1; next} s && /^SQL$/ {exit} s' "$here/02_sales_test.sh"
cat <<'SQL'
-- this test's rows: company 91 named like a market metrics firm and in MM_MAP on it (two leads agree); company 92 whose
-- name and MM_MAP point to different firms; a second LPL IFA sale on code M3 at a ZIP where the other IFA name has
-- opportunity (M3's sales then match two names by ZIP); code M12 sold at a ZIP where both IFA names have opportunity;
-- M4 and M3 sold there too: M4's other sale matched one name by ZIP (the MGA code rule takes it), M3's two
-- and the plain LPL name with FIXED opportunity at 10001: another product, so not a candidate for an INDEX sale there
INSERT INTO life_prod.lif_murkylake.wc_market_metrics_opportunity VALUES
  ('2025','Q1','0',NULL,'200','LPL Financial LLC','IFA','01','FA','-77777','10001',5),
  ('2025','Q1','0',NULL,'200','LPL Financial LLC - INDEPENDENT','IFA','01','IA','-77777','30301',5),
  ('2025','Q1','0',NULL,'200','LPL Financial LLC','IFA','01','IA','-77777','30301',5);
INSERT INTO ssdb_integration.lr_strategy.s1_sales_t VALUES
  (2025,1,1,'INDEX','IFA','LPL',8,'P','','30301','GA','W6','N6','ALL',1,1,1,'M12'),
  (2025,2,2,'INDEX','IFA','LPL',8,'P','','30301','GA','W6','N6','ALL',1,1,1,'M4'),
  (2025,3,3,'INDEX','IFA','LPL',8,'P','','30301','GA','W6','N6','ALL',1,1,1,'M3'),
  (2025,6,6,'INDEX','WH','Delta',91,'P','','10001','NY','W3','N3','ALL',1,1,1,'M10'),
  (2025,3,3,'INDEX','IFA','Echo',92,'P','','02134','MA','W1','N1','ALL',1,1,1,'M11'),
  (2025,2,2,'INDEX','IFA','LPL',8,'P','','02134','MA','W1','N1','ALL',1,1,1,'M3');
INSERT INTO ssdb_integration.lr_strategy.mm_map VALUES ('WH',91,11,NULL,'Delta',400), ('IFA',92,1,NULL,'Echo',100);
SQL
sed -e '/^use /d' -e '/^SET s[12]_/d' -e 's/TEMPORARY TABLE/TABLE/' \
    -e 's/IDENTIFIER(\$s1_territories)/ssdb_integration.lr_strategy.s1_terr_t/g' \
    -e 's/IDENTIFIER(\$s2_opp)/ssdb_integration.lr_strategy.s2_opp_t/g' \
    -e 's/IDENTIFIER(\$s2_territories)/ssdb_integration.lr_strategy.s2_terr_t/g' \
    -e 's/IDENTIFIER(\$s1_sales)/ssdb_integration.lr_strategy.s1_sales_t/g' \
    -e 's/IDENTIFIER(\$s2_sales)/ssdb_integration.lr_strategy.s2_sales_t/g' \
    -e "s/^SELECT 'UNMAPPED' AS layer,/CREATE TABLE full_result AS SELECT 'UNMAPPED' AS layer,/" \
    "$here/01_opportunity_sales.sql"
cat <<'SQL'
CREATE MACRO chk(name, got, want) AS CASE WHEN got IS NOT DISTINCT FROM want THEN 'ok'
  ELSE error(name || ': got ' || COALESCE(CAST(got AS VARCHAR), 'NULL') || ', want ' || CAST(want AS VARCHAR)) END;
CREATE MACRO dt(c, m) AS (SELECT leads || ' ' || COALESCE(lead_sources, '-') || ' ' || COALESCE(lead_firm, '-') || ' | '
  || mm_map_lead || ' ' || COALESCE(mm_map_firm, '-') || ' | ' || crd_to_cbd_lead || ' | ' || name_lead || ' '
  || COALESCE(name_firm, '-') || ' | ' || n_zip_firms || ' ' || COALESCE(zip_firm, '-') || ' ' || CAST(amt_zip AS INTEGER)
  || ' | ' || CAST(amt AS INTEGER)
  FROM full_result WHERE layer = 'UNMAPPED' AND part = 'DETAIL' AND company_id IS NOT DISTINCT FROM c
  AND mga_agent_cd IS NOT DISTINCT FROM m);
SELECT
 chk('mga code rule: a split no ZIP settles takes the name its code''s other sales matched by ZIP', (SELECT firm_basis || ' ' || broker_name FROM ssdb_integration.lr_strategy.tmp_o2_sales WHERE sales_firm_id = '8' AND mga_agent_cd = 'M4' AND zip = '30301'), 'SPLIT, MATCHED BY MGA CODE LPL FINANCIAL LLC'),
 chk('mga code rule: not where the code''s sales matched two names', dt('8', 'M3'), 'NONE - - | 2+ CHANNEL MATCHES - | 2+ CHANNEL MATCHES | NO NAME MATCH - | 0 - 0 | 3'),
 chk('zip rule: the code''s other sales, one name each', (SELECT string_agg(zip || ' ' || broker_name, ', ' ORDER BY zip) FROM ssdb_integration.lr_strategy.tmp_o2_sales WHERE sales_firm_id = '8' AND mga_agent_cd = 'M3' AND firm_basis = 'SPLIT, MATCHED BY ZIP'), '02134 LPL FINANCIAL LLC, 10001 LPL FINANCIAL LLC - INDEPENDENT'),
 chk('no firm: map and name agree', dt('91', 'M10'), 'AGREE MM_MAP NAME 400 | DELTA | ONE FIRM 400 | DELTA | NOT IN THE MAP | ONE FIRM 400 | DELTA | 0 - 0 | 6'),
 chk('no firm: map and name differ', dt('92', 'M11'), 'CONFLICT MM_MAP NAME - | ONE FIRM 100 | ALPHA | NOT IN THE MAP | ONE FIRM 500 | ECHO | 0 - 0 | 3'),
 chk('no firm, no lead', dt('77', 'M8'), 'NONE - - | NOT IN THE MAP - | NOT IN THE MAP | NO NAME MATCH - | 0 - 0 | 8'),
 chk('no company, no lead', dt(NULL, NULL), 'NONE - - | NOT IN THE MAP - | NOT IN THE MAP | NO NAME MATCH - | 0 - 0 | 1'),
 chk('new-channel list', (SELECT new_list_label || ' ' || leads FROM full_result WHERE part = 'DETAIL' AND company_id = '438'), 'AFS NONE'),
 chk('detail: every unresolved sale, once', (SELECT COUNT(*) || ' ' || CAST(SUM(amt) AS INTEGER) FROM full_result WHERE layer = 'UNMAPPED' AND part = 'DETAIL'), '7 27'),
 chk('summary', (SELECT string_agg(firm_basis || ' | ' || leads || ' ' || COALESCE(lead_sources, '-') || '=' || CAST(amt AS INTEGER) || '/' || n_groups || '/' || n_companies || '/' || CAST(pct_amt AS INTEGER), ', ' ORDER BY firm_basis, leads) FROM full_result WHERE layer = 'UNMAPPED' AND part = 'SUMMARY'), 'NO COMPANY | NONE -=1/1/0/100, NO MARKET METRICS FIRM | AGREE MM_MAP NAME=6/1/1/27, NO MARKET METRICS FIRM | CONFLICT MM_MAP NAME=3/1/1/14, NO MARKET METRICS FIRM | NONE -=13/2/2/59, SPLIT, 2+ CHANNEL MATCHES | NONE -=4/2/1/100'),
 chk('split: two candidates at the sale''s ZIP, no lead', dt('8', 'M12'), 'NONE - - | 2+ CHANNEL MATCHES - | 2+ CHANNEL MATCHES | NO NAME MATCH - | 0 - 0 | 1'),
 chk('check 0', (SELECT amt FROM full_result WHERE layer = 'UNMAPPED' AND part = 'CHECKS'), 0),
 chk('one result: every layer', (SELECT string_agg(layer || '=' || n, ' ' ORDER BY layer) FROM (SELECT layer, COUNT(*) AS n FROM full_result GROUP BY ALL) x) = 'OPPORTUNITY=' || (SELECT COUNT(*) FROM ssdb_integration.lr_strategy.tmp_o1_out) || ' SALES=' || (SELECT COUNT(*) FROM ssdb_integration.lr_strategy.tmp_o2_out) || ' UNMAPPED=' || (SELECT COUNT(*) FROM ssdb_integration.lr_strategy.tmp_um_out), true),
 chk('one result: the sales checks in it, all 0', (SELECT COUNT(*) || ' ' || CAST(SUM(ABS(amt)) AS INTEGER) FROM full_result WHERE layer = 'SALES' AND part = 'CHECKS'), '8 0');
SELECT 'sales_unmapped_test: ok';
SQL
} | duckdb -bail -noheader -list
