-- UNION_OPP: the union unchanged plus firm_2's opportunity rows, as the shape firm_1 uses (owner, 2026-10-24:
-- "yes new table"; data_withnewchannel_union_w_joinkeys itself is never touched).  It answers: what does the
-- union look like with firm_2's own opportunity in MM_OPP?
-- Same columns as the union, in its order, plus lineage columns at the end (NULL on union rows):
--   OPP_FILE      TRUE on an appended row
--   CBD_METHOD    METHOD of CRD_MATCH (23), taken from the CRD with the largest single OPP row in the group
--   CHANNEL_RULE  which rule gave NEW_DIST and CHANNEL: 'company x DIST_CH', 'company', 'DIST_CH default'
--   N_HOLDERS     distinct CLEAN_IDs holding the ZIP_CODE x DIST_CH in territories (0 = the TX/NY block, Q10; 2 = shared)
-- An appended row is OPP_MAPPED (23) without its dropped rows, with the CRD's CBD_ID from CRD_MATCH, summed to
-- ZIP_CODE x DIST_CH x CBD_ID x PRODUCT_V2; MM_OPP = SUM(OPP); a key that sums to 0 is left out.  FISCAL_YR, the
-- sales amounts and the address IDs are NULL.  Like firm_1's opportunity rows: TERR_WHOLESALER and
-- SALES_WHOLESALER are NULL, both CLEAN_NAME columns carry the holder's name, both TERRITORY_ID columns the
-- holder's CLEAN_ID, both HAS_TERRITORY flags are 1 (0 with no holder).
-- Run 23 first.  Run statement 1, then 2 (checks: every MUST_BE_ZERO row must be 0), then 3.

-- Statement 1.  The table.
CREATE OR REPLACE TABLE ssdb_integration.lr_strategy.UNION_OPP AS
WITH
k AS (SELECT * FROM ssdb_integration.lr_strategy.synthetic_key),
s1 AS (SELECT VALUE AS V FROM k WHERE KIND = 'SOURCE' AND CODE = 'firm_1'),
s2 AS (SELECT VALUE AS V FROM k WHERE KIND = 'SOURCE' AND CODE = 'firm_2'),
a AS (
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
SELECT u.*, CAST(NULL AS BOOLEAN) AS OPP_FILE, CAST(NULL AS VARCHAR) AS CBD_METHOD,
       CAST(NULL AS VARCHAR) AS CHANNEL_RULE, CAST(NULL AS BIGINT) AS N_HOLDERS
FROM ssdb_integration.lr_strategy.data_withnewchannel_union_w_joinkeys u
UNION ALL BY NAME     -- the columns not named below are NULL on appended rows
SELECT b.SRC AS SOURCE, b.CBD_ID, b.FIRM, b.PARENT, b.DIST_CH, b.NEW_DIST, b.CHANNEL, b.STATE,
       b.ZIP_CODE, b.PRODUCT_V2, b.MM_OPP,
       b.HOLDER_NAME AS TERR_WHOLESALER_CLEAN_NAME, b.HOLDER_NAME AS SALES_WHOLESALER_CLEAN_NAME,
       b.HOLDER_ID AS SALES_WHOLESALER_TERRITORY_ID, b.HOLDER_ID AS TERRITORY_WHOLESALER_TERRITORY_ID,
       CASE WHEN b.N_HOLDERS > 0 THEN 1 ELSE 0 END AS SALES_WHOLESALER_HAS_TERRITORY,
       CASE WHEN b.N_HOLDERS > 0 THEN 1 ELSE 0 END AS TERRITORY_WHOLESALER_HAS_TERRITORY,
       TRUE AS OPP_FILE, b.CBD_METHOD, b.CHANNEL_RULE, b.N_HOLDERS
FROM b;

-- Statement 2.  Checks.
WITH
k AS (SELECT * FROM ssdb_integration.lr_strategy.synthetic_key),
s1 AS (SELECT VALUE AS V FROM k WHERE KIND = 'SOURCE' AND CODE = 'firm_1'),
d AS (SELECT NUM AS D FROM k WHERE KIND = 'divisor' AND VALUE = 'MM_OPP'),
ap AS (SELECT * FROM ssdb_integration.lr_strategy.UNION_OPP WHERE OPP_FILE),
ot AS (SELECT SUM(MM_OPP) AS O FROM ap),
g AS (               -- the appended rows by each lineage column
  SELECT 'CHANNEL_RULE' AS DIM, CHANNEL_RULE AS V, MM_OPP FROM ap
  UNION ALL SELECT 'CBD_METHOD', CBD_METHOD, MM_OPP FROM ap
  UNION ALL SELECT 'N_HOLDERS', CAST(N_HOLDERS AS VARCHAR), MM_OPP FROM ap)
SELECT 'union rows in UNION_OPP minus the source union' AS CHECK_NAME,
       (SELECT COUNT(*) FROM ssdb_integration.lr_strategy.UNION_OPP WHERE OPP_FILE IS NULL)
     - (SELECT COUNT(*) FROM ssdb_integration.lr_strategy.data_withnewchannel_union_w_joinkeys) AS VALUE, TRUE AS MUST_BE_ZERO
UNION ALL SELECT 'source union rows not found unchanged in UNION_OPP',
       (SELECT COUNT(*) FROM (SELECT * FROM ssdb_integration.lr_strategy.data_withnewchannel_union_w_joinkeys
                              EXCEPT
                              SELECT * EXCLUDE (OPP_FILE, CBD_METHOD, CHANNEL_RULE, N_HOLDERS)
                              FROM ssdb_integration.lr_strategy.UNION_OPP WHERE OPP_FILE IS NULL) x), TRUE
UNION ALL SELECT 'firm_2 OPP after drops differs from appended MM_OPP by more than 0.001 x divisor (1 = yes)',
       (SELECT CASE WHEN ABS(COALESCE((SELECT SUM(OPP) FROM ssdb_integration.lr_strategy.OPP_MAPPED WHERE DROP_REASON IS NULL), 0)
                           - COALESCE((SELECT O FROM ot), 0)) > 0.001 * d.D THEN 1 ELSE 0 END FROM d), TRUE
UNION ALL SELECT 'appended rows with NULL DIST_CH, PRODUCT_V2, CHANNEL or NEW_DIST',
       (SELECT COUNT(*) FROM ap WHERE DIST_CH IS NULL OR PRODUCT_V2 IS NULL OR CHANNEL IS NULL OR NEW_DIST IS NULL), TRUE
UNION ALL SELECT 'CBD_IDs with 2+ FIRM in one SOURCE',
       (SELECT COUNT(*) FROM (SELECT CBD_ID, SOURCE FROM ssdb_integration.lr_strategy.data_withnewchannel_union_w_joinkeys
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
UNION ALL SELECT 'appended rows by ' || DIM || ': ' || COALESCE(V, 'NULL'), COUNT(*), FALSE FROM g GROUP BY DIM, V
UNION ALL SELECT 'appended percent of MM_OPP by ' || DIM || ': ' || COALESCE(V, 'NULL'),
       ROUND(100 * SUM(MM_OPP) / MAX(ot.O), 1), FALSE FROM g CROSS JOIN ot GROUP BY DIM, V
UNION ALL SELECT 'appended MM_OPP in coded units', ROUND((SELECT O FROM ot) / (SELECT D FROM d), 1), FALSE
UNION ALL SELECT 'firm_1 MM_OPP in coded units',
       ROUND((SELECT SUM(u.MM_OPP) FROM ssdb_integration.lr_strategy.data_withnewchannel_union_w_joinkeys u
              JOIN s1 ON u.SOURCE = s1.V) / (SELECT D FROM d), 1), FALSE
ORDER BY MUST_BE_ZERO DESC, CHECK_NAME;

-- Statement 3.  Appended firm_2 MM_OPP by DIST_CH x NEW_DIST x CHANNEL, next to firm_2's share of positive sales
-- in the same cell (as the firm_1 table in DATASET_LOG.md, 2026-10-21).
WITH
s2 AS (SELECT VALUE AS V FROM ssdb_integration.lr_strategy.synthetic_key WHERE KIND = 'SOURCE' AND CODE = 'firm_2'),
o AS (SELECT DIST_CH, NEW_DIST, CHANNEL, COUNT(*) AS ROWS_APPENDED, COUNT(DISTINCT CBD_ID) AS CBD_IDS, SUM(MM_OPP) AS MM_OPP
      FROM ssdb_integration.lr_strategy.UNION_OPP WHERE OPP_FILE GROUP BY DIST_CH, NEW_DIST, CHANNEL),
s AS (SELECT u.DIST_CH, u.NEW_DIST, u.CHANNEL, SUM(CASE WHEN u.ACTUAL_SALES_AMOUNT > 0 THEN u.ACTUAL_SALES_AMOUNT END) AS SALES
      FROM ssdb_integration.lr_strategy.data_withnewchannel_union_w_joinkeys u JOIN s2 ON u.SOURCE = s2.V
      GROUP BY u.DIST_CH, u.NEW_DIST, u.CHANNEL)
SELECT COALESCE(o.DIST_CH, s.DIST_CH) AS DIST_CH, COALESCE(o.NEW_DIST, s.NEW_DIST) AS NEW_DIST,
       COALESCE(o.CHANNEL, s.CHANNEL) AS CHANNEL,
       o.ROWS_APPENDED, o.CBD_IDS,
       ROUND(100 * o.MM_OPP / SUM(o.MM_OPP) OVER (), 2) AS PCT_OF_FIRM_2_MM_OPP,
       ROUND(100 * s.SALES / SUM(s.SALES) OVER (), 2) AS PCT_OF_FIRM_2_SALES
FROM o
FULL OUTER JOIN s ON s.DIST_CH IS NOT DISTINCT FROM o.DIST_CH AND s.NEW_DIST IS NOT DISTINCT FROM o.NEW_DIST
                 AND s.CHANNEL IS NOT DISTINCT FROM o.CHANNEL
ORDER BY PCT_OF_FIRM_2_MM_OPP DESC NULLS LAST, PCT_OF_FIRM_2_SALES DESC NULLS LAST;
