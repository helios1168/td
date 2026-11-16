use role rl_ssdb_Integration_Lr_Strategy_Rw;
use database ssdb_Integration;
use schema lr_strategy;

--The assignments table (the roster): one row per SOURCE x wholesaler who holds a territory today, with KEPT and ROLE.
--One Run All file.  It rebuilds the table from the territories table, a default and the owner's edits below, and
--returns the roster.  THE RESULT AND THE EDITS HOLD WHOLESALER NAMES: keep your edited copy in your own worksheet,
--never send it to an agent or put it in the repo.
--Default: a wholesaler who holds a ZIP in WH or FI is KEPT Y, ROLE WIFI.  Everyone else is blank (not in the main map).
--Edits: one row per wholesaler whose answer is not the default, between the two marker lines below:
--  ('<SOURCE>', '<WHOLESALER as the result shows it>', '<KEPT: Y, N or blank>', '<ROLE: NATIONAL, WH, FI, WIFI or blank>')
--with a comma after every row but the last.  An edit replaces both KEPT and ROLE.  The name is matched in upper case
--with single spaces, so copy it from the result.  Leave the EXAMPLE row in, it is ignored.
--To change the roster: change the rows, Run All, then Run All 04_assigned_coverage.sql.
--Result: STATUS first.  DEFAULT and EDITED rows are fine.  Rows to fix come first:
--  EDIT NOT MATCHED: NO SUCH WHOLESALER   the edit's SOURCE and name are not a holder of the territories table
--  ON 2+ EDIT ROWS                        one wholesaler has two edits
--  KEPT OR ROLE NOT A LISTED VALUE
--Columns: CURRENT_CHANNELS the territory channels held, ZIPS_WH and ZIPS_FI the ZIPs held in WH and FI, ZIPS_OTHER in
--any other channel, STATES the states of those ZIPs.  04_assigned_coverage.sql reads SOURCE, WHOLESALER, KEPT, ROLE.
--A wholesaler is a name that is not blank and not OPEN: CLEAN_NAME, or NAME when CLEAN_NAME is blank, as
--02_model_extract.sql.  ZIP_CODE is LPAD(LEFT(TRIM(..), 5), 5, '0').

SET terr_tbl   = 'ssdb_integration.lr_strategy.territories_tableau';
SET assign_tbl = 'ssdb_integration.lr_strategy.td_assignments';

CREATE OR REPLACE TEMPORARY TABLE ssdb_integration.lr_strategy.tmp_m_edit (source VARCHAR, wholesaler VARCHAR, kept VARCHAR, role VARCHAR);

INSERT INTO ssdb_integration.lr_strategy.tmp_m_edit (source, wholesaler, kept, role) VALUES
--owner edits: begin
  ('EXAMPLE', 'Last, First', 'N', '')
--owner edits: end
;

CREATE OR REPLACE TABLE IDENTIFIER($assign_tbl) AS
WITH
t AS (SELECT source, LPAD(LEFT(TRIM(zip_code), 5), 5, '0') AS zip_code, COALESCE(UPPER(TRIM(state)), '') AS st,
             COALESCE(UPPER(TRIM(channel)), '') AS ch, TRIM(COALESCE(NULLIF(TRIM(clean_name), ''), name)) AS spelling,
             NULLIF(NULLIF(UPPER(TRIM(REGEXP_REPLACE(TRIM(COALESCE(NULLIF(TRIM(clean_name), ''), name)), '\\s+', ' '))), ''), 'OPEN') AS nm
      FROM IDENTIFIER($terr_tbl)),
h AS (SELECT source, nm, MIN(spelling) AS wholesaler,
             COUNT(DISTINCT CASE WHEN ch = 'WH' THEN zip_code END) AS zips_wh,
             COUNT(DISTINCT CASE WHEN ch = 'FI' THEN zip_code END) AS zips_fi,
             COUNT(DISTINCT CASE WHEN ch NOT IN ('WH', 'FI') THEN zip_code END) AS zips_other
      FROM t WHERE nm IS NOT NULL AND source IS NOT NULL GROUP BY source, nm),
hc AS (SELECT source, nm, LISTAGG(ch, ' ') WITHIN GROUP (ORDER BY ch) AS current_channels
       FROM (SELECT DISTINCT source, nm, ch FROM t WHERE nm IS NOT NULL) GROUP BY source, nm),
hs AS (SELECT source, nm, LISTAGG(st, ' ') WITHIN GROUP (ORDER BY st) AS states
       FROM (SELECT DISTINCT source, nm, st FROM t WHERE nm IS NOT NULL) GROUP BY source, nm),
e AS (SELECT UPPER(TRIM(source)) AS source, UPPER(TRIM(REGEXP_REPLACE(TRIM(wholesaler), '\\s+', ' '))) AS nm,
             MAX(COALESCE(UPPER(TRIM(kept)), '')) AS kept, MAX(COALESCE(UPPER(TRIM(role)), '')) AS role, COUNT(*) AS n
      FROM ssdb_integration.lr_strategy.tmp_m_edit WHERE source <> 'EXAMPLE' GROUP BY UPPER(TRIM(source)),
           UPPER(TRIM(REGEXP_REPLACE(TRIM(wholesaler), '\\s+', ' '))))
SELECT CASE WHEN e.nm IS NULL THEN 'DEFAULT' WHEN e.n > 1 THEN 'ON 2+ EDIT ROWS'
            WHEN e.kept NOT IN ('Y', 'N', '') OR e.role NOT IN ('NATIONAL', 'WH', 'FI', 'WIFI', '') THEN 'KEPT OR ROLE NOT A LISTED VALUE'
            ELSE 'EDITED' END AS status,
       h.source, h.wholesaler, hc.current_channels, h.zips_wh, h.zips_fi, h.zips_other, hs.states,
       CASE WHEN e.nm IS NOT NULL THEN e.kept WHEN h.zips_wh + h.zips_fi > 0 THEN 'Y' ELSE '' END AS kept,
       CASE WHEN e.nm IS NOT NULL THEN e.role WHEN h.zips_wh + h.zips_fi > 0 THEN 'WIFI' ELSE '' END AS role
FROM h JOIN hc ON hc.source = h.source AND hc.nm = h.nm JOIN hs ON hs.source = h.source AND hs.nm = h.nm
LEFT JOIN e ON e.source = UPPER(h.source) AND e.nm = h.nm;

SELECT status, source, wholesaler, current_channels, zips_wh, zips_fi, zips_other, states, kept, role FROM (
SELECT status, source, wholesaler, current_channels, zips_wh, zips_fi, zips_other, states, kept, role
FROM IDENTIFIER($assign_tbl)
UNION ALL
SELECT 'EDIT NOT MATCHED: NO SUCH WHOLESALER', e.source, e.wholesaler, NULL, NULL, NULL, NULL, NULL, e.kept, e.role
FROM ssdb_integration.lr_strategy.tmp_m_edit e
LEFT JOIN IDENTIFIER($assign_tbl) a
       ON UPPER(a.source) = UPPER(TRIM(e.source))
      AND UPPER(TRIM(REGEXP_REPLACE(TRIM(a.wholesaler), '\\s+', ' '))) = UPPER(TRIM(REGEXP_REPLACE(TRIM(e.wholesaler), '\\s+', ' ')))
WHERE e.source <> 'EXAMPLE' AND a.source IS NULL)
ORDER BY CASE WHEN status LIKE 'EDIT NOT MATCHED%' THEN 0 WHEN status IN ('DEFAULT', 'EDITED') THEN 2 ELSE 1 END, source,
         CASE WHEN zips_wh + zips_fi > 0 THEN 0 ELSE 1 END, wholesaler;
