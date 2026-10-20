-- Worked example: how 15_territories_enriched.sql fills OPPORTUNITY, OPPORTUNITY_SHARE and sales for
-- the territories rows you choose.  Choose a ZIP_CODE (all its territories rows, both SOURCEs), or one
-- or more wholesalers (CLEAN_ID or CLEAN_NAME, from either SOURCE: all their territories rows), or both
-- (those wholesalers' rows in that ZIP_CODE); leave a placeholder as is to not use it.  If you choose
-- nothing, or nothing matches, it shows the busiest ZIP_CODE where the non-carrier SOURCE splits a
-- CHANNEL among several people.  Reads only the two source tables.  One result, one block of steps per territories
-- row and target CHANNEL, read top to bottom.  Output has real names and amounts: keep it at work.
WITH
pick_zip AS (        -- EDIT: a ZIP_CODE, or leave the placeholder
  SELECT ZIP_CODE FROM (VALUES ('<ZIP_CODE>')) AS v(ZIP_CODE)),
pick_who AS (        -- EDIT: CLEAN_ID or CLEAN_NAME values, one per row; add rows as needed
  SELECT WHO FROM (VALUES ('<CLEAN_ID or CLEAN_NAME, source 1>'),
                          ('<CLEAN_ID or CLEAN_NAME, source 2>')) AS v(WHO)),

carrier AS (         -- the SOURCE whose rows carry MM_OPP
  SELECT DISTINCT SOURCE FROM ssdb_integration.lr_strategy.data_withnewchannel_union_w_joinkeys
  WHERE COALESCE(MM_OPP, 0) <> 0),
products AS (        -- each SOURCE's product set
  SELECT DISTINCT SOURCE, PRODUCT_V2 FROM ssdb_integration.lr_strategy.data_withnewchannel_union_w_joinkeys
  WHERE ACTUAL_SALES_AMOUNT > 0),
ch_map AS (          -- (SOURCE, DIST_CH) -> target CHANNEL
  SELECT DISTINCT SOURCE, DIST_CH, CHANNEL FROM ssdb_integration.lr_strategy.data_withnewchannel_union_w_joinkeys),
pairs AS (           -- national positive sales per (SOURCE, DIST_CH, CHANNEL), non-carrier SOURCE
  SELECT SOURCE, DIST_CH, CHANNEL,
         SUM(CASE WHEN ACTUAL_SALES_AMOUNT > 0 THEN ACTUAL_SALES_AMOUNT ELSE 0 END) AS POS_SALES
  FROM ssdb_integration.lr_strategy.data_withnewchannel_union_w_joinkeys
  WHERE SOURCE NOT IN (SELECT SOURCE FROM carrier)
  GROUP BY SOURCE, DIST_CH, CHANNEL),
held AS (            -- non-carrier territories rows with their target CHANNEL
  SELECT DISTINCT t.SOURCE, t.ZIP_CODE, t.CHANNEL AS DIST_CH, p.CHANNEL, t.CLEAN_ID
  FROM ssdb_integration.lr_strategy.territories t
  JOIN pairs p ON p.SOURCE = t.SOURCE AND p.DIST_CH = t.CHANNEL),
held_by AS (         -- people holding each non-carrier (ZIP_CODE, DIST_CH, CHANNEL)
  SELECT SOURCE, ZIP_CODE, DIST_CH, CHANNEL, COUNT(DISTINCT CLEAN_ID) AS N
  FROM held GROUP BY SOURCE, ZIP_CODE, DIST_CH, CHANNEL),
holders AS (         -- holders per (SOURCE, ZIP_CODE, DIST_CH)
  SELECT SOURCE, ZIP_CODE, CHANNEL AS DIST_CH, COUNT(DISTINCT CLEAN_ID) AS N
  FROM ssdb_integration.lr_strategy.territories
  GROUP BY SOURCE, ZIP_CODE, CHANNEL),

auto_zip AS (        -- fallback: the busiest ZIP_CODE where the non-carrier SOURCE splits a CHANNEL among people
  SELECT h.ZIP_CODE
  FROM held h
  JOIN (SELECT u.ZIP_CODE, u.CHANNEL, SUM(u.MM_OPP) AS MM_OPP
        FROM ssdb_integration.lr_strategy.data_withnewchannel_union_w_joinkeys u
        JOIN carrier c ON c.SOURCE = u.SOURCE GROUP BY u.ZIP_CODE, u.CHANNEL) o
    ON o.ZIP_CODE = h.ZIP_CODE AND o.CHANNEL = h.CHANNEL
  GROUP BY h.ZIP_CODE, h.CHANNEL, o.MM_OPP
  HAVING COUNT(DISTINCT h.DIST_CH) > 1 AND COUNT(DISTINCT h.CLEAN_ID) > 1
  ORDER BY o.MM_OPP DESC
  LIMIT 1),
zips AS (SELECT ZIP_CODE FROM pick_zip WHERE ZIP_CODE NOT LIKE '<%'),
whos AS (SELECT WHO FROM pick_who WHERE WHO NOT LIKE '<%'),
chosen AS (          -- the territories rows you chose
  SELECT DISTINCT t.SOURCE, t.CLEAN_ID, t.CLEAN_NAME, t.ZIP_CODE, t.CHANNEL AS DIST_CH
  FROM ssdb_integration.lr_strategy.territories t
  WHERE ((SELECT COUNT(*) FROM zips) > 0 OR (SELECT COUNT(*) FROM whos) > 0)
    AND ((SELECT COUNT(*) FROM zips) = 0 OR t.ZIP_CODE IN (SELECT ZIP_CODE FROM zips))
    AND ((SELECT COUNT(*) FROM whos) = 0 OR t.CLEAN_ID IN (SELECT WHO FROM whos)
                                         OR t.CLEAN_NAME IN (SELECT WHO FROM whos))),
sel0 AS (
  SELECT * FROM chosen
  UNION ALL
  SELECT DISTINCT t.SOURCE, t.CLEAN_ID, t.CLEAN_NAME, t.ZIP_CODE, t.CHANNEL
  FROM ssdb_integration.lr_strategy.territories t
  WHERE t.ZIP_CODE IN (SELECT ZIP_CODE FROM auto_zip)
    AND NOT EXISTS (SELECT 1 FROM chosen)),
sel AS (             -- one row per chosen territories row and target CHANNEL (CHANNEL NULL: out of scope)
  SELECT s.*, m.CHANNEL,
         CASE WHEN s.SOURCE IN (SELECT SOURCE FROM carrier) THEN 1 ELSE 0 END AS IS_CARRIER
  FROM sel0 s
  LEFT JOIN ch_map m ON m.SOURCE = s.SOURCE AND m.DIST_CH = s.DIST_CH),

by_product AS (      -- the carrier's MM_OPP behind each chosen row, by PRODUCT_V2
  SELECT s.SOURCE, s.CLEAN_ID, s.ZIP_CODE, s.DIST_CH, s.CHANNEL, u.PRODUCT_V2, SUM(u.MM_OPP) AS MM_OPP,
         MAX(CASE WHEN p.PRODUCT_V2 IS NOT NULL THEN 1 ELSE 0 END) AS COUNTED
  FROM sel s
  JOIN ssdb_integration.lr_strategy.data_withnewchannel_union_w_joinkeys u
    ON u.ZIP_CODE = s.ZIP_CODE AND u.CHANNEL = s.CHANNEL
   AND u.SOURCE IN (SELECT SOURCE FROM carrier)
   AND (s.IS_CARRIER = 0 OR u.DIST_CH = s.DIST_CH)        -- carrier: its own DIST_CH only
  LEFT JOIN products p ON p.SOURCE = s.SOURCE AND p.PRODUCT_V2 = u.PRODUCT_V2
  GROUP BY s.SOURCE, s.CLEAN_ID, s.ZIP_CODE, s.DIST_CH, s.CHANNEL, u.PRODUCT_V2),
counted AS (
  SELECT SOURCE, CLEAN_ID, ZIP_CODE, DIST_CH, CHANNEL,
         SUM(CASE WHEN COUNTED = 1 THEN MM_OPP ELSE 0 END) AS MM_OPP
  FROM by_product GROUP BY SOURCE, CLEAN_ID, ZIP_CODE, DIST_CH, CHANNEL),
mix AS (             -- non-carrier: every DIST_CH of the CHANNEL, held in the ZIP_CODE or not, and shares
  SELECT s.SOURCE, s.CLEAN_ID, s.ZIP_CODE, s.DIST_CH AS ROW_DIST_CH, s.CHANNEL,
         p.DIST_CH, p.POS_SALES, COALESCE(hb.N, 0) AS HELD_BY
  FROM sel s
  JOIN pairs p ON p.SOURCE = s.SOURCE AND p.CHANNEL = s.CHANNEL
  LEFT JOIN held_by hb ON hb.SOURCE = s.SOURCE AND hb.ZIP_CODE = s.ZIP_CODE
                      AND hb.CHANNEL = s.CHANNEL AND hb.DIST_CH = p.DIST_CH
  WHERE s.IS_CARRIER = 0),
shares AS (
  SELECT m.*,
         CASE WHEN HELD_BY > 0 THEN
           CASE WHEN SUM(CASE WHEN HELD_BY > 0 THEN POS_SALES ELSE 0 END)
                       OVER (PARTITION BY SOURCE, CLEAN_ID, ZIP_CODE, ROW_DIST_CH, CHANNEL) > 0
                THEN POS_SALES / SUM(CASE WHEN HELD_BY > 0 THEN POS_SALES ELSE 0 END)
                                 OVER (PARTITION BY SOURCE, CLEAN_ID, ZIP_CODE, ROW_DIST_CH, CHANNEL)
                ELSE 1.0 / SUM(CASE WHEN HELD_BY > 0 THEN 1 ELSE 0 END)
                           OVER (PARTITION BY SOURCE, CLEAN_ID, ZIP_CODE, ROW_DIST_CH, CHANNEL) END
         END AS SHARE
  FROM mix m),
result AS (          -- OPPORTUNITY and OPPORTUNITY_SHARE per chosen row, as 15 computes them
  SELECT s.SOURCE, s.CLEAN_ID, s.ZIP_CODE, s.DIST_CH, s.CHANNEL, s.IS_CARRIER,
         COALESCE(c.MM_OPP, 0) AS COUNTED_OPP,
         sh.SHARE,
         CASE WHEN s.CHANNEL IS NULL THEN 0
              WHEN s.IS_CARRIER = 1 THEN COALESCE(c.MM_OPP, 0)
              ELSE COALESCE(c.MM_OPP, 0) * COALESCE(sh.SHARE, 0) END AS OPPORTUNITY,
         h.N AS HOLDERS
  FROM sel s
  LEFT JOIN counted c ON c.SOURCE = s.SOURCE AND c.CLEAN_ID = s.CLEAN_ID AND c.ZIP_CODE = s.ZIP_CODE
                     AND c.DIST_CH = s.DIST_CH AND c.CHANNEL = s.CHANNEL
  LEFT JOIN shares sh ON sh.SOURCE = s.SOURCE AND sh.CLEAN_ID = s.CLEAN_ID AND sh.ZIP_CODE = s.ZIP_CODE
                     AND sh.ROW_DIST_CH = s.DIST_CH AND sh.CHANNEL = s.CHANNEL AND sh.DIST_CH = s.DIST_CH
  LEFT JOIN holders h ON h.SOURCE = s.SOURCE AND h.ZIP_CODE = s.ZIP_CODE AND h.DIST_CH = s.DIST_CH),
sales AS (
  SELECT s.SOURCE, s.CLEAN_ID, s.ZIP_CODE, s.DIST_CH, s.CHANNEL,
         COALESCE(SUM(CASE WHEN u.SALES_WHOLESALER_TERRITORY_ID = s.CLEAN_ID THEN u.ACTUAL_SALES_AMOUNT ELSE 0 END), 0) AS BY_HOLDER,
         COALESCE(SUM(u.ACTUAL_SALES_AMOUNT), 0) AS TOTAL
  FROM sel s
  LEFT JOIN ssdb_integration.lr_strategy.data_withnewchannel_union_w_joinkeys u
    ON u.SOURCE = s.SOURCE AND u.ZIP_CODE = s.ZIP_CODE AND u.DIST_CH = s.DIST_CH AND u.CHANNEL = s.CHANNEL
  GROUP BY s.SOURCE, s.CLEAN_ID, s.ZIP_CODE, s.DIST_CH, s.CHANNEL),

steps AS (
  SELECT s.SOURCE, s.CLEAN_NAME, s.CLEAN_ID, s.ZIP_CODE, s.DIST_CH, s.CHANNEL, 0 AS STEP,
         CASE WHEN s.CHANNEL IS NULL THEN 'out of scope: DIST_CH is not in the union table, all zeros'
              WHEN s.IS_CARRIER = 1 THEN 'carrier SOURCE: OPPORTUNITY_METHOD exact'
              ELSE 'non-carrier SOURCE: OPPORTUNITY_METHOD sales_mix_held' END AS WHAT,
         CAST(NULL AS VARCHAR) AS ITEM, CAST(NULL AS VARCHAR) AS DETAIL, CAST(NULL AS DOUBLE) AS VALUE
  FROM sel s
  UNION ALL
  SELECT s.SOURCE, s.CLEAN_NAME, s.CLEAN_ID, s.ZIP_CODE, s.DIST_CH, s.CHANNEL, 1,
         CASE WHEN s.IS_CARRIER = 1 THEN 'carrier MM_OPP in this ZIP_CODE, DIST_CH and CHANNEL, by PRODUCT_V2'
              ELSE 'carrier MM_OPP in this ZIP_CODE and CHANNEL (all its DIST_CH), by PRODUCT_V2' END,
         b.PRODUCT_V2, CASE WHEN b.COUNTED = 1 THEN 'this SOURCE sells it: counted'
                            ELSE 'this SOURCE does not sell it: left out' END, b.MM_OPP
  FROM sel s JOIN by_product b ON b.SOURCE = s.SOURCE AND b.CLEAN_ID = s.CLEAN_ID AND b.ZIP_CODE = s.ZIP_CODE
                              AND b.DIST_CH = s.DIST_CH AND b.CHANNEL = s.CHANNEL
  UNION ALL
  SELECT r.SOURCE, s.CLEAN_NAME, r.CLEAN_ID, r.ZIP_CODE, r.DIST_CH, r.CHANNEL, 2,
         'opportunity counted (this SOURCE''s products only)', NULL, NULL, r.COUNTED_OPP
  FROM result r JOIN sel s ON s.SOURCE = r.SOURCE AND s.CLEAN_ID = r.CLEAN_ID AND s.ZIP_CODE = r.ZIP_CODE
                          AND s.DIST_CH = r.DIST_CH AND s.CHANNEL IS NOT DISTINCT FROM r.CHANNEL
  UNION ALL
  SELECT m.SOURCE, s.CLEAN_NAME, m.CLEAN_ID, m.ZIP_CODE, m.ROW_DIST_CH, m.CHANNEL, 3,
         'this SOURCE''s DIST_CH values in the CHANNEL: national sales; held in this ZIP_CODE?',
         m.DIST_CH,
         CASE WHEN m.HELD_BY > 0 THEN 'held here by ' || CAST(m.HELD_BY AS VARCHAR) || ' person(s)'
              ELSE 'not held here: no share' END
           || CASE WHEN m.DIST_CH = m.ROW_DIST_CH THEN ' (this row)' ELSE '' END,
         m.POS_SALES
  FROM shares m JOIN sel s ON s.SOURCE = m.SOURCE AND s.CLEAN_ID = m.CLEAN_ID AND s.ZIP_CODE = m.ZIP_CODE
                          AND s.DIST_CH = m.ROW_DIST_CH AND s.CHANNEL = m.CHANNEL
  UNION ALL
  SELECT r.SOURCE, s.CLEAN_NAME, r.CLEAN_ID, r.ZIP_CODE, r.DIST_CH, r.CHANNEL, 4,
         'this DIST_CH''s share: its national sales / national sales of the DIST_CH held here', NULL, NULL, r.SHARE
  FROM result r JOIN sel s ON s.SOURCE = r.SOURCE AND s.CLEAN_ID = r.CLEAN_ID AND s.ZIP_CODE = r.ZIP_CODE
                          AND s.DIST_CH = r.DIST_CH AND s.CHANNEL IS NOT DISTINCT FROM r.CHANNEL
  WHERE r.IS_CARRIER = 0 AND r.CHANNEL IS NOT NULL
  UNION ALL
  SELECT r.SOURCE, s.CLEAN_NAME, r.CLEAN_ID, r.ZIP_CODE, r.DIST_CH, r.CHANNEL, 5,
         CASE WHEN r.IS_CARRIER = 1 THEN 'OPPORTUNITY = step 2'
              ELSE 'OPPORTUNITY = step 2 x step 4' END, NULL, NULL, r.OPPORTUNITY
  FROM result r JOIN sel s ON s.SOURCE = r.SOURCE AND s.CLEAN_ID = r.CLEAN_ID AND s.ZIP_CODE = r.ZIP_CODE
                          AND s.DIST_CH = r.DIST_CH AND s.CHANNEL IS NOT DISTINCT FROM r.CHANNEL
  UNION ALL
  SELECT r.SOURCE, s.CLEAN_NAME, r.CLEAN_ID, r.ZIP_CODE, r.DIST_CH, r.CHANNEL, 6,
         'OPPORTUNITY_SHARE = OPPORTUNITY / holders of this DIST_CH in this ZIP_CODE',
         NULL, CAST(r.HOLDERS AS VARCHAR) || ' holder(s)', r.OPPORTUNITY / NULLIF(r.HOLDERS, 0)
  FROM result r JOIN sel s ON s.SOURCE = r.SOURCE AND s.CLEAN_ID = r.CLEAN_ID AND s.ZIP_CODE = r.ZIP_CODE
                          AND s.DIST_CH = r.DIST_CH AND s.CHANNEL IS NOT DISTINCT FROM r.CHANNEL
  UNION ALL
  SELECT s.SOURCE, s.CLEAN_NAME, s.CLEAN_ID, s.ZIP_CODE, s.DIST_CH, s.CHANNEL, 7,
         'sales in this ZIP_CODE, DIST_CH and CHANNEL', 'SALES_BY_HOLDER', NULL, a.BY_HOLDER
  FROM sel s JOIN sales a ON a.SOURCE = s.SOURCE AND a.CLEAN_ID = s.CLEAN_ID AND a.ZIP_CODE = s.ZIP_CODE
                         AND a.DIST_CH = s.DIST_CH AND a.CHANNEL IS NOT DISTINCT FROM s.CHANNEL
  UNION ALL
  SELECT s.SOURCE, s.CLEAN_NAME, s.CLEAN_ID, s.ZIP_CODE, s.DIST_CH, s.CHANNEL, 7,
         'sales in this ZIP_CODE, DIST_CH and CHANNEL', 'SALES_BY_OTHERS', NULL, a.TOTAL - a.BY_HOLDER
  FROM sel s JOIN sales a ON a.SOURCE = s.SOURCE AND a.CLEAN_ID = s.CLEAN_ID AND a.ZIP_CODE = s.ZIP_CODE
                         AND a.DIST_CH = s.DIST_CH AND a.CHANNEL IS NOT DISTINCT FROM s.CHANNEL
  UNION ALL
  SELECT s.SOURCE, s.CLEAN_NAME, s.CLEAN_ID, s.ZIP_CODE, s.DIST_CH, s.CHANNEL, 7,
         'sales in this ZIP_CODE, DIST_CH and CHANNEL', 'SALES_TOTAL', NULL, a.TOTAL
  FROM sel s JOIN sales a ON a.SOURCE = s.SOURCE AND a.CLEAN_ID = s.CLEAN_ID AND a.ZIP_CODE = s.ZIP_CODE
                         AND a.DIST_CH = s.DIST_CH AND a.CHANNEL IS NOT DISTINCT FROM s.CHANNEL)
SELECT SOURCE, CLEAN_NAME, CLEAN_ID, ZIP_CODE, DIST_CH, CHANNEL, STEP, WHAT, ITEM, DETAIL, VALUE
FROM steps
ORDER BY SOURCE, CLEAN_NAME, ZIP_CODE, DIST_CH, CHANNEL, STEP, ITEM;
