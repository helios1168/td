use secondary roles all;

--UNION_OPP and everything it needs, in one file: open it in a worksheet and Run All.  Each result is in Query history;
--the last one is the checks grid (statement 14).  To see a review list or report alone, put the cursor in it and Run.
--Needs at work: union_base, opp_original, crd_cbd_mm, crd_cbd, territories, synthetic_key, the vendor table, and the
--owner's manual dist_ch in crd_dist_override (statement 1 keeps it).  The firm overrides are the list in statement 2.
--   1  crd_dist_override (created once, never replaced)     2  tmp_firm_override (the firm overrides list)
--   3  tmp_opp_base_both    4  tmp_opp_f2_final    5  tmp_firm_key    6  UNION_OPP (the one table kept)
--   7  dist_ch by firm_2's own channel     8  dist_ch review list     9  new_dist against firm_1's
--  10  firm keys joining 2+ CBD_IDs       11  firm_2 MM_OPP by DIST_CH x NEW_DIST x CHANNEL
--  12  opportunity alignment by ZIP x firm   13  firm keys with the largest gaps   14  checks
--Statements 2-5 make temporary tables (tmp_*): they last until the session ends, and only UNION_OPP is kept
--(owner, 2026-10-26).  crd_dist_override stays a permanent table: it holds the owner's loaded overrides, an input.
--The reports (7-13) and the checks (14) read the tmp_ tables, so they run in the session of the builds: Run All does
--that; run one alone right after it, and if it says a tmp_ table does not exist, Run All again.
--
--firm_2's opportunity file through the opportunity steps of the firm_1 query (mm_query.sql, opp_base .. opp_final).
--The steps are copied as written; every change is marked --f2:.  In the repo by the owner's permission (2026-10-25).
--firm_2's file has no company, client firm ID or state: each firm_2 row takes them from firm_1's vendor rows of the
--same ZIP x CRD x broker name x product, else of the same ZIP x CRD x broker name, else crd_cbd_mm (company only).
--dist_ch: firm_2's file names its channels differently from the vendor table, so a firm_2 row takes the dist_ch the
--query gives firm_1's rows of the same CRD, when they all carry one; otherwise DIST_REVIEW says why and dist_ch is
--blank, for manual review (owner, 2026-10-25).  The owner's manual dist_ch (crd_dist_override, statement 1) fills
--those rows; it never overrules a CRD firm_1 gives one dist_ch.  DIST_SOURCE says which.  firm_2's own channel stays
--in FILE_DIST_CH.

--Statement 1.  Once, then fill it (Snowsight "Load data" from a CSV with these three headers, or INSERT ... VALUES).
--One row per CRD (BROKER_NAME blank: every broker name of the CRD) or per CRD x broker name (wins over the blank
--row).  DIST_CH as the query writes firm_1's (the labels in the dist_ch review list, statement 8).
CREATE TABLE IF NOT EXISTS ssdb_integration.lr_strategy.crd_dist_override (FIRM_CRD VARCHAR, BROKER_NAME VARCHAR, DIST_CH VARCHAR);

--Statement 2.  The firm overrides (owner, 2026-10-26): every row of the company, both firms, gets this DIST_CH and
--NEW_DIST (in tmp_opp_f2_final and UNION_OPP, where CHANNEL follows NEW_DIST and firm_2's union rows keep their own
--DIST_CH).  One line per CBD_ID, e.g. ('46', 'FI', 'FI'), ('123', 'WH', 'WH'); change it here and Run All.
CREATE OR REPLACE TEMPORARY TABLE ssdb_integration.lr_strategy.tmp_firm_override AS
SELECT CBD_ID, DIST_CH, NEW_DIST
FROM (VALUES ('46', 'FI', 'FI')) v(CBD_ID, DIST_CH, NEW_DIST);

--Statement 3.
CREATE OR REPLACE TEMPORARY TABLE ssdb_integration.lr_strategy.tmp_opp_base_both AS (
WITH
f2 AS (   --f2: firm_2's file; RILA is a VA type there (settled map, V02 -> PR01) but a product line in the vendor table
    SELECT o.*,
        CASE WHEN TO_CHAR(o.va_product_type) = rila.VALUE THEN 'RILA' ELSE TO_CHAR(o.product_line) END AS pl_vendor,
        LPAD(TRIM(TO_CHAR(o.zip_code)), 5, '0') AS zip5
    FROM ssdb_integration.lr_strategy.opp_original o
    CROSS JOIN (SELECT VALUE FROM ssdb_integration.lr_strategy.synthetic_key WHERE KIND = 'VA_TYPE' AND CODE = 'V02') rila
),

product_map AS (   --f2: the query's product CASE once per product line x VA type, so both firms meet at the same product
    SELECT product_line AS pl, va_product_type AS va,
        CASE WHEN va_product_type = 'IOVA' then 'IOVA'
                WHEN product_line = 'VA' THEN 'VARIABLE'
                WHEN product_line = 'IA' THEN 'INDEX'
                WHEN product_line = 'FA' THEN 'FIXED'
                WHEN product_line = 'RILA' THEN 'RILA'
            END AS product
    FROM (SELECT DISTINCT TO_CHAR(product_line) AS product_line, TO_CHAR(va_product_type) AS va_product_type FROM life_prod.lif_murkylake.wc_market_metrics_opportunity
          UNION
          SELECT DISTINCT pl_vendor, TO_CHAR(va_product_type) FROM f2)
),

vendor_g AS (   --f2: firm_1's vendor rows (fiscal years of the query) by ZIP x CRD x broker name x product
    SELECT LPAD(TRIM(TO_CHAR(zip_code)), 5, '0') AS zip_code, TO_CHAR(v.firm_crd) AS firm_crd, v.broker_name, pm.product,
        TO_CHAR(v.cbd_id) AS cbd_id, TO_CHAR(v.client_firm_id) AS client_firm_id, SUM(v.global_sales) AS opp
    FROM life_prod.lif_murkylake.wc_market_metrics_opportunity v
    JOIN product_map pm ON pm.pl IS NOT DISTINCT FROM TO_CHAR(v.product_line)
                       AND pm.va IS NOT DISTINCT FROM TO_CHAR(v.va_product_type)
    WHERE TO_CHAR(v.fiscal_yr) IN ('2024', '2025')
    GROUP BY LPAD(TRIM(TO_CHAR(zip_code)), 5, '0'), TO_CHAR(v.firm_crd), v.broker_name, pm.product, TO_CHAR(v.cbd_id), TO_CHAR(v.client_firm_id)
),

vendor_cell AS (   --f2: per ZIP x CRD x broker name x product, the company carrying most opportunity; N_CO = how many companies
    SELECT zip_code, firm_crd, broker_name, product, cbd_id, client_firm_id, n_co
    FROM (
        SELECT zip_code, firm_crd, broker_name, product, cbd_id, client_firm_id
            , COUNT(*) OVER (PARTITION BY zip_code, firm_crd, broker_name, product) AS n_co
            , ROW_NUMBER() OVER (PARTITION BY zip_code, firm_crd, broker_name, product ORDER BY opp DESC, cbd_id, client_firm_id) AS rk
        FROM (SELECT zip_code, firm_crd, broker_name, product, cbd_id, client_firm_id, SUM(opp) AS opp
              FROM vendor_g GROUP BY zip_code, firm_crd, broker_name, product, cbd_id, client_firm_id)
    )
    WHERE rk = 1
),

vendor_key AS (   --f2: the same per ZIP x CRD x broker name, for a product firm_1 has no row of there
    SELECT zip_code, firm_crd, broker_name, cbd_id, client_firm_id, n_co
    FROM (
        SELECT zip_code, firm_crd, broker_name, cbd_id, client_firm_id
            , COUNT(*) OVER (PARTITION BY zip_code, firm_crd, broker_name) AS n_co
            , ROW_NUMBER() OVER (PARTITION BY zip_code, firm_crd, broker_name ORDER BY opp DESC, cbd_id, client_firm_id) AS rk
        FROM (SELECT zip_code, firm_crd, broker_name, cbd_id, client_firm_id, SUM(opp) AS opp
              FROM vendor_g GROUP BY zip_code, firm_crd, broker_name, cbd_id, client_firm_id)
    )
    WHERE rk = 1
),

mm_co AS (   --f2: no vendor row at that ZIP: crd_cbd_mm, the company carrying most opportunity of the CRD x broker name
    SELECT firm_crd, broker_name, cbd_id
    FROM (
        SELECT TO_CHAR(firm_crd) AS firm_crd, broker_name, TO_CHAR(cbd_id) AS cbd_id
            , ROW_NUMBER() OVER (PARTITION BY TO_CHAR(firm_crd), broker_name ORDER BY mm_opp DESC, TO_CHAR(cbd_id)) AS rk
        FROM ssdb_integration.lr_strategy.crd_cbd_mm
    )
    WHERE rk = 1
),

zip_state AS (   --f2: the vendor's state of a ZIP (firm_2's file has none)
    SELECT LPAD(TRIM(TO_CHAR(zip_code)), 5, '0') AS zip_code, MAX(TO_CHAR(state)) AS state
    FROM life_prod.lif_murkylake.wc_market_metrics_opportunity
    GROUP BY LPAD(TRIM(TO_CHAR(zip_code)), 5, '0')
),

opp_source AS (   --f2: both firms' rows in the vendor table's columns, all text but the amount (stacked types must match)
    SELECT 'firm_1' AS src,
        TO_CHAR(product_line) AS product_line, TO_CHAR(va_product_type) AS va_product_type,
        TO_CHAR(cbd_id) AS cbd_id, TO_CHAR(client_firm_id) AS client_firm_id, TO_CHAR(firm_crd) AS firm_crd,
        broker_name, TO_CHAR(dist_ch) AS dist_ch, TO_CHAR(fiscal_yr) AS fiscal_yr, TO_CHAR(zip_code) AS zip_code,
        TO_CHAR(state) AS state, global_sales, TO_CHAR(territory) AS territory,
        TO_CHAR(dist_ch) AS file_dist_ch, TO_CHAR(product_line) AS file_product_line,
        TO_CHAR(va_product_type) AS file_va_type, 'vendor' AS cbd_method, 1 AS n_co
    FROM life_prod.lif_murkylake.wc_market_metrics_opportunity
    UNION ALL
    SELECT 'firm_2',
        f.pl_vendor, TO_CHAR(f.va_product_type),
        CASE WHEN c.zip_code IS NOT NULL THEN c.cbd_id WHEN k.zip_code IS NOT NULL THEN k.cbd_id ELSE m.cbd_id END,
        CASE WHEN c.zip_code IS NOT NULL THEN c.client_firm_id WHEN k.zip_code IS NOT NULL THEN k.client_firm_id END,
        TO_CHAR(f.firm_crd), f.broker_name,
        TO_CHAR(f.dist_ch),   --replaced after opp_base by firm_1's dist_ch of the CRD
        '2025', f.zip5, st.state, f.opp, CAST(NULL AS VARCHAR),
        TO_CHAR(f.dist_ch), TO_CHAR(f.product_line), TO_CHAR(f.va_product_type),
        CASE WHEN c.zip_code IS NOT NULL THEN 'vendor cell' WHEN k.zip_code IS NOT NULL THEN 'vendor ZIP x CRD x broker'
             WHEN m.cbd_id IS NOT NULL THEN 'crd_cbd_mm' END,
        COALESCE(c.n_co, k.n_co)
    FROM f2 f
    JOIN product_map pm ON pm.pl IS NOT DISTINCT FROM f.pl_vendor AND pm.va IS NOT DISTINCT FROM TO_CHAR(f.va_product_type)
    LEFT JOIN vendor_cell c
        ON c.zip_code = f.zip5 AND c.firm_crd = TO_CHAR(f.firm_crd) AND c.broker_name = f.broker_name AND c.product = pm.product
    LEFT JOIN vendor_key k
        ON k.zip_code = f.zip5 AND k.firm_crd = TO_CHAR(f.firm_crd) AND k.broker_name = f.broker_name
    LEFT JOIN mm_co m ON m.firm_crd = TO_CHAR(f.firm_crd) AND m.broker_name = f.broker_name
    LEFT JOIN zip_state st ON st.zip_code = f.zip5
),
opp_base AS (
    SELECT CASE WHEN va_product_type = 'IOVA' then 'IOVA'
            WHEN product_line = 'VA' THEN 'VARIABLE'
            WHEN product_line = 'IA' THEN 'INDEX'
            WHEN product_line = 'FA' THEN 'FIXED'
            WHEN product_line = 'RILA' THEN 'RILA'
        END AS product_line,
        CASE WHEN TO_CHAR(cbd_id) IN ('1993', '685') THEN 'PRI'
            WHEN TO_CHAR(cbd_id) = '805' THEN 'AMER'
            WHEN broker_name IN ('Wells Fargo Clearing Services, LLC',
                'First Command Brokerage Services, Inc.') THEN 'WH'
            WHEN broker_name = 'Mercer Allied Company, L.P.' THEN 'IFA'
            WHEN broker_name IN ('TD Securities (USA) LLC',
                'Woodmen Financial Services, Inc.',
                'United Brokerage Services, Inc',
                'Frost Brokerage Services, Inc.') THEN 'FI'
            WHEN dist_ch = 'EDWARD JONES' THEN 'EDJ'
            ELSE dist_ch
        END AS dist_ch,
        TO_CHAR(fiscal_yr) AS fiscal_yr,
        TO_CHAR(zip_code) AS zip_code,
        state,
        global_sales,
        TO_CHAR(firm_crd) AS firm_crd,   --CRD: carried to opp_resolved, attached at the end by cbd_id
        broker_name,
        CASE WHEN broker_name = 'Wells Fargo Clearing Services, LLC' THEN '1822'
            WHEN broker_name = 'Wells Fargo Clearing Services, LLC - BANK' THEN '1823'
            WHEN TO_CHAR(cbd_id) = '0' AND client_firm_id IS NOT NULL THEN TO_CHAR(client_firm_id)
            WHEN TO_CHAR(cbd_id) = '0' THEN NULL
            ELSE TO_CHAR(cbd_id)
        END AS original_cbd_id,
        territory,
        src, file_dist_ch, file_product_line, file_va_type, cbd_method, n_co   --f2: carried for the checks
    FROM opp_source
    WHERE TO_CHAR(fiscal_yr) IN ('2024', '2025')
),

crd_dist AS (   --f2: the dist_ch the query gives firm_1's rows of each CRD; N_DIST = how many (a blank counts as one)
    SELECT firm_crd AS crd, MAX(dist_ch) AS f1_dist_ch, COUNT(DISTINCT COALESCE(dist_ch, '~')) AS n_dist
    FROM opp_base
    WHERE src = 'firm_1'
    GROUP BY firm_crd
),

ov AS (   --f2: the owner's manual dist_ch (crd_dist_override)
    SELECT TO_CHAR(firm_crd) AS ov_crd, broker_name AS ov_broker, TO_CHAR(dist_ch) AS ov_dist_ch
    FROM ssdb_integration.lr_strategy.crd_dist_override
)

SELECT b.* EXCLUDE (dist_ch),
    CASE WHEN b.src = 'firm_1' THEN b.dist_ch
         WHEN c.n_dist = 1 AND c.f1_dist_ch IS NOT NULL THEN c.f1_dist_ch
         ELSE COALESCE(ob.ov_dist_ch, oc.ov_dist_ch) END AS dist_ch,   --f2: firm_1's by CRD, else the manual one
    CASE WHEN b.src = 'firm_1' THEN NULL
         WHEN c.n_dist = 1 AND c.f1_dist_ch IS NOT NULL THEN 'firm_1 CRD'
         WHEN COALESCE(ob.ov_dist_ch, oc.ov_dist_ch) IS NOT NULL THEN 'manual override' END AS dist_source,
    CASE WHEN b.src = 'firm_1' OR (c.n_dist = 1 AND c.f1_dist_ch IS NOT NULL)
              OR COALESCE(ob.ov_dist_ch, oc.ov_dist_ch) IS NOT NULL THEN NULL
         WHEN c.crd IS NULL THEN 'no firm_1 rows for the CRD'
         WHEN c.n_dist > 1 THEN 'firm_1 rows of the CRD carry 2+ dist_ch'
         ELSE 'firm_1 rows of the CRD have a blank dist_ch' END AS dist_review
FROM opp_base b
LEFT JOIN crd_dist c ON c.crd = b.firm_crd AND b.src = 'firm_2'
LEFT JOIN ov ob ON ob.ov_crd = b.firm_crd AND ob.ov_broker = b.broker_name AND b.src = 'firm_2'
LEFT JOIN ov oc ON oc.ov_crd = b.firm_crd AND oc.ov_broker IS NULL AND b.src = 'firm_2'
);

--Statement 4.
CREATE OR REPLACE TEMPORARY TABLE ssdb_integration.lr_strategy.tmp_opp_f2_final AS (
WITH
opp_base AS (SELECT * FROM ssdb_integration.lr_strategy.tmp_opp_base_both WHERE src = 'firm_2'),

sales_keys AS (   --f2: firm_2's sales, from union_base (firm_1's come from its sales table); its VA as VARIABLE (owner, 2026-10-26, Q8)
    SELECT DISTINCT
        TO_CHAR(u.fiscal_yr) AS fiscal_yr,
        LPAD(TRIM(TO_CHAR(u.zip_code)), 5, '0') AS zip_code,
        TO_CHAR(u.cbd_id) AS cbd_id,
        CASE WHEN u.product_v2 = va.VALUE THEN vr.VALUE ELSE u.product_v2 END AS product_v2,
        u.state
    FROM ssdb_integration.lr_strategy.union_base u
    JOIN ssdb_integration.lr_strategy.synthetic_key s ON s.KIND = 'SOURCE' AND s.CODE = 'firm_2' AND s.VALUE = u.source
    CROSS JOIN (SELECT VALUE FROM ssdb_integration.lr_strategy.synthetic_key WHERE KIND = 'PRODUCT_V2' AND CODE = 'PR05') va
    CROSS JOIN (SELECT VALUE FROM ssdb_integration.lr_strategy.synthetic_key WHERE KIND = 'PRODUCT_V2' AND CODE = 'PR02') vr
),

opp_grouped AS (
    SELECT
        product_line,
        dist_ch,
        fiscal_yr,
        zip_code,
        state,
        original_cbd_id,
        territory,
        firm_crd,
        broker_name,
        file_dist_ch,   --f2: firm_2's own channel, carried to the end so NO CHANNEL can be dropped later
        SUM(global_sales) AS mm_opp
    FROM opp_base
    WHERE original_cbd_id IS NOT NULL
    GROUP BY
        product_line,
        dist_ch,
        fiscal_yr,
        zip_code,
        state,
        original_cbd_id,
        territory,
        firm_crd,
        broker_name,
        file_dist_ch
),

opp_split AS (
    SELECT
        o.product_line,
        o.dist_ch,
        o.fiscal_yr,
        o.zip_code,
        o.state,
        o.original_cbd_id,
        o.mm_opp,
        territory,
        o.firm_crd,
        o.broker_name,
        o.file_dist_ch,
        TRIM(f.value::VARCHAR) AS candidate_cbd_id,
        f.index AS split_position
    FROM opp_grouped o,
    LATERAL FLATTEN(
        INPUT => SPLIT(o.original_cbd_id, '|')
    ) f
),

opp_matches AS (
    SELECT
        os.product_line,
        os.dist_ch,
        os.fiscal_yr,
        os.zip_code,
        os.state,
        os.original_cbd_id,
        os.mm_opp,
        os.candidate_cbd_id,
        os.split_position,
        sk.cbd_id AS matched_sales_cbd_id,
        os.territory,
        os.firm_crd,
        os.broker_name,
        os.file_dist_ch
    FROM opp_split os
    LEFT JOIN sales_keys sk
        ON sk.fiscal_yr = os.fiscal_yr
       AND sk.zip_code = os.zip_code
       AND sk.cbd_id = os.candidate_cbd_id
       AND sk.product_v2 = os.product_line
       --f2: no dist_ch and no territory condition: firm_2's sales name their channels differently and have no vendor territory
       AND sk.state = os.state
),

opp_ranked AS (
    SELECT
        *,
        ROW_NUMBER() OVER (
            PARTITION BY
                fiscal_yr,
                zip_code,
                state,
                product_line,
                dist_ch,
                original_cbd_id,
                territory,
                firm_crd,
                broker_name,
                file_dist_ch
            ORDER BY
                CASE
                    WHEN matched_sales_cbd_id IS NOT NULL THEN 0
                    ELSE 1
                END,
                split_position
        ) AS match_rank
    FROM opp_matches
),

opp_resolved AS (
    SELECT
        fiscal_yr,
        zip_code,
        state,
        product_line,
        dist_ch,
        territory,
        firm_crd,
        broker_name,
        file_dist_ch,

        /* Use the matching sales CBD.
           If no split value matches sales, use the first value. */
        COALESCE(
            matched_sales_cbd_id,
            candidate_cbd_id
        ) AS cbd_id,

        mm_opp
    FROM opp_ranked
    WHERE match_rank = 1
),

opp_final AS (
    SELECT
        fiscal_yr,
        LPAD(TRIM(zip_code::VARCHAR), 5, '0') AS zip_code,
        state,
        product_line,
        dist_ch,
        cbd_id,
        territory,
        file_dist_ch,
        firm_crd,      --f2: CRD and broker name kept (owner, 2026-10-25)
        broker_name,
        SUM(mm_opp) AS mm_opp
    FROM opp_resolved
    GROUP BY
        fiscal_yr,
        LPAD(TRIM(zip_code::VARCHAR), 5, '0'),
        state,
        product_line,
        dist_ch,
        cbd_id,
        territory,
        file_dist_ch,
        firm_crd,
        broker_name
)

SELECT opp_final.* REPLACE (COALESCE(ovr.ov_dist_ch, opp_final.dist_ch) AS dist_ch),   --f2: the firm overrides (tmp_firm_override)
    --f2: new_dist as the query sets it (outputfornick), on firm_2's resolved cbd_id and dist_ch; a firm override first
    case when ovr.ov_cbd IS NOT NULL then ovr.ov_new_dist
        when cbd_id in ('57', '1967') then 'National (Chase)'
        when cbd_id in ('1822', '14') then 'Wells WH'
        when cbd_id in ('1823') then 'Wells FI'
        when cbd_id in ('438') then 'AFS'
    else dist_ch
    end as new_dist
FROM opp_final
LEFT JOIN (SELECT TO_CHAR(CBD_ID) AS ov_cbd, DIST_CH AS ov_dist_ch, NEW_DIST AS ov_new_dist
           FROM ssdb_integration.lr_strategy.tmp_firm_override) ovr ON ovr.ov_cbd = opp_final.cbd_id
);

--Statement 5.  FIRM_KEY: one key per firm across both firms' rows (owner, 2026-10-26).  A CRD and a CBD_ID are linked
--when the vendor's resolved rows put them together: firm_1's (crd_cbd_mm) and firm_2's (tmp_opp_f2_final).
--Linked CRDs and CBD_IDs form one group (a CBD_ID of union_base with no link is a group alone), so both firms'
--opportunity of a CRD lands in one key, and sales reach it by CBD_ID.  FIRM_KEY = the group's CBD_ID carrying the
--most opportunity.  Groups: six label passes, each carrying the smallest CBD_ID one step along the links (no
--recursion); the checks (statement 14) say whether six were enough.  One row per CBD_ID and per CRD.  KEY_REVIEW: the key's CBD_IDs
--carry 2+ PARENT in firm_1's rows (a link may chain two firms), for manual review.
CREATE OR REPLACE TEMPORARY TABLE ssdb_integration.lr_strategy.tmp_firm_key AS (
WITH
e AS (   --the links, with their opportunity
    SELECT crd, cbd, SUM(opp) AS opp
    FROM (SELECT TO_CHAR(firm_crd) AS crd, TO_CHAR(cbd_id) AS cbd, mm_opp AS opp FROM ssdb_integration.lr_strategy.crd_cbd_mm
          UNION ALL
          SELECT TO_CHAR(firm_crd), TO_CHAR(cbd_id), mm_opp FROM ssdb_integration.lr_strategy.tmp_opp_f2_final) x
    WHERE crd IS NOT NULL AND cbd IS NOT NULL
    GROUP BY crd, cbd
),
c0 AS (SELECT DISTINCT cbd, cbd AS lab FROM e),
r1 AS (SELECT e.crd, MIN(c.lab) AS lab FROM e JOIN c0 c ON c.cbd = e.cbd GROUP BY e.crd),
c1 AS (SELECT e.cbd, MIN(r.lab) AS lab FROM e JOIN r1 r ON r.crd = e.crd GROUP BY e.cbd),
r2 AS (SELECT e.crd, MIN(c.lab) AS lab FROM e JOIN c1 c ON c.cbd = e.cbd GROUP BY e.crd),
c2 AS (SELECT e.cbd, MIN(r.lab) AS lab FROM e JOIN r2 r ON r.crd = e.crd GROUP BY e.cbd),
r3 AS (SELECT e.crd, MIN(c.lab) AS lab FROM e JOIN c2 c ON c.cbd = e.cbd GROUP BY e.crd),
c3 AS (SELECT e.cbd, MIN(r.lab) AS lab FROM e JOIN r3 r ON r.crd = e.crd GROUP BY e.cbd),
r4 AS (SELECT e.crd, MIN(c.lab) AS lab FROM e JOIN c3 c ON c.cbd = e.cbd GROUP BY e.crd),
c4 AS (SELECT e.cbd, MIN(r.lab) AS lab FROM e JOIN r4 r ON r.crd = e.crd GROUP BY e.cbd),
r5 AS (SELECT e.crd, MIN(c.lab) AS lab FROM e JOIN c4 c ON c.cbd = e.cbd GROUP BY e.crd),
c5 AS (SELECT e.cbd, MIN(r.lab) AS lab FROM e JOIN r5 r ON r.crd = e.crd GROUP BY e.cbd),
r6 AS (SELECT e.crd, MIN(c.lab) AS lab FROM e JOIN c5 c ON c.cbd = e.cbd GROUP BY e.crd),
c6 AS (SELECT e.cbd, MIN(r.lab) AS lab FROM e JOIN r6 r ON r.crd = e.crd GROUP BY e.cbd),
g AS (   --every CBD_ID and its group
    SELECT cbd, lab AS grp FROM c6
    UNION ALL
    SELECT DISTINCT TO_CHAR(x.cbd_id), TO_CHAR(x.cbd_id)
    FROM ssdb_integration.lr_strategy.union_base x
    WHERE x.cbd_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM e WHERE e.cbd = TO_CHAR(x.cbd_id))
),
w AS (SELECT g.cbd, g.grp, COALESCE(o.opp, 0) AS opp
      FROM g LEFT JOIN (SELECT cbd, SUM(opp) AS opp FROM e GROUP BY cbd) o ON o.cbd = g.cbd),
kl AS (   --the label: the group's CBD_ID with the most opportunity
    SELECT grp, cbd AS firm_key
    FROM (SELECT grp, cbd, ROW_NUMBER() OVER (PARTITION BY grp ORDER BY opp DESC, cbd) AS rk FROM w) x
    WHERE rk = 1
),
cr AS (SELECT DISTINCT e.crd, w.grp FROM e JOIN w ON w.cbd = e.cbd),
u AS (SELECT x.*, s.CODE AS src
      FROM ssdb_integration.lr_strategy.union_base x JOIN ssdb_integration.lr_strategy.synthetic_key s ON s.KIND = 'SOURCE' AND s.VALUE = x.source),
p1 AS (SELECT TO_CHAR(cbd_id) AS cbd, MAX(parent) AS parent FROM u WHERE src = 'firm_1' AND cbd_id IS NOT NULL
       GROUP BY TO_CHAR(cbd_id)),
n AS (SELECT w.grp, COUNT(DISTINCT w.cbd) AS n_cbd, COUNT(DISTINCT p1.parent) AS n_parent
      FROM w LEFT JOIN p1 ON p1.cbd = w.cbd GROUP BY w.grp),
nc AS (SELECT grp, COUNT(*) AS n_crd FROM cr GROUP BY grp)
SELECT 'CBD_ID' AS id_type, w.cbd AS id, kl.firm_key, n.n_cbd, COALESCE(nc.n_crd, 0) AS n_crd,
       CASE WHEN n.n_parent > 1 THEN 'CBD_IDs of the key carry 2+ PARENT' END AS key_review
FROM w JOIN kl ON kl.grp = w.grp JOIN n ON n.grp = w.grp LEFT JOIN nc ON nc.grp = w.grp
UNION ALL
SELECT 'CRD', cr.crd, kl.firm_key, n.n_cbd, COALESCE(nc.n_crd, 0),
       CASE WHEN n.n_parent > 1 THEN 'CBD_IDs of the key carry 2+ PARENT' END
FROM cr JOIN kl ON kl.grp = cr.grp JOIN n ON n.grp = cr.grp LEFT JOIN nc ON nc.grp = cr.grp
);

--Statement 6.  UNION_OPP: the union with firm_2's opportunity in MM_OPP, in firm_1's layout (owner, 2026-10-25: "no it needs
--to match the layout of firm 1's data. there needs to be a join so that mm_opp and sales exists for firm two on
--the same rows so we can do analytics ar the wholesaler level").  It reads union_base, the union without firm_2's
--opportunity (owner, 2026-10-25: the current data_withnewchannel_union_w_joinkeys already carries an earlier load
--of it, which would be counted twice); union_base itself is never touched.  firm_1 puts MM_OPP on a sales row of its key when the seller is the holder, else on its own row.
--firm_2's opportunity is tmp_opp_f2_final: its file through the opportunity steps of the owner's firm_1 query
--(statements 3-4: company, dist_ch and new_dist as firm_1's), without FIXED (out of scope, owner, 2026-10-24, Q22)
--and NO CHANNEL (owner, 2026-10-25).
--UNION_OPP = the union's firm_1 rows unchanged + its firm_2 rows (every column unchanged except MM_OPP, and
--PRODUCT_V2: firm_2's VA counted as VARIABLE, owner, 2026-10-26, Q8) + opp-only rows; except the firm overrides
--(tmp_firm_override, statement 2; owner, 2026-10-26): every row of an overridden CBD_ID, both firms,
--takes its NEW_DIST and the CHANNEL firm_1's rows carry for that NEW_DIST, and firm_1's rows its DIST_CH (firm_2's
--keep their own DIST_CH, firm_2's current state).
--Same columns as the union, in its order, plus lineage columns at the end:
--  ROW_ORIGIN    'union' (row as in the source), 'union + opp file' (a firm_2 sales row now carrying MM_OPP),
--                'opp file' (a new opp-only row)
--  FILE_NEW_DIST the new_dist tmp_opp_f2_final gives the opportunity (on a sales row: NULL if its key has 2+; the
--                sales row keeps its own NEW_DIST)
--  CHANNEL_RULE  'sales row'; on an opp-only row 'firm_1 NEW_DIST': the CHANNEL firm_1's union rows carry for that
--                NEW_DIST, until the owner's CHANNEL step is in; NULL where they carry none or 2+ (checks fail on it)
--  N_HOLDERS     distinct CLEAN_IDs holding the ZIP_CODE x DIST_CH in territories (0 = the TX/NY block, Q10; 2 = shared)
--  FIRM_KEY      one key per firm across both firms (tmp_firm_key, statement 5, by CBD_ID; owner, 2026-10-26)
--  FIRM_CRD      (owner, 2026-10-26) opp-only rows: the CRD of firm_2's file (one row per CRD); every other row: the
--                company's CRD where its CBD_ID has one in the vendor's resolved rows (crd_cbd_mm, tmp_opp_f2_final)
--  FIRM_OVERRIDE TRUE on the rows of an overridden CBD_ID
--  CRD_RULE      'file', 'company has one CRD', or, FIRM_CRD blank, 'company has 2+ CRDs' (for review) /
--                'company has no CRD'; NULL where CBD_ID is NULL
--The key is ZIP_CODE x DIST_CH x CBD_ID x PRODUCT_V2, as firm_1's (CHANNEL is not in it), DIST_CH = firm_2's own
--channel: the file's (FILE_DIST_CH) through the settled map (owner, 2026-10-25, Q19); MM_OPP = SUM; a key that sums
--to 0 is left out.  A key goes on exactly one firm_2 union row with that ZIP_CODE, DIST_CH, CBD_ID and PRODUCT_V2
--whose seller is the holder (SALES_WHOLESALER_TERRITORY_ID = TERRITORY_WHOLESALER_TERRITORY_ID): the one with the
--largest ACTUAL_SALES_AMOUNT, ties on the other columns.  It takes that row's NEW_DIST and CHANNEL.  A key with
--no such row becomes opp-only rows, one per the file's new_dist and CRD (NEW_DIST = it): FISCAL_YR, the sales amounts and the address IDs NULL; like firm_1's, TERR_WHOLESALER
--and SALES_WHOLESALER are NULL, both CLEAN_NAME columns carry the holder's name, both TERRITORY_ID columns the
--holder's CLEAN_ID, both HAS_TERRITORY flags are 1 (0 with no holder).  A firm_2 union row that gets no key keeps its NULL MM_OPP.
CREATE OR REPLACE TABLE ssdb_integration.lr_strategy.UNION_OPP AS
WITH
k AS (SELECT * FROM ssdb_integration.lr_strategy.synthetic_key),
s1 AS (SELECT VALUE AS V FROM k WHERE KIND = 'SOURCE' AND CODE = 'firm_1'),
s2 AS (SELECT VALUE AS V FROM k WHERE KIND = 'SOURCE' AND CODE = 'firm_2'),
dm AS (              -- the file's channel -> firm_2's union DIST_CH (owner, 2026-10-25, Q19); GONE = NO CHANNEL, dropped
  SELECT a.VALUE AS FILE_DIST_CH, b.VALUE AS DIST_CH, m.GONE
  FROM (VALUES ('O2_01', 'D2_01', FALSE), ('O2_02', 'D2_02', FALSE), ('O2_03', 'D2_04', FALSE),
               ('O2_04', 'D2_03', FALSE), ('O2_05', NULL, TRUE)) m(FILE_CODE, UNION_CODE, GONE)
  CROSS JOIN s2
  JOIN k a ON a.KIND = 'DIST_CH' AND a.SOURCE = s2.V AND a.CODE = m.FILE_CODE
  LEFT JOIN k b ON b.KIND = 'DIST_CH' AND b.SOURCE = s2.V AND b.CODE = m.UNION_CODE),
pv AS (              -- firm_2's VA is VARIABLE (owner, 2026-10-26, Q8)
  SELECT a.VALUE AS VA, b.VALUE AS VARIABLE
  FROM k a JOIN k b ON b.KIND = 'PRODUCT_V2' AND b.CODE = 'PR02'
  WHERE a.KIND = 'PRODUCT_V2' AND a.CODE = 'PR05'),
fov AS (SELECT TO_CHAR(CBD_ID) AS CBD_ID, DIST_CH, NEW_DIST FROM ssdb_integration.lr_strategy.tmp_firm_override),   -- the firm overrides
fo AS (              -- tmp_opp_f2_final without its dropped rows; a FILE_DIST_CH in no map is kept, with a NULL DIST_CH (checks fail)
  SELECT f.ZIP_CODE, dm.DIST_CH, TO_CHAR(f.CBD_ID) AS CBD_ID, f.PRODUCT_LINE AS PRODUCT_V2, f.NEW_DIST,
         TO_CHAR(f.FIRM_CRD) AS FIRM_CRD, f.MM_OPP
  FROM ssdb_integration.lr_strategy.tmp_opp_f2_final f
  LEFT JOIN dm ON dm.FILE_DIST_CH = f.FILE_DIST_CH
  WHERE dm.GONE IS DISTINCT FROM TRUE
    AND f.PRODUCT_LINE IS DISTINCT FROM 'FIXED'),   -- FIXED: the query's own label for fixed annuity
ak AS (              -- the opportunity keys
  SELECT ZIP_CODE, DIST_CH, CBD_ID, PRODUCT_V2, SUM(MM_OPP) AS MM_OPP,
         CASE WHEN COUNT(DISTINCT COALESCE(NEW_DIST, '~')) = 1 THEN MAX(NEW_DIST) END AS FILE_NEW_DIST
  FROM fo GROUP BY ZIP_CODE, DIST_CH, CBD_ID, PRODUCT_V2
  HAVING COALESCE(SUM(MM_OPP), 0) <> 0),
cc AS (              -- a company's CRDs in the vendor's resolved rows; FIRM_CRD where it has one
  SELECT CBD, MAX(CRD) AS CRD, COUNT(DISTINCT CRD) AS N_CRD
  FROM (SELECT TO_CHAR(cbd_id) AS CBD, TO_CHAR(firm_crd) AS CRD FROM ssdb_integration.lr_strategy.crd_cbd_mm
        UNION SELECT TO_CHAR(CBD_ID), TO_CHAR(FIRM_CRD) FROM ssdb_integration.lr_strategy.tmp_opp_f2_final) x
  WHERE CBD IS NOT NULL AND CRD IS NOT NULL
  GROUP BY CBD),
ch1 AS (             -- the CHANNEL firm_1's union rows carry for a NEW_DIST, where they carry one
  SELECT u.NEW_DIST, MAX(u.CHANNEL) AS CHANNEL
  FROM ssdb_integration.lr_strategy.union_base u JOIN s1 ON u.SOURCE = s1.V
  WHERE u.NEW_DIST IS NOT NULL
  GROUP BY u.NEW_DIST HAVING COUNT(DISTINCT COALESCE(u.CHANNEL, '~')) = 1),
fp AS (              -- FIRM and PARENT of a company in each SOURCE
  SELECT u.CBD_ID, u.SOURCE, MAX(u.FIRM) AS FIRM, MAX(u.PARENT) AS PARENT
  FROM ssdb_integration.lr_strategy.union_base u
  WHERE u.CBD_ID IS NOT NULL GROUP BY u.CBD_ID, u.SOURCE),
cn AS (              -- the firm name crd_cbd gives a CBD_ID: FIRM where union_base has none; PARENT stays blank (owner, 2026-10-25)
  SELECT CAST(CBD_ID AS VARCHAR) AS CBD_ID, MAX(FIRM) AS FIRM
  FROM ssdb_integration.lr_strategy.crd_cbd
  WHERE CBD_ID IS NOT NULL AND CAST(CBD_ID AS VARCHAR) <> '0' GROUP BY 1),
h AS (               -- holders of a ZIP_CODE x DIST_CH in territories
  SELECT t.ZIP_CODE, t.CHANNEL AS DIST_CH, MIN(t.CLEAN_ID) AS ID, COUNT(DISTINCT t.CLEAN_ID) AS N,
         MIN_BY(t.CLEAN_NAME, t.CLEAN_ID) AS NAME
  FROM ssdb_integration.lr_strategy.territories t JOIN s2 ON t.SOURCE = s2.V
  WHERE t.CLEAN_ID IS NOT NULL GROUP BY t.ZIP_CODE, t.CHANNEL),
nm AS (              -- the name the union already carries for that ID
  SELECT u.TERRITORY_WHOLESALER_TERRITORY_ID AS ID, MAX(u.TERR_WHOLESALER_CLEAN_NAME) AS NAME
  FROM ssdb_integration.lr_strategy.union_base u JOIN s2 ON u.SOURCE = s2.V
  GROUP BY u.TERRITORY_WHOLESALER_TERRITORY_ID),
st AS (SELECT ZIP_CODE, MAX(STATE) AS STATE FROM ssdb_integration.lr_strategy.territories GROUP BY ZIP_CODE),
us AS (SELECT ZIP_CODE, MAX(STATE) AS STATE FROM ssdb_integration.lr_strategy.union_base GROUP BY ZIP_CODE),
r0 AS (              -- the union with its seller = holder flag; firm_2's VA as VARIABLE (Q8); the firm overrides
  SELECT u.* REPLACE (CASE WHEN u.SOURCE = s2.V AND u.PRODUCT_V2 = pv.VA THEN pv.VARIABLE ELSE u.PRODUCT_V2 END AS PRODUCT_V2,
                      CASE WHEN fv.CBD_ID IS NOT NULL AND u.SOURCE = s1.V THEN fv.DIST_CH ELSE u.DIST_CH END AS DIST_CH,
                      CASE WHEN fv.CBD_ID IS NOT NULL THEN fv.NEW_DIST ELSE u.NEW_DIST END AS NEW_DIST,
                      CASE WHEN fv.CBD_ID IS NOT NULL THEN fc.CHANNEL ELSE u.CHANNEL END AS CHANNEL),
         COALESCE(u.SALES_WHOLESALER_TERRITORY_ID = u.TERRITORY_WHOLESALER_TERRITORY_ID, FALSE) AS IS_HOLDER,
         CASE WHEN fv.CBD_ID IS NOT NULL THEN TRUE END AS FIRM_OVERRIDE
  FROM ssdb_integration.lr_strategy.union_base u CROSS JOIN s1 CROSS JOIN s2 CROSS JOIN pv
  LEFT JOIN fov fv ON fv.CBD_ID = TO_CHAR(u.CBD_ID)
  LEFT JOIN ch1 fc ON fc.NEW_DIST = fv.NEW_DIST),
r AS (               -- PICK: the one firm_2 holder row per opportunity key that takes the key's MM_OPP
  SELECT r0.*, r0.SOURCE = s2.V AND r0.IS_HOLDER AND ROW_NUMBER() OVER (
           PARTITION BY r0.SOURCE, r0.ZIP_CODE, r0.DIST_CH, r0.CBD_ID, r0.PRODUCT_V2
           ORDER BY r0.IS_HOLDER DESC, r0.ACTUAL_SALES_AMOUNT DESC NULLS LAST, r0.FISCAL_YR, r0.TERR_WHOLESALER,
                    r0.SALES_WHOLESALER, r0.TERR_WHOLESALER_CLEAN_NAME, r0.SALES_WHOLESALER_CLEAN_NAME, r0.FIRM,
                    r0.PARENT, r0.NEW_DIST, r0.CHANNEL, r0.STATE, r0.SALES_AMOUNT, r0.SALES_WHOLESALER_TERRITORY_ID,
                    r0.SALES_WHOLESALER_ADDRESS_ID, r0.TERRITORY_WHOLESALER_TERRITORY_ID,
                    r0.TERRITORY_WHOLESALER_ADDRESS_ID, r0.SALES_WHOLESALER_HAS_TERRITORY,
                    r0.TERRITORY_WHOLESALER_HAS_TERRITORY) = 1 AS PICK
  FROM r0 CROSS JOIN s2),
a AS (               -- the keys with no holder row: their opportunity becomes opp-only rows, one per the file's new_dist and CRD
  SELECT fo.ZIP_CODE, fo.DIST_CH, fo.CBD_ID, fo.PRODUCT_V2, fo.NEW_DIST, fo.FIRM_CRD, SUM(fo.MM_OPP) AS MM_OPP
  FROM fo
  JOIN ak ON ak.ZIP_CODE = fo.ZIP_CODE AND ak.DIST_CH = fo.DIST_CH AND ak.CBD_ID = fo.CBD_ID AND ak.PRODUCT_V2 = fo.PRODUCT_V2
  WHERE NOT EXISTS (SELECT 1 FROM r WHERE r.PICK AND r.ZIP_CODE = ak.ZIP_CODE AND r.DIST_CH = ak.DIST_CH
                    AND r.CBD_ID = ak.CBD_ID AND r.PRODUCT_V2 = ak.PRODUCT_V2)
  GROUP BY fo.ZIP_CODE, fo.DIST_CH, fo.CBD_ID, fo.PRODUCT_V2, fo.NEW_DIST, fo.FIRM_CRD
  HAVING COALESCE(SUM(fo.MM_OPP), 0) <> 0),
b AS (
  SELECT a.*, s2.V AS SRC,
         CASE WHEN ch1.NEW_DIST IS NOT NULL THEN 'firm_1 NEW_DIST' END AS CHANNEL_RULE, ch1.CHANNEL,
         COALESCE(p2.FIRM, p1.FIRM, cn.FIRM) AS FIRM, COALESCE(p2.PARENT, p1.PARENT) AS PARENT,
         h.ID AS HOLDER_ID, COALESCE(nm.NAME, h.NAME) AS HOLDER_NAME, COALESCE(h.N, 0) AS N_HOLDERS,
         COALESCE(st.STATE, us.STATE) AS STATE, fk.FIRM_KEY,
         CASE WHEN fv.CBD_ID IS NOT NULL THEN TRUE END AS FIRM_OVERRIDE
  FROM a CROSS JOIN s1 CROSS JOIN s2
  LEFT JOIN ch1 ON ch1.NEW_DIST = a.NEW_DIST
  LEFT JOIN fp p2 ON p2.CBD_ID = a.CBD_ID AND p2.SOURCE = s2.V
  LEFT JOIN fp p1 ON p1.CBD_ID = a.CBD_ID AND p1.SOURCE = s1.V
  LEFT JOIN cn ON cn.CBD_ID = a.CBD_ID
  LEFT JOIN h ON h.ZIP_CODE = a.ZIP_CODE AND h.DIST_CH = a.DIST_CH
  LEFT JOIN nm ON nm.ID = h.ID
  LEFT JOIN st ON st.ZIP_CODE = a.ZIP_CODE
  LEFT JOIN us ON us.ZIP_CODE = a.ZIP_CODE
  LEFT JOIN ssdb_integration.lr_strategy.tmp_firm_key fk ON fk.ID_TYPE = 'CBD_ID' AND fk.ID = TO_CHAR(a.CBD_ID)
  LEFT JOIN fov fv ON fv.CBD_ID = TO_CHAR(a.CBD_ID))
SELECT r.* EXCLUDE (IS_HOLDER, PICK) REPLACE (COALESCE(ak.MM_OPP, r.MM_OPP) AS MM_OPP),
       CASE WHEN ak.CBD_ID IS NOT NULL THEN 'union + opp file' ELSE 'union' END AS ROW_ORIGIN,
       ak.FILE_NEW_DIST, CASE WHEN ak.CBD_ID IS NOT NULL THEN 'sales row' END AS CHANNEL_RULE,
       CASE WHEN ak.CBD_ID IS NOT NULL THEN COALESCE(h.N, 0) END AS N_HOLDERS, fk.FIRM_KEY,
       CASE WHEN cc.N_CRD = 1 THEN cc.CRD END AS FIRM_CRD,
       CASE WHEN r.CBD_ID IS NULL THEN NULL WHEN cc.N_CRD = 1 THEN 'company has one CRD'
            WHEN cc.N_CRD > 1 THEN 'company has 2+ CRDs' ELSE 'company has no CRD' END AS CRD_RULE
FROM r
LEFT JOIN ak ON r.PICK AND ak.ZIP_CODE = r.ZIP_CODE AND ak.DIST_CH = r.DIST_CH
            AND ak.CBD_ID = r.CBD_ID AND ak.PRODUCT_V2 = r.PRODUCT_V2
LEFT JOIN h ON h.ZIP_CODE = r.ZIP_CODE AND h.DIST_CH = r.DIST_CH
LEFT JOIN ssdb_integration.lr_strategy.tmp_firm_key fk ON fk.ID_TYPE = 'CBD_ID' AND fk.ID = TO_CHAR(r.CBD_ID)
LEFT JOIN cc ON cc.CBD = TO_CHAR(r.CBD_ID)
UNION ALL BY NAME     -- the columns not named below are NULL on opp-only rows
SELECT b.SRC AS SOURCE, b.CBD_ID, b.FIRM, b.PARENT, b.DIST_CH, b.NEW_DIST, b.CHANNEL, b.STATE,
       b.ZIP_CODE, b.PRODUCT_V2, b.MM_OPP,
       b.HOLDER_NAME AS TERR_WHOLESALER_CLEAN_NAME, b.HOLDER_NAME AS SALES_WHOLESALER_CLEAN_NAME,
       b.HOLDER_ID AS SALES_WHOLESALER_TERRITORY_ID, b.HOLDER_ID AS TERRITORY_WHOLESALER_TERRITORY_ID,
       CASE WHEN b.N_HOLDERS > 0 THEN 1 ELSE 0 END AS SALES_WHOLESALER_HAS_TERRITORY,
       CASE WHEN b.N_HOLDERS > 0 THEN 1 ELSE 0 END AS TERRITORY_WHOLESALER_HAS_TERRITORY,
       'opp file' AS ROW_ORIGIN, b.NEW_DIST AS FILE_NEW_DIST, b.CHANNEL_RULE, b.N_HOLDERS, b.FIRM_KEY,
       b.FIRM_CRD, 'file' AS CRD_RULE, b.FIRM_OVERRIDE
FROM b;

--Statement 7.  dist_ch by firm_2's own channel; share of firm_2's OPP.
WITH
b2 AS (SELECT * FROM ssdb_integration.lr_strategy.tmp_opp_base_both WHERE src = 'firm_2'),
t AS (SELECT SUM(global_sales) AS opp FROM b2)
SELECT b2.file_dist_ch AS firm_2_dist_ch, COALESCE(b2.dist_ch, 'REVIEW: ' || b2.dist_review) AS dist_ch,
       b2.dist_source, COUNT(DISTINCT b2.firm_crd) AS crds, ROUND(100 * SUM(b2.global_sales) / MAX(t.opp), 2) AS pct_firm_2_opp
FROM b2
CROSS JOIN t
GROUP BY b2.file_dist_ch, COALESCE(b2.dist_ch, 'REVIEW: ' || b2.dist_review), b2.dist_source
ORDER BY pct_firm_2_opp DESC;

--Statement 8.  For manual review: each CRD whose firm_2 rows have no dist_ch, with firm_1's dist_ch of the CRD and
--their shares of firm_1's OPP there.
WITH
b AS (SELECT * FROM ssdb_integration.lr_strategy.tmp_opp_base_both),
t AS (SELECT SUM(global_sales) AS opp FROM b WHERE src = 'firm_2'),
f1 AS (SELECT firm_crd, COALESCE(dist_ch, '(blank)') AS dist_ch, SUM(global_sales) AS opp
       FROM b WHERE src = 'firm_1' GROUP BY firm_crd, COALESCE(dist_ch, '(blank)')),
f1s AS (SELECT firm_crd,
               LISTAGG(dist_ch || ' ' || TO_CHAR(ROUND(100 * opp / NULLIF(tot, 0), 1)) || '%', ', ')
                   WITHIN GROUP (ORDER BY opp DESC) AS firm_1_dist_ch
        FROM (SELECT f1.*, SUM(opp) OVER (PARTITION BY firm_crd) AS tot FROM f1)
        GROUP BY firm_crd),
r AS (SELECT firm_crd, dist_review, LISTAGG(DISTINCT broker_name, ' | ') AS broker_names,
             LISTAGG(DISTINCT file_dist_ch, ', ') AS firm_2_dist_ch, SUM(global_sales) AS opp
      FROM b WHERE src = 'firm_2' AND dist_review IS NOT NULL
      GROUP BY firm_crd, dist_review)
SELECT r.firm_crd, r.broker_names, r.firm_2_dist_ch, f1s.firm_1_dist_ch, r.dist_review,
       ROUND(100 * r.opp / t.opp, 3) AS pct_firm_2_opp
FROM r
LEFT JOIN f1s ON f1s.firm_crd = r.firm_crd
CROSS JOIN t
ORDER BY r.opp DESC;

--Statement 9.  new_dist: firm_2's (tmp_opp_f2_final) next to firm_1's NEW_DIST in union_base at the same CBD_ID x DIST_CH,
--by firm_2's own channel; share of firm_2's OPP after opp_final.  AGREEMENT: same, differs, firm_1 2+ (union_base's
--firm_1 rows there carry 2+ NEW_DIST), no firm_1 row (none at that CBD_ID x DIST_CH, or a blank dist_ch).
WITH
f AS (SELECT * FROM ssdb_integration.lr_strategy.tmp_opp_f2_final),
t AS (SELECT SUM(mm_opp) AS opp FROM f),
u1 AS (
    SELECT TO_CHAR(u.cbd_id) AS cbd_id, TO_CHAR(u.dist_ch) AS dist_ch, MAX(TO_CHAR(u.new_dist)) AS f1_new_dist,
           COUNT(DISTINCT COALESCE(TO_CHAR(u.new_dist), '~')) AS n_nd
    FROM ssdb_integration.lr_strategy.union_base u
    JOIN ssdb_integration.lr_strategy.synthetic_key s ON s.KIND = 'SOURCE' AND s.CODE = 'firm_1' AND s.VALUE = u.source
    GROUP BY TO_CHAR(u.cbd_id), TO_CHAR(u.dist_ch)
),
x AS (
    SELECT f.file_dist_ch, f.dist_ch, f.new_dist, f.cbd_id, f.mm_opp,
           CASE WHEN u1.cbd_id IS NULL THEN '(no firm_1 row)' WHEN u1.n_nd > 1 THEN '(firm_1 2+)'
                ELSE COALESCE(u1.f1_new_dist, '(blank)') END AS firm_1_new_dist,
           CASE WHEN u1.cbd_id IS NULL THEN 'no firm_1 row' WHEN u1.n_nd > 1 THEN 'firm_1 2+'
                WHEN f.new_dist IS NOT DISTINCT FROM u1.f1_new_dist THEN 'same' ELSE 'differs' END AS agreement
    FROM f
    LEFT JOIN u1 ON u1.cbd_id = f.cbd_id AND u1.dist_ch = f.dist_ch
)
SELECT x.file_dist_ch AS firm_2_dist_ch, x.dist_ch, x.new_dist, x.firm_1_new_dist, x.agreement,
       COUNT(DISTINCT x.cbd_id) AS cbd_ids, ROUND(100 * SUM(x.mm_opp) / MAX(t.opp), 2) AS pct_firm_2_opp
FROM x
CROSS JOIN t
GROUP BY x.file_dist_ch, x.dist_ch, x.new_dist, x.firm_1_new_dist, x.agreement
ORDER BY pct_firm_2_opp DESC;

--Statement 10.  The FIRM_KEYs joining 2+ CBD_IDs: each CBD_ID with firm_1's FIRM and PARENT, the CRDs with their
--broker names, each firm's share of opportunity, and the review flag.  Names: read at work, never copied here.
WITH
fk AS (SELECT * FROM ssdb_integration.lr_strategy.tmp_firm_key WHERE n_cbd > 1),
u AS (SELECT x.*, s.CODE AS src
      FROM ssdb_integration.lr_strategy.union_base x JOIN ssdb_integration.lr_strategy.synthetic_key s ON s.KIND = 'SOURCE' AND s.VALUE = x.source),
nm AS (SELECT TO_CHAR(cbd_id) AS cbd, MAX(firm) AS firm, MAX(parent) AS parent FROM u
       WHERE src = 'firm_1' AND cbd_id IS NOT NULL GROUP BY TO_CHAR(cbd_id)),
o1 AS (SELECT TO_CHAR(cbd_id) AS cbd, SUM(mm_opp) AS opp FROM u WHERE src = 'firm_1' GROUP BY TO_CHAR(cbd_id)),
o2 AS (SELECT TO_CHAR(cbd_id) AS cbd, SUM(mm_opp) AS opp FROM ssdb_integration.lr_strategy.tmp_opp_f2_final GROUP BY TO_CHAR(cbd_id)),
t AS (SELECT (SELECT SUM(mm_opp) FROM u WHERE src = 'firm_1') AS t1, (SELECT SUM(mm_opp) FROM ssdb_integration.lr_strategy.tmp_opp_f2_final) AS t2),
bn AS (SELECT TO_CHAR(firm_crd) AS crd, broker_name FROM ssdb_integration.lr_strategy.crd_cbd_mm
       UNION SELECT TO_CHAR(firm_crd), broker_name FROM ssdb_integration.lr_strategy.tmp_opp_f2_final),
c AS (SELECT fk.firm_key, MAX(fk.key_review) AS key_review,
             LISTAGG(fk.id || ' ' || COALESCE(nm.firm, '?') || ' / ' || COALESCE(nm.parent, '?'), '; ')
                 WITHIN GROUP (ORDER BY fk.id) AS cbd_ids,
             SUM(o1.opp) AS opp1, SUM(o2.opp) AS opp2
      FROM fk LEFT JOIN nm ON nm.cbd = fk.id LEFT JOIN o1 ON o1.cbd = fk.id LEFT JOIN o2 ON o2.cbd = fk.id
      WHERE fk.id_type = 'CBD_ID' GROUP BY fk.firm_key),
r AS (SELECT fk.firm_key, LISTAGG(fk.id || ' ' || COALESCE(bn.broker_name, '?'), '; ') WITHIN GROUP (ORDER BY fk.id) AS crds
      FROM fk LEFT JOIN bn ON bn.crd = fk.id WHERE fk.id_type = 'CRD' GROUP BY fk.firm_key)
SELECT c.firm_key, c.key_review, c.cbd_ids, r.crds,
       ROUND(100 * c.opp1 / t.t1, 2) AS pct_firm_1_opp, ROUND(100 * c.opp2 / t.t2, 2) AS pct_firm_2_opp
FROM c LEFT JOIN r ON r.firm_key = c.firm_key CROSS JOIN t
ORDER BY COALESCE(c.opp1, 0) + COALESCE(c.opp2, 0) DESC;

--Statement 11.  firm_2 MM_OPP from the file by DIST_CH x NEW_DIST x CHANNEL (rows on sales rows and opp-only rows),
-- next to firm_2's share of positive sales in the same cell (as the firm_1 table in DATASET_LOG.md, 2026-10-21).
WITH
s2 AS (SELECT VALUE AS V FROM ssdb_integration.lr_strategy.synthetic_key WHERE KIND = 'SOURCE' AND CODE = 'firm_2'),
o AS (SELECT DIST_CH, NEW_DIST, CHANNEL,
             SUM(CASE WHEN ROW_ORIGIN = 'union + opp file' THEN 1 ELSE 0 END) AS ROWS_ON_SALES_ROWS,
             SUM(CASE WHEN ROW_ORIGIN = 'opp file' THEN 1 ELSE 0 END) AS ROWS_OPP_ONLY,
             COUNT(DISTINCT CBD_ID) AS CBD_IDS, SUM(MM_OPP) AS MM_OPP
      FROM ssdb_integration.lr_strategy.UNION_OPP WHERE ROW_ORIGIN <> 'union' GROUP BY DIST_CH, NEW_DIST, CHANNEL),
s AS (SELECT u.DIST_CH, u.NEW_DIST, u.CHANNEL, SUM(CASE WHEN u.ACTUAL_SALES_AMOUNT > 0 THEN u.ACTUAL_SALES_AMOUNT END) AS SALES
      FROM ssdb_integration.lr_strategy.union_base u JOIN s2 ON u.SOURCE = s2.V
      GROUP BY u.DIST_CH, u.NEW_DIST, u.CHANNEL)
SELECT COALESCE(o.DIST_CH, s.DIST_CH) AS DIST_CH, COALESCE(o.NEW_DIST, s.NEW_DIST) AS NEW_DIST,
       COALESCE(o.CHANNEL, s.CHANNEL) AS CHANNEL,
       o.ROWS_ON_SALES_ROWS, o.ROWS_OPP_ONLY, o.CBD_IDS,
       ROUND(100 * o.MM_OPP / SUM(o.MM_OPP) OVER (), 2) AS PCT_OF_FIRM_2_MM_OPP,
       ROUND(100 * s.SALES / SUM(s.SALES) OVER (), 2) AS PCT_OF_FIRM_2_SALES
FROM o
FULL OUTER JOIN s ON COALESCE(s.DIST_CH, '~') = COALESCE(o.DIST_CH, '~')    -- plain equality: a FULL JOIN needs it
                 AND COALESCE(s.NEW_DIST, '~') = COALESCE(o.NEW_DIST, '~') AND COALESCE(s.CHANNEL, '~') = COALESCE(o.CHANNEL, '~')
ORDER BY PCT_OF_FIRM_2_MM_OPP DESC NULLS LAST, PCT_OF_FIRM_2_SALES DESC NULLS LAST;

--Statement 12.  Does opportunity align across the firms at the same ZIP_CODE and firm (owner, 2026-10-26)?  Each firm's
-- MM_OPP in UNION_OPP summed to ZIP_CODE x firm x PRODUCT_V2 over all channels; firm = FIRM_KEY and, for comparison,
-- CBD_ID.  Equal = the same to 3 decimals of coded units (as Q23).  Shares of each firm's MM_OPP.
WITH
k AS (SELECT * FROM ssdb_integration.lr_strategy.synthetic_key),
s1 AS (SELECT VALUE AS V FROM k WHERE KIND = 'SOURCE' AND CODE = 'firm_1'),
s2 AS (SELECT VALUE AS V FROM k WHERE KIND = 'SOURCE' AND CODE = 'firm_2'),
d AS (SELECT NUM AS D FROM k WHERE KIND = 'divisor' AND VALUE = 'MM_OPP'),
uo AS (SELECT u.*, CASE WHEN u.SOURCE = s1.V THEN u.MM_OPP END AS M1, CASE WHEN u.SOURCE = s2.V THEN u.MM_OPP END AS M2
       FROM ssdb_integration.lr_strategy.UNION_OPP u CROSS JOIN s1 CROSS JOIN s2 WHERE u.MM_OPP IS NOT NULL),
c AS (SELECT 'FIRM_KEY' AS LVL, ZIP_CODE, FIRM_KEY AS FIRM, PRODUCT_V2, SUM(M1) AS O1, SUM(M2) AS O2
      FROM uo GROUP BY ZIP_CODE, FIRM_KEY, PRODUCT_V2
      UNION ALL
      SELECT 'CBD_ID', ZIP_CODE, CBD_ID, PRODUCT_V2, SUM(M1), SUM(M2)
      FROM uo GROUP BY ZIP_CODE, CBD_ID, PRODUCT_V2),
x AS (SELECT c.LVL, c.O1, c.O2,
             CASE WHEN COALESCE(c.O1, 0) = 0 THEN 'firm_2 only' WHEN COALESCE(c.O2, 0) = 0 THEN 'firm_1 only'
                  WHEN ROUND(c.O1 / d.D, 3) = ROUND(c.O2 / d.D, 3) THEN 'both: equal'
                  WHEN ABS(c.O2 - c.O1) <= 0.01 * ABS(c.O1) THEN 'both: within 1%'
                  WHEN c.O2 > c.O1 THEN 'both: firm_2 more than 1% higher'
                  ELSE 'both: firm_2 more than 1% lower' END AS ALIGNMENT
      FROM c CROSS JOIN d),
y AS (SELECT LVL, ALIGNMENT, COUNT(*) AS CELLS, SUM(O1) AS O1, SUM(O2) AS O2 FROM x GROUP BY LVL, ALIGNMENT)
SELECT LVL, ALIGNMENT, CELLS,
       ROUND(100 * O1 / SUM(O1) OVER (PARTITION BY LVL), 2) AS PCT_FIRM_1_MM_OPP,
       ROUND(100 * O2 / SUM(O2) OVER (PARTITION BY LVL), 2) AS PCT_FIRM_2_MM_OPP,
       ROUND(O2 / NULLIF(O1, 0), 3) AS FIRM_2_OVER_FIRM_1
FROM y
ORDER BY LVL DESC, ALIGNMENT;

--Statement 13.  By FIRM_KEY, the cells (ZIP_CODE x PRODUCT_V2) where both firms have MM_OPP: how many, the share equal,
-- each firm's MM_OPP there; largest gaps first.  FIRM_NAME = firm_1's FIRM of the key's CBD_ID.  Names: read at work.
WITH
k AS (SELECT * FROM ssdb_integration.lr_strategy.synthetic_key),
s1 AS (SELECT VALUE AS V FROM k WHERE KIND = 'SOURCE' AND CODE = 'firm_1'),
s2 AS (SELECT VALUE AS V FROM k WHERE KIND = 'SOURCE' AND CODE = 'firm_2'),
d AS (SELECT NUM AS D FROM k WHERE KIND = 'divisor' AND VALUE = 'MM_OPP'),
uo AS (SELECT u.*, CASE WHEN u.SOURCE = s1.V THEN u.MM_OPP END AS M1, CASE WHEN u.SOURCE = s2.V THEN u.MM_OPP END AS M2
       FROM ssdb_integration.lr_strategy.UNION_OPP u CROSS JOIN s1 CROSS JOIN s2 WHERE u.MM_OPP IS NOT NULL),
c AS (SELECT FIRM_KEY, ZIP_CODE, PRODUCT_V2, SUM(M1) AS O1, SUM(M2) AS O2
      FROM uo GROUP BY FIRM_KEY, ZIP_CODE, PRODUCT_V2
      HAVING COALESCE(SUM(M1), 0) <> 0 AND COALESCE(SUM(M2), 0) <> 0),
nm AS (SELECT TO_CHAR(u.CBD_ID) AS CBD_ID, MAX(u.FIRM) AS FIRM
       FROM ssdb_integration.lr_strategy.UNION_OPP u JOIN s1 ON u.SOURCE = s1.V WHERE u.CBD_ID IS NOT NULL GROUP BY TO_CHAR(u.CBD_ID))
SELECT c.FIRM_KEY, nm.FIRM AS FIRM_NAME, COUNT(*) AS CELLS_BOTH,
       ROUND(100 * AVG(CASE WHEN ROUND(c.O1 / d.D, 3) = ROUND(c.O2 / d.D, 3) THEN 1 ELSE 0 END), 1) AS PCT_CELLS_EQUAL,
       SUM(c.O1) AS FIRM_1_MM_OPP, SUM(c.O2) AS FIRM_2_MM_OPP, ROUND(SUM(c.O2) / NULLIF(SUM(c.O1), 0), 3) AS FIRM_2_OVER_FIRM_1
FROM c CROSS JOIN d
LEFT JOIN nm ON nm.CBD_ID = c.FIRM_KEY
GROUP BY c.FIRM_KEY, nm.FIRM
ORDER BY ABS(SUM(c.O2) - SUM(c.O1)) DESC
LIMIT 40;

--Statement 14.  Checks, last so Run All ends on them: every MUST_BE_ZERO = 1 row must be 0.  STEP says which table.
--If 'links whose CRD and CBD_ID have different FIRM_KEY' fails, the links are longer than six passes reach: in statement
--5 copy the r6/c6 pair as r7/c7 (and so on) and read the last one in g.
WITH
b AS (SELECT * FROM ssdb_integration.lr_strategy.tmp_opp_base_both),
b2 AS (SELECT * FROM b WHERE src = 'firm_2'),
o AS (SELECT COUNT(*) AS n, SUM(opp) AS opp FROM ssdb_integration.lr_strategy.opp_original),
t AS (SELECT SUM(global_sales) AS opp FROM b2),
k AS (SELECT * FROM ssdb_integration.lr_strategy.synthetic_key),
pm AS (   --the settled product map (owner, 2026-10-24, Q22), as in 23
    SELECT pl.VALUE AS PL, va.VALUE AS VA, p.VALUE AS PRODUCT_V2
    FROM (VALUES ('PR05', 'V01', 'PR04'), ('PR05', 'V02', 'PR01'), ('PR05', 'V03', 'PR02'),
                 ('L02', NULL, 'PR03')) m(PL_CODE, VA_CODE, PRODUCT_CODE)
    JOIN k pl ON pl.KIND = 'PRODUCT_V2' AND pl.CODE = m.PL_CODE
    LEFT JOIN k va ON va.KIND = 'VA_TYPE' AND va.CODE = m.VA_CODE
    JOIN k p ON p.KIND = 'PRODUCT_V2' AND p.CODE = m.PRODUCT_CODE
),
f1p AS (SELECT LPAD(TRIM(zip_code), 5, '0') AS zip, firm_crd, broker_name, product_line, SUM(global_sales) AS opp
        FROM b WHERE src = 'firm_1' GROUP BY LPAD(TRIM(zip_code), 5, '0'), firm_crd, broker_name, product_line),
f2p AS (SELECT zip_code AS zip, firm_crd, broker_name, product_line, SUM(global_sales) AS opp
        FROM b2 GROUP BY zip_code, firm_crd, broker_name, product_line),
fk AS (SELECT * FROM ssdb_integration.lr_strategy.tmp_firm_key),
e AS (SELECT TO_CHAR(firm_crd) AS crd, TO_CHAR(cbd_id) AS cbd FROM ssdb_integration.lr_strategy.crd_cbd_mm
      UNION SELECT TO_CHAR(firm_crd), TO_CHAR(cbd_id) FROM ssdb_integration.lr_strategy.tmp_opp_f2_final),
u AS (SELECT x.*, s.CODE AS src
      FROM ssdb_integration.lr_strategy.union_base x JOIN ssdb_integration.lr_strategy.synthetic_key s ON s.KIND = 'SOURCE' AND s.VALUE = x.source),
f1 AS (SELECT u.mm_opp, fk.n_cbd, fk.key_review FROM u LEFT JOIN fk ON fk.id_type = 'CBD_ID' AND fk.id = TO_CHAR(u.cbd_id)
       WHERE u.src = 'firm_1' AND u.mm_opp IS NOT NULL),
f2 AS (SELECT o.mm_opp, fk.n_cbd, fk.key_review FROM ssdb_integration.lr_strategy.tmp_opp_f2_final o
       LEFT JOIN fk ON fk.id_type = 'CBD_ID' AND fk.id = TO_CHAR(o.cbd_id)),
s1 AS (SELECT VALUE AS V FROM k WHERE KIND = 'SOURCE' AND CODE = 'firm_1'),
s2 AS (SELECT VALUE AS V FROM k WHERE KIND = 'SOURCE' AND CODE = 'firm_2'),
d AS (SELECT NUM AS D FROM k WHERE KIND = 'divisor' AND VALUE = 'MM_OPP'),
dm AS (              -- as in statement 6
  SELECT a.VALUE AS FILE_DIST_CH, m.GONE
  FROM (VALUES ('O2_01', FALSE), ('O2_02', FALSE), ('O2_03', FALSE), ('O2_04', FALSE), ('O2_05', TRUE)) m(FILE_CODE, GONE)
  CROSS JOIN s2
  JOIN k a ON a.KIND = 'DIST_CH' AND a.SOURCE = s2.V AND a.CODE = m.FILE_CODE),
pv AS (SELECT a.VALUE AS VA, b.VALUE AS VARIABLE
       FROM k a JOIN k b ON b.KIND = 'PRODUCT_V2' AND b.CODE = 'PR02' WHERE a.KIND = 'PRODUCT_V2' AND a.CODE = 'PR05'),
uo AS (SELECT * FROM ssdb_integration.lr_strategy.UNION_OPP),
fov AS (SELECT TO_CHAR(CBD_ID) AS CBD_ID, DIST_CH, NEW_DIST FROM ssdb_integration.lr_strategy.tmp_firm_override),
ch1 AS (             -- as in statement 6
  SELECT u.NEW_DIST, MAX(u.CHANNEL) AS CHANNEL
  FROM ssdb_integration.lr_strategy.union_base u JOIN s1 ON u.SOURCE = s1.V
  WHERE u.NEW_DIST IS NOT NULL
  GROUP BY u.NEW_DIST HAVING COUNT(DISTINCT COALESCE(u.CHANNEL, '~')) = 1),
src AS (             -- union_base as UNION_OPP should carry it: firm_2's VA as VARIABLE (Q8), the firm overrides
  SELECT u.* REPLACE (CASE WHEN u.SOURCE = s2.V AND u.PRODUCT_V2 = pv.VA THEN pv.VARIABLE ELSE u.PRODUCT_V2 END AS PRODUCT_V2,
                      CASE WHEN fv.CBD_ID IS NOT NULL AND u.SOURCE = s1.V THEN fv.DIST_CH ELSE u.DIST_CH END AS DIST_CH,
                      CASE WHEN fv.CBD_ID IS NOT NULL THEN fv.NEW_DIST ELSE u.NEW_DIST END AS NEW_DIST,
                      CASE WHEN fv.CBD_ID IS NOT NULL THEN fc.CHANNEL ELSE u.CHANNEL END AS CHANNEL)
  FROM ssdb_integration.lr_strategy.union_base u CROSS JOIN s1 CROSS JOIN s2 CROSS JOIN pv
  LEFT JOIN fov fv ON fv.CBD_ID = TO_CHAR(u.CBD_ID)
  LEFT JOIN ch1 fc ON fc.NEW_DIST = fv.NEW_DIST),
fo AS (              -- tmp_opp_f2_final with its drop reason
  SELECT f.*, CASE WHEN dm.GONE IS NULL THEN 'FILE_DIST_CH in no map' WHEN dm.GONE THEN 'NO CHANNEL'
                   WHEN f.PRODUCT_LINE = 'FIXED' THEN 'FIXED' END AS DROP_REASON
  FROM ssdb_integration.lr_strategy.tmp_opp_f2_final f LEFT JOIN dm ON dm.FILE_DIST_CH = f.FILE_DIST_CH),
ap AS (SELECT uo.* FROM uo JOIN s2 ON uo.SOURCE = s2.V WHERE uo.ROW_ORIGIN <> 'union'),   -- firm_2 rows carrying file opportunity
ot AS (SELECT SUM(MM_OPP) AS O FROM uo JOIN s2 ON uo.SOURCE = s2.V),
g AS (               -- the rows carrying file opportunity by each lineage column
  SELECT 'ROW_ORIGIN' AS DIM, ROW_ORIGIN AS V, MM_OPP FROM ap
  UNION ALL SELECT 'CHANNEL_RULE', CHANNEL_RULE, MM_OPP FROM ap
  UNION ALL SELECT 'FILE_NEW_DIST', FILE_NEW_DIST, MM_OPP FROM ap
  UNION ALL SELECT 'CRD_RULE', CRD_RULE, MM_OPP FROM ap
  UNION ALL SELECT 'N_HOLDERS', CAST(N_HOLDERS AS VARCHAR), MM_OPP FROM ap),
sc AS (              -- ACTUAL_SALES_AMOUNT by SOURCE x CHANNEL x PRODUCT_V2: UNION_OPP minus the source
  SELECT SOURCE, CHANNEL, PRODUCT_V2, SUM(S) AS DIFF
  FROM (SELECT SOURCE, CHANNEL, PRODUCT_V2, ACTUAL_SALES_AMOUNT AS S FROM uo
        UNION ALL SELECT SOURCE, CHANNEL, PRODUCT_V2, -ACTUAL_SALES_AMOUNT FROM src) x
  GROUP BY SOURCE, CHANNEL, PRODUCT_V2),
-- Row identity without EXCEPT: Snowflake's docs say neither how MINUS / EXCEPT compare NULLs nor whether they keep
-- duplicates (docs, Set operators, read 2026-10-25).  HASH "never returns NULL, even for NULL inputs" and takes * EXCLUDE (docs, HASH), so counting rows per
-- hash on each side compares the two tables as multisets, NULL-safe.  NUMBER values hash alike whatever their
-- precision and scale; a column whose type changes kind (FLOAT <-> NUMBER) would make every row differ (loud).
hs AS (SELECT H, MAX(SOURCE) AS SOURCE, COUNT(*) AS N, COUNT(MM_OPP) AS NM, SUM(MM_OPP) AS S
       FROM (SELECT HASH(* EXCLUDE (MM_OPP)) AS H, SOURCE, MM_OPP FROM src) x GROUP BY H),
hu AS (SELECT H, MAX(SOURCE) AS SOURCE, COUNT(*) AS N, COUNT(MM_OPP) AS NM, SUM(MM_OPP) AS S
       FROM (SELECT HASH(* EXCLUDE (MM_OPP, ROW_ORIGIN, FILE_NEW_DIST, CHANNEL_RULE, N_HOLDERS, FIRM_KEY, FIRM_CRD, CRD_RULE, FIRM_OVERRIDE)) AS H, SOURCE, MM_OPP
             FROM uo WHERE ROW_ORIGIN <> 'opp file') x GROUP BY H),
hd AS (SELECT COALESCE(hs.SOURCE, hu.SOURCE) AS SOURCE, COALESCE(hs.N, 0) AS NS, COALESCE(hu.N, 0) AS NU,
              COALESCE(hs.NM, 0) AS NMS, COALESCE(hu.NM, 0) AS NMU, COALESCE(hs.S, 0) AS SS, COALESCE(hu.S, 0) AS SU
       FROM hs FULL OUTER JOIN hu ON hu.H = hs.H),
chk_f2 AS (
    SELECT 'firm_2 rows: file minus opp_base' AS CHECK_NAME,
           (SELECT n FROM o) - (SELECT COUNT(*) FROM b2) AS VALUE, 1 AS MUST_BE_ZERO
    UNION ALL SELECT 'firm_2 OPP: file minus opp_base', ROUND((SELECT opp FROM o) - (SELECT opp FROM t), 2), 1
    UNION ALL SELECT 'firm_1 rows: vendor table (fiscal years of the query) minus opp_base',
           (SELECT COUNT(*) FROM life_prod.lif_murkylake.wc_market_metrics_opportunity WHERE TO_CHAR(fiscal_yr) IN ('2024', '2025'))
         - (SELECT COUNT(*) FROM b WHERE src = 'firm_1'), 1
    UNION ALL SELECT 'firm_2 % of OPP with no product (no branch of the product CASE)', ROUND(100 * COALESCE((SELECT SUM(global_sales) FROM b2 WHERE product_line IS NULL), 0) / (SELECT opp FROM t), 2), 1
    UNION ALL SELECT 'firm_2 % of non-fixed OPP whose product differs from the settled map',
           (SELECT ROUND(100 * COALESCE(SUM(CASE WHEN b2.product_line IS DISTINCT FROM pm.PRODUCT_V2 THEN b2.global_sales END), 0)
                         / SUM(b2.global_sales), 2)
            FROM b2 LEFT JOIN pm ON pm.PL = b2.file_product_line AND pm.VA IS NOT DISTINCT FROM b2.file_va_type
            WHERE b2.product_line IS DISTINCT FROM 'FIXED'), 1
    UNION ALL SELECT 'firm_2 OPP: opp_base with a company minus tmp_opp_f2_final',
           ROUND((SELECT SUM(global_sales) FROM b2 WHERE original_cbd_id IS NOT NULL)
               - (SELECT SUM(mm_opp) FROM ssdb_integration.lr_strategy.tmp_opp_f2_final), 2), 1
    UNION ALL SELECT 'firm_2 % of OPP: from firm_1''s vendor rows of the same ZIP x CRD x broker name x product', ROUND(100 * COALESCE((SELECT SUM(global_sales) FROM b2 WHERE cbd_method = 'vendor cell'), 0) / (SELECT opp FROM t), 2), 0
    UNION ALL SELECT 'firm_2 % of OPP: from firm_1''s vendor rows of the same ZIP x CRD x broker name, other product', ROUND(100 * COALESCE((SELECT SUM(global_sales) FROM b2 WHERE cbd_method = 'vendor ZIP x CRD x broker'), 0) / (SELECT opp FROM t), 2), 0
    UNION ALL SELECT 'firm_2 rows with neither a dist_ch nor a review reason',
           (SELECT COUNT(*) FROM b2 WHERE dist_ch IS NULL AND dist_review IS NULL), 1
    UNION ALL SELECT 'firm_2 % of OPP: company from crd_cbd_mm (no vendor row there)', ROUND(100 * COALESCE((SELECT SUM(global_sales) FROM b2 WHERE cbd_method = 'crd_cbd_mm'), 0) / (SELECT opp FROM t), 2), 0
    UNION ALL SELECT 'firm_2 % of OPP: no company, dropped by opp_grouped (as firm_1''s)', ROUND(100 * COALESCE((SELECT SUM(global_sales) FROM b2 WHERE original_cbd_id IS NULL), 0) / (SELECT opp FROM t), 2), 0
    UNION ALL SELECT 'firm_2 % of OPP whose firm_1 cell carries 2+ companies (the largest taken)', ROUND(100 * COALESCE((SELECT SUM(global_sales) FROM b2 WHERE n_co > 1), 0) / (SELECT opp FROM t), 2), 0
    UNION ALL SELECT 'firm_2 % of OPP with a | list of companies', ROUND(100 * COALESCE((SELECT SUM(global_sales) FROM b2 WHERE original_cbd_id LIKE '%|%'), 0) / (SELECT opp FROM t), 2), 0
    UNION ALL SELECT 'override rows: the same CRD x broker name twice',
           (SELECT COUNT(*) FROM (SELECT firm_crd, broker_name FROM ssdb_integration.lr_strategy.crd_dist_override
                                  GROUP BY firm_crd, broker_name HAVING COUNT(*) > 1) x), 1
    UNION ALL SELECT 'override rows that set no firm_2 row (CRD given one dist_ch by firm_1, or not in firm_2''s file)',
           (SELECT COUNT(*) FROM ssdb_integration.lr_strategy.crd_dist_override o
            WHERE NOT EXISTS (SELECT 1 FROM b2 WHERE b2.firm_crd = TO_CHAR(o.firm_crd) AND b2.dist_source = 'manual override'
                              AND (o.broker_name IS NULL OR b2.broker_name = o.broker_name))), 1
    UNION ALL SELECT 'override rows whose dist_ch is none of firm_1''s for the CRD',
           (SELECT COUNT(*) FROM ssdb_integration.lr_strategy.crd_dist_override o
            WHERE NOT EXISTS (SELECT 1 FROM b WHERE b.src = 'firm_1' AND b.firm_crd = TO_CHAR(o.firm_crd)
                              AND b.dist_ch = TO_CHAR(o.dist_ch))), 0
    UNION ALL SELECT 'firm_2 % of OPP: dist_ch from firm_1, one for the CRD', ROUND(100 * COALESCE((SELECT SUM(global_sales) FROM b2 WHERE dist_source = 'firm_1 CRD'), 0) / (SELECT opp FROM t), 2), 0
    UNION ALL SELECT 'firm_2 % of OPP: dist_ch from the manual override', ROUND(100 * COALESCE((SELECT SUM(global_sales) FROM b2 WHERE dist_source = 'manual override'), 0) / (SELECT opp FROM t), 2), 0
    UNION ALL SELECT 'firm_2 % of OPP for review: no firm_1 rows for the CRD', ROUND(100 * COALESCE((SELECT SUM(global_sales) FROM b2 WHERE dist_review = 'no firm_1 rows for the CRD'), 0) / (SELECT opp FROM t), 2), 0
    UNION ALL SELECT 'firm_2 % of OPP for review: firm_1 rows of the CRD carry 2+ dist_ch', ROUND(100 * COALESCE((SELECT SUM(global_sales) FROM b2 WHERE dist_review = 'firm_1 rows of the CRD carry 2+ dist_ch'), 0) / (SELECT opp FROM t), 2), 0
    UNION ALL SELECT 'firm_2 % of OPP for review: firm_1 rows of the CRD have a blank dist_ch', ROUND(100 * COALESCE((SELECT SUM(global_sales) FROM b2 WHERE dist_review = 'firm_1 rows of the CRD have a blank dist_ch'), 0) / (SELECT opp FROM t), 2), 0
    UNION ALL SELECT 'firm_2 % of OPP with a firm_1 cell (ZIP x CRD x broker name x product): OPP equal to firm_1''s to 3 decimals of coded units',
           (SELECT ROUND(100 * COALESCE(SUM(CASE WHEN ROUND(f2p.opp / d.D_OPP, 3) = ROUND(f1p.opp / d.D_OPP, 3) THEN f2p.opp END), 0)
                         / SUM(f2p.opp), 2)
            FROM f2p CROSS JOIN (SELECT NUM AS D_OPP FROM k WHERE KIND = 'divisor' AND VALUE = 'MM_OPP') d
            JOIN f1p ON f1p.zip = f2p.zip AND f1p.firm_crd = f2p.firm_crd AND f1p.broker_name = f2p.broker_name
                             AND f1p.product_line = f2p.product_line), 0
),
chk_key AS (
    SELECT 'links whose CRD and CBD_ID have different FIRM_KEY (passes not enough)' AS CHECK_NAME,
           (SELECT COUNT(*) FROM e JOIN fk a ON a.id_type = 'CRD' AND a.id = e.crd
                                   JOIN fk b ON b.id_type = 'CBD_ID' AND b.id = e.cbd
            WHERE a.firm_key <> b.firm_key) AS VALUE, 1 AS MUST_BE_ZERO
    UNION ALL SELECT 'IDs listed twice',
           (SELECT COUNT(*) FROM (SELECT id_type, id FROM fk GROUP BY id_type, id HAVING COUNT(*) > 1) x), 1
    UNION ALL SELECT 'links with a CRD or CBD_ID with no FIRM_KEY',
           (SELECT COUNT(*) FROM e
            WHERE e.crd IS NOT NULL AND e.cbd IS NOT NULL
              AND (NOT EXISTS (SELECT 1 FROM fk WHERE fk.id_type = 'CRD' AND fk.id = e.crd)
                   OR NOT EXISTS (SELECT 1 FROM fk WHERE fk.id_type = 'CBD_ID' AND fk.id = e.cbd))), 1
    UNION ALL SELECT 'union_base CBD_IDs with no FIRM_KEY',
           (SELECT COUNT(DISTINCT TO_CHAR(u.cbd_id)) FROM u
            WHERE u.cbd_id IS NOT NULL
              AND NOT EXISTS (SELECT 1 FROM fk WHERE fk.id_type = 'CBD_ID' AND fk.id = TO_CHAR(u.cbd_id))), 1
    UNION ALL SELECT 'FIRM_KEYs', (SELECT COUNT(DISTINCT firm_key) FROM fk), 0
    UNION ALL SELECT 'FIRM_KEYs joining 2+ CBD_IDs', (SELECT COUNT(DISTINCT firm_key) FROM fk WHERE n_cbd > 1), 0
    UNION ALL SELECT 'FIRM_KEYs for review (2+ PARENT)', (SELECT COUNT(DISTINCT firm_key) FROM fk WHERE key_review IS NOT NULL), 0
    UNION ALL SELECT 'most CBD_IDs in one FIRM_KEY', (SELECT MAX(n_cbd) FROM fk), 0
    UNION ALL SELECT 'most CRDs in one FIRM_KEY', (SELECT MAX(n_crd) FROM fk), 0
    UNION ALL SELECT 'firm_1 % of MM_OPP (union_base) in FIRM_KEYs joining 2+ CBD_IDs',
           (SELECT ROUND(100 * COALESCE(SUM(CASE WHEN n_cbd > 1 THEN mm_opp END), 0) / SUM(mm_opp), 2) FROM f1), 0
    UNION ALL SELECT 'firm_2 % of MM_OPP (tmp_opp_f2_final) in FIRM_KEYs joining 2+ CBD_IDs',
           (SELECT ROUND(100 * COALESCE(SUM(CASE WHEN n_cbd > 1 THEN mm_opp END), 0) / SUM(mm_opp), 2) FROM f2), 0
    UNION ALL SELECT 'firm_1 % of MM_OPP (union_base) in FIRM_KEYs for review',
           (SELECT ROUND(100 * COALESCE(SUM(CASE WHEN key_review IS NOT NULL THEN mm_opp END), 0) / SUM(mm_opp), 2) FROM f1), 0
    UNION ALL SELECT 'firm_2 % of MM_OPP (tmp_opp_f2_final) in FIRM_KEYs for review',
           (SELECT ROUND(100 * COALESCE(SUM(CASE WHEN key_review IS NOT NULL THEN mm_opp END), 0) / SUM(mm_opp), 2) FROM f2), 0
),
chk_union AS (
    SELECT 'union_base rows not found in UNION_OPP with every column but MM_OPP unchanged, plus rows added or repeated'
           AS CHECK_NAME,
           (SELECT SUM(ABS(NS - NU)) FROM hd) AS VALUE, TRUE AS MUST_BE_ZERO
    UNION ALL SELECT 'firm_1 rows whose MM_OPP changed (row groups by hash)',
           (SELECT COUNT(*) FROM hd WHERE SOURCE IN (SELECT V FROM s1)
              AND (NS <> NU OR NMS <> NMU OR ABS(SS - SU) > 1e-9 * GREATEST(ABS(SS), ABS(SU), 1))), TRUE
    UNION ALL SELECT 'firm_2 rows of union_base carrying MM_OPP (union_base is the union without firm_2 opportunity)',
           (SELECT COUNT(*) FROM src JOIN s2 ON src.SOURCE = s2.V WHERE src.MM_OPP IS NOT NULL), TRUE
    UNION ALL SELECT 'ACTUAL_SALES_AMOUNT cells (SOURCE x CHANNEL x PRODUCT_V2) different from the source',
           (SELECT COUNT(*) FROM sc WHERE ABS(COALESCE(DIFF, 0)) > 0.001), TRUE     -- ponytail: 0.001 absorbs float summation order
    UNION ALL SELECT 'firm_2 MM_OPP of tmp_opp_f2_final after drops differs from firm_2 MM_OPP in UNION_OPP by more than 0.001 x divisor (1 = yes)',
           (SELECT CASE WHEN ABS(COALESCE((SELECT SUM(MM_OPP) FROM fo WHERE DROP_REASON IS NULL), 0)
                               - COALESCE((SELECT O FROM ot), 0)) > 0.001 * d.D THEN 1 ELSE 0 END FROM d), TRUE
    UNION ALL SELECT 'UNION_OPP rows with a CBD_ID and no FIRM_KEY',
           (SELECT COUNT(*) FROM uo WHERE CBD_ID IS NOT NULL AND FIRM_KEY IS NULL), TRUE
    UNION ALL SELECT 'tmp_opp_f2_final rows whose FILE_DIST_CH is in no map',
           (SELECT COUNT(*) FROM fo WHERE DROP_REASON = 'FILE_DIST_CH in no map'), TRUE
    UNION ALL SELECT 'tmp_firm_override CBD_IDs listed twice',
           (SELECT COUNT(*) FROM (SELECT CBD_ID FROM fov GROUP BY CBD_ID HAVING COUNT(*) > 1) x), TRUE
    UNION ALL SELECT 'rows of an overridden CBD_ID without its NEW_DIST, or with no CHANNEL',
           (SELECT COUNT(*) FROM uo JOIN fov ON fov.CBD_ID = TO_CHAR(uo.CBD_ID)
            WHERE uo.NEW_DIST IS DISTINCT FROM fov.NEW_DIST OR uo.CHANNEL IS NULL), TRUE
    UNION ALL SELECT 'firm_1 rows of an overridden CBD_ID without its DIST_CH',
           (SELECT COUNT(*) FROM uo JOIN s1 ON uo.SOURCE = s1.V JOIN fov ON fov.CBD_ID = TO_CHAR(uo.CBD_ID)
            WHERE uo.DIST_CH IS DISTINCT FROM fov.DIST_CH), TRUE
    UNION ALL SELECT 'rows of an overridden CBD_ID not marked FIRM_OVERRIDE',
           (SELECT COUNT(*) FROM uo JOIN fov ON fov.CBD_ID = TO_CHAR(uo.CBD_ID) WHERE uo.FIRM_OVERRIDE IS NULL), TRUE
    UNION ALL SELECT 'rows changed by a firm override: ' || uo.SOURCE, COUNT(*), FALSE
           FROM uo WHERE uo.FIRM_OVERRIDE GROUP BY uo.SOURCE
    UNION ALL SELECT 'opp-only rows with no FIRM_CRD',
           (SELECT COUNT(*) FROM ap WHERE ROW_ORIGIN = 'opp file' AND FIRM_CRD IS NULL), TRUE
    UNION ALL SELECT 'firm_2 opportunity keys carrying MM_OPP on more than one row (opp-only rows: key x NEW_DIST x CRD)',
           (SELECT COUNT(*) FROM (SELECT 1 FROM ap WHERE MM_OPP IS NOT NULL
                                  GROUP BY ZIP_CODE, DIST_CH, CBD_ID, PRODUCT_V2, CASE WHEN ROW_ORIGIN = 'opp file' THEN NEW_DIST END,
                                           CASE WHEN ROW_ORIGIN = 'opp file' THEN FIRM_CRD END
                                  HAVING COUNT(*) > 1) x), TRUE
    UNION ALL SELECT 'opp-only rows with NULL DIST_CH, PRODUCT_V2 or NEW_DIST',
           (SELECT COUNT(*) FROM ap WHERE ROW_ORIGIN = 'opp file'
              AND (DIST_CH IS NULL OR PRODUCT_V2 IS NULL OR NEW_DIST IS NULL)), TRUE
    UNION ALL SELECT 'opp-only rows with no CHANNEL: firm_1''s union rows carry no single CHANNEL for their NEW_DIST (pending the CHANNEL step)',
           (SELECT COUNT(*) FROM ap WHERE ROW_ORIGIN = 'opp file' AND CHANNEL IS NULL), TRUE
    UNION ALL SELECT 'firm_2 rows of UNION_OPP still with firm_2''s VA product (Q8: counted as VARIABLE)',
           (SELECT COUNT(*) FROM uo CROSS JOIN pv JOIN s2 ON uo.SOURCE = s2.V WHERE uo.PRODUCT_V2 = pv.VA), TRUE
    UNION ALL SELECT 'firm_2 union rows with VA, counted as VARIABLE (Q8)',
           (SELECT COUNT(*) FROM ssdb_integration.lr_strategy.union_base u CROSS JOIN pv JOIN s2 ON u.SOURCE = s2.V
            WHERE u.PRODUCT_V2 = pv.VA), FALSE
    UNION ALL SELECT 'firm_2 percent of MM_OPP on opp-only rows with no CHANNEL, NEW_DIST ' || COALESCE(NEW_DIST, 'NULL'),
           ROUND(100 * SUM(MM_OPP) / MAX(ot.O), 2), FALSE
           FROM ap CROSS JOIN ot WHERE ROW_ORIGIN = 'opp file' AND CHANNEL IS NULL GROUP BY NEW_DIST
    UNION ALL SELECT 'firm_2 percent of MM_OPP on sales rows whose NEW_DIST differs from the file''s new_dist',
           (SELECT ROUND(100 * COALESCE(SUM(MM_OPP), 0) / MAX(ot.O), 2) FROM ap CROSS JOIN ot
            WHERE ROW_ORIGIN = 'union + opp file' AND FILE_NEW_DIST IS NOT NULL AND NEW_DIST IS DISTINCT FROM FILE_NEW_DIST), FALSE
    UNION ALL SELECT 'firm_2 percent of MM_OPP on sales rows whose key carries 2+ new_dist in the file',
           (SELECT ROUND(100 * COALESCE(SUM(MM_OPP), 0) / MAX(ot.O), 2) FROM ap CROSS JOIN ot
            WHERE ROW_ORIGIN = 'union + opp file' AND FILE_NEW_DIST IS NULL), FALSE
    UNION ALL SELECT 'CBD_IDs with 2+ FIRM in one SOURCE',
           (SELECT COUNT(*) FROM (SELECT CBD_ID, SOURCE FROM src
                                  WHERE CBD_ID IS NOT NULL GROUP BY CBD_ID, SOURCE HAVING COUNT(DISTINCT FIRM) > 1) x), TRUE
    UNION ALL SELECT 'firm_2 rows carrying file opportunity with no FIRM',
           (SELECT COUNT(*) FROM ap WHERE FIRM IS NULL), FALSE
    UNION ALL SELECT 'firm_2 percent of MM_OPP on rows with no FIRM',
           (SELECT ROUND(100 * SUM(MM_OPP) / MAX(ot.O), 2) FROM ap CROSS JOIN ot WHERE FIRM IS NULL), FALSE
    UNION ALL SELECT 'CBD_IDs in union_base and crd_cbd: percent whose crd_cbd firm name equals the union FIRM',
           (SELECT ROUND(100 * AVG(CASE WHEN c.FIRM = u.FIRM THEN 1 ELSE 0 END), 1)
            FROM (SELECT CBD_ID, MAX(FIRM) AS FIRM FROM src WHERE CBD_ID IS NOT NULL GROUP BY CBD_ID) u
            JOIN (SELECT CAST(CBD_ID AS VARCHAR) AS CBD_ID, MAX(FIRM) AS FIRM FROM ssdb_integration.lr_strategy.crd_cbd
                  WHERE CBD_ID IS NOT NULL GROUP BY 1) c ON c.CBD_ID = u.CBD_ID), FALSE
    UNION ALL SELECT 'dropped tmp_opp_f2_final rows: ' || DROP_REASON, COUNT(*), FALSE
           FROM fo WHERE DROP_REASON IS NOT NULL GROUP BY DROP_REASON
    UNION ALL SELECT 'dropped MM_OPP in coded units: ' || DROP_REASON, ROUND(SUM(MM_OPP) / MAX(d.D), 1), FALSE
           FROM fo CROSS JOIN d WHERE DROP_REASON IS NOT NULL GROUP BY DROP_REASON
    UNION ALL SELECT 'firm_2 rows by ' || DIM || ': ' || COALESCE(V, 'NULL'), COUNT(*), FALSE FROM g GROUP BY DIM, V
    UNION ALL SELECT 'firm_2 percent of MM_OPP by ' || DIM || ': ' || COALESCE(V, 'NULL'),
           ROUND(100 * SUM(MM_OPP) / MAX(ot.O), 1), FALSE FROM g CROSS JOIN ot GROUP BY DIM, V
    UNION ALL SELECT 'percent of ' || s.SRC_NAME || ' ACTUAL_SALES_AMOUNT on rows that carry MM_OPP',
           ROUND(100 * SUM(CASE WHEN uo.MM_OPP IS NOT NULL THEN uo.ACTUAL_SALES_AMOUNT END) / SUM(uo.ACTUAL_SALES_AMOUNT), 1), FALSE
           FROM uo JOIN (SELECT V, 'firm_1' AS SRC_NAME FROM s1 UNION ALL SELECT V, 'firm_2' FROM s2) s ON uo.SOURCE = s.V
           GROUP BY s.SRC_NAME
    UNION ALL SELECT 'firm_1 percent of MM_OPP by CRD_RULE: ' || COALESCE(uo.CRD_RULE, 'NULL'),
           ROUND(100 * SUM(uo.MM_OPP) / MAX(t1.O), 1), FALSE
           FROM uo JOIN s1 ON uo.SOURCE = s1.V
           CROSS JOIN (SELECT SUM(u.MM_OPP) AS O FROM uo u JOIN s1 ON u.SOURCE = s1.V) t1
           GROUP BY uo.CRD_RULE
    UNION ALL SELECT 'firm_2 MM_OPP in coded units', ROUND((SELECT O FROM ot) / (SELECT D FROM d), 1), FALSE
    UNION ALL SELECT 'firm_1 MM_OPP in coded units',
           ROUND((SELECT SUM(u.MM_OPP) FROM src u JOIN s1 ON u.SOURCE = s1.V) / (SELECT D FROM d), 1), FALSE
)
SELECT 'tmp_opp_base_both, tmp_opp_f2_final' AS STEP, CHECK_NAME, VALUE, MUST_BE_ZERO FROM chk_f2
UNION ALL SELECT 'tmp_firm_key', CHECK_NAME, VALUE, MUST_BE_ZERO FROM chk_key
UNION ALL SELECT 'UNION_OPP', CHECK_NAME, VALUE, CASE WHEN MUST_BE_ZERO THEN 1 ELSE 0 END FROM chk_union
ORDER BY MUST_BE_ZERO DESC, STEP, CHECK_NAME;
