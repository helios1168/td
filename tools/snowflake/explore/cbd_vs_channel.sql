-- Exploration (DuckDB, on the coded extract): firm_2 opportunity per person, by the current rule in 15
-- (A: ZIP_CODE x CHANNEL MM_OPP split over held DIST_CH by national sales mix) against a CBD_ID rule
-- (B: ZIP_CODE x CBD_ID MM_OPP to the DIST_CH firm_2 sells that CBD_ID through in that ZIP; else that
-- CBD_ID's national DIST_CH mix; else the CHANNEL mix).  Findings: DATASET_LOG.md, 2026-10-21.
--   duckdb -box < tools/snowflake/explore/cbd_vs_channel.sql      (run from the hub root)
ATTACH 'data/safe/extract_2026-10-20/ssdb.duckdb' AS s (READ_ONLY);
CREATE TEMP TABLE u AS SELECT * FROM s.lr_strategy.data_withnewchannel_union_w_joinkeys WHERE ZIP_CODE ~ '^[0-9]{5}$' AND ZIP_CODE <> '00000';
CREATE TEMP TABLE hold AS SELECT DISTINCT ZIP_CODE, CHANNEL AS DIST_CH, CLEAN_ID FROM s.lr_strategy.territories WHERE SOURCE = 'firm_2' AND CLEAN_ID IS NOT NULL;
CREATE TEMP TABLE prods AS SELECT DISTINCT PRODUCT_V2 FROM u WHERE SOURCE = 'firm_2' AND ACTUAL_SALES_AMOUNT > 0;
-- carrier MM_OPP in firm_2's products, per ZIP x CBD (CHANNEL comes with the CBD)
CREATE TEMP TABLE opp AS SELECT ZIP_CODE, CBD_ID, CHANNEL, SUM(MM_OPP) AS O FROM u
  WHERE SOURCE = 'firm_1' AND PRODUCT_V2 IN (SELECT * FROM prods) GROUP BY ALL HAVING SUM(MM_OPP) <> 0;
-- firm_2 positive sales by DIST_CH: per ZIP x CBD, per CBD, per CHANNEL
CREATE TEMP TABLE f2 AS SELECT ZIP_CODE, CBD_ID, CHANNEL, DIST_CH, SUM(ACTUAL_SALES_AMOUNT) AS S FROM u
  WHERE SOURCE = 'firm_2' AND ACTUAL_SALES_AMOUNT > 0 AND DIST_CH IS NOT NULL GROUP BY ALL;
CREATE TEMP TABLE mix_zc AS SELECT ZIP_CODE, CBD_ID, DIST_CH, S / SUM(S) OVER (PARTITION BY ZIP_CODE, CBD_ID) AS W FROM f2;
CREATE TEMP TABLE mix_c AS SELECT CBD_ID, DIST_CH, S / SUM(S) OVER (PARTITION BY CBD_ID) AS W FROM (SELECT CBD_ID, DIST_CH, SUM(S) AS S FROM f2 GROUP BY CBD_ID, DIST_CH);
CREATE TEMP TABLE mix_ch AS SELECT CHANNEL, DIST_CH, S / SUM(S) OVER (PARTITION BY CHANNEL) AS W FROM (SELECT CHANNEL, DIST_CH, SUM(S) AS S FROM f2 GROUP BY CHANNEL, DIST_CH);

-- A: current (15): ZIP x CHANNEL opp, split over the CHANNEL's DIST_CH held in the ZIP by national sales mix
CREATE TEMP TABLE a AS
WITH zc AS (SELECT ZIP_CODE, CHANNEL, SUM(O) AS O FROM opp GROUP BY ALL),
x AS (SELECT zc.ZIP_CODE, zc.CHANNEL, zc.O, m.DIST_CH, m.W, h.CLEAN_ID FROM zc JOIN mix_ch m USING (CHANNEL)
      JOIN (SELECT DISTINCT ZIP_CODE, DIST_CH, CLEAN_ID FROM hold) h ON h.ZIP_CODE = zc.ZIP_CODE AND h.DIST_CH = m.DIST_CH),
y AS (SELECT *, O * W / SUM(W) OVER (PARTITION BY ZIP_CODE, CHANNEL) AS PART FROM x)
SELECT CLEAN_ID, SUM(PART) AS OPP FROM y GROUP BY 1;
CREATE TEMP TABLE a_rows AS
WITH zc AS (SELECT ZIP_CODE, CHANNEL, SUM(O) AS O FROM opp GROUP BY ALL),
x AS (SELECT zc.ZIP_CODE, zc.CHANNEL, zc.O, m.DIST_CH, m.W FROM zc JOIN mix_ch m USING (CHANNEL)
      JOIN (SELECT DISTINCT ZIP_CODE, DIST_CH FROM hold) h ON h.ZIP_CODE = zc.ZIP_CODE AND h.DIST_CH = m.DIST_CH)
SELECT *, O * W / SUM(W) OVER (PARTITION BY ZIP_CODE, CHANNEL) AS PART FROM x;

-- B: CBD: the DIST_CH firm_2 sells that CBD through in that ZIP; else that CBD's national DIST_CH mix; else the CHANNEL mix
CREATE TEMP TABLE b_rows AS
WITH lvl AS (
  SELECT o.ZIP_CODE, o.CBD_ID, o.CHANNEL, o.O,
         CASE WHEN EXISTS (SELECT 1 FROM mix_zc z WHERE z.ZIP_CODE = o.ZIP_CODE AND z.CBD_ID = o.CBD_ID) THEN 1
              WHEN EXISTS (SELECT 1 FROM mix_c c WHERE c.CBD_ID = o.CBD_ID) THEN 2 ELSE 3 END AS LVL FROM opp o),
w AS (
  SELECT l.*, z.DIST_CH, z.W FROM lvl l JOIN mix_zc z ON z.ZIP_CODE = l.ZIP_CODE AND z.CBD_ID = l.CBD_ID WHERE LVL = 1
  UNION ALL SELECT l.*, c.DIST_CH, c.W FROM lvl l JOIN mix_c c ON c.CBD_ID = l.CBD_ID WHERE LVL = 2
  UNION ALL SELECT l.*, m.DIST_CH, m.W FROM lvl l JOIN mix_ch m ON m.CHANNEL = l.CHANNEL WHERE LVL = 3),
x AS (SELECT w.*, h.CLEAN_ID FROM w JOIN (SELECT DISTINCT ZIP_CODE, DIST_CH, CLEAN_ID FROM hold) h ON h.ZIP_CODE = w.ZIP_CODE AND h.DIST_CH = w.DIST_CH)
SELECT *, O * W / SUM(W) OVER (PARTITION BY ZIP_CODE, CBD_ID) AS PART FROM x;
CREATE TEMP TABLE b AS SELECT CLEAN_ID, SUM(PART) AS OPP FROM b_rows GROUP BY 1;

.print '== how much firm_2-product opportunity each CBD rule level covers'
WITH lv AS (SELECT DISTINCT ZIP_CODE, CBD_ID, O, LVL FROM b_rows)
SELECT CASE LVL WHEN 1 THEN '1 firm_2 sells that CBD in that ZIP' WHEN 2 THEN '2 firm_2 sells that CBD elsewhere' ELSE '3 firm_2 never sells that CBD' END AS rule,
       COUNT(*) AS zip_cbd_cells, ROUND(100 * SUM(O) / SUM(SUM(O)) OVER (), 1) AS pct_opp FROM lv GROUP BY 1 ORDER BY 1;
.print '== totals assigned (should be equal)'
SELECT ROUND((SELECT SUM(OPP) FROM a), 2) AS method_a, ROUND((SELECT SUM(OPP) FROM b), 2) AS method_b, ROUND((SELECT SUM(O) FROM opp), 2) AS opp_total;
.print '== per person: current method (A) vs CBD (B)'
WITH p AS (SELECT CLEAN_ID, COALESCE(a.OPP, 0) AS A, COALESCE(b.OPP, 0) AS B FROM a FULL JOIN b USING (CLEAN_ID)),
q AS (SELECT *, CASE WHEN A > 0 THEN B / A - 1 END AS CH FROM p)
SELECT COUNT(*) AS people, ROUND(CORR(A, B), 3) AS corr, ROUND(100 * MEDIAN(ABS(CH)), 1) AS median_abs_pct_change,
       COUNT_IF(ABS(CH) > 0.10) AS moved_over_10pct, COUNT_IF(ABS(CH) > 0.25) AS moved_over_25pct,
       ROUND(100 * SUM(ABS(B - A)) / 2 / SUM(A), 1) AS pct_of_opp_that_changes_hands FROM q;
.print '== per person, by DIST_CH combination'
WITH combo AS (SELECT CLEAN_ID, string_agg(DISTINCT DIST_CH, '+' ORDER BY DIST_CH) AS C FROM hold GROUP BY 1),
p AS (SELECT CLEAN_ID, COALESCE(a.OPP, 0) AS A, COALESCE(b.OPP, 0) AS B FROM a FULL JOIN b USING (CLEAN_ID))
SELECT c.C AS holds, COUNT(*) AS people, ROUND(100 * SUM(A) / (SELECT SUM(A) FROM p), 1) AS pct_opp_A, ROUND(100 * SUM(B) / (SELECT SUM(B) FROM p), 1) AS pct_opp_B,
       ROUND(100 * MEDIAN(B / NULLIF(A, 0) - 1), 1) AS median_pct_change
FROM p JOIN combo c USING (CLEAN_ID) GROUP BY 1 ORDER BY 2 DESC;
.print '== by DIST_CH: share of firm_2-product opportunity, A vs B, and of firm_2 sales'
SELECT DIST_CH, ROUND(100 * A / SUM(A) OVER (), 1) AS pct_A, ROUND(100 * B / SUM(B) OVER (), 1) AS pct_B, ROUND(100 * S / SUM(S) OVER (), 1) AS pct_firm_2_sales
FROM (SELECT DIST_CH, SUM(PART) A FROM a_rows GROUP BY 1) JOIN (SELECT DIST_CH, SUM(PART) B FROM b_rows GROUP BY 1) USING (DIST_CH)
JOIN (SELECT DIST_CH, SUM(S) S FROM f2 GROUP BY 1) USING (DIST_CH) ORDER BY 1;
