use role rl_ssdb_Integration_Lr_Strategy_Rw;
use database ssdb_Integration;
use schema lr_strategy;

--The profile for the assignment maps: what the union and territories tables hold, before any coverage table is built.
--Read-only, one Run All file, one result.  No wholesaler name, firm name or sales dollar is in the result: names are
--only counted, sales appear as row counts and as a percent of the source's own sales.  Opportunity is in dollars
--(not confidential, AGENTS.md Masking).  Send the one result back as CSV.
--Result columns: SECTION, SOURCE, K1..K4 (what they are is under each section), N, N2, MM_OPP, PCT.
--  01 UNION CHANNELS         K1 DIST_CH, K2 NEW_DIST, K3 CHANNEL.  N cells, MM_OPP their opportunity (once per cell, as
--                            02_model_extract.sql), N2 rows with a sale, PCT of the source's sales.
--  02 TERR CHANNELS          K1 territory channel, K2 the measure: ROWS, ZIPS, HOLDERS, OPEN OR NO NAME ROWS,
--                            ZIPS NOT A ZCTA.  N the count.
--  03 TERR HOLDERS PER ZIP   K1 territory channel, K2 holders on the ZIP (0 = open or no name only).  N ZIPs.
--  04 HOLDER CHANNEL SETS    K1 the channels one holder holds today, in firm 1's names (BD = WH, BK = FI, FP = IFA,
--                            RA = PRI, Q39).  N holders, N2 their ZIP x channel rows.
--  05 WH AND FI AT A ZIP     K1 who holds WH and who holds FI on the ZIP today: is WIFI already one person there.
--                            N ZIPs, MM_OPP the opportunity of the five main-map fine channels on them.
--  06 FINE CHANNEL HOLDER    K1 NEW_DIST, K2 DIST_CH, K3 the channel whose holder keeps the cell where national is
--                            absent (#67 fallback: Wells WH with WH, Wells FI and National (Chase) with FI, every other
--                            cell its own DIST_CH), K4 that channel's holders on the ZIP.  N cells, MM_OPP.
--  07 UNION HOLDER VS TERR   K1 DIST_CH, K2 the union's OLD_TERR_WHOLESALER against the territories table's holders of
--                            ZIP x DIST_CH (a firm 2 territory code read as firm 1's, Q39).  N cells, MM_OPP.
--  08 CROSS-FIRM             K1 channel in firm 1's names, K2 which sources have a holder on the ZIP.  N ZIPs.
--  09 SALES ROWS             K1 the sale's ZIP, K2 the seller, K3 whether the seller holds that ZIP in any channel.
--                            N rows, PCT of the source's sales.
--  10 NAMES                  K1 the count's name.  N distinct normalized names (upper case, single spaces, as the
--                            holder key of 02_model_extract.sql).
--A holder is a normalized name that is not blank and not OPEN.  ZIP_CODE is LPAD(LEFT(TRIM(..), 5), 5, '0').

SET union_tbl = 'ssdb_integration.lr_strategy.sales_opp_2026_11_9';
SET terr_tbl  = 'ssdb_integration.lr_strategy.territories_tableau';
SET zcta_tbl  = 'ssdb_integration.lr_strategy.census_zip_codes_zcta';

WITH
cm AS (SELECT terr_ch, canon FROM (VALUES ('WH', 'WH'), ('BD', 'WH'), ('FI', 'FI'), ('BK', 'FI'), ('IFA', 'IFA'), ('FP', 'IFA'),
                                          ('PRI', 'PRI'), ('RA', 'PRI')) AS v (terr_ch, canon)),
z AS (SELECT DISTINCT CAST(geo_id AS VARCHAR) AS zip_code FROM IDENTIFIER($zcta_tbl)),
u0 AS (SELECT source, fiscal_yr, LPAD(LEFT(TRIM(zip_code), 5), 5, '0') AS zip_code, cbd_id, firm, parent, firm_key,
              firm_crd, product_v2, dist_ch, new_dist, file_new_dist, channel, new_terr_channel, mm_opp,
              actual_sales_amount AS amt, COALESCE(UPPER(TRIM(dist_ch)), '') AS dc, COALESCE(UPPER(TRIM(new_dist)), '') AS nd,
              NULLIF(NULLIF(UPPER(TRIM(REGEXP_REPLACE(TRIM(old_terr_wholesaler), '\\s+', ' '))), ''), 'OPEN') AS old_nm,
              NULLIF(NULLIF(UPPER(TRIM(REGEXP_REPLACE(TRIM(sales_wholesaler), '\\s+', ' '))), ''), 'OPEN') AS sell_nm
       FROM IDENTIFIER($union_tbl)),
u AS (SELECT u0.*, COALESCE(cm.canon, u0.dc) AS dcc,
             CASE WHEN u0.nd = 'WELLS WH' THEN 'WH' WHEN u0.nd IN ('WELLS FI', 'NATIONAL (CHASE)') THEN 'FI'
                  ELSE COALESCE(cm.canon, u0.dc) END AS fb
      FROM u0 LEFT JOIN cm ON cm.terr_ch = u0.dc),
t0 AS (SELECT source, LPAD(LEFT(TRIM(zip_code), 5), 5, '0') AS zip_code, COALESCE(UPPER(TRIM(channel)), '') AS ch,
              NULLIF(NULLIF(UPPER(TRIM(REGEXP_REPLACE(TRIM(COALESCE(NULLIF(TRIM(clean_name), ''), name)), '\\s+', ' '))), ''), 'OPEN') AS nm
       FROM IDENTIFIER($terr_tbl)),
t AS (SELECT t0.source, t0.zip_code, t0.ch, COALESCE(cm.canon, t0.ch) AS canon, t0.nm FROM t0 LEFT JOIN cm ON cm.terr_ch = t0.ch),
tk AS (SELECT DISTINCT source, zip_code, canon, nm FROM t WHERE nm IS NOT NULL),
th AS (SELECT source, zip_code, canon, COUNT(DISTINCT nm) AS n_h FROM t GROUP BY source, zip_code, canon),
hs AS (SELECT DISTINCT source, nm FROM tk),
cell AS (SELECT u.source, u.zip_code, u.dc, u.dcc, u.nd, u.channel, u.fb, MAX(CASE WHEN u.mm_opp > 0 THEN u.mm_opp END) AS opp,
                COUNT(DISTINCT CASE WHEN u.mm_opp > 0 THEN u.old_nm END) AS n_u,
                COUNT(DISTINCT CASE WHEN u.mm_opp > 0 AND tk.nm IS NOT NULL THEN u.old_nm END) AS n_m
         FROM u LEFT JOIN tk ON tk.source = u.source AND tk.zip_code = u.zip_code AND tk.canon = u.dcc AND tk.nm = u.old_nm
         GROUP BY u.source, u.fiscal_yr, u.zip_code, u.cbd_id, u.firm, u.parent, u.firm_key, u.firm_crd, u.product_v2,
                  u.dist_ch, u.new_dist, u.file_new_dist, u.channel, u.new_terr_channel, u.dc, u.dcc, u.nd, u.fb
         HAVING MAX(CASE WHEN u.mm_opp > 0 THEN u.mm_opp END) IS NOT NULL),
sale AS (SELECT u.source, u.dc, u.nd, u.channel, u.zip_code, u.sell_nm, u.amt FROM u WHERE u.amt <> 0),
c1 AS (SELECT source, dc, nd, channel, COUNT(*) AS n, SUM(opp) AS opp FROM cell GROUP BY source, dc, nd, channel),
s1 AS (SELECT source, dc, nd, channel, COUNT(*) AS n, SUM(amt) AS amt FROM sale GROUP BY source, dc, nd, channel),
hc AS (SELECT source, nm, COUNT(*) AS n_rows,
              TRIM(MAX(CASE WHEN canon = 'WH' THEN 'WH ' ELSE '' END) || MAX(CASE WHEN canon = 'FI' THEN 'FI ' ELSE '' END)
                   || MAX(CASE WHEN canon = 'IFA' THEN 'IFA ' ELSE '' END) || MAX(CASE WHEN canon = 'PRI' THEN 'PRI ' ELSE '' END)
                   || MAX(CASE WHEN canon NOT IN ('WH', 'FI', 'IFA', 'PRI') THEN 'OTHER' ELSE '' END)) AS chans
       FROM tk GROUP BY source, nm),
wf AS (SELECT source, zip_code, COUNT(DISTINCT CASE WHEN canon = 'WH' THEN nm END) AS n_wh,
              COUNT(DISTINCT CASE WHEN canon = 'FI' THEN nm END) AS n_fi
       FROM tk WHERE canon IN ('WH', 'FI') GROUP BY source, zip_code),
wc AS (SELECT a.source, a.zip_code, COUNT(DISTINCT a.nm) AS n_common
       FROM tk a JOIN tk b ON b.source = a.source AND b.zip_code = a.zip_code AND b.nm = a.nm AND b.canon = 'FI'
       WHERE a.canon = 'WH' GROUP BY a.source, a.zip_code),
o5 AS (SELECT source, zip_code, SUM(opp) AS opp FROM cell
       WHERE nd IN ('WH', 'FI', 'WELLS WH', 'WELLS FI', 'NATIONAL (CHASE)') GROUP BY source, zip_code),
w5 AS (SELECT k.source, k.zip_code, o5.opp,
              CASE WHEN COALESCE(wf.n_wh, 0) = 0 AND COALESCE(wf.n_fi, 0) = 0 THEN 'NEITHER HELD (OPPORTUNITY ONLY)'
                   WHEN COALESCE(wf.n_fi, 0) = 0 THEN 'WH HELD, FI NOT'
                   WHEN COALESCE(wf.n_wh, 0) = 0 THEN 'FI HELD, WH NOT'
                   WHEN COALESCE(wc.n_common, 0) = 0 THEN 'BOTH HELD, DIFFERENT HOLDERS'
                   WHEN wc.n_common = wf.n_wh AND wc.n_common = wf.n_fi THEN 'BOTH HELD, THE SAME HOLDER(S)'
                   ELSE 'BOTH HELD, SOME HOLDERS SHARED' END AS cls
       FROM (SELECT source, zip_code FROM wf UNION SELECT source, zip_code FROM o5) k
       LEFT JOIN wf ON wf.source = k.source AND wf.zip_code = k.zip_code
       LEFT JOIN wc ON wc.source = k.source AND wc.zip_code = k.zip_code
       LEFT JOIN o5 ON o5.source = k.source AND o5.zip_code = k.zip_code),
xf AS (SELECT canon, zip_code, COUNT(DISTINCT source) AS n_src, MIN(source) AS src FROM tk GROUP BY canon, zip_code),
s9 AS (SELECT s.source, s.amt,
              CASE WHEN NOT COALESCE(REGEXP_LIKE(s.zip_code, '^[0-9]{5}$'), FALSE) THEN 'ZIP NOT 5 DIGITS'
                   WHEN z.zip_code IS NULL THEN 'ZIP NOT A ZCTA' ELSE 'ZIP IS A ZCTA' END AS zc,
              CASE WHEN s.sell_nm IS NULL THEN 'NO SELLER (BLANK OR OPEN)' WHEN hs.nm IS NULL THEN 'SELLER HOLDS NO TERRITORY'
                   ELSE 'SELLER HOLDS A TERRITORY' END AS sc,
              CASE WHEN hs.nm IS NULL THEN '-' WHEN hz.nm IS NULL THEN 'SALE OUTSIDE THE SELLER''S ZIPS'
                   ELSE 'SALE IN A ZIP THE SELLER HOLDS' END AS tc
       FROM sale s LEFT JOIN z ON z.zip_code = s.zip_code
       LEFT JOIN hs ON hs.source = s.source AND hs.nm = s.sell_nm
       LEFT JOIN (SELECT DISTINCT source, zip_code, nm FROM tk) hz
              ON hz.source = s.source AND hz.zip_code = s.zip_code AND hz.nm = s.sell_nm),
un AS (SELECT DISTINCT source, 'OLD HOLDER' AS kind, old_nm AS nm FROM u WHERE old_nm IS NOT NULL AND mm_opp > 0
       UNION SELECT DISTINCT source, 'SELLER', sell_nm FROM sale WHERE sell_nm IS NOT NULL)
--01
SELECT '01 UNION CHANNELS' AS section, COALESCE(c1.source, s1.source) AS source, COALESCE(c1.dc, s1.dc) AS k1,
       COALESCE(c1.nd, s1.nd) AS k2, CAST(COALESCE(c1.channel, s1.channel) AS VARCHAR) AS k3, CAST(NULL AS VARCHAR) AS k4,
       COALESCE(c1.n, 0) AS n, COALESCE(s1.n, 0) AS n2, CAST(c1.opp AS DOUBLE) AS mm_opp,
       CAST(100 * s1.amt / NULLIF(SUM(s1.amt) OVER (PARTITION BY COALESCE(c1.source, s1.source)), 0) AS DOUBLE) AS pct
FROM c1 FULL OUTER JOIN s1 ON s1.source = c1.source AND s1.dc = c1.dc AND s1.nd = c1.nd
                          AND COALESCE(s1.channel, '') = COALESCE(c1.channel, '')
UNION ALL
--02
SELECT '02 TERR CHANNELS', source, ch, 'ROWS', NULL, NULL, COUNT(*), NULL, NULL, NULL FROM t GROUP BY source, ch
UNION ALL
SELECT '02 TERR CHANNELS', source, ch, 'ZIPS', NULL, NULL, COUNT(DISTINCT zip_code), NULL, NULL, NULL FROM t GROUP BY source, ch
UNION ALL
SELECT '02 TERR CHANNELS', source, ch, 'HOLDERS', NULL, NULL, COUNT(DISTINCT nm), NULL, NULL, NULL FROM t GROUP BY source, ch
UNION ALL
SELECT '02 TERR CHANNELS', source, ch, 'OPEN OR NO NAME ROWS', NULL, NULL, COUNT(CASE WHEN nm IS NULL THEN 1 END), NULL, NULL, NULL
FROM t GROUP BY source, ch
UNION ALL
SELECT '02 TERR CHANNELS', t.source, t.ch, 'ZIPS NOT A ZCTA', NULL, NULL, COUNT(DISTINCT CASE WHEN z.zip_code IS NULL THEN t.zip_code END),
       NULL, NULL, NULL
FROM t LEFT JOIN z ON z.zip_code = t.zip_code GROUP BY t.source, t.ch
UNION ALL
--03
SELECT '03 TERR HOLDERS PER ZIP', source, ch, CASE WHEN n_h >= 3 THEN '3+' ELSE CAST(n_h AS VARCHAR) END, NULL, NULL, COUNT(*),
       NULL, NULL, NULL
FROM (SELECT source, ch, zip_code, COUNT(DISTINCT nm) AS n_h FROM t GROUP BY source, ch, zip_code)
GROUP BY source, ch, CASE WHEN n_h >= 3 THEN '3+' ELSE CAST(n_h AS VARCHAR) END
UNION ALL
--04
SELECT '04 HOLDER CHANNEL SETS', source, chans, NULL, NULL, NULL, COUNT(*), SUM(n_rows), NULL, NULL FROM hc GROUP BY source, chans
UNION ALL
--05
SELECT '05 WH AND FI AT A ZIP', source, cls, NULL, NULL, NULL, COUNT(*), NULL, SUM(opp), NULL FROM w5 GROUP BY source, cls
UNION ALL
--06
SELECT '06 FINE CHANNEL HOLDER', c.source, c.nd, c.dc, c.fb,
       CASE WHEN th.n_h IS NULL THEN 'NO TERRITORY ROW' WHEN th.n_h = 0 THEN 'OPEN OR NO NAME ONLY' WHEN th.n_h = 1 THEN '1 HOLDER'
            ELSE '2+ HOLDERS' END, COUNT(*), NULL, SUM(c.opp), NULL
FROM cell c LEFT JOIN th ON th.source = c.source AND th.zip_code = c.zip_code AND th.canon = c.fb
GROUP BY c.source, c.nd, c.dc, c.fb,
         CASE WHEN th.n_h IS NULL THEN 'NO TERRITORY ROW' WHEN th.n_h = 0 THEN 'OPEN OR NO NAME ONLY' WHEN th.n_h = 1 THEN '1 HOLDER'
              ELSE '2+ HOLDERS' END
UNION ALL
--07
SELECT '07 UNION HOLDER VS TERR', source, dc, cls, NULL, NULL, COUNT(*), NULL, SUM(opp), NULL
FROM (SELECT c.source, c.dc, c.opp,
             CASE WHEN c.n_u = 0 AND COALESCE(th.n_h, 0) = 0 THEN 'NO HOLDER IN EITHER'
                  WHEN c.n_u = 0 THEN 'TERRITORIES ONLY'
                  WHEN COALESCE(th.n_h, 0) = 0 THEN 'UNION ONLY'
                  WHEN c.n_m = c.n_u AND c.n_u = th.n_h THEN 'THE SAME HOLDER(S)'
                  WHEN c.n_m = c.n_u THEN 'UNION HAS FEWER, ALL IN TERRITORIES'
                  ELSE 'A UNION HOLDER NOT IN TERRITORIES' END AS cls
      FROM cell c LEFT JOIN th ON th.source = c.source AND th.zip_code = c.zip_code AND th.canon = c.dcc)
GROUP BY source, dc, cls
UNION ALL
--08
SELECT '08 CROSS-FIRM', NULL, canon, CASE WHEN n_src = 1 THEN src || ' ONLY' ELSE CAST(n_src AS VARCHAR) || ' SOURCES' END, NULL, NULL,
       COUNT(*), NULL, NULL, NULL
FROM xf GROUP BY canon, CASE WHEN n_src = 1 THEN src || ' ONLY' ELSE CAST(n_src AS VARCHAR) || ' SOURCES' END
UNION ALL
--09
SELECT '09 SALES ROWS', source, zc, sc, tc, NULL, COUNT(*), NULL, NULL,
       100 * SUM(amt) / NULLIF(SUM(SUM(amt)) OVER (PARTITION BY source), 0)
FROM s9 GROUP BY source, zc, sc, tc
UNION ALL
--10
SELECT '10 NAMES', source, 'TERR HOLDERS', NULL, NULL, NULL, COUNT(*), NULL, NULL, NULL FROM hs GROUP BY source
UNION ALL
SELECT '10 NAMES', source, 'TERR HOLDERS WITH A COMMA IN THE NAME', NULL, NULL, NULL, COUNT(CASE WHEN nm LIKE '%,%' THEN 1 END),
       NULL, NULL, NULL
FROM hs GROUP BY source
UNION ALL
SELECT '10 NAMES', a.source, 'TERR HOLDERS ALSO A HOLDER IN ANOTHER SOURCE', NULL, NULL, NULL,
       COUNT(DISTINCT CASE WHEN b.nm IS NOT NULL THEN a.nm END), NULL, NULL, NULL
FROM hs a LEFT JOIN hs b ON b.nm = a.nm AND b.source <> a.source GROUP BY a.source
UNION ALL
SELECT '10 NAMES', un.source, 'UNION ' || un.kind || 'S', NULL, NULL, NULL, COUNT(*), NULL, NULL, NULL
FROM un GROUP BY un.source, un.kind
UNION ALL
SELECT '10 NAMES', un.source, 'UNION ' || un.kind || 'S NOT A TERR HOLDER', NULL, NULL, NULL,
       COUNT(CASE WHEN hs.nm IS NULL THEN 1 END), NULL, NULL, NULL
FROM un LEFT JOIN hs ON hs.source = un.source AND hs.nm = un.nm GROUP BY un.source, un.kind
UNION ALL
SELECT '10 NAMES', un.source, 'UNION ' || un.kind || 'S WITH A COMMA IN THE NAME', NULL, NULL, NULL,
       COUNT(CASE WHEN un.nm LIKE '%,%' THEN 1 END), NULL, NULL, NULL
FROM un GROUP BY un.source, un.kind
ORDER BY section, source, k1, k2, k3, k4;
