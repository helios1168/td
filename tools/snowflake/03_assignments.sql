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
--Edits: INSERT statements between the two owner marker lines below (the repo's name-free edits by holder key go between the
--two key marker lines).  A statement sets only the columns it names, so a rule can set the role and a later one the states.
--Three forms:
--  by rule, from the roster before edits (TMP_M_BASE, one row per wholesaler, the result's first columns), for example
--    INSERT INTO ssdb_integration.lr_strategy.tmp_m_edit (source, wholesaler, kept, role)
--    SELECT source, wholesaler, 'Y', 'FI' FROM ssdb_integration.lr_strategy.tmp_m_base
--    WHERE source = 'CRBG' AND wholesaler ILIKE '%lastname%'
--    INSERT INTO ssdb_integration.lr_strategy.tmp_m_edit (source, wholesaler, assigned_states)
--    SELECT source, wholesaler, 'TX OK' FROM ssdb_integration.lr_strategy.tmp_m_base
--    WHERE wholesaler ILIKE '%lastname%'
--  by key, the holder key R<n> of td_holder_key (the masked id 02_model_extract.sql builds, so an edit needs no name), for example
--    INSERT INTO ssdb_integration.lr_strategy.tmp_m_edit (holder, kept, role, assigned_states) VALUES ('R12', 'N', NULL, NULL)
--    A key resolves to the roster row through td_holder_key (SET holder_tbl): R<n> of the same source and of the UUID of the
--    roster's normalized name, as 02.  Give holder instead of source and wholesaler: when both are given the key is used.
--  by row, as the EXAMPLE statement (which is ignored, leave it in).
--Statements apply in order, column by column: when a wholesaler is in two statements that both set a column, the later
--one wins, a key edit and a name edit alike, so write the broad rules first and the exceptions after.  Two different values
--for one column inside one statement are flagged.  A name typed by hand is matched in upper case with single spaces.
--The shortlist sheet comes first.  A sheet cell with several names (Ann Lee or Bo Ray, Ann Lee / Bo Ray: split on the whole
--word OR in any case and on a slash, any number of names) is each name on its own, each KEPT Y with the slot's role and states as
--a single name, and the result's STATUS is EDITED (EITHER) for a wholesaler with such a row.  Owner, 2026-11-18: "yes option 1".
--To change the roster: change the statements, Run All, then Run All 04_assigned_coverage.sql.
--Result: STATUS first.  DEFAULT, EDITED and EDITED (EITHER) rows are fine.  Rows to fix come first:
--  EDIT NOT MATCHED: NO SUCH WHOLESALER   the edit's SOURCE and name are not a holder of the territories table, or its
--                                         HOLDER key resolves to no roster row (source KEY, the key in the WHOLESALER column)
--  TWO ANSWERS IN ONE EDIT STATEMENT
--  KEPT OR ROLE NOT A LISTED VALUE
--  ASSIGNED_STATES CODE NOT A STATE (OR TWICE)   a code no territory row has as STATE, or a code listed twice
--Columns: CURRENT_CHANNELS the territory channels held, ZIPS_WH and ZIPS_FI the ZIPs held in WH and FI, ZIPS_OTHER in
--any other channel, STATES the states of those ZIPs.  04_assigned_coverage.sql reads SOURCE, WHOLESALER, KEPT, ROLE,
--ASSIGNED_STATES.
--The holder key table is only read here (02_model_extract.sql creates and extends it: Run All 02 first).
--A wholesaler is a name that is not blank and not OPEN: CLEAN_NAME, or NAME when CLEAN_NAME is blank, as
--02_model_extract.sql.  ZIP_CODE is LPAD(LEFT(TRIM(..), 5), 5, '0').

SET terr_tbl      = 'ssdb_integration.lr_strategy.territories_tableau';
SET assign_tbl    = 'ssdb_integration.lr_strategy.td_assignments';
SET sheet_tbl     = 'ssdb_integration.lr_strategy.channel_contacts';
SET holder_tbl    = 'ssdb_integration.lr_strategy.td_holder_key';

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

CREATE OR REPLACE TEMPORARY TABLE ssdb_integration.lr_strategy.tmp_m_edit (source VARCHAR, wholesaler VARCHAR, holder VARCHAR,
  kept VARCHAR, role VARCHAR, assigned_states VARCHAR, note VARCHAR, edited_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP());
--HOLDER is a key R<n>, NOTE is set only by the sheet below (EITHER: the row came from a cell with several names)

--the roster's holder keys, R<n> of td_holder_key (read only) by source and normalized name, for the edits by key
CREATE OR REPLACE TEMPORARY TABLE ssdb_integration.lr_strategy.tmp_m_hk AS
SELECT UPPER(b.source) AS source, b.nm, 'R' || k.holder_n AS holder
FROM ssdb_integration.lr_strategy.tmp_m_base b
JOIN IDENTIFIER($holder_tbl) k ON k.source = b.source AND k.holder_id = UUID_STRING('6ba7b810-9dad-11d1-80b4-00c04fd430c8', b.nm);

--the shortlist sheet (SET sheet_tbl: NAME, STATE, COMMENT, CHANNEL, one row per state x channel slot).  Owner,
--2026-11-18: "regional = wifi. 2 is the shortlist of names, we want to flag the open territories".  Each named person
--is KEPT Y, ROLE from CHANNEL (REGIONAL is WIFI), ASSIGNED_STATES the codes of their rows' STATE (full names).  A NAME
--cell may hold several names (owner, 2026-11-18, "yes option 1"): split on the whole word OR in any case and on a slash,
--each name is one person as above, and its edit row has NOTE EITHER (STATUS EDITED (EITHER)).  A person
--matches a holder of either firm on one key: a name with a comma flipped ("Lee, Ann" to "Ann Lee"), upper case, single
--spaces.  A name no holder has comes back as EDIT NOT MATCHED with source SHEET, a person on two channels as TWO ANSWERS,
--an unknown or blank channel or state as not a listed value (BLANK CHANNEL, BLANK_STATE).  Every other WH or FI holder
--is KEPT N, so their territory shows as open (only when the sheet names anyone), a person named only inside a cell with
--several names is on the sheet.  A slot with no name (an open seat) sets nothing.  The key edits and the owner edits below
--come later, so they win.
--TMP_M_SHEET: one row per name in a sheet cell (RID the sheet row, K the match key, N_NAMES the names in the cell).
--The cell's text gets a | at each split and one at the end, SPLIT_TO_TABLE cuts on it.
CREATE OR REPLACE TEMPORARY TABLE ssdb_integration.lr_strategy.tmp_m_sheet AS
SELECT rid, name, ch, st, k, n_names FROM (
  SELECT rid, name, ch, st, k, COUNT(k) OVER (PARTITION BY rid) AS n_names FROM (
    SELECT x.rid, TRIM(p.value) AS name, x.ch, x.st,
           NULLIF(UPPER(TRIM(REGEXP_REPLACE(CASE WHEN POSITION(',' IN p.value) > 0 THEN SPLIT_PART(p.value, ',', 2) || ' ' || SPLIT_PART(p.value, ',', 1)
                                 ELSE p.value END, '\\s+', ' '))), '') AS k
    FROM (SELECT ROW_NUMBER() OVER (ORDER BY name, state, channel) AS rid,
                 NULLIF(UPPER(TRIM(REGEXP_REPLACE(channel, '\\s+', ' '))), '') AS ch,
                 NULLIF(UPPER(TRIM(REGEXP_REPLACE(state, '\\s+', ' '))), '') AS st,
                 REGEXP_REPLACE(COALESCE(name, ''), '\\s+[Oo][Rr]\\s+|\\s*/\\s*', '|') || '|' AS nm_split
          FROM IDENTIFIER($sheet_tbl)) x,
    LATERAL SPLIT_TO_TABLE(x.nm_split, '|') p))
WHERE k IS NOT NULL;

INSERT INTO ssdb_integration.lr_strategy.tmp_m_edit (source, wholesaler, kept, role, note, assigned_states)
SELECT COALESCE(b.source, 'SHEET'), COALESCE(b.wholesaler, MIN(s.name)), 'Y',
       CASE WHEN s.ch = 'REGIONAL' THEN 'WIFI' ELSE COALESCE(s.ch, 'BLANK CHANNEL') END,
       CASE WHEN MAX(s.n_names) > 1 THEN 'EITHER' END,
       LISTAGG(DISTINCT COALESCE(c.code, REPLACE(s.st, ' ', '_'), 'BLANK_STATE'), ' ')
         WITHIN GROUP (ORDER BY COALESCE(c.code, REPLACE(s.st, ' ', '_'), 'BLANK_STATE'))
FROM ssdb_integration.lr_strategy.tmp_m_sheet s
LEFT JOIN (SELECT column1 AS st, column2 AS code FROM VALUES
       ('ALABAMA', 'AL'), ('ALASKA', 'AK'), ('ARIZONA', 'AZ'), ('ARKANSAS', 'AR'), ('CALIFORNIA', 'CA'),
       ('COLORADO', 'CO'), ('CONNECTICUT', 'CT'), ('DELAWARE', 'DE'), ('DISTRICT OF COLUMBIA', 'DC'),
       ('FLORIDA', 'FL'), ('GEORGIA', 'GA'), ('HAWAII', 'HI'), ('IDAHO', 'ID'), ('ILLINOIS', 'IL'),
       ('INDIANA', 'IN'), ('IOWA', 'IA'), ('KANSAS', 'KS'), ('KENTUCKY', 'KY'), ('LOUISIANA', 'LA'), ('MAINE', 'ME'),
       ('MARYLAND', 'MD'), ('MASSACHUSETTS', 'MA'), ('MICHIGAN', 'MI'), ('MINNESOTA', 'MN'), ('MISSISSIPPI', 'MS'),
       ('MISSOURI', 'MO'), ('MONTANA', 'MT'), ('NEBRASKA', 'NE'), ('NEVADA', 'NV'), ('NEW HAMPSHIRE', 'NH'),
       ('NEW JERSEY', 'NJ'), ('NEW MEXICO', 'NM'), ('NEW YORK', 'NY'), ('NORTH CAROLINA', 'NC'),
       ('NORTH DAKOTA', 'ND'), ('OHIO', 'OH'), ('OKLAHOMA', 'OK'), ('OREGON', 'OR'), ('PENNSYLVANIA', 'PA'),
       ('RHODE ISLAND', 'RI'), ('SOUTH CAROLINA', 'SC'), ('SOUTH DAKOTA', 'SD'), ('TENNESSEE', 'TN'),
       ('TEXAS', 'TX'), ('UTAH', 'UT'), ('VERMONT', 'VT'), ('VIRGINIA', 'VA'), ('WASHINGTON', 'WA'),
       ('WEST VIRGINIA', 'WV'), ('WISCONSIN', 'WI'), ('WYOMING', 'WY')) c ON c.st = s.st
LEFT JOIN (SELECT source, wholesaler, UPPER(TRIM(REGEXP_REPLACE(CASE WHEN POSITION(',' IN wholesaler) > 0 THEN SPLIT_PART(wholesaler, ',', 2) || ' ' || SPLIT_PART(wholesaler, ',', 1)
                                   ELSE wholesaler END, '\\s+', ' '))) AS k
           FROM ssdb_integration.lr_strategy.tmp_m_base) b ON b.k = s.k
GROUP BY s.k, b.source, b.wholesaler, s.ch;
INSERT INTO ssdb_integration.lr_strategy.tmp_m_edit (source, wholesaler, kept)
SELECT source, wholesaler, 'N' FROM ssdb_integration.lr_strategy.tmp_m_base
WHERE zips_wh + zips_fi > 0
  AND UPPER(TRIM(REGEXP_REPLACE(CASE WHEN POSITION(',' IN wholesaler) > 0 THEN SPLIT_PART(wholesaler, ',', 2) || ' ' || SPLIT_PART(wholesaler, ',', 1)
                                   ELSE wholesaler END, '\\s+', ' '))) NOT IN (SELECT k FROM ssdb_integration.lr_strategy.tmp_m_sheet)
  AND EXISTS (SELECT 1 FROM ssdb_integration.lr_strategy.tmp_m_sheet);

--key edits: begin
--(edits by holder key R<n>, no names: INSERT INTO ssdb_integration.lr_strategy.tmp_m_edit (holder, kept, role, assigned_states) VALUES ...)
--key edits: end

--owner edits: begin
INSERT INTO ssdb_integration.lr_strategy.tmp_m_edit (source, wholesaler, kept, role) VALUES
  ('EXAMPLE', 'Last, First', 'N', '');
--owner edits: end

CREATE OR REPLACE TABLE IDENTIFIER($assign_tbl) AS
WITH
--each edit row, one row per column it sets (a NULL column is not set)
e0 AS (SELECT CASE WHEN NULLIF(TRIM(x.holder), '') IS NULL THEN UPPER(TRIM(x.source)) ELSE k.source END AS source,
              CASE WHEN NULLIF(TRIM(x.holder), '') IS NULL THEN UPPER(TRIM(REGEXP_REPLACE(TRIM(x.wholesaler), '\\s+', ' '))) ELSE k.nm END AS nm,
              UPPER(TRIM(x.kept)) AS kept, UPPER(TRIM(x.role)) AS role,
              UPPER(TRIM(REGEXP_REPLACE(REPLACE(x.assigned_states, ',', ' '), '\\s+', ' '))) AS assigned_states, x.edited_at,
              CASE WHEN x.note = 'EITHER' THEN 1 ELSE 0 END AS either
       FROM ssdb_integration.lr_strategy.tmp_m_edit x
       LEFT JOIN ssdb_integration.lr_strategy.tmp_m_hk k ON k.holder = UPPER(TRIM(x.holder))
       WHERE COALESCE(x.source, '') <> 'EXAMPLE'),
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
ee AS (SELECT source, nm, MAX(either) AS either FROM e0 GROUP BY source, nm),
st AS (SELECT DISTINCT UPPER(TRIM(state)) AS st FROM IDENTIFIER($terr_tbl) WHERE TRIM(state) <> ''),
a AS (SELECT b.source, b.nm, b.wholesaler, b.current_channels, b.zips_wh, b.zips_fi, b.zips_other, b.states,
             e.nm IS NOT NULL AS edited, COALESCE(e.n, 0) AS n, COALESCE(ee.either, 0) AS either,
             COALESCE(e.kept, CASE WHEN b.zips_wh + b.zips_fi > 0 THEN 'Y' ELSE '' END) AS kept,
             COALESCE(e.role, CASE WHEN b.zips_wh + b.zips_fi > 0 THEN 'WIFI' ELSE '' END) AS role,
             COALESCE(e.assigned_states, '') AS assigned_states
      FROM ssdb_integration.lr_strategy.tmp_m_base b LEFT JOIN e ON e.source = UPPER(b.source) AND e.nm = b.nm
             LEFT JOIN ee ON ee.source = UPPER(b.source) AND ee.nm = b.nm),
ac AS (SELECT a.source, a.nm, COUNT(DISTINCT st.st) AS n_known,
              CASE WHEN a.assigned_states = '' THEN 0 ELSE LENGTH(a.assigned_states) - LENGTH(REPLACE(a.assigned_states, ' ', '')) + 1 END AS n_codes
       FROM a LEFT JOIN st ON (' ' || a.assigned_states || ' ') LIKE '% ' || st.st || ' %'
       GROUP BY a.source, a.nm, a.assigned_states)
SELECT CASE WHEN NOT a.edited THEN 'DEFAULT' WHEN a.n > 1 THEN 'TWO ANSWERS IN ONE EDIT STATEMENT'
            WHEN a.kept NOT IN ('Y', 'N', '') OR a.role NOT IN ('NATIONAL', 'WH', 'FI', 'WIFI', '') THEN 'KEPT OR ROLE NOT A LISTED VALUE'
            WHEN ac.n_known <> ac.n_codes THEN 'ASSIGNED_STATES CODE NOT A STATE (OR TWICE)'
            WHEN a.either = 1 THEN 'EDITED (EITHER)'
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
WHERE COALESCE(e.source, '') <> 'EXAMPLE' AND NULLIF(TRIM(e.holder), '') IS NULL AND b.source IS NULL
UNION ALL
SELECT DISTINCT 'EDIT NOT MATCHED: NO SUCH WHOLESALER', 'KEY', TRIM(e.holder), NULL, NULL, NULL, NULL, NULL, e.kept, e.role, e.assigned_states
FROM ssdb_integration.lr_strategy.tmp_m_edit e
LEFT JOIN ssdb_integration.lr_strategy.tmp_m_hk k ON k.holder = UPPER(TRIM(e.holder))
WHERE NULLIF(TRIM(e.holder), '') IS NOT NULL AND k.holder IS NULL)
ORDER BY CASE WHEN status LIKE 'EDIT NOT MATCHED%' THEN 0 WHEN status IN ('DEFAULT', 'EDITED', 'EDITED (EITHER)') THEN 2 ELSE 1 END, source,
         CASE WHEN zips_wh + zips_fi > 0 THEN 0 ELSE 1 END, wholesaler;
