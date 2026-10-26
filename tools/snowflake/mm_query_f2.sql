use secondary roles all;

--firm_2's opportunity file through the opportunity steps of the firm_1 query (mm_query.sql, opp_base .. opp_final).
--The steps are copied as written; every change is marked --f2:.  In the repo by the owner's permission (2026-10-25).
--firm_2's file has no company, client firm ID or state: each firm_2 row takes them from firm_1's vendor rows of the
--same ZIP x CRD x broker name x product, else of the same ZIP x CRD x broker name, else crd_cbd_mm (company only).
--dist_ch: firm_2's file names its channels differently from the vendor table, so a firm_2 row takes the dist_ch the
--query gives firm_1's rows of the same CRD, when they all carry one; otherwise DIST_REVIEW says why and dist_ch is
--blank, for manual review (owner, 2026-10-25).  The owner's manual dist_ch (crd_dist_override, statement 0) fills
--those rows; it never overrules a CRD firm_1 gives one dist_ch.  DIST_SOURCE says which.  firm_2's own channel stays
--in FILE_DIST_CH.
--Statement 0  (once) the table of manual dist_ch.   Statement 0b  the firm overrides (CBD_ID -> DIST_CH, NEW_DIST).
--Statement 1  ssdb_integration.lr_strategy.opp_base_both: both firms' rows through one opp_base.
--Statement 2  ssdb_integration.lr_strategy.opp_f2_final: firm_2's rows through opp_grouped .. opp_final, then the query's new_dist.
--Statement 3  checks: every MUST_BE_ZERO = 1 row must be 0.   Statement 4  dist_ch by firm_2's own channel.
--Statement 5  the CRDs for manual review.   Statement 6  new_dist against firm_1's in union_base.
--Statement 7  ssdb_integration.lr_strategy.firm_key: one key per firm across both firms.   Statement 8  its checks.
--Statement 9  the keys that join 2+ CBD_IDs, with the review flag.

--Statement 0.  Once, then fill it (Snowsight "Load data" from a CSV with these three headers, or INSERT ... VALUES).
--One row per CRD (BROKER_NAME blank: every broker name of the CRD) or per CRD x broker name (wins over the blank
--row).  DIST_CH as the query writes firm_1's (the labels in statement 5).
CREATE TABLE IF NOT EXISTS ssdb_integration.lr_strategy.crd_dist_override (FIRM_CRD VARCHAR, BROKER_NAME VARCHAR, DIST_CH VARCHAR);

--Statement 0b.  The firm overrides (owner, 2026-10-26): every row of the company, both firms, gets this DIST_CH and
--NEW_DIST (opp_f2_final in statement 2; UNION_OPP in 24, where CHANNEL follows NEW_DIST and firm_2's union rows keep
--their own DIST_CH).  One line per CBD_ID; rerun this statement after a change, then the pipeline.
CREATE OR REPLACE TABLE ssdb_integration.lr_strategy.firm_override AS
SELECT CBD_ID, DIST_CH, NEW_DIST
FROM (VALUES ('46', 'FI', 'FI')) v(CBD_ID, DIST_CH, NEW_DIST);

--Statement 1.
CREATE OR REPLACE TABLE ssdb_integration.lr_strategy.opp_base_both AS (
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

ov AS (   --f2: the owner's manual dist_ch (statement 0)
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

--Statement 2.
CREATE OR REPLACE TABLE ssdb_integration.lr_strategy.opp_f2_final AS (
WITH
opp_base AS (SELECT * FROM ssdb_integration.lr_strategy.opp_base_both WHERE src = 'firm_2'),

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

SELECT opp_final.* REPLACE (COALESCE(ovr.ov_dist_ch, opp_final.dist_ch) AS dist_ch),   --f2: the firm overrides (statement 0b)
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
           FROM ssdb_integration.lr_strategy.firm_override) ovr ON ovr.ov_cbd = opp_final.cbd_id
);

--Statement 3.  Checks.
WITH
b AS (SELECT * FROM ssdb_integration.lr_strategy.opp_base_both),
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
        FROM b2 GROUP BY zip_code, firm_crd, broker_name, product_line)
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
UNION ALL SELECT 'firm_2 OPP: opp_base with a company minus opp_f2_final',
       ROUND((SELECT SUM(global_sales) FROM b2 WHERE original_cbd_id IS NOT NULL)
           - (SELECT SUM(mm_opp) FROM ssdb_integration.lr_strategy.opp_f2_final), 2), 1
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
ORDER BY MUST_BE_ZERO DESC, CHECK_NAME;

--Statement 4.  dist_ch by firm_2's own channel; share of firm_2's OPP.
WITH
b2 AS (SELECT * FROM ssdb_integration.lr_strategy.opp_base_both WHERE src = 'firm_2'),
t AS (SELECT SUM(global_sales) AS opp FROM b2)
SELECT b2.file_dist_ch AS firm_2_dist_ch, COALESCE(b2.dist_ch, 'REVIEW: ' || b2.dist_review) AS dist_ch,
       b2.dist_source, COUNT(DISTINCT b2.firm_crd) AS crds, ROUND(100 * SUM(b2.global_sales) / MAX(t.opp), 2) AS pct_firm_2_opp
FROM b2
CROSS JOIN t
GROUP BY b2.file_dist_ch, COALESCE(b2.dist_ch, 'REVIEW: ' || b2.dist_review), b2.dist_source
ORDER BY pct_firm_2_opp DESC;

--Statement 5.  For manual review: each CRD whose firm_2 rows have no dist_ch, with firm_1's dist_ch of the CRD and
--their shares of firm_1's OPP there.
WITH
b AS (SELECT * FROM ssdb_integration.lr_strategy.opp_base_both),
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

--Statement 6.  new_dist: firm_2's (statement 2) next to firm_1's NEW_DIST in union_base at the same CBD_ID x DIST_CH,
--by firm_2's own channel; share of firm_2's OPP after opp_final.  AGREEMENT: same, differs, firm_1 2+ (union_base's
--firm_1 rows there carry 2+ NEW_DIST), no firm_1 row (none at that CBD_ID x DIST_CH, or a blank dist_ch).
WITH
f AS (SELECT * FROM ssdb_integration.lr_strategy.opp_f2_final),
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

--Statement 7.  FIRM_KEY: one key per firm across both firms' rows (owner, 2026-10-26).  A CRD and a CBD_ID are linked
--when the vendor's resolved rows put them together: firm_1's (crd_cbd_mm) and firm_2's (opp_f2_final, statement 2).
--Linked CRDs and CBD_IDs form one group (a CBD_ID of union_base with no link is a group alone), so both firms'
--opportunity of a CRD lands in one key, and sales reach it by CBD_ID.  FIRM_KEY = the group's CBD_ID carrying the
--most opportunity.  Groups: six label passes, each carrying the smallest CBD_ID one step along the links (no
--recursion); statement 8 checks that six were enough.  One row per CBD_ID and per CRD.  KEY_REVIEW: the key's CBD_IDs
--carry 2+ PARENT in firm_1's rows (a link may chain two firms), for manual review.
CREATE OR REPLACE TABLE ssdb_integration.lr_strategy.firm_key AS (
WITH
e AS (   --the links, with their opportunity
    SELECT crd, cbd, SUM(opp) AS opp
    FROM (SELECT TO_CHAR(firm_crd) AS crd, TO_CHAR(cbd_id) AS cbd, mm_opp AS opp FROM ssdb_integration.lr_strategy.crd_cbd_mm
          UNION ALL
          SELECT TO_CHAR(firm_crd), TO_CHAR(cbd_id), mm_opp FROM ssdb_integration.lr_strategy.opp_f2_final) x
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

--Statement 8.  FIRM_KEY checks.  Every MUST_BE_ZERO = 1 row must be 0.  If the first fails, the links are longer
--than six passes reach: copy the r6/c6 pair as r7/c7 (and so on) and read the last one in g.
WITH
fk AS (SELECT * FROM ssdb_integration.lr_strategy.firm_key),
e AS (SELECT TO_CHAR(firm_crd) AS crd, TO_CHAR(cbd_id) AS cbd FROM ssdb_integration.lr_strategy.crd_cbd_mm
      UNION SELECT TO_CHAR(firm_crd), TO_CHAR(cbd_id) FROM ssdb_integration.lr_strategy.opp_f2_final),
u AS (SELECT x.*, s.CODE AS src
      FROM ssdb_integration.lr_strategy.union_base x JOIN ssdb_integration.lr_strategy.synthetic_key s ON s.KIND = 'SOURCE' AND s.VALUE = x.source),
f1 AS (SELECT u.mm_opp, fk.n_cbd, fk.key_review FROM u LEFT JOIN fk ON fk.id_type = 'CBD_ID' AND fk.id = TO_CHAR(u.cbd_id)
       WHERE u.src = 'firm_1' AND u.mm_opp IS NOT NULL),
f2 AS (SELECT o.mm_opp, fk.n_cbd, fk.key_review FROM ssdb_integration.lr_strategy.opp_f2_final o
       LEFT JOIN fk ON fk.id_type = 'CBD_ID' AND fk.id = TO_CHAR(o.cbd_id))
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
UNION ALL SELECT 'firm_2 % of MM_OPP (opp_f2_final) in FIRM_KEYs joining 2+ CBD_IDs',
       (SELECT ROUND(100 * COALESCE(SUM(CASE WHEN n_cbd > 1 THEN mm_opp END), 0) / SUM(mm_opp), 2) FROM f2), 0
UNION ALL SELECT 'firm_1 % of MM_OPP (union_base) in FIRM_KEYs for review',
       (SELECT ROUND(100 * COALESCE(SUM(CASE WHEN key_review IS NOT NULL THEN mm_opp END), 0) / SUM(mm_opp), 2) FROM f1), 0
UNION ALL SELECT 'firm_2 % of MM_OPP (opp_f2_final) in FIRM_KEYs for review',
       (SELECT ROUND(100 * COALESCE(SUM(CASE WHEN key_review IS NOT NULL THEN mm_opp END), 0) / SUM(mm_opp), 2) FROM f2), 0
ORDER BY MUST_BE_ZERO DESC, CHECK_NAME;

--Statement 9.  The FIRM_KEYs joining 2+ CBD_IDs: each CBD_ID with firm_1's FIRM and PARENT, the CRDs with their
--broker names, each firm's share of opportunity, and the review flag.  Names: read at work, never copied here.
WITH
fk AS (SELECT * FROM ssdb_integration.lr_strategy.firm_key WHERE n_cbd > 1),
u AS (SELECT x.*, s.CODE AS src
      FROM ssdb_integration.lr_strategy.union_base x JOIN ssdb_integration.lr_strategy.synthetic_key s ON s.KIND = 'SOURCE' AND s.VALUE = x.source),
nm AS (SELECT TO_CHAR(cbd_id) AS cbd, MAX(firm) AS firm, MAX(parent) AS parent FROM u
       WHERE src = 'firm_1' AND cbd_id IS NOT NULL GROUP BY TO_CHAR(cbd_id)),
o1 AS (SELECT TO_CHAR(cbd_id) AS cbd, SUM(mm_opp) AS opp FROM u WHERE src = 'firm_1' GROUP BY TO_CHAR(cbd_id)),
o2 AS (SELECT TO_CHAR(cbd_id) AS cbd, SUM(mm_opp) AS opp FROM ssdb_integration.lr_strategy.opp_f2_final GROUP BY TO_CHAR(cbd_id)),
t AS (SELECT (SELECT SUM(mm_opp) FROM u WHERE src = 'firm_1') AS t1, (SELECT SUM(mm_opp) FROM ssdb_integration.lr_strategy.opp_f2_final) AS t2),
bn AS (SELECT TO_CHAR(firm_crd) AS crd, broker_name FROM ssdb_integration.lr_strategy.crd_cbd_mm
       UNION SELECT TO_CHAR(firm_crd), broker_name FROM ssdb_integration.lr_strategy.opp_f2_final),
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
