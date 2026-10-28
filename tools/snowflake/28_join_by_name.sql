use secondary roles all;

--A union table with its territory and address IDs, joined on name through NAME_XWALK (27_name_xwalk.sql: run it
--first).  Run once per firm.  Fill in every <...>: the labels exactly as SRC_TABLE in 26's input, the territory and
--address tables' name and ID columns, and the table to write.  Run All: statement 1 writes the table, statement 2
--checks it (MUST_BE_ZERO rows must be 0).
--Every union row is kept once: NAME_XWALK has at most one matched row per name x target column, and the territory
--and address tables are taken to one row per name first (the territory table has one row per ZIP_CODE x channel, so
--joining it directly would multiply the union rows).  A name carrying 2+ IDs gets a NULL ID, not a pick.  Unmatched
--names ('open', review, none) get NULL IDs; a review pair confirmed in 27's statement 3 is picked up on the next run.
--The *_MATCH columns say how each ID was found (27's STEP).

--Statement 1.
CREATE OR REPLACE TABLE ssdb_integration.lr_strategy.<output table> AS
WITH
x AS (   -- matched pairs only
  SELECT FROM_TABLE, FROM_COLUMN, FROM_NAME, TO_TABLE, TO_COLUMN, TO_NAME, STEP
  FROM ssdb_integration.lr_strategy.NAME_XWALK
  WHERE STATUS = 'matched'),
terr AS (   -- one row per territory name; the ID only where the name has exactly one
  SELECT <terr name col> AS NAME,
         CASE WHEN COUNT(DISTINCT <terr id col>) = 1 THEN MIN(<terr id col>) END AS TERR_ID
  FROM ssdb_integration.lr_strategy.<territory table>
  GROUP BY <terr name col>),
addr AS (   -- the same for the address table
  SELECT <addr name col> AS NAME,
         CASE WHEN COUNT(DISTINCT <addr id col>) = 1 THEN MIN(<addr id col>) END AS ADDR_ID
  FROM ssdb_integration.lr_strategy.<address table>
  GROUP BY <addr name col>)
SELECT u.*,
       th.TERR_ID AS TERRITORY_WHOLESALER_TERRITORY_ID,
       ah.ADDR_ID AS TERRITORY_WHOLESALER_ADDRESS_ID,
       ts.TERR_ID AS SALES_WHOLESALER_TERRITORY_ID,
       sa.ADDR_ID AS SALES_WHOLESALER_ADDRESS_ID,
       xht.STEP AS HOLDER_TERR_MATCH, xha.STEP AS HOLDER_ADDR_MATCH,
       xst.STEP AS SELLER_TERR_MATCH, xsa.STEP AS SELLER_ADDR_MATCH
FROM ssdb_integration.lr_strategy.<union table> u
-- the territory holder (updated_wholesaler2026) -> territory and address
LEFT JOIN x xht ON xht.FROM_TABLE = '<union label>' AND xht.FROM_COLUMN = 'updated_wholesaler2026'
               AND xht.FROM_NAME = u.updated_wholesaler2026 AND xht.TO_TABLE = '<terr label>'
LEFT JOIN terr th ON th.NAME = xht.TO_NAME
LEFT JOIN x xha ON xha.FROM_TABLE = '<union label>' AND xha.FROM_COLUMN = 'updated_wholesaler2026'
               AND xha.FROM_NAME = u.updated_wholesaler2026 AND xha.TO_TABLE = '<addr label>'
LEFT JOIN addr ah ON ah.NAME = xha.TO_NAME
-- the seller (wholesaler_name) -> territory and address
LEFT JOIN x xst ON xst.FROM_TABLE = '<union label>' AND xst.FROM_COLUMN = 'wholesaler_name'
               AND xst.FROM_NAME = u.wholesaler_name AND xst.TO_TABLE = '<terr label>'
LEFT JOIN terr ts ON ts.NAME = xst.TO_NAME
LEFT JOIN x xsa ON xsa.FROM_TABLE = '<union label>' AND xsa.FROM_COLUMN = 'wholesaler_name'
               AND xsa.FROM_NAME = u.wholesaler_name AND xsa.TO_TABLE = '<addr label>'
LEFT JOIN addr sa ON sa.NAME = xsa.TO_NAME;

--Statement 2.  Checks.
WITH
o AS (SELECT * FROM ssdb_integration.lr_strategy.<output table>),
t AS (SELECT COUNT(*) AS N FROM o)
SELECT 'rows: output minus the union table' AS CHECK_NAME,
       (SELECT N FROM t) - (SELECT COUNT(*) FROM ssdb_integration.lr_strategy.<union table>) AS VALUE, TRUE AS MUST_BE_ZERO
UNION ALL SELECT '% of rows with TERRITORY_WHOLESALER_TERRITORY_ID', ROUND(100 * COUNT(TERRITORY_WHOLESALER_TERRITORY_ID) / (SELECT N FROM t), 1), FALSE FROM o
UNION ALL SELECT '% of rows with TERRITORY_WHOLESALER_ADDRESS_ID', ROUND(100 * COUNT(TERRITORY_WHOLESALER_ADDRESS_ID) / (SELECT N FROM t), 1), FALSE FROM o
UNION ALL SELECT '% of rows with SALES_WHOLESALER_TERRITORY_ID', ROUND(100 * COUNT(SALES_WHOLESALER_TERRITORY_ID) / (SELECT N FROM t), 1), FALSE FROM o
UNION ALL SELECT '% of rows with SALES_WHOLESALER_ADDRESS_ID', ROUND(100 * COUNT(SALES_WHOLESALER_ADDRESS_ID) / (SELECT N FROM t), 1), FALSE FROM o
UNION ALL SELECT 'rows whose holder matched a territory name with 2+ IDs (ID left NULL)',
       COUNT_IF(HOLDER_TERR_MATCH IS NOT NULL AND TERRITORY_WHOLESALER_TERRITORY_ID IS NULL), FALSE FROM o
UNION ALL SELECT 'rows whose seller matched a territory name with 2+ IDs (ID left NULL)',
       COUNT_IF(SELLER_TERR_MATCH IS NOT NULL AND SALES_WHOLESALER_TERRITORY_ID IS NULL), FALSE FROM o;
