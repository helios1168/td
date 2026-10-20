-- One worked example, in the real data, of how 15_territories_enriched.sql gives the non-carrier
-- SOURCE its opportunity.  Picks one (ZIP_CODE, CHANNEL) where that SOURCE holds two or more DIST_CH
-- values of the CHANNEL with two or more people (the busiest such cell by opportunity), or the one you
-- set in `pick`.  One result, read top to bottom by STEP.  Its output has real names and amounts:
-- keep it at work.
WITH
carrier AS (
  SELECT DISTINCT SOURCE FROM ssdb_integration.lr_strategy.data_withnewchannel_union_w_joinkeys
  WHERE COALESCE(MM_OPP, 0) <> 0),
other AS (
  SELECT DISTINCT SOURCE FROM ssdb_integration.lr_strategy.data_withnewchannel_union_w_joinkeys
  WHERE SOURCE NOT IN (SELECT SOURCE FROM carrier) AND SOURCE IS NOT NULL),
products AS (
  SELECT DISTINCT SOURCE, PRODUCT_V2 FROM ssdb_integration.lr_strategy.data_withnewchannel_union_w_joinkeys
  WHERE ACTUAL_SALES_AMOUNT > 0),
pairs AS (           -- the other SOURCE's DIST_CH -> CHANNEL, with national positive sales
  SELECT u.SOURCE, u.DIST_CH, u.CHANNEL,
         SUM(CASE WHEN u.ACTUAL_SALES_AMOUNT > 0 THEN u.ACTUAL_SALES_AMOUNT ELSE 0 END) AS POS_SALES
  FROM ssdb_integration.lr_strategy.data_withnewchannel_union_w_joinkeys u
  JOIN other o ON o.SOURCE = u.SOURCE
  GROUP BY u.SOURCE, u.DIST_CH, u.CHANNEL),
held AS (            -- its territories rows, with the CHANNEL each DIST_CH maps to
  SELECT DISTINCT t.SOURCE, t.ZIP_CODE, t.CHANNEL AS DIST_CH, p.CHANNEL, t.CLEAN_ID, t.CLEAN_NAME
  FROM ssdb_integration.lr_strategy.territories t
  JOIN pairs p ON p.SOURCE = t.SOURCE AND p.DIST_CH = t.CHANNEL),
channel_opp AS (     -- the carrier's MM_OPP per (ZIP_CODE, CHANNEL), all products
  SELECT u.ZIP_CODE, u.CHANNEL, SUM(u.MM_OPP) AS MM_OPP
  FROM ssdb_integration.lr_strategy.data_withnewchannel_union_w_joinkeys u
  JOIN carrier c ON c.SOURCE = u.SOURCE
  GROUP BY u.ZIP_CODE, u.CHANNEL),
pick AS (            -- to choose your own: SELECT '<ZIP_CODE>' AS ZIP_CODE, '<CHANNEL>' AS CHANNEL
  SELECT h.ZIP_CODE, h.CHANNEL
  FROM held h JOIN channel_opp o ON o.ZIP_CODE = h.ZIP_CODE AND o.CHANNEL = h.CHANNEL
  GROUP BY h.ZIP_CODE, h.CHANNEL, o.MM_OPP
  HAVING COUNT(DISTINCT h.DIST_CH) > 1 AND COUNT(DISTINCT h.CLEAN_ID) > 1
  ORDER BY o.MM_OPP DESC
  LIMIT 1),
by_product AS (      -- step 1
  SELECT u.PRODUCT_V2, SUM(u.MM_OPP) AS MM_OPP,
         MAX(CASE WHEN p.PRODUCT_V2 IS NOT NULL THEN 1 ELSE 0 END) AS SOLD_BY_OTHER
  FROM ssdb_integration.lr_strategy.data_withnewchannel_union_w_joinkeys u
  JOIN carrier c ON c.SOURCE = u.SOURCE
  JOIN pick k    ON k.ZIP_CODE = u.ZIP_CODE AND k.CHANNEL = u.CHANNEL
  LEFT JOIN products p ON p.PRODUCT_V2 = u.PRODUCT_V2 AND p.SOURCE IN (SELECT SOURCE FROM other)
  GROUP BY u.PRODUCT_V2),
dist AS (            -- steps 3-5: each DIST_CH of the CHANNEL, held here or not, and its share
  SELECT p.DIST_CH, p.POS_SALES,
         MAX(CASE WHEN h.DIST_CH IS NOT NULL THEN 1 ELSE 0 END) AS HELD_HERE
  FROM pairs p
  JOIN pick k ON k.CHANNEL = p.CHANNEL
  LEFT JOIN held h ON h.ZIP_CODE = k.ZIP_CODE AND h.CHANNEL = k.CHANNEL AND h.DIST_CH = p.DIST_CH
  GROUP BY p.DIST_CH, p.POS_SALES),
shares AS (
  SELECT DIST_CH, POS_SALES, HELD_HERE,
         CASE WHEN HELD_HERE = 1
              THEN COALESCE(POS_SALES / NULLIF(SUM(CASE WHEN HELD_HERE = 1 THEN POS_SALES END) OVER (), 0),
                            1.0 / SUM(HELD_HERE) OVER ()) END AS SHARE
  FROM dist),
counted AS (SELECT SUM(CASE WHEN SOLD_BY_OTHER = 1 THEN MM_OPP ELSE 0 END) AS MM_OPP FROM by_product),
people AS (          -- step 6: each holder's row
  SELECT h.DIST_CH, h.CLEAN_ID, h.CLEAN_NAME,
         COUNT(*) OVER (PARTITION BY h.DIST_CH) AS HOLDERS
  FROM held h JOIN pick k ON k.ZIP_CODE = h.ZIP_CODE AND k.CHANNEL = h.CHANNEL),
sales AS (
  SELECT u.DIST_CH, u.SALES_WHOLESALER_TERRITORY_ID, SUM(u.ACTUAL_SALES_AMOUNT) AS ACTUAL_SALES_AMOUNT
  FROM ssdb_integration.lr_strategy.data_withnewchannel_union_w_joinkeys u
  JOIN other o ON o.SOURCE = u.SOURCE
  JOIN pick k  ON k.ZIP_CODE = u.ZIP_CODE AND k.CHANNEL = u.CHANNEL
  GROUP BY u.DIST_CH, u.SALES_WHOLESALER_TERRITORY_ID)
SELECT 0 AS STEP, 'the example: ZIP_CODE and CHANNEL' AS WHAT,
       k.ZIP_CODE AS ITEM, k.CHANNEL AS DETAIL, CAST(NULL AS DOUBLE) AS VALUE
FROM pick k
UNION ALL
SELECT 1, 'carrier MM_OPP here, by PRODUCT_V2 (DETAIL: does the other SOURCE sell it?)',
       PRODUCT_V2, CASE WHEN SOLD_BY_OTHER = 1 THEN 'sold: counted' ELSE 'not sold: left out' END, MM_OPP
FROM by_product
UNION ALL
SELECT 2, 'opportunity counted for the other SOURCE here (its products only)', NULL, NULL, MM_OPP
FROM counted
UNION ALL
SELECT 3, 'its DIST_CH values in this CHANNEL: national sales (DETAIL: held in this ZIP_CODE?)',
       DIST_CH, CASE WHEN HELD_HERE = 1 THEN 'held here' ELSE 'not held here: no share' END, POS_SALES
FROM shares
UNION ALL
SELECT 4, 'share of the counted opportunity: national sales / national sales of the held DIST_CH',
       DIST_CH, NULL, ROUND(SHARE, 4)
FROM shares WHERE HELD_HERE = 1
UNION ALL
SELECT 5, 'OPPORTUNITY of the DIST_CH here = step 2 x step 4', s.DIST_CH, NULL, c.MM_OPP * s.SHARE
FROM shares s CROSS JOIN counted c WHERE s.HELD_HERE = 1
UNION ALL
SELECT 6, 'each holder: OPPORTUNITY_SHARE = OPPORTUNITY / holders of that DIST_CH here (DETAIL: who)',
       p.DIST_CH, p.CLEAN_NAME, c.MM_OPP * s.SHARE / p.HOLDERS
FROM people p JOIN shares s ON s.DIST_CH = p.DIST_CH CROSS JOIN counted c
UNION ALL
SELECT 7, 'each holder''s own sales in that DIST_CH here, for comparison (DETAIL: who)',
       p.DIST_CH, p.CLEAN_NAME, COALESCE(sa.ACTUAL_SALES_AMOUNT, 0)
FROM people p
LEFT JOIN sales sa ON sa.DIST_CH = p.DIST_CH AND sa.SALES_WHOLESALER_TERRITORY_ID = p.CLEAN_ID
ORDER BY STEP, ITEM, DETAIL;
