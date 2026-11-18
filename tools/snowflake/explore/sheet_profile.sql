use role rl_ssdb_Integration_Lr_Strategy_Rw;
use database ssdb_Integration;
use schema lr_strategy;
--The owner's preliminary assignments sheet (NAME, STATE, COMMENT, CHANNEL, all VARCHAR), profiled before it feeds 03.
--Read only, one result, no names and no comment text: counts, and the CHANNEL and STATE values.
--The sheet has no firm column, so a name is matched to the territory holders of either firm on one key: a name with a
--comma is flipped ("Lee, Ann" to "Ann Lee"), then upper case, single spaces.  CRBG writes "Last, First", EQH "First Last".
--Sections:
--A NAME cell may hold several names (owner, 2026-11-18, "yes option 1"): split on the whole word OR in any case and on a
--slash, as 03_assignments.sql, so a name is one name of a cell.  Counts of rows are sheet rows, counts of names are split names.
--  ROWS       rows, names, names on 2+ rows, blanks, comments, names written with a comma, names with OR or /: the
--             rows whose cell has 2+ names and the names in those cells
--  CHANNEL    NATIONAL, REGIONAL, WH, FI, WIFI, (blank) or OTHER: rows and names
--  STATE      a territory's two-letter code, a full state name, (blank) or OTHER: rows and names
--No sheet text but those labels reaches the result.
--  MATCH      the sheet's split names (a cell A or B is two) by the firms that have a holder with that key (CRBG, EQH, CRBG EQH, or NO HOLDER)
--  NOT IN SHEET   per firm, the WH or FI holders whose key is not in the sheet
--sheet_tbl is the uploaded sheet, channel_contacts.
SET sheet_tbl = 'ssdb_integration.lr_strategy.channel_contacts';
SET terr_tbl  = 'ssdb_integration.lr_strategy.territories_tableau';
WITH
sp AS (SELECT x.rid, x.st, x.ch, x.cm, p.index AS ix,
              NULLIF(NULLIF(NULLIF(NULLIF(UPPER(TRIM(REGEXP_REPLACE(CASE WHEN POSITION(',' IN p.value) > 0
                                                    THEN SPLIT_PART(p.value, ',', 2) || ' ' || SPLIT_PART(p.value, ',', 1)
                                                    ELSE p.value END, '\\s+', ' '))), ''), 'N/A'), 'OPEN'), 'TBD') AS k,
              CASE WHEN POSITION(',' IN p.value) > 0 THEN 1 ELSE 0 END AS comma
       FROM (SELECT ROW_NUMBER() OVER (ORDER BY name, state, channel, comment) AS rid,
                    NULLIF(UPPER(TRIM(state)), '') AS st, NULLIF(UPPER(TRIM(channel)), '') AS ch,
                    CASE WHEN NULLIF(TRIM(comment), '') IS NULL THEN 0 ELSE 1 END AS cm,
                    REGEXP_REPLACE(CASE WHEN UPPER(TRIM(REPLACE(name, CHR(160), ' '))) IN ('N/A', 'OPEN', 'TBD') THEN '' ELSE COALESCE(REPLACE(name, CHR(160), ' '), '') END, '(\\s+[Oo][Rr])?\\s*/\\s*|\\s+[Oo][Rr]\\s+', '|') || '|' AS nm_split
             FROM IDENTIFIER($sheet_tbl)) x,
       LATERAL SPLIT_TO_TABLE(x.nm_split, '|') p),
sn AS (SELECT sp.*, COUNT(k) OVER (PARTITION BY rid) AS n_names FROM sp),
--one row per name, a sheet row with no name once with K blank
s AS (SELECT * FROM sn WHERE k IS NOT NULL OR (n_names = 0 AND ix = 1)),
t AS (SELECT UPPER(TRIM(source)) AS src, UPPER(TRIM(channel)) AS ch, UPPER(TRIM(state)) AS st,
             NULLIF(UPPER(TRIM(REGEXP_REPLACE(CASE WHEN POSITION(',' IN nm) > 0
                                                   THEN SPLIT_PART(nm, ',', 2) || ' ' || SPLIT_PART(nm, ',', 1)
                                                   ELSE nm END, '\\s+', ' '))), '') AS k
      FROM (SELECT source, channel, state, COALESCE(NULLIF(TRIM(clean_name), ''), name) AS nm FROM IDENTIFIER($terr_tbl))),
fs AS (SELECT column1 AS st FROM VALUES
       ('ALABAMA', 'AL'), ('ALASKA', 'AK'), ('ARIZONA', 'AZ'), ('ARKANSAS', 'AR'), ('CALIFORNIA', 'CA'),
       ('COLORADO', 'CO'), ('CONNECTICUT', 'CT'), ('DELAWARE', 'DE'), ('DISTRICT OF COLUMBIA', 'DC'),
       ('FLORIDA', 'FL'), ('GEORGIA', 'GA'), ('HAWAII', 'HI'), ('IDAHO', 'ID'), ('ILLINOIS', 'IL'),
       ('INDIANA', 'IN'), ('IOWA', 'IA'), ('KANSAS', 'KS'), ('KENTUCKY', 'KY'), ('LOUISIANA', 'LA'), ('MAINE', 'ME'),
       ('MARYLAND', 'MD'), ('MASSACHUSETTS', 'MA'), ('MICHIGAN', 'MI'), ('MINNESOTA', 'MN'), ('MISSISSIPPI', 'MS'),
       ('MISSOURI', 'MO'), ('MONTANA', 'MT'), ('NEBRASKA', 'NE'), ('NEVADA', 'NV'), ('NEW HAMPSHIRE', 'NH'),
       ('NEW JERSEY', 'NJ'), ('NEW MEXICO', 'NM'), ('NEW YORK', 'NY'), ('NORTH CAROLINA', 'NC'),
       ('NORTH DAKOTA', 'ND'), ('OHIO', 'OH'), ('OKLAHOMA', 'OK'), ('OREGON', 'OR'), ('PENNSYLVANIA', 'PA'),
       ('RHODE ISLAND', 'RI'), ('SOUTH CAROLINA', 'SC'), ('SOUTH DAKOTA', 'SD'), ('TENNESSEE', 'TN'),
       ('TEXAS', 'TX'), ('UTAH', 'UT'), ('VERMONT', 'VT'), ('VIRGINIA', 'VA'), ('WASHINGTON', 'WA'),
       ('WEST VIRGINIA', 'WV'), ('WISCONSIN', 'WI'), ('WYOMING', 'WY')),
h AS (SELECT DISTINCT src, k, CASE WHEN ch IN ('WH', 'FI') THEN 1 ELSE 0 END AS whfi
      FROM t WHERE k IS NOT NULL AND k <> 'OPEN' AND src IS NOT NULL),
m AS (SELECT sk.k, COALESCE(LISTAGG(DISTINCT h.src, ' ') WITHIN GROUP (ORDER BY h.src), '') AS srcs
      FROM (SELECT DISTINCT k FROM s WHERE k IS NOT NULL) sk LEFT JOIN h ON h.k = sk.k GROUP BY sk.k),
r AS (
  SELECT 1 AS o, 'ROWS' AS section, 'rows' AS item, COUNT(DISTINCT rid) AS n_rows, COUNT(DISTINCT k) AS n_names FROM s
  UNION ALL SELECT 1, 'ROWS', 'names on 2+ rows', NULL, COUNT(*) FROM (SELECT k FROM s WHERE k IS NOT NULL GROUP BY k HAVING COUNT(DISTINCT rid) > 1)
  UNION ALL SELECT 1, 'ROWS', 'names with OR or /', COUNT(DISTINCT CASE WHEN n_names > 1 THEN rid END), COUNT(DISTINCT CASE WHEN n_names > 1 THEN k END) FROM s
  UNION ALL SELECT 1, 'ROWS', 'blank name', COUNT(DISTINCT CASE WHEN k IS NULL THEN rid END), NULL FROM s
  UNION ALL SELECT 1, 'ROWS', 'blank state', COUNT(DISTINCT CASE WHEN st IS NULL THEN rid END), COUNT(DISTINCT CASE WHEN st IS NULL THEN k END) FROM s
  UNION ALL SELECT 1, 'ROWS', 'blank channel', COUNT(DISTINCT CASE WHEN ch IS NULL THEN rid END), COUNT(DISTINCT CASE WHEN ch IS NULL THEN k END) FROM s
  UNION ALL SELECT 1, 'ROWS', 'with a comment', COUNT(DISTINCT CASE WHEN cm = 1 THEN rid END), COUNT(DISTINCT CASE WHEN cm = 1 THEN k END) FROM s
  UNION ALL SELECT 1, 'ROWS', 'name written with a comma', COUNT(DISTINCT CASE WHEN comma = 1 THEN rid END), COUNT(DISTINCT CASE WHEN comma = 1 THEN k END) FROM s
  UNION ALL SELECT 2, 'CHANNEL', l, COUNT(DISTINCT rid), COUNT(DISTINCT k)
            FROM (SELECT rid, k, CASE WHEN ch IS NULL THEN '(blank)' WHEN ch IN ('NATIONAL', 'REGIONAL', 'WH', 'FI', 'WIFI') THEN ch
                                 ELSE 'OTHER' END AS l FROM s) GROUP BY l
  UNION ALL SELECT 3, 'STATE', l, COUNT(DISTINCT rid), COUNT(DISTINCT k)
            FROM (SELECT rid, k, CASE WHEN st IS NULL THEN '(blank)' WHEN st IN (SELECT st FROM t WHERE st IS NOT NULL) THEN 'two-letter code'
                                 WHEN UPPER(REGEXP_REPLACE(st, '\\s+', ' ')) IN (SELECT st FROM fs) THEN 'full state name'
                                 ELSE 'OTHER' END AS l FROM s) GROUP BY l
  UNION ALL SELECT 4, 'MATCH', CASE WHEN m.srcs = '' THEN 'NO HOLDER' ELSE m.srcs END, COUNT(*), COUNT(DISTINCT s.k)
            FROM s JOIN m ON m.k = s.k GROUP BY m.srcs
  UNION ALL SELECT 5, 'NOT IN SHEET', src, NULL, COUNT(DISTINCT k) FROM h
            WHERE whfi = 1 AND k NOT IN (SELECT k FROM s WHERE k IS NOT NULL) GROUP BY src)
SELECT section, item, n_rows, n_names FROM r ORDER BY o, item;
