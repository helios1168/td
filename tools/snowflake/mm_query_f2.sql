use secondary roles all;

--firm_2's opportunity file through the opportunity steps of the firm_1 query (mm_query.sql, opp_base .. opp_final).
--The steps are copied as written; every change is marked --f2:.  Kept out of the repo, like mm_query.sql.
--firm_2's file has no company, client firm ID or state, and names its channels differently from the vendor table
--(2026-10-25 run: 3.58% of its OPP had firm_1's dist_ch).  So each firm_2 row takes them from firm_1's vendor rows
--of the same ZIP x CRD x broker name x product, else of the same ZIP x CRD x broker name, else crd_cbd_mm (company
--only), and then goes through the query's rules like a firm_1 row.  Its own channel stays in FILE_DIST_CH.
--Statement 1  ssdb_integration.lr_strategy.opp_base_both: both firms' rows through one opp_base.
--Statement 2  ssdb_integration.lr_strategy.opp_f2_final: firm_2's rows through opp_grouped .. opp_final.
--Statement 3  checks: every MUST_BE_ZERO = 1 row must be 0.   Statement 4  dist_ch: firm_2's own, firm_1's, the rules'.

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
        TO_CHAR(v.cbd_id) AS cbd_id, TO_CHAR(v.client_firm_id) AS client_firm_id, TO_CHAR(v.dist_ch) AS dist_ch,
        SUM(v.global_sales) AS opp
    FROM life_prod.lif_murkylake.wc_market_metrics_opportunity v
    JOIN product_map pm ON pm.pl IS NOT DISTINCT FROM TO_CHAR(v.product_line)
                       AND pm.va IS NOT DISTINCT FROM TO_CHAR(v.va_product_type)
    WHERE TO_CHAR(v.fiscal_yr) IN ('2024', '2025')
    GROUP BY LPAD(TRIM(TO_CHAR(zip_code)), 5, '0'), TO_CHAR(v.firm_crd), v.broker_name, pm.product, TO_CHAR(v.cbd_id), TO_CHAR(v.client_firm_id), TO_CHAR(v.dist_ch)
),

vendor_cell AS (   --f2: per ZIP x CRD x broker name x product, the company and dist_ch carrying most opportunity; N_CO = how many
    SELECT zip_code, firm_crd, broker_name, product, cbd_id, client_firm_id, dist_ch, n_co
    FROM (
        SELECT zip_code, firm_crd, broker_name, product, cbd_id, client_firm_id, dist_ch
            , COUNT(*) OVER (PARTITION BY zip_code, firm_crd, broker_name, product) AS n_co
            , ROW_NUMBER() OVER (PARTITION BY zip_code, firm_crd, broker_name, product ORDER BY opp DESC, cbd_id, client_firm_id, dist_ch) AS rk
        FROM (SELECT zip_code, firm_crd, broker_name, product, cbd_id, client_firm_id, dist_ch, SUM(opp) AS opp
              FROM vendor_g GROUP BY zip_code, firm_crd, broker_name, product, cbd_id, client_firm_id, dist_ch)
    )
    WHERE rk = 1
),

vendor_key AS (   --f2: the same per ZIP x CRD x broker name, for a product firm_1 has no row of there
    SELECT zip_code, firm_crd, broker_name, cbd_id, client_firm_id, dist_ch, n_co
    FROM (
        SELECT zip_code, firm_crd, broker_name, cbd_id, client_firm_id, dist_ch
            , COUNT(*) OVER (PARTITION BY zip_code, firm_crd, broker_name) AS n_co
            , ROW_NUMBER() OVER (PARTITION BY zip_code, firm_crd, broker_name ORDER BY opp DESC, cbd_id, client_firm_id, dist_ch) AS rk
        FROM (SELECT zip_code, firm_crd, broker_name, cbd_id, client_firm_id, dist_ch, SUM(opp) AS opp
              FROM vendor_g GROUP BY zip_code, firm_crd, broker_name, cbd_id, client_firm_id, dist_ch)
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
        TO_CHAR(dist_ch) AS in_dist_ch, TO_CHAR(dist_ch) AS file_dist_ch, TO_CHAR(product_line) AS file_product_line,
        TO_CHAR(va_product_type) AS file_va_type, 'vendor' AS cbd_method, 1 AS n_co
    FROM life_prod.lif_murkylake.wc_market_metrics_opportunity
    UNION ALL
    SELECT 'firm_2',
        f.pl_vendor, TO_CHAR(f.va_product_type),
        CASE WHEN c.zip_code IS NOT NULL THEN c.cbd_id WHEN k.zip_code IS NOT NULL THEN k.cbd_id ELSE m.cbd_id END,
        CASE WHEN c.zip_code IS NOT NULL THEN c.client_firm_id WHEN k.zip_code IS NOT NULL THEN k.client_firm_id END,
        TO_CHAR(f.firm_crd), f.broker_name,
        CASE WHEN c.zip_code IS NOT NULL THEN c.dist_ch WHEN k.zip_code IS NOT NULL THEN k.dist_ch END,   --NULL: no firm_1 row
        '2025', f.zip5, st.state, f.opp, CAST(NULL AS VARCHAR),
        CASE WHEN c.zip_code IS NOT NULL THEN c.dist_ch WHEN k.zip_code IS NOT NULL THEN k.dist_ch END,
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
        src, in_dist_ch, file_dist_ch, file_product_line, file_va_type, cbd_method, n_co   --f2: carried for the checks
    FROM opp_source
    WHERE TO_CHAR(fiscal_yr) IN ('2024', '2025')
)

SELECT * FROM opp_base
);

--Statement 2.
CREATE OR REPLACE TABLE ssdb_integration.lr_strategy.opp_f2_final AS (
WITH
opp_base AS (SELECT * FROM ssdb_integration.lr_strategy.opp_base_both WHERE src = 'firm_2'),

sales_keys AS (   --f2: firm_2's sales, from union_base (firm_1's come from its sales table)
    SELECT DISTINCT
        TO_CHAR(u.fiscal_yr) AS fiscal_yr,
        LPAD(TRIM(TO_CHAR(u.zip_code)), 5, '0') AS zip_code,
        TO_CHAR(u.cbd_id) AS cbd_id,
        u.product_v2,
        u.state
    FROM ssdb_integration.lr_strategy.union_base u
    JOIN ssdb_integration.lr_strategy.synthetic_key s ON s.KIND = 'SOURCE' AND s.CODE = 'firm_2' AND s.VALUE = u.source
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
        broker_name
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
        os.broker_name
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
                broker_name
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
        SUM(mm_opp) AS mm_opp
    FROM opp_resolved
    GROUP BY
        fiscal_yr,
        LPAD(TRIM(zip_code::VARCHAR), 5, '0'),
        state,
        product_line,
        dist_ch,
        cbd_id,
        territory
)

SELECT * FROM opp_final
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
UNION ALL SELECT 'firm_2 % of OPP: company from crd_cbd_mm, no dist_ch (no firm_1 row there)', ROUND(100 * COALESCE((SELECT SUM(global_sales) FROM b2 WHERE cbd_method = 'crd_cbd_mm'), 0) / (SELECT opp FROM t), 2), 0
UNION ALL SELECT 'firm_2 % of OPP: no company, dropped by opp_grouped (as firm_1''s)', ROUND(100 * COALESCE((SELECT SUM(global_sales) FROM b2 WHERE original_cbd_id IS NULL), 0) / (SELECT opp FROM t), 2), 0
UNION ALL SELECT 'firm_2 % of OPP whose firm_1 rows carry 2+ company x dist_ch (the largest taken)', ROUND(100 * COALESCE((SELECT SUM(global_sales) FROM b2 WHERE n_co > 1), 0) / (SELECT opp FROM t), 2), 0
UNION ALL SELECT 'firm_2 % of OPP with a | list of companies', ROUND(100 * COALESCE((SELECT SUM(global_sales) FROM b2 WHERE original_cbd_id LIKE '%|%'), 0) / (SELECT opp FROM t), 2), 0
UNION ALL SELECT 'firm_2 % of OPP whose dist_ch the query''s rules changed', ROUND(100 * COALESCE((SELECT SUM(global_sales) FROM b2 WHERE dist_ch IS DISTINCT FROM in_dist_ch), 0) / (SELECT opp FROM t), 2), 0
UNION ALL SELECT 'firm_2 % of OPP with no dist_ch after the rules', ROUND(100 * COALESCE((SELECT SUM(global_sales) FROM b2 WHERE dist_ch IS NULL), 0) / (SELECT opp FROM t), 2), 0
UNION ALL SELECT 'firm_2 % of OPP with a firm_1 cell (ZIP x CRD x broker name x product): OPP equal to firm_1''s within 1',
       (SELECT ROUND(100 * COALESCE(SUM(CASE WHEN ABS(f2p.opp - f1p.opp) < 1 THEN f2p.opp END), 0) / SUM(f2p.opp), 2)
        FROM f2p JOIN f1p ON f1p.zip = f2p.zip AND f1p.firm_crd = f2p.firm_crd AND f1p.broker_name = f2p.broker_name
                         AND f1p.product_line = f2p.product_line), 0
ORDER BY MUST_BE_ZERO DESC, CHECK_NAME;

--Statement 4.  dist_ch: firm_2's own label, firm_1's at the same cell, and the query's rules' result; share of firm_2's OPP.
WITH
b2 AS (SELECT * FROM ssdb_integration.lr_strategy.opp_base_both WHERE src = 'firm_2'),
t AS (SELECT SUM(global_sales) AS opp FROM b2)
SELECT b2.file_dist_ch AS firm_2_dist_ch, COALESCE(b2.in_dist_ch, '(no firm_1 row)') AS firm_1_dist_ch,
       b2.dist_ch AS query_dist_ch, COUNT(DISTINCT b2.firm_crd) AS crds,
       ROUND(100 * SUM(b2.global_sales) / MAX(t.opp), 2) AS pct_firm_2_opp
FROM b2
CROSS JOIN t
GROUP BY b2.file_dist_ch, COALESCE(b2.in_dist_ch, '(no firm_1 row)'), b2.dist_ch
ORDER BY pct_firm_2_opp DESC;
