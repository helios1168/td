use secondary roles all;

--NAME_NORM: every wholesaler name in the listed columns split into one schema, so names from different tables join:
--  LAST_NAME, FIRST_NAME, MIDDLE_NAME, MIDDLE_INITIAL, SUFFIX   the parts, upper case
--  NAME_STD   "LAST, FIRST M SUFFIX"
--  NAME_KEY   LAST|FIRST, letters only (no middle, no suffix): the join key
--  FORMAT     how the raw name was written: 'LAST, FIRST', 'FIRST LAST', 'ONE WORD'
--  REVIEW     why a name needs a look, else NULL
--One row per table x column x SOURCE x raw name; N_ROWS = rows carrying it.
--Handles "Last, First M", "Last, First M Jr.", "Last Jr., First", "Last, M First", "First M Last", "First M Last, Jr.",
--"M First Last", credentials after the name ("First Last, CFP"), nicknames in () or "", periods, accents, extra spaces,
--case, and last names with a particle ("De La Cruz", "Van Dyke").  An initial before a full name is the middle
--initial, the full name the first name.  Not handled, so REVIEW or the checks flag them: a one-word name, a first name
--that is only an initial ("Last, J"), and "Last First" with no comma (it reads as "First Last"; the checks count
--names whose swap is another name's key).  V is never a suffix: in "Last, First V" it is an initial.
--Run All.  Statements 1-3 are temporary, NAME_NORM (4) is kept, 5 = checks (MUST_BE_ZERO rows must be 0),
--6 = the review list: real names, keep at work.
--To add a column (the address table's name column, ...): one more UNION ALL line in statement 2.
--To add a suffix, credential or particle: the lists in statement 3.

--Statement 1.  Made-up names in each format with their expected split.  They go through the same steps as the real
--names, so the first check proves the parsing on Snowflake itself.  Add a line for any new case.
CREATE OR REPLACE TEMPORARY TABLE ssdb_integration.lr_strategy.tmp_name_sample AS
SELECT * FROM (VALUES
  ('Doe, Jane Q',              'DOE',       'JANE',    'Q',      NULL),
  ('DOE, JANE Q.',             'DOE',       'JANE',    'Q',      NULL),
  ('Doe, Jane Quinn',          'DOE',       'JANE',    'QUINN',  NULL),
  ('Doe, Jane Q Jr.',          'DOE',       'JANE',    'Q',      'JR'),
  ('Doe, Jane Q, III',         'DOE',       'JANE',    'Q',      'III'),
  ('Doe Jr., Jane Q',          'DOE',       'JANE',    'Q',      'JR'),
  ('Roe, Richard V',           'ROE',       'RICHARD', 'V',      NULL),
  ('Jane Q. Doe',              'DOE',       'JANE',    'Q',      NULL),
  ('Jane Doe',                 'DOE',       'JANE',    NULL,     NULL),
  ('  jane   q   doe  ',       'DOE',       'JANE',    'Q',      NULL),
  ('Jane Q Doe Jr',            'DOE',       'JANE',    'Q',      'JR'),
  ('Jane Q Doe IV',            'DOE',       'JANE',    'Q',      'IV'),
  ('Jane Doe, CFP',            'DOE',       'JANE',    NULL,     NULL),
  ('Jane Doe II, CFP, ChFC',   'DOE',       'JANE',    NULL,     'II'),
  ('Jane (JJ) Doe',            'DOE',       'JANE',    NULL,     NULL),
  ('Jane "JJ" Doe',            'DOE',       'JANE',    NULL,     NULL),
  ('Jane O Doe',               'DOE',       'JANE',    'O',      NULL),
  ('Jane Q Smith-Roe',         'SMITH-ROE', 'JANE',    'Q',      NULL),
  ('Jane O''Roe',              'O''ROE',    'JANE',    NULL,     NULL),
  ('Jane de la Roe',           'DE LA ROE', 'JANE',    NULL,     NULL),
  ('Jane Q Van Roe',           'VAN ROE',   'JANE',    'Q',      NULL),
  ('De La Roe, Jane',          'DE LA ROE', 'JANE',    NULL,     NULL),
  ('Del Roe',                  'ROE',       'DEL',     NULL,     NULL),
  ('José Doe',                 'DOE',       'JOSE',    NULL,     NULL),
  ('Doe, Q Jane',              'DOE',       'JANE',    'Q',      NULL),
  ('DOE, Q. JANE JR',          'DOE',       'JANE',    'Q',      'JR'),
  ('J. Robert Doe',            'DOE',       'ROBERT',  'J',      NULL),
  ('Doe, J',                   'DOE',       'J',       NULL,     NULL),
  ('Vacant',                   'VACANT',    NULL,      NULL,     NULL)
) v(RAW_NAME, LAST_NAME, FIRST_NAME, MIDDLE_NAME, SUFFIX);

--Statement 2.  The names to normalize: one line per table x column.
CREATE OR REPLACE TEMPORARY TABLE ssdb_integration.lr_strategy.tmp_name_input AS
SELECT SRC_TABLE, SRC_COLUMN, SOURCE, RAW_NAME, COUNT(*) AS N_ROWS
FROM (
  SELECT 'union_base' AS SRC_TABLE, 'TERR_WHOLESALER' AS SRC_COLUMN, SOURCE, TERR_WHOLESALER AS RAW_NAME
  FROM ssdb_integration.lr_strategy.union_base
  UNION ALL SELECT 'union_base', 'SALES_WHOLESALER', SOURCE, SALES_WHOLESALER FROM ssdb_integration.lr_strategy.union_base
  UNION ALL SELECT 'territories', 'NAME', SOURCE, NAME FROM ssdb_integration.lr_strategy.territories
  --UNION ALL SELECT '<address table>', '<name column>', SOURCE, <name column> FROM ssdb_integration.lr_strategy.<address table>
  UNION ALL SELECT 'sample', 'RAW_NAME', NULL, RAW_NAME FROM ssdb_integration.lr_strategy.tmp_name_sample
) x
WHERE RAW_NAME IS NOT NULL
GROUP BY SRC_TABLE, SRC_COLUMN, SOURCE, RAW_NAME;

--Statement 3.  The split.  No backslashes in any pattern: [.] style classes instead, so nothing needs escaping.
CREATE OR REPLACE TEMPORARY TABLE ssdb_integration.lr_strategy.tmp_name_parsed AS
WITH
c AS (   -- accents off, upper case, nicknames in () or "" out, anything but letters ' - and , becomes a space
  SELECT i.*,
         REGEXP_REPLACE(REGEXP_REPLACE(
           UPPER(TRANSLATE(RAW_NAME, 'ÀÁÂÃÄÅÇÈÉÊËÌÍÎÏÑÒÓÔÕÖÙÚÛÜÝàáâãäåçèéêëìíîïñòóôõöùúûüý',
                                     'AAAAAACEEEEIIIINOOOOOUUUUYaaaaaaceeeeiiiinooooouuuuy')),
           '[(][^)]*[)]|"[^"]*"', ' '),
           '[^A-Z,''-]', ' ') AS U
  FROM ssdb_integration.lr_strategy.tmp_name_input i),
t AS (   -- every token (commas too) between its own spaces, so adjacent tokens each match ' TOKEN '
  SELECT c.*, ' ' || REPLACE(REPLACE(U, ',', ' , '), ' ', '  ') || ' ' AS T FROM c),
s AS (   -- the suffix kept; suffixes and credentials taken out
  SELECT t.*,
         REGEXP_SUBSTR(T, ' (JR|SR|II|III|IV) ', 1, 1, 'e', 1) AS SFX,
         REGEXP_REPLACE(T, ' (JR|SR|II|III|IV|CFP|CHFC|CLU|CIMA|CFA|RICP|MBA) ', ' ') AS R0
  FROM t),
r AS (   -- one space between tokens, none around a hyphen or a comma, one comma at most in a row, none at either end
  SELECT s.*,
         TRIM(REGEXP_REPLACE(REGEXP_REPLACE(REGEXP_REPLACE(REGEXP_REPLACE(R0, ' +', ' '), ' ?- ?', '-'), ' ?, ?', ','),
                             ',+', ','), ' ,-') AS R
  FROM s),
f AS (   -- "LAST, FIRST ..." when there is a comma
  SELECT r.*, POSITION(',' IN R) > 0 AS LF, LENGTH(R) - LENGTH(REPLACE(R, ',', '')) AS N_COMMA FROM r),
g AS (
  SELECT f.*,
         CASE WHEN LF THEN TRIM(REPLACE(SUBSTR(R, POSITION(',' IN R) + 1), ',', ' ')) ELSE R END AS GIVEN
  FROM f),
h AS (   -- FIRST = the first given token; REST = what follows it
  SELECT g.*, SPLIT_PART(GIVEN, ' ', 1) AS F1, TRIM(SUBSTR(GIVEN, LENGTH(SPLIT_PART(GIVEN, ' ', 1)) + 1)) AS REST
  FROM g),
l AS (   -- "FIRST ... LAST": LAST = the last token with any particles before it (never the first token)
  SELECT h.*,
         CASE WHEN LF THEN TRIM(SPLIT_PART(R, ',', 1))
              ELSE REGEXP_SUBSTR(REST, '(^| )(((DA|DE|DEL|DELLA|DER|DI|DU|LA|LE|VAN|VON|DEN|ST|SAN|SANTA) )*[^ ]+)$',
                                 1, 1, 'e', 2) END AS L1
  FROM h),
m AS (   -- M0 = the middle names: GIVEN after the first token ("LAST, FIRST ...") or REST before the last name
  SELECT l.*, NULLIF(TRIM(CASE WHEN LF THEN REST ELSE LEFT(REST, LENGTH(REST) - LENGTH(COALESCE(L1, ''))) END), '') AS M0
  FROM l),
x AS (   -- SW: an initial before a full name ("Last, M First", "M First Last"): the full name is the first name
  SELECT m.*, COALESCE(LENGTH(F1) = 1 AND LENGTH(SPLIT_PART(M0, ' ', 1)) > 1, FALSE) AS SW FROM m),
y AS (
  SELECT x.*,
         CASE WHEN SW THEN SPLIT_PART(M0, ' ', 1) ELSE F1 END AS FN,
         CASE WHEN SW THEN TRIM(F1 || ' ' || SUBSTR(M0, LENGTH(SPLIT_PART(M0, ' ', 1)) + 1)) ELSE M0 END AS MN
  FROM x)
SELECT SRC_TABLE, SRC_COLUMN, SOURCE, RAW_NAME, N_ROWS,
       NULLIF(COALESCE(NULLIF(L1, ''), F1), '') AS LAST_NAME,
       CASE WHEN NULLIF(L1, '') IS NOT NULL THEN NULLIF(FN, '') END AS FIRST_NAME,
       MN AS MIDDLE_NAME,
       LEFT(MN, 1) AS MIDDLE_INITIAL,
       SFX AS SUFFIX,
       CASE WHEN R = '' THEN NULL WHEN LF THEN 'LAST, FIRST' WHEN NULLIF(L1, '') IS NULL THEN 'ONE WORD' ELSE 'FIRST LAST' END
         AS FORMAT,
       CASE WHEN R = '' THEN 'no letters'
            WHEN NULLIF(L1, '') IS NULL THEN 'one word'
            WHEN N_COMMA > 1 THEN '2+ commas left after suffixes and credentials'
            WHEN LENGTH(FN) = 1 THEN 'first name is only an initial' END AS REVIEW
FROM y;

--Statement 4.  NAME_NORM, the table kept.
CREATE OR REPLACE TABLE ssdb_integration.lr_strategy.NAME_NORM AS
SELECT SRC_TABLE, SRC_COLUMN, SOURCE, RAW_NAME, N_ROWS, LAST_NAME, FIRST_NAME, MIDDLE_NAME, MIDDLE_INITIAL, SUFFIX,
       LAST_NAME || COALESCE(', ' || FIRST_NAME, '') || COALESCE(' ' || MIDDLE_INITIAL, '') || COALESCE(' ' || SUFFIX, '')
         AS NAME_STD,
       REGEXP_REPLACE(LAST_NAME, '[^A-Z]', '') || '|' || COALESCE(REGEXP_REPLACE(FIRST_NAME, '[^A-Z]', ''), '') AS NAME_KEY,
       FORMAT, REVIEW
FROM ssdb_integration.lr_strategy.tmp_name_parsed
WHERE SRC_TABLE <> 'sample';

--Statement 5.  Checks: every MUST_BE_ZERO = TRUE row must be 0.
WITH
e AS (SELECT * FROM ssdb_integration.lr_strategy.tmp_name_sample),
p AS (SELECT * FROM ssdb_integration.lr_strategy.tmp_name_parsed WHERE SRC_TABLE = 'sample'),
n AS (SELECT * FROM ssdb_integration.lr_strategy.NAME_NORM),
k AS (   -- one column gives a NAME_KEY to 2+ people: their middle initials or suffixes differ
  SELECT SRC_TABLE, SRC_COLUMN, SOURCE, NAME_KEY FROM n
  GROUP BY SRC_TABLE, SRC_COLUMN, SOURCE, NAME_KEY
  HAVING COUNT(DISTINCT MIDDLE_INITIAL) > 1 OR COUNT(DISTINCT SUFFIX) > 1),
w AS (   -- first and last swapped is another name's key in the same SOURCE: maybe "LAST FIRST" with no comma
  SELECT DISTINCT a.SOURCE, a.NAME_KEY FROM n a
  JOIN n b ON b.SOURCE IS NOT DISTINCT FROM a.SOURCE
          AND b.NAME_KEY = REGEXP_REPLACE(a.FIRST_NAME, '[^A-Z]', '') || '|' || REGEXP_REPLACE(a.LAST_NAME, '[^A-Z]', '')
  WHERE a.FIRST_NAME IS NOT NULL AND b.NAME_KEY <> a.NAME_KEY)
SELECT 'sample names split differently from expected (statement 6 lists them)' AS CHECK_NAME,
       (SELECT COUNT(*) FROM e LEFT JOIN p ON p.RAW_NAME = e.RAW_NAME
        WHERE p.RAW_NAME IS NULL OR p.LAST_NAME IS DISTINCT FROM e.LAST_NAME OR p.FIRST_NAME IS DISTINCT FROM e.FIRST_NAME
           OR p.MIDDLE_NAME IS DISTINCT FROM e.MIDDLE_NAME OR p.SUFFIX IS DISTINCT FROM e.SUFFIX) AS VALUE,
       TRUE AS MUST_BE_ZERO
UNION ALL SELECT 'names with no LAST_NAME', (SELECT COUNT(*) FROM n WHERE LAST_NAME IS NULL), FALSE
UNION ALL SELECT 'distinct names, ' || SRC_TABLE || '.' || SRC_COLUMN || ' ' || COALESCE(SOURCE, ''), COUNT(*), FALSE
          FROM n GROUP BY SRC_TABLE, SRC_COLUMN, SOURCE
UNION ALL SELECT 'names by FORMAT: ' || COALESCE(FORMAT, '(none)'), COUNT(*), FALSE FROM n GROUP BY FORMAT
UNION ALL SELECT 'names for review: ' || REVIEW, COUNT(*), FALSE FROM n WHERE REVIEW IS NOT NULL GROUP BY REVIEW
UNION ALL SELECT 'NAME_KEYs one column gives 2+ people (middle initials or suffixes differ)', (SELECT COUNT(*) FROM k), FALSE
UNION ALL SELECT 'NAME_KEYs whose first/last swap is another name''s key, same SOURCE (maybe "LAST FIRST", no comma)',
          (SELECT COUNT(*) FROM w), FALSE
UNION ALL SELECT '% of union_base.' || u.SRC_COLUMN || ' names whose NAME_KEY is in territories (same SOURCE)',
          ROUND(100 * COUNT(t.NAME_KEY) / COUNT(*), 2), FALSE
          FROM (SELECT DISTINCT SRC_COLUMN, SOURCE, NAME_KEY FROM n WHERE SRC_TABLE = 'union_base') u
          LEFT JOIN (SELECT DISTINCT SOURCE, NAME_KEY FROM n WHERE SRC_TABLE = 'territories') t
                 ON t.SOURCE = u.SOURCE AND t.NAME_KEY = u.NAME_KEY
          GROUP BY u.SRC_COLUMN;

--Statement 6.  The review list: real names, keep at work.  Sample names split wrong (EXPECTED = what statement 1
--says), names with a REVIEW, and names in a shared or swapped NAME_KEY.
WITH
e AS (SELECT * FROM ssdb_integration.lr_strategy.tmp_name_sample),
p AS (SELECT * FROM ssdb_integration.lr_strategy.tmp_name_parsed WHERE SRC_TABLE = 'sample'),
n AS (SELECT * FROM ssdb_integration.lr_strategy.NAME_NORM),
k AS (SELECT SRC_TABLE, SRC_COLUMN, SOURCE, NAME_KEY FROM n GROUP BY SRC_TABLE, SRC_COLUMN, SOURCE, NAME_KEY
      HAVING COUNT(DISTINCT MIDDLE_INITIAL) > 1 OR COUNT(DISTINCT SUFFIX) > 1),
w AS (SELECT DISTINCT a.SOURCE, a.NAME_KEY FROM n a
      JOIN n b ON b.SOURCE IS NOT DISTINCT FROM a.SOURCE
              AND b.NAME_KEY = REGEXP_REPLACE(a.FIRST_NAME, '[^A-Z]', '') || '|' || REGEXP_REPLACE(a.LAST_NAME, '[^A-Z]', '')
      WHERE a.FIRST_NAME IS NOT NULL AND b.NAME_KEY <> a.NAME_KEY)
SELECT 'sample split wrong' AS REASON, 'sample' AS SRC_TABLE, 'RAW_NAME' AS SRC_COLUMN, CAST(NULL AS VARCHAR) AS SOURCE,
       e.RAW_NAME, p.LAST_NAME, p.FIRST_NAME, p.MIDDLE_NAME, p.SUFFIX,
       COALESCE(e.LAST_NAME, '-') || ' | ' || COALESCE(e.FIRST_NAME, '-') || ' | ' || COALESCE(e.MIDDLE_NAME, '-') || ' | '
         || COALESCE(e.SUFFIX, '-') AS EXPECTED, CAST(NULL AS VARCHAR) AS NAME_KEY, CAST(NULL AS INTEGER) AS N_ROWS
FROM e LEFT JOIN p ON p.RAW_NAME = e.RAW_NAME
WHERE p.RAW_NAME IS NULL OR p.LAST_NAME IS DISTINCT FROM e.LAST_NAME OR p.FIRST_NAME IS DISTINCT FROM e.FIRST_NAME
   OR p.MIDDLE_NAME IS DISTINCT FROM e.MIDDLE_NAME OR p.SUFFIX IS DISTINCT FROM e.SUFFIX
UNION ALL
SELECT CASE WHEN n.REVIEW IS NOT NULL THEN n.REVIEW
            WHEN k.NAME_KEY IS NOT NULL THEN 'NAME_KEY shared by 2+ people in this column'
            ELSE 'first/last swap is another name''s key' END,
       n.SRC_TABLE, n.SRC_COLUMN, n.SOURCE, n.RAW_NAME, n.LAST_NAME, n.FIRST_NAME, n.MIDDLE_NAME, n.SUFFIX, NULL,
       n.NAME_KEY, n.N_ROWS
FROM n
LEFT JOIN k ON k.SRC_TABLE = n.SRC_TABLE AND k.SRC_COLUMN = n.SRC_COLUMN
           AND k.SOURCE IS NOT DISTINCT FROM n.SOURCE AND k.NAME_KEY = n.NAME_KEY
LEFT JOIN w ON w.SOURCE IS NOT DISTINCT FROM n.SOURCE AND w.NAME_KEY = n.NAME_KEY
WHERE n.REVIEW IS NOT NULL OR k.NAME_KEY IS NOT NULL OR w.NAME_KEY IS NOT NULL
ORDER BY 1, 2, 3, 4, 5;
