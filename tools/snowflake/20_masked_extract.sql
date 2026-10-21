-- Masked copies of the two source tables, for ZIP_CODE- and territory-level work outside work, with
-- CTEs only (no tables are created).  Same columns, same rows, same relationships, so 15-19 run on them
-- unchanged (point them at the masked files).  Kept as is: ZIP_CODE, STATE, FISCAL_YR, CHANNEL (target),
-- the two HAS_TERRITORY flags.  Coded (one code per distinct real value, so every join and match survives):
--   SOURCE                                  -> firm_1, firm_2 (SOURCE order, as in 13, 16 and 19)
--   DIST_CH, territories.CHANNEL            -> D1_01, D1_02, ... (as in 19)
--   NEW_DIST                                -> N1_01, ...
--   PRODUCT_V2                              -> PR01, ... (as in 19)
--   every person ID (CLEAN_ID, SALES_ and TERRITORY_WHOLESALER_TERRITORY_ID) -> W00001, ... one space
--   every name (NAME, CLEAN_NAME, the four *WHOLESALER* name columns)          -> M00001, ... one space
--   the two ADDRESS_IDs -> A00001, ...;  FIRM -> P00001, ...;  CBD_ID -> C00001, ...
-- People, names, addresses, FIRM and CBD_ID are numbered in the order of a salted hash: the same salt
-- and the same data give the same codes in every query and every run; without the salt the order says
-- nothing.  Amounts: MM_OPP / the median ZIP_CODE x CHANNEL MM_OPP; ACTUAL_SALES_AMOUNT and SALES_AMOUNT
-- / the median ZIP_CODE x CHANNEL positive sales.  Every share, split and comparison stays exact; the
-- dollar level and the sales-to-MM_OPP level are hidden.
-- Still identifying: a person's set of ZIP_CODEs, to anyone who knows the territory map.
--
-- Four queries; the block from "params" to "mt" is the same in all four.
--   1. Find-and-replace <SALT> with one long random string, in all four queries at once.  Never save it
--      in a file; keep it (e.g. in a password manager) to rebuild the key later.
--   2. Run query 4 (checks): every MUST_BE_ZERO row must be 0.
--   3. Run queries 1 and 2 and download each as CSV: these may leave work.
--   4. Query 3 is the key (real value -> code, and the two divisors).  It never leaves work.  Run it
--      when you need to map results back; same salt and same data give the same key.
-- Run all four on the same day: if the source tables change, the codes change.

-- Query 1.  Download as CSV: the masked union table.
WITH
params AS (SELECT '<SALT>' AS SALT),
src AS (             -- SOURCE -> its number
  SELECT SOURCE, DENSE_RANK() OVER (ORDER BY SOURCE) AS R
  FROM (SELECT SOURCE FROM ssdb_integration.lr_strategy.data_withnewchannel_union_w_joinkeys UNION SELECT SOURCE FROM ssdb_integration.lr_strategy.territories) x
  WHERE SOURCE IS NOT NULL),
dv AS (              -- every DIST_CH value of either table, with its rows in each
  SELECT SOURCE, V, SUM(UN) AS UN, SUM(TN) AS TN
  FROM (SELECT SOURCE, DIST_CH AS V, COUNT(*) AS UN, 0 AS TN FROM ssdb_integration.lr_strategy.data_withnewchannel_union_w_joinkeys GROUP BY SOURCE, DIST_CH
        UNION ALL
        SELECT SOURCE, CHANNEL, 0, COUNT(*) FROM ssdb_integration.lr_strategy.territories GROUP BY SOURCE, CHANNEL) x
  WHERE V IS NOT NULL
  GROUP BY SOURCE, V),
nd AS (SELECT SOURCE, NEW_DIST AS V, COUNT(*) AS N FROM ssdb_integration.lr_strategy.data_withnewchannel_union_w_joinkeys WHERE NEW_DIST IS NOT NULL GROUP BY SOURCE, NEW_DIST),
pv AS (SELECT PRODUCT_V2 AS V, COUNT(*) AS N FROM ssdb_integration.lr_strategy.data_withnewchannel_union_w_joinkeys WHERE PRODUCT_V2 IS NOT NULL GROUP BY PRODUCT_V2),
vals AS (            -- the kinds numbered by salted hash
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
  UNION SELECT 'CBD_ID', CBD_ID FROM ssdb_integration.lr_strategy.data_withnewchannel_union_w_joinkeys),
k AS (               -- the key: real value -> code
  SELECT 'SOURCE' AS KIND, CAST(NULL AS VARCHAR) AS SOURCE, SOURCE AS VALUE, 'firm_' || CAST(R AS VARCHAR) AS CODE
  FROM src
  UNION ALL
  SELECT 'DIST_CH', d.SOURCE, d.V,
         'D' || CAST(s.R AS VARCHAR) || '_'
             || LPAD(CAST(ROW_NUMBER() OVER (PARTITION BY d.SOURCE ORDER BY d.UN DESC, d.TN DESC, SHA2(d.V)) AS VARCHAR), 2, '0')
  FROM dv d JOIN src s ON s.SOURCE = d.SOURCE
  UNION ALL
  SELECT 'NEW_DIST', n.SOURCE, n.V,
         'N' || CAST(s.R AS VARCHAR) || '_'
             || LPAD(CAST(ROW_NUMBER() OVER (PARTITION BY n.SOURCE ORDER BY n.N DESC, SHA2(n.V)) AS VARCHAR), 2, '0')
  FROM nd n JOIN src s ON s.SOURCE = n.SOURCE
  UNION ALL
  SELECT 'PRODUCT_V2', NULL, V, 'PR' || LPAD(CAST(ROW_NUMBER() OVER (ORDER BY N DESC, SHA2(V)) AS VARCHAR), 2, '0')
  FROM pv
  UNION ALL
  SELECT v.KIND, NULL, v.V,
         CASE v.KIND WHEN 'person' THEN 'W' WHEN 'name' THEN 'M' WHEN 'address' THEN 'A' WHEN 'FIRM' THEN 'P' ELSE 'C' END
           || LPAD(CAST(ROW_NUMBER() OVER (PARTITION BY v.KIND ORDER BY SHA2(v.V || p.SALT)) AS VARCHAR), 5, '0')
  FROM vals v CROSS JOIN params p
  WHERE v.V IS NOT NULL),
dvs AS (             -- the two divisors
  SELECT (SELECT MEDIAN(X) FROM (SELECT SUM(MM_OPP) AS X FROM ssdb_integration.lr_strategy.data_withnewchannel_union_w_joinkeys
                                 WHERE COALESCE(MM_OPP, 0) <> 0 GROUP BY ZIP_CODE, CHANNEL) a WHERE X > 0) AS D_OPP,
         (SELECT MEDIAN(X) FROM (SELECT SUM(ACTUAL_SALES_AMOUNT) AS X FROM ssdb_integration.lr_strategy.data_withnewchannel_union_w_joinkeys
                                 WHERE ACTUAL_SALES_AMOUNT > 0 GROUP BY SOURCE, ZIP_CODE, CHANNEL) b) AS D_SALES),
mu AS (              -- the masked union table
  SELECT u.FISCAL_YR,
         s.CODE   AS SOURCE,
         n1.CODE  AS TERR_WHOLESALER,
         n2.CODE  AS SALES_WHOLESALER,
         n3.CODE  AS TERR_WHOLESALER_CLEAN_NAME,
         n4.CODE  AS SALES_WHOLESALER_CLEAN_NAME,
         cb.CODE  AS CBD_ID,
         fi.CODE  AS FIRM,
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
  LEFT JOIN k dc ON dc.KIND = 'DIST_CH'    AND dc.SOURCE = u.SOURCE AND dc.VALUE = u.DIST_CH
  LEFT JOIN k nd ON nd.KIND = 'NEW_DIST'   AND nd.SOURCE = u.SOURCE AND nd.VALUE = u.NEW_DIST
  LEFT JOIN k pr ON pr.KIND = 'PRODUCT_V2' AND pr.VALUE = u.PRODUCT_V2
  LEFT JOIN k p1 ON p1.KIND = 'person'     AND p1.VALUE = u.SALES_WHOLESALER_TERRITORY_ID
  LEFT JOIN k a1 ON a1.KIND = 'address'    AND a1.VALUE = u.SALES_WHOLESALER_ADDRESS_ID
  LEFT JOIN k p2 ON p2.KIND = 'person'     AND p2.VALUE = u.TERRITORY_WHOLESALER_TERRITORY_ID
  LEFT JOIN k a2 ON a2.KIND = 'address'    AND a2.VALUE = u.TERRITORY_WHOLESALER_ADDRESS_ID),
mt AS (              -- the masked territories table
  SELECT s.CODE AS SOURCE, nm.CODE AS NAME, t.ZIP_CODE, t.STATE, dc.CODE AS CHANNEL,
         cn.CODE AS CLEAN_NAME, p.CODE AS CLEAN_ID
  FROM ssdb_integration.lr_strategy.territories t
  LEFT JOIN k s  ON s.KIND  = 'SOURCE'  AND s.VALUE  = t.SOURCE
  LEFT JOIN k nm ON nm.KIND = 'name'    AND nm.VALUE = t.NAME
  LEFT JOIN k dc ON dc.KIND = 'DIST_CH' AND dc.SOURCE = t.SOURCE AND dc.VALUE = t.CHANNEL
  LEFT JOIN k cn ON cn.KIND = 'name'    AND cn.VALUE = t.CLEAN_NAME
  LEFT JOIN k p  ON p.KIND  = 'person'  AND p.VALUE  = t.CLEAN_ID)
SELECT * FROM mu;

-- Query 2.  Download as CSV: the masked territories table.
WITH
params AS (SELECT '<SALT>' AS SALT),
src AS (             -- SOURCE -> its number
  SELECT SOURCE, DENSE_RANK() OVER (ORDER BY SOURCE) AS R
  FROM (SELECT SOURCE FROM ssdb_integration.lr_strategy.data_withnewchannel_union_w_joinkeys UNION SELECT SOURCE FROM ssdb_integration.lr_strategy.territories) x
  WHERE SOURCE IS NOT NULL),
dv AS (              -- every DIST_CH value of either table, with its rows in each
  SELECT SOURCE, V, SUM(UN) AS UN, SUM(TN) AS TN
  FROM (SELECT SOURCE, DIST_CH AS V, COUNT(*) AS UN, 0 AS TN FROM ssdb_integration.lr_strategy.data_withnewchannel_union_w_joinkeys GROUP BY SOURCE, DIST_CH
        UNION ALL
        SELECT SOURCE, CHANNEL, 0, COUNT(*) FROM ssdb_integration.lr_strategy.territories GROUP BY SOURCE, CHANNEL) x
  WHERE V IS NOT NULL
  GROUP BY SOURCE, V),
nd AS (SELECT SOURCE, NEW_DIST AS V, COUNT(*) AS N FROM ssdb_integration.lr_strategy.data_withnewchannel_union_w_joinkeys WHERE NEW_DIST IS NOT NULL GROUP BY SOURCE, NEW_DIST),
pv AS (SELECT PRODUCT_V2 AS V, COUNT(*) AS N FROM ssdb_integration.lr_strategy.data_withnewchannel_union_w_joinkeys WHERE PRODUCT_V2 IS NOT NULL GROUP BY PRODUCT_V2),
vals AS (            -- the kinds numbered by salted hash
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
  UNION SELECT 'CBD_ID', CBD_ID FROM ssdb_integration.lr_strategy.data_withnewchannel_union_w_joinkeys),
k AS (               -- the key: real value -> code
  SELECT 'SOURCE' AS KIND, CAST(NULL AS VARCHAR) AS SOURCE, SOURCE AS VALUE, 'firm_' || CAST(R AS VARCHAR) AS CODE
  FROM src
  UNION ALL
  SELECT 'DIST_CH', d.SOURCE, d.V,
         'D' || CAST(s.R AS VARCHAR) || '_'
             || LPAD(CAST(ROW_NUMBER() OVER (PARTITION BY d.SOURCE ORDER BY d.UN DESC, d.TN DESC, SHA2(d.V)) AS VARCHAR), 2, '0')
  FROM dv d JOIN src s ON s.SOURCE = d.SOURCE
  UNION ALL
  SELECT 'NEW_DIST', n.SOURCE, n.V,
         'N' || CAST(s.R AS VARCHAR) || '_'
             || LPAD(CAST(ROW_NUMBER() OVER (PARTITION BY n.SOURCE ORDER BY n.N DESC, SHA2(n.V)) AS VARCHAR), 2, '0')
  FROM nd n JOIN src s ON s.SOURCE = n.SOURCE
  UNION ALL
  SELECT 'PRODUCT_V2', NULL, V, 'PR' || LPAD(CAST(ROW_NUMBER() OVER (ORDER BY N DESC, SHA2(V)) AS VARCHAR), 2, '0')
  FROM pv
  UNION ALL
  SELECT v.KIND, NULL, v.V,
         CASE v.KIND WHEN 'person' THEN 'W' WHEN 'name' THEN 'M' WHEN 'address' THEN 'A' WHEN 'FIRM' THEN 'P' ELSE 'C' END
           || LPAD(CAST(ROW_NUMBER() OVER (PARTITION BY v.KIND ORDER BY SHA2(v.V || p.SALT)) AS VARCHAR), 5, '0')
  FROM vals v CROSS JOIN params p
  WHERE v.V IS NOT NULL),
dvs AS (             -- the two divisors
  SELECT (SELECT MEDIAN(X) FROM (SELECT SUM(MM_OPP) AS X FROM ssdb_integration.lr_strategy.data_withnewchannel_union_w_joinkeys
                                 WHERE COALESCE(MM_OPP, 0) <> 0 GROUP BY ZIP_CODE, CHANNEL) a WHERE X > 0) AS D_OPP,
         (SELECT MEDIAN(X) FROM (SELECT SUM(ACTUAL_SALES_AMOUNT) AS X FROM ssdb_integration.lr_strategy.data_withnewchannel_union_w_joinkeys
                                 WHERE ACTUAL_SALES_AMOUNT > 0 GROUP BY SOURCE, ZIP_CODE, CHANNEL) b) AS D_SALES),
mu AS (              -- the masked union table
  SELECT u.FISCAL_YR,
         s.CODE   AS SOURCE,
         n1.CODE  AS TERR_WHOLESALER,
         n2.CODE  AS SALES_WHOLESALER,
         n3.CODE  AS TERR_WHOLESALER_CLEAN_NAME,
         n4.CODE  AS SALES_WHOLESALER_CLEAN_NAME,
         cb.CODE  AS CBD_ID,
         fi.CODE  AS FIRM,
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
  LEFT JOIN k dc ON dc.KIND = 'DIST_CH'    AND dc.SOURCE = u.SOURCE AND dc.VALUE = u.DIST_CH
  LEFT JOIN k nd ON nd.KIND = 'NEW_DIST'   AND nd.SOURCE = u.SOURCE AND nd.VALUE = u.NEW_DIST
  LEFT JOIN k pr ON pr.KIND = 'PRODUCT_V2' AND pr.VALUE = u.PRODUCT_V2
  LEFT JOIN k p1 ON p1.KIND = 'person'     AND p1.VALUE = u.SALES_WHOLESALER_TERRITORY_ID
  LEFT JOIN k a1 ON a1.KIND = 'address'    AND a1.VALUE = u.SALES_WHOLESALER_ADDRESS_ID
  LEFT JOIN k p2 ON p2.KIND = 'person'     AND p2.VALUE = u.TERRITORY_WHOLESALER_TERRITORY_ID
  LEFT JOIN k a2 ON a2.KIND = 'address'    AND a2.VALUE = u.TERRITORY_WHOLESALER_ADDRESS_ID),
mt AS (              -- the masked territories table
  SELECT s.CODE AS SOURCE, nm.CODE AS NAME, t.ZIP_CODE, t.STATE, dc.CODE AS CHANNEL,
         cn.CODE AS CLEAN_NAME, p.CODE AS CLEAN_ID
  FROM ssdb_integration.lr_strategy.territories t
  LEFT JOIN k s  ON s.KIND  = 'SOURCE'  AND s.VALUE  = t.SOURCE
  LEFT JOIN k nm ON nm.KIND = 'name'    AND nm.VALUE = t.NAME
  LEFT JOIN k dc ON dc.KIND = 'DIST_CH' AND dc.SOURCE = t.SOURCE AND dc.VALUE = t.CHANNEL
  LEFT JOIN k cn ON cn.KIND = 'name'    AND cn.VALUE = t.CLEAN_NAME
  LEFT JOIN k p  ON p.KIND  = 'person'  AND p.VALUE  = t.CLEAN_ID)
SELECT * FROM mt;

-- Query 3.  The key.  Never leaves work.
WITH
params AS (SELECT '<SALT>' AS SALT),
src AS (             -- SOURCE -> its number
  SELECT SOURCE, DENSE_RANK() OVER (ORDER BY SOURCE) AS R
  FROM (SELECT SOURCE FROM ssdb_integration.lr_strategy.data_withnewchannel_union_w_joinkeys UNION SELECT SOURCE FROM ssdb_integration.lr_strategy.territories) x
  WHERE SOURCE IS NOT NULL),
dv AS (              -- every DIST_CH value of either table, with its rows in each
  SELECT SOURCE, V, SUM(UN) AS UN, SUM(TN) AS TN
  FROM (SELECT SOURCE, DIST_CH AS V, COUNT(*) AS UN, 0 AS TN FROM ssdb_integration.lr_strategy.data_withnewchannel_union_w_joinkeys GROUP BY SOURCE, DIST_CH
        UNION ALL
        SELECT SOURCE, CHANNEL, 0, COUNT(*) FROM ssdb_integration.lr_strategy.territories GROUP BY SOURCE, CHANNEL) x
  WHERE V IS NOT NULL
  GROUP BY SOURCE, V),
nd AS (SELECT SOURCE, NEW_DIST AS V, COUNT(*) AS N FROM ssdb_integration.lr_strategy.data_withnewchannel_union_w_joinkeys WHERE NEW_DIST IS NOT NULL GROUP BY SOURCE, NEW_DIST),
pv AS (SELECT PRODUCT_V2 AS V, COUNT(*) AS N FROM ssdb_integration.lr_strategy.data_withnewchannel_union_w_joinkeys WHERE PRODUCT_V2 IS NOT NULL GROUP BY PRODUCT_V2),
vals AS (            -- the kinds numbered by salted hash
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
  UNION SELECT 'CBD_ID', CBD_ID FROM ssdb_integration.lr_strategy.data_withnewchannel_union_w_joinkeys),
k AS (               -- the key: real value -> code
  SELECT 'SOURCE' AS KIND, CAST(NULL AS VARCHAR) AS SOURCE, SOURCE AS VALUE, 'firm_' || CAST(R AS VARCHAR) AS CODE
  FROM src
  UNION ALL
  SELECT 'DIST_CH', d.SOURCE, d.V,
         'D' || CAST(s.R AS VARCHAR) || '_'
             || LPAD(CAST(ROW_NUMBER() OVER (PARTITION BY d.SOURCE ORDER BY d.UN DESC, d.TN DESC, SHA2(d.V)) AS VARCHAR), 2, '0')
  FROM dv d JOIN src s ON s.SOURCE = d.SOURCE
  UNION ALL
  SELECT 'NEW_DIST', n.SOURCE, n.V,
         'N' || CAST(s.R AS VARCHAR) || '_'
             || LPAD(CAST(ROW_NUMBER() OVER (PARTITION BY n.SOURCE ORDER BY n.N DESC, SHA2(n.V)) AS VARCHAR), 2, '0')
  FROM nd n JOIN src s ON s.SOURCE = n.SOURCE
  UNION ALL
  SELECT 'PRODUCT_V2', NULL, V, 'PR' || LPAD(CAST(ROW_NUMBER() OVER (ORDER BY N DESC, SHA2(V)) AS VARCHAR), 2, '0')
  FROM pv
  UNION ALL
  SELECT v.KIND, NULL, v.V,
         CASE v.KIND WHEN 'person' THEN 'W' WHEN 'name' THEN 'M' WHEN 'address' THEN 'A' WHEN 'FIRM' THEN 'P' ELSE 'C' END
           || LPAD(CAST(ROW_NUMBER() OVER (PARTITION BY v.KIND ORDER BY SHA2(v.V || p.SALT)) AS VARCHAR), 5, '0')
  FROM vals v CROSS JOIN params p
  WHERE v.V IS NOT NULL),
dvs AS (             -- the two divisors
  SELECT (SELECT MEDIAN(X) FROM (SELECT SUM(MM_OPP) AS X FROM ssdb_integration.lr_strategy.data_withnewchannel_union_w_joinkeys
                                 WHERE COALESCE(MM_OPP, 0) <> 0 GROUP BY ZIP_CODE, CHANNEL) a WHERE X > 0) AS D_OPP,
         (SELECT MEDIAN(X) FROM (SELECT SUM(ACTUAL_SALES_AMOUNT) AS X FROM ssdb_integration.lr_strategy.data_withnewchannel_union_w_joinkeys
                                 WHERE ACTUAL_SALES_AMOUNT > 0 GROUP BY SOURCE, ZIP_CODE, CHANNEL) b) AS D_SALES),
mu AS (              -- the masked union table
  SELECT u.FISCAL_YR,
         s.CODE   AS SOURCE,
         n1.CODE  AS TERR_WHOLESALER,
         n2.CODE  AS SALES_WHOLESALER,
         n3.CODE  AS TERR_WHOLESALER_CLEAN_NAME,
         n4.CODE  AS SALES_WHOLESALER_CLEAN_NAME,
         cb.CODE  AS CBD_ID,
         fi.CODE  AS FIRM,
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
  LEFT JOIN k dc ON dc.KIND = 'DIST_CH'    AND dc.SOURCE = u.SOURCE AND dc.VALUE = u.DIST_CH
  LEFT JOIN k nd ON nd.KIND = 'NEW_DIST'   AND nd.SOURCE = u.SOURCE AND nd.VALUE = u.NEW_DIST
  LEFT JOIN k pr ON pr.KIND = 'PRODUCT_V2' AND pr.VALUE = u.PRODUCT_V2
  LEFT JOIN k p1 ON p1.KIND = 'person'     AND p1.VALUE = u.SALES_WHOLESALER_TERRITORY_ID
  LEFT JOIN k a1 ON a1.KIND = 'address'    AND a1.VALUE = u.SALES_WHOLESALER_ADDRESS_ID
  LEFT JOIN k p2 ON p2.KIND = 'person'     AND p2.VALUE = u.TERRITORY_WHOLESALER_TERRITORY_ID
  LEFT JOIN k a2 ON a2.KIND = 'address'    AND a2.VALUE = u.TERRITORY_WHOLESALER_ADDRESS_ID),
mt AS (              -- the masked territories table
  SELECT s.CODE AS SOURCE, nm.CODE AS NAME, t.ZIP_CODE, t.STATE, dc.CODE AS CHANNEL,
         cn.CODE AS CLEAN_NAME, p.CODE AS CLEAN_ID
  FROM ssdb_integration.lr_strategy.territories t
  LEFT JOIN k s  ON s.KIND  = 'SOURCE'  AND s.VALUE  = t.SOURCE
  LEFT JOIN k nm ON nm.KIND = 'name'    AND nm.VALUE = t.NAME
  LEFT JOIN k dc ON dc.KIND = 'DIST_CH' AND dc.SOURCE = t.SOURCE AND dc.VALUE = t.CHANNEL
  LEFT JOIN k cn ON cn.KIND = 'name'    AND cn.VALUE = t.CLEAN_NAME
  LEFT JOIN k p  ON p.KIND  = 'person'  AND p.VALUE  = t.CLEAN_ID)
SELECT KIND, SOURCE, VALUE, CODE, CAST(NULL AS DOUBLE) AS NUM FROM k
UNION ALL SELECT 'divisor', NULL, 'MM_OPP', NULL, D_OPP FROM dvs
UNION ALL SELECT 'divisor', NULL, 'sales', NULL, D_SALES FROM dvs
ORDER BY KIND, SOURCE, CODE;

-- Query 4.  Checks: every MUST_BE_ZERO row must be 0 before anything is downloaded.
WITH
params AS (SELECT '<SALT>' AS SALT),
src AS (             -- SOURCE -> its number
  SELECT SOURCE, DENSE_RANK() OVER (ORDER BY SOURCE) AS R
  FROM (SELECT SOURCE FROM ssdb_integration.lr_strategy.data_withnewchannel_union_w_joinkeys UNION SELECT SOURCE FROM ssdb_integration.lr_strategy.territories) x
  WHERE SOURCE IS NOT NULL),
dv AS (              -- every DIST_CH value of either table, with its rows in each
  SELECT SOURCE, V, SUM(UN) AS UN, SUM(TN) AS TN
  FROM (SELECT SOURCE, DIST_CH AS V, COUNT(*) AS UN, 0 AS TN FROM ssdb_integration.lr_strategy.data_withnewchannel_union_w_joinkeys GROUP BY SOURCE, DIST_CH
        UNION ALL
        SELECT SOURCE, CHANNEL, 0, COUNT(*) FROM ssdb_integration.lr_strategy.territories GROUP BY SOURCE, CHANNEL) x
  WHERE V IS NOT NULL
  GROUP BY SOURCE, V),
nd AS (SELECT SOURCE, NEW_DIST AS V, COUNT(*) AS N FROM ssdb_integration.lr_strategy.data_withnewchannel_union_w_joinkeys WHERE NEW_DIST IS NOT NULL GROUP BY SOURCE, NEW_DIST),
pv AS (SELECT PRODUCT_V2 AS V, COUNT(*) AS N FROM ssdb_integration.lr_strategy.data_withnewchannel_union_w_joinkeys WHERE PRODUCT_V2 IS NOT NULL GROUP BY PRODUCT_V2),
vals AS (            -- the kinds numbered by salted hash
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
  UNION SELECT 'CBD_ID', CBD_ID FROM ssdb_integration.lr_strategy.data_withnewchannel_union_w_joinkeys),
k AS (               -- the key: real value -> code
  SELECT 'SOURCE' AS KIND, CAST(NULL AS VARCHAR) AS SOURCE, SOURCE AS VALUE, 'firm_' || CAST(R AS VARCHAR) AS CODE
  FROM src
  UNION ALL
  SELECT 'DIST_CH', d.SOURCE, d.V,
         'D' || CAST(s.R AS VARCHAR) || '_'
             || LPAD(CAST(ROW_NUMBER() OVER (PARTITION BY d.SOURCE ORDER BY d.UN DESC, d.TN DESC, SHA2(d.V)) AS VARCHAR), 2, '0')
  FROM dv d JOIN src s ON s.SOURCE = d.SOURCE
  UNION ALL
  SELECT 'NEW_DIST', n.SOURCE, n.V,
         'N' || CAST(s.R AS VARCHAR) || '_'
             || LPAD(CAST(ROW_NUMBER() OVER (PARTITION BY n.SOURCE ORDER BY n.N DESC, SHA2(n.V)) AS VARCHAR), 2, '0')
  FROM nd n JOIN src s ON s.SOURCE = n.SOURCE
  UNION ALL
  SELECT 'PRODUCT_V2', NULL, V, 'PR' || LPAD(CAST(ROW_NUMBER() OVER (ORDER BY N DESC, SHA2(V)) AS VARCHAR), 2, '0')
  FROM pv
  UNION ALL
  SELECT v.KIND, NULL, v.V,
         CASE v.KIND WHEN 'person' THEN 'W' WHEN 'name' THEN 'M' WHEN 'address' THEN 'A' WHEN 'FIRM' THEN 'P' ELSE 'C' END
           || LPAD(CAST(ROW_NUMBER() OVER (PARTITION BY v.KIND ORDER BY SHA2(v.V || p.SALT)) AS VARCHAR), 5, '0')
  FROM vals v CROSS JOIN params p
  WHERE v.V IS NOT NULL),
dvs AS (             -- the two divisors
  SELECT (SELECT MEDIAN(X) FROM (SELECT SUM(MM_OPP) AS X FROM ssdb_integration.lr_strategy.data_withnewchannel_union_w_joinkeys
                                 WHERE COALESCE(MM_OPP, 0) <> 0 GROUP BY ZIP_CODE, CHANNEL) a WHERE X > 0) AS D_OPP,
         (SELECT MEDIAN(X) FROM (SELECT SUM(ACTUAL_SALES_AMOUNT) AS X FROM ssdb_integration.lr_strategy.data_withnewchannel_union_w_joinkeys
                                 WHERE ACTUAL_SALES_AMOUNT > 0 GROUP BY SOURCE, ZIP_CODE, CHANNEL) b) AS D_SALES),
mu AS (              -- the masked union table
  SELECT u.FISCAL_YR,
         s.CODE   AS SOURCE,
         n1.CODE  AS TERR_WHOLESALER,
         n2.CODE  AS SALES_WHOLESALER,
         n3.CODE  AS TERR_WHOLESALER_CLEAN_NAME,
         n4.CODE  AS SALES_WHOLESALER_CLEAN_NAME,
         cb.CODE  AS CBD_ID,
         fi.CODE  AS FIRM,
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
  LEFT JOIN k dc ON dc.KIND = 'DIST_CH'    AND dc.SOURCE = u.SOURCE AND dc.VALUE = u.DIST_CH
  LEFT JOIN k nd ON nd.KIND = 'NEW_DIST'   AND nd.SOURCE = u.SOURCE AND nd.VALUE = u.NEW_DIST
  LEFT JOIN k pr ON pr.KIND = 'PRODUCT_V2' AND pr.VALUE = u.PRODUCT_V2
  LEFT JOIN k p1 ON p1.KIND = 'person'     AND p1.VALUE = u.SALES_WHOLESALER_TERRITORY_ID
  LEFT JOIN k a1 ON a1.KIND = 'address'    AND a1.VALUE = u.SALES_WHOLESALER_ADDRESS_ID
  LEFT JOIN k p2 ON p2.KIND = 'person'     AND p2.VALUE = u.TERRITORY_WHOLESALER_TERRITORY_ID
  LEFT JOIN k a2 ON a2.KIND = 'address'    AND a2.VALUE = u.TERRITORY_WHOLESALER_ADDRESS_ID),
mt AS (              -- the masked territories table
  SELECT s.CODE AS SOURCE, nm.CODE AS NAME, t.ZIP_CODE, t.STATE, dc.CODE AS CHANNEL,
         cn.CODE AS CLEAN_NAME, p.CODE AS CLEAN_ID
  FROM ssdb_integration.lr_strategy.territories t
  LEFT JOIN k s  ON s.KIND  = 'SOURCE'  AND s.VALUE  = t.SOURCE
  LEFT JOIN k nm ON nm.KIND = 'name'    AND nm.VALUE = t.NAME
  LEFT JOIN k dc ON dc.KIND = 'DIST_CH' AND dc.SOURCE = t.SOURCE AND dc.VALUE = t.CHANNEL
  LEFT JOIN k cn ON cn.KIND = 'name'    AND cn.VALUE = t.CLEAN_NAME
  LEFT JOIN k p  ON p.KIND  = 'person'  AND p.VALUE  = t.CLEAN_ID),
masked_vals AS (     -- every coded value in the two masked tables
  SELECT SOURCE AS V FROM mu
  UNION SELECT TERR_WHOLESALER FROM mu
  UNION SELECT SALES_WHOLESALER FROM mu
  UNION SELECT TERR_WHOLESALER_CLEAN_NAME FROM mu
  UNION SELECT SALES_WHOLESALER_CLEAN_NAME FROM mu
  UNION SELECT CBD_ID FROM mu
  UNION SELECT FIRM FROM mu
  UNION SELECT DIST_CH FROM mu
  UNION SELECT NEW_DIST FROM mu
  UNION SELECT PRODUCT_V2 FROM mu
  UNION SELECT SALES_WHOLESALER_TERRITORY_ID FROM mu
  UNION SELECT SALES_WHOLESALER_ADDRESS_ID FROM mu
  UNION SELECT TERRITORY_WHOLESALER_TERRITORY_ID FROM mu
  UNION SELECT TERRITORY_WHOLESALER_ADDRESS_ID FROM mu
  UNION SELECT SOURCE FROM mt
  UNION SELECT NAME FROM mt
  UNION SELECT CHANNEL FROM mt
  UNION SELECT CLEAN_NAME FROM mt
  UNION SELECT CLEAN_ID FROM mt),
real_vals AS (SELECT DISTINCT VALUE FROM k)
SELECT 'salt still the placeholder or under 16 characters' AS CHECK_NAME,
       (SELECT CASE WHEN SALT = '<' || 'SALT>' OR LENGTH(SALT) < 16 THEN 1 ELSE 0 END FROM params) AS VALUE, 1 AS MUST_BE_ZERO
UNION ALL SELECT 'real values left in the masked tables',
       (SELECT COUNT(*) FROM masked_vals m JOIN real_vals r ON r.VALUE = m.V), 1
UNION ALL SELECT 'union rows: real minus masked',
       (SELECT COUNT(*) FROM ssdb_integration.lr_strategy.data_withnewchannel_union_w_joinkeys) - (SELECT COUNT(*) FROM mu), 1
UNION ALL SELECT 'territories rows: real minus masked',
       (SELECT COUNT(*) FROM ssdb_integration.lr_strategy.territories) - (SELECT COUNT(*) FROM mt), 1
UNION ALL SELECT 'union values with no code (non-NULL in, NULL out)',
       (SELECT COUNT_IF(SOURCE IS NOT NULL) + COUNT_IF(TERR_WHOLESALER IS NOT NULL) + COUNT_IF(SALES_WHOLESALER IS NOT NULL) + COUNT_IF(TERR_WHOLESALER_CLEAN_NAME IS NOT NULL) + COUNT_IF(SALES_WHOLESALER_CLEAN_NAME IS NOT NULL) + COUNT_IF(CBD_ID IS NOT NULL) + COUNT_IF(FIRM IS NOT NULL) + COUNT_IF(DIST_CH IS NOT NULL) + COUNT_IF(NEW_DIST IS NOT NULL) + COUNT_IF(PRODUCT_V2 IS NOT NULL) + COUNT_IF(SALES_WHOLESALER_TERRITORY_ID IS NOT NULL) + COUNT_IF(SALES_WHOLESALER_ADDRESS_ID IS NOT NULL) + COUNT_IF(TERRITORY_WHOLESALER_TERRITORY_ID IS NOT NULL) + COUNT_IF(TERRITORY_WHOLESALER_ADDRESS_ID IS NOT NULL)
        FROM ssdb_integration.lr_strategy.data_withnewchannel_union_w_joinkeys) -
       (SELECT COUNT_IF(SOURCE IS NOT NULL) + COUNT_IF(TERR_WHOLESALER IS NOT NULL) + COUNT_IF(SALES_WHOLESALER IS NOT NULL) + COUNT_IF(TERR_WHOLESALER_CLEAN_NAME IS NOT NULL) + COUNT_IF(SALES_WHOLESALER_CLEAN_NAME IS NOT NULL) + COUNT_IF(CBD_ID IS NOT NULL) + COUNT_IF(FIRM IS NOT NULL) + COUNT_IF(DIST_CH IS NOT NULL) + COUNT_IF(NEW_DIST IS NOT NULL) + COUNT_IF(PRODUCT_V2 IS NOT NULL) + COUNT_IF(SALES_WHOLESALER_TERRITORY_ID IS NOT NULL) + COUNT_IF(SALES_WHOLESALER_ADDRESS_ID IS NOT NULL) + COUNT_IF(TERRITORY_WHOLESALER_TERRITORY_ID IS NOT NULL) + COUNT_IF(TERRITORY_WHOLESALER_ADDRESS_ID IS NOT NULL)
        FROM mu), 1
UNION ALL SELECT 'territories values with no code (non-NULL in, NULL out)',
       (SELECT COUNT_IF(SOURCE IS NOT NULL) + COUNT_IF(NAME IS NOT NULL) + COUNT_IF(CHANNEL IS NOT NULL) + COUNT_IF(CLEAN_NAME IS NOT NULL) + COUNT_IF(CLEAN_ID IS NOT NULL) FROM ssdb_integration.lr_strategy.territories)
     - (SELECT COUNT_IF(SOURCE IS NOT NULL) + COUNT_IF(NAME IS NOT NULL) + COUNT_IF(CHANNEL IS NOT NULL) + COUNT_IF(CLEAN_NAME IS NOT NULL) + COUNT_IF(CLEAN_ID IS NOT NULL) FROM mt), 1
UNION ALL SELECT 'people: real IDs minus codes',
       (SELECT COUNT(*) FROM k WHERE KIND = 'person')
     - (SELECT COUNT(*) FROM (SELECT SALES_WHOLESALER_TERRITORY_ID AS V FROM mu
                              UNION SELECT TERRITORY_WHOLESALER_TERRITORY_ID FROM mu
                              UNION SELECT CLEAN_ID FROM mt) x WHERE V IS NOT NULL), 1
UNION ALL SELECT 'codes used twice within a kind (and SOURCE)',
       (SELECT COUNT(*) FROM (SELECT KIND, SOURCE, CODE FROM k GROUP BY KIND, SOURCE, CODE HAVING COUNT(*) > 1) x), 1
UNION ALL SELECT 'MM_OPP total: masked x divisor / real (should be 1)',
       (SELECT SUM(MM_OPP) FROM mu) * (SELECT D_OPP FROM dvs) / NULLIF((SELECT SUM(MM_OPP) FROM ssdb_integration.lr_strategy.data_withnewchannel_union_w_joinkeys), 0), 0
UNION ALL SELECT 'ACTUAL_SALES_AMOUNT total: masked x divisor / real (should be 1)',
       (SELECT SUM(ACTUAL_SALES_AMOUNT) FROM mu) * (SELECT D_SALES FROM dvs)
     / NULLIF((SELECT SUM(ACTUAL_SALES_AMOUNT) FROM ssdb_integration.lr_strategy.data_withnewchannel_union_w_joinkeys), 0), 0
ORDER BY MUST_BE_ZERO DESC, CHECK_NAME;
