use role rl_ssdb_Integration_Lr_Strategy_Rw;
use database ssdb_Integration;
use schema lr_strategy;

--The current state, labelled with the assignments (the roster 03_assignments.sql builds).  One Run All file.  It builds
--four tables for the maps and ends on one result of checks.  Set the three table names below, nothing else.
--NOTHING HERE CHANGES A TERRITORY (owner, 2026-11-16: "we are simply looking at the current state, with the additional
--assignments data").  A wholesaler's territory is their rows of the territories table as they are, one piece per ZIP x
--territory channel.  A cell's holder is the holder of its SOURCE x ZIP x DIST_CH there (the union's OLD_TERR_WHOLESALER
--agrees, DATASET_LOG 2026-11-15).  Opportunity is the main map: the union's CHANNEL NATIONAL, WH or FI (its fine
--channels WH, FI, Wells WH, Wells FI, National (Chase) in NEW_DIST), once per cell as 02_model_extract.sql, never added
--across estimates: every opportunity column comes with its estimate's SOURCE (EST_SOURCE).
--The assignments only label: KEPT, ROLE, ASSIGNED_STATES.  A cell's FIT_CHANNEL is the side its opportunity counts for:
--WH or FI for those fine channels, and for Wells WH, Wells FI and National (Chase) NATIONAL where a kept NATIONAL wholesaler
--has an in-role piece on the ZIP, otherwise the side Q29 (DATASET_LOG Settled) gives them, Wells WH WH, Wells FI and
--National (Chase) FI (owner, 2026-11-17: "yes that's the right fix").  A role fits FIT_CHANNEL: WH fits WH, FI fits FI,
--WIFI fits WH and FI, NATIONAL fits NATIONAL.  No cell changes holder: FIT_CHANNEL only says which role it counts for.  A piece is in role when its territory channel can hold what the role fits:
--WH for WH, FI for FI, WH or FI for WIFI and NATIONAL.
--Tables (replaced on every run).  TD_MAP_PIECE and TD_MAP_WHOLESALER hold wholesaler names and stay in Snowflake:
--  TD_MAP_PIECE       every territory piece: SOURCE, WHOLESALER, KEPT, ROLE, ZIP_CODE, STATE, TERR_CHANNEL, PIECE_IN_ROLE,
--                     IN_ASSIGNED_STATE (NULL when no states are assigned), and on a kept wholesaler's in-role piece
--                     N_ROLE_HOLDERS, N_ROLE_FIRMS: the kept wholesalers of the same role, either source, with an in-role
--                     piece on the ZIP (2 or more is an overlap).
--  TD_MAP_CELL        the main map's cells: EST_SOURCE, ZIP_CODE, STATE, DIST_CH, NEW_DIST, CHANNEL, NEW_TERR_CHANNEL,
--                     FIT_CHANNEL, MM_OPP, N_HOLDERS,
--                     HOLDER_STATUS: KEPT IN ROLE, KEPT OUT OF ROLE, NOT KEPT (OPEN), NO HOLDER TODAY.  No names.
--  TD_MAP_WHOLESALER  one row per wholesaler x EST_SOURCE: KEPT, ROLE, ASSIGNED_STATES, N_ZIPS, N_ZIPS_IN_ROLE, STATES, the
--                     opportunity of their pieces OPP_MAIN = OPP_IN_ROLE + OPP_OUT_OF_ROLE, OPP_OVERLAP (in role, on in-role
--                     pieces whose ZIP has N_ROLE_HOLDERS 2 or more), OPP_IN_ASSIGNED_STATES (NULL when none).  On the wholesaler's
--                     own source only: SALES_MAIN (their sales with the union's CHANNEL NATIONAL, WH or FI) and
--                     SALES_MAIN_IN_OWN_ZIPS (of them, in a ZIP they hold in any channel).
--  (in role: the role fits the cell's FIT_CHANNEL, whatever the piece's channel: FI opportunity held today in an IFA piece is
--  in role for a WIFI or FI wholesaler.)
--  TD_MAP_ZIP         ZIP x role: N_ROLE_HOLDERS, N_ROLE_FIRMS, the overlap layer for the maps.  No names.
--Result: SECTION, SOURCE, K1, K2, N, MM_OPP, PCT, MUST_BE_ZERO.  No wholesaler name and no sales dollar: it can be sent back.
--  ROSTER       K1 the count's name.  MUST_BE_ZERO = 1 rows must have N 0 before the tables are used.
--  ROLES        K1 role.  N kept wholesalers.
--  OPPORTUNITY  SOURCE the estimate, K1 NEW_DIST, K2 holder status.  N cells, MM_OPP.  Per estimate the rows are the main map.
--  OVERLAP      SOURCE the estimate, K1 role, K2 kept holders of the role on the ZIP and their firms.  N ZIPs with the estimate's opportunity in the
--               channels the role fits, MM_OPP the
--               estimate's main-map opportunity there in the channels the role fits.
--  SALES        K1 the seller, K2 where the sale is.  N rows, PCT of the source's main-map sales.
--  TIE          the tables against the union, and (information) the national fine channels by the union's NEW_TERR_CHANNEL,
--               the channel the dataset gives their new-state holder, to read against Q29's side.
--A wholesaler is matched by name in upper case with single spaces.  ZIP_CODE is LPAD(LEFT(TRIM(..), 5), 5, '0').

SET union_tbl  = 'ssdb_integration.lr_strategy.sales_opp_2026_11_9';
SET terr_tbl   = 'ssdb_integration.lr_strategy.territories_tableau';
SET assign_tbl = 'ssdb_integration.lr_strategy.td_assignments';

--1 the roster, one row per SOURCE x normalized name
CREATE OR REPLACE TEMPORARY TABLE ssdb_integration.lr_strategy.tmp_m_roster AS
SELECT source, nm, MIN(wholesaler) AS wholesaler, MAX(kept) AS kept, MAX(role) AS role, MAX(assigned_states) AS assigned_states,
       COUNT(*) AS n_rows
FROM (SELECT source, TRIM(wholesaler) AS wholesaler,
             NULLIF(UPPER(TRIM(REGEXP_REPLACE(TRIM(wholesaler), '\\s+', ' '))), '') AS nm,
             CASE WHEN COALESCE(UPPER(TRIM(CAST(kept AS VARCHAR))), '') IN ('Y', 'YES', 'TRUE', '1') THEN 'Y'
                  WHEN COALESCE(UPPER(TRIM(CAST(kept AS VARCHAR))), '') IN ('N', 'NO', 'FALSE', '0') THEN 'N'
                  WHEN COALESCE(UPPER(TRIM(CAST(kept AS VARCHAR))), '') = '' THEN '' ELSE '?' END AS kept,
             COALESCE(UPPER(TRIM(role)), '') AS role,
             COALESCE(UPPER(TRIM(REGEXP_REPLACE(REPLACE(assigned_states, ',', ' '), '\\s+', ' '))), '') AS assigned_states
      FROM IDENTIFIER($assign_tbl))
WHERE nm IS NOT NULL AND source IS NOT NULL
GROUP BY source, nm;

--2 the territories as they are, every channel
CREATE OR REPLACE TEMPORARY TABLE ssdb_integration.lr_strategy.tmp_m_hold AS
SELECT source, zip_code, ch, nm, MIN(st) AS st
FROM (SELECT source, LPAD(LEFT(TRIM(zip_code), 5), 5, '0') AS zip_code, COALESCE(UPPER(TRIM(channel)), '') AS ch,
             NULLIF(UPPER(TRIM(state)), '') AS st,
             NULLIF(NULLIF(UPPER(TRIM(REGEXP_REPLACE(TRIM(COALESCE(NULLIF(TRIM(clean_name), ''), name)), '\\s+', ' '))), ''), 'OPEN') AS nm
      FROM IDENTIFIER($terr_tbl))
WHERE nm IS NOT NULL AND source IS NOT NULL
GROUP BY source, zip_code, ch, nm;

--3 the main map's opportunity, once per cell, by SOURCE x ZIP x DIST_CH x NEW_DIST x CHANNEL
CREATE OR REPLACE TEMPORARY TABLE ssdb_integration.lr_strategy.tmp_m_cell AS
SELECT source, zip_code, MIN(st) AS st, dist_ch, new_dist, channel, ntc, SUM(opp) AS mm_opp
FROM (SELECT source, LPAD(LEFT(TRIM(zip_code), 5), 5, '0') AS zip_code, MIN(NULLIF(UPPER(TRIM(state)), '')) AS st,
             COALESCE(UPPER(TRIM(dist_ch)), '') AS dist_ch, UPPER(TRIM(new_dist)) AS new_dist, UPPER(TRIM(channel)) AS channel,
             COALESCE(UPPER(TRIM(new_terr_channel)), '') AS ntc, MAX(CASE WHEN mm_opp > 0 THEN mm_opp END) AS opp
      FROM IDENTIFIER($union_tbl)
      WHERE UPPER(TRIM(channel)) IN ('NATIONAL', 'WH', 'FI')
      GROUP BY source, fiscal_yr, LPAD(LEFT(TRIM(zip_code), 5), 5, '0'), cbd_id, firm, parent, firm_key, firm_crd, product_v2,
               dist_ch, new_dist, file_new_dist, channel, new_terr_channel
      HAVING MAX(CASE WHEN mm_opp > 0 THEN mm_opp END) IS NOT NULL)
GROUP BY source, zip_code, dist_ch, new_dist, channel, ntc;

--3b the main map's sales rows, with whether the seller holds a territory and holds the sale's ZIP
CREATE OR REPLACE TEMPORARY TABLE ssdb_integration.lr_strategy.tmp_m_sale AS
SELECT s.source, s.nm, s.zip_code, s.amt, CASE WHEN hs.nm IS NULL THEN 0 ELSE 1 END AS seller_holds,
       CASE WHEN hz.nm IS NULL THEN 0 ELSE 1 END AS in_own_zip
FROM (SELECT source, LPAD(LEFT(TRIM(zip_code), 5), 5, '0') AS zip_code, actual_sales_amount AS amt,
             NULLIF(NULLIF(UPPER(TRIM(REGEXP_REPLACE(TRIM(sales_wholesaler), '\\s+', ' '))), ''), 'OPEN') AS nm
      FROM IDENTIFIER($union_tbl)
      WHERE UPPER(TRIM(channel)) IN ('NATIONAL', 'WH', 'FI') AND actual_sales_amount <> 0) s
LEFT JOIN (SELECT DISTINCT source, nm FROM ssdb_integration.lr_strategy.tmp_m_hold) hs ON hs.source = s.source AND hs.nm = s.nm
LEFT JOIN (SELECT DISTINCT source, nm, zip_code FROM ssdb_integration.lr_strategy.tmp_m_hold) hz
       ON hz.source = s.source AND hz.nm = s.nm AND hz.zip_code = s.zip_code;

--4 the pieces, labelled
CREATE OR REPLACE TEMPORARY TABLE ssdb_integration.lr_strategy.tmp_m_piece AS
SELECT h.source, h.nm, COALESCE(r.wholesaler, h.nm) AS wholesaler, COALESCE(r.kept, '') AS kept, COALESCE(r.role, '') AS role,
       COALESCE(r.assigned_states, '') AS assigned_states, h.zip_code, h.st, h.ch,
       CASE WHEN r.kept = 'Y' AND ((r.role = h.ch AND h.ch IN ('WH', 'FI')) OR (r.role IN ('WIFI', 'NATIONAL') AND h.ch IN ('WH', 'FI')))
            THEN 1 ELSE 0 END AS piece_in_role,
       CASE WHEN COALESCE(r.assigned_states, '') = '' THEN NULL
            WHEN (' ' || r.assigned_states || ' ') LIKE '% ' || h.st || ' %' THEN 1 ELSE 0 END AS in_assigned_state
FROM ssdb_integration.lr_strategy.tmp_m_hold h
LEFT JOIN ssdb_integration.lr_strategy.tmp_m_roster r ON r.source = h.source AND r.nm = h.nm;

CREATE OR REPLACE TABLE ssdb_integration.lr_strategy.td_map_zip AS
SELECT zip_code, role, COUNT(DISTINCT source || '|' || nm) AS n_role_holders, COUNT(DISTINCT source) AS n_role_firms
FROM ssdb_integration.lr_strategy.tmp_m_piece WHERE piece_in_role = 1 GROUP BY zip_code, role;

--5 the tables
CREATE OR REPLACE TABLE ssdb_integration.lr_strategy.td_map_piece AS
SELECT p.source, p.wholesaler, p.kept, p.role, p.zip_code, p.st AS state, p.ch AS terr_channel, p.piece_in_role,
       p.in_assigned_state, CASE WHEN p.piece_in_role = 1 THEN z.n_role_holders END AS n_role_holders,
       CASE WHEN p.piece_in_role = 1 THEN z.n_role_firms END AS n_role_firms
FROM ssdb_integration.lr_strategy.tmp_m_piece p
LEFT JOIN ssdb_integration.lr_strategy.td_map_zip z ON z.zip_code = p.zip_code AND z.role = p.role;

CREATE OR REPLACE TABLE ssdb_integration.lr_strategy.td_map_cell AS
WITH f AS (SELECT c.*, CASE WHEN c.new_dist IN ('WELLS WH', 'WELLS FI', 'NATIONAL (CHASE)') AND n.zip_code IS NOT NULL THEN 'NATIONAL'
                            WHEN c.new_dist IN ('WH', 'WELLS WH') THEN 'WH' ELSE 'FI' END AS fit_channel
           FROM ssdb_integration.lr_strategy.tmp_m_cell c
           LEFT JOIN ssdb_integration.lr_strategy.td_map_zip n ON n.zip_code = c.zip_code AND n.role = 'NATIONAL')
SELECT f.source AS est_source, f.zip_code, f.st AS state, f.dist_ch, f.new_dist, f.channel, f.ntc AS new_terr_channel, f.fit_channel,
       f.mm_opp, COUNT(p.nm) AS n_holders,
       CASE WHEN COUNT(p.nm) = 0 THEN 'NO HOLDER TODAY'
            WHEN MAX(CASE WHEN p.kept = 'Y' AND (p.role = f.fit_channel OR (p.role = 'WIFI' AND f.fit_channel IN ('WH', 'FI'))) THEN 1 ELSE 0 END) = 1
                 THEN 'KEPT IN ROLE'
            WHEN MAX(CASE WHEN p.kept = 'Y' THEN 1 ELSE 0 END) = 1 THEN 'KEPT OUT OF ROLE'
            ELSE 'NOT KEPT (OPEN)' END AS holder_status
FROM f
LEFT JOIN ssdb_integration.lr_strategy.tmp_m_piece p ON p.source = f.source AND p.zip_code = f.zip_code AND p.ch = f.dist_ch
GROUP BY f.source, f.zip_code, f.st, f.dist_ch, f.new_dist, f.channel, f.ntc, f.fit_channel, f.mm_opp;

CREATE OR REPLACE TABLE ssdb_integration.lr_strategy.td_map_wholesaler AS
WITH w AS (SELECT DISTINCT source, nm, wholesaler, kept, role, assigned_states FROM ssdb_integration.lr_strategy.tmp_m_piece),
     e AS (SELECT DISTINCT est_source FROM ssdb_integration.lr_strategy.td_map_cell),
     zc AS (SELECT source, nm, COUNT(DISTINCT zip_code) AS n_zips, COUNT(DISTINCT CASE WHEN piece_in_role = 1 THEN zip_code END) AS n_zips_in_role
            FROM ssdb_integration.lr_strategy.tmp_m_piece GROUP BY source, nm),
     sl AS (SELECT source, nm, LISTAGG(st, ' ') WITHIN GROUP (ORDER BY st) AS states
            FROM (SELECT DISTINCT source, nm, st FROM ssdb_integration.lr_strategy.tmp_m_piece WHERE st IS NOT NULL) GROUP BY source, nm),
     o AS (SELECT p.source, p.nm, c.est_source, SUM(c.mm_opp) AS opp_main,
                  SUM(CASE WHEN p.kept = 'Y' AND (p.role = c.fit_channel OR (p.role = 'WIFI' AND c.fit_channel IN ('WH', 'FI'))) THEN c.mm_opp ELSE 0 END) AS opp_in_role,
                  SUM(CASE WHEN p.kept = 'Y' AND (p.role = c.fit_channel OR (p.role = 'WIFI' AND c.fit_channel IN ('WH', 'FI'))) AND z.n_role_holders > 1
                           THEN c.mm_opp ELSE 0 END) AS opp_overlap,
                  SUM(CASE WHEN p.in_assigned_state = 1 THEN c.mm_opp ELSE 0 END) AS opp_in_assigned_states
           FROM ssdb_integration.lr_strategy.tmp_m_piece p
           JOIN ssdb_integration.lr_strategy.td_map_cell c ON c.zip_code = p.zip_code AND c.dist_ch = p.ch
           LEFT JOIN ssdb_integration.lr_strategy.td_map_zip z ON z.zip_code = p.zip_code AND z.role = p.role AND p.piece_in_role = 1
           GROUP BY p.source, p.nm, c.est_source),
     sa AS (SELECT source, nm, SUM(amt) AS sales_main, SUM(CASE WHEN in_own_zip = 1 THEN amt ELSE 0 END) AS sales_in_own
            FROM ssdb_integration.lr_strategy.tmp_m_sale GROUP BY source, nm)
SELECT w.source, w.wholesaler, w.kept, w.role, w.assigned_states, e.est_source, zc.n_zips, zc.n_zips_in_role, sl.states,
       COALESCE(o.opp_main, 0) AS opp_main, COALESCE(o.opp_in_role, 0) AS opp_in_role,
       COALESCE(o.opp_main, 0) - COALESCE(o.opp_in_role, 0) AS opp_out_of_role, COALESCE(o.opp_overlap, 0) AS opp_overlap,
       CASE WHEN w.assigned_states <> '' THEN COALESCE(o.opp_in_assigned_states, 0) END AS opp_in_assigned_states,
       CASE WHEN e.est_source = w.source THEN COALESCE(sa.sales_main, 0) END AS sales_main,
       CASE WHEN e.est_source = w.source THEN COALESCE(sa.sales_in_own, 0) END AS sales_main_in_own_zips
FROM w CROSS JOIN e
JOIN zc ON zc.source = w.source AND zc.nm = w.nm
LEFT JOIN sl ON sl.source = w.source AND sl.nm = w.nm
LEFT JOIN o ON o.source = w.source AND o.nm = w.nm AND o.est_source = e.est_source
LEFT JOIN sa ON sa.source = w.source AND sa.nm = w.nm;

--6 the one result
WITH
st AS (SELECT DISTINCT st FROM ssdb_integration.lr_strategy.tmp_m_hold WHERE st IS NOT NULL),
sc AS (SELECT r.source, r.nm, COUNT(DISTINCT st.st) AS n_known,
              CASE WHEN r.assigned_states = '' THEN 0
                   ELSE LENGTH(r.assigned_states) - LENGTH(REPLACE(r.assigned_states, ' ', '')) + 1 END AS n_codes
       FROM ssdb_integration.lr_strategy.tmp_m_roster r
       LEFT JOIN st ON (' ' || r.assigned_states || ' ') LIKE '% ' || st.st || ' %'
       GROUP BY r.source, r.nm, r.assigned_states),
ro AS (SELECT r.*, CASE WHEN hs.nm IS NULL THEN 0 ELSE 1 END AS in_terr, CASE WHEN ir.nm IS NULL THEN 0 ELSE 1 END AS has_in_role,
              sc.n_known, sc.n_codes
       FROM ssdb_integration.lr_strategy.tmp_m_roster r
       JOIN sc ON sc.source = r.source AND sc.nm = r.nm
       LEFT JOIN (SELECT DISTINCT source, nm FROM ssdb_integration.lr_strategy.tmp_m_hold) hs ON hs.source = r.source AND hs.nm = r.nm
       LEFT JOIN (SELECT DISTINCT source, nm FROM ssdb_integration.lr_strategy.tmp_m_piece WHERE piece_in_role = 1) ir
              ON ir.source = r.source AND ir.nm = r.nm),
rc AS (SELECT source,
              SUM(n_rows) AS c01, COUNT(CASE WHEN kept = 'Y' THEN 1 END) AS c02, COUNT(CASE WHEN kept = 'N' THEN 1 END) AS c03,
              COUNT(CASE WHEN kept = '' THEN 1 END) AS c04, COUNT(CASE WHEN kept = '?' THEN 1 END) AS c05,
              COUNT(CASE WHEN role NOT IN ('NATIONAL', 'WH', 'FI', 'WIFI', '') THEN 1 END) AS c06,
              COUNT(CASE WHEN n_rows > 1 THEN 1 END) AS c07, COUNT(CASE WHEN kept = 'Y' AND role = '' THEN 1 END) AS c08,
              COUNT(CASE WHEN kept = 'Y' AND role <> '' AND in_terr = 0 THEN 1 END) AS c09,
              COUNT(CASE WHEN kept = 'Y' AND role IN ('NATIONAL', 'WH', 'FI', 'WIFI') AND in_terr = 1 AND has_in_role = 0 THEN 1 END) AS c10,
              COUNT(CASE WHEN n_known <> n_codes THEN 1 END) AS c12
       FROM ro GROUP BY source),
sale AS (SELECT s.source, s.amt,
                CASE WHEN s.nm IS NULL THEN 'NO SELLER (BLANK OR OPEN)' WHEN s.seller_holds = 0 THEN 'SELLER HOLDS NO TERRITORY'
                     WHEN r.kept = 'Y' THEN 'SELLER KEPT' ELSE 'SELLER NOT KEPT' END AS who,
                CASE WHEN s.in_own_zip = 1 THEN 'IN A ZIP THE SELLER HOLDS' ELSE 'NOT IN A ZIP THE SELLER HOLDS' END AS wh
         FROM ssdb_integration.lr_strategy.tmp_m_sale s
         LEFT JOIN ssdb_integration.lr_strategy.tmp_m_roster r ON r.source = s.source AND r.nm = s.nm),
fit AS (SELECT role, channel FROM (VALUES ('WH', 'WH'), ('FI', 'FI'), ('WIFI', 'WH'), ('WIFI', 'FI'), ('NATIONAL', 'NATIONAL')) AS v (role, channel)),
ov AS (SELECT c.est_source AS source, z.role, z.zip_code,
              CASE WHEN z.n_role_holders >= 4 THEN '4+' ELSE CAST(z.n_role_holders AS VARCHAR) END || ' KEPT HOLDERS, '
                  || CAST(z.n_role_firms AS VARCHAR) || ' FIRM(S)' AS band,
              SUM(c.mm_opp) AS opp
       FROM ssdb_integration.lr_strategy.td_map_zip z
       JOIN fit ON fit.role = z.role
       JOIN ssdb_integration.lr_strategy.td_map_cell c ON c.zip_code = z.zip_code AND c.fit_channel = fit.channel
       GROUP BY c.est_source, z.role, z.zip_code, z.n_role_holders, z.n_role_firms)
SELECT 'ROSTER' AS section, rc.source, v.name AS k1, CAST(NULL AS VARCHAR) AS k2,
       CASE v.i WHEN 1 THEN rc.c01 WHEN 2 THEN rc.c02 WHEN 3 THEN rc.c03 WHEN 4 THEN rc.c04 WHEN 5 THEN rc.c05 WHEN 6 THEN rc.c06
                WHEN 7 THEN rc.c07 WHEN 8 THEN rc.c08 WHEN 9 THEN rc.c09 WHEN 10 THEN rc.c10 ELSE rc.c12 END AS n,
       CAST(NULL AS DOUBLE) AS mm_opp, CAST(NULL AS DOUBLE) AS pct, v.mbz AS must_be_zero
FROM rc CROSS JOIN (SELECT i, name, mbz FROM (VALUES
       (1, '01 ROWS', 0), (2, '02 KEPT Y', 0), (3, '03 KEPT N', 0), (4, '04 KEPT BLANK (NOT DECIDED)', 0),
       (5, '05 KEPT NOT Y, N OR BLANK', 1), (6, '06 ROLE NOT NATIONAL, WH, FI, WIFI OR BLANK', 1), (7, '07 WHOLESALER ON 2+ ROWS', 1),
       (8, '08 KEPT WITH NO ROLE (OUTSIDE THE MAIN MAP)', 0), (9, '09 KEPT WITH A ROLE, NAME NOT IN THE TERRITORIES', 0),
       (10, '10 KEPT WITH A ROLE, NO PIECE IN ROLE (HOLDS NO WH OR FI)', 0),
       (12, '12 ASSIGNED_STATES CODE NOT A TERRITORY STATE (OR TWICE)', 1)) AS t (i, name, mbz)) v
UNION ALL
SELECT 'ROSTER', h.source, '11 HOLDERS NOT ON THE ROSTER (NOT KEPT)', NULL, COUNT(DISTINCT CASE WHEN r.nm IS NULL THEN h.nm END), NULL, NULL, 0
FROM ssdb_integration.lr_strategy.tmp_m_hold h
LEFT JOIN ssdb_integration.lr_strategy.tmp_m_roster r ON r.source = h.source AND r.nm = h.nm GROUP BY h.source
UNION ALL
SELECT 'ROLES', source, role, NULL, COUNT(*), NULL, NULL, 0 FROM ro WHERE kept = 'Y' AND role <> '' GROUP BY source, role
UNION ALL
SELECT 'OPPORTUNITY', est_source, new_dist, holder_status, COUNT(*), SUM(mm_opp), NULL, 0
FROM ssdb_integration.lr_strategy.td_map_cell GROUP BY est_source, new_dist, holder_status
UNION ALL
SELECT 'OVERLAP', source, role, band, COUNT(*), SUM(opp), NULL, 0 FROM ov GROUP BY source, role, band
UNION ALL
SELECT 'SALES', source, who, wh, COUNT(*), NULL, 100 * SUM(amt) / NULLIF(SUM(SUM(amt)) OVER (PARTITION BY source), 0), 0
FROM sale GROUP BY source, who, wh
UNION ALL
SELECT 'TIE', o.source, 'TD_MAP_CELL MINUS THE UNION, MAIN MAP (N 1 = THEY DIFFER)', NULL,
       CASE WHEN ABS(COALESCE(c.opp, 0) - o.opp) > 0.5 OR COALESCE(c.n, 0) <> o.n THEN 1 ELSE 0 END, COALESCE(c.opp, 0) - o.opp, NULL, 1
FROM (SELECT source, SUM(mm_opp) AS opp, COUNT(*) AS n FROM ssdb_integration.lr_strategy.tmp_m_cell GROUP BY source) o
LEFT JOIN (SELECT est_source, SUM(mm_opp) AS opp, COUNT(*) AS n FROM ssdb_integration.lr_strategy.td_map_cell GROUP BY est_source) c
       ON c.est_source = o.source
UNION ALL
SELECT 'TIE', source, 'MAIN MAP CELLS WHOSE NEW_DIST IS NOT WH, FI, WELLS WH, WELLS FI OR NATIONAL (CHASE)', NULL,
       COUNT(CASE WHEN new_dist NOT IN ('WH', 'FI', 'WELLS WH', 'WELLS FI', 'NATIONAL (CHASE)') THEN 1 END),
       SUM(CASE WHEN new_dist NOT IN ('WH', 'FI', 'WELLS WH', 'WELLS FI', 'NATIONAL (CHASE)') THEN mm_opp ELSE 0 END), NULL, 1
FROM ssdb_integration.lr_strategy.tmp_m_cell GROUP BY source
UNION ALL
SELECT 'TIE', est_source, 'NATIONAL FINE CHANNELS BY NEW_TERR_CHANNEL (INFORMATION)', new_dist || ' -> ' || new_terr_channel,
       COUNT(*), SUM(mm_opp), NULL, 0
FROM ssdb_integration.lr_strategy.td_map_cell WHERE new_dist IN ('WELLS WH', 'WELLS FI', 'NATIONAL (CHASE)')
GROUP BY est_source, new_dist, new_terr_channel
UNION ALL
SELECT 'TIE', source, 'ROWS WITH NEW_DIST WH, FI, WELLS WH, WELLS FI OR NATIONAL (CHASE) AND CHANNEL NOT NATIONAL, WH OR FI', NULL,
       COUNT(CASE WHEN bad THEN 1 END), COALESCE(SUM(CASE WHEN bad THEN mm_opp END), 0), NULL, 1
FROM (SELECT source, mm_opp,
             UPPER(TRIM(new_dist)) IN ('WH', 'FI', 'WELLS WH', 'WELLS FI', 'NATIONAL (CHASE)')
             AND COALESCE(UPPER(TRIM(channel)), '') NOT IN ('NATIONAL', 'WH', 'FI') AND mm_opp > 0 AS bad
      FROM IDENTIFIER($union_tbl))
GROUP BY source
ORDER BY section, source, k1, k2;
