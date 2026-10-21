-- Exploration (DuckDB, on the coded extract): where the two firms meet at ZIP_CODE x CBD_ID x PRODUCT_V2.
-- Cells classed by who sells there (contested = both firms have positive net sales), at product level and
-- at ZIP_CODE x CBD_ID; then a "contestable by design" split: product both firms sell x CBD_ID both firms
-- sell to.  Findings: DATASET_LOG.md, 2026-10-21.
--   duckdb -box < tools/snowflake/explore/contested_cells.sql      (run from the hub root)
ATTACH 'data/safe/extract_2026-10-20/ssdb.duckdb' AS s (READ_ONLY);
CREATE TEMP TABLE u AS SELECT * FROM s.lr_strategy.data_withnewchannel_union_w_joinkeys WHERE ZIP_CODE ~ '^[0-9]{5}$' AND ZIP_CODE <> '00000';
-- one row per ZIP x CBD x PRODUCT: the market (carrier MM_OPP) and each firm's net sales
CREATE TEMP TABLE cell AS
SELECT ZIP_CODE, CBD_ID, PRODUCT_V2, ANY_VALUE(CHANNEL) AS CHANNEL,
       COALESCE(SUM(MM_OPP), 0) AS OPP,
       COALESCE(SUM(ACTUAL_SALES_AMOUNT) FILTER (WHERE SOURCE = 'firm_1'), 0) AS S1,
       COALESCE(SUM(ACTUAL_SALES_AMOUNT) FILTER (WHERE SOURCE = 'firm_2'), 0) AS S2
FROM u GROUP BY ZIP_CODE, CBD_ID, PRODUCT_V2;
CREATE TEMP TABLE c AS SELECT *, CASE WHEN S1 > 0 AND S2 > 0 THEN '1 contested: both sell'
  WHEN S1 > 0 THEN '2 firm_1 only sells' WHEN S2 > 0 THEN '3 firm_2 only sells'
  WHEN OPP <> 0 THEN '4 nobody sells (MM_OPP only)' ELSE '5 empty' END AS CLS FROM cell;
.print '== excluded: bad ZIP rows, share of each firm''s sales'
SELECT SOURCE, ROUND(100*SUM(ACTUAL_SALES_AMOUNT) FILTER (WHERE NOT (ZIP_CODE ~ '^[0-9]{5}$' AND ZIP_CODE <> '00000'))/SUM(ACTUAL_SALES_AMOUNT),2) pct FROM s.lr_strategy.data_withnewchannel_union_w_joinkeys GROUP BY 1;
.print '== ZIP x CBD x PRODUCT cells'
SELECT CLS, COUNT(*) cells, ROUND(100*SUM(OPP)/(SELECT SUM(OPP) FROM c),1) pct_mm_opp,
       ROUND(100*SUM(S1)/(SELECT SUM(S1) FROM c),1) pct_f1_sales, ROUND(100*SUM(S2)/(SELECT SUM(S2) FROM c),1) pct_f2_sales
FROM c GROUP BY 1 ORDER BY 1;
.print '== contested cells with no MM_OPP (both sell, no market number)'
SELECT COUNT(*) cells, ROUND(100*SUM(S1)/(SELECT SUM(S1) FROM c),2) pct_f1_sales, ROUND(100*SUM(S2)/(SELECT SUM(S2) FROM c),2) pct_f2_sales FROM c WHERE CLS LIKE '1%' AND OPP <= 0;
.print '== by product'
SELECT PRODUCT_V2, CLS, COUNT(*) cells, ROUND(100*SUM(OPP)/(SELECT SUM(OPP) FROM c),1) pct_mm_opp,
       ROUND(100*SUM(S1)/(SELECT SUM(S1) FROM c),1) pct_f1, ROUND(100*SUM(S2)/(SELECT SUM(S2) FROM c),1) pct_f2
FROM c WHERE CLS NOT LIKE '5%' GROUP BY ALL ORDER BY ALL;
.print '== coarser: ZIP x CBD (any product)'
WITH zc AS (SELECT ZIP_CODE, CBD_ID, SUM(OPP) OPP, SUM(S1) S1, SUM(S2) S2 FROM cell GROUP BY ALL)
SELECT CASE WHEN S1>0 AND S2>0 THEN '1 both sell' WHEN S1>0 THEN '2 firm_1 only' WHEN S2>0 THEN '3 firm_2 only' WHEN OPP<>0 THEN '4 nobody' ELSE '5 empty' END cls,
       COUNT(*) cells, ROUND(100*SUM(OPP)/(SELECT SUM(OPP) FROM cell),1) pct_mm_opp, ROUND(100*SUM(S1)/(SELECT SUM(S1) FROM cell),1) pct_f1, ROUND(100*SUM(S2)/(SELECT SUM(S2) FROM cell),1) pct_f2
FROM zc GROUP BY 1 ORDER BY 1;
.print '== contested cells by CHANNEL'
SELECT CHANNEL, COUNT(*) cells, ROUND(100*SUM(OPP)/SUM(SUM(OPP)) OVER (),1) pct_contested_opp, ROUND(100*SUM(S1)/SUM(SUM(S1)) OVER (),1) pct_contested_f1, ROUND(100*SUM(S2)/SUM(SUM(S2)) OVER (),1) pct_contested_f2,
       ROUND(SUM(S1)/NULLIF(SUM(OPP),0) / (SUM(S2)/NULLIF(SUM(OPP),0)),2) f1_to_f2_sales_ratio
FROM c WHERE CLS LIKE '1%' GROUP BY 1 ORDER BY 1;
.print '== per seller: share of own sales in contested cells'
WITH r AS (SELECT u.SOURCE, u.SALES_WHOLESALER_TERRITORY_ID ID, SUM(u.ACTUAL_SALES_AMOUNT) S,
           SUM(u.ACTUAL_SALES_AMOUNT) FILTER (WHERE c.CLS LIKE '1%') SC
           FROM u JOIN c USING (ZIP_CODE, CBD_ID, PRODUCT_V2) WHERE u.ACTUAL_SALES_AMOUNT IS NOT NULL AND u.SALES_WHOLESALER_TERRITORY_ID IS NOT NULL GROUP BY ALL HAVING SUM(u.ACTUAL_SALES_AMOUNT) > 0)
SELECT SOURCE, COUNT(*) sellers, COUNT_IF(COALESCE(SC,0) > 0) with_contested, ROUND(100*QUANTILE_CONT(COALESCE(SC,0)/S, 0.1),1) p10_pct,
       ROUND(100*MEDIAN(COALESCE(SC,0)/S),1) median_pct, ROUND(100*QUANTILE_CONT(COALESCE(SC,0)/S, 0.9),1) p90_pct,
       COUNT_IF(COALESCE(SC,0)/S < 0.10) under_10pct FROM r GROUP BY 1 ORDER BY 1;
.print '== in contested cells: can each firm''s DIST_CH and holder be read off its own rows?'
WITH k AS (SELECT ZIP_CODE, CBD_ID, PRODUCT_V2 FROM c WHERE CLS LIKE '1%'),
r AS (SELECT u.SOURCE, u.ZIP_CODE, u.CBD_ID, u.PRODUCT_V2, COUNT(DISTINCT u.DIST_CH) FILTER (WHERE u.ACTUAL_SALES_AMOUNT>0 OR COALESCE(u.MM_OPP,0)<>0) d
      FROM u JOIN k USING (ZIP_CODE, CBD_ID, PRODUCT_V2) GROUP BY ALL)
SELECT SOURCE, COUNT(*) cells, COUNT_IF(d=1) one_dist_ch, COUNT_IF(d>1) two_plus FROM r GROUP BY 1;
CREATE TEMP TABLE p_both AS SELECT PRODUCT_V2 FROM u WHERE ACTUAL_SALES_AMOUNT > 0 GROUP BY 1 HAVING COUNT(DISTINCT SOURCE) = 2;
CREATE TEMP TABLE cbd_both AS SELECT CBD_ID FROM u WHERE ACTUAL_SALES_AMOUNT > 0 GROUP BY 1 HAVING COUNT(DISTINCT SOURCE) = 2;
.print '== contestable by design: product both firms sell x CBD_ID both firms sell to'
SELECT CASE WHEN PRODUCT_V2 IN (SELECT * FROM p_both) AND CBD_ID IN (SELECT * FROM cbd_both) THEN '1 shared product, shared CBD'
            WHEN PRODUCT_V2 IN (SELECT * FROM p_both) THEN '2 shared product, CBD only one firm (or neither) sells to'
            ELSE '3 product only one firm sells (or neither)' END AS segment,
       COUNT(*) cells, ROUND(100*SUM(OPP)/(SELECT SUM(OPP) FROM c),1) pct_mm_opp,
       ROUND(100*SUM(S1)/(SELECT SUM(S1) FROM c),1) pct_f1_sales, ROUND(100*SUM(S2)/(SELECT SUM(S2) FROM c),1) pct_f2_sales,
       ROUND((SUM(S1)/NULLIF(SUM(OPP),0)) / NULLIF(SUM(S2)/NULLIF(SUM(OPP),0),0),2) f1_to_f2_sales_ratio
FROM c GROUP BY 1 ORDER BY 1;
-- IFA against National + WH + FI (2026-10-21)
CREATE TEMP TABLE x AS SELECT *, CASE WHEN CHANNEL = 'IFA' THEN 'IFA' ELSE 'non-IFA' END AS GRP,
  CASE WHEN S1 > 0 AND S2 > 0 THEN 'both sell' WHEN S1 > 0 THEN 'firm_1 only sells' WHEN S2 > 0 THEN 'firm_2 only sells' WHEN OPP <> 0 THEN 'nobody sells' END AS D1,
  CASE WHEN PRODUCT_V2 IN (SELECT * FROM p_both) AND CBD_ID IN (SELECT * FROM cbd_both) THEN '1 shared product x shared CBD'
       WHEN PRODUCT_V2 IN (SELECT * FROM p_both) THEN '2 shared product, CBD one firm' ELSE '3 product one firm only' END AS D2
FROM cell;
CREATE TEMP TABLE g AS SELECT GRP, SUM(OPP) TO_, SUM(S1) T1, SUM(S2) T2 FROM x GROUP BY 1;
.print '== IFA vs non-IFA: share of the total'
SELECT GRP, ROUND(100*TO_/SUM(TO_) OVER (),1) pct_mm_opp, ROUND(100*T1/SUM(T1) OVER (),1) pct_f1, ROUND(100*T2/SUM(T2) OVER (),1) pct_f2 FROM g ORDER BY 1;
.print '== definition 1 (who sold), shares within the group'
SELECT x.GRP, D1, COUNT(*) cells, ROUND(100*SUM(OPP)/ANY_VALUE(TO_),1) pct_opp, ROUND(100*SUM(S1)/ANY_VALUE(T1),1) pct_f1, ROUND(100*SUM(S2)/ANY_VALUE(T2),1) pct_f2
FROM x JOIN g USING (GRP) WHERE D1 IS NOT NULL GROUP BY x.GRP, D1 ORDER BY 1, 2;
.print '== definition 2 (who offers), shares within the group'
SELECT x.GRP, D2, COUNT(*) cells, ROUND(100*SUM(OPP)/ANY_VALUE(TO_),1) pct_opp, ROUND(100*SUM(S1)/ANY_VALUE(T1),1) pct_f1, ROUND(100*SUM(S2)/ANY_VALUE(T2),1) pct_f2,
       ROUND(SUM(S1)/NULLIF(SUM(S2),0),2) f1_over_f2 FROM x JOIN g USING (GRP) GROUP BY x.GRP, D2 ORDER BY 1, 2;
