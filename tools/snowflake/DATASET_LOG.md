# Opportunity and sales by channel and territory: conventions, decisions, questions, history

One file for what we track. Sections: **Conventions**, **Settled** (decisions in force), **Parked** (suspended, not
reversed), **Open questions** (index), **Log** (dated findings, append-only). The model is `DATA_MODEL.md`.

- Log entries are never rewritten. A wrong finding is corrected by a later entry that names it.
- An owner answer goes under its question in the log (quoted, dated), its rule into Settled, and the question leaves
  the index.
- Question numbers continue those of the archived log; a retired number is not reused.
- Everything before 2026-10-30 is in the tag `archive/snowflake-2026-10` (`tools/snowflake/DATASET_LOG.md` there).

**Purpose** (owner, 2026-10-21): "Firm 1 and firm 2 are large annuity carriers merging into a single company. I've
been tasked ... to design the combined territory." The analysis (owner, 2026-10-29): "we want to see opportunity under
the current state with the current channel definitions, as well as how that opportunity moves after we define the new
channels."

## Conventions

- **Database.** Every reference uses the full `database.schema.table` path; CTEs are exempt.
- **Table variables.** A table whose name carries a carrier is a session variable, set once at the top of the file
  (`SET s2_opp = 'db.schema.<...>'`) and read as `IDENTIFIER($s2_opp)`; the owner types the names there, never a
  find and replace (owner, 2026-10-30: "from now on, instead of using find and replace, set it up so I can just define
  snowflake SQL variables"). The real `SET` lines are in `$TD_REPO/owner_sql/vars.sql`.
- **Files.** One Run All file per layer, numbered from `01`; intermediates are temporary tables, only the layer's
  final table is kept. One-off digging: `explore/<topic>.sql`.
- **One result.** A file ends on one query that returns everything the owner reads, so a Run All gives one result
  set and one CSV, saved into `$TD_REPO/data/safe/` (owner, 2026-10-30: "only one single query to run at the end to
  see all relevent output, as opposed to having to manually run multiple queries step by step and check one at a
  time"). Each part (report, review list, checks) is its own temporary table with the same columns, and the last
  statement unions them; checks are rows of that result. Pattern: `explore/profile.sql`, statements 3-8 (`PART`,
  `DS`, `COL`, `COL2`, `ITEM`, counts, `AMT`, percentages).
- **Columns.** Source columns keep their names. Ratios `SHARE_` (0-1) or `PCT_` (0-100), naming what is divided by
  what; rankings `RANK_<within>_<by>`; checks `CHECK_NAME`, `VALUE`, `MUST_BE_ZERO`.
- **Rules.** Assign where unique and flag the rest; no largest-share guesses.
- **Snowflake.** How a function or clause behaves is settled by the Snowflake docs (page and date read) or by the
  owner, never assumed; a construct the owner has run at work counts as confirmed (owner, 2026-10-25).
- **Testing.** Every query runs first in DuckDB on the extract in `data/safe/extract_<date>/`. DuckDB accepts what
  Snowflake rejects: it renames a repeated column name where Snowflake errors, so every CTE is described for repeats;
  `IN` / `EXISTS` subqueries go only in `WHERE`; no named `WINDOW` clause.
- **Words.** "Source firm" (firm_1, firm_2) for the insurers, "distributor" for the broker-dealer; the rest of the
  vocabulary is in `DATA_MODEL.md`. A channel is a sales channel, never a "desk".
- **Owner's queries.** Kept verbatim in `$TD_REPO/owner_sql/` (git-excluded). A cite into one names the file's
  sha256 prefix in its log entry; a changed file gets a new entry that re-cites, and old cites stay with their hash.
- **Masking** (for `tools/snowflake/` only; the repo's `AGENTS.md` rule holds everywhere else). Never a person's name,
  and never sales $ tied to a firm name. Distributor firm names may stand in SQL and rule lists; a carrier's name only
  through the table variables. This file gives amounts as percentages and counts (owner, 2026-10-30: "the real concern
  is people or individual's names. or sales dollars associated with firm names"; "carrier-based names should be handled
  with the "set" convention we defined earlier"; "exceptions are scoped only to tools/snowflake").

## Settled

- The analysis is rebuilt from scratch on `DATA_MODEL.md` (owner, 2026-10-29: "we're starting from scratch").
- Territories stay fixed; a sale stays with the wholesaler credited; opportunity is tied to ZIP and channel (owner,
  2026-10-29). `DATA_MODEL.md` I1, I2.
- The two source firms are analysed separately, each with its own datasets, mapped to the common market metrics
  schema (owner, 2026-10-29 and 2026-10-30). Each source's market is its own opportunity estimate.
- The distributor key is the market metrics schema's: CRD x broker name (session, on the owner's 2026-10-30
  description; both full in both sources' opportunity, profile 2026-10-30).
- Fiscal year 2025 only (owner, 2026-10-25).
- Fixed annuity is in scope, both sources (owner, 2026-10-26).
- Sales = the actual sales amount, not the compensated amount (archived log, Settled).
- No reassignment: each wholesaler's numbers in the current state and in the new state (owner, 2026-10-21, Q3).
- Listed distributors break out to new labels that merge into National; WH and FI no longer hold the opportunity or
  sales placed with them (owner, 2026-10-21).
- Firm overrides: a listed distributor takes a new label on every row, both sources, sales and opportunity. When the
  override changes the current channel (source 1: the override's channel; source 2: its own channel, stated in the
  list), the opportunity goes to the holder of ZIP x that channel, the lowest ID where 2+ hold it; sellers stay
  (owner, 2026-10-26 and 2026-10-28). `DATA_MODEL.md` τ_s and k_s for listed distributors.
- Source 2's file channel maps one-to-one onto four of source 2's channels; its fifth value is no channel and those
  rows drop (owner, 2026-10-25, Q19). Its product line x VA type maps onto products (owner, 2026-10-24, Q22). The coded
  version is in the tag; the real labels and their pairs: Q19 (reopened 2026-10-30); products: `DATA_MODEL.md`, p.
- One set of new channels for both sources, in firm 1's channels: both sources' opportunity is routed by firm 1's
  channel per market metrics firm; source 2's own channels serve its current state only (owner, 2026-10-30: "we want
  each new channel to match across both source firms. so it seems natural to use firm 1's original channel in the
  master firm mapping table"; "we can simply just use firm 1's original channels, without even explicitly mapping
  source firm 2 to source firm 1"). Q6.
- Extracts may carry real values; the owner includes only relevant non-sensitive columns (owner, 2026-10-30: "do not
  worry about masking I will only include relevent non-sensitive columns"). What may enter the repo: Conventions,
  Masking.

- Opportunity or sales with no firm 1 channel takes the channel UNMAPPED: kept, with its $, and flagged as a manual
  mapping exercise for the project team (owner, 2026-10-30: "give it a new channel on it's own so that we can keep the
  opportunity and sales data but easily flag it as a manual mapping exercise to be done by the project team"). The
  label is the session's.

## Parked

Suspended while the sources are analysed separately (owner, 2026-10-30: "yes to park"); each returns with a combined
view.

- Market = the larger of the two estimates per ZIP x distributor x product (owner, 2026-10-24).
- Head-to-head, sold and offered (owner, 2026-10-21, Q11, Q15).
- Opportunity overrides: source 1's opportunity replaced by source 2's for listed distributors (owner, 2026-10-26).
- The cross-source firm key (owner, 2026-10-26).
- Name matching by geography (owner, 2026-10-21).
- Q4, Q8, Q10, Q12, Q14, Q18, Q30 (texts in the tag; Q30 in the 2026-10-29 entry there).

## Open questions

| Q | question | since |
|---|---|---|
| Q2 | What does the opportunity measure: the whole market, or what a source can address? | 2026-10-20 |
| Q7 | Same ZIP basis for opportunity and sales? Source 1's sales ZIP is the advisor's primary address (`s1_opp_sales.sql:100`). | 2026-10-20 |
| Q17 | Sellers with no territory: whose numbers? | 2026-10-21 |
| Q19 | Source 2's file labels to its territory channels: BANK → BK, INDEPENDENT → FP, REGIONAL → BD, REGIONAL AGENCY → RA (the archived coded map, O2_01-04 → D2_01-04, with the real labels; the pairs are the session's reading)? NO CHANNEL: still dropped (2026-10-25), or routed by firm 1's channel like the rest? | 2026-10-25 |
| Q21 | Opportunity and sales with no distributor (⊥_D): which new channel? Moot for opportunity (CRD on every row); for sales UNMAPPED is the session's reading. | 2026-10-24 |
| Q23 | Does source 2's file match the market metrics data on the cells both have? (now a conformance check) | 2026-10-24 |
| Q27 | Can product split a firm's channel? (The split list: the profile, 2026-10-30; I3 for every firm: the owner's route, Q6.) | 2026-10-29 |
| Q28 | λ_s vs κ_s: in the current state, is a sale placed by its recorded label (which can depend on the seller) or by its cell's channel? | 2026-10-29 |
| Q29 | τ_s for new channels such as National: covered by ZIP, by distributor-tied territories (`s1_opp_sales.sql:692` filters them out), or the current holder kept (`s1_opp_sales.sql:719`)? Listed distributors: settled 2026-10-28. Folds in Q13. | 2026-10-29 |
| Q31 | A wholesaler's market share: territory share (sales placed in held cells ÷ their market) or credited sales ÷ held market? | 2026-10-29 |
| Q32 | Does a source's market include products it does not sell? (Settled before as "the products where it has positive sales"; reopened 2026-10-30.) | 2026-10-30 |
| Q33 | Source 1's split-policy labels `IFA/IMO` and `FI/IMO` (`owner_sql/s1_sales.sql:18`, `:21`): which channel's territories hold them, and does the IMO rule apply to them? | 2026-10-30 |
| Q34 | The unified facts: opportunity and sales stacked in one long table and put side by side only by aggregation, never joined row to row; each step of `owner_sql/s1_opp_sales.sql` goes to the layer the 2026-10-30 entry gives it. Confirm? | 2026-10-30 |
| Q35 | `CRD_TO_CBD` beside `MM_MAP`: what is it, and which one takes source 1's company IDs to CRD? | 2026-10-30 |
| Q36 | Source 2: which period is the opportunity table (it has no year column), and what is `MM_AMOUNT` on the sales rows? | 2026-10-30 |
| Q37 | How is `MGA_MAP.CHANNEL_CALC` set: the channel with the most $ per MGA code, or a rule? | 2026-10-30 |
| Q38 | The route's level and the override: firm 1's channel per CRD x broker name, or per ZIP x CRD x broker name (they differ where firm 1's channel is blank in some ZIPs)? Where `crd_dist_override` differs from the route, which wins? | 2026-10-30 |
| Q39 | For each firm 1 channel, which source 2 territory channel holds source 2's opportunity routed to it in the new state? | 2026-10-30 |

## Log

### 2026-10-30: fresh start; each source on the market metrics schema; what the owner's query transforms

**Fresh start.** The union-based work (SQL `00`-`30`, the log to 2026-10-29, three handoffs) is frozen in the tag
`archive/snowflake-2026-10` (`5d490d6`); this branch, `m5-studio/snowflake-v2`, starts from `main` with
`DATA_MODEL.md` and the 2026-10-29 research note. The old extract and synthetic files moved to
`data/safe/_archive_2026-10/`. Owner, 2026-10-30: "yes go I approve all of your recommendations"; on the triage:
"retire q9, and keep the source's product set question open. yes close q24 and q25. yes to all folds and yes to park."

- Retired with the union design (texts in the tag): Q1 and Q15 as rules (the cross-source company key and the cell
  unit; `DATA_MODEL.md` replaces both), Q9 ("retire q9"; under the fixed territories opportunity follows ZIP and
  channel to the holder), Q26 (the union's address columns), `union_base` and its mechanics, the coded labels.
- Q24 closed. Owner, 2026-10-30: source 2's sales "have firm_crd BUT have a firm name that is different from the
  expected market metrics broker_name".
- Q25 closed. Owner, 2026-10-30: source 2's opportunity "is already in the expected market metrics format with
  firm_crd, broker_name, product_line, and va_product type".
- Folded: Q13 into Q29, Q16 and Q20 into Q27.

> **Owner, 2026-10-29:** "for now lets treat both source firms as completely separate with their own datasets"

> **Owner, 2026-10-29:** "recall that we are mapping both source firms's opportunity and sales data to a common market metrics schema"

> **Owner, 2026-10-30:** "For source 1: distributors are keyed by cbd_id and firm name (not necessarily unique keys) in both opportunity and sales files. We have a table called mm_map which attempts to map cbd_id to firm_crd (which is how we link to the common market metrics schema). For source 2: it's opportunity data is already in the expected market metrics format with firm_crd, broker_name, product_line, and va_product type. it's sales however have firm_crd BUT have a firm name that is different from the expected market metrics broker_name. and we have a mapping table called [source 2's CRD map] which is an attempt at pulling the market metrics broker_name by crd so that the sales firm data can match the opportunity firm data."

The session's reading (`DATA_MODEL.md`, the distributor key): `mm_map` is needed only for source 1's sales, since
source 1's raw vendor rows carry CRD and broker name; source 2's CRD map keyed on CRD alone adds nothing where a CRD
has one broker name and cannot choose where it has 2+. The first-pass master (2026-10-29 entry in the tag) has 4 CRDs
with 2+ broker names (10 names), so the key is CRD plus broker name on those CRDs a rule splits.

> **Owner, 2026-10-30:** "there are differing levels of transformations applied for each dataset unfortunately ... The rough idea was to first get a unified vendor/market metrics level dataset that can be joined to all other tables like territores, opportunity, sales (within each source). And then pass that market metrics based dataset through those transformations that are applied so both sources get the same transformations at the same time."

What the owner's query (`mm_query.sql`, hub root) does, sorted by what each step acts on:

| kind | steps | lines |
|---|---|---|
| source-internal (fields only source 1 has) | sales filters; ZIP from the advisor's address, state from the policy; channel by policy split and by agency code (`mga_map`); long labels shortened; IFA → IMO by the seller's sales district | `:11-21`, `:56-66`, `:100-101`, `:116-147`, `:320-324`, `:420` |
| conformance (different code, one target) | product on sales and on opportunity (two different maps); ZIP padding; fiscal year; broker name → company ID on a split CRD; company 0 → client firm ID list; lists resolved | `:317`, `:455-459`, `:477-499`, `:510-614` |
| distributor rules | current overrides by company ID and broker name; one company forced to PRI on sales; the new-label list | `:421`, `:461-472`, `:701-706` |
| coverage | channel-level regions only; holder looked up on the current label | `:676-692`, `:718` |
| display | parent and firm names; change no number | `:721` on |
| glue (dropped by the model) | sales joined to opportunity on seven columns; opp-only rows | `:616-674` |

So the owner's design is `DATA_MODEL.md`'s pipeline: conformance per source, unified facts, rules as tables applied
by join. Three things to settle as the extracts arrive: whether the vendor feed's channel and `territory` fields are
source 1's own (the query matches `territory` to source 1's wholesaler ID, `:549`); a company-ID list resolved by
reading source 1's sales (`:583-584`), which is conformance depending on sales; and Q7 with the two product maps.

Next: the owner pulls the tables' columns from `INFORMATION_SCHEMA`, then the extracts (the start note,
`notes/2026-10-30_snowflake-v2-start.md`).

### 2026-10-30: the owner's source 1 sales query, before the market metrics transformations

> **Owner, 2026-10-30:** "I have two new queries that supersede mm_query.sql. The first is a sales query for firm 1 that is intended to run before the transformations are applied to the market metrics - based firm data. so both source firms join their opportunity and sales data to territories table through the unified market metrics based firm mapping."

Saved verbatim as `$TD_REPO/owner_sql/s1_sales.sql` (git-excluded, 440 lines, sha256 `92fabcc00478…`). The cites
below are to that version. Findings from the session's reading; nothing run yet.

| # | finding | lines | becomes |
|---|---|---|---|
| 1 | Sales rows can duplicate. `supplemental_dist` keeps one row per policy, product line, MGA code and channel (`:59` `, dco.product_line`), but `base_sales` joins it on policy and MGA code only (`:114` `ON sd.policy_no = srd.policy_no and sd.mga_agent_cd = srd.mga_agent_cd`). Other joins that duplicate if their key repeats: `MGA_MAP` per MGA code (`:66`), `master_firm` per company ID (`:110`), the contact per agent tax ID (`:111`), `WHSLR` per wholesaler ID (`:115`, `:405`-`:409`). | `:59`, `:66`, `:110`-`:115`, `:405`-`:409` | check: filtered raw `SLS_RPT_DETAIL` total = `base_sales` total, per fiscal year; and each join key unique |
| 2 | Two current labels for split policies: `IFA/IMO` (`:18` `THEN 'IFA/IMO'`) and `FI/IMO` (`:21` `THEN 'FI/IMO'`). The IMO rule tests only `IFA` (`:418` `case when (iw.sales_district_name like 'IMO%' and fo.dist_ch = 'IFA') then 'IMO'`), so it leaves them as they are; a territory lookup on the label finds no holder unless the territories carry them. | `:18`, `:21`, `:418` | Q33 |
| 3 | The window is two years (`:28`, `:117` `TO_DATE(srd.sales_date) BETWEEN '2024-01-01' and '2025-12-31'`); fiscal year 2025 is kept downstream on `fiscal_yr` (Settled). | `:28`, `:117` | none |
| 4 | CRD is blank (`:99` `, '' as firmcrd --get firm_crd  --added`); the company ID is the key (`:97`), so source 1's sales reach CRD through `mm_map`, as `DATA_MODEL.md` has it. | `:97`, `:99` | E4 |

### 2026-10-30: the owner's source 1 opportunity and sales query; which steps are the shared transformations

> **Owner, 2026-10-30:** "this query is how we currently produce firm 1's opporunity and sales data that feeds the union table. The key item here is to identify which parts of the logic transform opportunity / firm / channel and other relevent items. as these will be the transformations we want to apply to both source firms's market metrics based firm / opportunity data."

Saved verbatim as `$TD_REPO/owner_sql/s1_opp_sales.sql` (git-excluded, 786 lines, sha256 `6262e2f93bbd…`); cites
below are to that version, and `DATA_MODEL.md` and the open index now cite it instead of `mm_query.sql`. It is
`mm_query.sql` plus two broker-name → company-ID rows (`:477`-`:479`, dated 10/29 in the file); the rest differs only
in whitespace. Its lines 1-435 equal `s1_sales.sql` (`92fabcc00478…`) except the commented table name on line 3.
Reading only; nothing run.

**Each step, by kind.** Layer 1 is conformance per source, layer 3 the rule tables both sources pass through
(`DATA_MODEL.md`, Pipeline). Names and IDs are counted, not quoted.

| step | lines | acts on | kind | in the rebuild |
|---|---|---|---|---|
| sales filters, net-zero policies, split-policy labels, MGA channel, long labels shortened, sales product map, ZIP from the advisor's address, IMO by the seller's district | `:11`-`:435` | source 1 sales | conformance, source 1 | `s1_sales.sql` as is, then `mm_map` to CRD; its label is λ₁ |
| one company's sales forced to PRI | `:419` | sales channel | κ rule; the same company is in the opportunity rule `:459` | one κ table row, applied to sales and opportunity alike |
| product: market metrics product line × VA type (`:453` `SELECT CASE WHEN va_product_type = 'IOVA' then 'IOVA'`) | `:453`-`:458` | opportunity product | shared: both sources' opportunity is in this format | product map table |
| current channel: feed channel overridden by company ID (3 IDs), by broker name (7 names), one feed label renamed; first match wins | `:459`-`:470` | opportunity channel | shared κ rules | κ table on CRD and broker name, with a priority; the company IDs re-keyed to CRD |
| distributor key: broker name → company ID (4 rows), company 0 → its client firm ID list, company 0 without one → NULL | `:475`-`:483` | opportunity firm | conformance: market metrics → source 1's company ID | dropped: opportunity keeps the market metrics CRD and broker name (if `wc_market_metrics_opportunity` carries CRD; `explore/schema.sql` shows) |
| opportunity with no company ID dropped (`:500` `WHERE original_cbd_id IS NOT NULL`) | `:500` | opportunity $ | a loss, not reported | kept as ⊥_D, its $ reported |
| a company-ID list resolved by matching source 1's sales on seven columns, else the first ID | `:511`-`:594` | opportunity firm | conformance that reads sales | dropped with the row above |
| fiscal year as text; opportunity ZIP padded to 5 (`:599`); sales ZIP `LEFT(a.zip_cd, 5)`, not padded (`:100`) | `:471`-`:472`, `:599`, `:100` | keys | conformance | 5-character ZIP text in every dataset |
| sales joined to opportunity on fiscal year, ZIP, company, product, channel, state and seller = the feed's `territory` (`:634`-`:640`); opportunity-only rows appended (`:644`-`:675`) | `:439`-`:449`, `:617`-`:675` | both | glue | dropped: stacked, not joined (proposal below) |
| territories: channel-level regions plus one company's regions, two labels renamed, ZIP `left(gr.start_zip,5)` | `:677`-`:694` | holders | conformance, per source's territory table | territories table (source, channel, ZIP, holder) |
| new channel by company-ID list (6 IDs, 4 labels), else the current label (`:707` `else iwn.dist_ch`) | `:703`-`:707` | channel | shared ν_D; ρ is the same label | ν_D table on CRD |
| holder looked up on the current label and ZIP | `:719` | holders | shared mechanism; τ = κ | territories joined on τ_s, the lowest ID where 2+ hold (Settled) |
| parent and firm names from the master, then fixed names for 14 company IDs | `:722`-`:784` | display | shared; changes no number | display table |

**Sales, against `s1_sales.sql`.** Identical through `:435`; both keep only the `ALL` rows (`:641`). After that this
query:

1. Gives each sales row the opportunity of its seven-column key (`:633`-`:640`). `opp_final` is unique on those
   columns, so sales rows do not repeat there, but sales rows also differ by broker name, parent and wholesaler name,
   so two sales rows on one key both carry the full opportunity. Check: `ALL` sales rows per seven-column key.
2. Repeats sales and opportunity rows where 2+ wholesalers hold a channel × ZIP (`:719`) or the master has 2+ rows for
   a company (`:740`). Check: sales total here = `s1_sales.sql`'s, per fiscal year.
3. Replaces the sale's broker name with the master's (`:727`), keeps the wholesaler's name but not its ID (`:626`),
   drops the ticket counts.
4. Puts opportunity and a sale of the same cell on one row only if the sale's label is the opportunity's channel, its
   seller is the feed's `territory` and its state (the policy's, `:101`) is the opportunity's. The IMO rule, the
   split-policy labels and the MGA channel on sales, a seller other than the feed's wholesaler, or a policy state
   that differs each put them on separate rows. Sales have no `IOVA` product (`:315`), so IOVA opportunity never
   shares a row with a sale.

**Proposal (session; Q34): stack, do not join.** Layer 1, per source: opportunity (source, fiscal year, ZIP, CRD,
broker name on a split CRD, market metrics product line and VA type, feed channel, $); sales (the same key, λ_s,
credited seller, $); territories (source, channel, ZIP, holder). Layer 2: one long table, both measures of both
sources, with `SOURCE` and `MEASURE` columns; nothing is matched row to row. Layer 3: the rule tables joined on the
key (product map, κ, ν_D, τ, territories, display), so source 2 passes through the same rows. A view puts opportunity
and sales side by side by grouping on its grain with `SUM(CASE WHEN MEASURE = 'OPP' ...)`: labels that differ cost no
rows, totals hold by construction (I4), and Q28 becomes which label column a view groups on, not a join condition.
The feed's `territory` and the state leave the key: holders come from the territories table, and ZIP gives the state.

### 2026-10-30: the tables' columns; the profile replaces the tier-1 extracts

The owner's run of `explore/schema.sql` statement 3: `$TD_REPO/data/safe/scratch_2026-10-30-0221.csv` (18 tables).
Tables whose names carry a carrier are named here by role and name suffix.

1. Source 1's market metrics opportunity (`WC_MARKET_METRICS_OPPORTUNITY`) carries `FIRM_CRD` (text) beside `CBD_ID`,
   `CLIENT_FIRM_ID`, `BROKER_NAME`, `FDS_BROKER_ID` and `SI_FIRM_ID`. If `FIRM_CRD` is full, the company-ID steps of
   `s1_opp_sales.sql:475`-`:594` are not needed (Q34). It also has `CHANNEL` beside `DIST_CH`, `TERRITORY` and
   `WHOLESALER_NAME`, quarter and month columns, and a column of source 1's own sales as the vendor counts them.
2. `MM_MAP` has the first-pass master's columns (`DIST_CH`, `CBD_ID`, `CHANNEL`, `FIRM_CLIENT_ID`, `BROKER_NAME`,
   `FIRM_CRD`): it is the table profiled on 2026-10-29 (archived log). `CRD_TO_CBD` is a second CRD - company ID map
   (`FIRM_CRD`, `CBD_ID` as floats, two name columns). Q35.
3. Source 2: opportunity (`…_OPP_ORIGINAL`) has no year and no state column; its ZIP and CRD are numbers (a ZIP loses
   its leading zero) and `CHANNEL` is a float code beside `DIST_CH`. Sales (`…_SALES`): CRD a float, `YEAR`, ZIP as
   text, `PRODUCT`, `CHANNEL`, `RVP`, `DVP`, `REGIONIDS`, and `MM_AMOUNT` beside `SALES_AMOUNT`. The CRD map
   (`…_FIRM_CRD`) is CRD → one name: it cannot choose on a split CRD, as the first 2026-10-30 entry expected.
   Territories (`…_TERRITORIES`): `TERRITORY_ID`, `RVP`, `ZIPCODE`, `STATE`, `CHANNEL`, `CHANNEL_NAME`. Q36.
4. Source 1's territories exist as a ZIP-level table (`…_TERRITORIES`: `WHSLR_ID`, `WHSLR_NM`, `ZIP`, `STATE_CD`,
   `NEW_DIST_CHANNEL`), the columns of `current_territories` (`s1_opp_sales.sql:677`-`:694`). `GEOGRAPHIC_REGION`
   has `END_ZIP` beside `START_ZIP`; the query reads only `START_ZIP` (`:684` `, left(gr.start_zip,5) as zip`), so a
   region spanning a range of ZIPs would lose all but its first.
5. Key types differ by table: CRD is text, number or float; the company ID number, text or float. Every ID is cast to
   whole-number text (`DECIMAL(38, 0)`, then `VARCHAR`) before a join.
6. Source 1's sales rows carry `DUPLICATE_ENTRY_IN`, `SRC_DELETE_IND`, `REVERSAL_CD`, `CREDIT_TYPE` and `TRANS_TYPE`,
   which neither query filters, and `RGN_CD`, the region a sale is credited under.
7. `MGA_MAP` holds $ per channel per MGA code (bank, wirehouse, independent, IMO, regional, captive, none, total) beside
   `CHANNEL`, `CHANNEL_CALC` and `CHANNEL_OVERRIDE`. If `CHANNEL_CALC` is the channel with the most $, it is a
   largest-share rule (Conventions, Rules). Q37.

**The profile.** `explore/profile.sql`: every dataset as its distinct key combinations with rows and $, in long form,
then five parts in one result set: columns (missing by rows and $, lengths, non-digit values), pairs of keys within a
dataset by shape (the 2026-10-29 master profile, now with $), matches across datasets (0, 1 or 2+ right rows per left
value: join repeats and coverage), labels (values of channel, product and flag columns), and checks (the findings of
the two entries before: policies on 2+ product lines, agents on 2+ contacts, region ZIP ranges, the territory table
against the regions, ZIP form per dataset, totals by year). It answers what the tier-1 extracts E1-E7 were for, so
they are dropped; the tier-2 extract shrinks to a slice for testing the rebuild's SQL. Tested in DuckDB on made-up
tables with the real columns, one planted case per outcome (`explore/profile_test.sh`, 30 checks); a wrong expected
value and a misspelled column each stop it.

### 2026-10-30: opportunity first, routed by firm; the profile narrowed to it

> **Owner, 2026-10-30:** "ok first lets think through the immediate ask. We need to have opportunity data, routed by firm based on the market metrics schema as the top priority. sales can come later. Please first develop a deep understanding of our data model as it relates to opportunity and focus the profiling to the relevent items to get that deliverable done"

`DATA_MODEL.md` has a new section, Opportunity routed by firm: each step for each source with its table, columns and
status. One rule from the archived log bears on it and is not in this log's Settled; it is Q38 until the owner
confirms it for the rebuild:

> **Owner, 2026-10-25** (archived log, line 1351): "no, we need to match firm 2 dist_ch based on crd, in perfect alignment with what is done for firm 1, the rest should be flagged for manual review"

The manual review was done and loaded into `ssdb_integration.lr_strategy.crd_dist_override` (`FIRM_CRD`,
`BROKER_NAME`, `DIST_CH`; a blank broker name covers the whole CRD), archived log line 1380. What the archived runs
measured, on source 2's opportunity: source 2's file names its channels differently from the vendor table (line
1299), and each of its labels has a main source 1 channel, with 8.6% of the opportunity at firms whose source 1
channel is not that main one (line 1339). That 8.6% is roughly where readings A and B of Q38 differ for source 2;
the profile measures it again, by CRD.

The profile (`explore/profile.sql`) now covers opportunity only; its sales half is in commit `73774ed`. It reads source
1's market metrics opportunity (fiscal year 2025), source 2's opportunity table, both territory tables,
`crd_dist_override` and source 1's regions, and answers: how full the firm key is (CRD, broker name, company ID) by $;
how CRD, broker name and company ID nest (which CRDs split, how cleanly company-ID rules re-key to CRD); whether a firm
has one channel (CRD - channel pairs, each source); the product and channel labels of both sources and both territory
tables; which ZIP x channel has 0, 1 or 2+ holders, by $; for source 2's opportunity, whether its CRD has one source 1
channel, several, or none, and whether `crd_dist_override` covers it; ZIP forms, region ZIP ranges, source 1's periods.
Source 1's channel is the vendor's `DIST_CH` before the query's rules (they hold names; they become rule tables at
work). Tested in DuckDB (`explore/profile_test.sh`, 27 checks, one planted case per outcome); a wrong expected value
stops it.

### 2026-10-30: the profile gains source 2's label x source 1's firm channel

> **Owner, 2026-10-30** (on Q38): "We will want firm 2's original channels to be mapped to firm 1's original channels, routed by firm? help me think through it, at the firm level - we want each new channel to match across both source firms. so it seems natural to use firm 1's original channel in the master firm mapping table, we just need to take care of mapping firm 2's original channels to align"

`explore/profile.sql` statement 7, check `S2 DIST_CH -> S1 CHANNEL OF THE CRD`: source 2's opportunity by its own
label and the one channel source 1 gives its CRD (or 2+, or no source 1 rows), marked where `crd_dist_override`
lists the CRD; the archived 2026-10-25 table, by CRD. It is the evidence for a source 2 -> source 1 channel map and
measures where that map and the firm's own route disagree. Statements 1-2 now clean each source's rows once
(`tmp_opp_s1`, `tmp_opp_s2`). DuckDB test: 31 checks.

### 2026-10-30: firm 1's company ID exists to split a CRD by channel

> **Owner, 2026-10-30:** "think about it though, each source firm applies their own inhouse logic to produce their original channels. But if both source's firm data is in the unified market metrics schema, then we can simply just use firm 1's original channels, without even explicitly mapping source firm 2 to source firm 1. instead allowing the market metrics firm data route things appropriately"

> **Owner, 2026-10-30:** "firm 1 does indeed split the same firm_crd's into multiple dist_ch's which is purely in-house logic specific to firm 1. the creation of cbd_id was actually to resolve this issue in the first place..."

So firm 1's firm is its company ID, and its channel follows the company ID; the market metrics key (CRD, broker name)
is coarser wherever firm 1 split a CRD. The archived 2026-10-29 profile of the first-pass master found 28 CRDs split
into 77 company IDs with the same CRD and broker name (archived log, line 1885): the split is invisible in the market
metrics firm columns. Source 2's opportunity carries only those columns, ZIP and product, so for a split CRD it can
follow firm 1's channel only as far as ZIP (or product) shows the split. Q38 restated; Q39, Q40 new.

`explore/profile.sql` statement 7 gains two checks. `S1 CHANNELS PER ZIP X CRD X NAME, PER CRD X NAME`: firm 1's
opportunity by whether its firm's channels differ within a ZIP or only across ZIPs. `S2 ROUTE LEVEL`: source 2's
opportunity by the finest market metrics key at which firm 1's rows give one channel (the same ZIP x CRD x broker name,
the CRD x broker name, the CRD), else 2+ or none, marked where `crd_dist_override` lists the CRD. DuckDB test: 41
checks.

### 2026-10-30: can firm 1's market metrics table give firm 2's opportunity its channel? What the queries show

> **Owner, 2026-10-30:** "can you check the queries I shared earlier for any hints on whether we can just pull our wc market metrics opporunity data at the right level of granularity to swap out the original channel in firm 2's opportunity / firm mapping? since firm 2 already conforms to the market metrics data but with a different original channel appended"

Read: `owner_sql/s1_opp_sales.sql` (`6262e2f93bbd…`), the schema run, and the session's 2026-10-25 variants of the
owner's query (`data/safe/_archive_2026-10/hub_root/mm_query_crd.sql`, `mm_query_crosswalk.sql`: the same query plus
CRD and broker name carried through; the second builds `crd_cbd_mm` at work).

1. Firm 1's original channel is a column on every row of its market metrics table, read as is unless a rule applies
   (`:469` `ELSE dist_ch`). The table's rows are finer than firm 2's file: office (`SI_OFFICE_ID`, `MM_ADDRESS_1`-`3`,
   `CITY`), share class, deposit type, quarter and month, with firm 1's company ID, territory and wholesaler appended.
2. Firm 2's file has a subset of those columns: ZIP, `FIRM_CRD`, `BROKER_NAME`, `PRODUCT_LINE`, `VA_PRODUCT_TYPE`, its
   own `DIST_CH`, `OPP`. So the finest grain both share is ZIP x CRD x broker name x product: firm 1's table grouped to
   it, with the number of channels and the channel where there is one, is the swap table. Product goes through each
   source's map, not the raw columns: RILA is a VA type in firm 2's file and a product line in firm 1's (archived log,
   2026-10-25).
3. The vendor's broker name already carries some channel splits: one name with a " - BANK" suffix has its own company
   ID (`:476`), and three name variants of another CRD go to one company ID (`:478`). CRD x broker name separates those
   when the names match exactly.
4. Firm 1's company ID is not clean on the raw rows: company 0 takes the client firm ID (`:480`), which can be a `|`
   list resolved by matching firm 1's sales (`:511`-`:594`), and company 0 with none is dropped (`:481`, `:500`). The
   archived first run found 52.26% of firm 2's opportunity in ZIP x CRD x broker name cells where firm 1's raw rows
   name 2+ company IDs, before that resolution (archived log, 2026-10-26, `FIRM_KEY`). After it, `crd_cbd_mm` (CRD x
   broker name -> resolved company ID, fiscal year 2025) had 404 rows, 382 CRDs, 393 company IDs and 13 CRDs with 2+
   (archived log, 2026-10-25). The channel itself is on the raw row and needs no resolution; the company ID (for the
   new-channel list, keyed on it) does.
5. Firm 1's table has quarters and months, and its query reads two fiscal years (`:486`): a cell's channel can change
   within a year, so the swap reads fiscal year 2025 and counts channels per cell.
6. This swap was built once, on 2026-10-25 (`mm_query_f2.sql`): 99.72% of firm 2's opportunity found firm 1's rows of
   the same ZIP x CRD x broker name x product, but where those rows carried 2+ company x channel (50.61%) the largest
   was taken, and the owner then set firm 2's channel per CRD with manual overrides. The swap without a largest-share
   step is Q38's finest-first order.
7. The two opportunity numbers matched within 1 in 6.89% of those cells (archived log, 2026-10-25): firm 2's file is
   the same schema, not firm 1's rows with another channel (Q23). The keys line up; the amounts do not.

So the swap is possible at ZIP x CRD x broker name x product; what is open is the share of firm 2's opportunity in
cells where firm 1's rows carry 2+ channels. `S2 ROUTE LEVEL` measures it at ZIP x CRD x broker name; the product level
waits for firm 2's product labels (the profile's labels part).

### 2026-10-30: source 2's opportunity uses the market metrics broker names, suffixes included

> **Owner, 2026-10-30:** "firm 2 does not use the same suffix convention in their SALEs file but that is why the [source 2's CRD map] mapping exists. I beleve source 2's opportunity data does conform to the same market metrics broker_name with the suffixes"

So CRD x broker name keys both sources' opportunity alike, and the vendor's channel suffixes (item 3 of the entry
before) separate those splits in source 2's opportunity too. The profile's match `S2_OPP_FIRM.CRD_NAME ->
S1_OPP_FIRM.CRD_NAME` measures it (share of source 2's opportunity whose CRD x broker name source 1's rows carry).
Source 2's sales reach the broker name through its CRD map, which is CRD -> one name (2026-10-30, schema): a CRD with
suffixed names stays open there; that is sales, later.

### 2026-10-30: the opportunity profile, first run

The owner's run of `explore/profile.sql` (`aa52017` + `6171c8c`): `$TD_REPO/data/safe/profile_2026-10-30-0324.csv`,
277 rows. Source 1 is fiscal year 2025 ($196.4B); source 2's table is read whole ($179.6B, NO CHANNEL included).

**The firm key.** `FIRM_CRD` and `BROKER_NAME` are on every row of both sources (0% missing). 99.93% of source 2's $
is at a CRD x broker name that source 1's rows carry; 92.6% of source 1's $ is at CRDs source 2's table has. Source 1's
company ID is missing (0 or blank) on 26.1% of its $, and 3 company IDs carry 2+ channels (28.1% of its $); 5 company
IDs hold 15 broker names (29.0%).

**Firm 1's channel per firm.** Every CRD x broker name carries at most one non-blank `DIST_CH` in source 1's rows (pair
shapes: no broker name or CRD x broker name links to 2+ channels). A CRD spread over channels is spread through its
broker names: 4 CRDs with 12 names hold 28.4% of source 1's $ and 29.3% of source 2's. Within a ZIP x CRD x broker
name, firm 1 never has 2+ channels (4 rows, $0.00B); 5.85% of its $ is at firms with a channel in some ZIPs and a blank
`DIST_CH` in others. So Q40's split follows the broker name, not the place, and the company ID is the weaker key.

**Routing source 2 by firm 1's channel** (`S2 ROUTE LEVEL`, blank counted as a channel): 99.71% of source 2's $ finds
one channel at the same ZIP x CRD x broker name (33.50 points of it at CRDs `crd_dist_override` lists); 0.21% at the
CRD x broker name only; 0.02% at the CRD only; 0.00% where the ZIP cell has 2+; 0.05% has no source 1 rows.
`crd_dist_override` has 866 rows on 51 CRDs; where it and this route disagree is not measured yet.

**Firm 1's channels are the vendor's, mostly.** Source 1's `DIST_CH` and the vendor's `CHANNEL` code line up row for
row: code 01 is IFA (185,874 rows each), code 13 is the one-firm label the rule `s1_opp_sales.sql:468` renames, code
11 is FI plus WH (105,121 + 32,531 = 137,652 rows), and codes 08, 10 and NO CHANNEL are a blank `DIST_CH` (25,955 rows,
5.06% of $). Firm 1's in-house step is the FI / WH split of code 11 and the blank for 08 and 10.

**Source 2's labels against firm 1's channel of the CRD** (% of source 2's $, CRDs with one firm 1 channel; the 4
split CRDs are '2+'): BANK 44.79 (FI 27.11, 2+ 13.82, IFA 3.70); INDEPENDENT 35.47 (IFA 21.07, 2+ 12.66, WH 1.25);
REGIONAL 11.31 (WH 7.45, 2+ 2.25, IFA 1.61); REGIONAL AGENCY 5.95 (blank 2.59, IFA 1.94, WH 1.42); NO CHANNEL 2.48.
3.61% of source 2's $ is at CRDs firm 1 gives only a blank channel, most of it REGIONAL AGENCY.

**Territories.** Source 1: 7 channels (FI, IFA, WH, IMO and three named for one firm or unit), 100 wholesalers, one
holder per channel x ZIP; each channel covers about 41.6k ZIPs (IMO 29.6k). Source 1's opportunity finds a holder for
89.02% of its $ on the raw feed label; 5.93% misses because the one-firm label is renamed (`:468`) before the lookup,
5.06% has a blank channel. The table matches the regions it comes from on 99.28% of wholesaler x ZIP pairs (0.39%
regions only, 0.34% table only); every region's `START_ZIP` is longer than 5 digits and differs from its `END_ZIP`
(whether a range crosses a 5-digit ZIP is not measured). Source 2: channels BD, BK, FP, RA (broker dealers, bank,
financial planners, regional agency), each about 42.3k ZIPs, 196 territory IDs, 74 RVPs, 12 channel x ZIPs with 2
holders; 7.71% of its ZIPs lost a leading zero (padded in the profile).

**Products.** Both sources use the same codes: `PRODUCT_LINE` FA, IA, VA (and RILA in source 1), `VA_PRODUCT_TYPE`
IOVA, RILA, TRVA (-77777 in source 1 and blank in source 2 for FA and IA). One map serves both: RILA if either column
says RILA, IOVA, VARIABLE for TRVA, INDEX, FIXED. Totals, source 1 / source 2 ($B): FA 75.89 / 63.23, RILA 58.22 /
57.71, IA 30.87 / 29.99, TRVA 28.32 / 25.59, IOVA 3.11 / 3.10.

**Periods.** Source 1's table runs from 2012 Q3 to 2026 Q2, plus fiscal year 1900 rows ($39.7B over Q1-Q3, a filler
date); fiscal year 2025 is its four quarters. Source 2 has no period (Q36); its product totals sit close to source 1's
fiscal year 2025.

### 2026-10-30: how the one-firm channel (vendor code 13) gets its label

> **Owner, 2026-10-30:** "check the queries to see how [the one-firm feed label] is mapped to become [its short label]. it should be in one of them - if not even the older mm_query.sql file"

Two places, the same in `owner_sql/s1_opp_sales.sql` and `mm_query.sql` (`:470`, `:677`, `:691` there); none in
`owner_sql/s1_sales.sql`:
- Opportunity: the rule renames the feed label (`s1_opp_sales.sql:468`), so the cell's channel is the short label.
- Territories: company 3's own regions take the short label (`:678` `select distinct case when gr.cbd = '3' then ...`),
  and the channel-level regions carrying the long label are left out (`:692`: company 0 except that label, or company
  3). The firm's territories are company 3's regions, not the channel-level ones.
- Sales: no rule; a sale of this firm takes the MGA map's channel (`s1_sales.sql:56`-`:66`) like any other (Q28).

In the profile it is one broker name, one company ID and vendor code 13 (32,482 rows, 5.84% of source 1's $); the
5.93% of source 1's $ with no holder on the raw label is this rename not yet applied.

### 2026-10-30: the route against `crd_dist_override`; firm 1's rules as a table; UNMAPPED

> **Owner, 2026-10-30:** "for route-level, how does it stack up against our oriting crd_dist override? and did the profiler apply that override? or use the less-transformed data? for opportunity with no firm 1 channel - give it a new channel on it's own so that we can keep the opportunity and sales data but easily flag it as a manual mapping exercise to be done by the project team. lets knock those items out first. and then we wil ltackle q19 and q39"

The first run applied neither: source 1's channel was the vendor's `DIST_CH` before the rules of
`s1_opp_sales.sql:459`-`:470`, and `crd_dist_override` only marked which CRDs it lists. The override was made against
firm 1's channels after those rules, so the comparison needs them.

- Firm 1's rules are now a table at work, `ssdb_integration.lr_strategy.s1_channel_rule` (`RULE_ORDER`, `CBD_ID`,
  `BROKER_NAME`, `DIST_CH`, `CHANNEL`: 11 rows from the 6 branches), made by `$TD_REPO/owner_sql/rules_s1.sql`
  (git-excluded: the rules name firms; generated from those lines). A row matches on the one column it fills; the
  lowest `RULE_ORDER` wins, as the `CASE` does.
- `explore/profile.sql` applies it to source 1's rows (`DIST_CH` is firm 1's channel, `FEED_DIST_CH` the vendor's) and
  adds: the firm-level route per CRD x broker name (the one non-blank firm 1 channel, the CRD's for a name source 1
  lacks, else UNMAPPED), for both sources; that route against `crd_dist_override` (its CRD x name row, else its CRD
  row: agrees, differs with the pair, fills a 2+ / UNMAPPED / absent route); the override table's own keys (CRD only or
  CRD x name, repeated, 2+ channels, matching no source 2 row); whether a region's ZIP range stays within one ZIP.
- DuckDB test: 62 checks, worked out by hand from the made-up rows; reversing the rule order fails one.

### 2026-10-30: masking narrowed for this directory; firm 1's rules inside the profile

> **Owner, 2026-10-30:** "no worries about the masking lapse. the real concern is people or individual's names. or sales dollars associated with firm names - which have never been pushed to this machine raw so we are good. and ok lets update that code piece to be a temporary table and add the logic to profile.sql"

> **Owner, 2026-10-30:** "carrier-based names should be handled with the "set" convention we defined earlier"

> **Owner, 2026-10-30:** "exceptions are scoped only to tools/snowflake"

Conventions, Masking, now says this. The three commits of the masking slip (`5fdc55c`, `9e3beb3`, `243dd77`) stay as
they are: the owner declined a rewrite.

`explore/profile.sql` statement 1 now builds firm 1's rules itself, as the temporary table `tmp_s1_channel_rule` (the
same 11 rows, generated from `s1_opp_sales.sql:459`-`:470`), so nothing has to run first; the permanent
`s1_channel_rule` of the entry before is not needed and `owner_sql/rules_s1.sql` is removed. The carrier-named tables
stay `SET` placeholders. The DuckDB test runs the file's own rules on made-up rows that use two of their values
(company 685 with an IFA-rule broker name: the company rule wins; the one-firm feed label): 62 checks.

### 2026-10-30: housekeeping; Q6 settled, Q19 reopened, Q40 closed

> **Owner, 2026-10-30:** "before I run the latest profile.sql script. lets do some housekeeping an ensure all relevent files/docs etc are up to date with what we've made progress on so far."

- Q6 settled from the owner's words of 2026-10-30 (Settled). Q27 narrowed to product; Q38 restated as the route's level
  and the override's role; Q21 annotated (moot for opportunity).
- Q19 back in the index: its settled form has coded labels only; the profile gave the real ones, and the label pairs
  are the session's reading until the owner confirms them; NO CHANNEL's drop (2026-10-25) predates the firm route.
- Q40 closed by the profile's first run: the split of a CRD over channels follows the broker name, never the ZIP.
- `DATA_MODEL.md`: the distributor key and the opportunity steps carry the profile's facts; the route paragraph states
  the owner's basis and what is open. `README.md` lists `explore/`. `explore/schema.sql` marked as run.
