#!/bin/sh
# Runs sheet_slots.sql in DuckDB on a made-up sheet, territories table and holder key and checks its one result against
# answers worked out by hand: a one-name cell matching holders of both firms (both keys), an "or" cell with a comma name, a
# 3-name cell cut on "/" (a holder whose key table has no row: NO KEY, a new name: NEW1), a lower case "or", the same new name
# on two rows in two spellings (NEW1 each time, a second new name NEW2 in the cell's order), open seats (no name, blank,
# tab) as (open) with 0 names, a full state name kept, a two-letter code kept, a blank state and a blank channel, and the
# holder section (channels and WH and FI ZIPs per key, a holder not on the sheet and one with no key left out).
# Masking canary: a name typed as a CHANNEL (Jane Doe) and as a STATE (John Roe) shows as OTHER, and no sheet name, no
# territory name and no comment appears anywhere in the result.
# Prints "sheet_slots_test: ok" or stops at the failed check.  Run from anywhere: sh sheet_slots_test.sh
set -e
here=$(cd "$(dirname "$0")" && pwd)
{
cat <<'SQL'
ATTACH ':memory:' AS ssdb_integration; CREATE SCHEMA ssdb_integration.lr_strategy;
CREATE MACRO UUID_STRING(ns, nm) AS md5(ns || nm);
CREATE TABLE ssdb_integration.lr_strategy.terr_t (source TEXT, name TEXT, zip_code TEXT, state TEXT, channel TEXT,
  clean_name TEXT, clean_id TEXT);
INSERT INTO ssdb_integration.lr_strategy.terr_t (source, name, zip_code, state, channel, clean_name) VALUES
  ('CRBG','Lee, Ann','2134','MA','WH',NULL), ('CRBG','Lee, Ann','02135','MA','WH',NULL), ('CRBG','Lee, Ann','02136','MA','FI',NULL),
  ('EQH','Ann Lee','02134','MA','WH',NULL), ('CRBG','Orr, Abe','03031','NH','FI',NULL), ('CRBG','Orr, Abe','03032','NH','IFA',NULL),
  ('EQH','Bo  Ray','06001','CT','WH',NULL), ('CRBG','Kim, Dot','02134','MA','IFA',NULL), ('EQH','Cy Day','02134','MA','WH',NULL),
  ('EQH','Zed Zo','43001','OH','IFA',NULL), ('EQH','Open','02139','MA','FI',NULL);
-- the holder key (02 owns it): R1 CRBG Lee, Ann; R2 EQH Ann Lee; R3 CRBG Orr, Abe; R4 EQH Bo Ray; R5 EQH Zed Zo; R6 EQH Cy Day;
-- Kim, Dot has no row
CREATE TABLE ssdb_integration.lr_strategy.hk_t (source TEXT, holder_id TEXT, holder_n INTEGER, first_seen TIMESTAMP);
INSERT INTO ssdb_integration.lr_strategy.hk_t SELECT source, UUID_STRING('6ba7b810-9dad-11d1-80b4-00c04fd430c8', nm), n, now()
FROM (VALUES ('CRBG','LEE, ANN',1), ('EQH','ANN LEE',2), ('CRBG','ORR, ABE',3), ('EQH','BO RAY',4), ('EQH','ZED ZO',5),
             ('EQH','CY DAY',6)) v(source, nm, n);
CREATE TABLE ssdb_integration.lr_strategy.sheet_t (name TEXT, state TEXT, comment TEXT, channel TEXT);
INSERT INTO ssdb_integration.lr_strategy.sheet_t VALUES
  ('Ann Lee','Massachusetts','secret comment','NATIONAL'), ('Orr, Abe or Bo Ray',' New  Hampshire',NULL,'regional'),
  ('Bo Ray / Dot Kim/New Hire','MA',NULL,'WH'), ('New Hire','John Roe','secret','Jane Doe'),
  (NULL,'Utah',NULL,'WH'), ('  ','Utah',NULL,'WH'), (chr(9),'Utah',NULL,'NATIONAL'), ('Pat New or new  hire','Utah',NULL,'FI'),
  ('Cy Day OR Ann Lee','Utah',NULL,NULL), ('Bo Ray',NULL,NULL,'WIFI');
SQL
# DuckDB has no LISTAGG ... WITHIN GROUP: string_agg with ORDER BY.  SPLIT_TO_TABLE: unnest of string_split.
sed -e "s/LISTAGG(\(DISTINCT \)\{0,1\}\([a-z]*\), '\([ a-z]*\)') WITHIN GROUP (ORDER BY \([a-z, ]*\))/string_agg(\1\2, '\3' ORDER BY \4)/" \
    -e "s/\\\\\\\\s+', ' ')/\\\\s+', ' ', 'g')/g" -e "s/\\\\\\\\s/\\\\s/g" -e "s/', '|')/', '|', 'g')/" \
    -e "s/LATERAL SPLIT_TO_TABLE(\\(x\\.[a-z_]*\\), '|') p/LATERAL (SELECT unnest(string_split(\\1, '|')) AS value, generate_subscripts(string_split(\\1, '|'), 1) AS index) p/" \
    -e '/^use /d' -e '/^SET /d' \
    -e 's/ FROM VALUES$/ FROM (VALUES/' -e "s/('WYOMING', 'WY')),/('WYOMING', 'WY')) v(column1, column2)),/" \
    -e 's/IDENTIFIER(\$sheet_tbl)/ssdb_integration.lr_strategy.sheet_t/' \
    -e 's/IDENTIFIER(\$holder_tbl)/ssdb_integration.lr_strategy.hk_t/' \
    -e 's/IDENTIFIER(\$terr_tbl)/ssdb_integration.lr_strategy.terr_t/' \
    -e 's/^WITH$/CREATE TABLE res AS WITH/' "$here/sheet_slots.sql"
cat <<'SQL'
CREATE MACRO chk(name, got, want) AS CASE WHEN got IS NOT DISTINCT FROM want THEN 'ok'
  ELSE error(name || ': got ' || COALESCE(CAST(got AS VARCHAR), 'NULL') || ', want ' || CAST(want AS VARCHAR)) END;
SELECT chk('the result',
  (SELECT string_agg(concat_ws('|', section, COALESCE(state, '-'), COALESCE(channel, '-'), COALESCE(CAST(n_names AS VARCHAR), '-'),
                               COALESCE(candidates, '-'), COALESCE(holder, '-'), COALESCE(current_channels, '-'),
                               COALESCE(CAST(zips_wh AS VARCHAR), '-'), COALESCE(CAST(zips_fi AS VARCHAR), '-')), ' / ' ORDER BY rowid) FROM res),
  'SLOT|(blank)|WIFI|1|EQH:R4|-|-|-|-'
  || ' / SLOT|MA|WH|3|EQH:R4 or NO KEY or NEW1|-|-|-|-'
  || ' / SLOT|MASSACHUSETTS|NATIONAL|1|CRBG:R1 or EQH:R2|-|-|-|-'
  || ' / SLOT|NEW HAMPSHIRE|REGIONAL|2|CRBG:R3 or EQH:R4|-|-|-|-'
  || ' / SLOT|OTHER|OTHER|1|NEW1|-|-|-|-'
  || ' / SLOT|UTAH|(blank)|2|EQH:R6 or CRBG:R1 or EQH:R2|-|-|-|-'
  || ' / SLOT|UTAH|FI|2|NEW2 or NEW1|-|-|-|-'
  || ' / SLOT|UTAH|NATIONAL|0|(open)|-|-|-|-'
  || ' / SLOT|UTAH|WH|0|(open)|-|-|-|-'
  || ' / SLOT|UTAH|WH|0|(open)|-|-|-|-'
  || ' / HOLDER|-|-|-|-|CRBG:R1|FI WH|2|1'
  || ' / HOLDER|-|-|-|-|CRBG:R3|FI IFA|0|1'
  || ' / HOLDER|-|-|-|-|EQH:R2|WH|1|0'
  || ' / HOLDER|-|-|-|-|EQH:R4|WH|1|0'
  || ' / HOLDER|-|-|-|-|EQH:R6|WH|1|0'),
 chk('masking canary: no name, comment or typed text in the result',
  (SELECT COUNT(*) FROM res WHERE regexp_matches(lower(concat_ws(' ', section, state, channel, candidates, holder, current_channels)),
      'lee|ann|orr|abe|ray|bo |kim|dot|new hire|new  hire|pat|cy |day|zed|zo|jane|doe|john|roe|secret|comment')), 0);
SELECT 'sheet_slots_test: ok';
SQL
} | duckdb -bail -noheader -list
