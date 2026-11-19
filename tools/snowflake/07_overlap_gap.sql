use role rl_ssdb_Integration_Lr_Strategy_Rw;
use database ssdb_Integration;
use schema lr_strategy;

--Overlaps and gaps per roster scenario (issue 148).  One Run All file, run after 03_assignments.sql and 04_assigned_coverage.sql in the
--same session for the same scenario.  Set SET scenario to the scenario you ran 03 with (the scenario run replaces that line as in 03), the
--table names below, nothing else.  It builds three tables and ends on one result of checks.  No wholesaler name anywhere: a person is the
--holder key R<n> of td_holder_key (02_model_extract.sql, only read here, as 06_map_extract.sql), ASSIGNED_STATES is built from the cells' own
--state codes, so no owner-typed text leaves.  TD_MAP_PIECE and td_assignments hold names and are only read.
--Attribution, per cell of TD_MAP_CELL (a row each, the estimate EST_SOURCE x ZIP x DIST_CH x NEW_DIST x CHANNEL, never added across
--estimates), owner, 2026-11-18: "national first, then WH, then WIFI".  A person is assigned to a state when it is in their ASSIGNED_STATES
--(kept Y, ROLE NATIONAL, WH or WIFI, ROLE FI is not in this file).  The cell goes to
--  NATIONAL   NEW_DIST National (Chase), Wells FI or Wells WH, and a NATIONAL person is assigned to the cell's STATE
--  WH         else NEW_DIST WH or Wells WH, and a WH person is assigned there
--  REGIONAL   else, any NEW_DIST, a WIFI person is assigned there
--  OPEN       else
--HOLDERS of a cell are the kept people of the channel's role (OPEN: any of the three roles) with an in-role piece (TD_MAP_PIECE PIECE_IN_ROLE
--1, either firm) on the ZIP, whatever the piece's channel.  Class, one per cell:
--  OPEN seat      CHANNEL OPEN: OPEN SEAT HELD with a holder, OPEN SEAT UNHELD without
--  GAP (HELD TODAY)  assigned, no holder, but someone else has the ZIP in a territory today of the channel's kind (a WH piece for WH,
--                 a WH or FI piece otherwise): mostly holders not on the sheet, a hand-over to the assigned person (owner, 2026-11-18, #149)
--  GAP (UNHELD)   assigned, no holder and no such piece: no one works it today
--  OVERLAP        two or more holders
--  COVERED        one holder and it is an assigned person
--  HELD BY ANOTHER  one holder and it is not an assigned person
--A state the sheet splits between two or more people of one channel (several slots of a state, e.g. two REGIONAL) is not a
--class of its own (owner's sheet, 2026-11-18): its cells are classed the same way against the set of its assigned people,
--ASSIGNED lists them all, and a COVERED cell counts for its holder only.  DOUBLE ASSIGNED is no longer produced.
--Tables (replaced on every run), SCENARIO is SET scenario trimmed:
--  TD_GAP_CELL    SCENARIO, EST_SOURCE, ZIP_CODE, STATE, NEW_DIST, MM_OPP, CHANNEL, ASSIGNED (keys 'R12 R40' by number, NULL for OPEN), CLASS,
--                 N_HOLDERS, HOLDERS (keys the same way).  One row per TD_MAP_CELL row.
--  TD_GAP_PAIR    SCENARIO, EST_SOURCE, CHANNEL, HOLDER_A, HOLDER_B (A before B by number), N_ZIPS, MM_OPP: each unordered pair of holders of each
--                 OVERLAP cell, the cell's full MM_OPP to every pair (a cell with 3 holders is in 3 pairs, so pairs are not additive).
--  TD_GAP_PERSON  SCENARIO, EST_SOURCE, HOLDER, SOURCE, ROLE, ASSIGNED_STATES, OPP_ASSIGNED (cells attributed to them: they are among the
--                 assigned of the cell), OPP_COVERED, OPP_OVERLAP, OPP_GAP, OPP_HELD_BY_ANOTHER (of those, by class), OPP_HELD_ELSEWHERE (cells
--                 on a ZIP where they have an in-role piece and not assigned to them, whatever the cell's channel: someone else's or OPEN), N_ZIPS_ASSIGNED.  A DOUBLE ASSIGNED cell counts in each one's
--                 OPP_ASSIGNED only.  One row per kept person (role NATIONAL, WH, WIFI) x estimate.
--Result: SECTION, SCENARIO, EST_SOURCE, CHANNEL, ITEM, N_ZIPS, MM_OPP, PCT, MUST_BE_ZERO.
--  CLASS   CHANNEL, ITEM the class, N_ZIPS distinct ZIPs, PCT of the estimate's main map (TD_MAP_CELL)
--  STATE   CHANNEL, ITEM the state then the class, as CLASS
--  TIE     N_ZIPS 1 and MUST_BE_ZERO 1: the classes' cells differ from TD_MAP_CELL in rows or by more than 0.5 (MM_OPP the difference), the
--          kept holders with no td_holder_key row (N_ZIPS the count), the cells with no class (N_ZIPS the count)
--A wholesaler is matched by name in upper case with single spaces, as 04.  The key is by SOURCE and the UUID of that name, as 06.

SET scenario    = '';
SET cell_tbl   = 'ssdb_integration.lr_strategy.td_map_cell';
SET piece_tbl  = 'ssdb_integration.lr_strategy.td_map_piece';
SET assign_tbl = 'ssdb_integration.lr_strategy.td_assignments';
SET holder_tbl = 'ssdb_integration.lr_strategy.td_holder_key';

--1 the kept people of the three roles, with their key and their assigned states
CREATE OR REPLACE TEMPORARY TABLE ssdb_integration.lr_strategy.tmp_g_person AS
SELECT r.source, r.nm, r.source || '|' || r.nm AS pid, r.role, r.assigned_states, 'R' || k.holder_n AS k, k.holder_n AS n
FROM (SELECT source, nm, MAX(kept) AS kept, MAX(role) AS role, MAX(assigned_states) AS assigned_states
      FROM (SELECT source, NULLIF(UPPER(TRIM(REGEXP_REPLACE(TRIM(wholesaler), '\\s+', ' '))), '') AS nm,
                   CASE WHEN COALESCE(UPPER(TRIM(CAST(kept AS VARCHAR))), '') IN ('Y', 'YES', 'TRUE', '1') THEN 'Y' ELSE '' END AS kept,
                   COALESCE(UPPER(TRIM(role)), '') AS role,
                   COALESCE(UPPER(TRIM(REGEXP_REPLACE(REPLACE(assigned_states, ',', ' '), '\\s+', ' '))), '') AS assigned_states
            FROM IDENTIFIER($assign_tbl))
      WHERE nm IS NOT NULL AND source IS NOT NULL
      GROUP BY source, nm) r
LEFT JOIN IDENTIFIER($holder_tbl) k
       ON k.source = r.source AND k.holder_id = UUID_STRING('6ba7b810-9dad-11d1-80b4-00c04fd430c8', r.nm)
WHERE r.kept = 'Y' AND r.role IN ('NATIONAL', 'WH', 'WIFI');

--2 person x assigned state, and per state x role who is assigned
CREATE OR REPLACE TEMPORARY TABLE ssdb_integration.lr_strategy.tmp_g_ps AS
SELECT p.pid, p.k, p.n, p.role, s.state
FROM ssdb_integration.lr_strategy.tmp_g_person p
JOIN (SELECT DISTINCT state FROM IDENTIFIER($cell_tbl) WHERE state IS NOT NULL) s
  ON (' ' || p.assigned_states || ' ') LIKE '% ' || s.state || ' %';

CREATE OR REPLACE TEMPORARY TABLE ssdb_integration.lr_strategy.tmp_g_sr AS
SELECT state, role, COUNT(*) AS n_asg, LISTAGG(k, ' ') WITHIN GROUP (ORDER BY n) AS keys, MIN(pid) AS pid1
FROM ssdb_integration.lr_strategy.tmp_g_ps GROUP BY state, role;

--3 who holds what: a kept person with an in-role piece on the ZIP
CREATE OR REPLACE TEMPORARY TABLE ssdb_integration.lr_strategy.tmp_g_hold AS
SELECT DISTINCT p.pid, p.k, p.n, p.role, m.zip_code
FROM IDENTIFIER($piece_tbl) m
JOIN ssdb_integration.lr_strategy.tmp_g_person p
  ON p.source = m.source AND p.nm = NULLIF(UPPER(TRIM(REGEXP_REPLACE(TRIM(m.wholesaler), '\\s+', ' '))), '')
WHERE m.piece_in_role = 1;

--3b each ZIP's territory pieces today, anyone's (kept or not, in role or not): has a WH piece, has a WH or FI piece
CREATE OR REPLACE TEMPORARY TABLE ssdb_integration.lr_strategy.tmp_g_today AS
SELECT zip_code, MAX(CASE WHEN UPPER(TRIM(terr_channel)) = 'WH' THEN 1 ELSE 0 END) AS has_wh,
       MAX(CASE WHEN UPPER(TRIM(terr_channel)) IN ('WH', 'FI') THEN 1 ELSE 0 END) AS has_any
FROM IDENTIFIER($piece_tbl) GROUP BY zip_code;

--4 the cells, the channel of the priority chain and the role that channel asks for
CREATE OR REPLACE TEMPORARY TABLE ssdb_integration.lr_strategy.tmp_g_c1 AS
SELECT c.*, CASE c.ch WHEN 'NATIONAL' THEN 'NATIONAL' WHEN 'WH' THEN 'WH' WHEN 'REGIONAL' THEN 'WIFI' END AS role_ch,
       COALESCE(a.n_asg, 0) AS n_asg, a.keys AS asg_keys, a.pid1 AS asg_pid
FROM (SELECT ROW_NUMBER() OVER (ORDER BY c.est_source, c.zip_code, c.dist_ch, c.new_dist, c.channel, c.new_terr_channel) AS cid,
             c.est_source, c.zip_code, c.state, c.new_dist, c.mm_opp,
             CASE WHEN c.new_dist IN ('NATIONAL (CHASE)', 'WELLS FI', 'WELLS WH') AND COALESCE(sn.n_asg, 0) > 0 THEN 'NATIONAL'
                  WHEN c.new_dist IN ('WH', 'WELLS WH') AND COALESCE(sw.n_asg, 0) > 0 THEN 'WH'
                  WHEN COALESCE(sr.n_asg, 0) > 0 THEN 'REGIONAL' ELSE 'OPEN' END AS ch
      FROM IDENTIFIER($cell_tbl) c
      LEFT JOIN ssdb_integration.lr_strategy.tmp_g_sr sn ON sn.state = c.state AND sn.role = 'NATIONAL'
      LEFT JOIN ssdb_integration.lr_strategy.tmp_g_sr sw ON sw.state = c.state AND sw.role = 'WH'
      LEFT JOIN ssdb_integration.lr_strategy.tmp_g_sr sr ON sr.state = c.state AND sr.role = 'WIFI') c
LEFT JOIN ssdb_integration.lr_strategy.tmp_g_sr a
       ON a.state = c.state AND a.role = CASE c.ch WHEN 'NATIONAL' THEN 'NATIONAL' WHEN 'WH' THEN 'WH' WHEN 'REGIONAL' THEN 'WIFI' END;

--5 the cell's holders and assigned people, one row each
CREATE OR REPLACE TEMPORARY TABLE ssdb_integration.lr_strategy.tmp_g_ch AS
SELECT c.cid, h.pid, h.k, h.n
FROM ssdb_integration.lr_strategy.tmp_g_c1 c
JOIN ssdb_integration.lr_strategy.tmp_g_hold h ON h.zip_code = c.zip_code AND (c.ch = 'OPEN' OR h.role = c.role_ch);

CREATE OR REPLACE TEMPORARY TABLE ssdb_integration.lr_strategy.tmp_g_ca AS
SELECT c.cid, s.pid
FROM ssdb_integration.lr_strategy.tmp_g_c1 c
JOIN ssdb_integration.lr_strategy.tmp_g_ps s ON s.state = c.state AND s.role = c.role_ch;

--6 the class, one per cell
CREATE OR REPLACE TEMPORARY TABLE ssdb_integration.lr_strategy.tmp_g_cls AS
SELECT c.cid, TRIM($scenario) AS scenario, c.est_source, c.zip_code, c.state, c.new_dist, c.mm_opp, c.ch AS channel,
       c.asg_keys AS assigned,
       CASE WHEN c.ch = 'OPEN' THEN CASE WHEN COALESCE(h.n_h, 0) > 0 THEN 'OPEN SEAT HELD' ELSE 'OPEN SEAT UNHELD' END
            WHEN COALESCE(h.n_h, 0) = 0 THEN CASE WHEN COALESCE(CASE c.ch WHEN 'WH' THEN t.has_wh ELSE t.has_any END, 0) = 1
                                                  THEN 'GAP (HELD TODAY)' ELSE 'GAP (UNHELD)' END
            WHEN h.n_h >= 2 THEN 'OVERLAP'
            WHEN ca.pid IS NOT NULL THEN 'COVERED'
            ELSE 'HELD BY ANOTHER' END AS class,
       COALESCE(h.n_h, 0) AS n_holders, h.keys AS holders, CASE WHEN h.n_h = 1 THEN h.pid1 END AS holder_pid, c.n_asg
FROM ssdb_integration.lr_strategy.tmp_g_c1 c
LEFT JOIN (SELECT cid, COUNT(*) AS n_h, LISTAGG(k, ' ') WITHIN GROUP (ORDER BY n) AS keys, MIN(pid) AS pid1
           FROM ssdb_integration.lr_strategy.tmp_g_ch GROUP BY cid) h ON h.cid = c.cid
LEFT JOIN ssdb_integration.lr_strategy.tmp_g_ca ca ON ca.cid = c.cid AND ca.pid = h.pid1 AND h.n_h = 1
LEFT JOIN ssdb_integration.lr_strategy.tmp_g_today t ON t.zip_code = c.zip_code;

--7 the tables
CREATE OR REPLACE TABLE ssdb_integration.lr_strategy.td_gap_cell AS
SELECT scenario, est_source, zip_code, state, new_dist, mm_opp, channel, assigned, class, n_holders, holders
FROM ssdb_integration.lr_strategy.tmp_g_cls;

CREATE OR REPLACE TABLE ssdb_integration.lr_strategy.td_gap_pair AS
SELECT TRIM($scenario) AS scenario, c.est_source, c.channel, a.k AS holder_a, b.k AS holder_b, COUNT(DISTINCT c.zip_code) AS n_zips,
       SUM(c.mm_opp) AS mm_opp
FROM ssdb_integration.lr_strategy.tmp_g_cls c
JOIN ssdb_integration.lr_strategy.tmp_g_ch a ON a.cid = c.cid
JOIN ssdb_integration.lr_strategy.tmp_g_ch b ON b.cid = c.cid AND a.n < b.n
WHERE c.class = 'OVERLAP'
GROUP BY c.est_source, c.channel, a.k, b.k;

CREATE OR REPLACE TABLE ssdb_integration.lr_strategy.td_gap_person AS
WITH e AS (SELECT DISTINCT est_source FROM ssdb_integration.lr_strategy.tmp_g_cls),
     st AS (SELECT pid, LISTAGG(state, ' ') WITHIN GROUP (ORDER BY state) AS states FROM ssdb_integration.lr_strategy.tmp_g_ps GROUP BY pid),
     asg AS (SELECT a.pid, c.est_source, SUM(c.mm_opp) AS opp_assigned,
                    SUM(CASE WHEN c.class = 'COVERED' THEN c.mm_opp ELSE 0 END) AS opp_covered,
                    SUM(CASE WHEN c.class = 'OVERLAP' THEN c.mm_opp ELSE 0 END) AS opp_overlap,
                    SUM(CASE WHEN c.class LIKE 'GAP%' THEN c.mm_opp ELSE 0 END) AS opp_gap,
                    SUM(CASE WHEN c.class = 'HELD BY ANOTHER' THEN c.mm_opp ELSE 0 END) AS opp_held_by_another,
                    COUNT(DISTINCT c.zip_code) AS n_zips_assigned
             FROM ssdb_integration.lr_strategy.tmp_g_ca a JOIN ssdb_integration.lr_strategy.tmp_g_cls c ON c.cid = a.cid
             WHERE c.class <> 'COVERED' OR c.holder_pid = a.pid
             GROUP BY a.pid, c.est_source),
     hld AS (SELECT h.pid, c.est_source, SUM(c.mm_opp) AS opp_held_elsewhere
             FROM ssdb_integration.lr_strategy.tmp_g_hold h
             JOIN ssdb_integration.lr_strategy.tmp_g_cls c ON c.zip_code = h.zip_code
             LEFT JOIN ssdb_integration.lr_strategy.tmp_g_ca a ON a.cid = c.cid AND a.pid = h.pid
             WHERE a.pid IS NULL GROUP BY h.pid, c.est_source)
SELECT TRIM($scenario) AS scenario, e.est_source, p.k AS holder, p.source, p.role, st.states AS assigned_states,
       COALESCE(asg.opp_assigned, 0) AS opp_assigned, COALESCE(asg.opp_covered, 0) AS opp_covered,
       COALESCE(asg.opp_overlap, 0) AS opp_overlap, COALESCE(asg.opp_gap, 0) AS opp_gap,
       COALESCE(asg.opp_held_by_another, 0) AS opp_held_by_another, COALESCE(hld.opp_held_elsewhere, 0) AS opp_held_elsewhere,
       COALESCE(asg.n_zips_assigned, 0) AS n_zips_assigned
FROM ssdb_integration.lr_strategy.tmp_g_person p
CROSS JOIN e
LEFT JOIN st ON st.pid = p.pid
LEFT JOIN asg ON asg.pid = p.pid AND asg.est_source = e.est_source
LEFT JOIN hld ON hld.pid = p.pid AND hld.est_source = e.est_source;

--8 the one result
WITH
tot AS (SELECT est_source, SUM(mm_opp) AS opp, COUNT(*) AS n FROM IDENTIFIER($cell_tbl) GROUP BY est_source)
SELECT 'CLASS' AS section, g.scenario, g.est_source, g.channel, g.class AS item, COUNT(DISTINCT g.zip_code) AS n_zips, SUM(g.mm_opp) AS mm_opp,
       100 * SUM(g.mm_opp) / NULLIF(MAX(t.opp), 0) AS pct, 0 AS must_be_zero
FROM ssdb_integration.lr_strategy.td_gap_cell g JOIN tot t ON t.est_source = g.est_source
GROUP BY g.scenario, g.est_source, g.channel, g.class
UNION ALL
SELECT 'STATE', g.scenario, g.est_source, g.channel, COALESCE(g.state, '(NO STATE)') || ' | ' || g.class, COUNT(DISTINCT g.zip_code), SUM(g.mm_opp),
       100 * SUM(g.mm_opp) / NULLIF(MAX(t.opp), 0), 0
FROM ssdb_integration.lr_strategy.td_gap_cell g JOIN tot t ON t.est_source = g.est_source
GROUP BY g.scenario, g.est_source, g.channel, g.state, g.class
UNION ALL
SELECT 'TIE', TRIM($scenario), t.est_source, CAST(NULL AS VARCHAR), 'CLASSES MINUS TD_MAP_CELL, MAIN MAP (N_ZIPS 1 = THEY DIFFER)',
       CASE WHEN ABS(COALESCE(g.opp, 0) - t.opp) > 0.5 OR COALESCE(g.n, 0) <> t.n THEN 1 ELSE 0 END, COALESCE(g.opp, 0) - t.opp,
       CAST(NULL AS DOUBLE), 1
FROM tot t
LEFT JOIN (SELECT est_source, SUM(mm_opp) AS opp, COUNT(*) AS n FROM ssdb_integration.lr_strategy.td_gap_cell WHERE class IS NOT NULL
           GROUP BY est_source) g ON g.est_source = t.est_source
UNION ALL
SELECT 'TIE', TRIM($scenario), est_source, NULL, 'CELLS WITH NO CLASS', COUNT(CASE WHEN class IS NULL THEN 1 END),
       SUM(CASE WHEN class IS NULL THEN mm_opp ELSE 0 END), NULL, 1
FROM ssdb_integration.lr_strategy.td_gap_cell GROUP BY est_source
UNION ALL
SELECT 'TIE', TRIM($scenario), NULL, NULL, 'KEPT HOLDERS WITH NO td_holder_key ROW', COUNT(CASE WHEN n IS NULL THEN 1 END), NULL, NULL, 1
FROM ssdb_integration.lr_strategy.tmp_g_person
ORDER BY section, est_source, channel, item;
