use role rl_ssdb_Integration_Lr_Strategy_Rw;
use database ssdb_Integration;
use schema lr_strategy;

--Seat fit per roster scenario (issue 151).  One Run All file, run after 07_overlap_gap.sql in the same session for the same scenario.  Set
--SET scenario to the scenario you ran 03 and 07 with (the scenario run replaces that line as in 03), nothing else.  For every open seat it
--lists who could take it, the people whose assigned states border the seat (NEIGHBOUR) and the people with a territory piece in it (HOLDER),
--ranked by the bargaining utility.  Everything is by key R<n> of td_holder_key, no name leaves.  It builds TD_SEAT_FIT, which uses sales and stays
--in Snowflake, and ends on one result of masked ranks and checks.
--A seat is a state with an OPEN cell of TD_GAP_CELL (07) for an estimate EST_SOURCE, SEAT_MM_OPP the sum of its OPEN cells' MM_OPP.  Sales do not depend
--on the estimate: S(k,z) is the sales of person k in ZIP z, T(z) all sales in z, both firms' sales added (rows as 04 reads the main map, union CHANNEL
--NATIONAL, WH or FI, amount not 0).  M(z) is the MM_OPP of the seat's OPEN cells in z.  With theta 0.40 and lambda 0.30, c1 = 1 - lambda = 0.70 and
--c2 = theta * (1 - lambda) = 0.28 (owner's bargaining utility, DATASET_LOG)
--  U(k, seat)  sum over the seat's OPEN ZIPs z of  c1 S(k,z) + c2 (T(z) - S(k,z)) + lambda M(z)
--  g(k)        the value of k's current book, kept people of role NATIONAL, WH or WIFI.  Each non-OPEN cell whose ASSIGNED has k's key gives k a share of
--              it: 1 when ASSIGNED has one key, a COVERED cell in full to its sole holder (1, the other assignees 0, as gap_load), else 1 / (keys in ASSIGNED).  w(k,z) is the largest
--              share over k's cells in z, g = sum over z of w(k,z) (c1 S(k,z) + c2 (T(z) - S(k,z))) + lambda sum over cells of share MM_OPP
--  DNASH       LN(1 + U / g) when g > 0, else NULL (a NEIGHBOUR with no book value ranks after all with a value, HOLDER rows leave it NULL)
--Candidates of a seat.  NEIGHBOUR: a kept person with role NATIONAL, WH or WIFI who has an assigned state next to the seat in td_state_adj (both
--directions, the Python side makes it), BORDERS 1, ranked by DNASH descending, NULL last, then key number.  HOLDER: anyone, kept or not, whatever the
--role, with a TD_MAP_PIECE row whose STATE is the seat, BORDERS 1 when also a neighbour, ranked by U descending then key number.  A person can be both.
--A candidate with no td_holder_key row cannot be keyed or have sales, it is left out of the table and counted by a TIE row.
--Table (replaced on every run), SCENARIO is SET scenario trimmed:
--  TD_SEAT_FIT  SCENARIO, EST_SOURCE, SEAT, SEAT_MM_OPP, KIND, HOLDER (key), SOURCE, KEPT (Y or N), ROLE, BORDERS, U, G, DNASH, RANK.  RANK counts from 1
--               within scenario, estimate, seat and kind.
--Result: SECTION, SCENARIO, EST_SOURCE, SEAT, KIND, HOLDER, RANK, BORDERS, SEAT_MM_OPP, N, MUST_BE_ZERO.  No U, G, DNASH, sales, name or firm id.
--  SEAT   one per TD_SEAT_FIT row
--  SEATS  per estimate, N the number of seats
--  TIE    MUST_BE_ZERO 1, N must be 0, KIND says which: seats with no candidate of either kind per estimate (SEAT NULL), and candidates with no
--         td_holder_key row (EST_SOURCE NULL, the people counted once)
--A wholesaler is matched by name in upper case with single spaces, as 04.  The key is by SOURCE and the UUID of that name, as 06 and 07.

SET scenario    = '';
SET gap_tbl    = 'ssdb_integration.lr_strategy.td_gap_cell';
SET piece_tbl  = 'ssdb_integration.lr_strategy.td_map_piece';
SET assign_tbl = 'ssdb_integration.lr_strategy.td_assignments';
SET holder_tbl = 'ssdb_integration.lr_strategy.td_holder_key';
SET union_tbl  = 'ssdb_integration.lr_strategy.sales_opp_2026_11_9';
SET adj_tbl    = 'ssdb_integration.lr_strategy.td_state_adj';
SET c1  = 0.70;
SET c2  = 0.28;
SET lam = 0.30;

--1 this scenario's cells, and the people: kept, role NATIONAL, WH or WIFI, with their key, assigned states, and the states of them that have a neighbour
CREATE OR REPLACE TEMPORARY TABLE ssdb_integration.lr_strategy.tmp_f_gap AS
SELECT * FROM IDENTIFIER($gap_tbl) WHERE scenario = TRIM($scenario);

CREATE OR REPLACE TEMPORARY TABLE ssdb_integration.lr_strategy.tmp_f_person AS
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

CREATE OR REPLACE TEMPORARY TABLE ssdb_integration.lr_strategy.tmp_f_ps AS
SELECT p.pid, s.state
FROM ssdb_integration.lr_strategy.tmp_f_person p
JOIN (SELECT DISTINCT state_a AS state FROM IDENTIFIER($adj_tbl)) s
  ON (' ' || p.assigned_states || ' ') LIKE '% ' || s.state || ' %';

--2 sales per key and ZIP, and all sales per ZIP
CREATE OR REPLACE TEMPORARY TABLE ssdb_integration.lr_strategy.tmp_f_sale AS
SELECT source, LPAD(LEFT(TRIM(zip_code), 5), 5, '0') AS zip_code, actual_sales_amount AS amt,
       NULLIF(NULLIF(UPPER(TRIM(REGEXP_REPLACE(TRIM(sales_wholesaler), '\\s+', ' '))), ''), 'OPEN') AS nm
FROM IDENTIFIER($union_tbl)
WHERE UPPER(TRIM(channel)) IN ('NATIONAL', 'WH', 'FI') AND actual_sales_amount <> 0;

CREATE OR REPLACE TEMPORARY TABLE ssdb_integration.lr_strategy.tmp_f_s AS
SELECT k.holder_n AS n, s.zip_code, SUM(s.amt) AS s
FROM ssdb_integration.lr_strategy.tmp_f_sale s
JOIN IDENTIFIER($holder_tbl) k
  ON k.source = s.source AND k.holder_id = UUID_STRING('6ba7b810-9dad-11d1-80b4-00c04fd430c8', s.nm)
GROUP BY k.holder_n, s.zip_code;

CREATE OR REPLACE TEMPORARY TABLE ssdb_integration.lr_strategy.tmp_f_t AS
SELECT zip_code, SUM(amt) AS t FROM ssdb_integration.lr_strategy.tmp_f_sale GROUP BY zip_code;

--3 the seats: a state with an OPEN cell, per estimate, and its OPEN ZIPs with M(z)
CREATE OR REPLACE TEMPORARY TABLE ssdb_integration.lr_strategy.tmp_f_seatzip AS
SELECT est_source, state AS seat, zip_code, SUM(mm_opp) AS m
FROM ssdb_integration.lr_strategy.tmp_f_gap WHERE channel = 'OPEN' AND state IS NOT NULL
GROUP BY est_source, state, zip_code;

CREATE OR REPLACE TEMPORARY TABLE ssdb_integration.lr_strategy.tmp_f_seat AS
SELECT est_source, seat, SUM(m) AS seat_mm_opp FROM ssdb_integration.lr_strategy.tmp_f_seatzip GROUP BY est_source, seat;

--4 the candidates: neighbours (an assigned state next to the seat), holders (a piece in the seat, anyone), BORDERS 1 for a holder who is also a neighbour
CREATE OR REPLACE TEMPORARY TABLE ssdb_integration.lr_strategy.tmp_f_nb AS
SELECT DISTINCT s.est_source, s.seat, ps.pid
FROM ssdb_integration.lr_strategy.tmp_f_seat s
JOIN IDENTIFIER($adj_tbl) a ON a.state_b = s.seat
JOIN ssdb_integration.lr_strategy.tmp_f_ps ps ON ps.state = a.state_a;

CREATE OR REPLACE TEMPORARY TABLE ssdb_integration.lr_strategy.tmp_f_hp AS
SELECT source, nm, state, MAX(kept) AS kept, MAX(role) AS role
FROM (SELECT source, NULLIF(UPPER(TRIM(REGEXP_REPLACE(TRIM(wholesaler), '\\s+', ' '))), '') AS nm, UPPER(TRIM(state)) AS state,
             CASE WHEN COALESCE(UPPER(TRIM(CAST(kept AS VARCHAR))), '') IN ('Y', 'YES', 'TRUE', '1') THEN 'Y' ELSE '' END AS kept,
             COALESCE(UPPER(TRIM(role)), '') AS role
      FROM IDENTIFIER($piece_tbl))
WHERE nm IS NOT NULL AND source IS NOT NULL AND state IS NOT NULL
GROUP BY source, nm, state;

CREATE OR REPLACE TEMPORARY TABLE ssdb_integration.lr_strategy.tmp_f_cand AS
SELECT nb.est_source, nb.seat, 'NEIGHBOUR' AS kind, p.source, p.pid, p.k, p.n, 'Y' AS kept, p.role, 1 AS borders
FROM ssdb_integration.lr_strategy.tmp_f_nb nb
JOIN ssdb_integration.lr_strategy.tmp_f_person p ON p.pid = nb.pid
UNION ALL
SELECT s.est_source, s.seat, 'HOLDER', h.source, h.source || '|' || h.nm, 'R' || k.holder_n, k.holder_n,
       CASE WHEN h.kept = 'Y' THEN 'Y' ELSE 'N' END, NULLIF(h.role, ''), CASE WHEN nb.pid IS NULL THEN 0 ELSE 1 END
FROM ssdb_integration.lr_strategy.tmp_f_seat s
JOIN ssdb_integration.lr_strategy.tmp_f_hp h ON h.state = s.seat
LEFT JOIN IDENTIFIER($holder_tbl) k
       ON k.source = h.source AND k.holder_id = UUID_STRING('6ba7b810-9dad-11d1-80b4-00c04fd430c8', h.nm)
LEFT JOIN ssdb_integration.lr_strategy.tmp_f_nb nb
       ON nb.est_source = s.est_source AND nb.seat = s.seat AND nb.pid = h.source || '|' || h.nm;

--5 U per estimate, seat and key
CREATE OR REPLACE TEMPORARY TABLE ssdb_integration.lr_strategy.tmp_f_u AS
SELECT c.est_source, c.seat, c.n,
       SUM($c1 * COALESCE(s.s, 0) + $c2 * (COALESCE(t.t, 0) - COALESCE(s.s, 0)) + $lam * z.m) AS u
FROM (SELECT DISTINCT est_source, seat, n FROM ssdb_integration.lr_strategy.tmp_f_cand WHERE n IS NOT NULL) c
JOIN ssdb_integration.lr_strategy.tmp_f_seatzip z ON z.est_source = c.est_source AND z.seat = c.seat
LEFT JOIN ssdb_integration.lr_strategy.tmp_f_s s ON s.n = c.n AND s.zip_code = z.zip_code
LEFT JOIN ssdb_integration.lr_strategy.tmp_f_t t ON t.zip_code = z.zip_code
GROUP BY c.est_source, c.seat, c.n;

--6 the share of each non-OPEN cell that is a person's, then g per estimate and person
CREATE OR REPLACE TEMPORARY TABLE ssdb_integration.lr_strategy.tmp_f_share AS
SELECT g.est_source, g.zip_code, g.mm_opp, p.n,
       CASE WHEN g.nk = 1 THEN 1 WHEN g.class = 'COVERED' THEN CASE WHEN g.holders = p.k THEN 1 ELSE 0 END ELSE 1.0 / g.nk END AS share
FROM (SELECT est_source, zip_code, mm_opp, class, holders, assigned, LENGTH(assigned) - LENGTH(REPLACE(assigned, ' ', '')) + 1 AS nk
      FROM ssdb_integration.lr_strategy.tmp_f_gap WHERE channel <> 'OPEN' AND assigned IS NOT NULL) g
JOIN ssdb_integration.lr_strategy.tmp_f_person p
  ON p.n IS NOT NULL AND (' ' || g.assigned || ' ') LIKE '% ' || p.k || ' %';

CREATE OR REPLACE TEMPORARY TABLE ssdb_integration.lr_strategy.tmp_f_g AS
WITH w AS (SELECT est_source, n, zip_code, MAX(share) AS w FROM ssdb_integration.lr_strategy.tmp_f_share GROUP BY est_source, n, zip_code),
     book AS (SELECT w.est_source, w.n,
                     SUM(w.w * ($c1 * COALESCE(s.s, 0) + $c2 * (COALESCE(t.t, 0) - COALESCE(s.s, 0)))) AS sales_part
              FROM w
              LEFT JOIN ssdb_integration.lr_strategy.tmp_f_s s ON s.n = w.n AND s.zip_code = w.zip_code
              LEFT JOIN ssdb_integration.lr_strategy.tmp_f_t t ON t.zip_code = w.zip_code
              GROUP BY w.est_source, w.n),
     opp AS (SELECT est_source, n, SUM(share * mm_opp) AS opp_part FROM ssdb_integration.lr_strategy.tmp_f_share GROUP BY est_source, n)
SELECT e.est_source, p.n, COALESCE(book.sales_part, 0) + $lam * COALESCE(opp.opp_part, 0) AS g
FROM (SELECT DISTINCT est_source FROM ssdb_integration.lr_strategy.tmp_f_gap) e
CROSS JOIN (SELECT DISTINCT n FROM ssdb_integration.lr_strategy.tmp_f_person WHERE n IS NOT NULL) p
LEFT JOIN book ON book.est_source = e.est_source AND book.n = p.n
LEFT JOIN opp ON opp.est_source = e.est_source AND opp.n = p.n;

--7 the table
CREATE OR REPLACE TABLE ssdb_integration.lr_strategy.td_seat_fit AS
SELECT TRIM($scenario) AS scenario, x.est_source, x.seat, x.seat_mm_opp, x.kind, x.holder, x.source, x.kept, x.role, x.borders, x.u, x.g, x.dnash,
       ROW_NUMBER() OVER (PARTITION BY x.est_source, x.seat, x.kind
                          ORDER BY CASE WHEN x.kind = 'NEIGHBOUR' THEN x.dnash END DESC NULLS LAST,
                                   CASE WHEN x.kind = 'HOLDER' THEN x.u END DESC, x.n) AS rank
FROM (SELECT c.est_source, c.seat, s.seat_mm_opp, c.kind, c.k AS holder, c.n, c.source, c.kept, c.role, c.borders, u.u, g.g,
             CASE WHEN c.kind = 'NEIGHBOUR' AND g.g > 0 AND u.u + g.g > 0 THEN LN(1 + u.u / g.g) END AS dnash
      FROM ssdb_integration.lr_strategy.tmp_f_cand c
      JOIN ssdb_integration.lr_strategy.tmp_f_seat s ON s.est_source = c.est_source AND s.seat = c.seat
      JOIN ssdb_integration.lr_strategy.tmp_f_u u ON u.est_source = c.est_source AND u.seat = c.seat AND u.n = c.n
      LEFT JOIN ssdb_integration.lr_strategy.tmp_f_g g ON g.est_source = c.est_source AND g.n = c.n
      WHERE c.n IS NOT NULL) x;

--8 the one result
WITH
e AS (SELECT DISTINCT est_source FROM ssdb_integration.lr_strategy.tmp_f_gap)
SELECT 'SEAT' AS section, f.scenario, f.est_source, f.seat, f.kind, f.holder, f.rank, f.borders, f.seat_mm_opp, CAST(NULL AS BIGINT) AS n, 0 AS must_be_zero
FROM ssdb_integration.lr_strategy.td_seat_fit f
UNION ALL
SELECT 'SEATS', TRIM($scenario), e.est_source, NULL, NULL, NULL, NULL, NULL, NULL, COUNT(s.seat), 0
FROM e LEFT JOIN ssdb_integration.lr_strategy.tmp_f_seat s ON s.est_source = e.est_source
GROUP BY e.est_source
UNION ALL
SELECT 'TIE', TRIM($scenario), e.est_source, NULL, 'SEATS WITH NO CANDIDATE', NULL, NULL, NULL, NULL,
       COUNT(CASE WHEN s.seat IS NOT NULL AND f.seat IS NULL THEN 1 END), 1
FROM e
LEFT JOIN ssdb_integration.lr_strategy.tmp_f_seat s ON s.est_source = e.est_source
LEFT JOIN (SELECT DISTINCT est_source, seat FROM ssdb_integration.lr_strategy.td_seat_fit) f ON f.est_source = s.est_source AND f.seat = s.seat
GROUP BY e.est_source
UNION ALL
SELECT 'TIE', TRIM($scenario), NULL, NULL, 'CANDIDATES WITH NO td_holder_key ROW', NULL, NULL, NULL, NULL,
       COUNT(DISTINCT CASE WHEN n IS NULL THEN pid END), 1
FROM ssdb_integration.lr_strategy.tmp_f_cand
ORDER BY section, est_source, seat, kind, rank, holder;
