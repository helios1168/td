use secondary roles all;

--UNION_OPP: union_base with firm_2's opportunity file added, in firm_1's layout, so both firms carry sales and
--opportunity on the same rows.  Open in a worksheet and Run All, it ends on the checks.
--  firm_1 (CRBG): its opportunity is on union_base already (the vendor table through your query, mm_query.sql).
--  firm_2 (EQH):  its opportunity file (opp_original) goes through the same steps here (statement 7).
--Edit only the statements marked EDIT.
--   1 EDIT  tmp_label          the labels this file needs
--   2 EDIT  tmp_f2_channel     firm_2's file channel -> firm_2's DIST_CH in union_base
--   3 EDIT  crd_dist_override  your dist_ch for firm_2 CRDs (permanent: created once, then loaded)
--   4 EDIT  tmp_firm_override  companies moved to another channel
--   5 EDIT  tmp_opp_override   companies whose firm_1 opportunity becomes firm_2's
--   6       tmp_f1_crd_dist    firm_1's dist_ch per CRD
--   7       tmp_f2_opp         firm_2's file, one row per file row, in firm_1's terms, and why a row drops
--   8       tmp_f2_key         firm_2's opportunity per key ZIP x DIST_CH x CBD_ID x PRODUCT_V2
--   9       tmp_firm_key       one key per firm across both firms
--  10       UNION_OPP          the table kept
--  11       tmp_opp_xwalk      the opportunity crosswalk: each step, by firm, from -> to, before and after
--  12       report: the opportunity crosswalk
--  13       review: firm_2 CRDs with no dist_ch (fill crd_dist_override)
--  14       review: firm keys joining 2+ CBD_IDs
--  15-16    reports: does opportunity align across the firms
--  17       checks: every MUST_BE_ZERO = 1 row must be 0
--Only UNION_OPP and crd_dist_override are kept, the tmp_ tables last for the session, so run 11-17 in the session of
--the builds (Run All does).
--
--What touches opportunity (the crosswalk, statement 11, follows each step):
--  firm_2  7  product, company (vendor rows, crd_cbd_mm, your query's rules), firm_1 channel and new_dist, firm_2's
--             own channel, drops: no company, NO CHANNEL.  Amounts per row unchanged.
--          8  summed per key, drops: keys summing to 0.
--         10  each key on the holder's sales row, else opp-only rows for the holder of its ZIP x DIST_CH.
--  firm_1     its opportunity comes on union_base (your query), here only the overrides touch it:
--         10  firm override: DIST_CH (and the holder) of the company's rows, amounts unchanged, opportunity override:
--             the listed companies' amounts scaled to firm_2's, removed, or added.

--Statement 1.  EDIT once: the labels as they are in your tables.  A label not found in the data fails a check.
CREATE OR REPLACE TEMPORARY TABLE ssdb_integration.lr_strategy.tmp_label AS
SELECT 'CRBG'            AS F1,             -- union_base.SOURCE of firm_1
       'EQH'             AS F2,             -- union_base.SOURCE of firm_2
       '<label of PR05>' AS F2_VA,          -- firm_2's PRODUCT_V2 for VA in union_base: counted as VARIABLE (Q8)
       'VARIABLE'        AS VARIABLE,       -- the PRODUCT_V2 of variable annuity
       '<label of V02>'  AS RILA_VA_TYPE;   -- opp_original.VA_PRODUCT_TYPE that means RILA

--Statement 2.  EDIT once: firm_2's file channel (opp_original.DIST_CH) -> firm_2's DIST_CH in union_base (Q19).
--DIST_CH NULL drops the file's rows (NO CHANNEL, owner 2026-10-25).  A file channel not listed fails a check.
CREATE OR REPLACE TEMPORARY TABLE ssdb_integration.lr_strategy.tmp_f2_channel AS
SELECT FILE_DIST_CH, DIST_CH FROM (VALUES
  ('<label of O2_01>', '<label of D2_01>'),
  ('<label of O2_02>', '<label of D2_02>'),
  ('<label of O2_03>', '<label of D2_04>'),
  ('<label of O2_04>', '<label of D2_03>'),
  ('NO CHANNEL',       NULL)
) v(FILE_DIST_CH, DIST_CH);

--Statement 3.  Created once, never replaced, load it from a CSV with these headers (Snowsight "Load data") or with
--INSERT.  A firm_2 row whose CRD firm_1 does not settle (statement 6) takes this dist_ch: one row per CRD (BROKER_NAME
--NULL: every broker name of the CRD) or per CRD x broker name (wins over the NULL row).  Statement 13 lists the CRDs.
CREATE TABLE IF NOT EXISTS ssdb_integration.lr_strategy.crd_dist_override (FIRM_CRD VARCHAR, BROKER_NAME VARCHAR, DIST_CH VARCHAR);

--Statement 4.  EDIT: firm overrides (owner, 2026-10-26 and 2026-10-28).  Every row of the company, both firms, sales
--and opportunity, gets NEW_DIST (CHANNEL follows it), firm_1's rows get DIST_CH, firm_2's rows F2_DIST_CH (firm_2's
--own channel label, NULL keeps theirs, and a check fails if firm_2 has rows of the company).  A row whose DIST_CH
--changes takes the territory holder of its ZIP_CODE x new DIST_CH.  One line per CBD_ID.
CREATE OR REPLACE TEMPORARY TABLE ssdb_integration.lr_strategy.tmp_firm_override AS
SELECT CBD_ID, DIST_CH, NEW_DIST, CAST(F2_DIST_CH AS VARCHAR) AS F2_DIST_CH
FROM (VALUES ('46', 'FI', 'FI', NULL)) v(CBD_ID, DIST_CH, NEW_DIST, F2_DIST_CH);

--Statement 5.  EDIT: opportunity overrides (owner, 2026-10-26).  For each company listed, firm_1's MM_OPP becomes
--firm_2's per ZIP_CODE x PRODUCT_V2: scaled where both have it, removed where only firm_1 has it, added as firm_1
--opp-only rows where only firm_2 has it.  E.g. VALUES ('46'), ('123'), ('') lists none.
CREATE OR REPLACE TEMPORARY TABLE ssdb_integration.lr_strategy.tmp_opp_override AS
SELECT CBD_ID FROM (VALUES ('')) v(CBD_ID) WHERE CBD_ID <> '';

--Statement 6.  firm_1's dist_ch per CRD: your query's dist_ch rules on the vendor table (its fiscal years), with the
--opportunity.  firm_2's file has no firm_1 channel, so a firm_2 row takes its CRD's when the CRD has exactly one.
CREATE OR REPLACE TEMPORARY TABLE ssdb_integration.lr_strategy.tmp_f1_crd_dist AS
SELECT TO_CHAR(firm_crd) AS FIRM_CRD,
       CASE WHEN TO_CHAR(cbd_id) IN ('1993', '685') THEN 'PRI'
            WHEN TO_CHAR(cbd_id) = '805' THEN 'AMER'
            WHEN broker_name IN ('Wells Fargo Clearing Services, LLC', 'First Command Brokerage Services, Inc.') THEN 'WH'
            WHEN broker_name = 'Mercer Allied Company, L.P.' THEN 'IFA'
            WHEN broker_name IN ('TD Securities (USA) LLC', 'Woodmen Financial Services, Inc.',
                                 'United Brokerage Services, Inc', 'Frost Brokerage Services, Inc.') THEN 'FI'
            WHEN TO_CHAR(dist_ch) = 'EDWARD JONES' THEN 'EDJ'
            ELSE TO_CHAR(dist_ch) END AS DIST_CH,
       SUM(global_sales) AS OPP
FROM life_prod.lif_murkylake.wc_market_metrics_opportunity
WHERE TO_CHAR(fiscal_yr) IN ('2024', '2025')
GROUP BY 1, 2;

--Statement 7.  firm_2's opportunity file, one row per file row, in firm_1's terms:
--  PRODUCT_V2       your query's product rule (RILA is a VA type in the file, a product line in the vendor table)
--  ORIGINAL_CBD_ID  the company firm_1's vendor rows give the same ZIP x CRD x broker name x product (the one with
--                   the most opportunity), else the same ZIP x CRD x broker name, else crd_cbd_mm, then your query's
--                   company rules (Wells, client firm ID), NULL = no company (dropped later, as firm_1's)
--  CBD_ID           a list 'a|b': the first company firm_2 has a sales row of at that ZIP x product x state, else
--                   the first (your query's rule)
--  DIST_CH          firm_1's dist_ch of the CRD when it has one, else crd_dist_override, DIST_SOURCE says which,
--                   DIST_REVIEW why there is none, a firm override wins
--  NEW_DIST         your query's new_dist rules on CBD_ID and DIST_CH, a firm override wins
--  UNION_DIST_CH    firm_2's own channel in union_base (tmp_f2_channel, a firm override's F2_DIST_CH wins): the key
--  CBD_METHOD       how the company was found,  DROP_REASON  'no company' or 'NO CHANNEL' (else the row goes on)
CREATE OR REPLACE TEMPORARY TABLE ssdb_integration.lr_strategy.tmp_f2_opp AS
WITH
l AS (SELECT * FROM ssdb_integration.lr_strategy.tmp_label),
opp AS (   -- both firms' opportunity rows in one shape with your query's product
  SELECT x.*, CASE WHEN VA = 'IOVA' THEN 'IOVA' WHEN PL = 'VA' THEN 'VARIABLE' WHEN PL = 'IA' THEN 'INDEX'
                   WHEN PL = 'FA' THEN 'FIXED' WHEN PL = 'RILA' THEN 'RILA' END AS PRODUCT_V2
  FROM (SELECT 'firm_1' AS SRC, LPAD(TRIM(TO_CHAR(v.zip_code)), 5, '0') AS ZIP_CODE, TO_CHAR(v.firm_crd) AS FIRM_CRD,
               v.broker_name AS BROKER_NAME, TO_CHAR(v.product_line) AS PL, TO_CHAR(v.va_product_type) AS VA,
               TO_CHAR(v.cbd_id) AS CBD_ID, TO_CHAR(v.client_firm_id) AS CLIENT_FIRM_ID,
               CAST(NULL AS VARCHAR) AS FILE_DIST_CH, CAST(NULL AS VARCHAR) AS FILE_PL, v.global_sales AS OPP
        FROM life_prod.lif_murkylake.wc_market_metrics_opportunity v
        WHERE TO_CHAR(v.fiscal_yr) IN ('2024', '2025')
        UNION ALL
        SELECT 'firm_2', LPAD(TRIM(TO_CHAR(o.zip_code)), 5, '0'), TO_CHAR(o.firm_crd), o.broker_name,
               CASE WHEN TO_CHAR(o.va_product_type) = l.RILA_VA_TYPE THEN 'RILA' ELSE TO_CHAR(o.product_line) END,
               TO_CHAR(o.va_product_type), NULL, NULL, TO_CHAR(o.dist_ch), TO_CHAR(o.product_line), o.opp
        FROM ssdb_integration.lr_strategy.opp_original o CROSS JOIN l) x),
cell AS (  -- firm_1's company per ZIP x CRD x broker name x product: the one with the most opportunity
  SELECT ZIP_CODE, FIRM_CRD, BROKER_NAME, PRODUCT_V2, CBD_ID, CLIENT_FIRM_ID
  FROM (SELECT ZIP_CODE, FIRM_CRD, BROKER_NAME, PRODUCT_V2, CBD_ID, CLIENT_FIRM_ID, SUM(OPP) AS OPP
        FROM opp WHERE SRC = 'firm_1' GROUP BY ZIP_CODE, FIRM_CRD, BROKER_NAME, PRODUCT_V2, CBD_ID, CLIENT_FIRM_ID)
  QUALIFY ROW_NUMBER() OVER (PARTITION BY ZIP_CODE, FIRM_CRD, BROKER_NAME, PRODUCT_V2
                             ORDER BY OPP DESC, CBD_ID, CLIENT_FIRM_ID) = 1),
zcb AS (   -- the same per ZIP x CRD x broker name, any product
  SELECT ZIP_CODE, FIRM_CRD, BROKER_NAME, CBD_ID, CLIENT_FIRM_ID
  FROM (SELECT ZIP_CODE, FIRM_CRD, BROKER_NAME, CBD_ID, CLIENT_FIRM_ID, SUM(OPP) AS OPP
        FROM opp WHERE SRC = 'firm_1' GROUP BY ZIP_CODE, FIRM_CRD, BROKER_NAME, CBD_ID, CLIENT_FIRM_ID)
  QUALIFY ROW_NUMBER() OVER (PARTITION BY ZIP_CODE, FIRM_CRD, BROKER_NAME ORDER BY OPP DESC, CBD_ID, CLIENT_FIRM_ID) = 1),
mm AS (    -- no vendor row at that ZIP: crd_cbd_mm's company with the most opportunity of the CRD x broker name
  SELECT TO_CHAR(firm_crd) AS FIRM_CRD, broker_name AS BROKER_NAME, TO_CHAR(cbd_id) AS CBD_ID
  FROM ssdb_integration.lr_strategy.crd_cbd_mm
  QUALIFY ROW_NUMBER() OVER (PARTITION BY TO_CHAR(firm_crd), broker_name ORDER BY mm_opp DESC, TO_CHAR(cbd_id)) = 1),
zs AS (    -- the vendor's state of a ZIP (firm_2's file has none)
  SELECT LPAD(TRIM(TO_CHAR(zip_code)), 5, '0') AS ZIP_CODE, MAX(TO_CHAR(state)) AS STATE
  FROM life_prod.lif_murkylake.wc_market_metrics_opportunity GROUP BY 1),
f2 AS (    -- firm_2's rows with their company
  SELECT o.ZIP_CODE, zs.STATE, o.FIRM_CRD, o.BROKER_NAME, o.FILE_DIST_CH, o.FILE_PL, o.VA AS FILE_VA, o.PRODUCT_V2, o.OPP,
         CASE WHEN o.BROKER_NAME IN ('Wells Fargo Clearing Services, LLC', 'Wells Fargo Clearing Services, LLC - BANK')
                   THEN 'your query: Wells broker name'
              WHEN o.CBD = '0' AND o.CLIENT IS NOT NULL THEN 'your query: company 0 -> client firm ID'
              WHEN o.CBD = '0' THEN 'your query: company 0 -> none'
              WHEN o.HOW IS NOT NULL THEN o.HOW ELSE 'not found' END AS CBD_METHOD,
         CASE WHEN o.BROKER_NAME = 'Wells Fargo Clearing Services, LLC' THEN '1822'
              WHEN o.BROKER_NAME = 'Wells Fargo Clearing Services, LLC - BANK' THEN '1823'
              WHEN o.CBD = '0' AND o.CLIENT IS NOT NULL THEN o.CLIENT
              WHEN o.CBD = '0' THEN NULL
              ELSE o.CBD END AS ORIGINAL_CBD_ID
  FROM (SELECT o.*,
               CASE WHEN c.ZIP_CODE IS NOT NULL THEN c.CBD_ID WHEN k.ZIP_CODE IS NOT NULL THEN k.CBD_ID ELSE m.CBD_ID END AS CBD,
               CASE WHEN c.ZIP_CODE IS NOT NULL THEN c.CLIENT_FIRM_ID WHEN k.ZIP_CODE IS NOT NULL THEN k.CLIENT_FIRM_ID END AS CLIENT,
               CASE WHEN c.ZIP_CODE IS NOT NULL THEN 'vendor: same ZIP x CRD x broker x product'
                    WHEN k.ZIP_CODE IS NOT NULL THEN 'vendor: same ZIP x CRD x broker'
                    WHEN m.FIRM_CRD IS NOT NULL THEN 'crd_cbd_mm: same CRD x broker' END AS HOW
        FROM opp o
        LEFT JOIN cell c ON c.ZIP_CODE = o.ZIP_CODE AND c.FIRM_CRD = o.FIRM_CRD AND c.BROKER_NAME = o.BROKER_NAME
                        AND c.PRODUCT_V2 = o.PRODUCT_V2
        LEFT JOIN zcb k ON k.ZIP_CODE = o.ZIP_CODE AND k.FIRM_CRD = o.FIRM_CRD AND k.BROKER_NAME = o.BROKER_NAME
        LEFT JOIN mm m ON m.FIRM_CRD = o.FIRM_CRD AND m.BROKER_NAME = o.BROKER_NAME
        WHERE o.SRC = 'firm_2') o
  LEFT JOIN zs ON zs.ZIP_CODE = o.ZIP_CODE),
sk AS (    -- firm_2's sales keys in union_base (its VA as VARIABLE)
  SELECT DISTINCT TO_CHAR(u.fiscal_yr) AS FISCAL_YR, LPAD(TRIM(TO_CHAR(u.zip_code)), 5, '0') AS ZIP_CODE,
         TO_CHAR(u.cbd_id) AS CBD_ID, CASE WHEN u.product_v2 = l.F2_VA THEN l.VARIABLE ELSE u.product_v2 END AS PRODUCT_V2,
         u.state AS STATE
  FROM ssdb_integration.lr_strategy.union_base u CROSS JOIN l
  WHERE u.source = l.F2),
cand AS (  -- each company of ORIGINAL_CBD_ID in list order (one company: itself)
  SELECT o.ZIP_CODE, o.STATE, o.PRODUCT_V2, o.ORIGINAL_CBD_ID, TRIM(f.value::VARCHAR) AS CBD_ID, f.index AS POS
  FROM (SELECT DISTINCT ZIP_CODE, STATE, PRODUCT_V2, ORIGINAL_CBD_ID FROM f2 WHERE ORIGINAL_CBD_ID IS NOT NULL) o,
  LATERAL FLATTEN(INPUT => SPLIT(o.original_cbd_id, '|')) f),
pick AS (  -- the first company firm_2 has a sales row of at that ZIP x product x state, else the first
  SELECT c.ZIP_CODE, c.STATE, c.PRODUCT_V2, c.ORIGINAL_CBD_ID, c.CBD_ID
  FROM cand c
  LEFT JOIN sk ON sk.FISCAL_YR = '2025' AND sk.ZIP_CODE = c.ZIP_CODE AND sk.CBD_ID = c.CBD_ID
              AND sk.PRODUCT_V2 = c.PRODUCT_V2 AND sk.STATE = c.STATE
  QUALIFY ROW_NUMBER() OVER (PARTITION BY c.ZIP_CODE, c.STATE, c.PRODUCT_V2, c.ORIGINAL_CBD_ID
                             ORDER BY CASE WHEN sk.CBD_ID IS NOT NULL THEN 0 ELSE 1 END, c.POS) = 1),
crd AS (   -- firm_1's dist_ch of a CRD (N = how many, a blank counts as one)
  SELECT FIRM_CRD, MAX(DIST_CH) AS DIST_CH, COUNT(DISTINCT COALESCE(DIST_CH, '~')) AS N
  FROM ssdb_integration.lr_strategy.tmp_f1_crd_dist GROUP BY FIRM_CRD),
ov AS (SELECT TO_CHAR(firm_crd) AS FIRM_CRD, broker_name AS BROKER_NAME, TO_CHAR(dist_ch) AS DIST_CH
       FROM ssdb_integration.lr_strategy.crd_dist_override),
d AS (     -- the dist_ch before the firm overrides
  SELECT f2.*, p.CBD_ID, c.FIRM_CRD AS CRD_FOUND, c.N,
         CASE WHEN c.N = 1 AND c.DIST_CH IS NOT NULL THEN c.DIST_CH ELSE COALESCE(ob.DIST_CH, oc.DIST_CH) END AS DIST_CH0,
         CASE WHEN c.N = 1 AND c.DIST_CH IS NOT NULL THEN 'firm_1 CRD'
              WHEN COALESCE(ob.DIST_CH, oc.DIST_CH) IS NOT NULL THEN 'manual override' END AS DIST_SOURCE
  FROM f2
  LEFT JOIN pick p ON p.ZIP_CODE IS NOT DISTINCT FROM f2.ZIP_CODE AND p.STATE IS NOT DISTINCT FROM f2.STATE
                  AND p.PRODUCT_V2 IS NOT DISTINCT FROM f2.PRODUCT_V2 AND p.ORIGINAL_CBD_ID = f2.ORIGINAL_CBD_ID
  LEFT JOIN crd c ON c.FIRM_CRD = f2.FIRM_CRD
  LEFT JOIN ov ob ON ob.FIRM_CRD = f2.FIRM_CRD AND ob.BROKER_NAME = f2.BROKER_NAME
  LEFT JOIN ov oc ON oc.FIRM_CRD = f2.FIRM_CRD AND oc.BROKER_NAME IS NULL)
SELECT d.ZIP_CODE, d.STATE, d.FIRM_CRD, d.BROKER_NAME, d.FILE_DIST_CH, d.FILE_PL AS FILE_PRODUCT_LINE,
       d.FILE_VA AS FILE_VA_TYPE, d.PRODUCT_V2, d.CBD_METHOD, d.ORIGINAL_CBD_ID, d.CBD_ID,
       COALESCE(fo.DIST_CH, d.DIST_CH0) AS DIST_CH, d.DIST_SOURCE,
       CASE WHEN d.DIST_SOURCE IS NOT NULL THEN NULL
            WHEN d.CRD_FOUND IS NULL THEN 'no firm_1 rows for the CRD'
            WHEN d.N > 1 THEN 'firm_1 rows of the CRD carry 2+ dist_ch'
            ELSE 'firm_1 rows of the CRD have a blank dist_ch' END AS DIST_REVIEW,
       CASE WHEN fo.CBD_ID IS NOT NULL THEN fo.NEW_DIST
            WHEN d.CBD_ID IN ('57', '1967') THEN 'National (Chase)'
            WHEN d.CBD_ID IN ('1822', '14') THEN 'Wells WH'
            WHEN d.CBD_ID IN ('1823') THEN 'Wells FI'
            WHEN d.CBD_ID IN ('438') THEN 'AFS'
            ELSE d.DIST_CH0 END AS NEW_DIST,
       COALESCE(fo.F2_DIST_CH, m.DIST_CH) AS UNION_DIST_CH,
       CASE WHEN d.CBD_ID IS NULL THEN 'no company'
            WHEN m.FILE_DIST_CH IS NOT NULL AND m.DIST_CH IS NULL THEN 'NO CHANNEL' END AS DROP_REASON,
       d.OPP AS MM_OPP
FROM d
LEFT JOIN (SELECT TO_CHAR(CBD_ID) AS CBD_ID, DIST_CH, NEW_DIST, F2_DIST_CH FROM ssdb_integration.lr_strategy.tmp_firm_override) fo
       ON fo.CBD_ID = d.CBD_ID
LEFT JOIN ssdb_integration.lr_strategy.tmp_f2_channel m ON m.FILE_DIST_CH = d.FILE_DIST_CH;

--Statement 8.  firm_2's opportunity per key ZIP_CODE x DIST_CH (firm_2's own) x CBD_ID x PRODUCT_V2, from the rows that
--go on, FILE_NEW_DIST where the key's rows carry one new_dist, KEPT = FALSE: the key sums to 0 and is left out.
CREATE OR REPLACE TEMPORARY TABLE ssdb_integration.lr_strategy.tmp_f2_key AS
SELECT ZIP_CODE, UNION_DIST_CH AS DIST_CH, CBD_ID, PRODUCT_V2, COUNT(*) AS FILE_ROWS, SUM(MM_OPP) AS MM_OPP,
       CASE WHEN COUNT(DISTINCT COALESCE(NEW_DIST, '~')) = 1 THEN MAX(NEW_DIST) END AS FILE_NEW_DIST,
       COALESCE(SUM(MM_OPP), 0) <> 0 AS KEPT
FROM ssdb_integration.lr_strategy.tmp_f2_opp
WHERE DROP_REASON IS NULL
GROUP BY ZIP_CODE, UNION_DIST_CH, CBD_ID, PRODUCT_V2;

--Statement 9.  FIRM_KEY, one key per firm across both firms (owner, 2026-10-26): a CRD and a CBD_ID are linked when
--the vendor's resolved rows put them together (firm_1's crd_cbd_mm, firm_2's tmp_f2_opp), linked CRDs and CBD_IDs
--are one firm (a CBD_ID of union_base with no link is a firm alone).  FIRM_KEY = its CBD_ID with the most opportunity.
--Six passes each carry the smallest CBD_ID one link further, a check says whether six were enough (if not, copy the
--r6/c6 lines as r7/c7 and read c7 in g).  KEY_REVIEW: the key's CBD_IDs carry 2+ PARENT in firm_1's rows.
CREATE OR REPLACE TEMPORARY TABLE ssdb_integration.lr_strategy.tmp_firm_key AS
WITH
l AS (SELECT * FROM ssdb_integration.lr_strategy.tmp_label),
e AS (   -- the links, with their opportunity
  SELECT CRD, CBD, SUM(OPP) AS OPP
  FROM (SELECT TO_CHAR(firm_crd) AS CRD, TO_CHAR(cbd_id) AS CBD, mm_opp AS OPP FROM ssdb_integration.lr_strategy.crd_cbd_mm
        UNION ALL
        SELECT FIRM_CRD, CBD_ID, MM_OPP FROM ssdb_integration.lr_strategy.tmp_f2_opp) x
  WHERE CRD IS NOT NULL AND CBD IS NOT NULL
  GROUP BY CRD, CBD),
c0 AS (SELECT DISTINCT CBD, CBD AS LAB FROM e),
r1 AS (SELECT e.CRD, MIN(c.LAB) AS LAB FROM e JOIN c0 c ON c.CBD = e.CBD GROUP BY e.CRD),
c1 AS (SELECT e.CBD, MIN(r.LAB) AS LAB FROM e JOIN r1 r ON r.CRD = e.CRD GROUP BY e.CBD),
r2 AS (SELECT e.CRD, MIN(c.LAB) AS LAB FROM e JOIN c1 c ON c.CBD = e.CBD GROUP BY e.CRD),
c2 AS (SELECT e.CBD, MIN(r.LAB) AS LAB FROM e JOIN r2 r ON r.CRD = e.CRD GROUP BY e.CBD),
r3 AS (SELECT e.CRD, MIN(c.LAB) AS LAB FROM e JOIN c2 c ON c.CBD = e.CBD GROUP BY e.CRD),
c3 AS (SELECT e.CBD, MIN(r.LAB) AS LAB FROM e JOIN r3 r ON r.CRD = e.CRD GROUP BY e.CBD),
r4 AS (SELECT e.CRD, MIN(c.LAB) AS LAB FROM e JOIN c3 c ON c.CBD = e.CBD GROUP BY e.CRD),
c4 AS (SELECT e.CBD, MIN(r.LAB) AS LAB FROM e JOIN r4 r ON r.CRD = e.CRD GROUP BY e.CBD),
r5 AS (SELECT e.CRD, MIN(c.LAB) AS LAB FROM e JOIN c4 c ON c.CBD = e.CBD GROUP BY e.CRD),
c5 AS (SELECT e.CBD, MIN(r.LAB) AS LAB FROM e JOIN r5 r ON r.CRD = e.CRD GROUP BY e.CBD),
r6 AS (SELECT e.CRD, MIN(c.LAB) AS LAB FROM e JOIN c5 c ON c.CBD = e.CBD GROUP BY e.CRD),
c6 AS (SELECT e.CBD, MIN(r.LAB) AS LAB FROM e JOIN r6 r ON r.CRD = e.CRD GROUP BY e.CBD),
g AS (   -- every CBD_ID and its group
  SELECT CBD, LAB AS GRP FROM c6
  UNION ALL
  SELECT DISTINCT TO_CHAR(u.cbd_id), TO_CHAR(u.cbd_id) FROM ssdb_integration.lr_strategy.union_base u
  WHERE u.cbd_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM e WHERE e.CBD = TO_CHAR(u.cbd_id))),
w AS (SELECT g.CBD, g.GRP, COALESCE(o.OPP, 0) AS OPP
      FROM g LEFT JOIN (SELECT CBD, SUM(OPP) AS OPP FROM e GROUP BY CBD) o ON o.CBD = g.CBD),
kl AS (SELECT GRP, CBD AS FIRM_KEY FROM w QUALIFY ROW_NUMBER() OVER (PARTITION BY GRP ORDER BY OPP DESC, CBD) = 1),
cr AS (SELECT DISTINCT e.CRD, w.GRP FROM e JOIN w ON w.CBD = e.CBD),
p1 AS (SELECT TO_CHAR(u.cbd_id) AS CBD, MAX(u.parent) AS PARENT
       FROM ssdb_integration.lr_strategy.union_base u CROSS JOIN l
       WHERE u.source = l.F1 AND u.cbd_id IS NOT NULL GROUP BY TO_CHAR(u.cbd_id)),
n AS (SELECT w.GRP, COUNT(DISTINCT w.CBD) AS N_CBD, COUNT(DISTINCT p1.PARENT) AS N_PARENT
      FROM w LEFT JOIN p1 ON p1.CBD = w.CBD GROUP BY w.GRP),
nc AS (SELECT GRP, COUNT(*) AS N_CRD FROM cr GROUP BY GRP),
ids AS (SELECT 'CBD_ID' AS ID_TYPE, CBD AS ID, GRP FROM w UNION ALL SELECT 'CRD', CRD, GRP FROM cr)
SELECT ids.ID_TYPE, ids.ID, kl.FIRM_KEY, n.N_CBD, COALESCE(nc.N_CRD, 0) AS N_CRD,
       CASE WHEN n.N_PARENT > 1 THEN 'CBD_IDs of the key carry 2+ PARENT' END AS KEY_REVIEW
FROM ids JOIN kl ON kl.GRP = ids.GRP JOIN n ON n.GRP = ids.GRP LEFT JOIN nc ON nc.GRP = ids.GRP;

--Statement 10.  UNION_OPP (owner, 2026-10-25: "it needs to match the layout of firm 1's data. there needs to be a join
--so that mm_opp and sales exists for firm two on the same rows").  union_base itself is never changed.
--  * Every union_base row, as it is, except: firm_2's VA counted as VARIABLE (Q8), the firm overrides (statement 4),
--    a row whose DIST_CH an override changes takes the territory holder of its ZIP_CODE x new DIST_CH.
--  * firm_2's opportunity per key ZIP_CODE x DIST_CH (firm_2's own) x CBD_ID x PRODUCT_V2 goes on one firm_2 sales
--    row of that key whose seller is the territory holder (the largest ACTUAL_SALES_AMOUNT, ties on the other columns).
--  * A key with no such row becomes opp-only rows, one per new_dist x CRD, with the territory holder of its
--    ZIP_CODE x DIST_CH in both wholesaler columns (lowest CLEAN_ID where 2+ hold it, none: NULL).
--  * The opportunity overrides (statement 5) scale, remove or add firm_1's opportunity of the listed companies.
--Columns: union_base's, in its order, then
--  FIRM_OVERRIDE  TRUE on every row of a company in tmp_firm_override
--  HOLDER_MOVED   TRUE on a union row whose territory holder moved with a firm override
--  ROW_ORIGIN     'union', 'union + opp file' (a firm_2 sales row now carrying MM_OPP), 'opp file' (opp-only row)
--  FILE_NEW_DIST  the new_dist firm_2's file gives the opportunity (on a sales row: NULL if its key has 2+)
--  CHANNEL_RULE   'sales row', on an opp-only row 'firm_1 NEW_DIST': the CHANNEL firm_1's rows carry for its NEW_DIST
--  N_HOLDERS      how many hold the row's ZIP_CODE x DIST_CH in territories (opp-only and moved rows)
--  FIRM_KEY       statement 9
--  FIRM_CRD       the company's CRD where it has exactly one (CRD_RULE says why not), opp-only rows: the file's CRD
--  CRD_RULE       'file', 'company has one CRD', 'company has 2+ CRDs', 'company has no CRD'
--  OPP_OVERRIDE   firm_1 rows of a statement-5 company: 'scaled', 'removed', 'added'
CREATE OR REPLACE TABLE ssdb_integration.lr_strategy.UNION_OPP AS
WITH
l AS (SELECT * FROM ssdb_integration.lr_strategy.tmp_label),
fov AS (SELECT TO_CHAR(CBD_ID) AS CBD_ID, DIST_CH, NEW_DIST, F2_DIST_CH FROM ssdb_integration.lr_strategy.tmp_firm_override),
oo AS (SELECT DISTINCT TO_CHAR(CBD_ID) AS CBD_ID FROM ssdb_integration.lr_strategy.tmp_opp_override),
--Lookups
hz AS (    -- the territory holder of a SOURCE x ZIP_CODE x DIST_CH: the lowest CLEAN_ID, N = how many hold it
  SELECT SOURCE, ZIP_CODE, CHANNEL AS DIST_CH, MIN(CLEAN_ID) AS ID, COUNT(DISTINCT CLEAN_ID) AS N,
         MIN_BY(CLEAN_NAME, CLEAN_ID) AS NAME, MIN_BY(NAME, CLEAN_ID) AS RAW
  FROM ssdb_integration.lr_strategy.territories WHERE CLEAN_ID IS NOT NULL GROUP BY SOURCE, ZIP_CODE, CHANNEL),
hn AS (    -- the holder's names as union_base spells them (else territories')
  SELECT SOURCE, TERRITORY_WHOLESALER_TERRITORY_ID AS ID, MAX(TERR_WHOLESALER_CLEAN_NAME) AS NAME, MAX(TERR_WHOLESALER) AS RAW
  FROM ssdb_integration.lr_strategy.union_base GROUP BY SOURCE, TERRITORY_WHOLESALER_TERRITORY_ID),
ad AS (    -- the address ID union_base pairs with a territory ID, where it pairs exactly one
  SELECT SOURCE, TERRITORY_WHOLESALER_TERRITORY_ID AS ID, MIN(TERRITORY_WHOLESALER_ADDRESS_ID) AS ADDR
  FROM ssdb_integration.lr_strategy.union_base
  WHERE TERRITORY_WHOLESALER_TERRITORY_ID IS NOT NULL AND TERRITORY_WHOLESALER_ADDRESS_ID IS NOT NULL
  GROUP BY SOURCE, TERRITORY_WHOLESALER_TERRITORY_ID HAVING COUNT(DISTINCT TERRITORY_WHOLESALER_ADDRESS_ID) = 1),
ch AS (    -- the CHANNEL firm_1's rows carry for a NEW_DIST, where they carry one
  SELECT u.NEW_DIST, MAX(u.CHANNEL) AS CHANNEL FROM ssdb_integration.lr_strategy.union_base u CROSS JOIN l
  WHERE u.SOURCE = l.F1 AND u.NEW_DIST IS NOT NULL
  GROUP BY u.NEW_DIST HAVING COUNT(DISTINCT COALESCE(u.CHANNEL, '~')) = 1),
fp AS (    -- FIRM and PARENT of a company in each SOURCE
  SELECT CBD_ID, SOURCE, MAX(FIRM) AS FIRM, MAX(PARENT) AS PARENT
  FROM ssdb_integration.lr_strategy.union_base WHERE CBD_ID IS NOT NULL GROUP BY CBD_ID, SOURCE),
cn AS (    -- crd_cbd's firm name: FIRM where union_base has none (owner, 2026-10-25)
  SELECT CAST(CBD_ID AS VARCHAR) AS CBD_ID, MAX(FIRM) AS FIRM FROM ssdb_integration.lr_strategy.crd_cbd
  WHERE CBD_ID IS NOT NULL AND CAST(CBD_ID AS VARCHAR) <> '0' GROUP BY 1),
cc AS (    -- a company's CRDs in the vendor's resolved rows
  SELECT CBD, MAX(CRD) AS CRD, COUNT(DISTINCT CRD) AS N_CRD
  FROM (SELECT TO_CHAR(cbd_id) AS CBD, TO_CHAR(firm_crd) AS CRD FROM ssdb_integration.lr_strategy.crd_cbd_mm
        UNION SELECT CBD_ID, FIRM_CRD FROM ssdb_integration.lr_strategy.tmp_f2_opp) x
  WHERE CBD IS NOT NULL AND CRD IS NOT NULL GROUP BY CBD),
st AS (SELECT ZIP_CODE, MAX(STATE) AS STATE FROM ssdb_integration.lr_strategy.territories GROUP BY ZIP_CODE),
us AS (SELECT ZIP_CODE, MAX(STATE) AS STATE FROM ssdb_integration.lr_strategy.union_base GROUP BY ZIP_CODE),
fk AS (SELECT ID, FIRM_KEY FROM ssdb_integration.lr_strategy.tmp_firm_key WHERE ID_TYPE = 'CBD_ID'),
--firm_2's opportunity (statements 7-8): the rows that go on, in firm_2's own channel (DIST_CH), and the keys kept,
--F1_DIST_CH = the firm_1 channel a row was given (for rows the opportunity overrides add)
f2 AS (
  SELECT ZIP_CODE, UNION_DIST_CH AS DIST_CH, CBD_ID, PRODUCT_V2, NEW_DIST, FIRM_CRD, MM_OPP, DIST_CH AS F1_DIST_CH
  FROM ssdb_integration.lr_strategy.tmp_f2_opp WHERE DROP_REASON IS NULL),
f2_key AS (SELECT ZIP_CODE, DIST_CH, CBD_ID, PRODUCT_V2, MM_OPP, FILE_NEW_DIST FROM ssdb_integration.lr_strategy.tmp_f2_key WHERE KEPT),
--The union rows
u_ov AS (     -- the overrides: NEW_DIST, CHANNEL and ND, the new DIST_CH (firm_1's: DIST_CH, firm_2's: F2_DIST_CH)
  SELECT u.* REPLACE (CASE WHEN u.SOURCE = l.F2 AND u.PRODUCT_V2 = l.F2_VA THEN l.VARIABLE ELSE u.PRODUCT_V2 END AS PRODUCT_V2,
                      CASE WHEN fv.CBD_ID IS NOT NULL THEN fv.NEW_DIST ELSE u.NEW_DIST END AS NEW_DIST,
                      CASE WHEN fv.CBD_ID IS NOT NULL THEN fc.CHANNEL ELSE u.CHANNEL END AS CHANNEL),
         CASE WHEN fv.CBD_ID IS NULL THEN u.DIST_CH WHEN u.SOURCE = l.F1 THEN fv.DIST_CH
              ELSE COALESCE(fv.F2_DIST_CH, u.DIST_CH) END AS ND,
         CASE WHEN fv.CBD_ID IS NOT NULL THEN TRUE END AS FIRM_OVERRIDE
  FROM ssdb_integration.lr_strategy.union_base u CROSS JOIN l
  LEFT JOIN fov fv ON fv.CBD_ID = TO_CHAR(u.CBD_ID)
  LEFT JOIN ch fc ON fc.NEW_DIST = fv.NEW_DIST),
u_hold AS (   -- DIST_CH = ND, a moved row (MV) takes the holder of its ZIP_CODE x new DIST_CH, IS_HOLDER: seller = holder
  SELECT x.* REPLACE (x.ND AS DIST_CH,
           CASE WHEN x.MV THEN COALESCE(nn.RAW, hh.RAW) ELSE x.TERR_WHOLESALER END AS TERR_WHOLESALER,
           CASE WHEN x.MV THEN COALESCE(nn.NAME, hh.NAME) ELSE x.TERR_WHOLESALER_CLEAN_NAME END AS TERR_WHOLESALER_CLEAN_NAME,
           CASE WHEN x.MV THEN hh.ID ELSE x.TERRITORY_WHOLESALER_TERRITORY_ID END AS TERRITORY_WHOLESALER_TERRITORY_ID,
           CASE WHEN x.MV THEN ha.ADDR ELSE x.TERRITORY_WHOLESALER_ADDRESS_ID END AS TERRITORY_WHOLESALER_ADDRESS_ID,
           CASE WHEN x.MV THEN CASE WHEN hh.ID IS NOT NULL THEN 1 ELSE 0 END
                ELSE x.TERRITORY_WHOLESALER_HAS_TERRITORY END AS TERRITORY_WHOLESALER_HAS_TERRITORY),
         CASE WHEN x.MV THEN TRUE END AS HOLDER_MOVED,
         COALESCE(x.SALES_WHOLESALER_TERRITORY_ID
                  = CASE WHEN x.MV THEN hh.ID ELSE x.TERRITORY_WHOLESALER_TERRITORY_ID END, FALSE) AS IS_HOLDER
  FROM (SELECT u_ov.*, u_ov.ND IS DISTINCT FROM u_ov.DIST_CH AS MV FROM u_ov) x
  LEFT JOIN hz hh ON x.MV AND hh.SOURCE = x.SOURCE AND hh.ZIP_CODE = x.ZIP_CODE AND hh.DIST_CH = x.ND
  LEFT JOIN hn nn ON nn.SOURCE = x.SOURCE AND nn.ID = hh.ID
  LEFT JOIN ad ha ON ha.SOURCE = x.SOURCE AND ha.ID = hh.ID),
u_pick AS (   -- PICK: the one firm_2 holder row per key that takes the key's opportunity
  SELECT r.*, r.SOURCE = l.F2 AND r.IS_HOLDER AND ROW_NUMBER() OVER (
           PARTITION BY r.SOURCE, r.ZIP_CODE, r.DIST_CH, r.CBD_ID, r.PRODUCT_V2
           ORDER BY r.IS_HOLDER DESC, r.ACTUAL_SALES_AMOUNT DESC NULLS LAST, r.FISCAL_YR, r.TERR_WHOLESALER,
                    r.SALES_WHOLESALER, r.TERR_WHOLESALER_CLEAN_NAME, r.SALES_WHOLESALER_CLEAN_NAME, r.FIRM,
                    r.PARENT, r.NEW_DIST, r.CHANNEL, r.STATE, r.SALES_AMOUNT, r.SALES_WHOLESALER_TERRITORY_ID,
                    r.SALES_WHOLESALER_ADDRESS_ID, r.TERRITORY_WHOLESALER_TERRITORY_ID,
                    r.TERRITORY_WHOLESALER_ADDRESS_ID, r.SALES_WHOLESALER_HAS_TERRITORY,
                    r.TERRITORY_WHOLESALER_HAS_TERRITORY) = 1 AS PICK
  FROM u_hold r CROSS JOIN l),
--The opp-only rows: firm_2's keys with no holder row, and firm_1's cells an opportunity override adds
f2_left AS (
  SELECT f2.ZIP_CODE, f2.DIST_CH, f2.CBD_ID, f2.PRODUCT_V2, f2.NEW_DIST, f2.FIRM_CRD, SUM(f2.MM_OPP) AS MM_OPP
  FROM f2
  JOIN f2_key k ON k.ZIP_CODE = f2.ZIP_CODE AND k.DIST_CH = f2.DIST_CH AND k.CBD_ID = f2.CBD_ID AND k.PRODUCT_V2 = f2.PRODUCT_V2
  WHERE NOT EXISTS (SELECT 1 FROM u_pick r WHERE r.PICK AND r.ZIP_CODE = k.ZIP_CODE AND r.DIST_CH = k.DIST_CH
                    AND r.CBD_ID = k.CBD_ID AND r.PRODUCT_V2 = k.PRODUCT_V2)
  GROUP BY f2.ZIP_CODE, f2.DIST_CH, f2.CBD_ID, f2.PRODUCT_V2, f2.NEW_DIST, f2.FIRM_CRD
  HAVING COALESCE(SUM(f2.MM_OPP), 0) <> 0),
f1_cell AS (  -- firm_1's opportunity of a listed company per ZIP_CODE x PRODUCT_V2
  SELECT r.ZIP_CODE, TO_CHAR(r.CBD_ID) AS CBD_ID, r.PRODUCT_V2, SUM(r.MM_OPP) AS O1
  FROM u_pick r CROSS JOIN l JOIN oo ON oo.CBD_ID = TO_CHAR(r.CBD_ID)
  WHERE r.SOURCE = l.F1 AND r.MM_OPP IS NOT NULL GROUP BY r.ZIP_CODE, TO_CHAR(r.CBD_ID), r.PRODUCT_V2),
f1_added AS ( -- firm_2's opportunity of a listed company where firm_1 has none, in the firm_1 channel it was given
  SELECT f2.ZIP_CODE, f2.F1_DIST_CH AS DIST_CH, f2.CBD_ID, f2.PRODUCT_V2, f2.NEW_DIST, f2.FIRM_CRD, SUM(f2.MM_OPP) AS MM_OPP
  FROM f2 JOIN oo ON oo.CBD_ID = f2.CBD_ID
  WHERE NOT EXISTS (SELECT 1 FROM f1_cell t WHERE t.ZIP_CODE = f2.ZIP_CODE AND t.CBD_ID = f2.CBD_ID
                    AND t.PRODUCT_V2 = f2.PRODUCT_V2 AND t.O1 <> 0)
  GROUP BY f2.ZIP_CODE, f2.F1_DIST_CH, f2.CBD_ID, f2.PRODUCT_V2, f2.NEW_DIST, f2.FIRM_CRD
  HAVING COALESCE(SUM(f2.MM_OPP), 0) <> 0),
opp_only AS ( -- both kinds in union_base's columns: the holder of the ZIP_CODE x DIST_CH in both wholesaler columns
  SELECT k.SOURCE, k.CBD_ID, COALESCE(own.FIRM, oth.FIRM, cn.FIRM) AS FIRM, COALESCE(own.PARENT, oth.PARENT) AS PARENT,
         k.DIST_CH, k.NEW_DIST, ch.CHANNEL, COALESCE(st.STATE, us.STATE) AS STATE, k.ZIP_CODE, k.PRODUCT_V2, k.MM_OPP,
         COALESCE(nn.RAW, h.RAW) AS TERR_WHOLESALER, COALESCE(nn.RAW, h.RAW) AS SALES_WHOLESALER,
         COALESCE(nn.NAME, h.NAME) AS TERR_WHOLESALER_CLEAN_NAME, COALESCE(nn.NAME, h.NAME) AS SALES_WHOLESALER_CLEAN_NAME,
         h.ID AS SALES_WHOLESALER_TERRITORY_ID, h.ID AS TERRITORY_WHOLESALER_TERRITORY_ID,
         ad.ADDR AS SALES_WHOLESALER_ADDRESS_ID, ad.ADDR AS TERRITORY_WHOLESALER_ADDRESS_ID,
         CASE WHEN h.N > 0 THEN 1 ELSE 0 END AS SALES_WHOLESALER_HAS_TERRITORY,
         CASE WHEN h.N > 0 THEN 1 ELSE 0 END AS TERRITORY_WHOLESALER_HAS_TERRITORY,
         'opp file' AS ROW_ORIGIN, k.NEW_DIST AS FILE_NEW_DIST,
         CASE WHEN ch.NEW_DIST IS NOT NULL THEN 'firm_1 NEW_DIST' END AS CHANNEL_RULE, COALESCE(h.N, 0) AS N_HOLDERS,
         fk.FIRM_KEY, k.FIRM_CRD, 'file' AS CRD_RULE, CASE WHEN fv.CBD_ID IS NOT NULL THEN TRUE END AS FIRM_OVERRIDE,
         k.OPP_OVERRIDE
  FROM (SELECT l.F2 AS SOURCE, l.F1 AS OTHER, CAST(NULL AS VARCHAR) AS OPP_OVERRIDE, a.ZIP_CODE, a.DIST_CH, a.CBD_ID,
               a.PRODUCT_V2, a.NEW_DIST, a.FIRM_CRD, a.MM_OPP
        FROM f2_left a CROSS JOIN l
        UNION ALL
        SELECT l.F1, l.F2, 'added', a.ZIP_CODE, a.DIST_CH, a.CBD_ID, a.PRODUCT_V2, a.NEW_DIST, a.FIRM_CRD, a.MM_OPP
        FROM f1_added a CROSS JOIN l) k
  LEFT JOIN ch ON ch.NEW_DIST = k.NEW_DIST
  LEFT JOIN fp own ON own.CBD_ID = k.CBD_ID AND own.SOURCE = k.SOURCE
  LEFT JOIN fp oth ON oth.CBD_ID = k.CBD_ID AND oth.SOURCE = k.OTHER
  LEFT JOIN cn ON cn.CBD_ID = k.CBD_ID
  LEFT JOIN hz h ON h.SOURCE = k.SOURCE AND h.ZIP_CODE = k.ZIP_CODE AND h.DIST_CH = k.DIST_CH
  LEFT JOIN hn nn ON nn.SOURCE = k.SOURCE AND nn.ID = h.ID
  LEFT JOIN ad ON ad.SOURCE = k.SOURCE AND ad.ID = h.ID
  LEFT JOIN st ON st.ZIP_CODE = k.ZIP_CODE
  LEFT JOIN us ON us.ZIP_CODE = k.ZIP_CODE
  LEFT JOIN fk ON fk.ID = k.CBD_ID
  LEFT JOIN fov fv ON fv.CBD_ID = k.CBD_ID),
--The union rows with firm_2's opportunity on them, and firm_2's opp-only rows
pre AS (
  SELECT r.* EXCLUDE (IS_HOLDER, PICK, ND, MV) REPLACE (COALESCE(k.MM_OPP, r.MM_OPP) AS MM_OPP),
         CASE WHEN k.CBD_ID IS NOT NULL THEN 'union + opp file' ELSE 'union' END AS ROW_ORIGIN,
         k.FILE_NEW_DIST, CASE WHEN k.CBD_ID IS NOT NULL THEN 'sales row' END AS CHANNEL_RULE,
         CASE WHEN k.CBD_ID IS NOT NULL OR r.HOLDER_MOVED THEN COALESCE(h.N, 0) END AS N_HOLDERS, fk.FIRM_KEY,
         CASE WHEN cc.N_CRD = 1 THEN cc.CRD END AS FIRM_CRD,
         CASE WHEN r.CBD_ID IS NULL THEN NULL WHEN cc.N_CRD = 1 THEN 'company has one CRD'
              WHEN cc.N_CRD > 1 THEN 'company has 2+ CRDs' ELSE 'company has no CRD' END AS CRD_RULE
  FROM u_pick r
  LEFT JOIN f2_key k ON r.PICK AND k.ZIP_CODE = r.ZIP_CODE AND k.DIST_CH = r.DIST_CH AND k.CBD_ID = r.CBD_ID
                    AND k.PRODUCT_V2 = r.PRODUCT_V2
  LEFT JOIN hz h ON h.SOURCE = r.SOURCE AND h.ZIP_CODE = r.ZIP_CODE AND h.DIST_CH = r.DIST_CH
  LEFT JOIN fk ON fk.ID = TO_CHAR(r.CBD_ID)
  LEFT JOIN cc ON cc.CBD = TO_CHAR(r.CBD_ID)
  UNION ALL BY NAME
  SELECT * EXCLUDE (OPP_OVERRIDE) FROM opp_only WHERE OPP_OVERRIDE IS NULL),
f2_cell AS (  -- firm_2's opportunity of a listed company per ZIP_CODE x PRODUCT_V2
  SELECT p.ZIP_CODE, TO_CHAR(p.CBD_ID) AS CBD_ID, p.PRODUCT_V2, SUM(p.MM_OPP) AS O2
  FROM pre p CROSS JOIN l JOIN oo ON oo.CBD_ID = TO_CHAR(p.CBD_ID)
  WHERE p.SOURCE = l.F2 AND p.MM_OPP IS NOT NULL GROUP BY p.ZIP_CODE, TO_CHAR(p.CBD_ID), p.PRODUCT_V2)
--The opportunity overrides: firm_1's rows of a listed company scaled to firm_2's, or removed, then the rows added
SELECT p.* REPLACE (CASE WHEN p.SOURCE = l.F1 AND oo.CBD_ID IS NOT NULL AND p.MM_OPP IS NOT NULL
                         THEN CASE WHEN COALESCE(t1.O1, 0) = 0 OR COALESCE(t2.O2, 0) = 0 THEN NULL
                                   ELSE p.MM_OPP * t2.O2 / t1.O1 END
                         ELSE p.MM_OPP END AS MM_OPP),
       CASE WHEN p.SOURCE = l.F1 AND oo.CBD_ID IS NOT NULL AND p.MM_OPP IS NOT NULL
            THEN CASE WHEN COALESCE(t1.O1, 0) = 0 OR COALESCE(t2.O2, 0) = 0 THEN 'removed' ELSE 'scaled' END
       END AS OPP_OVERRIDE
FROM pre p CROSS JOIN l
LEFT JOIN oo ON oo.CBD_ID = TO_CHAR(p.CBD_ID)
LEFT JOIN f1_cell t1 ON t1.ZIP_CODE = p.ZIP_CODE AND t1.CBD_ID = TO_CHAR(p.CBD_ID) AND t1.PRODUCT_V2 = p.PRODUCT_V2
LEFT JOIN f2_cell t2 ON t2.ZIP_CODE = p.ZIP_CODE AND t2.CBD_ID = TO_CHAR(p.CBD_ID) AND t2.PRODUCT_V2 = p.PRODUCT_V2
UNION ALL BY NAME
SELECT * FROM opp_only WHERE OPP_OVERRIDE = 'added';

--Statement 11.  The opportunity crosswalk: for each firm, every step that touches opportunity, one row per FROM ->
--TO with the rows and opportunity before and after it.  A step's rows and opportunity after are the next step's
--before (checked, statement 17).  CHANGES says what a step may do: 'nothing' (labels only: before = after on every
--row), 'drops' (each row keeps all or drops all), 'regroups' (rows change grain, opportunity stays), 'amounts'
--(only the opportunity override's scaled, removed and added change amounts).
CREATE OR REPLACE TEMPORARY TABLE ssdb_integration.lr_strategy.tmp_opp_xwalk AS
WITH
l AS (SELECT * FROM ssdb_integration.lr_strategy.tmp_label),
f2 AS (SELECT * FROM ssdb_integration.lr_strategy.tmp_f2_opp),
k AS (SELECT * FROM ssdb_integration.lr_strategy.tmp_f2_key),
fov AS (SELECT TO_CHAR(CBD_ID) AS CBD_ID, DIST_CH, F2_DIST_CH FROM ssdb_integration.lr_strategy.tmp_firm_override),
oo AS (SELECT DISTINCT TO_CHAR(CBD_ID) AS CBD_ID FROM ssdb_integration.lr_strategy.tmp_opp_override),
u1 AS (SELECT u.* FROM ssdb_integration.lr_strategy.union_base u JOIN l ON u.SOURCE = l.F1 WHERE u.MM_OPP IS NOT NULL),
o1 AS (SELECT u.* FROM ssdb_integration.lr_strategy.UNION_OPP u JOIN l ON u.SOURCE = l.F1),
o2 AS (SELECT u.* FROM ssdb_integration.lr_strategy.UNION_OPP u JOIN l ON u.SOURCE = l.F2 WHERE u.ROW_ORIGIN <> 'union'),
place AS (   -- each kept key and the UNION_OPP rows that carry it
  SELECT k.MM_OPP AS OPP_BEFORE, COUNT(o2.SOURCE) AS ROWS_AFTER, COALESCE(SUM(o2.MM_OPP), 0) AS OPP_AFTER,
         CASE WHEN MAX(CASE WHEN o2.ROW_ORIGIN = 'union + opp file' THEN 1 ELSE 0 END) = 1 THEN 'the holder''s sales row'
              WHEN COUNT(o2.SOURCE) = 0 THEN 'no UNION_OPP row'
              WHEN MAX(o2.N_HOLDERS) = 0 THEN 'opp-only rows, no territory holder'
              WHEN MAX(o2.N_HOLDERS) > 1 THEN 'opp-only rows, 2+ holders (lowest CLEAN_ID)'
              ELSE 'opp-only rows, the territory holder' END AS TO_VALUE
  FROM k
  LEFT JOIN o2 ON o2.ZIP_CODE = k.ZIP_CODE AND o2.DIST_CH IS NOT DISTINCT FROM k.DIST_CH AND TO_CHAR(o2.CBD_ID) = k.CBD_ID
              AND o2.PRODUCT_V2 IS NOT DISTINCT FROM k.PRODUCT_V2
  WHERE k.KEPT
  GROUP BY k.ZIP_CODE, k.DIST_CH, k.CBD_ID, k.PRODUCT_V2, k.MM_OPP),
c1 AS (SELECT ZIP_CODE, TO_CHAR(CBD_ID) AS CBD_ID, PRODUCT_V2, COUNT(*) AS N, SUM(MM_OPP) AS O FROM u1 GROUP BY 1, 2, 3),
c2 AS (SELECT ZIP_CODE, TO_CHAR(CBD_ID) AS CBD_ID, PRODUCT_V2, COUNT(MM_OPP) AS N, SUM(MM_OPP) AS O,
              -- a cell whose firm_1 opportunity sums to 0 is 'removed' and gets firm_2's 'added': both
              CASE WHEN MIN(OPP_OVERRIDE) <> MAX(OPP_OVERRIDE) THEN MIN(OPP_OVERRIDE) || ' + ' || MAX(OPP_OVERRIDE)
                   ELSE MAX(OPP_OVERRIDE) END AS OUTCOME
       FROM o1 WHERE MM_OPP IS NOT NULL OR OPP_OVERRIDE IS NOT NULL GROUP BY 1, 2, 3),
cells AS (   -- firm_1's opportunity per ZIP_CODE x CBD_ID x PRODUCT_V2, before (union_base) and after (UNION_OPP)
  SELECT COALESCE(c1.CBD_ID, c2.CBD_ID) AS CBD_ID, c2.OUTCOME, COALESCE(c1.N, 0) AS N1, COALESCE(c2.N, 0) AS N2,
         COALESCE(c1.O, 0) AS O1, COALESCE(c2.O, 0) AS O2
  FROM c1 FULL OUTER JOIN c2 ON COALESCE(c2.ZIP_CODE, '~') = COALESCE(c1.ZIP_CODE, '~')    -- plain equality: a FULL JOIN needs it
                            AND COALESCE(c2.CBD_ID, '~') = COALESCE(c1.CBD_ID, '~')
                            AND COALESCE(c2.PRODUCT_V2, '~') = COALESCE(c1.PRODUCT_V2, '~'))
--firm_2
SELECT 'firm_2' AS FIRM, 0 AS STEP_NO, 'source: opp_original, as read in' AS STEP, 'nothing' AS CHANGES,
       'opp_original' AS FROM_VALUE, 'tmp_f2_opp' AS TO_VALUE,
       (SELECT COUNT(*) FROM ssdb_integration.lr_strategy.opp_original) AS ROWS_BEFORE, (SELECT COUNT(*) FROM f2) AS ROWS_AFTER,
       (SELECT SUM(opp) FROM ssdb_integration.lr_strategy.opp_original) AS OPP_BEFORE, (SELECT SUM(MM_OPP) FROM f2) AS OPP_AFTER
UNION ALL
SELECT 'firm_2', 1, 'product: file product line / VA type -> PRODUCT_V2', 'nothing',
       COALESCE(FILE_PRODUCT_LINE, '(blank)') || ' / ' || COALESCE(FILE_VA_TYPE, '(blank)'),
       COALESCE(PRODUCT_V2, '(none: no branch of the rule)'), COUNT(*), COUNT(*), SUM(MM_OPP), SUM(MM_OPP)
FROM f2 GROUP BY 5, 6
UNION ALL
SELECT 'firm_2', 2, 'company: how found -> company', 'drops',
       CBD_METHOD,
       CASE WHEN CBD_ID IS NULL THEN 'no company: dropped' WHEN ORIGINAL_CBD_ID LIKE '%|%' THEN 'company, picked from a list'
            ELSE 'company' END,
       COUNT(*), COUNT(CBD_ID), SUM(MM_OPP), COALESCE(SUM(CASE WHEN CBD_ID IS NOT NULL THEN MM_OPP END), 0)
FROM f2 GROUP BY 5, 6
UNION ALL
SELECT 'firm_2', 3, 'firm_1 channel: how found -> dist_ch -> new_dist (sets NEW_DIST of opp-only rows)', 'nothing',
       CASE WHEN fov.CBD_ID IS NOT NULL THEN 'firm override' ELSE COALESCE(f2.DIST_SOURCE, 'none: ' || f2.DIST_REVIEW) END,
       COALESCE(f2.DIST_CH, '(none)') || ' -> ' || COALESCE(f2.NEW_DIST, '(none)'),
       COUNT(*), COUNT(*), SUM(f2.MM_OPP), SUM(f2.MM_OPP)
FROM f2 LEFT JOIN fov ON fov.CBD_ID = f2.CBD_ID WHERE f2.CBD_ID IS NOT NULL GROUP BY 5, 6
UNION ALL
SELECT 'firm_2', 4, 'firm_2 channel: file DIST_CH -> DIST_CH in union_base (the key)', 'drops',
       COALESCE(f2.FILE_DIST_CH, '(blank)') || CASE WHEN fov.F2_DIST_CH IS NOT NULL THEN ', firm override' ELSE '' END,
       CASE WHEN f2.DROP_REASON = 'NO CHANNEL' THEN 'NO CHANNEL: dropped'
            ELSE COALESCE(f2.UNION_DIST_CH, '(not in tmp_f2_channel)') END,
       COUNT(*), SUM(CASE WHEN f2.DROP_REASON IS NULL THEN 1 ELSE 0 END),
       SUM(f2.MM_OPP), COALESCE(SUM(CASE WHEN f2.DROP_REASON IS NULL THEN f2.MM_OPP END), 0)
FROM f2 LEFT JOIN fov ON fov.CBD_ID = f2.CBD_ID WHERE f2.CBD_ID IS NOT NULL GROUP BY 5, 6
UNION ALL
SELECT 'firm_2', 5, 'keys: rows summed per ZIP_CODE x DIST_CH x CBD_ID x PRODUCT_V2', 'regroups', 'rows',
       CASE WHEN KEPT THEN 'keys' ELSE 'keys summing to 0: dropped' END,
       SUM(FILE_ROWS), SUM(CASE WHEN KEPT THEN 1 ELSE 0 END), SUM(MM_OPP), COALESCE(SUM(CASE WHEN KEPT THEN MM_OPP END), 0)
FROM k GROUP BY 6
UNION ALL
SELECT 'firm_2', 6, 'placement: key -> UNION_OPP rows', 'regroups', 'keys', TO_VALUE,
       COUNT(*), SUM(ROWS_AFTER), SUM(OPP_BEFORE), SUM(OPP_AFTER)
FROM place GROUP BY 6
--firm_1
UNION ALL
SELECT 'firm_1', 0, 'source: union_base (your query''s opportunity)', 'nothing', 'union_base',
       CASE WHEN ACTUAL_SALES_AMOUNT IS NOT NULL OR SALES_AMOUNT IS NOT NULL THEN 'on a sales row' ELSE 'on an opp-only row' END,
       COUNT(*), COUNT(*), SUM(MM_OPP), SUM(MM_OPP)
FROM u1 GROUP BY 6
UNION ALL
SELECT 'firm_1', 1, 'firm override: company DIST_CH -> DIST_CH (the holder moves with it)', 'nothing',
       CASE WHEN fov.CBD_ID IS NULL THEN 'not in tmp_firm_override' ELSE fov.CBD_ID || ': ' || COALESCE(u1.DIST_CH, '(blank)') END,
       CASE WHEN fov.CBD_ID IS NULL THEN 'unchanged'
            WHEN fov.DIST_CH IS DISTINCT FROM u1.DIST_CH THEN fov.DIST_CH || ', holder moves' ELSE fov.DIST_CH || ', holder stays' END,
       COUNT(*), COUNT(*), SUM(u1.MM_OPP), SUM(u1.MM_OPP)
FROM u1 LEFT JOIN fov ON fov.CBD_ID = TO_CHAR(u1.CBD_ID) GROUP BY 5, 6
UNION ALL
SELECT 'firm_1', 2, 'opportunity override: ZIP_CODE x CBD_ID x PRODUCT_V2 cells', 'amounts',
       CASE WHEN oo.CBD_ID IS NULL THEN 'not in tmp_opp_override' ELSE 'in tmp_opp_override' END,
       COALESCE(cells.OUTCOME, 'unchanged'),
       SUM(cells.N1), SUM(cells.N2), SUM(cells.O1), SUM(cells.O2)
FROM cells LEFT JOIN oo ON oo.CBD_ID = cells.CBD_ID GROUP BY 5, 6
UNION ALL
SELECT 'firm_1', 3, 'territory holder of the rows carrying opportunity', 'nothing',
       CASE WHEN OPP_OVERRIDE = 'added' THEN 'row added by the opportunity override'
            WHEN HOLDER_MOVED THEN 'firm override changed DIST_CH' ELSE 'no change' END,
       CASE WHEN OPP_OVERRIDE = 'added' OR HOLDER_MOVED
            THEN CASE WHEN N_HOLDERS = 0 THEN 'no territory holder' WHEN N_HOLDERS > 1 THEN '2+ holders: lowest CLEAN_ID'
                      ELSE 'the territory holder of its ZIP x DIST_CH' END
            ELSE 'holder as in union_base' END,
       COUNT(*), COUNT(*), SUM(MM_OPP), SUM(MM_OPP)
FROM o1 WHERE MM_OPP IS NOT NULL GROUP BY 5, 6;

--Statement 12.  Report: the opportunity crosswalk, each firm step by step, each step starts with its totals
--('= step total'), then one row per FROM -> TO.  PCT = share of the firm's opportunity at its source.
WITH
x AS (SELECT * FROM ssdb_integration.lr_strategy.tmp_opp_xwalk),
s AS (SELECT FIRM, OPP_BEFORE AS O FROM x WHERE STEP_NO = 0 AND FIRM = 'firm_2'
      UNION ALL SELECT FIRM, SUM(OPP_BEFORE) FROM x WHERE STEP_NO = 0 AND FIRM = 'firm_1' GROUP BY FIRM),
r AS (SELECT FIRM, STEP_NO, STEP, CHANGES, '= step total' AS FROM_VALUE, '' AS TO_VALUE, SUM(ROWS_BEFORE) AS ROWS_BEFORE,
             SUM(ROWS_AFTER) AS ROWS_AFTER, SUM(OPP_BEFORE) AS OPP_BEFORE, SUM(OPP_AFTER) AS OPP_AFTER, 0 AS T
      FROM x GROUP BY FIRM, STEP_NO, STEP, CHANGES
      UNION ALL
      SELECT FIRM, STEP_NO, STEP, CHANGES, FROM_VALUE, TO_VALUE, ROWS_BEFORE, ROWS_AFTER, OPP_BEFORE, OPP_AFTER, 1 FROM x)
SELECT r.FIRM, r.STEP_NO, r.STEP, r.CHANGES, r.FROM_VALUE, r.TO_VALUE, r.ROWS_BEFORE, r.ROWS_AFTER,
       r.OPP_BEFORE, r.OPP_AFTER, ROUND(100 * r.OPP_BEFORE / s.O, 2) AS PCT_BEFORE, ROUND(100 * r.OPP_AFTER / s.O, 2) AS PCT_AFTER
FROM r JOIN s ON s.FIRM = r.FIRM
ORDER BY r.FIRM DESC, r.STEP_NO, r.T, r.OPP_BEFORE DESC;

--Statement 13.  Review: firm_2 CRDs with no dist_ch, with firm_1's dist_ch of the CRD and their shares, put the
--answer in crd_dist_override (statement 3) and Run All again.  Names: read at work.
WITH
t AS (SELECT SUM(MM_OPP) AS OPP FROM ssdb_integration.lr_strategy.tmp_f2_opp),
f1 AS (SELECT FIRM_CRD, LISTAGG(DIST_CH || ' ' || TO_CHAR(ROUND(100 * OPP / NULLIF(TOT, 0), 1)) || '%', ', ') WITHIN GROUP (ORDER BY OPP DESC) AS FIRM_1_DIST_CH
       FROM (SELECT FIRM_CRD, COALESCE(DIST_CH, '(blank)') AS DIST_CH, OPP, SUM(OPP) OVER (PARTITION BY FIRM_CRD) AS TOT
             FROM ssdb_integration.lr_strategy.tmp_f1_crd_dist) x
       GROUP BY FIRM_CRD),
r AS (SELECT FIRM_CRD, DIST_REVIEW, LISTAGG(DISTINCT BROKER_NAME, ' | ') AS BROKER_NAMES,
             LISTAGG(DISTINCT FILE_DIST_CH, ', ') AS FIRM_2_DIST_CH, SUM(MM_OPP) AS OPP
      FROM ssdb_integration.lr_strategy.tmp_f2_opp WHERE DIST_REVIEW IS NOT NULL GROUP BY FIRM_CRD, DIST_REVIEW)
SELECT r.FIRM_CRD, r.BROKER_NAMES, r.FIRM_2_DIST_CH, f1.FIRM_1_DIST_CH, r.DIST_REVIEW,
       ROUND(100 * r.OPP / t.OPP, 3) AS PCT_FIRM_2_OPP
FROM r LEFT JOIN f1 ON f1.FIRM_CRD = r.FIRM_CRD CROSS JOIN t
ORDER BY r.OPP DESC;

--Statement 14.  Review: the FIRM_KEYs joining 2+ CBD_IDs: each CBD_ID with firm_1's FIRM and PARENT, the CRDs with
--their broker names, each firm's share of opportunity, the review flag.  Names: read at work.
WITH
l AS (SELECT * FROM ssdb_integration.lr_strategy.tmp_label),
fk AS (SELECT * FROM ssdb_integration.lr_strategy.tmp_firm_key WHERE N_CBD > 1),
u1 AS (SELECT u.* FROM ssdb_integration.lr_strategy.union_base u CROSS JOIN l WHERE u.SOURCE = l.F1),
nm AS (SELECT TO_CHAR(CBD_ID) AS CBD, MAX(FIRM) AS FIRM, MAX(PARENT) AS PARENT FROM u1 WHERE CBD_ID IS NOT NULL GROUP BY 1),
o1 AS (SELECT TO_CHAR(CBD_ID) AS CBD, SUM(MM_OPP) AS OPP FROM u1 GROUP BY 1),
o2 AS (SELECT CBD_ID AS CBD, SUM(MM_OPP) AS OPP FROM ssdb_integration.lr_strategy.tmp_f2_opp WHERE CBD_ID IS NOT NULL GROUP BY 1),
t AS (SELECT (SELECT SUM(OPP) FROM o1) AS T1, (SELECT SUM(OPP) FROM o2) AS T2),
bn AS (SELECT TO_CHAR(firm_crd) AS CRD, broker_name AS BROKER_NAME FROM ssdb_integration.lr_strategy.crd_cbd_mm
       UNION SELECT FIRM_CRD, BROKER_NAME FROM ssdb_integration.lr_strategy.tmp_f2_opp WHERE CBD_ID IS NOT NULL),
c AS (SELECT fk.FIRM_KEY, MAX(fk.KEY_REVIEW) AS KEY_REVIEW,
             LISTAGG(fk.ID || ' ' || COALESCE(nm.FIRM, '?') || ' / ' || COALESCE(nm.PARENT, '?'), '; ') WITHIN GROUP (ORDER BY fk.ID) AS CBD_IDS,
             SUM(o1.OPP) AS OPP1, SUM(o2.OPP) AS OPP2
      FROM fk LEFT JOIN nm ON nm.CBD = fk.ID LEFT JOIN o1 ON o1.CBD = fk.ID LEFT JOIN o2 ON o2.CBD = fk.ID
      WHERE fk.ID_TYPE = 'CBD_ID' GROUP BY fk.FIRM_KEY),
r AS (SELECT fk.FIRM_KEY, LISTAGG(fk.ID || ' ' || COALESCE(bn.BROKER_NAME, '?'), '; ') WITHIN GROUP (ORDER BY fk.ID) AS CRDS
      FROM fk LEFT JOIN bn ON bn.CRD = fk.ID WHERE fk.ID_TYPE = 'CRD' GROUP BY fk.FIRM_KEY)
SELECT c.FIRM_KEY, c.KEY_REVIEW, c.CBD_IDS, r.CRDS,
       ROUND(100 * c.OPP1 / t.T1, 2) AS PCT_FIRM_1_OPP, ROUND(100 * c.OPP2 / t.T2, 2) AS PCT_FIRM_2_OPP
FROM c LEFT JOIN r ON r.FIRM_KEY = c.FIRM_KEY CROSS JOIN t
ORDER BY COALESCE(c.OPP1, 0) + COALESCE(c.OPP2, 0) DESC;

--Statement 15.  Report: does opportunity align across the firms (owner, 2026-10-26)?  Each firm's MM_OPP in UNION_OPP
--summed to ZIP_CODE x firm x PRODUCT_V2, firm = FIRM_KEY and, to compare, CBD_ID.  Equal: within 1e-6 of the larger.
WITH
l AS (SELECT * FROM ssdb_integration.lr_strategy.tmp_label),
uo AS (SELECT u.*, CASE WHEN u.SOURCE = l.F1 THEN u.MM_OPP END AS M1, CASE WHEN u.SOURCE = l.F2 THEN u.MM_OPP END AS M2
       FROM ssdb_integration.lr_strategy.UNION_OPP u CROSS JOIN l WHERE u.MM_OPP IS NOT NULL),
c AS (SELECT 'FIRM_KEY' AS LVL, ZIP_CODE, FIRM_KEY AS FIRM, PRODUCT_V2, SUM(M1) AS O1, SUM(M2) AS O2
      FROM uo GROUP BY ZIP_CODE, FIRM_KEY, PRODUCT_V2
      UNION ALL
      SELECT 'CBD_ID', ZIP_CODE, CBD_ID, PRODUCT_V2, SUM(M1), SUM(M2) FROM uo GROUP BY ZIP_CODE, CBD_ID, PRODUCT_V2),
x AS (SELECT LVL, O1, O2,
             CASE WHEN COALESCE(O1, 0) = 0 THEN 'firm_2 only' WHEN COALESCE(O2, 0) = 0 THEN 'firm_1 only'
                  WHEN ABS(O1 - O2) <= 1e-6 * GREATEST(ABS(O1), ABS(O2)) THEN 'both: equal'
                  WHEN ABS(O2 - O1) <= 0.01 * ABS(O1) THEN 'both: within 1%'
                  WHEN O2 > O1 THEN 'both: firm_2 more than 1% higher'
                  ELSE 'both: firm_2 more than 1% lower' END AS ALIGNMENT
      FROM c),
y AS (SELECT LVL, ALIGNMENT, COUNT(*) AS CELLS, SUM(O1) AS O1, SUM(O2) AS O2 FROM x GROUP BY LVL, ALIGNMENT)
SELECT LVL, ALIGNMENT, CELLS,
       ROUND(100 * O1 / SUM(O1) OVER (PARTITION BY LVL), 2) AS PCT_FIRM_1_MM_OPP,
       ROUND(100 * O2 / SUM(O2) OVER (PARTITION BY LVL), 2) AS PCT_FIRM_2_MM_OPP,
       ROUND(O2 / NULLIF(O1, 0), 3) AS FIRM_2_OVER_FIRM_1
FROM y
ORDER BY LVL DESC, ALIGNMENT;

--Statement 16.  Report: by FIRM_KEY, the ZIP_CODE x PRODUCT_V2 cells where both firms have MM_OPP: how many, the share
--equal, each firm's MM_OPP there, the 40 largest gaps.  FIRM_NAME = firm_1's FIRM of the key's CBD_ID.
WITH
l AS (SELECT * FROM ssdb_integration.lr_strategy.tmp_label),
uo AS (SELECT u.*, CASE WHEN u.SOURCE = l.F1 THEN u.MM_OPP END AS M1, CASE WHEN u.SOURCE = l.F2 THEN u.MM_OPP END AS M2
       FROM ssdb_integration.lr_strategy.UNION_OPP u CROSS JOIN l WHERE u.MM_OPP IS NOT NULL),
c AS (SELECT FIRM_KEY, ZIP_CODE, PRODUCT_V2, SUM(M1) AS O1, SUM(M2) AS O2
      FROM uo GROUP BY FIRM_KEY, ZIP_CODE, PRODUCT_V2
      HAVING COALESCE(SUM(M1), 0) <> 0 AND COALESCE(SUM(M2), 0) <> 0),
nm AS (SELECT TO_CHAR(u.CBD_ID) AS CBD_ID, MAX(u.FIRM) AS FIRM FROM ssdb_integration.lr_strategy.UNION_OPP u CROSS JOIN l
       WHERE u.SOURCE = l.F1 AND u.CBD_ID IS NOT NULL GROUP BY 1)
SELECT c.FIRM_KEY, nm.FIRM AS FIRM_NAME, COUNT(*) AS CELLS_BOTH,
       ROUND(100 * AVG(CASE WHEN ABS(c.O1 - c.O2) <= 1e-6 * GREATEST(ABS(c.O1), ABS(c.O2)) THEN 1 ELSE 0 END), 1) AS PCT_CELLS_EQUAL,
       SUM(c.O1) AS FIRM_1_MM_OPP, SUM(c.O2) AS FIRM_2_MM_OPP, ROUND(SUM(c.O2) / NULLIF(SUM(c.O1), 0), 3) AS FIRM_2_OVER_FIRM_1
FROM c LEFT JOIN nm ON nm.CBD_ID = c.FIRM_KEY
GROUP BY c.FIRM_KEY, nm.FIRM
ORDER BY ABS(SUM(c.O2) - SUM(c.O1)) DESC
LIMIT 40;

--Statement 17.  Checks, last so Run All ends on them: every MUST_BE_ZERO = 1 row must be 0, the others are to read.
--A failing "labels" row lists the label below it.  "pending your CHANNEL step" fails until that step is in.
WITH
l AS (SELECT * FROM ssdb_integration.lr_strategy.tmp_label),
m AS (SELECT * FROM ssdb_integration.lr_strategy.tmp_f2_channel),
f2 AS (SELECT * FROM ssdb_integration.lr_strategy.tmp_f2_opp),
fov AS (SELECT TO_CHAR(CBD_ID) AS CBD_ID, DIST_CH, NEW_DIST, F2_DIST_CH FROM ssdb_integration.lr_strategy.tmp_firm_override),
oo AS (SELECT DISTINCT TO_CHAR(CBD_ID) AS CBD_ID FROM ssdb_integration.lr_strategy.tmp_opp_override),
fk AS (SELECT * FROM ssdb_integration.lr_strategy.tmp_firm_key),
ub AS (SELECT * FROM ssdb_integration.lr_strategy.union_base),
uo AS (SELECT * FROM ssdb_integration.lr_strategy.UNION_OPP),
oc AS (SELECT * FROM uo WHERE ROW_ORIGIN = 'opp file'),
lab AS (   -- each label and how many rows carry it
  SELECT 'tmp_label F1' AS LABEL, (SELECT COUNT(*) FROM ub JOIN l ON ub.SOURCE = l.F1) AS N
  UNION ALL SELECT 'tmp_label F2', (SELECT COUNT(*) FROM ub JOIN l ON ub.SOURCE = l.F2)
  UNION ALL SELECT 'tmp_label F2_VA', (SELECT COUNT(*) FROM ub JOIN l ON ub.SOURCE = l.F2 AND ub.PRODUCT_V2 = l.F2_VA)
  UNION ALL SELECT 'tmp_label VARIABLE', (SELECT COUNT(*) FROM ub JOIN l ON ub.PRODUCT_V2 = l.VARIABLE)
  UNION ALL SELECT 'tmp_label RILA_VA_TYPE',
                   (SELECT COUNT(*) FROM ssdb_integration.lr_strategy.opp_original o JOIN l ON TO_CHAR(o.va_product_type) = l.RILA_VA_TYPE)
  UNION ALL SELECT 'tmp_f2_channel FILE_DIST_CH ' || m.FILE_DIST_CH, COUNT(f2.FILE_DIST_CH)
            FROM m LEFT JOIN f2 ON f2.FILE_DIST_CH = m.FILE_DIST_CH GROUP BY m.FILE_DIST_CH
  UNION ALL SELECT 'tmp_f2_channel DIST_CH ' || m.DIST_CH, COUNT(u.SOURCE)
            FROM m CROSS JOIN l LEFT JOIN ub u ON u.SOURCE = l.F2 AND u.DIST_CH = m.DIST_CH
            WHERE m.DIST_CH IS NOT NULL GROUP BY m.DIST_CH),
ch AS (    -- as in statement 10
  SELECT u.NEW_DIST, MAX(u.CHANNEL) AS CHANNEL FROM ub u CROSS JOIN l
  WHERE u.SOURCE = l.F1 AND u.NEW_DIST IS NOT NULL
  GROUP BY u.NEW_DIST HAVING COUNT(DISTINCT COALESCE(u.CHANNEL, '~')) = 1),
src AS (   -- union_base as UNION_OPP should carry it, MV: an override changed DIST_CH, so the holder is checked below
  SELECT u.* REPLACE (CASE WHEN u.SOURCE = l.F2 AND u.PRODUCT_V2 = l.F2_VA THEN l.VARIABLE ELSE u.PRODUCT_V2 END AS PRODUCT_V2,
                      CASE WHEN fv.CBD_ID IS NULL THEN u.DIST_CH WHEN u.SOURCE = l.F1 THEN fv.DIST_CH
                           ELSE COALESCE(fv.F2_DIST_CH, u.DIST_CH) END AS DIST_CH,
                      CASE WHEN fv.CBD_ID IS NOT NULL THEN fv.NEW_DIST ELSE u.NEW_DIST END AS NEW_DIST,
                      CASE WHEN fv.CBD_ID IS NOT NULL THEN fc.CHANNEL ELSE u.CHANNEL END AS CHANNEL),
         CASE WHEN fv.CBD_ID IS NULL THEN FALSE WHEN u.SOURCE = l.F1 THEN fv.DIST_CH IS DISTINCT FROM u.DIST_CH
              ELSE COALESCE(fv.F2_DIST_CH, u.DIST_CH) IS DISTINCT FROM u.DIST_CH END AS MV
  FROM ub u CROSS JOIN l
  LEFT JOIN fov fv ON fv.CBD_ID = TO_CHAR(u.CBD_ID)
  LEFT JOIN ch fc ON fc.NEW_DIST = fv.NEW_DIST),
--Row identity: count rows per hash of every column on each side (NULL-safe, keeps duplicates).  A moved row's holder
--columns are left out on both sides, OV marks the companies of tmp_opp_override (their firm_1 MM_OPP changes).
sv AS (SELECT y.* REPLACE (CASE WHEN y.MV THEN NULL ELSE y.TERR_WHOLESALER END AS TERR_WHOLESALER,
                           CASE WHEN y.MV THEN NULL ELSE y.TERR_WHOLESALER_CLEAN_NAME END AS TERR_WHOLESALER_CLEAN_NAME,
                           CASE WHEN y.MV THEN NULL ELSE y.TERRITORY_WHOLESALER_TERRITORY_ID END AS TERRITORY_WHOLESALER_TERRITORY_ID,
                           CASE WHEN y.MV THEN NULL ELSE y.TERRITORY_WHOLESALER_ADDRESS_ID END AS TERRITORY_WHOLESALER_ADDRESS_ID,
                           CASE WHEN y.MV THEN NULL ELSE y.TERRITORY_WHOLESALER_HAS_TERRITORY END AS TERRITORY_WHOLESALER_HAS_TERRITORY),
              CASE WHEN oo.CBD_ID IS NOT NULL THEN 1 ELSE 0 END AS OV
       FROM src y LEFT JOIN oo ON oo.CBD_ID = TO_CHAR(y.CBD_ID)),
uv AS (SELECT y.* REPLACE (CASE WHEN y.HOLDER_MOVED THEN NULL ELSE y.TERR_WHOLESALER END AS TERR_WHOLESALER,
                           CASE WHEN y.HOLDER_MOVED THEN NULL ELSE y.TERR_WHOLESALER_CLEAN_NAME END AS TERR_WHOLESALER_CLEAN_NAME,
                           CASE WHEN y.HOLDER_MOVED THEN NULL ELSE y.TERRITORY_WHOLESALER_TERRITORY_ID END AS TERRITORY_WHOLESALER_TERRITORY_ID,
                           CASE WHEN y.HOLDER_MOVED THEN NULL ELSE y.TERRITORY_WHOLESALER_ADDRESS_ID END AS TERRITORY_WHOLESALER_ADDRESS_ID,
                           CASE WHEN y.HOLDER_MOVED THEN NULL ELSE y.TERRITORY_WHOLESALER_HAS_TERRITORY END AS TERRITORY_WHOLESALER_HAS_TERRITORY),
              CASE WHEN oo.CBD_ID IS NOT NULL THEN 1 ELSE 0 END AS OV
       FROM uo y LEFT JOIN oo ON oo.CBD_ID = TO_CHAR(y.CBD_ID) WHERE y.ROW_ORIGIN <> 'opp file'),
hs AS (SELECT H, MAX(SOURCE) AS SOURCE, COUNT(*) AS N, COUNT(MM_OPP) AS NM, SUM(MM_OPP) AS S, MAX(OV) AS OV
       FROM (SELECT HASH(* EXCLUDE (MM_OPP, MV, OV)) AS H, SOURCE, MM_OPP, OV FROM sv) x GROUP BY H),
hu AS (SELECT H, MAX(SOURCE) AS SOURCE, COUNT(*) AS N, COUNT(MM_OPP) AS NM, SUM(MM_OPP) AS S, MAX(OV) AS OV
       FROM (SELECT HASH(* EXCLUDE (MM_OPP, FIRM_OVERRIDE, HOLDER_MOVED, ROW_ORIGIN, FILE_NEW_DIST, CHANNEL_RULE, N_HOLDERS, FIRM_KEY, FIRM_CRD, CRD_RULE, OPP_OVERRIDE, OV)) AS H, SOURCE, MM_OPP, OV
             FROM uv) x GROUP BY H),
hd AS (SELECT COALESCE(hs.SOURCE, hu.SOURCE) AS SOURCE, COALESCE(hs.OV, hu.OV) AS OV, COALESCE(hs.N, 0) AS NS, COALESCE(hu.N, 0) AS NU,
              COALESCE(hs.NM, 0) AS NMS, COALESCE(hu.NM, 0) AS NMU, COALESCE(hs.S, 0) AS SS, COALESCE(hu.S, 0) AS SU
       FROM hs FULL OUTER JOIN hu ON hu.H = hs.H),
tz AS (SELECT SOURCE, ZIP_CODE, CHANNEL AS DIST_CH, MIN(CLEAN_ID) AS ID
       FROM ssdb_integration.lr_strategy.territories WHERE CLEAN_ID IS NOT NULL GROUP BY SOURCE, ZIP_CODE, CHANNEL),
e AS (SELECT TO_CHAR(firm_crd) AS CRD, TO_CHAR(cbd_id) AS CBD FROM ssdb_integration.lr_strategy.crd_cbd_mm
      UNION SELECT FIRM_CRD, CBD_ID FROM f2),
t2 AS (SELECT SUM(MM_OPP) AS O FROM f2),
xw AS (SELECT * FROM ssdb_integration.lr_strategy.tmp_opp_xwalk),
xs AS (      -- the crosswalk's totals per firm x step
  SELECT FIRM, STEP_NO, SUM(ROWS_BEFORE) AS RB, SUM(ROWS_AFTER) AS RA, SUM(OPP_BEFORE) AS OB, SUM(OPP_AFTER) AS OA
  FROM xw GROUP BY FIRM, STEP_NO),
xe AS (      -- each firm's last step, against UNION_OPP
  SELECT x.FIRM, x.OA, x.RA, SUM(uo.MM_OPP) AS UO, COUNT(uo.MM_OPP) AS UR
  FROM (SELECT * FROM xs QUALIFY STEP_NO = MAX(STEP_NO) OVER (PARTITION BY FIRM)) x
  CROSS JOIN l
  JOIN uo ON uo.SOURCE = CASE WHEN x.FIRM = 'firm_1' THEN l.F1 ELSE l.F2 END
  GROUP BY x.FIRM, x.OA, x.RA),
ck AS (
  SELECT 'inputs: labels in statements 1-2 found in no row (listed below)' AS CHECK_NAME,
         (SELECT COUNT(*) FROM lab WHERE N = 0) AS VALUE, 1 AS MUST_BE_ZERO
  UNION ALL SELECT 'inputs: label found in no row: ' || LABEL, 0, 0 FROM lab WHERE N = 0
  UNION ALL SELECT 'inputs: firm_2 file rows whose channel is not in tmp_f2_channel',
         (SELECT COUNT(*) FROM f2 LEFT JOIN m ON m.FILE_DIST_CH = f2.FILE_DIST_CH WHERE m.FILE_DIST_CH IS NULL), 1
  UNION ALL SELECT 'inputs: crd_dist_override, the same CRD x broker name twice',
         (SELECT COUNT(*) FROM (SELECT firm_crd, broker_name FROM ssdb_integration.lr_strategy.crd_dist_override
                                GROUP BY firm_crd, broker_name HAVING COUNT(*) > 1) x), 1
  UNION ALL SELECT 'inputs: crd_dist_override rows that set no firm_2 row (CRD settled by firm_1, or not in the file)',
         (SELECT COUNT(*) FROM ssdb_integration.lr_strategy.crd_dist_override o
          WHERE NOT EXISTS (SELECT 1 FROM f2 WHERE f2.FIRM_CRD = TO_CHAR(o.firm_crd) AND f2.DIST_SOURCE = 'manual override'
                            AND (o.broker_name IS NULL OR f2.BROKER_NAME = o.broker_name))), 1
  UNION ALL SELECT 'inputs: crd_dist_override rows whose dist_ch is none of firm_1''s for the CRD (a typo, or meant)',
         (SELECT COUNT(*) FROM ssdb_integration.lr_strategy.crd_dist_override o
          WHERE NOT EXISTS (SELECT 1 FROM ssdb_integration.lr_strategy.tmp_f1_crd_dist d
                            WHERE d.FIRM_CRD = TO_CHAR(o.firm_crd) AND d.DIST_CH = TO_CHAR(o.dist_ch))), 0
  UNION ALL SELECT 'inputs: tmp_firm_override companies listed twice',
         (SELECT COUNT(*) FROM (SELECT CBD_ID FROM fov GROUP BY CBD_ID HAVING COUNT(*) > 1) x), 1
  UNION ALL SELECT 'inputs: tmp_firm_override companies firm_2 has rows or opportunity of, with no F2_DIST_CH',
         (SELECT COUNT(*) FROM fov
          WHERE fov.F2_DIST_CH IS NULL
            AND (EXISTS (SELECT 1 FROM ub JOIN l ON ub.SOURCE = l.F2 WHERE TO_CHAR(ub.CBD_ID) = fov.CBD_ID)
                 OR EXISTS (SELECT 1 FROM f2 LEFT JOIN m ON m.FILE_DIST_CH = f2.FILE_DIST_CH
                            WHERE f2.CBD_ID = fov.CBD_ID AND (m.FILE_DIST_CH IS NULL OR m.DIST_CH IS NOT NULL)))), 1
  UNION ALL SELECT 'inputs: tmp_opp_override companies listed twice',
         (SELECT COUNT(*) FROM (SELECT CBD_ID FROM ssdb_integration.lr_strategy.tmp_opp_override
                                GROUP BY CBD_ID HAVING COUNT(*) > 1) x), 1
  UNION ALL SELECT 'inputs: tmp_opp_override companies with no firm_2 MM_OPP (firm_1 would be left none)',
         (SELECT COUNT(*) FROM oo WHERE NOT EXISTS (SELECT 1 FROM uo JOIN l ON uo.SOURCE = l.F2
                                                    WHERE TO_CHAR(uo.CBD_ID) = oo.CBD_ID AND COALESCE(uo.MM_OPP, 0) <> 0)), 1
  UNION ALL SELECT 'inputs: union_base CBD_IDs with 2+ FIRM in one SOURCE',
         (SELECT COUNT(*) FROM (SELECT CBD_ID, SOURCE FROM ub WHERE CBD_ID IS NOT NULL
                                GROUP BY CBD_ID, SOURCE HAVING COUNT(DISTINCT FIRM) > 1) x), 1
  UNION ALL SELECT 'inputs: union_base firm_2 rows carrying MM_OPP (union_base is the union without firm_2 opportunity)',
         (SELECT COUNT(*) FROM ub JOIN l ON ub.SOURCE = l.F2 WHERE ub.MM_OPP IS NOT NULL), 1
  UNION ALL SELECT 'inputs: SOURCEs with no FIXED row in union_base',
         2 - (SELECT COUNT(DISTINCT ub.SOURCE) FROM ub JOIN l ON ub.SOURCE IN (l.F1, l.F2) WHERE ub.PRODUCT_V2 = 'FIXED'), 1
  UNION ALL SELECT 'inputs: union_base PRODUCT_V2, ' || SOURCE || ': ' || LISTAGG(DISTINCT PRODUCT_V2, ', ') WITHIN GROUP (ORDER BY PRODUCT_V2),
         COUNT(DISTINCT PRODUCT_V2), 0 FROM ub GROUP BY SOURCE
  UNION ALL SELECT 'inputs: firm_2 union_base DIST_CH: ' || LISTAGG(DISTINCT ub.DIST_CH, ', ') WITHIN GROUP (ORDER BY ub.DIST_CH),
         COUNT(DISTINCT ub.DIST_CH), 0 FROM ub JOIN l ON ub.SOURCE = l.F2
  UNION ALL SELECT 'inputs: opp_original DIST_CH: ' || LISTAGG(DISTINCT TO_CHAR(o.dist_ch), ', ') WITHIN GROUP (ORDER BY TO_CHAR(o.dist_ch)),
         COUNT(DISTINCT o.dist_ch), 0 FROM ssdb_integration.lr_strategy.opp_original o
  UNION ALL SELECT 'inputs: opp_original VA_PRODUCT_TYPE: ' || LISTAGG(DISTINCT TO_CHAR(o.va_product_type), ', ') WITHIN GROUP (ORDER BY TO_CHAR(o.va_product_type)),
         COUNT(DISTINCT o.va_product_type), 0 FROM ssdb_integration.lr_strategy.opp_original o
  UNION ALL SELECT 'firm_2 file: rows in opp_original minus rows in tmp_f2_opp',
         (SELECT COUNT(*) FROM ssdb_integration.lr_strategy.opp_original) - (SELECT COUNT(*) FROM f2), 1
  UNION ALL SELECT 'firm_2 file: OPP in opp_original minus OPP in tmp_f2_opp',
         ROUND((SELECT SUM(opp) FROM ssdb_integration.lr_strategy.opp_original) - (SELECT O FROM t2), 2), 1
  UNION ALL SELECT 'firm_2 file: % of OPP with no product (no branch of your query''s product rule)',
         ROUND(100 * COALESCE((SELECT SUM(MM_OPP) FROM f2 WHERE PRODUCT_V2 IS NULL), 0) / (SELECT O FROM t2), 2), 1
  UNION ALL SELECT 'firm_2 file: % of OPP with no company (dropped, as your query drops firm_1''s)',
         ROUND(100 * COALESCE((SELECT SUM(MM_OPP) FROM f2 WHERE CBD_ID IS NULL), 0) / (SELECT O FROM t2), 2), 0
  UNION ALL SELECT 'firm_2 file: % of OPP dropped as NO CHANNEL',
         ROUND(100 * COALESCE((SELECT SUM(f2.MM_OPP) FROM f2 JOIN m ON m.FILE_DIST_CH = f2.FILE_DIST_CH
                               WHERE m.DIST_CH IS NULL), 0) / (SELECT O FROM t2), 2), 0
  UNION ALL SELECT 'firm_2 file: % of OPP whose dist_ch is from ' || COALESCE(DIST_SOURCE, 'nowhere (statement 13 lists the CRDs)'),
         ROUND(100 * SUM(MM_OPP) / MAX(t2.O), 2), 0 FROM f2 CROSS JOIN t2 GROUP BY DIST_SOURCE
  UNION ALL SELECT 'firm key: links whose CRD and CBD_ID have different FIRM_KEY (six passes not enough)',
         (SELECT COUNT(*) FROM e JOIN fk a ON a.ID_TYPE = 'CRD' AND a.ID = e.CRD JOIN fk b ON b.ID_TYPE = 'CBD_ID' AND b.ID = e.CBD
          WHERE a.FIRM_KEY <> b.FIRM_KEY), 1
  UNION ALL SELECT 'firm key: IDs on 2+ rows of tmp_firm_key',
         (SELECT COUNT(*) FROM (SELECT ID_TYPE, ID FROM fk GROUP BY ID_TYPE, ID HAVING COUNT(*) > 1) x), 1
  UNION ALL SELECT 'firm key: FIRM_KEYs joining 2+ CBD_IDs (statement 14)', (SELECT COUNT(DISTINCT FIRM_KEY) FROM fk WHERE N_CBD > 1), 0
  UNION ALL SELECT 'firm key: FIRM_KEYs for review (2+ PARENT)', (SELECT COUNT(DISTINCT FIRM_KEY) FROM fk WHERE KEY_REVIEW IS NOT NULL), 0
  UNION ALL SELECT 'UNION_OPP: union_base rows not found unchanged (but MM_OPP), or rows added or repeated',
         (SELECT SUM(ABS(NS - NU)) FROM hd), 1
  UNION ALL SELECT 'UNION_OPP: firm_1 rows whose MM_OPP changed, companies not in tmp_opp_override',
         (SELECT COUNT(*) FROM hd JOIN l ON hd.SOURCE = l.F1 WHERE hd.OV = 0
            AND (NS <> NU OR NMS <> NMU OR ABS(SS - SU) > 1e-9 * GREATEST(ABS(SS), ABS(SU), 1))), 1
  UNION ALL SELECT 'opportunity: ' || b.FIRM || ', steps whose rows or opportunity before differ from the step before''s after',
         SUM(CASE WHEN b.RB <> a.RA OR ABS(b.OB - a.OA) > 1e-6 * GREATEST(ABS(a.OA), 1) THEN 1 ELSE 0 END), 1
         FROM xs b JOIN xs a ON a.FIRM = b.FIRM AND a.STEP_NO = b.STEP_NO - 1 GROUP BY b.FIRM
  UNION ALL SELECT 'opportunity: ' || FIRM || ', crosswalk rows breaking their step''s CHANGES',
         SUM(CASE WHEN (CHANGES = 'nothing' AND (ROWS_BEFORE <> ROWS_AFTER
                                                OR ABS(OPP_BEFORE - OPP_AFTER) > 1e-6 * GREATEST(ABS(OPP_BEFORE), 1)))
                    OR (CHANGES = 'drops' AND NOT ((ROWS_AFTER = ROWS_BEFORE AND ABS(OPP_BEFORE - OPP_AFTER) <= 1e-6 * GREATEST(ABS(OPP_BEFORE), 1))
                                                   OR (ROWS_AFTER = 0 AND OPP_AFTER = 0)))
                    OR (CHANGES = 'regroups' AND ABS(OPP_BEFORE - OPP_AFTER) > 1e-6 * GREATEST(ABS(OPP_BEFORE), 1))
                    OR (CHANGES = 'amounts' AND TO_VALUE = 'unchanged'
                        AND (ROWS_BEFORE <> ROWS_AFTER OR ABS(OPP_BEFORE - OPP_AFTER) > 1e-6 * GREATEST(ABS(OPP_BEFORE), 1)))
                    OR TO_VALUE = 'no UNION_OPP row' THEN 1 ELSE 0 END), 1
         FROM xw GROUP BY FIRM
  UNION ALL SELECT 'opportunity: ' || FIRM || ', last step''s rows or opportunity differ from UNION_OPP''s',
         CASE WHEN RA <> UR OR ABS(OA - UO) > 1e-6 * GREATEST(ABS(UO), 1) THEN 1 ELSE 0 END, 1 FROM xe
  UNION ALL SELECT 'opportunity: ' || xe.FIRM || ', % of the source''s opportunity in UNION_OPP',
         ROUND(100 * xe.UO / s0.OB, 2), 0 FROM xe JOIN xs s0 ON s0.FIRM = xe.FIRM AND s0.STEP_NO = 0
  UNION ALL SELECT 'UNION_OPP: rows with a CBD_ID and no FIRM_KEY', (SELECT COUNT(*) FROM uo WHERE CBD_ID IS NOT NULL AND FIRM_KEY IS NULL), 1
  UNION ALL SELECT 'UNION_OPP: firm_2 opportunity keys carrying MM_OPP on 2+ rows (opp-only rows: key x NEW_DIST x CRD)',
         (SELECT COUNT(*) FROM (SELECT 1 FROM uo JOIN l ON uo.SOURCE = l.F2
                                WHERE uo.ROW_ORIGIN <> 'union' AND uo.MM_OPP IS NOT NULL
                                GROUP BY uo.ZIP_CODE, uo.DIST_CH, uo.CBD_ID, uo.PRODUCT_V2,
                                         CASE WHEN uo.ROW_ORIGIN = 'opp file' THEN uo.NEW_DIST END,
                                         CASE WHEN uo.ROW_ORIGIN = 'opp file' THEN uo.FIRM_CRD END
                                HAVING COUNT(*) > 1) x), 1
  UNION ALL SELECT 'UNION_OPP: opp-only rows with NULL DIST_CH, PRODUCT_V2 or NEW_DIST',
         (SELECT COUNT(*) FROM oc WHERE DIST_CH IS NULL OR PRODUCT_V2 IS NULL OR NEW_DIST IS NULL), 1
  UNION ALL SELECT 'UNION_OPP: opp-only rows with no CHANNEL (pending your CHANNEL step)', (SELECT COUNT(*) FROM oc WHERE CHANNEL IS NULL), 1
  UNION ALL SELECT 'UNION_OPP: opp-only rows with no FIRM_CRD', (SELECT COUNT(*) FROM oc WHERE FIRM_CRD IS NULL), 1
  UNION ALL SELECT 'UNION_OPP: opp-only rows with a holder and no TERR_WHOLESALER or SALES_WHOLESALER',
         (SELECT COUNT(*) FROM oc WHERE N_HOLDERS > 0 AND (TERR_WHOLESALER IS NULL OR SALES_WHOLESALER IS NULL)), 1
  UNION ALL SELECT 'UNION_OPP: firm override rows without its NEW_DIST, or with no CHANNEL',
         (SELECT COUNT(*) FROM uo JOIN fov ON fov.CBD_ID = TO_CHAR(uo.CBD_ID)
          WHERE uo.NEW_DIST IS DISTINCT FROM fov.NEW_DIST OR uo.CHANNEL IS NULL), 1
  UNION ALL SELECT 'UNION_OPP: firm override rows without its DIST_CH (firm_1) or F2_DIST_CH (firm_2)',
         (SELECT COUNT(*) FROM uo CROSS JOIN l JOIN fov ON fov.CBD_ID = TO_CHAR(uo.CBD_ID)
          WHERE (uo.SOURCE = l.F1 AND uo.DIST_CH IS DISTINCT FROM fov.DIST_CH)
             OR (uo.SOURCE = l.F2 AND fov.F2_DIST_CH IS NOT NULL AND uo.DIST_CH IS DISTINCT FROM fov.F2_DIST_CH)), 1
  UNION ALL SELECT 'UNION_OPP: firm override rows not marked FIRM_OVERRIDE',
         (SELECT COUNT(*) FROM uo JOIN fov ON fov.CBD_ID = TO_CHAR(uo.CBD_ID) WHERE uo.FIRM_OVERRIDE IS NULL), 1
  UNION ALL SELECT 'UNION_OPP: moved rows whose holder is not the territories holder of their ZIP_CODE x DIST_CH, or unnamed',
         (SELECT COUNT(*) FROM uo LEFT JOIN tz ON tz.SOURCE = uo.SOURCE AND tz.ZIP_CODE = uo.ZIP_CODE AND tz.DIST_CH = uo.DIST_CH
          WHERE uo.HOLDER_MOVED
            AND (uo.TERRITORY_WHOLESALER_TERRITORY_ID IS DISTINCT FROM tz.ID
                 OR uo.TERRITORY_WHOLESALER_HAS_TERRITORY <> CASE WHEN tz.ID IS NOT NULL THEN 1 ELSE 0 END
                 OR (tz.ID IS NOT NULL AND (uo.TERR_WHOLESALER IS NULL OR uo.TERR_WHOLESALER_CLEAN_NAME IS NULL)))), 1
  UNION ALL SELECT 'UNION_OPP: tmp_opp_override ZIP_CODE x PRODUCT_V2 cells where firm_1 MM_OPP differs from firm_2''s',
         (SELECT COUNT(*) FROM (SELECT uo.ZIP_CODE, uo.CBD_ID, uo.PRODUCT_V2,
                                       COALESCE(SUM(CASE WHEN uo.SOURCE = l.F1 THEN uo.MM_OPP END), 0) AS O1,
                                       COALESCE(SUM(CASE WHEN uo.SOURCE = l.F2 THEN uo.MM_OPP END), 0) AS O2
                                FROM uo CROSS JOIN l JOIN oo ON oo.CBD_ID = TO_CHAR(uo.CBD_ID)
                                GROUP BY uo.ZIP_CODE, uo.CBD_ID, uo.PRODUCT_V2) x
          WHERE ABS(O1 - O2) > 1e-6 * GREATEST(ABS(O1), ABS(O2), 1)), 1
  UNION ALL SELECT 'UNION_OPP: tmp_opp_override firm_1 rows carrying MM_OPP and not marked OPP_OVERRIDE',
         (SELECT COUNT(*) FROM uo CROSS JOIN l JOIN oo ON oo.CBD_ID = TO_CHAR(uo.CBD_ID)
          WHERE uo.SOURCE = l.F1 AND uo.MM_OPP IS NOT NULL AND uo.OPP_OVERRIDE IS NULL), 1
  UNION ALL SELECT 'UNION_OPP: rows, ' || SOURCE || ' ' || ROW_ORIGIN, COUNT(*), 0 FROM uo GROUP BY SOURCE, ROW_ORIGIN
  UNION ALL SELECT 'UNION_OPP: % of ' || uo.SOURCE || ' MM_OPP on ' || uo.ROW_ORIGIN || ' rows',
         ROUND(100 * SUM(uo.MM_OPP) / MAX(t.O), 1), 0
         FROM uo JOIN (SELECT SOURCE, SUM(MM_OPP) AS O FROM uo GROUP BY SOURCE) t ON t.SOURCE = uo.SOURCE
         WHERE uo.MM_OPP IS NOT NULL GROUP BY uo.SOURCE, uo.ROW_ORIGIN
  UNION ALL SELECT 'UNION_OPP: opp-only rows with no territory holder, ' || SOURCE, COUNT(*), 0 FROM oc WHERE N_HOLDERS = 0 GROUP BY SOURCE
  UNION ALL SELECT 'UNION_OPP: rows changed by a firm override, ' || SOURCE, COUNT(*), 0 FROM uo WHERE FIRM_OVERRIDE GROUP BY SOURCE
  UNION ALL SELECT 'UNION_OPP: rows whose holder moved with a firm override, ' || SOURCE, COUNT(*), 0 FROM uo WHERE HOLDER_MOVED GROUP BY SOURCE
  UNION ALL SELECT 'UNION_OPP: moved rows into a ZIP_CODE x DIST_CH with 2+ holders (lowest CLEAN_ID taken)',
         (SELECT COUNT(*) FROM uo WHERE HOLDER_MOVED AND N_HOLDERS > 1), 0
  UNION ALL SELECT 'UNION_OPP: moved rows into a ZIP_CODE x DIST_CH with no holder', (SELECT COUNT(*) FROM uo WHERE HOLDER_MOVED AND N_HOLDERS = 0), 0
  UNION ALL SELECT 'UNION_OPP: firm_2 rows of tmp_firm_override companies by DIST_CH (to choose F2_DIST_CH): ' || TO_CHAR(ub.CBD_ID)
                   || ' ' || COALESCE(ub.DIST_CH, 'NULL'), COUNT(*), 0
         FROM ub JOIN l ON ub.SOURCE = l.F2 JOIN fov ON fov.CBD_ID = TO_CHAR(ub.CBD_ID) GROUP BY TO_CHAR(ub.CBD_ID), ub.DIST_CH
  UNION ALL SELECT 'UNION_OPP: firm_1 rows by OPP_OVERRIDE: ' || OPP_OVERRIDE, COUNT(*), 0 FROM uo WHERE OPP_OVERRIDE IS NOT NULL GROUP BY OPP_OVERRIDE)
SELECT CHECK_NAME, VALUE, MUST_BE_ZERO FROM ck ORDER BY MUST_BE_ZERO DESC, CHECK_NAME;
