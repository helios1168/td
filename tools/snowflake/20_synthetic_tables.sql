-- Coded copies of the two source tables, for ZIP_CODE- and territory-level work outside work:
-- ssdb_integration.lr_strategy.synthetic_union and synthetic_territories.  Their rows are the real rows
-- with every name, ID and amount replaced (not generated data).  Same columns, same rows, same
-- relationships, so 15-19 run on them unchanged (point them at the synthetic tables).
-- Kept as is: ZIP_CODE, STATE, FISCAL_YR, CHANNEL (target), the two HAS_TERRITORY flags.
-- Coded (one code per distinct real value, so every join and match survives):
--   SOURCE                                  -> firm_1, firm_2 (SOURCE order, as in 13, 16 and 19)
--   DIST_CH, territories.CHANNEL            -> D1_01, D1_02, ... (as in 19)
--   NEW_DIST                                -> N1_01, ...
--   PRODUCT_V2                              -> PR01, ... (as in 19)
--   every person ID (CLEAN_ID, SALES_ and TERRITORY_WHOLESALER_TERRITORY_ID) -> W00001, ... one space
--   every name (NAME, CLEAN_NAME, the four *WHOLESALER* name columns)          -> M00001, ... one space
--   FIRM and PARENT -> P00001, ... one space (a FIRM that is also a PARENT keeps one code)
--   the two ADDRESS_IDs -> A00001, ...;  CBD_ID -> C00001, ...
-- People, names, addresses, FIRM, PARENT and CBD_ID are numbered in random order.
-- Amounts: MM_OPP / the median ZIP_CODE x CHANNEL MM_OPP; ACTUAL_SALES_AMOUNT and SALES_AMOUNT / the
-- median ZIP_CODE x CHANNEL positive sales.  Every share, split and comparison stays exact; the dollar
-- level and the sales-to-MM_OPP level are hidden.
-- Still identifying: a person's set of ZIP_CODEs, to anyone who knows the territory map.
-- The key (real value -> code, and the two divisors) is ssdb_integration.lr_strategy.synthetic_key.  It
-- never leaves work; it maps results from outside back to real values.
-- Run statements 1-4 in order; every MUST_BE_ZERO row of 4 must be 0.  Then download 5 and 6 as CSV.

-- Statement 1.  The key.
CREATE OR REPLACE TABLE ssdb_integration.lr_strategy.synthetic_key AS
WITH
src AS (
  SELECT SOURCE, DENSE_RANK() OVER (ORDER BY SOURCE) AS R
  FROM (SELECT SOURCE FROM ssdb_integration.lr_strategy.data_withnewchannel_union_w_joinkeys
        UNION SELECT SOURCE FROM ssdb_integration.lr_strategy.territories) x
  WHERE SOURCE IS NOT NULL),
dv AS (              -- every DIST_CH value of either table, with its rows in each
  SELECT SOURCE, V, SUM(UN) AS UN, SUM(TN) AS TN
  FROM (SELECT SOURCE, DIST_CH AS V, COUNT(*) AS UN, 0 AS TN
        FROM ssdb_integration.lr_strategy.data_withnewchannel_union_w_joinkeys GROUP BY SOURCE, DIST_CH
        UNION ALL
        SELECT SOURCE, CHANNEL, 0, COUNT(*) FROM ssdb_integration.lr_strategy.territories GROUP BY SOURCE, CHANNEL) x
  WHERE V IS NOT NULL
  GROUP BY SOURCE, V),
nd AS (
  SELECT SOURCE, NEW_DIST AS V, COUNT(*) AS N
  FROM ssdb_integration.lr_strategy.data_withnewchannel_union_w_joinkeys
  WHERE NEW_DIST IS NOT NULL GROUP BY SOURCE, NEW_DIST),
pv AS (
  SELECT PRODUCT_V2 AS V, COUNT(*) AS N
  FROM ssdb_integration.lr_strategy.data_withnewchannel_union_w_joinkeys
  WHERE PRODUCT_V2 IS NOT NULL GROUP BY PRODUCT_V2),
vals AS (            -- the randomly numbered kinds
  SELECT 'person' AS KIND, SALES_WHOLESALER_TERRITORY_ID AS V FROM ssdb_integration.lr_strategy.data_withnewchannel_union_w_joinkeys
  UNION SELECT 'person', TERRITORY_WHOLESALER_TERRITORY_ID FROM ssdb_integration.lr_strategy.data_withnewchannel_union_w_joinkeys
  UNION SELECT 'person', CLEAN_ID FROM ssdb_integration.lr_strategy.territories
  UNION SELECT 'name', TERR_WHOLESALER FROM ssdb_integration.lr_strategy.data_withnewchannel_union_w_joinkeys
  UNION SELECT 'name', SALES_WHOLESALER FROM ssdb_integration.lr_strategy.data_withnewchannel_union_w_joinkeys
  UNION SELECT 'name', TERR_WHOLESALER_CLEAN_NAME FROM ssdb_integration.lr_strategy.data_withnewchannel_union_w_joinkeys
  UNION SELECT 'name', SALES_WHOLESALER_CLEAN_NAME FROM ssdb_integration.lr_strategy.data_withnewchannel_union_w_joinkeys
  UNION SELECT 'name', NAME FROM ssdb_integration.lr_strategy.territories
  UNION SELECT 'name', CLEAN_NAME FROM ssdb_integration.lr_strategy.territories
  UNION SELECT 'address', SALES_WHOLESALER_ADDRESS_ID FROM ssdb_integration.lr_strategy.data_withnewchannel_union_w_joinkeys
  UNION SELECT 'address', TERRITORY_WHOLESALER_ADDRESS_ID FROM ssdb_integration.lr_strategy.data_withnewchannel_union_w_joinkeys
  UNION SELECT 'FIRM', FIRM FROM ssdb_integration.lr_strategy.data_withnewchannel_union_w_joinkeys
  UNION SELECT 'FIRM', PARENT FROM ssdb_integration.lr_strategy.data_withnewchannel_union_w_joinkeys
  UNION SELECT 'CBD_ID', CBD_ID FROM ssdb_integration.lr_strategy.data_withnewchannel_union_w_joinkeys),
rnd AS (
  SELECT KIND, V, ROW_NUMBER() OVER (PARTITION BY KIND ORDER BY RANDOM()) AS R
  FROM vals WHERE V IS NOT NULL),
opp_cell AS (
  SELECT ZIP_CODE, CHANNEL, SUM(MM_OPP) AS X
  FROM ssdb_integration.lr_strategy.data_withnewchannel_union_w_joinkeys
  WHERE COALESCE(MM_OPP, 0) <> 0 GROUP BY ZIP_CODE, CHANNEL),
sales_cell AS (
  SELECT SOURCE, ZIP_CODE, CHANNEL, SUM(ACTUAL_SALES_AMOUNT) AS X
  FROM ssdb_integration.lr_strategy.data_withnewchannel_union_w_joinkeys
  WHERE ACTUAL_SALES_AMOUNT > 0 GROUP BY SOURCE, ZIP_CODE, CHANNEL)
SELECT 'SOURCE' AS KIND, CAST(NULL AS VARCHAR) AS SOURCE, SOURCE AS VALUE,
       'firm_' || CAST(R AS VARCHAR) AS CODE, CAST(NULL AS DOUBLE) AS NUM
FROM src
UNION ALL
SELECT 'DIST_CH', d.SOURCE, d.V,
       'D' || CAST(s.R AS VARCHAR) || '_'
           || LPAD(CAST(ROW_NUMBER() OVER (PARTITION BY d.SOURCE ORDER BY d.UN DESC, d.TN DESC, SHA2(d.V)) AS VARCHAR), 2, '0'),
       NULL
FROM dv d JOIN src s ON s.SOURCE = d.SOURCE
UNION ALL
SELECT 'NEW_DIST', n.SOURCE, n.V,
       'N' || CAST(s.R AS VARCHAR) || '_'
           || LPAD(CAST(ROW_NUMBER() OVER (PARTITION BY n.SOURCE ORDER BY n.N DESC, SHA2(n.V)) AS VARCHAR), 2, '0'),
       NULL
FROM nd n JOIN src s ON s.SOURCE = n.SOURCE
UNION ALL
SELECT 'PRODUCT_V2', NULL, V, 'PR' || LPAD(CAST(ROW_NUMBER() OVER (ORDER BY N DESC, SHA2(V)) AS VARCHAR), 2, '0'), NULL
FROM pv
UNION ALL
SELECT KIND, NULL, V,
       CASE KIND WHEN 'person' THEN 'W' WHEN 'name' THEN 'M' WHEN 'address' THEN 'A' WHEN 'FIRM' THEN 'P' ELSE 'C' END
         || LPAD(CAST(R AS VARCHAR), 5, '0'),
       NULL
FROM rnd
UNION ALL
SELECT 'divisor', NULL, 'MM_OPP', NULL, MEDIAN(X) FROM opp_cell WHERE X > 0
UNION ALL
SELECT 'divisor', NULL, 'sales', NULL, MEDIAN(X) FROM sales_cell;

-- Statement 2.  The synthetic union table.
CREATE OR REPLACE TABLE ssdb_integration.lr_strategy.synthetic_union AS
WITH
k AS (SELECT * FROM ssdb_integration.lr_strategy.synthetic_key),
dvs AS (
  SELECT MAX(CASE WHEN VALUE = 'MM_OPP' THEN NUM END) AS D_OPP,
         MAX(CASE WHEN VALUE = 'sales' THEN NUM END) AS D_SALES
  FROM k WHERE KIND = 'divisor')
SELECT u.FISCAL_YR,
       s.CODE   AS SOURCE,
       n1.CODE  AS TERR_WHOLESALER,
       n2.CODE  AS SALES_WHOLESALER,
       n3.CODE  AS TERR_WHOLESALER_CLEAN_NAME,
       n4.CODE  AS SALES_WHOLESALER_CLEAN_NAME,
       cb.CODE  AS CBD_ID,
       fi.CODE  AS FIRM,
       pa.CODE  AS PARENT,
       dc.CODE  AS DIST_CH,
       nd.CODE  AS NEW_DIST,
       u.CHANNEL,
       u.STATE,
       u.ZIP_CODE,
       pr.CODE  AS PRODUCT_V2,
       u.MM_OPP / v.D_OPP                AS MM_OPP,
       u.ACTUAL_SALES_AMOUNT / v.D_SALES AS ACTUAL_SALES_AMOUNT,
       u.SALES_AMOUNT / v.D_SALES        AS SALES_AMOUNT,
       p1.CODE  AS SALES_WHOLESALER_TERRITORY_ID,
       a1.CODE  AS SALES_WHOLESALER_ADDRESS_ID,
       p2.CODE  AS TERRITORY_WHOLESALER_TERRITORY_ID,
       a2.CODE  AS TERRITORY_WHOLESALER_ADDRESS_ID,
       u.SALES_WHOLESALER_HAS_TERRITORY,
       u.TERRITORY_WHOLESALER_HAS_TERRITORY
FROM ssdb_integration.lr_strategy.data_withnewchannel_union_w_joinkeys u
CROSS JOIN dvs v
LEFT JOIN k s  ON s.KIND  = 'SOURCE'     AND s.VALUE  = u.SOURCE
LEFT JOIN k n1 ON n1.KIND = 'name'       AND n1.VALUE = u.TERR_WHOLESALER
LEFT JOIN k n2 ON n2.KIND = 'name'       AND n2.VALUE = u.SALES_WHOLESALER
LEFT JOIN k n3 ON n3.KIND = 'name'       AND n3.VALUE = u.TERR_WHOLESALER_CLEAN_NAME
LEFT JOIN k n4 ON n4.KIND = 'name'       AND n4.VALUE = u.SALES_WHOLESALER_CLEAN_NAME
LEFT JOIN k cb ON cb.KIND = 'CBD_ID'     AND cb.VALUE = u.CBD_ID
LEFT JOIN k fi ON fi.KIND = 'FIRM'       AND fi.VALUE = u.FIRM
LEFT JOIN k pa ON pa.KIND = 'FIRM'       AND pa.VALUE = u.PARENT
LEFT JOIN k dc ON dc.KIND = 'DIST_CH'    AND dc.SOURCE = u.SOURCE AND dc.VALUE = u.DIST_CH
LEFT JOIN k nd ON nd.KIND = 'NEW_DIST'   AND nd.SOURCE = u.SOURCE AND nd.VALUE = u.NEW_DIST
LEFT JOIN k pr ON pr.KIND = 'PRODUCT_V2' AND pr.VALUE = u.PRODUCT_V2
LEFT JOIN k p1 ON p1.KIND = 'person'     AND p1.VALUE = u.SALES_WHOLESALER_TERRITORY_ID
LEFT JOIN k a1 ON a1.KIND = 'address'    AND a1.VALUE = u.SALES_WHOLESALER_ADDRESS_ID
LEFT JOIN k p2 ON p2.KIND = 'person'     AND p2.VALUE = u.TERRITORY_WHOLESALER_TERRITORY_ID
LEFT JOIN k a2 ON a2.KIND = 'address'    AND a2.VALUE = u.TERRITORY_WHOLESALER_ADDRESS_ID;

-- Statement 3.  The synthetic territories table.
CREATE OR REPLACE TABLE ssdb_integration.lr_strategy.synthetic_territories AS
SELECT s.CODE AS SOURCE, nm.CODE AS NAME, t.ZIP_CODE, t.STATE, dc.CODE AS CHANNEL,
       cn.CODE AS CLEAN_NAME, p.CODE AS CLEAN_ID
FROM ssdb_integration.lr_strategy.territories t
LEFT JOIN ssdb_integration.lr_strategy.synthetic_key s  ON s.KIND  = 'SOURCE'  AND s.VALUE  = t.SOURCE
LEFT JOIN ssdb_integration.lr_strategy.synthetic_key nm ON nm.KIND = 'name'    AND nm.VALUE = t.NAME
LEFT JOIN ssdb_integration.lr_strategy.synthetic_key dc ON dc.KIND = 'DIST_CH' AND dc.SOURCE = t.SOURCE AND dc.VALUE = t.CHANNEL
LEFT JOIN ssdb_integration.lr_strategy.synthetic_key cn ON cn.KIND = 'name'    AND cn.VALUE = t.CLEAN_NAME
LEFT JOIN ssdb_integration.lr_strategy.synthetic_key p  ON p.KIND  = 'person'  AND p.VALUE  = t.CLEAN_ID;

-- Statement 4.  Checks.  Every MUST_BE_ZERO row must be 0 before anything is downloaded.
WITH
real_vals AS (SELECT DISTINCT VALUE FROM ssdb_integration.lr_strategy.synthetic_key WHERE KIND <> 'divisor'),
synthetic_vals AS (     -- every coded value in the two synthetic tables
  SELECT SOURCE AS V FROM ssdb_integration.lr_strategy.synthetic_union
  UNION SELECT TERR_WHOLESALER FROM ssdb_integration.lr_strategy.synthetic_union
  UNION SELECT SALES_WHOLESALER FROM ssdb_integration.lr_strategy.synthetic_union
  UNION SELECT TERR_WHOLESALER_CLEAN_NAME FROM ssdb_integration.lr_strategy.synthetic_union
  UNION SELECT SALES_WHOLESALER_CLEAN_NAME FROM ssdb_integration.lr_strategy.synthetic_union
  UNION SELECT CBD_ID FROM ssdb_integration.lr_strategy.synthetic_union
  UNION SELECT FIRM FROM ssdb_integration.lr_strategy.synthetic_union
  UNION SELECT PARENT FROM ssdb_integration.lr_strategy.synthetic_union
  UNION SELECT DIST_CH FROM ssdb_integration.lr_strategy.synthetic_union
  UNION SELECT NEW_DIST FROM ssdb_integration.lr_strategy.synthetic_union
  UNION SELECT PRODUCT_V2 FROM ssdb_integration.lr_strategy.synthetic_union
  UNION SELECT SALES_WHOLESALER_TERRITORY_ID FROM ssdb_integration.lr_strategy.synthetic_union
  UNION SELECT SALES_WHOLESALER_ADDRESS_ID FROM ssdb_integration.lr_strategy.synthetic_union
  UNION SELECT TERRITORY_WHOLESALER_TERRITORY_ID FROM ssdb_integration.lr_strategy.synthetic_union
  UNION SELECT TERRITORY_WHOLESALER_ADDRESS_ID FROM ssdb_integration.lr_strategy.synthetic_union
  UNION SELECT SOURCE FROM ssdb_integration.lr_strategy.synthetic_territories
  UNION SELECT NAME FROM ssdb_integration.lr_strategy.synthetic_territories
  UNION SELECT CHANNEL FROM ssdb_integration.lr_strategy.synthetic_territories
  UNION SELECT CLEAN_NAME FROM ssdb_integration.lr_strategy.synthetic_territories
  UNION SELECT CLEAN_ID FROM ssdb_integration.lr_strategy.synthetic_territories)
SELECT 'real coded values left in the synthetic tables' AS CHECK_NAME,
       (SELECT COUNT(*) FROM synthetic_vals m JOIN real_vals r ON r.VALUE = m.V) AS VALUE, 1 AS MUST_BE_ZERO
UNION ALL SELECT 'union rows: real minus synthetic',
       (SELECT COUNT(*) FROM ssdb_integration.lr_strategy.data_withnewchannel_union_w_joinkeys)
     - (SELECT COUNT(*) FROM ssdb_integration.lr_strategy.synthetic_union), 1
UNION ALL SELECT 'territories rows: real minus synthetic',
       (SELECT COUNT(*) FROM ssdb_integration.lr_strategy.territories)
     - (SELECT COUNT(*) FROM ssdb_integration.lr_strategy.synthetic_territories), 1
UNION ALL SELECT 'territories values with no code (SOURCE, NAME, CHANNEL, CLEAN_NAME, CLEAN_ID)',
       (SELECT COUNT_IF(t.SOURCE IS NOT NULL) + COUNT_IF(t.NAME IS NOT NULL) + COUNT_IF(t.CHANNEL IS NOT NULL)
             + COUNT_IF(t.CLEAN_NAME IS NOT NULL) + COUNT_IF(t.CLEAN_ID IS NOT NULL)
        FROM ssdb_integration.lr_strategy.territories t) -
       (SELECT COUNT_IF(SOURCE IS NOT NULL) + COUNT_IF(NAME IS NOT NULL) + COUNT_IF(CHANNEL IS NOT NULL)
             + COUNT_IF(CLEAN_NAME IS NOT NULL) + COUNT_IF(CLEAN_ID IS NOT NULL)
        FROM ssdb_integration.lr_strategy.synthetic_territories), 1
UNION ALL SELECT 'union values with no code (non-NULL in, NULL out)',
       (SELECT COUNT_IF(SOURCE IS NOT NULL) + COUNT_IF(TERR_WHOLESALER IS NOT NULL) + COUNT_IF(SALES_WHOLESALER IS NOT NULL)
             + COUNT_IF(TERR_WHOLESALER_CLEAN_NAME IS NOT NULL) + COUNT_IF(SALES_WHOLESALER_CLEAN_NAME IS NOT NULL)
             + COUNT_IF(CBD_ID IS NOT NULL) + COUNT_IF(FIRM IS NOT NULL) + COUNT_IF(PARENT IS NOT NULL) + COUNT_IF(DIST_CH IS NOT NULL)
             + COUNT_IF(NEW_DIST IS NOT NULL) + COUNT_IF(PRODUCT_V2 IS NOT NULL)
             + COUNT_IF(SALES_WHOLESALER_TERRITORY_ID IS NOT NULL) + COUNT_IF(SALES_WHOLESALER_ADDRESS_ID IS NOT NULL)
             + COUNT_IF(TERRITORY_WHOLESALER_TERRITORY_ID IS NOT NULL) + COUNT_IF(TERRITORY_WHOLESALER_ADDRESS_ID IS NOT NULL)
        FROM ssdb_integration.lr_strategy.data_withnewchannel_union_w_joinkeys) -
       (SELECT COUNT_IF(SOURCE IS NOT NULL) + COUNT_IF(TERR_WHOLESALER IS NOT NULL) + COUNT_IF(SALES_WHOLESALER IS NOT NULL)
             + COUNT_IF(TERR_WHOLESALER_CLEAN_NAME IS NOT NULL) + COUNT_IF(SALES_WHOLESALER_CLEAN_NAME IS NOT NULL)
             + COUNT_IF(CBD_ID IS NOT NULL) + COUNT_IF(FIRM IS NOT NULL) + COUNT_IF(PARENT IS NOT NULL) + COUNT_IF(DIST_CH IS NOT NULL)
             + COUNT_IF(NEW_DIST IS NOT NULL) + COUNT_IF(PRODUCT_V2 IS NOT NULL)
             + COUNT_IF(SALES_WHOLESALER_TERRITORY_ID IS NOT NULL) + COUNT_IF(SALES_WHOLESALER_ADDRESS_ID IS NOT NULL)
             + COUNT_IF(TERRITORY_WHOLESALER_TERRITORY_ID IS NOT NULL) + COUNT_IF(TERRITORY_WHOLESALER_ADDRESS_ID IS NOT NULL)
        FROM ssdb_integration.lr_strategy.synthetic_union), 1
UNION ALL SELECT 'people: real IDs minus codes',
       (SELECT COUNT(*) FROM ssdb_integration.lr_strategy.synthetic_key WHERE KIND = 'person')
     - (SELECT COUNT(*) FROM (SELECT SALES_WHOLESALER_TERRITORY_ID AS V FROM ssdb_integration.lr_strategy.synthetic_union
                              UNION SELECT TERRITORY_WHOLESALER_TERRITORY_ID FROM ssdb_integration.lr_strategy.synthetic_union
                              UNION SELECT CLEAN_ID FROM ssdb_integration.lr_strategy.synthetic_territories) x WHERE V IS NOT NULL), 1
UNION ALL SELECT 'codes used twice within a kind (and SOURCE)',
       (SELECT COUNT(*) FROM (SELECT KIND, SOURCE, CODE FROM ssdb_integration.lr_strategy.synthetic_key WHERE KIND <> 'divisor'
                              GROUP BY KIND, SOURCE, CODE HAVING COUNT(*) > 1) x), 1
UNION ALL SELECT 'MM_OPP total: synthetic x divisor / real (should be 1)',
       (SELECT SUM(MM_OPP) FROM ssdb_integration.lr_strategy.synthetic_union)
     * (SELECT NUM FROM ssdb_integration.lr_strategy.synthetic_key WHERE KIND = 'divisor' AND VALUE = 'MM_OPP')
     / NULLIF((SELECT SUM(MM_OPP) FROM ssdb_integration.lr_strategy.data_withnewchannel_union_w_joinkeys), 0), 0
UNION ALL SELECT 'ACTUAL_SALES_AMOUNT total: synthetic x divisor / real (should be 1)',
       (SELECT SUM(ACTUAL_SALES_AMOUNT) FROM ssdb_integration.lr_strategy.synthetic_union)
     * (SELECT NUM FROM ssdb_integration.lr_strategy.synthetic_key WHERE KIND = 'divisor' AND VALUE = 'sales')
     / NULLIF((SELECT SUM(ACTUAL_SALES_AMOUNT) FROM ssdb_integration.lr_strategy.data_withnewchannel_union_w_joinkeys), 0), 0
ORDER BY MUST_BE_ZERO DESC, CHECK_NAME;

-- Statement 5.  Download as CSV: the synthetic union table.
SELECT * FROM ssdb_integration.lr_strategy.synthetic_union;

-- Statement 6.  Download as CSV: the synthetic territories table.
SELECT * FROM ssdb_integration.lr_strategy.synthetic_territories;
