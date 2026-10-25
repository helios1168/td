-- UNION_OPP: the union with firm_2's opportunity in MM_OPP, in firm_1's layout (owner, 2026-10-25: "no it needs
-- to match the layout of firm 1's data. there needs to be a join so that mm_opp and sales exists for firm two on
-- the same rows so we can do analytics ar the wholesaler level"; data_withnewchannel_union_w_joinkeys itself is
-- never touched).  firm_1 puts MM_OPP on a sales row of its key when the seller is the holder, else on its own row.
-- UNION_OPP = the union's firm_1 rows unchanged + its firm_2 rows (every column unchanged except MM_OPP) + opp-only rows.
-- Same columns as the union, in its order, plus lineage columns at the end:
--   ROW_ORIGIN    'union' (row as in the source), 'union + opp file' (a firm_2 sales row now carrying MM_OPP),
--                 'opp file' (a new opp-only row)
--   CBD_METHOD    METHOD of CRD_MATCH (23), taken from the CRD with the largest single OPP row in the key
--   CHANNEL_RULE  which rule gave NEW_DIST and CHANNEL on an opp-only row: 'company x DIST_CH', 'company',
--                 'DIST_CH default'; 'sales row' where the row is a sales row
--   N_HOLDERS     distinct CLEAN_IDs holding the ZIP_CODE x DIST_CH in territories (0 = the TX/NY block, Q10; 2 = shared)
-- The file's opportunity is OPP_MAPPED (23) without its dropped rows, with the CRD's CBD_ID from CRD_MATCH, summed
-- to the key ZIP_CODE x DIST_CH x CBD_ID x PRODUCT_V2 (CHANNEL is not in it); MM_OPP = SUM(OPP); a key that sums
-- to 0 is left out.  A key goes on exactly one firm_2 union row with that ZIP_CODE, DIST_CH, CBD_ID and PRODUCT_V2
-- whose seller is the holder (SALES_WHOLESALER_TERRITORY_ID = TERRITORY_WHOLESALER_TERRITORY_ID): the one with the
-- largest ACTUAL_SALES_AMOUNT, ties on the other columns.  It takes that row's NEW_DIST and CHANNEL.  A key with
-- no such row is an opp-only row: FISCAL_YR, the sales amounts and the address IDs NULL; like firm_1's, TERR_WHOLESALER
-- and SALES_WHOLESALER are NULL, both CLEAN_NAME columns carry the holder's name, both TERRITORY_ID columns the
-- holder's CLEAN_ID, both HAS_TERRITORY flags are 1 (0 with no holder).  A firm_2 union row that gets no key keeps its NULL MM_OPP.
-- Run 23 first.  Run statement 1, then 2 (checks: every MUST_BE_ZERO row must be 0), then 3.

-- Statement 1.  The table.
CREATE OR REPLACE TABLE ssdb_integration.lr_strategy.UNION_OPP AS
WITH
k AS (SELECT * FROM ssdb_integration.lr_strategy.synthetic_key),
s1 AS (SELECT VALUE AS V FROM k WHERE KIND = 'SOURCE' AND CODE = 'firm_1'),
s2 AS (SELECT VALUE AS V FROM k WHERE KIND = 'SOURCE' AND CODE = 'firm_2'),
ak AS (
  SELECT m.ZIP_CODE, m.DIST_CH, c.CBD_ID, m.PRODUCT_V2, SUM(m.OPP) AS MM_OPP,
         MAX_BY(c.METHOD, ABS(m.OPP)) AS CBD_METHOD
  FROM ssdb_integration.lr_strategy.OPP_MAPPED m
  JOIN ssdb_integration.lr_strategy.CRD_MATCH c ON c.FIRM_CRD = m.FIRM_CRD
  WHERE m.DROP_REASON IS NULL
  GROUP BY m.ZIP_CODE, m.DIST_CH, c.CBD_ID, m.PRODUCT_V2
  HAVING COALESCE(SUM(m.OPP), 0) <> 0),
f2 AS (              -- firm_2's union rows: the company's own NEW_DIST and CHANNEL
  SELECT u.CBD_ID, u.DIST_CH, u.NEW_DIST, u.CHANNEL
  FROM ssdb_integration.lr_strategy.data_withnewchannel_union_w_joinkeys u JOIN s2 ON u.SOURCE = s2.V
  WHERE u.NEW_DIST IS NOT NULL AND u.CHANNEL IS NOT NULL),
cx AS (              -- company x DIST_CH: the NEW_DIST / CHANNEL on most rows
  SELECT CBD_ID, DIST_CH, NEW_DIST, CHANNEL,
         ROW_NUMBER() OVER (PARTITION BY CBD_ID, DIST_CH ORDER BY N DESC, NEW_DIST, CHANNEL) AS RK
  FROM (SELECT CBD_ID, DIST_CH, NEW_DIST, CHANNEL, COUNT(*) AS N FROM f2
        WHERE CBD_ID IS NOT NULL AND DIST_CH IS NOT NULL GROUP BY CBD_ID, DIST_CH, NEW_DIST, CHANNEL) x),
co AS (              -- company, any DIST_CH
  SELECT CBD_ID, NEW_DIST, CHANNEL,
         ROW_NUMBER() OVER (PARTITION BY CBD_ID ORDER BY N DESC, NEW_DIST, CHANNEL) AS RK
  FROM (SELECT CBD_ID, NEW_DIST, CHANNEL, COUNT(*) AS N FROM f2
        WHERE CBD_ID IS NOT NULL GROUP BY CBD_ID, NEW_DIST, CHANNEL) x),
df AS (              -- proposed, Q21: CHANNEL by DIST_CH, NEW_DIST = firm_2's on most rows of that CHANNEL
  SELECT b.VALUE AS DIST_CH, m.CHANNEL, nd.NEW_DIST
  FROM (VALUES ('D2_01', 'IFA'), ('D2_02', 'FI'), ('D2_03', 'WH'), ('D2_04', 'IFA')) m(DIST_CODE, CHANNEL)
  CROSS JOIN s2
  JOIN k b ON b.KIND = 'DIST_CH' AND b.SOURCE = s2.V AND b.CODE = m.DIST_CODE
  LEFT JOIN (SELECT CHANNEL, NEW_DIST, ROW_NUMBER() OVER (PARTITION BY CHANNEL ORDER BY N DESC, NEW_DIST) AS RK
             FROM (SELECT CHANNEL, NEW_DIST, COUNT(*) AS N FROM f2 GROUP BY CHANNEL, NEW_DIST) x) nd
         ON nd.CHANNEL = m.CHANNEL AND nd.RK = 1),
fp AS (              -- FIRM and PARENT of a company in each SOURCE
  SELECT u.CBD_ID, u.SOURCE, MAX(u.FIRM) AS FIRM, MAX(u.PARENT) AS PARENT
  FROM ssdb_integration.lr_strategy.data_withnewchannel_union_w_joinkeys u
  WHERE u.CBD_ID IS NOT NULL GROUP BY u.CBD_ID, u.SOURCE),
h AS (               -- holders of a ZIP_CODE x DIST_CH in territories
  SELECT t.ZIP_CODE, t.CHANNEL AS DIST_CH, MIN(t.CLEAN_ID) AS ID, COUNT(DISTINCT t.CLEAN_ID) AS N,
         MIN_BY(t.CLEAN_NAME, t.CLEAN_ID) AS NAME
  FROM ssdb_integration.lr_strategy.territories t JOIN s2 ON t.SOURCE = s2.V
  WHERE t.CLEAN_ID IS NOT NULL GROUP BY t.ZIP_CODE, t.CHANNEL),
nm AS (              -- the name the union already carries for that ID
  SELECT u.TERRITORY_WHOLESALER_TERRITORY_ID AS ID, MAX(u.TERR_WHOLESALER_CLEAN_NAME) AS NAME
  FROM ssdb_integration.lr_strategy.data_withnewchannel_union_w_joinkeys u JOIN s2 ON u.SOURCE = s2.V
  GROUP BY u.TERRITORY_WHOLESALER_TERRITORY_ID),
st AS (SELECT ZIP_CODE, MAX(STATE) AS STATE FROM ssdb_integration.lr_strategy.territories GROUP BY ZIP_CODE),
us AS (SELECT ZIP_CODE, MAX(STATE) AS STATE FROM ssdb_integration.lr_strategy.data_withnewchannel_union_w_joinkeys GROUP BY ZIP_CODE),
r0 AS (              -- the union with its seller = holder flag
  SELECT u.*, COALESCE(u.SALES_WHOLESALER_TERRITORY_ID = u.TERRITORY_WHOLESALER_TERRITORY_ID, FALSE) AS IS_HOLDER
  FROM ssdb_integration.lr_strategy.data_withnewchannel_union_w_joinkeys u),
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
a AS (               -- the keys with no holder row: they become opp-only rows
  SELECT ak.* FROM ak
  WHERE NOT EXISTS (SELECT 1 FROM r WHERE r.PICK AND r.ZIP_CODE = ak.ZIP_CODE AND r.DIST_CH = ak.DIST_CH
                    AND r.CBD_ID = ak.CBD_ID AND r.PRODUCT_V2 = ak.PRODUCT_V2)),
b AS (
  SELECT a.*, s2.V AS SRC,
         CASE WHEN cx.CBD_ID IS NOT NULL THEN 'company x DIST_CH' WHEN co.CBD_ID IS NOT NULL THEN 'company'
              ELSE 'DIST_CH default' END AS CHANNEL_RULE,
         CASE WHEN cx.CBD_ID IS NOT NULL THEN cx.NEW_DIST WHEN co.CBD_ID IS NOT NULL THEN co.NEW_DIST
              ELSE df.NEW_DIST END AS NEW_DIST,
         CASE WHEN cx.CBD_ID IS NOT NULL THEN cx.CHANNEL WHEN co.CBD_ID IS NOT NULL THEN co.CHANNEL
              ELSE df.CHANNEL END AS CHANNEL,
         COALESCE(p2.FIRM, p1.FIRM) AS FIRM, COALESCE(p2.PARENT, p1.PARENT) AS PARENT,
         h.ID AS HOLDER_ID, COALESCE(nm.NAME, h.NAME) AS HOLDER_NAME, COALESCE(h.N, 0) AS N_HOLDERS,
         COALESCE(st.STATE, us.STATE) AS STATE
  FROM a CROSS JOIN s1 CROSS JOIN s2
  LEFT JOIN cx ON cx.CBD_ID = a.CBD_ID AND cx.DIST_CH = a.DIST_CH AND cx.RK = 1
  LEFT JOIN co ON co.CBD_ID = a.CBD_ID AND co.RK = 1
  LEFT JOIN df ON df.DIST_CH = a.DIST_CH
  LEFT JOIN fp p2 ON p2.CBD_ID = a.CBD_ID AND p2.SOURCE = s2.V
  LEFT JOIN fp p1 ON p1.CBD_ID = a.CBD_ID AND p1.SOURCE = s1.V
  LEFT JOIN h ON h.ZIP_CODE = a.ZIP_CODE AND h.DIST_CH = a.DIST_CH
  LEFT JOIN nm ON nm.ID = h.ID
  LEFT JOIN st ON st.ZIP_CODE = a.ZIP_CODE
  LEFT JOIN us ON us.ZIP_CODE = a.ZIP_CODE)
SELECT r.* EXCLUDE (IS_HOLDER, PICK) REPLACE (COALESCE(ak.MM_OPP, r.MM_OPP) AS MM_OPP),
       CASE WHEN ak.CBD_ID IS NOT NULL THEN 'union + opp file' ELSE 'union' END AS ROW_ORIGIN,
       ak.CBD_METHOD, CASE WHEN ak.CBD_ID IS NOT NULL THEN 'sales row' END AS CHANNEL_RULE,
       CASE WHEN ak.CBD_ID IS NOT NULL THEN COALESCE(h.N, 0) END AS N_HOLDERS
FROM r
LEFT JOIN ak ON r.PICK AND ak.ZIP_CODE = r.ZIP_CODE AND ak.DIST_CH = r.DIST_CH
            AND ak.CBD_ID = r.CBD_ID AND ak.PRODUCT_V2 = r.PRODUCT_V2
LEFT JOIN h ON h.ZIP_CODE = r.ZIP_CODE AND h.DIST_CH = r.DIST_CH
UNION ALL BY NAME     -- the columns not named below are NULL on opp-only rows
SELECT b.SRC AS SOURCE, b.CBD_ID, b.FIRM, b.PARENT, b.DIST_CH, b.NEW_DIST, b.CHANNEL, b.STATE,
       b.ZIP_CODE, b.PRODUCT_V2, b.MM_OPP,
       b.HOLDER_NAME AS TERR_WHOLESALER_CLEAN_NAME, b.HOLDER_NAME AS SALES_WHOLESALER_CLEAN_NAME,
       b.HOLDER_ID AS SALES_WHOLESALER_TERRITORY_ID, b.HOLDER_ID AS TERRITORY_WHOLESALER_TERRITORY_ID,
       CASE WHEN b.N_HOLDERS > 0 THEN 1 ELSE 0 END AS SALES_WHOLESALER_HAS_TERRITORY,
       CASE WHEN b.N_HOLDERS > 0 THEN 1 ELSE 0 END AS TERRITORY_WHOLESALER_HAS_TERRITORY,
       'opp file' AS ROW_ORIGIN, b.CBD_METHOD, b.CHANNEL_RULE, b.N_HOLDERS
FROM b;

-- Statement 2.  Checks.
WITH
k AS (SELECT * FROM ssdb_integration.lr_strategy.synthetic_key),
s1 AS (SELECT VALUE AS V FROM k WHERE KIND = 'SOURCE' AND CODE = 'firm_1'),
s2 AS (SELECT VALUE AS V FROM k WHERE KIND = 'SOURCE' AND CODE = 'firm_2'),
d AS (SELECT NUM AS D FROM k WHERE KIND = 'divisor' AND VALUE = 'MM_OPP'),
uo AS (SELECT * FROM ssdb_integration.lr_strategy.UNION_OPP),
src AS (SELECT * FROM ssdb_integration.lr_strategy.data_withnewchannel_union_w_joinkeys),
ap AS (SELECT uo.* FROM uo JOIN s2 ON uo.SOURCE = s2.V WHERE uo.ROW_ORIGIN <> 'union'),   -- firm_2 rows carrying file opportunity
ot AS (SELECT SUM(MM_OPP) AS O FROM uo JOIN s2 ON uo.SOURCE = s2.V),
g AS (               -- the rows carrying file opportunity by each lineage column
  SELECT 'ROW_ORIGIN' AS DIM, ROW_ORIGIN AS V, MM_OPP FROM ap
  UNION ALL SELECT 'CHANNEL_RULE', CHANNEL_RULE, MM_OPP FROM ap
  UNION ALL SELECT 'CBD_METHOD', CBD_METHOD, MM_OPP FROM ap
  UNION ALL SELECT 'N_HOLDERS', CAST(N_HOLDERS AS VARCHAR), MM_OPP FROM ap),
sc AS (              -- ACTUAL_SALES_AMOUNT by SOURCE x CHANNEL x PRODUCT_V2: UNION_OPP minus the source
  SELECT SOURCE, CHANNEL, PRODUCT_V2, SUM(S) AS DIFF
  FROM (SELECT SOURCE, CHANNEL, PRODUCT_V2, ACTUAL_SALES_AMOUNT AS S FROM uo
        UNION ALL SELECT SOURCE, CHANNEL, PRODUCT_V2, -ACTUAL_SALES_AMOUNT FROM src) x
  GROUP BY SOURCE, CHANNEL, PRODUCT_V2)
SELECT 'source union rows missing from UNION_OPP (every column except MM_OPP)' AS CHECK_NAME,
       (SELECT COUNT(*) FROM (SELECT * EXCLUDE (MM_OPP) FROM src
                              EXCEPT ALL
                              SELECT * EXCLUDE (MM_OPP, ROW_ORIGIN, CBD_METHOD, CHANNEL_RULE, N_HOLDERS)
                              FROM uo WHERE ROW_ORIGIN <> 'opp file') x) AS VALUE, TRUE AS MUST_BE_ZERO
UNION ALL SELECT 'UNION_OPP rows other than opp-only rows missing from the source (every column except MM_OPP)',
       (SELECT COUNT(*) FROM (SELECT * EXCLUDE (MM_OPP, ROW_ORIGIN, CBD_METHOD, CHANNEL_RULE, N_HOLDERS)
                              FROM uo WHERE ROW_ORIGIN <> 'opp file'
                              EXCEPT ALL
                              SELECT * EXCLUDE (MM_OPP) FROM src) x), TRUE
UNION ALL SELECT 'firm_1 rows whose MM_OPP changed (either way)',
       (SELECT COUNT(*) FROM (SELECT * FROM src WHERE SOURCE IN (SELECT V FROM s1)
                              EXCEPT ALL
                              SELECT * EXCLUDE (ROW_ORIGIN, CBD_METHOD, CHANNEL_RULE, N_HOLDERS)
                              FROM uo WHERE SOURCE IN (SELECT V FROM s1)) x)
     + (SELECT COUNT(*) FROM (SELECT * EXCLUDE (ROW_ORIGIN, CBD_METHOD, CHANNEL_RULE, N_HOLDERS)
                              FROM uo WHERE SOURCE IN (SELECT V FROM s1)
                              EXCEPT ALL
                              SELECT * FROM src WHERE SOURCE IN (SELECT V FROM s1)) x), TRUE
UNION ALL SELECT 'ACTUAL_SALES_AMOUNT cells (SOURCE x CHANNEL x PRODUCT_V2) different from the source',
       (SELECT COUNT(*) FROM sc WHERE ABS(COALESCE(DIFF, 0)) > 0.001), TRUE     -- ponytail: 0.001 absorbs float summation order
UNION ALL SELECT 'firm_2 OPP after drops differs from firm_2 MM_OPP in UNION_OPP by more than 0.001 x divisor (1 = yes)',
       (SELECT CASE WHEN ABS(COALESCE((SELECT SUM(OPP) FROM ssdb_integration.lr_strategy.OPP_MAPPED WHERE DROP_REASON IS NULL), 0)
                           - COALESCE((SELECT O FROM ot), 0)) > 0.001 * d.D THEN 1 ELSE 0 END FROM d), TRUE
UNION ALL SELECT 'firm_2 opportunity keys carrying MM_OPP on more than one row',
       (SELECT COUNT(*) FROM (SELECT 1 FROM ap WHERE MM_OPP IS NOT NULL
                              GROUP BY ZIP_CODE, DIST_CH, CBD_ID, PRODUCT_V2 HAVING COUNT(*) > 1) x), TRUE
UNION ALL SELECT 'opp-only rows with NULL DIST_CH, PRODUCT_V2, CHANNEL or NEW_DIST',
       (SELECT COUNT(*) FROM ap WHERE ROW_ORIGIN = 'opp file'
          AND (DIST_CH IS NULL OR PRODUCT_V2 IS NULL OR CHANNEL IS NULL OR NEW_DIST IS NULL)), TRUE
UNION ALL SELECT 'CBD_IDs with 2+ FIRM in one SOURCE',
       (SELECT COUNT(*) FROM (SELECT CBD_ID, SOURCE FROM src
                              WHERE CBD_ID IS NOT NULL GROUP BY CBD_ID, SOURCE HAVING COUNT(DISTINCT FIRM) > 1) x), TRUE
UNION ALL SELECT 'dropped rows: ' || DROP_REASON, COUNT(*), FALSE
       FROM ssdb_integration.lr_strategy.OPP_MAPPED WHERE DROP_REASON IS NOT NULL GROUP BY DROP_REASON
UNION ALL SELECT 'dropped OPP in coded units: ' || DROP_REASON, ROUND(SUM(OPP) / MAX(d.D), 1), FALSE
       FROM ssdb_integration.lr_strategy.OPP_MAPPED CROSS JOIN d WHERE DROP_REASON IS NOT NULL GROUP BY DROP_REASON
UNION ALL SELECT 'zero-sum keys left out (ZIP_CODE x DIST_CH x CBD_ID x PRODUCT_V2)',
       (SELECT COUNT(*) FROM (SELECT 1 FROM ssdb_integration.lr_strategy.OPP_MAPPED m
                              JOIN ssdb_integration.lr_strategy.CRD_MATCH c ON c.FIRM_CRD = m.FIRM_CRD
                              WHERE m.DROP_REASON IS NULL
                              GROUP BY m.ZIP_CODE, m.DIST_CH, c.CBD_ID, m.PRODUCT_V2
                              HAVING COALESCE(SUM(m.OPP), 0) = 0) x), FALSE
UNION ALL SELECT 'firm_2 rows by ' || DIM || ': ' || COALESCE(V, 'NULL'), COUNT(*), FALSE FROM g GROUP BY DIM, V
UNION ALL SELECT 'firm_2 percent of MM_OPP by ' || DIM || ': ' || COALESCE(V, 'NULL'),
       ROUND(100 * SUM(MM_OPP) / MAX(ot.O), 1), FALSE FROM g CROSS JOIN ot GROUP BY DIM, V
UNION ALL SELECT 'percent of ' || s.SRC_NAME || ' ACTUAL_SALES_AMOUNT on rows that carry MM_OPP',
       ROUND(100 * SUM(CASE WHEN uo.MM_OPP IS NOT NULL THEN uo.ACTUAL_SALES_AMOUNT END) / SUM(uo.ACTUAL_SALES_AMOUNT), 1), FALSE
       FROM uo JOIN (SELECT V, 'firm_1' AS SRC_NAME FROM s1 UNION ALL SELECT V, 'firm_2' FROM s2) s ON uo.SOURCE = s.V
       GROUP BY s.SRC_NAME
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
      FROM ssdb_integration.lr_strategy.data_withnewchannel_union_w_joinkeys u JOIN s2 ON u.SOURCE = s2.V
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
