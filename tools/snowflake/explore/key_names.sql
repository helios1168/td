use role rl_ssdb_Integration_Lr_Strategy_Rw;
use database ssdb_Integration;
use schema lr_strategy;
--Saves its result as the temporary table key_names (replaced on every run, ROW_N its order) for filtering in a
--scratch file with F6, e.g. SELECT * FROM key_names WHERE ...  It lives as long as the session: with
--sql_session.ps1 running, F5 here then F6 there share it.  The last statement shows it.
--THE RESULT HOLDS WHOLESALER NAMES AND THE SHEET'S COMMENTS: the owner's key lookup, for their screen only, never sent
--to an agent (owner, 2026-11-18: "How do I pull the data needed to investigate this with the wholesaler keys").  It
--writes only its temporary table, one result: one row per holder key of td_holder_key (as sheet_slots.sql: <SOURCE>:R<n> of the source and the
--UUID of the normalized name), the holders on the shortlist sheet first.  KEY, NAME (CLEAN_NAME, or NAME when it is
--blank), CURRENT_CHANNELS, ZIPS_WH, ZIPS_FI and STATES from the territories table, SHEET_SLOTS the sheet's slots naming
--this holder (state channel, "either" when the cell names several), SHEET_CHANNELS, TWO_CHANNELS 1 when the sheet has
--the holder on more than one channel (03 flags TWO ANSWERS), SHEET_COMMENTS the comments of those slots.  The sheet is
--read as 03 reads it (an "A or B" cell is each name, N/A, OPEN and TBD are open seats).
SET sheet_tbl  = 'ssdb_integration.lr_strategy.channel_contacts';
SET terr_tbl   = 'ssdb_integration.lr_strategy.territories_tableau';
SET holder_tbl = 'ssdb_integration.lr_strategy.td_holder_key';
CREATE OR REPLACE TEMPORARY TABLE ssdb_integration.lr_strategy.key_names AS
WITH
sp AS (SELECT x.rid, x.st, x.ch, x.cell, x.cm, p.index AS ix,
              NULLIF(NULLIF(NULLIF(NULLIF(UPPER(TRIM(REGEXP_REPLACE(CASE WHEN POSITION(',' IN p.value) > 0
                                                    THEN SPLIT_PART(p.value, ',', 2) || ' ' || SPLIT_PART(p.value, ',', 1)
                                                    ELSE p.value END, '\\s+', ' '))), ''), 'N/A'), 'OPEN'), 'TBD') AS k
       FROM (SELECT ROW_NUMBER() OVER (ORDER BY name, state, channel, comment) AS rid,
                    NULLIF(UPPER(TRIM(REGEXP_REPLACE(state, '\\s+', ' '))), '') AS st,
                    NULLIF(UPPER(TRIM(REGEXP_REPLACE(channel, '\\s+', ' '))), '') AS ch, TRIM(name) AS cell, NULLIF(TRIM(comment), '') AS cm,
                    REGEXP_REPLACE(CASE WHEN UPPER(TRIM(REPLACE(name, CHR(160), ' '))) IN ('N/A', 'OPEN', 'TBD') THEN '' ELSE COALESCE(REPLACE(name, CHR(160), ' '), '') END, '(\\s+[Oo][Rr])?\\s*/\\s*|\\s+[Oo][Rr]\\s+', '|') || '|' AS nm_split
             FROM IDENTIFIER($sheet_tbl)) x,
       LATERAL SPLIT_TO_TABLE(x.nm_split, '|') p),
sn AS (SELECT sp.*, COUNT(k) OVER (PARTITION BY rid) AS n_names FROM sp),
t AS (SELECT source, LPAD(LEFT(TRIM(zip_code), 5), 5, '0') AS zip_code, NULLIF(UPPER(TRIM(channel)), '') AS ch,
             NULLIF(UPPER(TRIM(state)), '') AS st, TRIM(COALESCE(NULLIF(TRIM(clean_name), ''), name)) AS spelling,
             NULLIF(NULLIF(UPPER(TRIM(REGEXP_REPLACE(TRIM(COALESCE(NULLIF(TRIM(clean_name), ''), name)), '\\s+', ' '))), ''), 'OPEN') AS nm
      FROM IDENTIFIER($terr_tbl)),
h0 AS (SELECT source, nm, MIN(spelling) AS name, LISTAGG(DISTINCT ch, ' ') WITHIN GROUP (ORDER BY ch) AS current_channels,
              COUNT(DISTINCT CASE WHEN ch = 'WH' THEN zip_code END) AS zips_wh,
              COUNT(DISTINCT CASE WHEN ch = 'FI' THEN zip_code END) AS zips_fi,
              LISTAGG(DISTINCT st, ' ') WITHIN GROUP (ORDER BY st) AS states
       FROM t WHERE nm IS NOT NULL AND source IS NOT NULL GROUP BY source, nm),
hn AS (SELECT h0.*, hk.holder_n,
              NULLIF(UPPER(TRIM(REGEXP_REPLACE(CASE WHEN POSITION(',' IN h0.nm) > 0
                                                    THEN SPLIT_PART(h0.nm, ',', 2) || ' ' || SPLIT_PART(h0.nm, ',', 1)
                                                    ELSE h0.nm END, '\\s+', ' '))), '') AS k
       FROM h0 JOIN IDENTIFIER($holder_tbl) hk
         ON hk.source = h0.source AND hk.holder_id = UUID_STRING('6ba7b810-9dad-11d1-80b4-00c04fd430c8', h0.nm)),
--each sheet slot naming a key: its state and channel, either when the cell names several
ks AS (SELECT DISTINCT hn.source, hn.holder_n, sn.rid, sn.st, sn.ch, sn.cm, sn.n_names
       FROM sn JOIN hn ON hn.k = sn.k),
kv AS (SELECT source, holder_n,
              LISTAGG(st || ' ' || COALESCE(ch, '(blank)') || CASE WHEN n_names > 1 THEN ' either' ELSE '' END, '; ')
                WITHIN GROUP (ORDER BY st, ch) AS sheet_slots,
              LISTAGG(DISTINCT COALESCE(ch, '(blank)'), ' ') WITHIN GROUP (ORDER BY COALESCE(ch, '(blank)')) AS sheet_channels,
              CASE WHEN COUNT(DISTINCT COALESCE(ch, '(blank)')) > 1 THEN 1 ELSE 0 END AS two_channels,
              LISTAGG(DISTINCT cm, ' | ') WITHIN GROUP (ORDER BY cm) AS sheet_comments
       FROM ks GROUP BY source, holder_n)
SELECT hn.source || ':R' || CAST(hn.holder_n AS VARCHAR) AS key, hn.name, hn.current_channels, hn.zips_wh, hn.zips_fi,
       hn.states, kv.sheet_slots, kv.sheet_channels, kv.two_channels, kv.sheet_comments,
       ROW_NUMBER() OVER (ORDER BY CASE WHEN kv.holder_n IS NULL THEN 1 ELSE 0 END, kv.two_channels DESC, hn.source, hn.holder_n) AS row_n
FROM hn LEFT JOIN kv ON kv.source = hn.source AND kv.holder_n = hn.holder_n;
SELECT * EXCLUDE (row_n) FROM ssdb_integration.lr_strategy.key_names ORDER BY row_n;
