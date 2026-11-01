use role rl_ssdb_Integration_Lr_Strategy_Rw;
use database ssdb_Integration;
use schema lr_strategy;

--Firm 1's base sales table with MGA_AGENT_CD (the owner's query of 2026-10-31, sha256
--428f51472a97..., saved as owner_sql/s1_sales_v2.sql).  Changed only where a line says EDIT
--(session, 2026-10-31): the table name as the SET variable s1_sales, two names masked, ok_policies back to policy grain, and MGA in final_output's join to agent_ticket.  Checks: the base table's
--2025 totals must equal SLS_RPT_DETAIL's (01_opportunity_sales.sql, SALES TABLE MINUS SLS_RPT_DETAIL, MUST BE 0).
/*select sum(sales_amount)/1000000 amt from LIFE_PROD.LIF_MURKYLAKE.sls_rpt_Detail m  where m.mga_agent_cd  = 'WNL0BD4400000000000'
and fiscal_yr =2025 */

use secondary roles all;

-- EDIT (session, 2026-10-31): the table name comes from a SET variable (masking: no carrier name in the repo), the
--same s1_sales that 01_opportunity_sales.sql reads.  It names the _temp table: this statement REPLACES whatever it
--names, so never the old base sales table.  Then 01_opportunity_sales.sql's two SALES TABLE MINUS SLS_RPT_DETAIL
--checks must be 0 on it.
SET s1_sales = 'ssdb_integration.lr_strategy.<firm 1 base sales, _temp>';
CREATE OR REPLACE TABLE IDENTIFIER($s1_sales) AS (
/*=========================================================
  1) Distribution channel manual assignments
  If a policy is split across exactly IFA + IMO, and only
     for INDEX / ASSURED EDGE, assign it to IFA/IMO.
  If a policy is split across exactly WIFI + IMO, assign
     it to FI/IMO.
============================================================*/
WITH distchannel_override AS (
    SELECT 
        srd.policy_no
        , srd.product_line
        , CASE WHEN COUNT(DISTINCT wst.sales_team_name) >= 2
                AND COUNT(DISTINCT CASE WHEN wst.sales_team_name IN ('INDEPENDENT FA','IMO') THEN wst.sales_team_name END) = 2
                AND srd.product_line IN ('INDEX','ASSURED EDGE')
                THEN 'IFA/IMO'
            WHEN COUNT(DISTINCT wst.sales_team_name) = 2
                AND COUNT(DISTINCT CASE WHEN wst.sales_team_name IN ('WIFI','IMO') THEN wst.sales_team_name END) = 2
                THEN 'FI/IMO'
            END AS override_dist_ch
    FROM LIFE_PROD.LIF_MURKYLAKE.SLS_RPT_DETAIL srd
        INNER JOIN LIFE_PROD.LIF_MURKYLAKE.WC_SALES_DISTRICT wsd
            ON wsd.sales_district_id = srd.sales_district_id
        INNER JOIN LIFE_PROD.LIF_MURKYLAKE.WC_SALES_TEAM wst
            ON wst.sales_team_id = wsd.sales_team_id
    WHERE TO_DATE(srd.sales_date) BETWEEN '2024-01-01' and '2025-12-31'
        AND srd.bonus_rate <> 0
        AND srd.init_pay_in = 'Y'
        AND srd.consol_brkr_dlr_id <> '342'
        AND srd.life70_co_cd NOT IN ('VV', 'VB')
        AND srd.agent_tax_id IS NOT NULL
        AND srd.product_line IN (
            'RILA','INDEX','VARIABLE','ASSURED EDGE','FIXED','SPIA/DIA'
        )
    GROUP BY srd.policy_no, srd.product_line
)
--select * from distchannel_override
,
-- Add your favorite comment here. Get firm mga code
distchannel_withmga AS (
    SELECT DISTINCT dc.*
        , srd.mga_agent_cd
    FROM distchannel_override dc
    LEFT JOIN LIFE_PROD.LIF_MURKYLAKE.SLS_RPT_DETAIL srd on srd.policy_no = dc.policy_no
)
--select * from distchannel_withmga
,

/*==========================================================
  2) Adding in distribution channels from MGA mapping
  Where the above dual channels don't apply supplement with
  the MGA map file from [a colleague] (MGA_Map).  masked a person's name.
============================================================*/
supplemental_dist AS (
    SELECT DISTINCT
        dco.policy_no
        , dco.product_line
        , dco.mga_agent_cd
        , CASE WHEN dco.override_dist_ch is not null then dco.override_dist_ch
            WHEN dco.override_dist_ch is null and mm.channel_override is null then mm.channel_calc
            ELSE mm.channel_override
            END as dist_ch
    FROM distchannel_withmga dco
    LEFT JOIN SSDB_INTEGRATION.LR_STRATEGY.MGA_MAP mm on mm.mga_agent_cd = dco.mga_agent_cd
)
--select * from supplemental_dist 
,
master_firm as  (
    select distinct
        m.master_consol_brkr_dealer_id
    , m.consol_brkr_dealer_id
    , m.master_consol_brkr_dealer_name
    , m.consol_brkr_dealer_name
--    , m.distch_cd   
    from LIFE_PROD.LIF_MURKYLAKE.WC_EDW_CONSOL_BRKR_DEALER_MGA_MASTER m
    where m.expiration_dte = '9999-12-31' and consol_brkr_dealer_id <> 0 and consol_brkr_dealer_id is not null
    -- and consol_brkr_dealer_name like '%LPL%'  --testing
),

/*==========================================================
  3) Base filtered dataset (2024–2025)
  Shared filters live here so they are only written once.
==========================================================*/
base_sales AS (
    SELECT
        srd.agent_tax_id, srd.mga_agent_cd
        , srd.policy_no
        , srd.fiscal_yr
        , TO_DATE(srd.sales_date) AS sales_dt
        , srd.actual_sales_amount
        , srd.sales_amount
        , srd.product_line AS raw_product_line
        , sd.dist_ch
        , srd.consol_broker_nm --get name and crd --added
        , srd.consol_brkr_dlr_id --get name and crd  --added
        , m.master_consol_brkr_dealer_name as parent -- get parent  --added
        , '' as firmcrd --get firm_crd  --added
        , LEFT(a.zip_cd, 5) as zip_cd --added--added
        , srd.plcy_state_cd as state_cd  --added
        , srd.whslr_id  --added
        , w.whslr_nm  --added
        , CASE
            WHEN srd.product_line IN ('RILA', 'INDEX', 'VARIABLE', 'ASSURED EDGE') THEN 'RIVA'
            WHEN srd.product_line IN ('FIXED', 'SPIA/DIA') THEN 'FASD'
            ELSE NULL
        END AS product_bucket
    FROM LIFE_PROD.LIF_MURKYLAKE.SLS_RPT_DETAIL srd
    LEFT JOIN master_firm m on m.consol_brkr_dealer_id = srd.consol_brkr_dlr_id --changed to left, I don't want to lose rows
    LEFT JOIN LIFE_PROD.LIF_MURKYLAKE.WC_SBL_CONTACT c on c.contact_ssn = srd.agent_tax_id    
    LEFT JOIN LIFE_PROD.LIF_MURKYLAKE.WC_SBL_ADDR a on c.primary_addr_id = a.address_id
    LEFT JOIN supplemental_dist sd
        ON sd.policy_no = srd.policy_no and sd.mga_agent_cd = srd.mga_agent_cd
    LEFT JOIN LIFE_PROD.LIF_MURKYLAKE.WHSLR W on w.whslr_id = srd.whslr_id
    WHERE
        TO_DATE(srd.sales_date) BETWEEN '2024-01-01' and '2025-12-31'
        AND srd.bonus_rate <> 0
        AND srd.init_pay_in = 'Y'
        AND srd.consol_brkr_dlr_id <> '342'
        AND srd.life70_co_cd NOT IN ('VV', 'VB')
        AND srd.agent_tax_id IS NOT NULL
        AND srd.product_line IN (
            'RILA','INDEX','VARIABLE','ASSURED EDGE','FIXED','SPIA/DIA'
        )
),
/*select sum(actual_sales_amount)/1000000000, sum(sales_amount)/1000000000, fiscal_yr
from base_sales
group by fiscal_yr*/

/*==========================================================
  4) Keep only policies that don't equal 0 across the base so as not to
  skew these results to the positive side.
  Replaces repeated EXISTS() checks.
==========================================================*/
nonetzero_policies AS (
    SELECT policy_no
    FROM base_sales
    GROUP BY policy_no
    HAVING SUM(sales_amount) <> 0
),
 
base_sales_final AS (
    SELECT b.*
    FROM base_sales b
    INNER JOIN nonetzero_policies n
        ON n.policy_no = b.policy_no
)
--select * from base_sales_final
,
--shows actual sales at 21.9 and comp'd sales at 23.2 for 2025
/*select sum(actual_sales_amount)/1000000000, sum(sales_amount)/1000000000, fiscal_yr
from base_sales_final
group by fiscal_yr*/

/*==========================================================
  6) Agent dollars by policy/channel for product buckets
==========================================================*/
agent_policy_sales_bucket AS (
    SELECT
        agent_tax_id, b.mga_agent_cd
        , policy_no
        , fiscal_yr
        , SUM(actual_sales_amount) as actual_agent_dollars
        , SUM(sales_amount) as compd_agent_dollars
        , raw_product_line
        , dist_ch
        , consol_broker_nm --get name and crd --added
        , consol_brkr_dlr_id --get name and crd  --added
        , parent -- get parent  --added
        , firmcrd --get firm_crd  --added
        , CASE WHEN zip_cd is NULL then 'BLANK' else zip_cd end as zip_cd
        , CASE WHEN state_cd is NULL then 'BLANK' else state_cd end as state_cd
        , whslr_id  --added
        , whslr_nm  --added
        , product_bucket
    FROM base_sales_final b
    WHERE product_bucket IS NOT NULL
    GROUP BY 
        agent_tax_id, b.mga_agent_cd
        , policy_no
        , fiscal_yr
        , raw_product_line
        , dist_ch
        , consol_broker_nm --get name and crd --added
        , consol_brkr_dlr_id --get name and crd  --added
        , parent -- get parent  --added
        , firmcrd --get firm_crd  --added
        , CASE WHEN zip_cd is NULL then 'BLANK' else zip_cd end
        , CASE WHEN state_cd is NULL then 'BLANK' else state_cd end
        , whslr_id  --added
        , whslr_nm  --added
        , product_bucket
)
--select * from agent_policy_sales_bucket
,

/*==========================================================
  7) Agent dollars by policy/channel across all products
==========================================================*/
agent_policy_sales_all AS (
    SELECT
        agent_tax_id, b.mga_agent_cd
        , policy_no
        , fiscal_yr
        , SUM(actual_sales_amount) as actual_agent_dollars
        , SUM(sales_amount) as compd_agent_dollars
        , raw_product_line
        , dist_ch
        , consol_broker_nm --get name and crd --added
        , consol_brkr_dlr_id --get name and crd  --added
        , parent -- get parent  --added
        , firmcrd --get firm_crd  --added
        , CASE WHEN zip_cd is NULL then 'BLANK' else zip_cd end as zip_cd
        , CASE WHEN state_cd is NULL then 'BLANK' else state_cd end as state_cd
        , whslr_id  --added
        , whslr_nm  --added
        , 'ALL' as product_bucket
    FROM base_sales_final b
    GROUP BY
        agent_tax_id, b.mga_agent_cd
        , policy_no
        , fiscal_yr
        , raw_product_line
        , dist_ch
        , consol_broker_nm --get name and crd --added
        , consol_brkr_dlr_id --get name and crd  --added
        , parent -- get parent  --added
        , firmcrd --get firm_crd  --added
        , CASE WHEN zip_cd is NULL then 'BLANK' else zip_cd end
        , CASE WHEN state_cd is NULL then 'BLANK' else state_cd end
        , whslr_id  --added
        , whslr_nm  --added
)
--  select * from agent_policy_sales_all
,
 
agent_policy_sales AS (
    SELECT * FROM agent_policy_sales_bucket
    UNION ALL
    SELECT * FROM agent_policy_sales_all
)
--2025: actual 21.93 compd 23.21
--2024: actual 22.31 compd 23.47
/*select *
from agent_policy_sales
where policy_no = 'A51G5521690' and product_bucket = 'ALL'*/
/*select policy_no, count(*), sum(actual_agent_dollars) as actual_Sales, sum(compd_agent_dollars) as compd_sales
from agent_policy_sales
where product_bucket = 'ALL'
group by policy_no*/
/*select sum(actual_agent_dollars)/1000000000, sum(compd_agent_dollars)/1000000000, fiscal_yr
from agent_policy_sales
where product_bucket = 'ALL'
group by fiscal_yr*/
,

/*==========================================================
  11) Policy/channel/year ticket dollar denominator.
  Want to include everything not equal to 0 so as not to
  skew results.
==========================================================*/
ok_policies AS (
    SELECT
        fiscal_yr
        , policy_no  -- EDIT (session, 2026-10-31): no MGA here: the ticket denominator is the policy's total, and agent_ticket
        --joins this on policy, year and channel only; per MGA it repeated agent rows and counted a split policy twice.
        , dist_ch
        , SUM(sales_amount) AS total_ticket_dollars
        , SUM(actual_sales_amount) AS total_ticket_dollars_act    -- this doesn't matter. primarily picks up ones with 0s that crossed year windows
    FROM base_sales_final b
    GROUP BY
        fiscal_yr
        , policy_no  -- EDIT (session, 2026-10-31): MGA removed, as above.
        , dist_ch
    HAVING SUM(sales_amount) <> 0
)
--select * from ok_policies
,

/*==========================================================
  12) True ticket allocation
  Split ticket counts proportionally by compd agent dollars.
==========================================================*/
agent_ticket AS (
    SELECT
        a.agent_tax_id, a.mga_agent_cd
        , a.dist_ch
        , a.policy_no
        , CASE WHEN a.zip_cd is NULL then 'BLANK' else a.zip_cd end as zip_cd
        , CASE WHEN a.state_cd is NULL then 'BLANK' else a.state_cd end as state_cd
        , a.fiscal_yr
        , a.consol_brkr_dlr_id
        , a.consol_broker_nm
        , a.product_bucket
        , a.raw_product_line
        , a.whslr_id
        , a.compd_agent_dollars / NULLIF(o.total_ticket_dollars, 0.0) AS ticket_portion  --- [masked name], I think this breaks, will cause double attribution
        , a.actual_agent_dollars / NULLIF(o.total_ticket_dollars_act, 0.0) AS ticket_portion_act  --- [masked name], I think this breaks, will cause double attribution
    FROM agent_policy_sales a
    INNER JOIN ok_policies o
        ON  a.policy_no = o.policy_no
        AND a.fiscal_yr = o.fiscal_yr
        AND a.dist_ch = o.dist_ch
)
/*select *
from agent_ticket
where policy_no = 'A51G5521690' and product_bucket = 'ALL'*/
,
final_output as (
select
    aps.agent_tax_id, aps.mga_agent_cd
    , aps.policy_no
    , aps.fiscal_yr
    , SUM(aps.actual_agent_dollars) as actual_agent_dollars
    , SUM(aps.compd_agent_dollars) as compd_agent_dollars
    , aps.raw_product_line
    , case when aps.raw_product_line in ('FIXED', 'SPIA/DIA', 'ASSURED EDGE') then 'FIXED'
        else aps.raw_product_line
        end as product_line2
    , case when aps.dist_ch = 'WIREHOUSE' then 'WH'
        when aps.dist_ch = 'INDEPENDENT' then 'IFA'
        when aps.dist_ch = 'BANK' then 'FI'
        else aps.dist_ch
    end as dist_ch 
    , aps.consol_broker_nm --get name and crd --added
    , aps.consol_brkr_dlr_id --get name and crd  --added
    , aps.parent -- get parent  --added
    , aps.firmcrd --get firm_crd  --added
    , aps.zip_cd --added--added
    , aps.state_cd  --added
    , aps.whslr_id  --added
    , aps.whslr_nm  --added
    , aps.product_bucket
    , sum(ticket_portion) as true_ticket_count
    , sum(ticket_portion_act) as true_ticket_count_act
from agent_policy_sales aps
left join agent_ticket at
    ON at.policy_no = aps.policy_no
    AND at.agent_tax_id = aps.agent_tax_Id
    AND at.fiscal_yr = aps.fiscal_yr
    AND at.dist_ch = aps.dist_ch
    AND at.product_bucket = aps.product_bucket
    AND at.raw_product_line = aps.raw_product_line
    AND at.zip_cd = aps.zip_cd
    AND at.whslr_id = aps.whslr_id
    AND at.state_cd = aps.state_cd
    AND at.consol_brkr_dlr_id = aps.consol_brkr_dlr_id
    AND at.consol_broker_nm = aps.consol_broker_nm
    AND EQUAL_NULL(at.mga_agent_cd, aps.mga_agent_cd)  -- EDIT (session, 2026-10-31): match on MGA too, or a policy x agent with 2+ codes
    --picks up every code's ticket row and its dollars sum once per code; EQUAL_NULL keeps blank codes matched.
group by
    aps.agent_tax_id, aps.mga_agent_cd
    , aps.policy_no
    , aps.fiscal_yr
    , aps.raw_product_line
    , case when aps.dist_ch = 'WIREHOUSE' then 'WH'
        when aps.dist_ch = 'INDEPENDENT' then 'IFA'
        when aps.dist_ch = 'BANK' then 'FI'
        else aps.dist_ch
    end
    , aps.consol_broker_nm --get name and crd --added
    , aps.consol_brkr_dlr_id --get name and crd  --added
    , aps.parent -- get parent  --added
    , aps.firmcrd --get firm_crd  --added
    , aps.zip_cd --added--added
    , aps.state_cd  --added
    , aps.whslr_id  --added
    , aps.whslr_nm  --added
    , aps.product_bucket
--select * from agent_ticket
),

final_output_wo_policy as (
select fiscal_yr, f.mga_agent_cd
    , sum(actual_agent_dollars) as actual_agent_dollars
    , sum(compd_agent_dollars) as compd_agent_dollars
 --   , raw_product_line
    , product_line2
    , dist_ch
    , consol_broker_nm
    , consol_brkr_dlr_id
    , parent
    , firmcrd
    , zip_cd
    , state_cd
    , whslr_id
    , whslr_nm
    , product_bucket
    , sum(true_ticket_count) as true_ticket_count
    , sum(true_ticket_count_act) as true_ticket_count_act
    , count(distinct agent_tax_id) as Distinct_Agents
from final_output f
group by fiscal_yr, f.mga_agent_cd
--    , raw_product_line
    , product_line2
    , dist_ch
    , consol_broker_nm
    , consol_brkr_dlr_id
    , parent
    , firmcrd
    , zip_cd
    , state_cd
    , whslr_id
    , whslr_nm
    , product_bucket
),

IMOwhslrs as (
select distinct w.whslr_id
    , w.whslr_nm
    , wsd.sales_district_name
from LIFE_PROD.LIF_MURKYLAKE.whslr w
inner join LIFE_PROD.LIF_MURKYLAKE.wc_sales_district wsd on wsd.sales_district_id = w.sales_district_id
where wsd.sales_district_name like '%IMO%'
),

finaloutputwithimoadjustment as (
select fo.fiscal_yr, fo.mga_agent_cd
    , fo.actual_agent_dollars
    , fo.compd_agent_dollars
    , fo.product_line2
    , case when (iw.sales_district_name like 'IMO%' and fo.dist_ch = 'IFA') then 'IMO'
    when fo.consol_brkr_dlr_id = '685' then 'PRI'
    else fo.dist_ch
    end as dist_ch
    , fo.consol_broker_nm
    , fo.consol_brkr_dlr_id
    , fo.parent
    , fo.firmcrd
    , fo.zip_cd
    , fo.state_cd
    , fo.whslr_id
    , fo.whslr_nm
    , fo.product_bucket
    , fo.true_ticket_count
    , fo.true_ticket_count_act
    , fo.distinct_agents
from final_output_wo_policy fo
left join IMOwhslrs iw on iw.whslr_id = fo.whslr_id
)
select *
from finaloutputwithimoadjustment
where product_bucket = 'ALL'
)
