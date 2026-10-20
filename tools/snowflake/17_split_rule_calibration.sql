-- Which rule for dividing a CHANNEL's opportunity among a SOURCE's DIST_CH values comes closest to
-- the truth?  Only the carrier SOURCE (the one whose rows carry MM_OPP) has MM_OPP per DIST_CH, so its
-- true per-person opportunity is known.  This rebuilds that from CHANNEL-level opportunity under each
-- rule, as if its DIST_CH values had no MM_OPP of their own (the other SOURCE's situation), and
-- compares per person (CLEAN_ID).  Reads the two source tables only.  Output: one row per rule,
-- counts and error rates only.
--   exact            MM_OPP of the person's own (ZIP_CODE, DIST_CH), split among that cell's holders
--   equal_people     each (ZIP_CODE, CHANNEL) a person holds: its MM_OPP / people holding that CHANNEL there
--   sales_mix_held   each held (ZIP_CODE, DIST_CH): (ZIP_CODE, CHANNEL) MM_OPP x the DIST_CH's national
--                    share of the SOURCE's sales in that CHANNEL, rescaled over the DIST_CH values held
--                    in that ZIP_CODE; then split among that cell's holders
WITH
carrier AS (
  SELECT DISTINCT SOURCE FROM ssdb_integration.lr_strategy.data_withnewchannel_union_w_joinkeys
  WHERE COALESCE(MM_OPP, 0) <> 0),
u AS (
  SELECT x.* FROM ssdb_integration.lr_strategy.data_withnewchannel_union_w_joinkeys x
  JOIN carrier c ON c.SOURCE = x.SOURCE),
products AS (SELECT DISTINCT PRODUCT_V2 FROM u WHERE ACTUAL_SALES_AMOUNT > 0),
pairs AS (            -- DIST_CH -> CHANNEL, with positive sales in each pair
  SELECT DIST_CH, CHANNEL, SUM(CASE WHEN ACTUAL_SALES_AMOUNT > 0 THEN ACTUAL_SALES_AMOUNT ELSE 0 END) AS POS_SALES
  FROM u GROUP BY DIST_CH, CHANNEL),
w_nat AS (            -- a DIST_CH's national share of the SOURCE's sales within a CHANNEL
  SELECT DIST_CH, CHANNEL, POS_SALES / NULLIF(SUM(POS_SALES) OVER (PARTITION BY CHANNEL), 0) AS W
  FROM pairs),
opp_d AS (            -- MM_OPP per (ZIP_CODE, DIST_CH, CHANNEL), own products
  SELECT ZIP_CODE, DIST_CH, CHANNEL, SUM(MM_OPP) AS MM_OPP
  FROM u WHERE PRODUCT_V2 IN (SELECT PRODUCT_V2 FROM products)
  GROUP BY ZIP_CODE, DIST_CH, CHANNEL),
opp_c AS (            -- MM_OPP per (ZIP_CODE, CHANNEL)
  SELECT ZIP_CODE, CHANNEL, SUM(MM_OPP) AS MM_OPP FROM opp_d GROUP BY ZIP_CODE, CHANNEL),
t AS (                -- the carrier's territories rows that are in scope
  SELECT DISTINCT t.CLEAN_ID, t.ZIP_CODE, t.CHANNEL AS DIST_CH
  FROM ssdb_integration.lr_strategy.territories t
  JOIN carrier c ON c.SOURCE = t.SOURCE
  WHERE t.CHANNEL IN (SELECT DIST_CH FROM pairs)),
held_d AS (           -- holders per (ZIP_CODE, DIST_CH)
  SELECT ZIP_CODE, DIST_CH, COUNT(DISTINCT CLEAN_ID) AS N FROM t GROUP BY ZIP_CODE, DIST_CH),
tc AS (               -- territories rows expanded to CHANNEL
  SELECT DISTINCT t.CLEAN_ID, t.ZIP_CODE, t.DIST_CH, p.CHANNEL
  FROM t JOIN pairs p ON p.DIST_CH = t.DIST_CH),
held_c AS (           -- people holding any DIST_CH of a CHANNEL in a ZIP_CODE
  SELECT ZIP_CODE, CHANNEL, COUNT(DISTINCT CLEAN_ID) AS N FROM tc GROUP BY ZIP_CODE, CHANNEL),
w_held AS (           -- national shares rescaled over the DIST_CH values held in each ZIP_CODE
  SELECT h.ZIP_CODE, h.DIST_CH, h.CHANNEL,
         w.W / NULLIF(SUM(w.W) OVER (PARTITION BY h.ZIP_CODE, h.CHANNEL), 0) AS W
  FROM (SELECT DISTINCT ZIP_CODE, DIST_CH, CHANNEL FROM tc) h
  JOIN w_nat w ON w.DIST_CH = h.DIST_CH AND w.CHANNEL = h.CHANNEL),
exact AS (
  SELECT t.CLEAN_ID, SUM(o.MM_OPP / n.N) AS OPP
  FROM t
  JOIN opp_d o  ON o.ZIP_CODE = t.ZIP_CODE AND o.DIST_CH = t.DIST_CH
  JOIN held_d n ON n.ZIP_CODE = t.ZIP_CODE AND n.DIST_CH = t.DIST_CH
  GROUP BY t.CLEAN_ID),
equal_people AS (
  SELECT x.CLEAN_ID, SUM(o.MM_OPP / n.N) AS OPP
  FROM (SELECT DISTINCT CLEAN_ID, ZIP_CODE, CHANNEL FROM tc) x
  JOIN opp_c o  ON o.ZIP_CODE = x.ZIP_CODE AND o.CHANNEL = x.CHANNEL
  JOIN held_c n ON n.ZIP_CODE = x.ZIP_CODE AND n.CHANNEL = x.CHANNEL
  GROUP BY x.CLEAN_ID),
sales_mix_held AS (
  SELECT x.CLEAN_ID, SUM(o.MM_OPP * w.W / n.N) AS OPP
  FROM tc x
  JOIN opp_c o  ON o.ZIP_CODE = x.ZIP_CODE AND o.CHANNEL = x.CHANNEL
  JOIN w_held w ON w.ZIP_CODE = x.ZIP_CODE AND w.DIST_CH = x.DIST_CH AND w.CHANNEL = x.CHANNEL
  JOIN held_d n ON n.ZIP_CODE = x.ZIP_CODE AND n.DIST_CH = x.DIST_CH
  GROUP BY x.CLEAN_ID),
est AS (
  SELECT 'equal_people' AS RULE, CLEAN_ID, OPP FROM equal_people
  UNION ALL SELECT 'sales_mix_held', CLEAN_ID, OPP FROM sales_mix_held),
cmp AS (
  SELECT e.RULE, x.CLEAN_ID, x.OPP AS EXACT, COALESCE(e.OPP, 0) AS EST,
         ABS(COALESCE(e.OPP, 0) - x.OPP) / NULLIF(x.OPP, 0) AS ABS_PCT_ERR
  FROM exact x JOIN est e ON e.CLEAN_ID = x.CLEAN_ID
  WHERE x.OPP > 0)
SELECT RULE,
       COUNT(*)                                         AS PEOPLE,
       ROUND(100 * MEDIAN(ABS_PCT_ERR), 1)              AS MEDIAN_ABS_PCT_ERROR,
       ROUND(100 * COUNT_IF(ABS_PCT_ERR > 0.10) / COUNT(*), 1) AS PCT_PEOPLE_OFF_BY_OVER_10PCT,
       ROUND(100 * COUNT_IF(ABS_PCT_ERR > 0.25) / COUNT(*), 1) AS PCT_PEOPLE_OFF_BY_OVER_25PCT,
       ROUND(CORR(EST, EXACT), 3)                       AS CORR_WITH_EXACT
FROM cmp
GROUP BY RULE
ORDER BY RULE;
