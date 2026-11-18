use role rl_ssdb_Integration_Lr_Strategy_Rw;
use database ssdb_Integration;
use schema lr_strategy;
--Saves its result as the transient table td_x_sheet_slots (replaced on every run, ROW_N its order) for filtering in a
--scratch file with F6, e.g. SELECT * FROM td_x_sheet_slots WHERE ...  The last statement shows it.
--The shortlist sheet's slots by holder key, NO NAMES and no comment text: safe to send to an agent.  It writes only its td_x table, one result.
--Owner, 2026-11-18: "should we just work directly with the wholesaler name keys? so i can explicitly give you the logic
--while still masking names".  A NAME cell may hold several names (Ann Lee or Bo Ray, Ann Lee / Bo Ray: split on the whole
--word OR in any case and on a slash), the key is 03's: a comma flipped, upper case, single spaces.  A holder is a name in the
--territories table (not blank, not OPEN) of either firm, its key R<n> is td_holder_key's (02_model_extract.sql builds it, this file
--only reads it): R<n> of the same source and of the UUID of the normalized name, as 02.
--Result, SECTION first.  Sheet rows come first, one per sheet row, then one row per holder key on the sheet:
--  SLOT    STATE (a two-letter code, or the full state name as the sheet has it when it is a known one, upper case, (blank), or OTHER), CHANNEL (NATIONAL, REGIONAL, WH, FI, WIFI,
--          (blank) or OTHER), N_NAMES the names in the cell, CANDIDATES the cell's names as holder keys joined with ' or ' in the
--          cell's order, each <SOURCE>:R<n> (a name that matches holders of both firms gives both keys), NEW<k> for a name no
--          holder has (k numbers the new names in this result, the same new name has the same k on every row), NO KEY for a
--          name a holder has but td_holder_key has no row for (Run All 02_model_extract.sql, then this file), (open) for a blank NAME
--  HOLDER  HOLDER <SOURCE>:R<n> of a key a sheet name has, CURRENT_CHANNELS the territory channels it holds, ZIPS_WH and ZIPS_FI
--          its ZIPs in WH and FI
--No sheet text but those labels reaches the result.  ZIP_CODE is LPAD(LEFT(TRIM(..), 5), 5, '0').
SET sheet_tbl  = 'ssdb_integration.lr_strategy.channel_contacts';
SET terr_tbl   = 'ssdb_integration.lr_strategy.territories_tableau';
SET holder_tbl = 'ssdb_integration.lr_strategy.td_holder_key';
CREATE OR REPLACE TRANSIENT TABLE ssdb_integration.lr_strategy.td_x_sheet_slots AS
WITH
sp AS (SELECT x.rid, x.st, x.ch, p.index AS ix,
              NULLIF(NULLIF(NULLIF(NULLIF(UPPER(TRIM(REGEXP_REPLACE(CASE WHEN POSITION(',' IN p.value) > 0
                                                    THEN SPLIT_PART(p.value, ',', 2) || ' ' || SPLIT_PART(p.value, ',', 1)
                                                    ELSE p.value END, '\\s+', ' '))), ''), 'N/A'), 'OPEN'), 'TBD') AS k
       FROM (SELECT ROW_NUMBER() OVER (ORDER BY name, state, channel, comment) AS rid,
                    NULLIF(UPPER(TRIM(REGEXP_REPLACE(state, '\\s+', ' '))), '') AS st,
                    NULLIF(UPPER(TRIM(REGEXP_REPLACE(channel, '\\s+', ' '))), '') AS ch,
                    REGEXP_REPLACE(CASE WHEN UPPER(TRIM(REPLACE(name, CHR(160), ' '))) IN ('N/A', 'OPEN', 'TBD') THEN '' ELSE COALESCE(REPLACE(name, CHR(160), ' '), '') END, '(\\s+[Oo][Rr])?\\s*/\\s*|\\s+[Oo][Rr]\\s+', '|') || '|' AS nm_split
             FROM IDENTIFIER($sheet_tbl)) x,
       LATERAL SPLIT_TO_TABLE(x.nm_split, '|') p),
sn AS (SELECT sp.*, COUNT(k) OVER (PARTITION BY rid) AS n_names FROM sp),
--one row per name, a sheet row with no name once with K blank
s AS (SELECT * FROM sn WHERE k IS NOT NULL OR (n_names = 0 AND ix = 1)),
fs AS (SELECT column1 AS st, column2 AS code FROM VALUES
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
       ('WEST VIRGINIA', 'WV'), ('WISCONSIN', 'WI'), ('WYOMING', 'WY')),
t AS (SELECT source, LPAD(LEFT(TRIM(zip_code), 5), 5, '0') AS zip_code, NULLIF(UPPER(TRIM(channel)), '') AS ch,
             NULLIF(NULLIF(UPPER(TRIM(REGEXP_REPLACE(TRIM(COALESCE(NULLIF(TRIM(clean_name), ''), name)), '\\s+', ' '))), ''), 'OPEN') AS nm
      FROM IDENTIFIER($terr_tbl)),
h0 AS (SELECT source, nm, LISTAGG(DISTINCT ch, ' ') WITHIN GROUP (ORDER BY ch) AS current_channels,
              COUNT(DISTINCT CASE WHEN ch = 'WH' THEN zip_code END) AS zips_wh,
              COUNT(DISTINCT CASE WHEN ch = 'FI' THEN zip_code END) AS zips_fi
       FROM t WHERE nm IS NOT NULL AND source IS NOT NULL GROUP BY source, nm),
--a holder with its match key and its number (holder_n blank: td_holder_key has no row)
hn AS (SELECT h0.source, NULLIF(UPPER(TRIM(REGEXP_REPLACE(CASE WHEN POSITION(',' IN h0.nm) > 0
                                                              THEN SPLIT_PART(h0.nm, ',', 2) || ' ' || SPLIT_PART(h0.nm, ',', 1)
                                                              ELSE h0.nm END, '\\s+', ' '))), '') AS k,
              hk.holder_n, h0.current_channels, h0.zips_wh, h0.zips_fi
       FROM h0 LEFT JOIN IDENTIFIER($holder_tbl) hk
         ON hk.source = h0.source AND hk.holder_id = UUID_STRING('6ba7b810-9dad-11d1-80b4-00c04fd430c8', h0.nm)),
sl AS (SELECT s.rid, s.ix, s.k, s.n_names,
              CASE WHEN s.st IS NULL THEN '(blank)' WHEN c1.st IS NOT NULL OR c2.code IS NOT NULL THEN s.st
                   ELSE 'OTHER' END AS state,
              CASE WHEN s.ch IS NULL THEN '(blank)' WHEN s.ch IN ('NATIONAL', 'REGIONAL', 'WH', 'FI', 'WIFI') THEN s.ch
                   ELSE 'OTHER' END AS channel
       FROM s LEFT JOIN fs c1 ON c1.st = s.st LEFT JOIN (SELECT DISTINCT code FROM fs) c2 ON c2.code = s.st),
--the names no holder has, numbered over this result
nw AS (SELECT k, DENSE_RANK() OVER (ORDER BY k) AS r
       FROM (SELECT DISTINCT k FROM sl WHERE k IS NOT NULL AND k NOT IN (SELECT k FROM hn WHERE k IS NOT NULL))),
tk AS (SELECT DISTINCT sl.rid, sl.ix,
              CASE WHEN sl.k IS NULL THEN '(open)' WHEN hn.source IS NULL THEN 'NEW' || CAST(nw.r AS VARCHAR)
                   WHEN hn.holder_n IS NULL THEN 'NO KEY' ELSE hn.source || ':R' || CAST(hn.holder_n AS VARCHAR) END AS tok,
              CASE WHEN hn.holder_n IS NOT NULL THEN hn.source END AS so, hn.holder_n AS nn
       FROM sl LEFT JOIN hn ON hn.k = sl.k LEFT JOIN nw ON nw.k = sl.k),
slots AS (SELECT l.state, l.channel, l.n_names, c.cands
          FROM (SELECT rid, MAX(state) AS state, MAX(channel) AS channel, MAX(n_names) AS n_names FROM sl GROUP BY rid) l
          JOIN (SELECT rid, LISTAGG(tok, ' or ') WITHIN GROUP (ORDER BY ix, so, nn) AS cands FROM tk GROUP BY rid) c ON c.rid = l.rid),
hs AS (SELECT DISTINCT source, holder_n, current_channels, zips_wh, zips_fi FROM hn
       WHERE holder_n IS NOT NULL AND k IN (SELECT k FROM sl WHERE k IS NOT NULL))
SELECT section, state, channel, n_names, candidates, holder, current_channels, zips_wh, zips_fi,
       ROW_NUMBER() OVER (ORDER BY o, state, channel, candidates, holder) AS row_n FROM (
  SELECT 1 AS o, 'SLOT' AS section, state, channel, n_names, cands AS candidates, CAST(NULL AS VARCHAR) AS holder,
         CAST(NULL AS VARCHAR) AS current_channels, CAST(NULL AS INTEGER) AS zips_wh, CAST(NULL AS INTEGER) AS zips_fi FROM slots
  UNION ALL SELECT 2, 'HOLDER', NULL, NULL, NULL, NULL, source || ':R' || CAST(holder_n AS VARCHAR), current_channels, zips_wh, zips_fi FROM hs);
SELECT * EXCLUDE (row_n) FROM ssdb_integration.lr_strategy.td_x_sheet_slots ORDER BY row_n;
