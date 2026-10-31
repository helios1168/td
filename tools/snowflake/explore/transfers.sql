--Transfers: how opportunity changes hands between wholesalers with the channel swap, from 01_opportunity_sales.sql's
--TMP_O2_DATASET (owner, 2026-10-30: "are we able to easily see how opportunity is transfered between wholesalers as it
--relates to the channel swaps?"; "no in the new combined dataset").  Run 01_opportunity_sales.sql first, in the same
--worksheet: this file reads its temporary tables.  Wholesaler names appear: read it at work, never bring it here.
--TMP_O2_DATASET holds each opportunity cell twice, under its old wholesaler (OPP_HELD_OLD) and its new one
--(OPP_HELD_NEW), on the same ZIP x firm x product x old channel x new channel key; grouping on that key puts giver and
--receiver back on one row.  Sales rows carry no opportunity and do not enter the pairing.  One result set:
--  TRANSFERS: opportunity that changes hands, by source x from wholesaler x to wholesaler x old channel (in firm 1's
--    names) x new channel; (NO HOLDER) where a side has none.  WHOLESALER_KEY / WHOLESALER: the giver; TO_KEY /
--    TO_WHOLESALER: the receiver.  Firm 1's key is the wholesaler ID, firm 2's the RVP (a move between two territories
--    of one RVP is no transfer).
--  BOOKS: each wholesaler's held opportunity before and after, the change, and the sales credited to them (which never
--    move).  The changes net to 0 within a source.
--Snowflake docs read 2026-10-30: GROUP BY ALL (https://docs.snowflake.com/en/sql-reference/constructs/group-by), IS
--DISTINCT FROM (.../functions/is-distinct-from), a set operator's columns one type each (.../operators-query).
use secondary roles all;

--1. Transfers.
CREATE OR REPLACE TEMPORARY TABLE ssdb_integration.lr_strategy.tmp_xfer_moves AS
WITH c AS (
  SELECT source, zip, firm_crd, broker_name, product, old_channel, old_channel_s1, new_channel,
         MAX(CASE WHEN opp_held_old <> 0 THEN wholesaler_key END) AS from_key,
         MAX(CASE WHEN opp_held_old <> 0 THEN wholesaler END) AS from_wholesaler,
         MAX(CASE WHEN opp_held_new <> 0 THEN wholesaler_key END) AS to_key,
         MAX(CASE WHEN opp_held_new <> 0 THEN wholesaler END) AS to_wholesaler,
         SUM(opp_held_old) AS opp
  FROM ssdb_integration.lr_strategy.tmp_o2_dataset
  GROUP BY ALL)
SELECT 'TRANSFERS' AS part, source, from_key AS wholesaler_key,
       COALESCE(from_wholesaler, from_key, '(NO HOLDER)') AS wholesaler, to_key,
       COALESCE(to_wholesaler, to_key, '(NO HOLDER)') AS to_wholesaler,
       COALESCE(old_channel_s1, '(BLANK)') AS old_channel_s1, new_channel, COUNT(*) AS cells,
       CAST(SUM(opp) AS DOUBLE) AS opp, CAST(NULL AS DOUBLE) AS old_book, CAST(NULL AS DOUBLE) AS new_book,
       CAST(NULL AS DOUBLE) AS change, CAST(NULL AS DECIMAL(38, 6)) AS sales
FROM c
WHERE from_key IS DISTINCT FROM to_key
GROUP BY ALL;

--2. Books.
CREATE OR REPLACE TEMPORARY TABLE ssdb_integration.lr_strategy.tmp_xfer_books AS
SELECT 'BOOKS' AS part, source, wholesaler_key, COALESCE(MIN(wholesaler), wholesaler_key, '(NO HOLDER)') AS wholesaler,
       CAST(NULL AS VARCHAR) AS to_key, CAST(NULL AS VARCHAR) AS to_wholesaler, CAST(NULL AS VARCHAR) AS old_channel_s1,
       CAST(NULL AS VARCHAR) AS new_channel, CAST(NULL AS BIGINT) AS cells, CAST(NULL AS DOUBLE) AS opp,
       CAST(SUM(opp_held_old) AS DOUBLE) AS old_book, CAST(SUM(opp_held_new) AS DOUBLE) AS new_book,
       CAST(SUM(opp_held_new) - SUM(opp_held_old) AS DOUBLE) AS change, CAST(SUM(sales) AS DECIMAL(38, 6)) AS sales
FROM ssdb_integration.lr_strategy.tmp_o2_dataset
GROUP BY source, wholesaler_key;

--3. Everything, one result set.
SELECT * FROM ssdb_integration.lr_strategy.tmp_xfer_moves
UNION ALL SELECT * FROM ssdb_integration.lr_strategy.tmp_xfer_books
ORDER BY part DESC, source, opp DESC NULLS LAST, change DESC NULLS LAST, wholesaler;
