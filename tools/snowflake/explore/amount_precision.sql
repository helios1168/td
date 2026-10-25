-- Where do the decimals of MM_OPP, ACTUAL_SALES_AMOUNT and SALES_AMOUNT disappear?  23 and 24 round no amount; a
-- column type with too small a scale, in union_base or in UNION_OPP, would.  Safe to send back: types and counts.

-- 1.  Column types of the amounts in each table (scale = digits kept after the point).
SELECT TABLE_NAME, COLUMN_NAME, DATA_TYPE, NUMERIC_PRECISION, NUMERIC_SCALE
FROM ssdb_integration.INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = 'LR_STRATEGY'
  AND TABLE_NAME IN ('DATA_WITHNEWCHANNEL_UNION_W_JOINKEYS', 'UNION_BASE', 'UNION_OPP', 'OPP_ORIGINAL', 'OPP_MAPPED')
  AND COLUMN_NAME IN ('MM_OPP', 'ACTUAL_SALES_AMOUNT', 'SALES_AMOUNT', 'OPP')
ORDER BY COLUMN_NAME, TABLE_NAME;

-- 2.  Rows whose amount has a fractional part, per table.  A table with 0 where the table before it has some is where
--     the decimals were lost: source union -> union_base -> UNION_OPP (and opp_original -> UNION_OPP for firm_2).
SELECT 'a. source union' AS TBL,
       COUNT_IF(MM_OPP <> TRUNC(MM_OPP)) AS MM_OPP_WITH_DECIMALS, COUNT(MM_OPP) AS MM_OPP_ROWS,
       COUNT_IF(ACTUAL_SALES_AMOUNT <> TRUNC(ACTUAL_SALES_AMOUNT)) AS ACTUAL_SALES_WITH_DECIMALS, COUNT(ACTUAL_SALES_AMOUNT) AS ACTUAL_SALES_ROWS,
       COUNT_IF(SALES_AMOUNT <> TRUNC(SALES_AMOUNT)) AS SALES_AMOUNT_WITH_DECIMALS, COUNT(SALES_AMOUNT) AS SALES_AMOUNT_ROWS
FROM ssdb_integration.lr_strategy.data_withnewchannel_union_w_joinkeys
UNION ALL
SELECT 'b. union_base',
       COUNT_IF(MM_OPP <> TRUNC(MM_OPP)), COUNT(MM_OPP),
       COUNT_IF(ACTUAL_SALES_AMOUNT <> TRUNC(ACTUAL_SALES_AMOUNT)), COUNT(ACTUAL_SALES_AMOUNT),
       COUNT_IF(SALES_AMOUNT <> TRUNC(SALES_AMOUNT)), COUNT(SALES_AMOUNT)
FROM ssdb_integration.lr_strategy.union_base
UNION ALL
SELECT 'c. UNION_OPP, rows from union_base (MM_OPP: the ones without file opportunity)',   -- must equal b
       COUNT_IF(ROW_ORIGIN = 'union' AND MM_OPP <> TRUNC(MM_OPP)), COUNT(CASE WHEN ROW_ORIGIN = 'union' THEN MM_OPP END),
       COUNT_IF(ACTUAL_SALES_AMOUNT <> TRUNC(ACTUAL_SALES_AMOUNT)), COUNT(ACTUAL_SALES_AMOUNT),
       COUNT_IF(SALES_AMOUNT <> TRUNC(SALES_AMOUNT)), COUNT(SALES_AMOUNT)
FROM ssdb_integration.lr_strategy.UNION_OPP WHERE ROW_ORIGIN <> 'opp file'
UNION ALL
SELECT 'd. opp_original (OPP)', COUNT_IF(OPP <> TRUNC(OPP)), COUNT(OPP), NULL, NULL, NULL, NULL
FROM ssdb_integration.lr_strategy.opp_original
UNION ALL
SELECT 'e. UNION_OPP, rows carrying file opportunity',
       COUNT_IF(MM_OPP <> TRUNC(MM_OPP)), COUNT(MM_OPP), NULL, NULL, NULL, NULL
FROM ssdb_integration.lr_strategy.UNION_OPP WHERE ROW_ORIGIN <> 'union'
ORDER BY TBL;
