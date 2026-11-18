#!/bin/sh
# Runs sheet_unmatched.sql in DuckDB on a made-up sheet and territories table and checks its one result against answers
# worked out by hand: a matched name left out (whatever its case and spacing, "Last, First" on the holder side), an
# unmatched name beside the holders of both firms with its last name (a vacancy OPEN not one), a name with no candidate
# on one row, a blank name left out, cells with several names (Ann Lee OR Cy Zed / Lee, Ann: the first and third are the matched
# holder, Cy Zed is a candidate for Al Zed; Dee Fox or New Hire: New Hire on two rows, its channels joined) each name on its own.
# Prints "sheet_unmatched_test: ok" or stops at the failed check.  Run from anywhere: sh sheet_unmatched_test.sh
set -e
here=$(cd "$(dirname "$0")" && pwd)
{
cat <<'SQL'
ATTACH ':memory:' AS ssdb_integration; CREATE SCHEMA ssdb_integration.lr_strategy;
CREATE TABLE ssdb_integration.lr_strategy.terr_t (source TEXT, name TEXT, zip_code TEXT, state TEXT, channel TEXT,
  clean_name TEXT, clean_id TEXT);
INSERT INTO ssdb_integration.lr_strategy.terr_t (source, name, state, channel, clean_name) VALUES
  ('CRBG','Lee, Ann','MA','WH',NULL), ('CRBG','Smith, Robert','NH','FI',NULL), ('CRBG','Smith, Robert','NH','WH',NULL),
  ('EQH','Jo Smith','MA','WH',NULL), ('EQH','Open','MA','FI',NULL), ('EQH','Al Zed','MA','FI',NULL);
CREATE TABLE ssdb_integration.lr_strategy.sheet_t (name TEXT, state TEXT, comment TEXT, channel TEXT);
INSERT INTO ssdb_integration.lr_strategy.sheet_t VALUES
  ('ann  LEE','MAINE',NULL,'WH'), ('Bob Smith','OHIO',NULL,'REGIONAL'), ('Bob Smith','IOWA',NULL,'NATIONAL'),
  ('New Hire','IOWA',NULL,'WH'), ('Pat Open','IOWA',NULL,'WH'), ('  ','UTAH',NULL,'WH'), ('TBD','UTAH',NULL,'WH'), ('Ann Lee or tbd','UTAH',NULL,'WH'), ('N/A','IOWA',NULL,'FI'), ('open','IOWA',NULL,'WH'),
  ('Ann Lee OR Cy Zed / Lee, Ann','IOWA',NULL,'FI'), ('Dee Fox or New Hire','UTAH',NULL,'NATIONAL'), ('Ed'||chr(160)||'Fox','UTAH',NULL,'WH'), ('Ty O'||chr(8217)||'Neil','UTAH',NULL,'WH'),
  ('Ann Lee'||chr(160)||'or'||chr(160)||'Dee Fox','OHIO',NULL,'WH'), ('TBD'||chr(160),'OHIO',NULL,'WH');
SQL
sed -e "s/LISTAGG(DISTINCT ch, ' ') WITHIN GROUP (ORDER BY ch)/string_agg(DISTINCT ch, ' ' ORDER BY ch)/g" \
    -e "s/'\\\\\\\\s+', ' ')/'\\\\s+', ' ', 'g')/g" -e "s/\\\\\\\\s/\\\\s/g" -e "s/', '|')/', '|', 'g')/" \
    -e "s/LATERAL SPLIT_TO_TABLE(\\(x\\.[a-z_]*\\), '|') p/LATERAL (SELECT unnest(string_split(\\1, '|')) AS value) p/" \
    -e '/^use /d' -e '/^SET /d' -e 's/REGEXP_LIKE(/regexp_matches(/g' \
    -e "s/REGEXP_SUBSTR(\([a-z.]*\), '\[^ \]+\$')/regexp_extract(\1, '[^ ]+\$')/g" \
    -e 's/IDENTIFIER(\$sheet_tbl)/ssdb_integration.lr_strategy.sheet_t/' \
    -e 's/IDENTIFIER(\$terr_tbl)/ssdb_integration.lr_strategy.terr_t/' \
    -e 's/^CREATE OR REPLACE TEMPORARY TABLE ssdb_integration.lr_strategy.sheet_unmatched AS$/CREATE TABLE res AS/' -e 's/FROM ssdb_integration.lr_strategy.sheet_unmatched ORDER BY row_n/FROM res ORDER BY row_n/' \
    "$here/sheet_unmatched.sql"
cat <<'SQL'
CREATE MACRO chk(name, got, want) AS CASE WHEN got IS NOT DISTINCT FROM want THEN 'ok'
  ELSE error(name || ': got ' || COALESCE(CAST(got AS VARCHAR), 'NULL') || ', want ' || CAST(want AS VARCHAR)) END;
SELECT chk('the result',
  (SELECT string_agg(concat_ws('|', replace(sheet_name, chr(160), '~'), replace(sheet_key, chr(160), '~'), sheet_odd_char, sheet_channels,
                               COALESCE(holder_source, '-'), COALESCE(holder, '-'), COALESCE(holder_key, '-'),
                               COALESCE(CAST(holder_odd_char AS VARCHAR), '-'), COALESCE(holder_channels, '-')), ' / '
          ORDER BY sheet_name, holder_source, holder) FROM res),
  'Bob Smith|BOB SMITH|0|NATIONAL REGIONAL|CRBG|Smith, Robert|ROBERT SMITH|0|FI WH / Bob Smith|BOB SMITH|0|NATIONAL REGIONAL|EQH|Jo Smith|JO SMITH|0|WH'
  || ' / Cy Zed|CY ZED|0|FI|EQH|Al Zed|AL ZED|0|FI / Dee Fox|DEE FOX|0|NATIONAL WH|-|-|-|-|-'
  || ' / Ed Fox|ED FOX|0|WH|-|-|-|-|- / New Hire|NEW HIRE|0|NATIONAL WH|-|-|-|-|- / Pat Open|PAT OPEN|0|WH|-|-|-|-|-'
  || ' / Ty O'||chr(8217)||'Neil|TY O'||chr(8217)||'NEIL|1|WH|-|-|-|-|-');
SELECT 'sheet_unmatched_test: ok';
SQL
} | duckdb -bail -noheader -list
