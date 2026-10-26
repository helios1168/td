-- Is the union's ADDRESS_ID the person's CLEAN_ID (the address table is keyed by CLEAN_ID, like territories; owner,
-- 2026-10-26)?  If yes, UNION_OPP's opp-only rows can carry the holder's CLEAN_ID as their ADDRESS_ID directly.
-- Safe to send back: counts only.

-- 1.  *_EQ_* = *_FILLED means the same ID; 0 or low means the address table has its own CLEAN_ID.
WITH t AS (SELECT DISTINCT SOURCE, TO_CHAR(CLEAN_ID) AS CLEAN_ID FROM ssdb_integration.lr_strategy.territories WHERE CLEAN_ID IS NOT NULL)
SELECT u.SOURCE, COUNT(*) AS N_ROWS,
       COUNT(u.TERRITORY_WHOLESALER_ADDRESS_ID) AS TERR_ADDR_FILLED,
       COUNT_IF(TO_CHAR(u.TERRITORY_WHOLESALER_ADDRESS_ID) = TO_CHAR(u.TERRITORY_WHOLESALER_TERRITORY_ID)) AS TERR_ADDR_EQ_TERR_ID,
       COUNT(u.SALES_WHOLESALER_ADDRESS_ID) AS SALES_ADDR_FILLED,
       COUNT_IF(TO_CHAR(u.SALES_WHOLESALER_ADDRESS_ID) = TO_CHAR(u.SALES_WHOLESALER_TERRITORY_ID)) AS SALES_ADDR_EQ_SALES_ID,
       COUNT(t.CLEAN_ID) AS TERR_ADDR_IS_A_TERRITORIES_CLEAN_ID
FROM ssdb_integration.lr_strategy.union_base u
LEFT JOIN t ON t.SOURCE = u.SOURCE AND t.CLEAN_ID = TO_CHAR(u.TERRITORY_WHOLESALER_ADDRESS_ID)
GROUP BY u.SOURCE
ORDER BY u.SOURCE;

-- 2.  Where the two IDs differ (owner's run of 1, 2026-10-26: same ID on 90.5% of firm_1's rows with an address ID,
-- 77.5% of firm_2's; an address ID that is a territories CLEAN_ID is always the row's own).  Territory side, by row
-- type and by whether the row's territory ID is a territories CLEAN_ID (an opp-only row of UNION_OPP always has one).
WITH t AS (SELECT DISTINCT SOURCE, TO_CHAR(CLEAN_ID) AS CLEAN_ID FROM ssdb_integration.lr_strategy.territories WHERE CLEAN_ID IS NOT NULL),
x AS (
  SELECT u.SOURCE,
         CASE WHEN u.MM_OPP IS NOT NULL AND u.ACTUAL_SALES_AMOUNT IS NULL THEN 'opp-only' ELSE 'sales' END AS ROW_TYPE,
         CASE WHEN u.TERRITORY_WHOLESALER_TERRITORY_ID IS NULL THEN 'no territory ID'
              WHEN t.CLEAN_ID IS NULL THEN 'territory ID not in territories'
              ELSE 'territory ID in territories' END AS TERR_ID,
         CASE WHEN u.TERRITORY_WHOLESALER_ADDRESS_ID IS NULL THEN 'no address ID'
              WHEN TO_CHAR(u.TERRITORY_WHOLESALER_ADDRESS_ID) = TO_CHAR(u.TERRITORY_WHOLESALER_TERRITORY_ID) THEN 'address ID = territory ID'
              ELSE 'address ID differs' END AS ADDR
  FROM ssdb_integration.lr_strategy.union_base u
  LEFT JOIN t ON t.SOURCE = u.SOURCE AND t.CLEAN_ID = TO_CHAR(u.TERRITORY_WHOLESALER_TERRITORY_ID))
SELECT SOURCE, ROW_TYPE, TERR_ID, ADDR, COUNT(*) AS N_ROWS
FROM x
GROUP BY SOURCE, ROW_TYPE, TERR_ID, ADDR
ORDER BY SOURCE, ROW_TYPE, TERR_ID, ADDR;
