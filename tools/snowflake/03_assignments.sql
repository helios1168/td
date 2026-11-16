use role rl_ssdb_Integration_Lr_Strategy_Rw;
use database ssdb_Integration;
use schema lr_strategy;

--The assignments table (the roster): one row per SOURCE x wholesaler who holds a territory today, with KEPT, ROLE and
--ASSIGNED_STATES.  These are labels: they change no territory.  One Run All file.  It rebuilds the table from the
--territories table, a default and the owner's edits below, and returns the roster.  THE RESULT AND THE EDITS HOLD
--WHOLESALER NAMES: keep your edited copy in your own worksheet, never send it to an agent or put it in the repo.
--Default: a wholesaler who holds a ZIP in WH or FI is KEPT Y, ROLE WIFI.  Everyone else is blank (not in the main map).
--ASSIGNED_STATES blank for everyone.
--The columns you set:
--  KEPT             Y, N or blank (not decided)
--  ROLE             NATIONAL, WH, FI, WIFI or blank (kept outside the main map)
--  ASSIGNED_STATES  the preliminary states, two-letter codes with a space or comma between them, for example 'CA NV AZ'.
--                   Only reported against: how much of today's territory lies in them.
--Edits: INSERT statements between the two marker lines below.  A statement sets only the columns it names, so a rule
--can set the role and a later one the states.  Two forms:
--  by rule, from the roster before edits (TMP_M_BASE, one row per wholesaler, the result's first columns), for example
--    INSERT INTO ssdb_integration.lr_strategy.tmp_m_edit (source, wholesaler, kept, role)
--    SELECT source, wholesaler, 'Y', 'FI' FROM ssdb_integration.lr_strategy.tmp_m_base
--    WHERE source = 'CRBG' AND wholesaler ILIKE '%lastname%'
--    INSERT INTO ssdb_integration.lr_strategy.tmp_m_edit (source, wholesaler, assigned_states)
--    SELECT source, wholesaler, 'TX OK' FROM ssdb_integration.lr_strategy.tmp_m_base
--    WHERE wholesaler ILIKE '%lastname%'
--  by row, as the EXAMPLE statement (which is ignored, leave it in).
--Statements apply in order, column by column: when a wholesaler is in two statements that both set a column, the later
--one wins, so write the broad rules first and the exceptions after.  Two different values for one column inside one
--statement are flagged.  A name typed by hand is matched in upper case with single spaces.
--To change the roster: change the statements, Run All, then Run All 04_assigned_coverage.sql.
--Result: STATUS first.  DEFAULT and EDITED rows are fine.  Rows to fix come first:
--  EDIT NOT MATCHED: NO SUCH WHOLESALER   the edit's SOURCE and name are not a holder of the territories table
--  TWO ANSWERS IN ONE EDIT STATEMENT
--  KEPT OR ROLE NOT A LISTED VALUE
--  ASSIGNED_STATES CODE NOT A STATE (OR TWICE)   a code no territory row has as STATE, or a code listed twice
--Columns: CURRENT_CHANNELS the territory channels held, ZIPS_WH and ZIPS_FI the ZIPs held in WH and FI, ZIPS_OTHER in
--any other channel, STATES the states of those ZIPs.  04_assigned_coverage.sql reads SOURCE, WHOLESALER, KEPT, ROLE,
--ASSIGNED_STATES.
--A wholesaler is a name that is not blank and not OPEN: CLEAN_NAME, or NAME when CLEAN_NAME is blank, as
--02_model_extract.sql.  ZIP_CODE is LPAD(LEFT(TRIM(..), 5), 5, '0').

SET terr_tbl      = 'ssdb_integration.lr_strategy.territories_tableau';
SET assign_tbl    = 'ssdb_integration.lr_strategy.td_assignments';

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
  role VARCHAR, assigned_states VARCHAR, edited_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP());

--owner edits: begin
INSERT INTO ssdb_integration.lr_strategy.tmp_m_edit (source, wholesaler, kept, role) VALUES
  ('EXAMPLE', 'Last, First', 'N', '');
--owner edits: end

CREATE OR REPLACE TABLE IDENTIFIER($assign_tbl) AS
WITH
--each edit row, one row per column it sets (a NULL column is not set)
e0 AS (SELECT UPPER(TRIM(source)) AS source, UPPER(TRIM(REGEXP_REPLACE(TRIM(wholesaler), '\\s+', ' '))) AS nm,
              UPPER(TRIM(kept)) AS kept, UPPER(TRIM(role)) AS role,
              UPPER(TRIM(REGEXP_REPLACE(REPLACE(assigned_states, ',', ' '), '\\s+', ' '))) AS assigned_states, edited_at
       FROM ssdb_integration.lr_strategy.tmp_m_edit WHERE source <> 'EXAMPLE'),
ea AS (SELECT source, nm, 'KEPT' AS fld, kept AS val, edited_at FROM e0 WHERE kept IS NOT NULL
       UNION ALL SELECT source, nm, 'ROLE', role, edited_at FROM e0 WHERE role IS NOT NULL
       UNION ALL SELECT source, nm, 'ASSIGNED_STATES', assigned_states, edited_at FROM e0 WHERE assigned_states IS NOT NULL),
el AS (SELECT source, nm, fld, MAX(edited_at) AS edited_at FROM ea GROUP BY source, nm, fld),
ev AS (SELECT ea.source, ea.nm, ea.fld, MAX(ea.val) AS val, COUNT(DISTINCT ea.val) AS n
       FROM ea JOIN el ON el.source = ea.source AND el.nm = ea.nm AND el.fld = ea.fld AND el.edited_at = ea.edited_at
       GROUP BY ea.source, ea.nm, ea.fld),
e AS (SELECT source, nm, MAX(CASE WHEN fld = 'KEPT' THEN val END) AS kept, MAX(CASE WHEN fld = 'ROLE' THEN val END) AS role,
             MAX(CASE WHEN fld = 'ASSIGNED_STATES' THEN val END) AS assigned_states, MAX(n) AS n
      FROM ev GROUP BY source, nm),
st AS (SELECT DISTINCT UPPER(TRIM(state)) AS st FROM IDENTIFIER($terr_tbl) WHERE TRIM(state) <> ''),
a AS (SELECT b.source, b.nm, b.wholesaler, b.current_channels, b.zips_wh, b.zips_fi, b.zips_other, b.states,
             e.nm IS NOT NULL AS edited, COALESCE(e.n, 0) AS n,
             COALESCE(e.kept, CASE WHEN b.zips_wh + b.zips_fi > 0 THEN 'Y' ELSE '' END) AS kept,
             COALESCE(e.role, CASE WHEN b.zips_wh + b.zips_fi > 0 THEN 'WIFI' ELSE '' END) AS role,
             COALESCE(e.assigned_states, '') AS assigned_states
      FROM ssdb_integration.lr_strategy.tmp_m_base b LEFT JOIN e ON e.source = UPPER(b.source) AND e.nm = b.nm),
ac AS (SELECT a.source, a.nm, COUNT(DISTINCT st.st) AS n_known,
              CASE WHEN a.assigned_states = '' THEN 0 ELSE LENGTH(a.assigned_states) - LENGTH(REPLACE(a.assigned_states, ' ', '')) + 1 END AS n_codes
       FROM a LEFT JOIN st ON (' ' || a.assigned_states || ' ') LIKE '% ' || st.st || ' %'
       GROUP BY a.source, a.nm, a.assigned_states)
SELECT CASE WHEN NOT a.edited THEN 'DEFAULT' WHEN a.n > 1 THEN 'TWO ANSWERS IN ONE EDIT STATEMENT'
            WHEN a.kept NOT IN ('Y', 'N', '') OR a.role NOT IN ('NATIONAL', 'WH', 'FI', 'WIFI', '') THEN 'KEPT OR ROLE NOT A LISTED VALUE'
            WHEN ac.n_known <> ac.n_codes THEN 'ASSIGNED_STATES CODE NOT A STATE (OR TWICE)'
            ELSE 'EDITED' END AS status,
       a.source, a.wholesaler, a.current_channels, a.zips_wh, a.zips_fi, a.zips_other, a.states, a.kept, a.role,
       a.assigned_states
FROM a JOIN ac ON ac.source = a.source AND ac.nm = a.nm;

SELECT status, source, wholesaler, current_channels, zips_wh, zips_fi, zips_other, states, kept, role, assigned_states FROM (
SELECT status, source, wholesaler, current_channels, zips_wh, zips_fi, zips_other, states, kept, role, assigned_states
FROM IDENTIFIER($assign_tbl)
UNION ALL
SELECT DISTINCT 'EDIT NOT MATCHED: NO SUCH WHOLESALER', e.source, e.wholesaler, NULL, NULL, NULL, NULL, NULL, e.kept, e.role, e.assigned_states
FROM ssdb_integration.lr_strategy.tmp_m_edit e
LEFT JOIN ssdb_integration.lr_strategy.tmp_m_base b
       ON UPPER(b.source) = UPPER(TRIM(e.source)) AND b.nm = UPPER(TRIM(REGEXP_REPLACE(TRIM(e.wholesaler), '\\s+', ' ')))
WHERE e.source <> 'EXAMPLE' AND b.source IS NULL)
ORDER BY CASE WHEN status LIKE 'EDIT NOT MATCHED%' THEN 0 WHEN status IN ('DEFAULT', 'EDITED') THEN 2 ELSE 1 END, source,
         CASE WHEN zips_wh + zips_fi > 0 THEN 0 ELSE 1 END, wholesaler;
