use role rl_ssdb_Integration_Lr_Strategy_Rw;
use database ssdb_Integration;
use schema lr_strategy;

--The assignments table (the roster): one row per SOURCE x wholesaler who holds a territory today, with KEPT and ROLE.
--One Run All file.  It rebuilds the table from the territories table, a default and the owner's edits below, and
--returns the roster.  THE RESULT AND THE EDITS HOLD WHOLESALER NAMES: keep your edited copy in your own worksheet,
--never send it to an agent or put it in the repo.
--Default: a wholesaler who holds a ZIP in WH or FI is KEPT Y, ROLE WIFI.  Everyone else is blank (not in the main map).
--Edits: INSERT statements between the two marker lines below, each giving SOURCE, WHOLESALER, KEPT (Y, N or blank) and
--ROLE (NATIONAL, WH, FI, WIFI or blank) for the wholesalers whose answer is not the default.  Two forms:
--  by rule, from the roster before edits (one row per wholesaler, the result's columns), for example
--    INSERT INTO ssdb_integration.lr_strategy.tmp_m_edit (source, wholesaler, kept, role)
--    SELECT source, wholesaler, 'Y', 'FI' FROM ssdb_integration.lr_strategy.tmp_m_base
--    WHERE source = 'CRBG' AND wholesaler ILIKE '%lastname%'
--  by row, as the EXAMPLE statement (which is ignored, leave it in).
--An edit replaces both KEPT and ROLE.  Statements apply in order: when a wholesaler is in two of them the later one
--wins, so write the broad rules first and the exceptions after.  Two different answers inside one statement are flagged.
--A name typed by hand is matched in upper case with single spaces.
--To change the roster: change the statements, Run All, then Run All 04_assigned_coverage.sql.
--Result: STATUS first.  DEFAULT and EDITED rows are fine.  Rows to fix come first:
--  EDIT NOT MATCHED: NO SUCH WHOLESALER   the edit's SOURCE and name are not a holder of the territories table
--  TWO ANSWERS IN ONE EDIT STATEMENT
--  KEPT OR ROLE NOT A LISTED VALUE
--Columns: CURRENT_CHANNELS the territory channels held, ZIPS_WH and ZIPS_FI the ZIPs held in WH and FI, ZIPS_OTHER in
--any other channel, STATES the states of those ZIPs.  04_assigned_coverage.sql reads SOURCE, WHOLESALER, KEPT, ROLE.
--A wholesaler is a name that is not blank and not OPEN: CLEAN_NAME, or NAME when CLEAN_NAME is blank, as
--02_model_extract.sql.  ZIP_CODE is LPAD(LEFT(TRIM(..), 5), 5, '0').

SET terr_tbl   = 'ssdb_integration.lr_strategy.territories_tableau';
SET assign_tbl = 'ssdb_integration.lr_strategy.td_assignments';

--the roster before edits
CREATE OR REPLACE TEMPORARY TABLE ssdb_integration.lr_strategy.tmp_m_base AS
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
       FROM (SELECT DISTINCT source, nm, st FROM t WHERE nm IS NOT NULL) GROUP BY source, nm)
SELECT h.source, h.wholesaler, h.nm, hc.current_channels, h.zips_wh, h.zips_fi, h.zips_other, hs.states
FROM h JOIN hc ON hc.source = h.source AND hc.nm = h.nm JOIN hs ON hs.source = h.source AND hs.nm = h.nm;

CREATE OR REPLACE TEMPORARY TABLE ssdb_integration.lr_strategy.tmp_m_edit (source VARCHAR, wholesaler VARCHAR, kept VARCHAR,
  role VARCHAR, edited_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP());

--owner edits: begin
INSERT INTO ssdb_integration.lr_strategy.tmp_m_edit (source, wholesaler, kept, role) VALUES
  ('EXAMPLE', 'Last, First', 'N', '');
--owner edits: end

CREATE OR REPLACE TABLE IDENTIFIER($assign_tbl) AS
WITH
e0 AS (SELECT UPPER(TRIM(source)) AS source, UPPER(TRIM(REGEXP_REPLACE(TRIM(wholesaler), '\\s+', ' '))) AS nm,
              COALESCE(UPPER(TRIM(kept)), '') AS kept, COALESCE(UPPER(TRIM(role)), '') AS role, edited_at
       FROM ssdb_integration.lr_strategy.tmp_m_edit WHERE source <> 'EXAMPLE'),
el AS (SELECT source, nm, MAX(edited_at) AS edited_at FROM e0 GROUP BY source, nm),
e AS (SELECT e0.source, e0.nm, MAX(e0.kept) AS kept, MAX(e0.role) AS role, COUNT(DISTINCT e0.kept || '|' || e0.role) AS n
      FROM e0 JOIN el ON el.source = e0.source AND el.nm = e0.nm AND el.edited_at = e0.edited_at GROUP BY e0.source, e0.nm)
SELECT CASE WHEN e.nm IS NULL THEN 'DEFAULT' WHEN e.n > 1 THEN 'TWO ANSWERS IN ONE EDIT STATEMENT'
            WHEN e.kept NOT IN ('Y', 'N', '') OR e.role NOT IN ('NATIONAL', 'WH', 'FI', 'WIFI', '') THEN 'KEPT OR ROLE NOT A LISTED VALUE'
            ELSE 'EDITED' END AS status,
       b.source, b.wholesaler, b.current_channels, b.zips_wh, b.zips_fi, b.zips_other, b.states,
       CASE WHEN e.nm IS NOT NULL THEN e.kept WHEN b.zips_wh + b.zips_fi > 0 THEN 'Y' ELSE '' END AS kept,
       CASE WHEN e.nm IS NOT NULL THEN e.role WHEN b.zips_wh + b.zips_fi > 0 THEN 'WIFI' ELSE '' END AS role
FROM ssdb_integration.lr_strategy.tmp_m_base b LEFT JOIN e ON e.source = UPPER(b.source) AND e.nm = b.nm;

SELECT status, source, wholesaler, current_channels, zips_wh, zips_fi, zips_other, states, kept, role FROM (
SELECT status, source, wholesaler, current_channels, zips_wh, zips_fi, zips_other, states, kept, role
FROM IDENTIFIER($assign_tbl)
UNION ALL
SELECT DISTINCT 'EDIT NOT MATCHED: NO SUCH WHOLESALER', e.source, e.wholesaler, NULL, NULL, NULL, NULL, NULL, e.kept, e.role
FROM ssdb_integration.lr_strategy.tmp_m_edit e
LEFT JOIN ssdb_integration.lr_strategy.tmp_m_base b
       ON UPPER(b.source) = UPPER(TRIM(e.source)) AND b.nm = UPPER(TRIM(REGEXP_REPLACE(TRIM(e.wholesaler), '\\s+', ' ')))
WHERE e.source <> 'EXAMPLE' AND b.source IS NULL)
ORDER BY CASE WHEN status LIKE 'EDIT NOT MATCHED%' THEN 0 WHEN status IN ('DEFAULT', 'EDITED') THEN 2 ELSE 1 END, source,
         CASE WHEN zips_wh + zips_fi > 0 THEN 0 ELSE 1 END, wholesaler;
