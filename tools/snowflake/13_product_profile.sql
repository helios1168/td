-- Product sets: which products carry opportunity, and which firm sells them.  Reads the source table
-- only.  Shares and counts per product, firms as firm_1 / firm_2; rename any product value you would
-- rather not share before passing the output on.
--   a product with sales from one firm only -> that firm's set
--   a product with sales but pct_of_opportunity = 0 -> its sales have nothing to be measured against
WITH
s AS (
  SELECT SOURCE AS firm, PRODUCT_V2 AS product, MM_OPP AS opp, ACTUAL_SALES_AMOUNT AS sales
  FROM ssdb_integration.lr_strategy.data_withnewchannel_union_w_joinkeys),
f AS (
  SELECT firm, 'firm_' || DENSE_RANK() OVER (ORDER BY firm) AS firm_label
  FROM (SELECT DISTINCT firm FROM s WHERE firm IS NOT NULL) x),
p AS (
  SELECT s.product,
         SUM(COALESCE(s.opp, 0))                                              AS opp,
         SUM(CASE WHEN f.firm_label = 'firm_1' THEN s.sales ELSE 0 END)       AS sales_1,
         SUM(CASE WHEN f.firm_label = 'firm_2' THEN s.sales ELSE 0 END)       AS sales_2,
         COUNT_IF(COALESCE(s.opp, 0) <> 0)                                    AS rows_with_opp,
         COUNT_IF(f.firm_label = 'firm_1' AND COALESCE(s.opp, 0) <> 0)        AS opp_rows_on_firm_1,
         COUNT_IF(f.firm_label = 'firm_2' AND COALESCE(s.opp, 0) <> 0)        AS opp_rows_on_firm_2
  FROM s JOIN f ON f.firm = s.firm
  GROUP BY s.product)
SELECT product,
       ROUND(100 * opp     / NULLIF(SUM(opp)     OVER (), 0), 2) AS pct_of_opportunity,
       ROUND(100 * sales_1 / NULLIF(SUM(sales_1) OVER (), 0), 2) AS pct_of_firm_1_sales,
       ROUND(100 * sales_2 / NULLIF(SUM(sales_2) OVER (), 0), 2) AS pct_of_firm_2_sales,
       rows_with_opp, opp_rows_on_firm_1, opp_rows_on_firm_2
FROM p
ORDER BY product;
