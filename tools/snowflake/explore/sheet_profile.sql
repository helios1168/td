use role rl_ssdb_Integration_Lr_Strategy_Rw;
use database ssdb_Integration;
use schema lr_strategy;
--The owner's preliminary assignments sheet (NAME, STATE, COMMENT, CHANNEL, all VARCHAR), profiled before it feeds 03.
--Read only, one result, no names and no comment text: counts, and the CHANNEL and STATE values.
--The sheet has no firm column, so a name is matched to the territory holders of either firm on one key: a name with a
--comma is flipped ("Lee, Ann" to "Ann Lee"), then upper case, single spaces.  CRBG writes "Last, First", EQH "First Last".
--Sections:
--  ROWS       rows, names, names on 2+ rows, blanks, comments, names written with a comma
--  CHANNEL    each CHANNEL value: rows and names
--  STATE      each STATE value that no territory row has as its STATE: rows and names
--  MATCH      the sheet's names by the firms that have a holder with that key (CRBG, EQH, CRBG EQH, or NO HOLDER)
--  NOT IN SHEET   per firm, the WH or FI holders whose key is not in the sheet
--Set sheet_tbl to the uploaded table.
SET sheet_tbl = 'ssdb_integration.lr_strategy.REPLACE_WITH_THE_SHEET_TABLE';
SET terr_tbl  = 'ssdb_integration.lr_strategy.territories_tableau';
WITH
s AS (SELECT NULLIF(UPPER(TRIM(REGEXP_REPLACE(CASE WHEN POSITION(',' IN name) > 0
                                                  THEN SPLIT_PART(name, ',', 2) || ' ' || SPLIT_PART(name, ',', 1)
                                                  ELSE name END, '\\s+', ' '))), '') AS k,
             CASE WHEN POSITION(',' IN COALESCE(name, '')) > 0 THEN 1 ELSE 0 END AS comma,
             NULLIF(UPPER(TRIM(state)), '') AS st, NULLIF(UPPER(TRIM(channel)), '') AS ch,
             CASE WHEN NULLIF(TRIM(comment), '') IS NULL THEN 0 ELSE 1 END AS cm
      FROM IDENTIFIER($sheet_tbl)),
t AS (SELECT UPPER(TRIM(source)) AS src, UPPER(TRIM(channel)) AS ch, UPPER(TRIM(state)) AS st,
             NULLIF(UPPER(TRIM(REGEXP_REPLACE(CASE WHEN POSITION(',' IN nm) > 0
                                                   THEN SPLIT_PART(nm, ',', 2) || ' ' || SPLIT_PART(nm, ',', 1)
                                                   ELSE nm END, '\\s+', ' '))), '') AS k
      FROM (SELECT source, channel, state, COALESCE(NULLIF(TRIM(clean_name), ''), name) AS nm FROM IDENTIFIER($terr_tbl))),
h AS (SELECT DISTINCT src, k, CASE WHEN ch IN ('WH', 'FI') THEN 1 ELSE 0 END AS whfi
      FROM t WHERE k IS NOT NULL AND k <> 'OPEN' AND src IS NOT NULL),
m AS (SELECT sk.k, COALESCE(LISTAGG(DISTINCT h.src, ' ') WITHIN GROUP (ORDER BY h.src), '') AS srcs
      FROM (SELECT DISTINCT k FROM s WHERE k IS NOT NULL) sk LEFT JOIN h ON h.k = sk.k GROUP BY sk.k),
r AS (
  SELECT 1 AS o, 'ROWS' AS section, 'rows' AS item, COUNT(*) AS n_rows, COUNT(DISTINCT k) AS n_names FROM s
  UNION ALL SELECT 1, 'ROWS', 'names on 2+ rows', NULL, COUNT(*) FROM (SELECT k FROM s WHERE k IS NOT NULL GROUP BY k HAVING COUNT(*) > 1)
  UNION ALL SELECT 1, 'ROWS', 'blank name', SUM(CASE WHEN k IS NULL THEN 1 ELSE 0 END), NULL FROM s
  UNION ALL SELECT 1, 'ROWS', 'blank state', SUM(CASE WHEN st IS NULL THEN 1 ELSE 0 END), COUNT(DISTINCT CASE WHEN st IS NULL THEN k END) FROM s
  UNION ALL SELECT 1, 'ROWS', 'blank channel', SUM(CASE WHEN ch IS NULL THEN 1 ELSE 0 END), COUNT(DISTINCT CASE WHEN ch IS NULL THEN k END) FROM s
  UNION ALL SELECT 1, 'ROWS', 'with a comment', SUM(cm), COUNT(DISTINCT CASE WHEN cm = 1 THEN k END) FROM s
  UNION ALL SELECT 1, 'ROWS', 'name written with a comma', SUM(comma), COUNT(DISTINCT CASE WHEN comma = 1 THEN k END) FROM s
  UNION ALL SELECT 2, 'CHANNEL', COALESCE(ch, '(blank)'), COUNT(*), COUNT(DISTINCT k) FROM s GROUP BY ch
  UNION ALL SELECT 3, 'STATE', st, COUNT(*), COUNT(DISTINCT k) FROM s
            WHERE st IS NOT NULL AND st NOT IN (SELECT st FROM t WHERE st IS NOT NULL) GROUP BY st
  UNION ALL SELECT 4, 'MATCH', CASE WHEN m.srcs = '' THEN 'NO HOLDER' ELSE m.srcs END, COUNT(*), COUNT(DISTINCT s.k)
            FROM s JOIN m ON m.k = s.k GROUP BY m.srcs
  UNION ALL SELECT 5, 'NOT IN SHEET', src, NULL, COUNT(DISTINCT k) FROM h
            WHERE whfi = 1 AND k NOT IN (SELECT k FROM s WHERE k IS NOT NULL) GROUP BY src)
SELECT section, item, n_rows, n_names FROM r ORDER BY o, item;
