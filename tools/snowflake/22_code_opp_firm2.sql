-- Coded copies of firm_2's own opportunity file, for work outside work, joined to the 2026-10-20 extract
-- by the SAME key: ssdb_integration.lr_strategy.synthetic_opp_original, synthetic_opp_matched and
-- synthetic_crd_cbd.  It answers: can firm_2's opportunity (opp_original, the first-attempt match
-- opp_matched, and the owner's CRD-to-CBD_ID table crd_cbd) be compared with the union outside work?
-- Their rows are the real rows with the coded columns replaced, same columns as their sources
-- (opp_original without CHANNEL: all NULL, dropped).
-- At work opp_original and crd_cbd are views over the real tables, whose names stay out of this repo (owner,
-- 2026-10-25); every file from 22 on uses these two names.
--   ssdb_integration.lr_strategy.opp_original  CHANNEL, DIST_CH, ZIP_CODE, FIRM_CRD, BROKER_NAME,
--                                              PRODUCT_LINE, VA_PRODUCT_TYPE, OPP
--   ssdb_integration.lr_strategy.opp_matched   FIRM_CRD, BROKER_NAME, PRODUCT_LINE, VA_PRODUCT_LINE, OPP,
--                                              CHANNEL_ADJUSTED, PRODUCT_V2, CBD_ID, DIST_CH, ZIP_CODE
--   ssdb_integration.lr_strategy.crd_cbd       FIRM_CRD, CBD_ID
-- The key is the one 20_synthetic_tables.sql built; a value already in it keeps its code, a new value gets
-- the next code, inserted into the key (statement 3).  NEVER re-run statement 1 of 20: RANDOM() numbering
-- would change every code, and the extract of 2026-10-20 would no longer join.  Statements 2-3 can be re-run
-- (they add nothing the second time).
-- Coded:
--   DIST_CH, CHANNEL_ADJUSTED   -> the DIST_CH kind of firm_2 (D2_xx); a new label -> O2_01, ...
--   PRODUCT_LINE, PRODUCT_V2    -> the PRODUCT_V2 kind (PRxx); a new label -> L01, ...
--   VA_PRODUCT_TYPE, VA_PRODUCT_LINE -> a new kind VA_TYPE: V01, ...
--   CBD_ID                      -> the CBD_ID kind (Cxxxxx); a new value -> C after the largest number, random order
--   OPP                         -> / the MM_OPP divisor already in the key (same scale as MM_OPP)
-- New codes within a kind are numbered by rows, largest first, ties by SHA2, after the largest existing number.
-- Clear (owner, 2026-10-24): BROKER_NAME (equivalent to the firm name; the owner chose clear after being told a
-- clear name beside a coded CBD_ID decodes the C and P codes outside work), FIRM_CRD (a public FINRA firm ID,
-- so with the name clear coding it hides nothing), ZIP_CODE.
-- The key never leaves work; it maps results from outside back to real values.
-- Run order: 1 (backup), 2, 3, 4-6, then 7: every MUST_BE_ZERO row of 7 must be 0.  Then 8 and the downloads
-- 9-11: every file sent must be under 800 KB, so the opportunity tables go out in parts.

-- Statement 1.  Backup of the key as it was.  IF NOT EXISTS: a re-run keeps the first backup.
CREATE TABLE IF NOT EXISTS ssdb_integration.lr_strategy.synthetic_key_before_22 AS
SELECT * FROM ssdb_integration.lr_strategy.synthetic_key;

-- Statement 2.  The new key rows only: values of the three files not yet in the key.
CREATE OR REPLACE TABLE ssdb_integration.lr_strategy.synthetic_key_new AS
WITH
k AS (SELECT * FROM ssdb_integration.lr_strategy.synthetic_key),
f2 AS (SELECT VALUE AS SRC FROM k WHERE KIND = 'SOURCE' AND CODE = 'firm_2'),
mx AS (              -- the largest existing number of each prefix
  SELECT COALESCE(MAX(CASE WHEN KIND = 'DIST_CH' AND LEFT(CODE, 3) = 'O2_' THEN TRY_CAST(SUBSTR(CODE, 4) AS INT) END), 0) AS O,
         COALESCE(MAX(CASE WHEN KIND = 'PRODUCT_V2' AND LEFT(CODE, 1) = 'L' THEN TRY_CAST(SUBSTR(CODE, 2) AS INT) END), 0) AS L,
         COALESCE(MAX(CASE WHEN KIND = 'VA_TYPE' THEN TRY_CAST(SUBSTR(CODE, 2) AS INT) END), 0) AS V,
         COALESCE(MAX(CASE WHEN KIND = 'CBD_ID' THEN TRY_CAST(SUBSTR(CODE, 2) AS INT) END), 0) AS C
  FROM k),
dv AS (
  SELECT V, COUNT(*) AS N FROM (
    SELECT CAST(DIST_CH AS VARCHAR) AS V FROM ssdb_integration.lr_strategy.opp_original
    UNION ALL SELECT CAST(DIST_CH AS VARCHAR) FROM ssdb_integration.lr_strategy.opp_matched
    UNION ALL SELECT CAST(CHANNEL_ADJUSTED AS VARCHAR) FROM ssdb_integration.lr_strategy.opp_matched) x
  WHERE V IS NOT NULL GROUP BY V),
pv AS (
  SELECT V, COUNT(*) AS N FROM (
    SELECT CAST(PRODUCT_LINE AS VARCHAR) AS V FROM ssdb_integration.lr_strategy.opp_original
    UNION ALL SELECT CAST(PRODUCT_LINE AS VARCHAR) FROM ssdb_integration.lr_strategy.opp_matched
    UNION ALL SELECT CAST(PRODUCT_V2 AS VARCHAR) FROM ssdb_integration.lr_strategy.opp_matched) x
  WHERE V IS NOT NULL GROUP BY V),
vv AS (
  SELECT V, COUNT(*) AS N FROM (
    SELECT CAST(VA_PRODUCT_TYPE AS VARCHAR) AS V FROM ssdb_integration.lr_strategy.opp_original
    UNION ALL SELECT CAST(VA_PRODUCT_LINE AS VARCHAR) FROM ssdb_integration.lr_strategy.opp_matched) x
  WHERE V IS NOT NULL GROUP BY V),
cv AS (
  SELECT CAST(CBD_ID AS VARCHAR) AS V FROM ssdb_integration.lr_strategy.opp_matched WHERE CBD_ID IS NOT NULL
  UNION SELECT CAST(CBD_ID AS VARCHAR) FROM ssdb_integration.lr_strategy.crd_cbd WHERE CBD_ID IS NOT NULL)
SELECT 'DIST_CH' AS KIND, f2.SRC AS SOURCE, d.V AS VALUE,
       'O2_' || LPAD(CAST(ROW_NUMBER() OVER (ORDER BY d.N DESC, SHA2(d.V)) + mx.O AS VARCHAR), 2, '0') AS CODE,
       CAST(NULL AS DOUBLE) AS NUM
FROM dv d CROSS JOIN f2 CROSS JOIN mx
WHERE NOT EXISTS (SELECT 1 FROM k WHERE k.KIND = 'DIST_CH' AND k.SOURCE = f2.SRC AND k.VALUE = d.V)
UNION ALL
SELECT 'PRODUCT_V2', NULL, p.V,
       'L' || LPAD(CAST(ROW_NUMBER() OVER (ORDER BY p.N DESC, SHA2(p.V)) + mx.L AS VARCHAR), 2, '0'), NULL
FROM pv p CROSS JOIN mx
WHERE NOT EXISTS (SELECT 1 FROM k WHERE k.KIND = 'PRODUCT_V2' AND k.VALUE = p.V)
UNION ALL
SELECT 'VA_TYPE', NULL, v.V,
       'V' || LPAD(CAST(ROW_NUMBER() OVER (ORDER BY v.N DESC, SHA2(v.V)) + mx.V AS VARCHAR), 2, '0'), NULL
FROM vv v CROSS JOIN mx
WHERE NOT EXISTS (SELECT 1 FROM k WHERE k.KIND = 'VA_TYPE' AND k.VALUE = v.V)
UNION ALL
SELECT 'CBD_ID', NULL, c.V,
       'C' || LPAD(CAST(ROW_NUMBER() OVER (ORDER BY RANDOM()) + mx.C AS VARCHAR), 5, '0'), NULL
FROM cv c CROSS JOIN mx
WHERE NOT EXISTS (SELECT 1 FROM k WHERE k.KIND = 'CBD_ID' AND k.VALUE = c.V);

-- Statement 3.  Insert them.  Insert-only: the existing rows are never touched; a row already in the key is skipped.
INSERT INTO ssdb_integration.lr_strategy.synthetic_key
SELECT n.* FROM ssdb_integration.lr_strategy.synthetic_key_new n
WHERE NOT EXISTS (SELECT 1 FROM ssdb_integration.lr_strategy.synthetic_key k
                  WHERE k.KIND = n.KIND AND k.SOURCE IS NOT DISTINCT FROM n.SOURCE AND k.VALUE = n.VALUE);

-- Statement 4.  The synthetic opp_original (no CHANNEL).
CREATE OR REPLACE TABLE ssdb_integration.lr_strategy.synthetic_opp_original AS
WITH
k AS (SELECT * FROM ssdb_integration.lr_strategy.synthetic_key),
f2 AS (SELECT VALUE AS SRC FROM k WHERE KIND = 'SOURCE' AND CODE = 'firm_2'),
dv AS (SELECT NUM AS D_OPP FROM k WHERE KIND = 'divisor' AND VALUE = 'MM_OPP')
SELECT dc.CODE AS DIST_CH,
       o.ZIP_CODE,
       o.FIRM_CRD,
       o.BROKER_NAME,
       pr.CODE AS PRODUCT_LINE,
       va.CODE AS VA_PRODUCT_TYPE,
       ROUND(o.OPP / dv.D_OPP, 3) AS OPP      -- 3 decimals, as the 2026-10-20 export (integers x 1,000)
FROM ssdb_integration.lr_strategy.opp_original o
CROSS JOIN f2 CROSS JOIN dv
LEFT JOIN k dc ON dc.KIND = 'DIST_CH'    AND dc.SOURCE = f2.SRC AND dc.VALUE = CAST(o.DIST_CH AS VARCHAR)
LEFT JOIN k pr ON pr.KIND = 'PRODUCT_V2' AND pr.VALUE = CAST(o.PRODUCT_LINE AS VARCHAR)
LEFT JOIN k va ON va.KIND = 'VA_TYPE'    AND va.VALUE = CAST(o.VA_PRODUCT_TYPE AS VARCHAR);

-- Statement 5.  The synthetic opp_matched.
CREATE OR REPLACE TABLE ssdb_integration.lr_strategy.synthetic_opp_matched AS
WITH
k AS (SELECT * FROM ssdb_integration.lr_strategy.synthetic_key),
f2 AS (SELECT VALUE AS SRC FROM k WHERE KIND = 'SOURCE' AND CODE = 'firm_2'),
dv AS (SELECT NUM AS D_OPP FROM k WHERE KIND = 'divisor' AND VALUE = 'MM_OPP')
SELECT m.FIRM_CRD,
       m.BROKER_NAME,
       pl.CODE AS PRODUCT_LINE,
       va.CODE AS VA_PRODUCT_LINE,
       ROUND(m.OPP / dv.D_OPP, 3) AS OPP,     -- 3 decimals, as the 2026-10-20 export
       ca.CODE AS CHANNEL_ADJUSTED,
       p2.CODE AS PRODUCT_V2,
       cb.CODE AS CBD_ID,
       dc.CODE AS DIST_CH,
       m.ZIP_CODE
FROM ssdb_integration.lr_strategy.opp_matched m
CROSS JOIN f2 CROSS JOIN dv
LEFT JOIN k pl ON pl.KIND = 'PRODUCT_V2' AND pl.VALUE = CAST(m.PRODUCT_LINE AS VARCHAR)
LEFT JOIN k va ON va.KIND = 'VA_TYPE'    AND va.VALUE = CAST(m.VA_PRODUCT_LINE AS VARCHAR)
LEFT JOIN k ca ON ca.KIND = 'DIST_CH'    AND ca.SOURCE = f2.SRC AND ca.VALUE = CAST(m.CHANNEL_ADJUSTED AS VARCHAR)
LEFT JOIN k p2 ON p2.KIND = 'PRODUCT_V2' AND p2.VALUE = CAST(m.PRODUCT_V2 AS VARCHAR)
LEFT JOIN k cb ON cb.KIND = 'CBD_ID'     AND cb.VALUE = CAST(m.CBD_ID AS VARCHAR)
LEFT JOIN k dc ON dc.KIND = 'DIST_CH'    AND dc.SOURCE = f2.SRC AND dc.VALUE = CAST(m.DIST_CH AS VARCHAR);

-- Statement 6.  The synthetic crd_cbd.
CREATE OR REPLACE TABLE ssdb_integration.lr_strategy.synthetic_crd_cbd AS
SELECT c.FIRM_CRD, cb.CODE AS CBD_ID
FROM ssdb_integration.lr_strategy.crd_cbd c
LEFT JOIN ssdb_integration.lr_strategy.synthetic_key cb ON cb.KIND = 'CBD_ID' AND cb.VALUE = CAST(c.CBD_ID AS VARCHAR);

-- Statement 7.  Checks.  Every MUST_BE_ZERO = 1 row must be 0 before anything is downloaded; the 0 rows are for reading.
WITH
k AS (SELECT * FROM ssdb_integration.lr_strategy.synthetic_key),
b AS (SELECT * FROM ssdb_integration.lr_strategy.synthetic_key_before_22),
newk AS (           -- key rows not in the backup; IS NOT DISTINCT FROM is NULL-safe (most rows have SOURCE NULL), and the
                    -- docs do not say how EXCEPT compares NULLs (docs, Set operators, read 2026-10-25)
  SELECT * FROM k
  WHERE NOT EXISTS (SELECT 1 FROM b WHERE b.KIND = k.KIND AND b.SOURCE IS NOT DISTINCT FROM k.SOURCE
                    AND b.VALUE IS NOT DISTINCT FROM k.VALUE)),
d AS (SELECT NUM AS D_OPP FROM k WHERE KIND = 'divisor' AND VALUE = 'MM_OPP'),
real_vals AS (SELECT DISTINCT VALUE FROM k WHERE KIND <> 'divisor'),
coded AS (           -- every coded value in the three synthetic tables (BROKER_NAME, FIRM_CRD, ZIP_CODE stay clear)
  SELECT DIST_CH AS V FROM ssdb_integration.lr_strategy.synthetic_opp_original
  UNION SELECT PRODUCT_LINE FROM ssdb_integration.lr_strategy.synthetic_opp_original
  UNION SELECT VA_PRODUCT_TYPE FROM ssdb_integration.lr_strategy.synthetic_opp_original
  UNION SELECT PRODUCT_LINE FROM ssdb_integration.lr_strategy.synthetic_opp_matched
  UNION SELECT VA_PRODUCT_LINE FROM ssdb_integration.lr_strategy.synthetic_opp_matched
  UNION SELECT CHANNEL_ADJUSTED FROM ssdb_integration.lr_strategy.synthetic_opp_matched
  UNION SELECT PRODUCT_V2 FROM ssdb_integration.lr_strategy.synthetic_opp_matched
  UNION SELECT CBD_ID FROM ssdb_integration.lr_strategy.synthetic_opp_matched
  UNION SELECT DIST_CH FROM ssdb_integration.lr_strategy.synthetic_opp_matched
  UNION SELECT CBD_ID FROM ssdb_integration.lr_strategy.synthetic_crd_cbd)
SELECT 'opp_original rows: real minus synthetic' AS CHECK_NAME,
       (SELECT COUNT(*) FROM ssdb_integration.lr_strategy.opp_original)
     - (SELECT COUNT(*) FROM ssdb_integration.lr_strategy.synthetic_opp_original) AS VALUE, 1 AS MUST_BE_ZERO
UNION ALL SELECT 'opp_matched rows: real minus synthetic',
       (SELECT COUNT(*) FROM ssdb_integration.lr_strategy.opp_matched)
     - (SELECT COUNT(*) FROM ssdb_integration.lr_strategy.synthetic_opp_matched), 1
UNION ALL SELECT 'crd_cbd rows: real minus synthetic',
       (SELECT COUNT(*) FROM ssdb_integration.lr_strategy.crd_cbd)
     - (SELECT COUNT(*) FROM ssdb_integration.lr_strategy.synthetic_crd_cbd), 1
UNION ALL SELECT 'opp_original values with no code (non-NULL in, NULL out)',
       (SELECT COUNT_IF(DIST_CH IS NOT NULL) + COUNT_IF(PRODUCT_LINE IS NOT NULL) + COUNT_IF(VA_PRODUCT_TYPE IS NOT NULL)
        FROM ssdb_integration.lr_strategy.opp_original)
     - (SELECT COUNT_IF(DIST_CH IS NOT NULL) + COUNT_IF(PRODUCT_LINE IS NOT NULL) + COUNT_IF(VA_PRODUCT_TYPE IS NOT NULL)
        FROM ssdb_integration.lr_strategy.synthetic_opp_original), 1
UNION ALL SELECT 'opp_matched values with no code (non-NULL in, NULL out)',
       (SELECT COUNT_IF(PRODUCT_LINE IS NOT NULL) + COUNT_IF(VA_PRODUCT_LINE IS NOT NULL) + COUNT_IF(CHANNEL_ADJUSTED IS NOT NULL)
             + COUNT_IF(PRODUCT_V2 IS NOT NULL) + COUNT_IF(CBD_ID IS NOT NULL) + COUNT_IF(DIST_CH IS NOT NULL)
        FROM ssdb_integration.lr_strategy.opp_matched)
     - (SELECT COUNT_IF(PRODUCT_LINE IS NOT NULL) + COUNT_IF(VA_PRODUCT_LINE IS NOT NULL) + COUNT_IF(CHANNEL_ADJUSTED IS NOT NULL)
             + COUNT_IF(PRODUCT_V2 IS NOT NULL) + COUNT_IF(CBD_ID IS NOT NULL) + COUNT_IF(DIST_CH IS NOT NULL)
        FROM ssdb_integration.lr_strategy.synthetic_opp_matched), 1
UNION ALL SELECT 'crd_cbd values with no code (non-NULL in, NULL out)',
       (SELECT COUNT_IF(CBD_ID IS NOT NULL) FROM ssdb_integration.lr_strategy.crd_cbd)
     - (SELECT COUNT_IF(CBD_ID IS NOT NULL) FROM ssdb_integration.lr_strategy.synthetic_crd_cbd), 1
UNION ALL SELECT 'opp_original CHANNEL non-NULL rows (dropped column)',
       (SELECT COUNT_IF(CHANNEL IS NOT NULL) FROM ssdb_integration.lr_strategy.opp_original), 1
UNION ALL SELECT 'key (KIND, SOURCE, VALUE) twice',
       (SELECT COUNT(*) FROM (SELECT KIND, SOURCE, VALUE FROM k GROUP BY KIND, SOURCE, VALUE HAVING COUNT(*) > 1) x), 1
UNION ALL SELECT 'key (KIND, SOURCE, CODE) twice',
       (SELECT COUNT(*) FROM (SELECT KIND, SOURCE, CODE FROM k WHERE KIND <> 'divisor'
                              GROUP BY KIND, SOURCE, CODE HAVING COUNT(*) > 1) x), 1
UNION ALL SELECT 'synthetic_key_before_22 rows missing from synthetic_key',
       (SELECT COUNT(*) FROM b WHERE NOT EXISTS (SELECT 1 FROM k WHERE k.KIND = b.KIND
          AND k.SOURCE IS NOT DISTINCT FROM b.SOURCE AND k.VALUE IS NOT DISTINCT FROM b.VALUE
          AND k.CODE IS NOT DISTINCT FROM b.CODE AND k.NUM IS NOT DISTINCT FROM b.NUM)), 1
UNION ALL SELECT 'real key values left in coded output columns',
       (SELECT COUNT(*) FROM coded c JOIN real_vals r ON r.VALUE = c.V), 1
UNION ALL SELECT 'new CBD_ID values equal to an old one after TRIM and leading zeros (format mismatch)',
       (SELECT COUNT(*) FROM newk n JOIN b ON b.KIND = 'CBD_ID' AND LTRIM(TRIM(b.VALUE), '0') = LTRIM(TRIM(n.VALUE), '0')
        WHERE n.KIND = 'CBD_ID'), 1
UNION ALL SELECT 'new codes: ' || KIND, COUNT(*), 0 FROM newk GROUP BY KIND
UNION ALL SELECT 'opp_original OPP total: synthetic x divisor / real (should be 1)',
       (SELECT SUM(OPP) FROM ssdb_integration.lr_strategy.synthetic_opp_original) * (SELECT D_OPP FROM d)
     / NULLIF((SELECT SUM(OPP) FROM ssdb_integration.lr_strategy.opp_original), 0), 0
UNION ALL SELECT 'opp_matched OPP total: synthetic x divisor / real (should be 1)',
       (SELECT SUM(OPP) FROM ssdb_integration.lr_strategy.synthetic_opp_matched) * (SELECT D_OPP FROM d)
     / NULLIF((SELECT SUM(OPP) FROM ssdb_integration.lr_strategy.opp_matched), 0), 0
UNION ALL SELECT 'union MM_OPP total in coded units: compare outside work',
       (SELECT SUM(MM_OPP) FROM ssdb_integration.lr_strategy.data_withnewchannel_union_w_joinkeys) / (SELECT D_OPP FROM d), 0
UNION ALL SELECT 'opp_original non-NULL ZIP_CODE not 5 characters',
       (SELECT COUNT_IF(LENGTH(CAST(ZIP_CODE AS VARCHAR)) <> 5) FROM ssdb_integration.lr_strategy.opp_original), 0
UNION ALL SELECT 'opp_matched non-NULL ZIP_CODE not 5 characters',
       (SELECT COUNT_IF(LENGTH(CAST(ZIP_CODE AS VARCHAR)) <> 5) FROM ssdb_integration.lr_strategy.opp_matched), 0
ORDER BY MUST_BE_ZERO DESC, CHECK_NAME;

-- Statement 8.  Rows per part: the parts of each table must add up to its rows; send this grid with the files.
-- N = parts: opp_original 3 (about 965 KB a part on 2026-10-24, so 4 if 800 KB is a hard limit), opp_matched 5 (more
-- columns).  HASH(*) is allowed only in a SELECT list, so the part is computed in a subquery.
SELECT 'synthetic_opp_original' AS TBL, PART, COUNT(*) AS N_ROWS
FROM (SELECT MOD(ABS(HASH(*)), 3) AS PART FROM ssdb_integration.lr_strategy.synthetic_opp_original) GROUP BY PART
UNION ALL
SELECT 'synthetic_opp_matched', PART, COUNT(*)
FROM (SELECT MOD(ABS(HASH(*)), 5) AS PART FROM ssdb_integration.lr_strategy.synthetic_opp_matched) GROUP BY PART
UNION ALL
SELECT 'synthetic_crd_cbd', 0, COUNT(*) FROM ssdb_integration.lr_strategy.synthetic_crd_cbd
ORDER BY TBL, PART;

-- Downloads, one file per run: change only the part number (0 .. N-1) and name the file <table>_<part>.  Download
-- as CSV with header and gzip it, or unload it gzipped to your user stage and check its size with LIST before GET:
--   COPY INTO @~/td_opp/<table>_<part>.csv.gz FROM (<the SELECT>)
--     FILE_FORMAT = (TYPE = CSV COMPRESSION = GZIP FIELD_OPTIONALLY_ENCLOSED_BY = '"') HEADER = TRUE SINGLE = TRUE;
--   LIST @~/td_opp/;
-- (BROKER_NAME can hold commas: keep the quoting.)  A row's part depends only on its values, so the parts never
-- overlap and never miss a row.

-- Statement 9.  synthetic_opp_original, 3 parts: 0, 1, 2.
SELECT * EXCLUDE PART
FROM (SELECT *, MOD(ABS(HASH(*)), 3) AS PART FROM ssdb_integration.lr_strategy.synthetic_opp_original)
WHERE PART = 0;

-- Statement 10.  synthetic_opp_matched, 5 parts: 0, 1, 2, 3, 4.
SELECT * EXCLUDE PART
FROM (SELECT *, MOD(ABS(HASH(*)), 5) AS PART FROM ssdb_integration.lr_strategy.synthetic_opp_matched)
WHERE PART = 0;

-- Statement 11.  synthetic_crd_cbd, one file.
SELECT * FROM ssdb_integration.lr_strategy.synthetic_crd_cbd;
