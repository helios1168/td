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

-- 3.  Query 2 at work (owner, 2026-10-26) put every union_base row under 'sales': no row has MM_OPP with a NULL
-- ACTUAL_SALES_AMOUNT.  How MM_OPP and ACTUAL_SALES_AMOUNT are filled, per SOURCE.
WITH x AS (
  SELECT SOURCE,
         CASE WHEN MM_OPP IS NULL THEN 'NULL' WHEN MM_OPP = 0 THEN '0' ELSE 'value' END AS OPP_IS,
         CASE WHEN ACTUAL_SALES_AMOUNT IS NULL THEN 'NULL' WHEN ACTUAL_SALES_AMOUNT = 0 THEN '0' ELSE 'value' END AS SALES_IS
  FROM ssdb_integration.lr_strategy.union_base)
SELECT SOURCE, OPP_IS, SALES_IS, COUNT(*) AS N_ROWS
FROM x
GROUP BY SOURCE, OPP_IS, SALES_IS
ORDER BY SOURCE, OPP_IS, SALES_IS;

-- 4.  Per person (territory ID): which address ID the union gives them on the territory side.  'always one other ID'
-- = a person whose address ID is consistently not their CLEAN_ID; 'own ID on some rows' = mixed.
WITH p AS (
  SELECT SOURCE, TO_CHAR(TERRITORY_WHOLESALER_TERRITORY_ID) AS ID, COUNT(*) AS N_ROWS,
         COUNT(TERRITORY_WHOLESALER_ADDRESS_ID) AS N_ADDR,
         COUNT_IF(TO_CHAR(TERRITORY_WHOLESALER_ADDRESS_ID) = TO_CHAR(TERRITORY_WHOLESALER_TERRITORY_ID)) AS N_SAME,
         COUNT(DISTINCT CASE WHEN TO_CHAR(TERRITORY_WHOLESALER_ADDRESS_ID) <> TO_CHAR(TERRITORY_WHOLESALER_TERRITORY_ID)
                             THEN TO_CHAR(TERRITORY_WHOLESALER_ADDRESS_ID) END) AS N_OTHER
  FROM ssdb_integration.lr_strategy.union_base
  WHERE TERRITORY_WHOLESALER_TERRITORY_ID IS NOT NULL
  GROUP BY SOURCE, TO_CHAR(TERRITORY_WHOLESALER_TERRITORY_ID)),
q AS (
  SELECT SOURCE, N_ROWS, N_ADDR,
         CASE WHEN N_ADDR = 0 THEN 'no address ID'
              WHEN N_SAME = N_ADDR THEN 'always own ID'
              WHEN N_SAME = 0 AND N_OTHER = 1 THEN 'always one other ID'
              WHEN N_SAME = 0 THEN '2+ other IDs'
              ELSE 'own ID on some rows, another on others' END AS PERSON
  FROM p)
SELECT SOURCE, PERSON, COUNT(*) AS N_PEOPLE, SUM(N_ROWS) AS N_ROWS, SUM(N_ROWS - N_ADDR) AS N_ROWS_NO_ADDRESS
FROM q
GROUP BY SOURCE, PERSON
ORDER BY SOURCE, PERSON;
