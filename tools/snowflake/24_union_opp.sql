-- UNION_OPP: the union with firm_2's opportunity in MM_OPP, in firm_1's layout (owner, 2026-10-25: "no it needs
-- to match the layout of firm 1's data. there needs to be a join so that mm_opp and sales exists for firm two on
-- the same rows so we can do analytics ar the wholesaler level").  It reads union_base, the union without firm_2's
-- opportunity (owner, 2026-10-25: the current data_withnewchannel_union_w_joinkeys already carries an earlier load
-- of it, which would be counted twice); union_base itself is never touched.  firm_1 puts MM_OPP on a sales row of its key when the seller is the holder, else on its own row.
-- firm_2's opportunity is opp_f2_final: its file through the opportunity steps of the owner's firm_1 query
-- (mm_query_f2.sql: company, dist_ch and new_dist as firm_1's), without FIXED (out of scope, owner, 2026-10-24, Q22)
-- and NO CHANNEL (owner, 2026-10-25).
-- UNION_OPP = the union's firm_1 rows unchanged + its firm_2 rows (every column unchanged except MM_OPP, and
-- PRODUCT_V2: firm_2's VA counted as VARIABLE, owner, 2026-10-26, Q8) + opp-only rows.
-- Same columns as the union, in its order, plus lineage columns at the end:
--   ROW_ORIGIN    'union' (row as in the source), 'union + opp file' (a firm_2 sales row now carrying MM_OPP),
--                 'opp file' (a new opp-only row)
--   FILE_NEW_DIST the new_dist mm_query_f2.sql gives the opportunity (on a sales row: NULL if its key has 2+; the
--                 sales row keeps its own NEW_DIST)
--   CHANNEL_RULE  'sales row'; on an opp-only row 'firm_1 NEW_DIST': the CHANNEL firm_1's union rows carry for that
--                 NEW_DIST, until the owner's CHANNEL step is in; NULL where they carry none or 2+ (checks fail on it)
--   N_HOLDERS     distinct CLEAN_IDs holding the ZIP_CODE x DIST_CH in territories (0 = the TX/NY block, Q10; 2 = shared)
--   FIRM_KEY      one key per firm across both firms (mm_query_f2.sql statement 7, by CBD_ID; owner, 2026-10-26)
--   FIRM_CRD      (owner, 2026-10-26) opp-only rows: the CRD of firm_2's file (one row per CRD); every other row: the
--                 company's CRD where its CBD_ID has one in the vendor's resolved rows (crd_cbd_mm, opp_f2_final)
--   CRD_RULE      'file', 'company has one CRD', or, FIRM_CRD blank, 'company has 2+ CRDs' (for review) /
--                 'company has no CRD'; NULL where CBD_ID is NULL
-- The key is ZIP_CODE x DIST_CH x CBD_ID x PRODUCT_V2, as firm_1's (CHANNEL is not in it), DIST_CH = firm_2's own
-- channel: the file's (FILE_DIST_CH) through the settled map (owner, 2026-10-25, Q19); MM_OPP = SUM; a key that sums
-- to 0 is left out.  A key goes on exactly one firm_2 union row with that ZIP_CODE, DIST_CH, CBD_ID and PRODUCT_V2
-- whose seller is the holder (SALES_WHOLESALER_TERRITORY_ID = TERRITORY_WHOLESALER_TERRITORY_ID): the one with the
-- largest ACTUAL_SALES_AMOUNT, ties on the other columns.  It takes that row's NEW_DIST and CHANNEL.  A key with
-- no such row becomes opp-only rows, one per the file's new_dist and CRD (NEW_DIST = it): FISCAL_YR, the sales amounts and the address IDs NULL; like firm_1's, TERR_WHOLESALER
-- and SALES_WHOLESALER are NULL, both CLEAN_NAME columns carry the holder's name, both TERRITORY_ID columns the
-- holder's CLEAN_ID, both HAS_TERRITORY flags are 1 (0 with no holder).  A firm_2 union row that gets no key keeps its NULL MM_OPP.
-- 25_union_opp_one.sql builds the same table in one CREATE (generated from this file and mm_query_f2.sql).
-- Run mm_query_f2.sql statements 1-2 and 7 first.  Run statement 1, then 2 (checks: every MUST_BE_ZERO row must be 0), then 3.

-- Statement 1.  The table.
CREATE OR REPLACE TABLE ssdb_integration.lr_strategy.UNION_OPP AS
WITH
k AS (SELECT * FROM ssdb_integration.lr_strategy.synthetic_key),
s1 AS (SELECT VALUE AS V FROM k WHERE KIND = 'SOURCE' AND CODE = 'firm_1'),
s2 AS (SELECT VALUE AS V FROM k WHERE KIND = 'SOURCE' AND CODE = 'firm_2'),
dm AS (              -- the file's channel -> firm_2's union DIST_CH (owner, 2026-10-25, Q19); GONE = NO CHANNEL, dropped
  SELECT a.VALUE AS FILE_DIST_CH, b.VALUE AS DIST_CH, m.GONE
  FROM (VALUES ('O2_01', 'D2_01', FALSE), ('O2_02', 'D2_02', FALSE), ('O2_03', 'D2_04', FALSE),
               ('O2_04', 'D2_03', FALSE), ('O2_05', NULL, TRUE)) m(FILE_CODE, UNION_CODE, GONE)
  CROSS JOIN s2
  JOIN k a ON a.KIND = 'DIST_CH' AND a.SOURCE = s2.V AND a.CODE = m.FILE_CODE
  LEFT JOIN k b ON b.KIND = 'DIST_CH' AND b.SOURCE = s2.V AND b.CODE = m.UNION_CODE),
pv AS (              -- firm_2's VA is VARIABLE (owner, 2026-10-26, Q8)
  SELECT a.VALUE AS VA, b.VALUE AS VARIABLE
  FROM k a JOIN k b ON b.KIND = 'PRODUCT_V2' AND b.CODE = 'PR02'
  WHERE a.KIND = 'PRODUCT_V2' AND a.CODE = 'PR05'),
fo AS (              -- opp_f2_final without its dropped rows; a FILE_DIST_CH in no map is kept, with a NULL DIST_CH (checks fail)
  SELECT f.ZIP_CODE, dm.DIST_CH, TO_CHAR(f.CBD_ID) AS CBD_ID, f.PRODUCT_LINE AS PRODUCT_V2, f.NEW_DIST,
         TO_CHAR(f.FIRM_CRD) AS FIRM_CRD, f.MM_OPP
  FROM ssdb_integration.lr_strategy.opp_f2_final f
  LEFT JOIN dm ON dm.FILE_DIST_CH = f.FILE_DIST_CH
  WHERE dm.GONE IS DISTINCT FROM TRUE
    AND f.PRODUCT_LINE IS DISTINCT FROM 'FIXED'),   -- FIXED: the query's own label for fixed annuity
ak AS (              -- the opportunity keys
  SELECT ZIP_CODE, DIST_CH, CBD_ID, PRODUCT_V2, SUM(MM_OPP) AS MM_OPP,
         CASE WHEN COUNT(DISTINCT COALESCE(NEW_DIST, '~')) = 1 THEN MAX(NEW_DIST) END AS FILE_NEW_DIST
  FROM fo GROUP BY ZIP_CODE, DIST_CH, CBD_ID, PRODUCT_V2
  HAVING COALESCE(SUM(MM_OPP), 0) <> 0),
cc AS (              -- a company's CRDs in the vendor's resolved rows; FIRM_CRD where it has one
  SELECT CBD, MAX(CRD) AS CRD, COUNT(DISTINCT CRD) AS N_CRD
  FROM (SELECT TO_CHAR(cbd_id) AS CBD, TO_CHAR(firm_crd) AS CRD FROM ssdb_integration.lr_strategy.crd_cbd_mm
        UNION SELECT TO_CHAR(CBD_ID), TO_CHAR(FIRM_CRD) FROM ssdb_integration.lr_strategy.opp_f2_final) x
  WHERE CBD IS NOT NULL AND CRD IS NOT NULL
  GROUP BY CBD),
ch1 AS (             -- the CHANNEL firm_1's union rows carry for a NEW_DIST, where they carry one
  SELECT u.NEW_DIST, MAX(u.CHANNEL) AS CHANNEL
  FROM ssdb_integration.lr_strategy.union_base u JOIN s1 ON u.SOURCE = s1.V
  WHERE u.NEW_DIST IS NOT NULL
  GROUP BY u.NEW_DIST HAVING COUNT(DISTINCT COALESCE(u.CHANNEL, '~')) = 1),
fp AS (              -- FIRM and PARENT of a company in each SOURCE
  SELECT u.CBD_ID, u.SOURCE, MAX(u.FIRM) AS FIRM, MAX(u.PARENT) AS PARENT
  FROM ssdb_integration.lr_strategy.union_base u
  WHERE u.CBD_ID IS NOT NULL GROUP BY u.CBD_ID, u.SOURCE),
cn AS (              -- the firm name crd_cbd gives a CBD_ID: FIRM where union_base has none; PARENT stays blank (owner, 2026-10-25)
  SELECT CAST(CBD_ID AS VARCHAR) AS CBD_ID, MAX(FIRM) AS FIRM
  FROM ssdb_integration.lr_strategy.crd_cbd
  WHERE CBD_ID IS NOT NULL AND CAST(CBD_ID AS VARCHAR) <> '0' GROUP BY 1),
h AS (               -- holders of a ZIP_CODE x DIST_CH in territories
  SELECT t.ZIP_CODE, t.CHANNEL AS DIST_CH, MIN(t.CLEAN_ID) AS ID, COUNT(DISTINCT t.CLEAN_ID) AS N,
         MIN_BY(t.CLEAN_NAME, t.CLEAN_ID) AS NAME
  FROM ssdb_integration.lr_strategy.territories t JOIN s2 ON t.SOURCE = s2.V
  WHERE t.CLEAN_ID IS NOT NULL GROUP BY t.ZIP_CODE, t.CHANNEL),
nm AS (              -- the name the union already carries for that ID
  SELECT u.TERRITORY_WHOLESALER_TERRITORY_ID AS ID, MAX(u.TERR_WHOLESALER_CLEAN_NAME) AS NAME
  FROM ssdb_integration.lr_strategy.union_base u JOIN s2 ON u.SOURCE = s2.V
  GROUP BY u.TERRITORY_WHOLESALER_TERRITORY_ID),
st AS (SELECT ZIP_CODE, MAX(STATE) AS STATE FROM ssdb_integration.lr_strategy.territories GROUP BY ZIP_CODE),
us AS (SELECT ZIP_CODE, MAX(STATE) AS STATE FROM ssdb_integration.lr_strategy.union_base GROUP BY ZIP_CODE),
r0 AS (              -- the union with its seller = holder flag; firm_2's VA as VARIABLE (Q8)
  SELECT u.* REPLACE (CASE WHEN u.SOURCE = s2.V AND u.PRODUCT_V2 = pv.VA THEN pv.VARIABLE ELSE u.PRODUCT_V2 END AS PRODUCT_V2),
         COALESCE(u.SALES_WHOLESALER_TERRITORY_ID = u.TERRITORY_WHOLESALER_TERRITORY_ID, FALSE) AS IS_HOLDER
  FROM ssdb_integration.lr_strategy.union_base u CROSS JOIN s2 CROSS JOIN pv),
r AS (               -- PICK: the one firm_2 holder row per opportunity key that takes the key's MM_OPP
  SELECT r0.*, r0.SOURCE = s2.V AND r0.IS_HOLDER AND ROW_NUMBER() OVER (
           PARTITION BY r0.SOURCE, r0.ZIP_CODE, r0.DIST_CH, r0.CBD_ID, r0.PRODUCT_V2
           ORDER BY r0.IS_HOLDER DESC, r0.ACTUAL_SALES_AMOUNT DESC NULLS LAST, r0.FISCAL_YR, r0.TERR_WHOLESALER,
                    r0.SALES_WHOLESALER, r0.TERR_WHOLESALER_CLEAN_NAME, r0.SALES_WHOLESALER_CLEAN_NAME, r0.FIRM,
                    r0.PARENT, r0.NEW_DIST, r0.CHANNEL, r0.STATE, r0.SALES_AMOUNT, r0.SALES_WHOLESALER_TERRITORY_ID,
                    r0.SALES_WHOLESALER_ADDRESS_ID, r0.TERRITORY_WHOLESALER_TERRITORY_ID,
                    r0.TERRITORY_WHOLESALER_ADDRESS_ID, r0.SALES_WHOLESALER_HAS_TERRITORY,
                    r0.TERRITORY_WHOLESALER_HAS_TERRITORY) = 1 AS PICK
  FROM r0 CROSS JOIN s2),
a AS (               -- the keys with no holder row: their opportunity becomes opp-only rows, one per the file's new_dist and CRD
  SELECT fo.ZIP_CODE, fo.DIST_CH, fo.CBD_ID, fo.PRODUCT_V2, fo.NEW_DIST, fo.FIRM_CRD, SUM(fo.MM_OPP) AS MM_OPP
  FROM fo
  JOIN ak ON ak.ZIP_CODE = fo.ZIP_CODE AND ak.DIST_CH = fo.DIST_CH AND ak.CBD_ID = fo.CBD_ID AND ak.PRODUCT_V2 = fo.PRODUCT_V2
  WHERE NOT EXISTS (SELECT 1 FROM r WHERE r.PICK AND r.ZIP_CODE = ak.ZIP_CODE AND r.DIST_CH = ak.DIST_CH
                    AND r.CBD_ID = ak.CBD_ID AND r.PRODUCT_V2 = ak.PRODUCT_V2)
  GROUP BY fo.ZIP_CODE, fo.DIST_CH, fo.CBD_ID, fo.PRODUCT_V2, fo.NEW_DIST, fo.FIRM_CRD
  HAVING COALESCE(SUM(fo.MM_OPP), 0) <> 0),
b AS (
  SELECT a.*, s2.V AS SRC,
         CASE WHEN ch1.NEW_DIST IS NOT NULL THEN 'firm_1 NEW_DIST' END AS CHANNEL_RULE, ch1.CHANNEL,
         COALESCE(p2.FIRM, p1.FIRM, cn.FIRM) AS FIRM, COALESCE(p2.PARENT, p1.PARENT) AS PARENT,
         h.ID AS HOLDER_ID, COALESCE(nm.NAME, h.NAME) AS HOLDER_NAME, COALESCE(h.N, 0) AS N_HOLDERS,
         COALESCE(st.STATE, us.STATE) AS STATE, fk.FIRM_KEY
  FROM a CROSS JOIN s1 CROSS JOIN s2
  LEFT JOIN ch1 ON ch1.NEW_DIST = a.NEW_DIST
  LEFT JOIN fp p2 ON p2.CBD_ID = a.CBD_ID AND p2.SOURCE = s2.V
  LEFT JOIN fp p1 ON p1.CBD_ID = a.CBD_ID AND p1.SOURCE = s1.V
  LEFT JOIN cn ON cn.CBD_ID = a.CBD_ID
  LEFT JOIN h ON h.ZIP_CODE = a.ZIP_CODE AND h.DIST_CH = a.DIST_CH
  LEFT JOIN nm ON nm.ID = h.ID
  LEFT JOIN st ON st.ZIP_CODE = a.ZIP_CODE
  LEFT JOIN us ON us.ZIP_CODE = a.ZIP_CODE
  LEFT JOIN ssdb_integration.lr_strategy.firm_key fk ON fk.ID_TYPE = 'CBD_ID' AND fk.ID = TO_CHAR(a.CBD_ID))
SELECT r.* EXCLUDE (IS_HOLDER, PICK) REPLACE (COALESCE(ak.MM_OPP, r.MM_OPP) AS MM_OPP),
       CASE WHEN ak.CBD_ID IS NOT NULL THEN 'union + opp file' ELSE 'union' END AS ROW_ORIGIN,
       ak.FILE_NEW_DIST, CASE WHEN ak.CBD_ID IS NOT NULL THEN 'sales row' END AS CHANNEL_RULE,
       CASE WHEN ak.CBD_ID IS NOT NULL THEN COALESCE(h.N, 0) END AS N_HOLDERS, fk.FIRM_KEY,
       CASE WHEN cc.N_CRD = 1 THEN cc.CRD END AS FIRM_CRD,
       CASE WHEN r.CBD_ID IS NULL THEN NULL WHEN cc.N_CRD = 1 THEN 'company has one CRD'
            WHEN cc.N_CRD > 1 THEN 'company has 2+ CRDs' ELSE 'company has no CRD' END AS CRD_RULE
FROM r
LEFT JOIN ak ON r.PICK AND ak.ZIP_CODE = r.ZIP_CODE AND ak.DIST_CH = r.DIST_CH
            AND ak.CBD_ID = r.CBD_ID AND ak.PRODUCT_V2 = r.PRODUCT_V2
LEFT JOIN h ON h.ZIP_CODE = r.ZIP_CODE AND h.DIST_CH = r.DIST_CH
LEFT JOIN ssdb_integration.lr_strategy.firm_key fk ON fk.ID_TYPE = 'CBD_ID' AND fk.ID = TO_CHAR(r.CBD_ID)
LEFT JOIN cc ON cc.CBD = TO_CHAR(r.CBD_ID)
UNION ALL BY NAME     -- the columns not named below are NULL on opp-only rows
SELECT b.SRC AS SOURCE, b.CBD_ID, b.FIRM, b.PARENT, b.DIST_CH, b.NEW_DIST, b.CHANNEL, b.STATE,
       b.ZIP_CODE, b.PRODUCT_V2, b.MM_OPP,
       b.HOLDER_NAME AS TERR_WHOLESALER_CLEAN_NAME, b.HOLDER_NAME AS SALES_WHOLESALER_CLEAN_NAME,
       b.HOLDER_ID AS SALES_WHOLESALER_TERRITORY_ID, b.HOLDER_ID AS TERRITORY_WHOLESALER_TERRITORY_ID,
       CASE WHEN b.N_HOLDERS > 0 THEN 1 ELSE 0 END AS SALES_WHOLESALER_HAS_TERRITORY,
       CASE WHEN b.N_HOLDERS > 0 THEN 1 ELSE 0 END AS TERRITORY_WHOLESALER_HAS_TERRITORY,
       'opp file' AS ROW_ORIGIN, b.NEW_DIST AS FILE_NEW_DIST, b.CHANNEL_RULE, b.N_HOLDERS, b.FIRM_KEY,
       b.FIRM_CRD, 'file' AS CRD_RULE
FROM b;

-- Statement 2.  Checks.
WITH
k AS (SELECT * FROM ssdb_integration.lr_strategy.synthetic_key),
s1 AS (SELECT VALUE AS V FROM k WHERE KIND = 'SOURCE' AND CODE = 'firm_1'),
s2 AS (SELECT VALUE AS V FROM k WHERE KIND = 'SOURCE' AND CODE = 'firm_2'),
d AS (SELECT NUM AS D FROM k WHERE KIND = 'divisor' AND VALUE = 'MM_OPP'),
dm AS (              -- as statement 1
  SELECT a.VALUE AS FILE_DIST_CH, m.GONE
  FROM (VALUES ('O2_01', FALSE), ('O2_02', FALSE), ('O2_03', FALSE), ('O2_04', FALSE), ('O2_05', TRUE)) m(FILE_CODE, GONE)
  CROSS JOIN s2
  JOIN k a ON a.KIND = 'DIST_CH' AND a.SOURCE = s2.V AND a.CODE = m.FILE_CODE),
pv AS (SELECT a.VALUE AS VA, b.VALUE AS VARIABLE
       FROM k a JOIN k b ON b.KIND = 'PRODUCT_V2' AND b.CODE = 'PR02' WHERE a.KIND = 'PRODUCT_V2' AND a.CODE = 'PR05'),
uo AS (SELECT * FROM ssdb_integration.lr_strategy.UNION_OPP),
src AS (             -- union_base as UNION_OPP should carry it: firm_2's VA as VARIABLE (Q8)
  SELECT u.* REPLACE (CASE WHEN u.SOURCE = s2.V AND u.PRODUCT_V2 = pv.VA THEN pv.VARIABLE ELSE u.PRODUCT_V2 END AS PRODUCT_V2)
  FROM ssdb_integration.lr_strategy.union_base u CROSS JOIN s2 CROSS JOIN pv),
fo AS (              -- opp_f2_final with its drop reason
  SELECT f.*, CASE WHEN dm.GONE IS NULL THEN 'FILE_DIST_CH in no map' WHEN dm.GONE THEN 'NO CHANNEL'
                   WHEN f.PRODUCT_LINE = 'FIXED' THEN 'FIXED' END AS DROP_REASON
  FROM ssdb_integration.lr_strategy.opp_f2_final f LEFT JOIN dm ON dm.FILE_DIST_CH = f.FILE_DIST_CH),
ap AS (SELECT uo.* FROM uo JOIN s2 ON uo.SOURCE = s2.V WHERE uo.ROW_ORIGIN <> 'union'),   -- firm_2 rows carrying file opportunity
ot AS (SELECT SUM(MM_OPP) AS O FROM uo JOIN s2 ON uo.SOURCE = s2.V),
g AS (               -- the rows carrying file opportunity by each lineage column
  SELECT 'ROW_ORIGIN' AS DIM, ROW_ORIGIN AS V, MM_OPP FROM ap
  UNION ALL SELECT 'CHANNEL_RULE', CHANNEL_RULE, MM_OPP FROM ap
  UNION ALL SELECT 'FILE_NEW_DIST', FILE_NEW_DIST, MM_OPP FROM ap
  UNION ALL SELECT 'CRD_RULE', CRD_RULE, MM_OPP FROM ap
  UNION ALL SELECT 'N_HOLDERS', CAST(N_HOLDERS AS VARCHAR), MM_OPP FROM ap),
sc AS (              -- ACTUAL_SALES_AMOUNT by SOURCE x CHANNEL x PRODUCT_V2: UNION_OPP minus the source
  SELECT SOURCE, CHANNEL, PRODUCT_V2, SUM(S) AS DIFF
  FROM (SELECT SOURCE, CHANNEL, PRODUCT_V2, ACTUAL_SALES_AMOUNT AS S FROM uo
        UNION ALL SELECT SOURCE, CHANNEL, PRODUCT_V2, -ACTUAL_SALES_AMOUNT FROM src) x
  GROUP BY SOURCE, CHANNEL, PRODUCT_V2),
-- Row identity without EXCEPT: Snowflake's docs say neither how MINUS / EXCEPT compare NULLs nor whether they keep
-- duplicates (docs, Set operators, read 2026-10-25).  HASH "never returns NULL, even for NULL inputs" and takes * EXCLUDE (docs, HASH), so counting rows per
-- hash on each side compares the two tables as multisets, NULL-safe.  NUMBER values hash alike whatever their
-- precision and scale; a column whose type changes kind (FLOAT <-> NUMBER) would make every row differ (loud).
hs AS (SELECT H, MAX(SOURCE) AS SOURCE, COUNT(*) AS N, COUNT(MM_OPP) AS NM, SUM(MM_OPP) AS S
       FROM (SELECT HASH(* EXCLUDE (MM_OPP)) AS H, SOURCE, MM_OPP FROM src) x GROUP BY H),
hu AS (SELECT H, MAX(SOURCE) AS SOURCE, COUNT(*) AS N, COUNT(MM_OPP) AS NM, SUM(MM_OPP) AS S
       FROM (SELECT HASH(* EXCLUDE (MM_OPP, ROW_ORIGIN, FILE_NEW_DIST, CHANNEL_RULE, N_HOLDERS, FIRM_KEY, FIRM_CRD, CRD_RULE)) AS H, SOURCE, MM_OPP
             FROM uo WHERE ROW_ORIGIN <> 'opp file') x GROUP BY H),
hd AS (SELECT COALESCE(hs.SOURCE, hu.SOURCE) AS SOURCE, COALESCE(hs.N, 0) AS NS, COALESCE(hu.N, 0) AS NU,
              COALESCE(hs.NM, 0) AS NMS, COALESCE(hu.NM, 0) AS NMU, COALESCE(hs.S, 0) AS SS, COALESCE(hu.S, 0) AS SU
       FROM hs FULL OUTER JOIN hu ON hu.H = hs.H)
SELECT 'union_base rows not found in UNION_OPP with every column but MM_OPP unchanged, plus rows added or repeated'
       AS CHECK_NAME,
       (SELECT SUM(ABS(NS - NU)) FROM hd) AS VALUE, TRUE AS MUST_BE_ZERO
UNION ALL SELECT 'firm_1 rows whose MM_OPP changed (row groups by hash)',
       (SELECT COUNT(*) FROM hd WHERE SOURCE IN (SELECT V FROM s1)
          AND (NS <> NU OR NMS <> NMU OR ABS(SS - SU) > 1e-9 * GREATEST(ABS(SS), ABS(SU), 1))), TRUE
UNION ALL SELECT 'firm_2 rows of union_base carrying MM_OPP (union_base is the union without firm_2 opportunity)',
       (SELECT COUNT(*) FROM src JOIN s2 ON src.SOURCE = s2.V WHERE src.MM_OPP IS NOT NULL), TRUE
UNION ALL SELECT 'ACTUAL_SALES_AMOUNT cells (SOURCE x CHANNEL x PRODUCT_V2) different from the source',
       (SELECT COUNT(*) FROM sc WHERE ABS(COALESCE(DIFF, 0)) > 0.001), TRUE     -- ponytail: 0.001 absorbs float summation order
UNION ALL SELECT 'firm_2 MM_OPP of opp_f2_final after drops differs from firm_2 MM_OPP in UNION_OPP by more than 0.001 x divisor (1 = yes)',
       (SELECT CASE WHEN ABS(COALESCE((SELECT SUM(MM_OPP) FROM fo WHERE DROP_REASON IS NULL), 0)
                           - COALESCE((SELECT O FROM ot), 0)) > 0.001 * d.D THEN 1 ELSE 0 END FROM d), TRUE
UNION ALL SELECT 'UNION_OPP rows with a CBD_ID and no FIRM_KEY',
       (SELECT COUNT(*) FROM uo WHERE CBD_ID IS NOT NULL AND FIRM_KEY IS NULL), TRUE
UNION ALL SELECT 'opp_f2_final rows whose FILE_DIST_CH is in no map',
       (SELECT COUNT(*) FROM fo WHERE DROP_REASON = 'FILE_DIST_CH in no map'), TRUE
UNION ALL SELECT 'opp-only rows with no FIRM_CRD',
       (SELECT COUNT(*) FROM ap WHERE ROW_ORIGIN = 'opp file' AND FIRM_CRD IS NULL), TRUE
UNION ALL SELECT 'firm_2 opportunity keys carrying MM_OPP on more than one row (opp-only rows: key x NEW_DIST x CRD)',
       (SELECT COUNT(*) FROM (SELECT 1 FROM ap WHERE MM_OPP IS NOT NULL
                              GROUP BY ZIP_CODE, DIST_CH, CBD_ID, PRODUCT_V2, CASE WHEN ROW_ORIGIN = 'opp file' THEN NEW_DIST END,
                                       CASE WHEN ROW_ORIGIN = 'opp file' THEN FIRM_CRD END
                              HAVING COUNT(*) > 1) x), TRUE
UNION ALL SELECT 'opp-only rows with NULL DIST_CH, PRODUCT_V2 or NEW_DIST',
       (SELECT COUNT(*) FROM ap WHERE ROW_ORIGIN = 'opp file'
          AND (DIST_CH IS NULL OR PRODUCT_V2 IS NULL OR NEW_DIST IS NULL)), TRUE
UNION ALL SELECT 'opp-only rows with no CHANNEL: firm_1''s union rows carry no single CHANNEL for their NEW_DIST (pending the CHANNEL step)',
       (SELECT COUNT(*) FROM ap WHERE ROW_ORIGIN = 'opp file' AND CHANNEL IS NULL), TRUE
UNION ALL SELECT 'firm_2 rows of UNION_OPP still with firm_2''s VA product (Q8: counted as VARIABLE)',
       (SELECT COUNT(*) FROM uo CROSS JOIN pv JOIN s2 ON uo.SOURCE = s2.V WHERE uo.PRODUCT_V2 = pv.VA), TRUE
UNION ALL SELECT 'firm_2 union rows with VA, counted as VARIABLE (Q8)',
       (SELECT COUNT(*) FROM ssdb_integration.lr_strategy.union_base u CROSS JOIN pv JOIN s2 ON u.SOURCE = s2.V
        WHERE u.PRODUCT_V2 = pv.VA), FALSE
UNION ALL SELECT 'firm_2 percent of MM_OPP on opp-only rows with no CHANNEL, NEW_DIST ' || COALESCE(NEW_DIST, 'NULL'),
       ROUND(100 * SUM(MM_OPP) / MAX(ot.O), 2), FALSE
       FROM ap CROSS JOIN ot WHERE ROW_ORIGIN = 'opp file' AND CHANNEL IS NULL GROUP BY NEW_DIST
UNION ALL SELECT 'firm_2 percent of MM_OPP on sales rows whose NEW_DIST differs from the file''s new_dist',
       (SELECT ROUND(100 * COALESCE(SUM(MM_OPP), 0) / MAX(ot.O), 2) FROM ap CROSS JOIN ot
        WHERE ROW_ORIGIN = 'union + opp file' AND FILE_NEW_DIST IS NOT NULL AND NEW_DIST IS DISTINCT FROM FILE_NEW_DIST), FALSE
UNION ALL SELECT 'firm_2 percent of MM_OPP on sales rows whose key carries 2+ new_dist in the file',
       (SELECT ROUND(100 * COALESCE(SUM(MM_OPP), 0) / MAX(ot.O), 2) FROM ap CROSS JOIN ot
        WHERE ROW_ORIGIN = 'union + opp file' AND FILE_NEW_DIST IS NULL), FALSE
UNION ALL SELECT 'CBD_IDs with 2+ FIRM in one SOURCE',
       (SELECT COUNT(*) FROM (SELECT CBD_ID, SOURCE FROM src
                              WHERE CBD_ID IS NOT NULL GROUP BY CBD_ID, SOURCE HAVING COUNT(DISTINCT FIRM) > 1) x), TRUE
UNION ALL SELECT 'firm_2 rows carrying file opportunity with no FIRM',
       (SELECT COUNT(*) FROM ap WHERE FIRM IS NULL), FALSE
UNION ALL SELECT 'firm_2 percent of MM_OPP on rows with no FIRM',
       (SELECT ROUND(100 * SUM(MM_OPP) / MAX(ot.O), 2) FROM ap CROSS JOIN ot WHERE FIRM IS NULL), FALSE
UNION ALL SELECT 'CBD_IDs in union_base and crd_cbd: percent whose crd_cbd firm name equals the union FIRM',
       (SELECT ROUND(100 * AVG(CASE WHEN c.FIRM = u.FIRM THEN 1 ELSE 0 END), 1)
        FROM (SELECT CBD_ID, MAX(FIRM) AS FIRM FROM src WHERE CBD_ID IS NOT NULL GROUP BY CBD_ID) u
        JOIN (SELECT CAST(CBD_ID AS VARCHAR) AS CBD_ID, MAX(FIRM) AS FIRM FROM ssdb_integration.lr_strategy.crd_cbd
              WHERE CBD_ID IS NOT NULL GROUP BY 1) c ON c.CBD_ID = u.CBD_ID), FALSE
UNION ALL SELECT 'dropped opp_f2_final rows: ' || DROP_REASON, COUNT(*), FALSE
       FROM fo WHERE DROP_REASON IS NOT NULL GROUP BY DROP_REASON
UNION ALL SELECT 'dropped MM_OPP in coded units: ' || DROP_REASON, ROUND(SUM(MM_OPP) / MAX(d.D), 1), FALSE
       FROM fo CROSS JOIN d WHERE DROP_REASON IS NOT NULL GROUP BY DROP_REASON
UNION ALL SELECT 'firm_2 rows by ' || DIM || ': ' || COALESCE(V, 'NULL'), COUNT(*), FALSE FROM g GROUP BY DIM, V
UNION ALL SELECT 'firm_2 percent of MM_OPP by ' || DIM || ': ' || COALESCE(V, 'NULL'),
       ROUND(100 * SUM(MM_OPP) / MAX(ot.O), 1), FALSE FROM g CROSS JOIN ot GROUP BY DIM, V
UNION ALL SELECT 'percent of ' || s.SRC_NAME || ' ACTUAL_SALES_AMOUNT on rows that carry MM_OPP',
       ROUND(100 * SUM(CASE WHEN uo.MM_OPP IS NOT NULL THEN uo.ACTUAL_SALES_AMOUNT END) / SUM(uo.ACTUAL_SALES_AMOUNT), 1), FALSE
       FROM uo JOIN (SELECT V, 'firm_1' AS SRC_NAME FROM s1 UNION ALL SELECT V, 'firm_2' FROM s2) s ON uo.SOURCE = s.V
       GROUP BY s.SRC_NAME
UNION ALL SELECT 'firm_1 percent of MM_OPP by CRD_RULE: ' || COALESCE(uo.CRD_RULE, 'NULL'),
       ROUND(100 * SUM(uo.MM_OPP) / MAX(t1.O), 1), FALSE
       FROM uo JOIN s1 ON uo.SOURCE = s1.V
       CROSS JOIN (SELECT SUM(u.MM_OPP) AS O FROM uo u JOIN s1 ON u.SOURCE = s1.V) t1
       GROUP BY uo.CRD_RULE
UNION ALL SELECT 'firm_2 MM_OPP in coded units', ROUND((SELECT O FROM ot) / (SELECT D FROM d), 1), FALSE
UNION ALL SELECT 'firm_1 MM_OPP in coded units',
       ROUND((SELECT SUM(u.MM_OPP) FROM src u JOIN s1 ON u.SOURCE = s1.V) / (SELECT D FROM d), 1), FALSE
ORDER BY MUST_BE_ZERO DESC, CHECK_NAME;

-- Statement 3.  firm_2 MM_OPP from the file by DIST_CH x NEW_DIST x CHANNEL (rows on sales rows and opp-only rows),
-- next to firm_2's share of positive sales in the same cell (as the firm_1 table in DATASET_LOG.md, 2026-10-21).
WITH
s2 AS (SELECT VALUE AS V FROM ssdb_integration.lr_strategy.synthetic_key WHERE KIND = 'SOURCE' AND CODE = 'firm_2'),
o AS (SELECT DIST_CH, NEW_DIST, CHANNEL,
             SUM(CASE WHEN ROW_ORIGIN = 'union + opp file' THEN 1 ELSE 0 END) AS ROWS_ON_SALES_ROWS,
             SUM(CASE WHEN ROW_ORIGIN = 'opp file' THEN 1 ELSE 0 END) AS ROWS_OPP_ONLY,
             COUNT(DISTINCT CBD_ID) AS CBD_IDS, SUM(MM_OPP) AS MM_OPP
      FROM ssdb_integration.lr_strategy.UNION_OPP WHERE ROW_ORIGIN <> 'union' GROUP BY DIST_CH, NEW_DIST, CHANNEL),
s AS (SELECT u.DIST_CH, u.NEW_DIST, u.CHANNEL, SUM(CASE WHEN u.ACTUAL_SALES_AMOUNT > 0 THEN u.ACTUAL_SALES_AMOUNT END) AS SALES
      FROM ssdb_integration.lr_strategy.union_base u JOIN s2 ON u.SOURCE = s2.V
      GROUP BY u.DIST_CH, u.NEW_DIST, u.CHANNEL)
SELECT COALESCE(o.DIST_CH, s.DIST_CH) AS DIST_CH, COALESCE(o.NEW_DIST, s.NEW_DIST) AS NEW_DIST,
       COALESCE(o.CHANNEL, s.CHANNEL) AS CHANNEL,
       o.ROWS_ON_SALES_ROWS, o.ROWS_OPP_ONLY, o.CBD_IDS,
       ROUND(100 * o.MM_OPP / SUM(o.MM_OPP) OVER (), 2) AS PCT_OF_FIRM_2_MM_OPP,
       ROUND(100 * s.SALES / SUM(s.SALES) OVER (), 2) AS PCT_OF_FIRM_2_SALES
FROM o
FULL OUTER JOIN s ON COALESCE(s.DIST_CH, '~') = COALESCE(o.DIST_CH, '~')    -- plain equality: a FULL JOIN needs it
                 AND COALESCE(s.NEW_DIST, '~') = COALESCE(o.NEW_DIST, '~') AND COALESCE(s.CHANNEL, '~') = COALESCE(o.CHANNEL, '~')
ORDER BY PCT_OF_FIRM_2_MM_OPP DESC NULLS LAST, PCT_OF_FIRM_2_SALES DESC NULLS LAST;

-- Statement 4.  Does opportunity align across the firms at the same ZIP_CODE and firm (owner, 2026-10-26)?  Each firm's
-- MM_OPP in UNION_OPP summed to ZIP_CODE x firm x PRODUCT_V2 over all channels; firm = FIRM_KEY and, for comparison,
-- CBD_ID.  Equal = the same to 3 decimals of coded units (as Q23).  Shares of each firm's MM_OPP.
WITH
k AS (SELECT * FROM ssdb_integration.lr_strategy.synthetic_key),
s1 AS (SELECT VALUE AS V FROM k WHERE KIND = 'SOURCE' AND CODE = 'firm_1'),
s2 AS (SELECT VALUE AS V FROM k WHERE KIND = 'SOURCE' AND CODE = 'firm_2'),
d AS (SELECT NUM AS D FROM k WHERE KIND = 'divisor' AND VALUE = 'MM_OPP'),
uo AS (SELECT u.*, CASE WHEN u.SOURCE = s1.V THEN u.MM_OPP END AS M1, CASE WHEN u.SOURCE = s2.V THEN u.MM_OPP END AS M2
       FROM ssdb_integration.lr_strategy.UNION_OPP u CROSS JOIN s1 CROSS JOIN s2 WHERE u.MM_OPP IS NOT NULL),
c AS (SELECT 'FIRM_KEY' AS LVL, ZIP_CODE, FIRM_KEY AS FIRM, PRODUCT_V2, SUM(M1) AS O1, SUM(M2) AS O2
      FROM uo GROUP BY ZIP_CODE, FIRM_KEY, PRODUCT_V2
      UNION ALL
      SELECT 'CBD_ID', ZIP_CODE, CBD_ID, PRODUCT_V2, SUM(M1), SUM(M2)
      FROM uo GROUP BY ZIP_CODE, CBD_ID, PRODUCT_V2),
x AS (SELECT c.LVL, c.O1, c.O2,
             CASE WHEN COALESCE(c.O1, 0) = 0 THEN 'firm_2 only' WHEN COALESCE(c.O2, 0) = 0 THEN 'firm_1 only'
                  WHEN ROUND(c.O1 / d.D, 3) = ROUND(c.O2 / d.D, 3) THEN 'both: equal'
                  WHEN ABS(c.O2 - c.O1) <= 0.01 * ABS(c.O1) THEN 'both: within 1%'
                  WHEN c.O2 > c.O1 THEN 'both: firm_2 more than 1% higher'
                  ELSE 'both: firm_2 more than 1% lower' END AS ALIGNMENT
      FROM c CROSS JOIN d),
y AS (SELECT LVL, ALIGNMENT, COUNT(*) AS CELLS, SUM(O1) AS O1, SUM(O2) AS O2 FROM x GROUP BY LVL, ALIGNMENT)
SELECT LVL, ALIGNMENT, CELLS,
       ROUND(100 * O1 / SUM(O1) OVER (PARTITION BY LVL), 2) AS PCT_FIRM_1_MM_OPP,
       ROUND(100 * O2 / SUM(O2) OVER (PARTITION BY LVL), 2) AS PCT_FIRM_2_MM_OPP,
       ROUND(O2 / NULLIF(O1, 0), 3) AS FIRM_2_OVER_FIRM_1
FROM y
ORDER BY LVL DESC, ALIGNMENT;

-- Statement 5.  By FIRM_KEY, the cells (ZIP_CODE x PRODUCT_V2) where both firms have MM_OPP: how many, the share equal,
-- each firm's MM_OPP there; largest gaps first.  FIRM_NAME = firm_1's FIRM of the key's CBD_ID.  Names: read at work.
WITH
k AS (SELECT * FROM ssdb_integration.lr_strategy.synthetic_key),
s1 AS (SELECT VALUE AS V FROM k WHERE KIND = 'SOURCE' AND CODE = 'firm_1'),
s2 AS (SELECT VALUE AS V FROM k WHERE KIND = 'SOURCE' AND CODE = 'firm_2'),
d AS (SELECT NUM AS D FROM k WHERE KIND = 'divisor' AND VALUE = 'MM_OPP'),
uo AS (SELECT u.*, CASE WHEN u.SOURCE = s1.V THEN u.MM_OPP END AS M1, CASE WHEN u.SOURCE = s2.V THEN u.MM_OPP END AS M2
       FROM ssdb_integration.lr_strategy.UNION_OPP u CROSS JOIN s1 CROSS JOIN s2 WHERE u.MM_OPP IS NOT NULL),
c AS (SELECT FIRM_KEY, ZIP_CODE, PRODUCT_V2, SUM(M1) AS O1, SUM(M2) AS O2
      FROM uo GROUP BY FIRM_KEY, ZIP_CODE, PRODUCT_V2
      HAVING COALESCE(SUM(M1), 0) <> 0 AND COALESCE(SUM(M2), 0) <> 0),
nm AS (SELECT TO_CHAR(u.CBD_ID) AS CBD_ID, MAX(u.FIRM) AS FIRM
       FROM ssdb_integration.lr_strategy.UNION_OPP u JOIN s1 ON u.SOURCE = s1.V WHERE u.CBD_ID IS NOT NULL GROUP BY TO_CHAR(u.CBD_ID))
SELECT c.FIRM_KEY, nm.FIRM AS FIRM_NAME, COUNT(*) AS CELLS_BOTH,
       ROUND(100 * AVG(CASE WHEN ROUND(c.O1 / d.D, 3) = ROUND(c.O2 / d.D, 3) THEN 1 ELSE 0 END), 1) AS PCT_CELLS_EQUAL,
       SUM(c.O1) AS FIRM_1_MM_OPP, SUM(c.O2) AS FIRM_2_MM_OPP, ROUND(SUM(c.O2) / NULLIF(SUM(c.O1), 0), 3) AS FIRM_2_OVER_FIRM_1
FROM c CROSS JOIN d
LEFT JOIN nm ON nm.CBD_ID = c.FIRM_KEY
GROUP BY c.FIRM_KEY, nm.FIRM
ORDER BY ABS(SUM(c.O2) - SUM(c.O1)) DESC
LIMIT 40;
