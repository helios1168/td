use role rl_ssdb_Integration_Lr_Strategy_Rw;
use database ssdb_Integration;
use schema lr_strategy;

--The roster to fill in for the preliminary assignments: one row per SOURCE x wholesaler who holds a territory today,
--with what they hold, and two blank columns for the owner.  Read-only, one Run All file, one result.
--THE RESULT HOLDS WHOLESALER NAMES: it stays with the owner, it is never sent to an agent or put in the repo.
--To use it: download the result, fill in
--  KEPT  Y or N (blank = not decided)
--  ROLE  NATIONAL, WH, FI or WIFI for a kept wholesaler of the main map (blank otherwise)
--and load the file back as the assignments table.  Only SOURCE, WHOLESALER, KEPT and ROLE are read from it, and
--WHOLESALER is matched to the territories table in upper case with single spaces, so do not retype the names.
--One person in both sources has a row in each.  Wholesalers of WH and FI (firm 2: BD and BK) come first.
--Columns: CURRENT_CHANNELS the territory channels held, ZIPS_WH and ZIPS_FI the ZIPs held in WH and FI (firm 2: BD
--and BK), ZIPS_OTHER in any other channel, STATES the states of those ZIPs.
--A wholesaler is a name that is not blank and not OPEN: CLEAN_NAME, or NAME when CLEAN_NAME is blank, as
--02_model_extract.sql.  ZIP_CODE is LPAD(LEFT(TRIM(..), 5), 5, '0').

SET terr_tbl = 'ssdb_integration.lr_strategy.territories_tableau';

WITH
t AS (SELECT source, LPAD(LEFT(TRIM(zip_code), 5), 5, '0') AS zip_code, COALESCE(UPPER(TRIM(state)), '') AS st,
             COALESCE(UPPER(TRIM(channel)), '') AS ch, TRIM(COALESCE(NULLIF(TRIM(clean_name), ''), name)) AS spelling,
             NULLIF(NULLIF(UPPER(TRIM(REGEXP_REPLACE(TRIM(COALESCE(NULLIF(TRIM(clean_name), ''), name)), '\\s+', ' '))), ''), 'OPEN') AS nm
      FROM IDENTIFIER($terr_tbl)),
h AS (SELECT source, nm, MIN(spelling) AS wholesaler,
             COUNT(DISTINCT CASE WHEN ch IN ('WH', 'BD') THEN zip_code END) AS zips_wh,
             COUNT(DISTINCT CASE WHEN ch IN ('FI', 'BK') THEN zip_code END) AS zips_fi,
             COUNT(DISTINCT CASE WHEN ch NOT IN ('WH', 'BD', 'FI', 'BK') THEN zip_code END) AS zips_other
      FROM t WHERE nm IS NOT NULL AND source IS NOT NULL GROUP BY source, nm),
hc AS (SELECT source, nm, LISTAGG(ch, ' ') WITHIN GROUP (ORDER BY ch) AS current_channels
       FROM (SELECT DISTINCT source, nm, ch FROM t WHERE nm IS NOT NULL) GROUP BY source, nm),
hs AS (SELECT source, nm, LISTAGG(st, ' ') WITHIN GROUP (ORDER BY st) AS states
       FROM (SELECT DISTINCT source, nm, st FROM t WHERE nm IS NOT NULL) GROUP BY source, nm)
SELECT h.source, h.wholesaler, hc.current_channels, h.zips_wh, h.zips_fi, h.zips_other, hs.states,
       CAST('' AS VARCHAR) AS kept, CAST('' AS VARCHAR) AS role
FROM h JOIN hc ON hc.source = h.source AND hc.nm = h.nm JOIN hs ON hs.source = h.source AND hs.nm = h.nm
ORDER BY h.source, CASE WHEN h.zips_wh + h.zips_fi > 0 THEN 0 ELSE 1 END, h.wholesaler;
