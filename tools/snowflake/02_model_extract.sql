use role rl_ssdb_Integration_Lr_Strategy_Rw;
use database ssdb_Integration;
use schema lr_strategy;

--The opportunity-only model extract for td (td.data.load, format td_instance_descaled/3), one Run All file, one result set.
--The owner edits the first two SET lines below to the real table names, nothing else (owner's names, 2026-11-09, schema
--lr_strategy assumed as for every other table: correct it there if not).  It reads only those two tables, plus the holder key
--below: no sales, no wholesaler name, no firm name or ID leaves Snowflake.  Download the result as CSV into $TD_REPO/data/safe/ and
--run model_extract.py on it.
--Result, under LAYER (all layers share the column list, NULL where a layer has no such column):
--  OPP    SOURCE, ZIP_CODE, DIST_CH, NEW_DIST, CHANNEL, MM_OPP, N_CELLS: the opportunity once per cell.  The union table
--         repeats a cell's MM_OPP on one row per holder pair (01_opportunity_sales.sql statement 17), so a cell is
--         one row-set of the columns below (every column except wholesaler, holder, ID, address and has-territory
--         columns, the measures and the lineage flags): SOURCE, FISCAL_YR, ZIP_CODE, CBD_ID, FIRM, PARENT, FIRM_KEY,
--         FIRM_CRD, PRODUCT_V2, DIST_CH, NEW_DIST, FILE_NEW_DIST, CHANNEL, NEW_TERR_CHANNEL.  The cell's opportunity is
--         the MAX of its positive MM_OPP, summed to SOURCE x ZIP_CODE x DIST_CH x NEW_DIST x CHANNEL.  N_CELLS: cells
--         summed.  A row with MM_OPP of 0 or NULL (a sales-only row) adds nothing.  FIRM and CBD_ID never leave.
--  TERR   SOURCE, ZIP_CODE, STATE, CHANNEL, HOLDER: who holds each ZIP x channel, HOLDER a surrogate R<n> of the holder id
--         from the holder key (below), neither the id nor NAME appears.  The holder id is CLEAN_ID, or when CLEAN_ID is NULL or
--         blank the UUID of CLEAN_NAME, the owner's own definition (uni_latest.sql:130, UUID_STRING over the namespace below), so a
--         later populated CLEAN_ID gets the same number.  A row whose CLEAN_NAME is 'open' is a vacancy: no holder, never keyed.
--         Vacancies and rows with neither id nor name are left out and counted in CHECKS.
--  CHECKS NAME, VALUE (a count unless NAME says otherwise), MM_OPP where the check has an amount, per SOURCE.
--         MUST_BE_ZERO = 1 rows must have VALUE 0: model_extract.py refuses the file otherwise.
--ZIP_CODE is LPAD(LEFT(TRIM(..), 5), 5, '0') on both tables.
--The holder key (owner, 2026-11-09: stable mapping in Snowflake for wholesalers): the permanent table holder_tbl, one row per
--SOURCE x holder id (column clean_id) with its number holder_n, so R<n> is the same wholesaler in every run.  The first run numbers every holder
--in SOURCE, holder id order, later runs add only the pairs not yet in it as max + 1 onward.  Rows are never updated or deleted,
--a holder who leaves the territories table keeps their number and it is never reused.  Never DROP or CREATE OR REPLACE it,
--that renumbers everyone.  It is the de-masking key: it stays in Snowflake, never export or download it.  It is keyed on
--SOURCE x holder id, the id being the UUID of the clean name, so a change in the name cleaning gives a holder a new number.
--The result SELECT must stay the last statement, Run All shows one result.

SET union_tbl = 'ssdb_integration.lr_strategy.sales_opp_2026_11_9';
SET terr_tbl  = 'ssdb_integration.lr_strategy.territories_tableau';
SET holder_tbl = 'ssdb_integration.lr_strategy.td_holder_key';

CREATE TABLE IF NOT EXISTS IDENTIFIER($holder_tbl) (source VARCHAR, clean_id VARCHAR, holder_n INTEGER, first_seen TIMESTAMP_NTZ);

INSERT INTO IDENTIFIER($holder_tbl)
SELECT s.source, s.clean_id,
       COALESCE((SELECT MAX(holder_n) FROM IDENTIFIER($holder_tbl)), 0) + ROW_NUMBER() OVER (ORDER BY s.source, s.clean_id),
       CURRENT_TIMESTAMP()
FROM (SELECT DISTINCT source, hid AS clean_id
      FROM (SELECT source, CASE WHEN LOWER(TRIM(clean_name)) = 'open' THEN NULL
                                ELSE COALESCE(NULLIF(TRIM(clean_id), ''), UUID_STRING('6ba7b810-9dad-11d1-80b4-00c04fd430c8', NULLIF(TRIM(clean_name), ''))) END AS hid
            FROM IDENTIFIER($terr_tbl))
      WHERE hid IS NOT NULL AND source IS NOT NULL) s
LEFT JOIN IDENTIFIER($holder_tbl) k ON k.source = s.source AND k.clean_id = s.clean_id
WHERE k.clean_id IS NULL;

WITH
u AS (SELECT source, fiscal_yr, LPAD(LEFT(TRIM(zip_code), 5), 5, '0') AS zip_code, cbd_id, firm, parent, firm_key,
             firm_crd, product_v2, dist_ch, new_dist, file_new_dist, channel, new_terr_channel, mm_opp, n_holders
      FROM IDENTIFIER($union_tbl)),
r AS (SELECT u.*, COUNT(CASE WHEN mm_opp > 0 THEN 1 END) OVER (PARTITION BY source, fiscal_yr, zip_code, cbd_id, firm,
                     parent, firm_key, firm_crd, product_v2, dist_ch, new_dist, file_new_dist, channel,
                     new_terr_channel) AS n_rep
      FROM u),
cell AS (SELECT source, zip_code, dist_ch, new_dist, channel, MAX(CASE WHEN mm_opp > 0 THEN mm_opp END) AS opp,
                MIN(CASE WHEN mm_opp > 0 THEN mm_opp END) AS opp_min,
                COUNT(CASE WHEN mm_opp > 0 AND n_holders IS NOT NULL AND n_holders <> n_rep THEN 1 END) AS n_disagree
         FROM r
         GROUP BY source, fiscal_yr, zip_code, cbd_id, firm, parent, firm_key, firm_crd, product_v2, dist_ch, new_dist,
                  file_new_dist, channel, new_terr_channel
         HAVING MAX(CASE WHEN mm_opp > 0 THEN mm_opp END) IS NOT NULL),
t AS (SELECT source, LPAD(LEFT(TRIM(zip_code), 5), 5, '0') AS zip_code, state, channel,
             COALESCE(LOWER(TRIM(clean_name)) = 'open', FALSE) AS is_open, NULLIF(TRIM(clean_id), '') IS NULL AS no_cid,
             CASE WHEN LOWER(TRIM(clean_name)) = 'open' THEN NULL
                  ELSE COALESCE(NULLIF(TRIM(clean_id), ''), UUID_STRING('6ba7b810-9dad-11d1-80b4-00c04fd430c8', NULLIF(TRIM(clean_name), ''))) END AS hid
      FROM IDENTIFIER($terr_tbl)),
th AS (SELECT source, zip_code, channel, COUNT(DISTINCT hid) AS n FROM t WHERE hid IS NOT NULL
       GROUP BY source, zip_code, channel),
hk AS (SELECT source, clean_id, holder_n, first_seen FROM IDENTIFIER($holder_tbl)),
hd AS (SELECT holder_n, COUNT(*) AS n FROM hk GROUP BY holder_n)
--OPP
SELECT 'OPP' AS layer, source, CAST(NULL AS VARCHAR) AS name, zip_code, CAST(NULL AS VARCHAR) AS state, dist_ch, new_dist,
       channel, CAST(NULL AS VARCHAR) AS holder, SUM(opp) AS mm_opp, COUNT(*) AS n_cells, CAST(NULL AS DOUBLE) AS value,
       CAST(NULL AS INTEGER) AS must_be_zero
FROM cell GROUP BY source, zip_code, dist_ch, new_dist, channel
UNION ALL
--TERR
SELECT 'TERR', t.source, NULL, t.zip_code, t.state, NULL, NULL, t.channel, 'R' || hk.holder_n, NULL, NULL, NULL, NULL
FROM t JOIN hk ON hk.source = t.source AND hk.clean_id = t.hid
WHERE t.hid IS NOT NULL
GROUP BY t.source, t.zip_code, t.state, t.channel, hk.holder_n
UNION ALL
--CHECKS
SELECT 'CHECKS', source, 'OPP RAW SUM(MM_OPP)', NULL, NULL, NULL, NULL, NULL, NULL, SUM(mm_opp), NULL, NULL, 0
FROM u GROUP BY source
UNION ALL
SELECT 'CHECKS', source, 'OPP DEDUP (CELLS)', NULL, NULL, NULL, NULL, NULL, NULL, SUM(opp), COUNT(*), NULL, 0
FROM cell GROUP BY source
UNION ALL
SELECT 'CHECKS', source, 'CELL KEYS WITH UNEQUAL POSITIVE MM_OPP, THEIR OPP', NULL, NULL, NULL, NULL, NULL, NULL,
       SUM(CASE WHEN opp_min <> opp THEN opp END), NULL, COUNT(CASE WHEN opp_min <> opp THEN 1 END), 1
FROM cell GROUP BY source
UNION ALL
SELECT 'CHECKS', source, 'ROWS WITH NEGATIVE MM_OPP', NULL, NULL, NULL, NULL, NULL, NULL, SUM(CASE WHEN mm_opp < 0 THEN mm_opp END),
       NULL, COUNT(CASE WHEN mm_opp < 0 THEN 1 END), 0
FROM u GROUP BY source
UNION ALL
SELECT 'CHECKS', source, 'ROWS WHERE N_HOLDERS <> REPEAT COUNT OF THE CELL', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL,
       SUM(n_disagree), 0
FROM cell GROUP BY source
UNION ALL
SELECT 'CHECKS', source, 'CELLS WITH ZIP_CODE NOT 5 DIGITS', NULL, NULL, NULL, NULL, NULL, NULL,
       SUM(CASE WHEN NOT COALESCE(REGEXP_LIKE(zip_code, '^[0-9]{5}$'), FALSE) THEN opp END), NULL,
       COUNT(CASE WHEN NOT COALESCE(REGEXP_LIKE(zip_code, '^[0-9]{5}$'), FALSE) THEN 1 END), 0
FROM cell GROUP BY source
UNION ALL
SELECT 'CHECKS', source, 'CELLS WITH NULL OR BLANK DIST_CH', NULL, NULL, NULL, NULL, NULL, NULL,
       SUM(CASE WHEN COALESCE(TRIM(dist_ch), '') = '' THEN opp END), NULL,
       COUNT(CASE WHEN COALESCE(TRIM(dist_ch), '') = '' THEN 1 END), 0
FROM cell GROUP BY source
UNION ALL
SELECT 'CHECKS', source, 'CELLS WITH NULL OR BLANK NEW_DIST', NULL, NULL, NULL, NULL, NULL, NULL,
       SUM(CASE WHEN COALESCE(TRIM(new_dist), '') = '' THEN opp END), NULL,
       COUNT(CASE WHEN COALESCE(TRIM(new_dist), '') = '' THEN 1 END), 0
FROM cell GROUP BY source
UNION ALL
SELECT 'CHECKS', source, 'CELLS WITH NULL OR BLANK CHANNEL', NULL, NULL, NULL, NULL, NULL, NULL,
       SUM(CASE WHEN COALESCE(TRIM(channel), '') = '' THEN opp END), NULL,
       COUNT(CASE WHEN COALESCE(TRIM(channel), '') = '' THEN 1 END), 0
FROM cell GROUP BY source
UNION ALL
SELECT 'CHECKS', source, 'TERR ZIP X CHANNEL WITH 2+ HOLDERS', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL,
       COUNT(CASE WHEN n > 1 THEN 1 END), 0
FROM th GROUP BY source
UNION ALL
SELECT 'CHECKS', source, 'TERR ROWS WITH NO HOLDER ID (NO CLEAN_ID, NO CLEAN_NAME)', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL,
       COUNT(CASE WHEN NOT is_open AND hid IS NULL THEN 1 END), 0
FROM t GROUP BY source
UNION ALL
SELECT 'CHECKS', source, 'TERR ROWS HOLDER ID FROM CLEAN_NAME', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL,
       COUNT(CASE WHEN no_cid AND hid IS NOT NULL THEN 1 END), 0
FROM t GROUP BY source
UNION ALL
SELECT 'CHECKS', source, 'TERR ROWS OPEN (VACANT)', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL,
       COUNT(CASE WHEN is_open THEN 1 END), 0
FROM t GROUP BY source
UNION ALL
SELECT 'CHECKS', t.source, 'TERR HOLDERS WITH NO KEY', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL,
       COUNT(DISTINCT CASE WHEN t.hid IS NOT NULL AND hk.clean_id IS NULL THEN t.hid END), 1
FROM t LEFT JOIN hk ON hk.source = t.source AND hk.clean_id = t.hid GROUP BY t.source
UNION ALL
SELECT 'CHECKS', source, 'KEY ROWS IN THE LATEST ADDITION', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL,
       COUNT(CASE WHEN first_seen = (SELECT MAX(first_seen) FROM hk) THEN 1 END), 0
FROM hk GROUP BY source
UNION ALL
SELECT 'CHECKS', hk.source, 'KEY HOLDER_N DUPLICATED', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL,
       COUNT(CASE WHEN hd.n > 1 THEN 1 END), 1
FROM hk JOIN hd ON hd.holder_n = hk.holder_n GROUP BY hk.source
UNION ALL
SELECT 'CHECKS', t.source, 'TERR SOURCE WITH NO OPP SOURCE OF THE SAME NAME', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL,
       COUNT(*), 1
FROM t LEFT JOIN (SELECT DISTINCT source FROM u) us ON us.source = t.source WHERE us.source IS NULL GROUP BY t.source
ORDER BY layer, source, name, zip_code, channel, dist_ch, new_dist, holder;
