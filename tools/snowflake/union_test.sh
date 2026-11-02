#!/bin/sh
# Runs all of 01_opportunity_sales.sql in DuckDB on 02_sales_test.sh's made-up tables (its fixture block) plus the rows
# below, and checks the Tableau table (statements 17-18; answers worked out by hand).
# Prints "union_test: ok" or stops at the first failed check.  Run from anywhere: sh union_test.sh
set -e
here=$(cd "$(dirname "$0")" && pwd)
{
awk '/^cat <<.SQL.$/ && !s {s=1; next} s && /^SQL$/ {exit} s' "$here/02_sales_test.sh"
cat <<'SQL'
-- a second firm 1 IFA holder at 02134 (W7, after W1 in ID order); two more Alpha IFA sales there: one with no seller,
-- one by W7, whose sales table spells the name another way
INSERT INTO ssdb_integration.lr_strategy.s1_terr_t VALUES ('W7','N7','02134','MA','IFA');
-- a second territory ID for firm 2's R1 FP at 10001 (one key in TERRITORIES_V2, its lowest ID)
INSERT INTO ssdb_integration.lr_strategy.s2_terr_t VALUES ('R1','T8','10001','NY','FP','x');
INSERT INTO ssdb_integration.lr_strategy.s1_sales_t VALUES
  (2025,3,3,'INDEX','IFA','ALPHA BD',10,'P','','02134','MA',NULL,NULL,'ALL',1,1,1,'M1'),
  (2025,2,2,'INDEX','IFA','ALPHA BD',10,'P','','02134','MA','W7','N7 AS SOLD','ALL',1,1,1,'M1');
SQL
sed -e '/^use /d' -e '/^  -- owner sales channels: begin$/,/^  -- owner sales channels: end$/d' -e '/^  -- owner routes: begin$/,/^  -- owner routes: end$/d' -e '/^  -- owner rows: begin$/,/^  -- owner rows: end$/d' -e '/^SET s[12]_/d' -e 's/TEMPORARY TABLE/TABLE/' \
    -e 's/IDENTIFIER(\$s1_territories)/ssdb_integration.lr_strategy.s1_terr_t/g' \
    -e 's/IDENTIFIER(\$s2_opp)/ssdb_integration.lr_strategy.s2_opp_t/g' \
    -e 's/IDENTIFIER(\$s2_territories)/ssdb_integration.lr_strategy.s2_terr_t/g' \
    -e 's/IDENTIFIER(\$s1_sales)/ssdb_integration.lr_strategy.s1_sales_t/g' \
    -e 's/IDENTIFIER(\$s2_sales)/ssdb_integration.lr_strategy.s2_sales_t/g' \
    -e 's/IDENTIFIER(\$s1_addr)/ssdb_integration.lr_strategy.s1_addr_t/g' -e 's/IDENTIFIER(\$s2_addr)/ssdb_integration.lr_strategy.s2_addr_t/g' -e "s/\$s1_addr/'ssdb_integration.lr_strategy.s1_addr_t'/g" -e "s/\$s2_addr/'ssdb_integration.lr_strategy.s2_addr_t'/g" -e "s/\$s1_source/'SRC1'/g" -e "s/\$s2_source/'SRC2'/g" -e 's/^  LIKE \(.*\);$/  AS SELECT * FROM \1 LIMIT 0;/'  -e 's/ssdb_integration\.information_schema\./information_schema./' \
    -e "s/^SELECT 'REVIEW' AS layer,/CREATE TABLE full_result AS SELECT 'REVIEW' AS layer,/" \
    "$here/01_opportunity_sales.sql"
cat <<'SQL'
CREATE MACRO chk(name, got, want) AS CASE WHEN got IS NOT DISTINCT FROM want THEN 'ok'
  ELSE error(name || ': got ' || COALESCE(CAST(got AS VARCHAR), 'NULL') || ', want ' || CAST(want AS VARCHAR)) END;
CREATE VIEW v AS SELECT * FROM ssdb_integration.lr_strategy.data_withnewchannel_union_w_joinkeys_v2;
CREATE VIEW t AS SELECT * FROM ssdb_integration.lr_strategy.tmp_tb_out;
SELECT
 chk('2+ holders: the cell on a row per holder; sales on one, the holder''s with its cell, no seller under the holder',
     (SELECT string_agg(old_terr_wholesaler || '|' || new_terr_wholesaler || '|' || sales_wholesaler || '|'
                        || CAST(mm_opp AS INTEGER) || '|' || CAST(actual_sales_amount AS INTEGER), ', '
                        ORDER BY old_terr_wholesaler, sales_wholesaler)
      FROM v WHERE source = 'SRC1' AND zip_code = '02134' AND firm = 'ALPHA' AND product_v2 = 'INDEX' AND dist_ch = 'IFA'),
     'N1|N1|N1|100|13, N1|N1|N6|0|5, N7|N7|N7 AS SOLD|100|2'),
 chk('clean names: the territory table''s name for the seller''s key (firm 1 by ID, firm 2 by RVP)',
     (SELECT string_agg(source || '|' || sales_wholesaler || '|' || sales_wholesaler_clean_name || '|' || COALESCE(terr_wholesaler_clean_name, '-'), ', ' ORDER BY source)
      FROM v WHERE (source = 'SRC1' AND sales_wholesaler = 'N7 AS SOLD') OR (source = 'SRC2' AND sales_wholesaler = 'r1 ')),
     'SRC1|N7 AS SOLD|N7|N7, SRC2|r1 |R1|R1'),
 chk('TERR_WHOLESALER_CLEAN_NAME is the new holder on every row', (SELECT COUNT(*) FROM v WHERE terr_wholesaler_clean_name IS DISTINCT FROM new_terr_wholesaler), 0),
 chk('a sale''s old territory is its own channel''s, the new its firm''s',
     (SELECT old_terr_wholesaler || '|' || new_terr_wholesaler || '|' || dist_ch || '|' || CAST(actual_sales_amount AS INTEGER)
      FROM v WHERE source = 'SRC1' AND sales_wholesaler = 'N9'), 'N9|N1|IMO|4'),
 chk('firm 2: holders by RVP, old and new apart',
     (SELECT string_agg(dist_ch || '|' || old_terr_wholesaler || '|' || new_terr_wholesaler || '|' || sales_wholesaler
                        || '|' || CAST(mm_opp AS INTEGER) || '|' || CAST(actual_sales_amount AS INTEGER), ', ' ORDER BY dist_ch)
      FROM v WHERE source = 'SRC2' AND zip_code = '10001' AND firm = 'LPL FINANCIAL LLC - INDEPENDENT'),
     'IFA|R1|R1|R2|0|3, WH|R2|R1|R2|30|0'),
 chk('sizes: opportunity repeated for 2+ holders',
     (SELECT string_agg(source || '=' || CAST(amt AS INTEGER) || '/' || CAST(amt_alt AS INTEGER), ' ' ORDER BY source)
      FROM t WHERE part = 'SIZES' AND name LIKE 'MM_OPP%'), 'SRC1=1020/820 SRC2=130/130'),
 chk('sizes: every sale once',
     (SELECT string_agg(source || '=' || CAST(amt AS INTEGER) || '/' || CAST(amt_alt AS INTEGER), ' ' ORDER BY source)
      FROM t WHERE part = 'SIZES' AND name LIKE 'ACTUAL%'), 'SRC1=68/68 SRC2=24/24'),
 chk('state: one per ZIP, the lowest', (SELECT string_agg(DISTINCT zip_code || '=' || state, ' ' ORDER BY zip_code || '=' || state) FROM v WHERE zip_code IN ('02134', '10001')), '02134=MA 10001=NJ'),
 chk('layout: the live columns and types, TERR_WHOLESALER renamed, NEW_TERR_WHOLESALER last',
     (SELECT COUNT(*) || ' ' || MAX(CASE WHEN column_index = 3 THEN column_name END) || ' '
             || MAX(CASE WHEN column_index = 25 THEN column_name END) || ' '
             || MAX(CASE WHEN column_name = 'fiscal_yr' THEN data_type END) || ' '
             || MAX(CASE WHEN column_name = 'mm_opp' THEN data_type END)
      FROM duckdb_columns() WHERE table_name = 'data_withnewchannel_union_w_joinkeys_v2'),
     '26 old_terr_wholesaler new_terr_wholesaler INTEGER DOUBLE'),
 chk('NEW_TERR_CHANNEL: the new holder''s channel in the territory table''s codes (firm 2 IFA route: FP)',
     (SELECT string_agg(DISTINCT source || '=' || new_terr_channel, ' ' ORDER BY source || '=' || new_terr_channel) FROM v
      WHERE (source = 'SRC1' AND sales_wholesaler = 'N9') OR (source = 'SRC2' AND zip_code = '10001' AND firm = 'LPL FINANCIAL LLC - INDEPENDENT')),
     'SRC1=IFA SRC2=FP'),
 chk('TERRITORIES_V2: rows per source; one row for 2 territory IDs, the lowest, the name as the holder''s',
     (SELECT string_agg(source || '=' || n, ' ' ORDER BY source) FROM (SELECT source, COUNT(*) AS n FROM ssdb_integration.lr_strategy.territories_v2 GROUP BY ALL))
     || ' ' || (SELECT wholesaler || '/' || territory_id || '/' || n_territory_ids FROM ssdb_integration.lr_strategy.territories_v2
                WHERE source = 'SRC2' AND zip_code = '10001' AND terr_channel = 'FP'), 'SRC1=8 SRC2=4 R1/T7/2'),
 chk('TERRITORIES_V2 joins each row with a new holder exactly once',
     (SELECT COUNT(*) FROM v WHERE territory_wholesaler_territory_id IS NOT NULL)
     = (SELECT COUNT(*) FROM v JOIN ssdb_integration.lr_strategy.territories_v2 r ON r.source = v.source
        AND r.wholesaler_key = v.territory_wholesaler_territory_id AND r.zip_code = v.zip_code AND r.terr_channel = v.new_terr_channel), true),
 chk('address columns, no values', (SELECT string_agg(source || ':' || item || '/' || n_rows, ' ' ORDER BY source, n_rows) FROM t WHERE part = 'ADDRESS COLUMNS'),
     'SRC1:whslr_id/1 SRC1:addr_line/2 SRC1:zip/3 SRC2:rvp/1 SRC2:city/2'),
 chk('address rows', (SELECT string_agg(source || '=' || n_rows, ' ' ORDER BY source) FROM t WHERE part = 'ADDRESS ROWS'), 'SRC1=2 SRC2=1'),
 chk('layout: CBD_ID the CRD, FIRM the broker name', (SELECT cbd_id || ' ' || firm FROM v WHERE source = 'SRC1' AND sales_wholesaler = 'N9'), '200 LPL FINANCIAL LLC'),
 chk('comp''d sales in SALES_AMOUNT: firm 1 per row, 0 on its opportunity rows, firm 2 NULL on every row',
     (SELECT (SELECT string_agg(sales_wholesaler || '=' || CAST(sales_amount AS INTEGER), ', ' ORDER BY old_terr_wholesaler, sales_wholesaler)
              FROM v WHERE source = 'SRC1' AND zip_code = '02134' AND firm = 'ALPHA' AND product_v2 = 'INDEX' AND dist_ch = 'IFA')
             || ' | ' || CAST(SUM(CASE WHEN source = 'SRC1' THEN sales_amount END) AS INTEGER)
             || ' ' || COUNT(CASE WHEN source = 'SRC1' AND sales_amount IS NULL THEN 1 END)
             || ' ' || COUNT(CASE WHEN source = 'SRC2' THEN sales_amount END) FROM v),
     'N1=14, N6=6, N7 AS SOLD=2 | 70 0 0'),
 chk('layout: PARENT, address IDs, HAS_TERRITORY flags all NULL',
     (SELECT COUNT(*) FROM v WHERE parent IS NOT NULL OR sales_wholesaler_address_id IS NOT NULL
      OR territory_wholesaler_address_id IS NOT NULL OR sales_wholesaler_has_territory IS NOT NULL
      OR territory_wholesaler_has_territory IS NOT NULL), 0),
 chk('layout: clean names and territory IDs as they are',
     (SELECT terr_wholesaler_clean_name || ' ' || sales_wholesaler_clean_name || ' ' || territory_wholesaler_territory_id
             || ' ' || sales_wholesaler_territory_id FROM v WHERE source = 'SRC1' AND sales_wholesaler = 'N9'), 'N1 N9 W1 W9'),
 chk('a recorded IMO label is the new channel at a market metrics firm (the old table)', (SELECT firm || '|' || new_dist || '|' || channel FROM v WHERE source = 'SRC1' AND sales_wholesaler = 'N9'), 'LPL FINANCIAL LLC|IMO|IMO'),
 chk('channel: uni_latest.sql''s CASE (AFS to pri_afs)', (SELECT CAST(SUM(actual_sales_amount) AS INTEGER) FROM v WHERE channel = 'pri_afs'), 5),
 chk('no filter: UNMAPPED, EDJ kept', (SELECT string_agg(DISTINCT channel, ' ' ORDER BY channel) FROM v WHERE channel IN ('UNMAPPED', 'EDJ')), 'EDJ UNMAPPED'),
 chk('vs live', (SELECT CAST(amt AS INTEGER) || '/' || CAST(amt_alt AS INTEGER) FROM t WHERE part = 'VS LIVE' AND source = 'SRC1' AND name LIKE 'MM_OPP%' AND item = 'IFA' AND item2 = 'INDEX'), '600/500'),
 chk('checks all 0', (SELECT COUNT(*) || ' ' || CAST(SUM(ABS(amt)) AS INTEGER) || ' ' || SUM(n_rows) FROM t WHERE part = 'CHECKS'), '15 0 0');
SELECT 'union_test: ok';
SQL
} | duckdb -bail -noheader -list
