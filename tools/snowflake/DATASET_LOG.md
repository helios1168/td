# Opportunity and sales by channel and territory: conventions, decisions, questions, history

One file for what we track. Sections: **Conventions**, **Settled** (decisions in force), **Key decisions** (settled
answers that move the numbers, and how to rerun them another way), **Parked** (suspended, not reversed), **Open questions** (index), **Log** (dated findings, append-only). The model is `DATA_MODEL.md`.

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
- **Columns** (layer files; an `explore/` profile reports in the long layout of `explore/profile.sql`). Source columns
  keep their names. Ratios `SHARE_` (0-1) or `PCT_` (0-100), naming what is divided by
  what; rankings `RANK_<within>_<by>`; checks `CHECK_NAME`, `VALUE`, `MUST_BE_ZERO`.
- **Rules.** Assign where unique and flag the rest; no largest-share guesses.
- **Snowflake.** How a function or clause behaves is settled by the Snowflake docs (page and date read) or by the
  owner, never assumed; a construct the owner has run at work counts as confirmed (owner, 2026-10-25).
- **Testing.** Every query runs first in DuckDB on the extract in `data/safe/extract_<date>/`. DuckDB accepts what
  Snowflake rejects: it renames a repeated column name where Snowflake errors, so every CTE is described for repeats;
  `IN` / `EXISTS` subqueries go only in `WHERE`; no named `WINDOW` clause.
- **Words.** "Source firm" (firm_1, firm_2) for the insurers, "distributor" for the broker-dealer; the rest of the
  vocabulary is in `DATA_MODEL.md`. A channel is a sales channel, never a "desk".
- **Audit.** `audit.js` checks this directory's documents against its code: a reader lists the claims of `DATA_MODEL.md`
  (the reference), `README.md` and the log entries since a date, plus fixed convention checks; auditors verify each
  against the SQL, the owner's queries, the run outputs and the archived log, one row per claim; both on GPT-6.1 Sol,
  thinking max (agents `reader-sol`, `auditor-sol`; owner, 2026-10-30: "update the models to both be gpt sol 6.1 on
  max"). Run it after a step
  that changes the model, the log or the SQL, and before the owner runs a new file:
  `subagent({ workflow: "tools/snowflake/audit.js", cwd: "<worktree>", async: true, args: { since: "<first date not
  yet audited>" } })`. Its outcome is a log entry: counts by tag, every Weakened and Falsified row with its fix (owner,
  2026-10-30: "can we save option 1 as a repeatable workflow for this snowflake-related portion of the project?").
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
- No reassignment: each wholesaler's numbers in the current state and in the new state (owner, 2026-10-21, Q3);
  the firm overrides' holder move (2026-10-28, below) is the exception.
- Listed distributors break out to new labels that merge into National; WH and FI no longer hold the opportunity or
  sales placed with them (owner, 2026-10-21).
- Firm overrides: a listed distributor takes a new label on every row, both sources, sales and opportunity. When the
  override changes the current channel (source 1: the override's channel; source 2: its own channel, stated in the
  list), the opportunity goes to the holder of ZIP x that channel, the lowest ID where 2+ hold it; sellers stay
  (owner, 2026-10-26 and 2026-10-28). `DATA_MODEL.md` τ_s and k_s for listed distributors.
- Source 2's own labels go to its territory channels BANK → BK, INDEPENDENT → FP, REGIONAL → BD, REGIONAL AGENCY → RA
  (Q19; owner, 2026-10-25 for the one-to-one map, 2026-10-30 for these pairs: "go with your recommendation"). NO
  CHANNEL is kept: no territory channel in the current state, routed by firm 1's channel in the new state (owner,
  2026-10-30; reverses the drop of 2026-10-25). Its product line x VA type maps onto products (owner, 2026-10-24, Q22;
  `DATA_MODEL.md`, p). Key decision.
- Source 2's new-state holder: the source 2 territory channel of firm 1's channel, IFA → FP, FI → BK, WH → BD, PRI → RA
  (Q39; owner, 2026-10-30, "go with your recommendation"); EDJ and AMER carry none of source 2's opportunity. Key
  decision.
- Source 2's old channel in firm 1's names: its own label through Q19, then Q39 read back, BANK → FI, INDEPENDENT →
  IFA, REGIONAL → WH, REGIONAL AGENCY → PRI, NO CHANNEL blank (owner, 2026-10-30: "lets actually implement option (a)
  for the source 2's old channel in source 1's terms item"). Key decision.
- A sale's old channel is its own recorded channel, as its sales table has it (firm 1: the base sales table's
  `DIST_CH`), and layer 02's table ties exactly to the sales tables, so every sale stays in it (owner, 2026-10-30: "I want to validate against the original dist_ch at the
  firm level since that is what we have in [firm 1's base sales table]. ... which we must be able to exactly
  replicate in this new table").
- Sales stay with the wholesaler who sold them, in both states; they meet opportunity at the wholesaler, at ZIP
  grain: one row per wholesaler x ZIP x firm x product with the opportunity held (old, new) and the sales credited
  there (owner, 2026-10-30: "sales is tied to the actual wholesaler, not necessarily a cell"; "sales stay fixed to
  whoever actually sold"; "no we also want sales at the zip grain"). So Q31: a wholesaler is measured by its credited
  sales against the opportunity it holds; only the held opportunity changes between states (I2).
- One set of new channels for both sources, in firm 1's channels: both sources' opportunity is routed by firm 1's
  channel per market metrics firm; source 2's own channels serve its current state only (owner, 2026-10-30: "we want
  each new channel to match across both source firms. so it seems natural to use firm 1's original channel in the
  master firm mapping table"; "we can simply just use firm 1's original channels, without even explicitly mapping
  source firm 2 to source firm 1"). Q6.
- The route (Q38): both sources' opportunity takes firm 1's channel per CRD x broker name; `crd_dist_override` fills
  only where that route is UNMAPPED, 2+ or has no firm 1 rows, and where the two disagree the route wins (owner,
  2026-10-30: "it should land in the route_dist_ch"; the disagreement, the override's FI against the route's WH, 2.48%
  of source 2's $, is Wells). A split firm keeps its split: Wells' CRD has a WH name and a bank name, which the
  new-channel list makes Wells WH and Wells FI (owner: "capture the case where we create wells wh, and wells fi. this
  is an example of that split happening"; `DATA_MODEL.md`, Example). So the new-channel list is keyed on CRD x broker
  name; its company IDs are re-keyed off source 1's rows.
- EDJ, AMER and AFS are channels like the others, in every table and view: EDJ and AMER come from firm 1's rules
  (`s1_opp_sales.sql:468`, `:460`), old and new; AFS from the new-channel list (`:706`), new only, its firms' cells
  sitting in their original channel in the old state. A cut that leaves them out filters `NEW_CHANNEL` (owner,
  2026-10-30: "drop EDJ, AMER, from the exercise all together. they are out of scpoe for now but again record this
  decision as we will likely return to include them"; "we can drop AFS as well"; "lets actually keep EDJ, AMER, and
  AFS in first so we have a single master table across all cases which we then filter down afterwards"; "should edj,
  amer, and afs just be considered like their own channels?"; and, to the session's drop of the `SCOPE` column,
  "yes to 1"). Their holders are open: Q41 (AMER), Q44 (AFS, new state). Key decision.
- The new channels' holders (Q29): in the new state Wells WH, Wells FI and National (Chase) stay with the holder of the
  firm's original channel at the ZIP, WH for Wells WH and FI for the other two, so those cells are reclassified, not
  reassigned; source 2's through Q39 (WH → BD, FI → BK) (owner, 2026-10-30: "in the new state, wells WH, wells FI, and
  National (Chase) should go to the wholesaler who held those firms in their original distribution channel (WH for wells
  WH, FI for wells FI and National (Chase))"). The firm overrides' holder rule stands (2026-10-28). Key decision.
- Source 2's opportunity table is fiscal year 2025, the same period as source 1's (owner, 2026-10-30: "q36 is 2025").
- A source's market includes products it does not sell: each source's market is all of its opportunity, every product
  (owner, 2026-10-30: "q32 yes"; replaces "the products where it has positive sales").
- Extracts may carry real values; the owner includes only relevant non-sensitive columns (owner, 2026-10-30: "do not
  worry about masking I will only include relevent non-sensitive columns"). What may enter the repo: Conventions,
  Masking.

- Opportunity or sales with no firm 1 channel takes the channel UNMAPPED: kept, with its $, and flagged as a manual
  mapping exercise for the project team (owner, 2026-10-30: "give it a new channel on it's own so that we can keep the
  opportunity and sales data but easily flag it as a manual mapping exercise to be done by the project team"). The
  label is the session's.

## Key decisions

Settled answers whose alternative would move the numbers. Each names where it lives in the SQL; change it there, rerun,
and the named report shows the new numbers beside the logged ones (owner, 2026-10-30: "be sure to flag this as a key
decision point, and we should be able to easily come back and look at the numbers if we changed our answers here").

| decision | chosen | alternative | evidence when chosen | change it in | report |
|---|---|---|---|---|---|
| Q38: route against `crd_dist_override` | firm 1's route per CRD x broker name wins; the override fills gaps | the override wins | they differ on 2.48% of source 2's $ (Wells: FI against WH); fills 0.13% | the route and override join of the build (`profile.sql` 7, `s2_route`) | `explore/override_review.sql`; profile `S2 ROUTE (CRD X NAME) VS OVERRIDE` |
| Q19: source 2's labels to its territory channels | BANK → BK, INDEPENDENT → FP, REGIONAL → BD, REGIONAL AGENCY → RA | other pairs | the names; firm 1's channel for those firms: BANK FI 27.18, INDEPENDENT IFA 21.26, REGIONAL WH 7.45 of source 2's $ | `profile.sql` 1, `tmp_s2_label_terr` | profile `S2 HOLDER MOVES`, `... BY LABEL AND ROUTE`; matches `S2_OPP_GEO.CH_ZIP` |
| source 2's NO CHANNEL rows | kept: no current holder, routed in the new state | dropped (2026-10-25) | 2.48% of source 2's $; under the route IFA 1.29, FI 0.44, split firms 0.57, UNMAPPED or absent 0.17 | `profile.sql` 1, `tmp_s2_label_terr.KEEP_NEW` | profile `S2 HOLDER MOVES` (`DROPPED`) |
| EDJ, AMER, AFS | channels like the others, in every table and view; a cut without them filters `NEW_CHANNEL` | out of the tables (the first answer, 2026-10-30), then kept but flagged by a `SCOPE` column | firm 1's $ (second run): EDJ 5.84%, AMER 1.39%, AFS not yet measured; no source 2 $ routes to EDJ or AMER | a cut's `new_channel NOT IN ('EDJ', 'AMER', 'AFS')` | 01 `V1 CHANNEL` (their rows); profile `S1 SCOPE`, `S2 SCOPE` (its own list) |
| Q29: holders of Wells WH, Wells FI, National (Chase) | the holder of the firm's original channel: WH, FI, FI (reclassified, not reassigned) | a national or firm-tied team; another channel's holder | not measured: the firms' $ and route channels come with the new-channel list on CRD x broker name | the build's new-label table (label → holder channel) | view 2b of the build |
| Q39: firm 1's channel to source 2's territory channel | IFA → FP, FI → BK, WH → BD, PRI → RA | other pairs | source 2's $ by route: IFA 42.82, FI 41.60, WH 12.71, PRI 2.58 (all REGIONAL AGENCY); label and route disagree on at least ~10% | `profile.sql` 1, `tmp_s1ch_s2terr` | profile `S2 HOLDER MOVES`, `... BY LABEL AND ROUTE` |
| source 2's old channel in firm 1's names | (a) its own label translated, Q19 then Q39 read back: agrees with its old wholesaler | (b) the channel firm 1 gives the firm (the route): agrees with the new channel | label and route disagree on at least ~10% of source 2's $ (the profile, second run) | `01_opportunity_sales.sql` 6, the `q39` join of `TMP_O1_DATASET` | `TMP_O1_DATASET.OLD_CHANNEL_S1` |
| firm 1's sales: company ID to firm | the firms whose market metrics rows carry the company, derived as `s1_opp_sales.sql:475-482` (the link the owner's output uses, LPL's 10/29 names included); a client firm ID list counts only for a company no row carries alone | `MM_MAP` or `CRD_TO_CBD` (Q35) | not yet measured: the Q35 part of `01_opportunity_sales.sql` compares both maps with the firm found here, by sales $ | `01_opportunity_sales.sql` 9, `tmp_o2_company_firm` | `01_opportunity_sales.sql` `SALES FIRM BASIS`, `Q35` |
| a company or CRD on 2+ firms (sales) | the firm whose firm 1 channel is the sale's (firm 1's IMO and split-policy labels on their base channel; firm 2's CHANNEL through Q19 and Q39); none or 2+: no firm, flagged | every split left without a firm | company 8 carries all three LPL broker names (`s1_opp_sales.sql:478`) | `01_opportunity_sales.sql` 8 `tmp_s1_sale_channel`, 10-11 the `m` joins | `01_opportunity_sales.sql` `SALES FIRM BASIS` (`SPLIT, ...`) |
| source 1's blank-channel rows in the new state | the holder of the firm's route at the ZIP (second run: 2 rows, $0.00B; the other blank rows, 0.23% of source 1's $, are firms with no channel, UNMAPPED either way) | no holder, as the owner's query (`s1_opp_sales.sql:719` joins the row's own label) | session, 2026-10-30: the route is the firm's channel (Q38), so its holder serves every row of the firm; source 2 already works this way (Q39) | `01_opportunity_sales.sql` 5, the `hn` join of `TMP_O1_CELLS_S1` (`f.tau`; `c.cur_label` for the alternative) | `01_opportunity_sales.sql` V2B `GAINS A HOLDER` |

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
| Q21 | Opportunity and sales with no distributor (⊥_D): which new channel? Moot for opportunity (CRD on every row); for sales UNMAPPED is the session's reading. | 2026-10-24 |
| Q23 | Does source 2's file match the market metrics data on the cells both have? (now a conformance check) | 2026-10-24 |
| Q27 | Can product split a firm's channel? (The split list: the profile, 2026-10-30; I3 for every firm: the owner's route, Q6.) | 2026-10-29 |
| Q28 | λ_s vs κ_s: in the current state, is a sale placed by its recorded label (which can depend on the seller) or by its cell's channel? | 2026-10-29 |
| Q33 | Source 1's split-policy labels `IFA/IMO` and `FI/IMO` (`owner_sql/s1_sales.sql:18`, `:21`): which channel's territories hold them, and does the IMO rule apply to them? | 2026-10-30 |
| Q34 | The unified facts: opportunity and sales stacked in one long table and put side by side only by aggregation, never joined row to row; each step of `owner_sql/s1_opp_sales.sql` goes to the layer the 2026-10-30 entry gives it. Confirm? | 2026-10-30 |
| Q35 | `CRD_TO_CBD` beside `MM_MAP`: what is it, and which one takes source 1's company IDs to CRD? | 2026-10-30 |
| Q42 | Source 2's sales: what is `MM_AMOUNT` beside `SALES_AMOUNT`? (Q36's second half; its first half, the opportunity period, is settled.) | 2026-10-30 |
| Q43 | Firm 1's LPL opportunity in the owner's output: $500MM under in total, too high per wholesaler; firm 2 ties. Which of A1-A4, B1-B3 (2026-10-30 entry; checks: `explore/lpl_checks.sql`)? If B1, layer 01's channel x ZIP holders over-credit channel wholesalers too. | 2026-10-30 |
| Q41 | Who holds AMER (company 805's channel, `s1_opp_sales.sql:460`)? Firm 1's territory step keeps company 0's regions and company 3's (`:692`), so AMER has no territory and no holder in either state. Evidence: `explore/amer_holder.sql`. | 2026-10-30 |
| Q44 | Who holds AFS (company 438, `s1_opp_sales.sql:706`) in the new state? The new-channel list gives it no holder channel, so its cells keep their channel's holder in the old state and have none in the new. | 2026-10-30 |
| Q37 | How is `MGA_MAP.CHANNEL_CALC` set: the channel with the most $ per MGA code, or a rule? | 2026-10-30 |

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

### 2026-10-30: the first audit (611 claims); what it corrects

`audit.js`, run `d05bfc35`: `reader-sol` and 11 `auditor-sol` batches, all on `gpt-6.1-sol` thinking max (the run's own
records). Every log entry dated 2026-10-30, `DATA_MODEL.md`, `README.md` and the handoff note, plus the six fixed
checks: 611 claims, **508 Verified, 77 Weakened, 26 Falsified**. Claims and rows (they quote the owner's queries):
`$TD_REPO/data/safe/audit_2026-10-30_claims.md` and `audit_2026-10-30_rows.md`.

**Corrections to entries above** (those entries stay as written; this one corrects them; C = the audit's claim id):

| C | entry | was | is |
|---|---|---|---|
| 305 | source 1 opportunity and sales query | `mm_query.sql` plus two broker-name rows, the rest whitespace | also line 3, the commented table name, differs |
| 359 | the tables' columns, item 2 | `MM_MAP` is the table profiled 2026-10-29 | its columns match that master's (plus `CHANNEL`); the archived entry does not name the table |
| 371 | the tables' columns, item 4 | the territory table has the columns of `current_territories` | the same grain and label; it has `STATE_CD`, not the CTE's `DISTCH_CHANNEL` and `CBD` |
| 392, 393 | opportunity first | archived log line 1380 for the override table | its columns: line 1368; the blank broker name rule: 1369-1370 |
| 438 | swapping firm 2's channel, item 6 | `mm_query_f2.sql` | not on disk; the archived log's 2026-10-25 entries describe it |
| 440 | same, item 7 | within 1 in 6.89% of those cells | 6.89% of source 2's opportunity $ |
| 453 | profile, first run | 3 company IDs on 2+ channels: 28.1% of source 1's $ | 19.73% (28.14% was of $ with both a company ID and a channel) |
| 454 | same | 5 company IDs, 15 names: 29.0% | 21.43% (29.01% left out missing company IDs) |
| 457 | same | 4 CRDs, 12 names: 28.4% of source 1's $ | 27.20% (28.37% left out blank channels); source 2's 29.3% stands |
| 459 | same | firm 1 never has 2+ channels within a ZIP x CRD x broker name | 4 rows do ($0.4M, 0.00%), a blank counted as a channel |
| 467 | same | 0.02% at the CRD only | 0.03% (the unrounded sum) |
| 486, 494 | same | INDEPENDENT → IFA 21.07; REGIONAL AGENCY → blank 2.59 | 21.08; 2.58 (sums of rounded parts before) |
| 506 | same | 5.93% has no holder because the one-firm label is renamed | 5.84 points are that label, 0.09 another cause |
| 542, 543 | the one-firm channel's label | `:692` leaves out the channel-level regions carrying the long label | `distch` there is the wholesaler's (`WHSLR.DISTCH`), not the region's `DISTCH_CHANNEL`: it leaves out company-0 regions whose wholesaler's channel is the long label |
| 284 | source 1 query, steps table | display changes no number | unless the master has 2+ rows for a company (`:740`), as the sales item 2 says |
| 334-345 | same, sales against `s1_sales.sql` | cites `:633`-`:640`, `:315` | `opp_final` is unique by its `GROUP BY` (`:607`-`:614`); the amount per row `:628`; no IOVA in sales by the product list (`:34`-`:36`, `:123`-`:124`), not `:315` |
| 473-478, 545, 595 | profile, first run | vendor code and `DIST_CH` line up row for row | their counts match exactly; rows are not compared yet (the profile now pairs them) |
| 395 | opportunity first | the 8.6% is where Q38's readings differ | it came from a cell-level choice that took the largest (2026-10-25), not a CRD route |
| 365, 357, 378, 444 | the tables' columns | `CHANNEL` a code; a vendor own-sales column; `RGN_CD` the credit region; the CRD map is CRD → one name | readings, not schema facts; the CRD map is keyed on CRD alone, its rows per CRD unmeasured |
| 519, 235, 566 | various | 7.71% of ZIPs; Q30 in the 2026-10-29 entry; the owner declined a rewrite | 7.71% of territory rows; Q30's text is in the archived open index (line 179); the owner waived the slip, no rewrite asked |

The handoff note `notes/2026-10-30_snowflake-opp-routing.md` is write-once: its `DATASET_LOG.md:20` cite holds Table
variables only; its `/tmp` learning was seen for one file; only the rule-priority mutation was run. The DuckDB test
has no planted case for a missing `END_ZIP` or a non-digit ZIP (C405).

**Fixed in place** (living documents): `DATA_MODEL.md` (a layer file names its symbols, C6; the shared rules beside the
shared sets, C11; source 2's period, C18; the product map is the session's, the owner's reads RILA from
`PRODUCT_LINE` only, C104, K5); Conventions, Columns, scoped to layer files (C175-C180); Settled, no reassignment,
names the firm overrides' holder move (C209); `README.md` on testing (C142); `explore/profile.sql`: a territory match
counts distinct rows, so 2+ means 2+ holders (C402), and pairs vendor code with feed label, product line with VA type,
source 2's territory code with its name (C473-C478, C514, C523-C524); `audit.js`: fixed checks read this thread's
notes only. DuckDB test: 65 checks; undoing the distinct-holder change fails one.

**Process:** two entries were edited in place against Conventions (C158): `62da7ca` (masking redactions in two quotes)
and `6c8e932` (a cite). **Not changed:** K2 (document metadata in another thread's note); the layer-file claims (C167,
C168, C387: none written yet); the uniqueness claims made before the rules were applied (C32, C103, C119, C120, C579:
the profile's next run measures them after).

### 2026-10-30: the opportunity profile, second run (firm 1's rules applied)

The owner's run of `explore/profile.sql` at `0cd7229`: `$TD_REPO/data/safe/profile_2026-10-30-0444.csv`, 389 rows.

- **Firm 1's rules.** Vendor code 08 becomes AMER and code 10 PRI through the company-ID rules (6,537 and 14,482 rows,
  each code's own count); code 13 is the one-firm label (EDJ). The pairs now show it row by row: code 01 and 13 are
  1 : 1 with their feed labels, code 11 holds FI and WH, codes 08, 10 and NO CHANNEL have no feed label. Corrects the
  first run's entry: the blank for 08 and 10 was not firm 1's last word; after the rules 0.23% of source 1's $ (1,436
  rows) has no channel.
- **One channel per firm.** After the rules every CRD x broker name still has at most one channel (pair shapes); the
  firm-level route gives one channel to 99.77% of source 1's $ (UNMAPPED 0.23%; a blank row in a firm with a channel:
  2 rows, $0.00B) and to source 2's $: IFA 42.82%, FI 41.60%, WH 12.71%, PRI 2.58%, UNMAPPED 0.25%, no source 1 rows
  0.05%. The ZIP-level route adds nothing over it.
- **The route against `crd_dist_override`** (source 2's $): no override 66.39% (route found 66.22, UNMAPPED 0.12, no
  source 1 rows 0.05); override = route 31.01%; override FI where the route is WH 2.48% ($4.46B); the override fills an
  UNMAPPED route 0.13% (IFA 0.08, FI 0.04, WH 0.01). The table has 59 keys, all CRD x broker name, none with 2+
  channels, none outside source 2; 38 keys repeat (866 rows): a join on it must take distinct keys.
- **Holders.** Source 1's opportunity finds a holder for 98.28% of its $ on firm 1's channel; 1.49% has none, most of it
  AMER, a channel with no territory in source 1's table (Q41); 0.23% has no channel. Source 2's territory codes pair
  1 : 1 with their names (BD broker dealers, BK bank, FP financial planners, RA regional agency).
- **Products.** Source 1: RILA is RILA in both columns; FA and IA carry -77777; VA carries IOVA or TRVA. Source 2: VA
  carries IOVA, RILA or TRVA; FA and IA no VA type. The one map of `DATA_MODEL.md` (p) holds for both.
- Q38 restated with these numbers; Q41 new.

### 2026-10-30: the override review query

> **Owner, 2026-10-30:** "draft a query so I can see details on the cases in 2"

`explore/override_review.sql`: one row per CRD x broker name of every CRD where `crd_dist_override` and firm 1's route
disagree (the 2.48% of source 2's $ in the second profile run), all the CRD's names, the disputed ones first: status,
the override's channel, firm 1's route and whether it came from the name or the CRD, firm 1's channel mix for the name
in $ shares, its vendor `DIST_CH`, vendor codes, company IDs and the rules that fired, its fiscal year 2025
opportunity, source 2's own labels, opportunity and share, and the override's row count. Firm names and opportunity $
appear (Conventions, Masking: allowed here). The rules are `profile.sql`'s; the DuckDB test
(`explore/override_review_test.sh`, 16 checks) fails if the two copies differ, and a flipped status test fails it.

### 2026-10-30: Q38 settled: the route wins; Wells is the split case

> **Owner, 2026-10-30:** "it should land in the route_dist_ch. note that this overall firm is wells and capture the case where we create wells wh, and wells fi. this is an example of that split happening"

Settled (Settled, The route): firm 1's channel per CRD x broker name for both sources, the override only for the gaps;
Q38 leaves the index. The owner read the cases at work with `explore/override_review.sql`: the disagreement is Wells.
Wells in the owner's query: the name `Wells Fargo Clearing Services, LLC` is WH by the rule `s1_opp_sales.sql:461` and
company ID 1822 (`:475`); its `- BANK` name is company ID 1823 (`:476`); the new-channel list sends 1822 and 14 to
Wells WH and 1823 to Wells FI (`:704`-`:705`). On the shared firm key the two names are two firms with two channels
and two new labels, so the new-channel list re-keyed to CRD x broker name carries the split; company 14's CRD x
broker name is read off source 1's rows when the list is built. `DATA_MODEL.md` takes Wells as its second example.

### 2026-10-30: Q19 and Q39 settled; NO CHANNEL kept; key decisions flagged

> **Owner, 2026-10-30:** "go with your recommendation but be sure to flag this as a key decision point, and we should be able to easily come back and look at the numbers if we changed our answers here"

The recommendations (second run's cross-tab of source 2's label against firm 1's channel of the CRD, % of source 2's
$): Q19 BANK → BK, INDEPENDENT → FP (by elimination; firm 1 sees it as IFA, 21.26 of 35.47), REGIONAL → BD (by
elimination; WH, 7.45 of 11.31), REGIONAL AGENCY → RA; NO CHANNEL kept and routed (IFA 1.29, FI 0.44, split firms
0.57, UNMAPPED or absent 0.17); Q39 IFA → FP, FI → BK, WH → BD, PRI → RA (PRI's 2.58 is all REGIONAL AGENCY). Where label
and route disagree, source 2's opportunity changes holder in the new state: at least ~10% of its $ by the CRD-level
cross-tab (BANK as IFA 3.70, REGIONAL AGENCY as IFA 1.94, REGIONAL as IFA 1.61, REGIONAL AGENCY as WH 1.42, INDEPENDENT
as WH 1.30), more inside the split firms.

New section Key decisions: Q38, Q19, NO CHANNEL, Q39, each with its alternative, evidence, the SQL to change and the
report. `explore/profile.sql` statement 1 holds the three answers as tables (`tmp_s2_label_terr` with `KEEP_NEW`,
`tmp_s1ch_s2terr`); statement 7 gains `S2 HOLDER MOVES` (source 2's opportunity from its current territory, by label and
Q19, to its new-state territory, by route and Q39, the lowest territory ID where 2+: same, other, none, dropped) and
`... BY LABEL AND ROUTE`; source 2's coverage match now goes through Q19. DuckDB test: 76 checks; switching NO CHANNEL to
dropped fails it.

### 2026-10-30: Q41, AMER's holder: what the query shows and the evidence query

> **Owner, 2026-10-30:** "lets go to q41"

AMER is company 805's channel (`s1_opp_sales.sql:460`). The territory step keeps channel-level regions (company 0)
and company 3's own (`:692`); a region tied to any other company is left out, so if company 805 has regions of its own
they never reach the territory table, and the holder lookup (`:719`) finds no AMER: in the owner's own output AMER's
opportunity has no wholesaler. `explore/amer_holder.sql` (company in `SET company_id`, 805): every company with
regions of its own (regions, ZIPs, wholesalers, region labels, teams); what covers the company's opportunity ZIPs (its
own regions, channel-level regions per label, neither; % of its $); who sells to it in fiscal year 2025 (seller's
channel and team, whether the seller holds one of its regions; % of its sales $, no amounts). DuckDB test
(`explore/amer_holder_test.sh`, 14 checks); leaving the company's own regions out of the coverage fails it.

### 2026-10-30: EDJ and AMER out of scope; Q41 parked

> **Owner, 2026-10-30:** "drop EDJ, AMER, from the exercise all together. they are out of scpoe for now but again record this decision as we will likely return to include them"

Settled, Key decisions and Parked carry it; Q41 leaves the index for Parked with EDJ's holders. Out of scope is by
firm: a CRD x broker name whose firm 1 channel is EDJ or AMER (both are whole firms after the rules: each CRD x broker
name has one channel). In the second run that is 5.84% (EDJ) and 1.39% (AMER) of source 1's $, and none of source 2's.
`explore/profile.sql` statement 1 holds the scope as `tmp_scope_out` (delete a row to bring a channel back); statement
7 reports `S1 SCOPE` and `S2 SCOPE` and tags `OUT OF SCOPE (...)` in `S2 HOLDER MOVES`. DuckDB test: 80 checks; taking
EDJ off the list fails it.

### 2026-10-30: Q29 settled for Wells WH, Wells FI, National (Chase); AFS out of scope

> **Owner, 2026-10-30:** "in the new state, wells WH, wells FI, and National (Chase) should go to the wholesaler who held those firms in their original distribution channel (WH for wells WH, FI for wells FI and National (Chase))"

> **Owner, 2026-10-30:** "we can drop AFS as well"

Settled and Key decisions carry both; Q29 leaves the index (its last label, AFS, is out of scope). For those three
labels τ_s is the firm's original channel: the new label changes, the holder does not (view 2a reclassified, not 2b).
Whether each listed firm's firm 1 route is that channel (Chase's FI, for one) is measured when the new-channel list is
keyed on CRD x broker name in the build. `explore/profile.sql`: `tmp_scope_out` takes a kind (CHANNEL or COMPANY) and
AFS as company 438; a firm is out if its firm 1 channel or any of its source 1 rows' company IDs is listed. DuckDB
test: 81 checks.

### 2026-10-30: Q36 (period) and Q32 settled

> **Owner, 2026-10-30:** "q36 is 2025, q32 yes."

Settled: source 2's opportunity table is fiscal year 2025; a source's market includes products it does not sell.
Q36's second half (what `MM_AMOUNT` is on source 2's sales) is sales, so it continues as Q42. The opportunity
deliverable now has no open question; Q34 (stack, do not join) bites only when sales come in.

### 2026-10-30: `audit.js` can start at a log entry

Every entry today shares one date, so `since` would recheck the first audit's ~600 claims. `audit.js` takes `from` (a
Log heading after `### `) instead: that entry and every one below it. Exactly one of `since` and `from`; a heading with
no match stops the run. The reader also reads Key decisions now. Checked with a stub `runs` (six argument cases) and
the runner's validation. The next audit starts at "2026-10-30: the first audit (611 claims); what it corrects": that
entry's corrections were never audited themselves. Not run yet (owner, 2026-10-30: "do not run the audit yet").

### 2026-10-30: layer 01, opportunity routed by firm (`01_opportunity.sql`)

> **Owner, 2026-10-30:** "yes do that and create them as temporary tables for now"

`01_opportunity.sql` builds, per source, the opportunity cells with their current and new label and holder, from the
settled decisions; its four decision tables are `explore/profile.sql`'s row for row (the test compares them). Tables:
`TMP_O1_FIRM` (one row per CRD x broker name either source carries), `TMP_O1_CELLS_S1`, `TMP_O1_CELLS_S2`. The result
set: views 1, 2a, 2b, 3 summed by label, the scope, and checks (source total minus cells and current minus new must be
0; firm keys and listed labels must be single; the rest reported). DuckDB test `01_opportunity_test.sh`: 69 checks;
ten mutations each fail it (override over route, Q29 holder, client firm ID, scope by company, a decision table that
drifts from the profile's, NO CHANNEL dropped, highest holder for lowest in each source, the new-channel list keyed on
the CRD, cells with 2+ labels never counted). Snowflake: reserved keywords read 2026-10-30
(https://docs.snowflake.com/en/sql-reference/reserved-keywords), none used as a name; no `HAVING` beside `GROUP BY
ALL` (the GROUP BY page, read 2026-10-30, shows neither together), so both counts filter a grouped subquery.

Choices made in the build (session; each simple, recorded with its reason; the first is a key decision):

- Source 1's blank-channel rows take the holder of their firm's route in the new state (Key decisions).
- The new-channel list re-keyed: a CRD x broker name takes a listed label if any of its source 1 rows carries the
  listed company ID, derived as the owner's query does (`s1_opp_sales.sql:475-482`: the pinned names' IDs, then company
  0 → client firm ID). A source 2 name source 1 lacks gets no listed label; the check `NO LISTED LABEL, ANOTHER NAME OF
  THE CRD HAS ONE` reports its $.
- A cell is ZIP x CRD x broker name x product x current label: a firm's rows with a channel and without stay apart
  (`CELLS WITH 2+ CURRENT LABELS` reports them), so no $ moves between labels.
- A row with no CRD has no firm: UNMAPPED in the new state (`ROUTE BASIS` `NO CRD`). A product the map does not cover
  stays, product blank (`PRODUCT UNMAPPED`).
- Q29 in source 2: the listed firms keep the holder of their holder channel's Q39 pair (FI → BK, WH → BD); where source
  2's own label points at another territory channel (Chase on a REGIONAL row) the cell moves holder, as any firm's does.
  "Reclassified, not reassigned" holds for source 1.

### 2026-10-30: correction, the blank-channel key decision's size

The layer 01 entry gave 0.23% of source 1's $ as the size of the blank-channel choice. The second run says otherwise
(the entry "the opportunity profile, second run"): blank rows in a firm that has a channel are 2 rows, $0.00B; the
0.23% is firms with no channel at all, UNMAPPED and without a holder under either choice. Key decisions corrected.

### 2026-10-30: layer 01's dataset; holders stay at channel x ZIP

> **Owner, 2026-10-30:** "that's actually fine lets keep it at the channel x zip level for now. produce final table where I can look at opportunity by source, firm, channel, product, firm, etc"

Settled for now: holders come from the territory tables by channel x ZIP; the opportunity feed's `TERRITORY` and
`WHOLESALER_NAME` are not used. `01_opportunity.sql` statement 6 builds `TMP_O1_DATASET`: both sources' cells in
scope, stacked (`SOURCE`), one row per ZIP x CRD x broker name x product x old channel, with the old and new channel,
territory channel and wholesaler (ID and name: firm 1's `WHSLR_NM`, firm 2's territory `RVP`), how the new channel was
found, and the opportunity. Firm is CRD x broker name (no parent or display name: those come through the company ID);
firm 2's old channel is its own label (session defaults, offered 2026-10-30, not objected to). Names stay in Snowflake:
the CSV that comes here is still the summary. DuckDB test: 74 checks; dropping the scope filter or naming the new
wholesaler from the old ID fails it.

### 2026-10-30: source 2's old channel in firm 1's names (option (a))

> **Owner, 2026-10-30:** "ok slight edit, we need to include source 2's old channel as it would be in source 1's old channels. how can we implement that"

> **Owner, 2026-10-30:** "lets actually implement option (a) for the source 2's old channel in source 1's terms item"

Settled and Key decisions carry it. `TMP_O1_DATASET.OLD_CHANNEL_S1`: source 1's old channel as is; source 2's old
territory channel read back through `tmp_s1ch_s2terr` (aggregated to one row per territory channel, so it cannot fan
out). A new must-be-0 check, `Q39 TERRITORY CHANNELS ON 2+ FIRM 1 CHANNELS`, fails loudly if the pairs stop being one
to one. DuckDB test: 77 checks; reading the wrong column back, or a many-to-one pair, fails it.

The owner also asked whether a full outer join across sources could put the two opportunities side by side; the
session proposed a pivot of `TMP_O1_DATASET` instead (`SUM(CASE WHEN source = ...)` on ZIP x firm x product x new
channel; old channels and wholesalers as per-side columns): no fan-out, NULL keys kept, totals by construction (Q34).
Not built: the key and the go are the owner's.

### 2026-10-30: firm 1's LPL opportunity does not tie out (Q43)

> **Owner, 2026-10-30:** "an issue we see with firm 1 at-least is that in aggregate we seem to be ~$500MM from what we see in aggregate for LPL, but then at the individual wholesaler level we see their lpl opportunity being too high. interestingly enough it is only for source 1, with source 2 actually tieing out almost exactly. what could be driving this?"

> **Owner, 2026-10-30:** "its $500MM under in aggregate"

> **Owner, 2026-10-30:** "this is for opportunity only not sales"

The owner's current output, from `s1_opp_sales.sql`; not layer 01. The session's reading: two effects in opposite
directions. Total short: A1 `:478` sends three exact names to company 8, and Snowflake compares strings by their Unicode
codes unless a collation is set (https://docs.snowflake.com/en/sql-reference/collation, read 2026-10-30), so any other
LPL spelling falls through; A2 such a row with company 0 and no client firm ID gets NULL (`:481`) and `:500` deletes
it; A3 with a client firm ID list, `:511-594` picks the sales-matched ID or the first; A4 picked out by name, company 8
is not in `:745-772`'s fixed names, and 1385 is Wayne Hummer at the firm level. Too high per wholesaler: B1 `:692`
drops firm-specific regions, so an LPL team's ZIPs go to the channel-level holder; B2 a channel x ZIP with 2+ rows in
the territory CTE (`:678-687`, distinct over six columns) copies the opportunity; B3 on rows with sales, `:633-640`
copies `MM_OPP` onto every sales row of a seven-column key. Firm 2's opportunity has no company ID and its territories
no firm layer, so A1-A4 and B1 cannot arise there. Layer 01 has none of these but B1. Two checks given in chat, tested
in DuckDB on made-up rows (not committed): LPL's feed rows (by name and by their CRDs) with the company ID `:475-482`
gives them; every company with regions of its own, with its master name.

### 2026-10-30: the LPL checks committed (`explore/lpl_checks.sql`)

> **Owner, 2026-10-30:** "put these checks in github"

The two checks of the Q43 entry, as one Run All file with one result set (parts `LPL FEED ROWS`, `OWN REGIONS`). One
change from the chat version: the CRD lookup skips blank CRDs, so an LPL row with a blank CRD no longer pulls in every
other blank-CRD row of the feed. Snowflake: ILIKE (https://docs.snowflake.com/en/sql-reference/functions/ilike) and
`SUM(...) OVER ()` (.../functions/sum) read 2026-10-30. DuckDB test `explore/lpl_checks_test.sh`: 15 checks on the
file's own last statement; nine mutations each fail it (the CRD lookup dropped, company 0 kept instead of dropped, the
blank-CRD guard removed, the LPL list made case-insensitive, expired wholesaler rows, regions or master names read,
channel-level regions kept, the regions part left out of the result).

### 2026-10-30: layer 02, sales credited to the seller beside held opportunity (`02_sales.sql`)

> **Owner, 2026-10-30:** "lets think about this though, sales is tied to the actual wholesaler, not necessarily a cell"

> **Owner, 2026-10-30:** "sales stay fixed to whoever actually sold"

> **Owner, 2026-10-30:** "no we also want sales at the zip grain"

Settled and Key decisions carry it; Q31 leaves the index. The session's first proposal (a sale takes its cell's
holder) is withdrawn: credit never moves. `02_sales.sql` runs after `01_opportunity.sql` in the same session and
builds `TMP_O2_SALES` (each source's 2025 sales with the firm each reaches, how, scope, and whether the seller holds
that ZIP x firm x product, old and new) and `TMP_O2_DATASET` (one row per source x wholesaler x ZIP x firm x product x
new channel: opportunity held old and new, sales credited, the part sold in held cells). Firm 1's wholesaler is its
ID; firm 2's is the RVP, since its 196 territory IDs are seats held by 74 RVPs. Inputs: firm 1's sales are the table
`owner_sql/s1_sales.sql` makes (its first CREATE line and last line uncommented), checked against `SLS_RPT_DETAIL`
under that file's row filters and non-zero policies (must be 0); firm 2's sales table, `YEAR` 2025. Two new table
variables, `s1_sales` and `s2_sales`.

Session defaults, each simple and recorded (the first two in Key decisions): firm 1's company-to-firm link; splits by
channel; `SALES` is firm 1's actual sales (`DATA_MODEL.md`, σ) and firm 2's `SALES_AMOUNT`, with comp'd sales and
`MM_AMOUNT` as `SALES_ALT` until Q42; products by `s1_sales.sql:315-317` and the market metrics codes, VA sales as
VARIABLE (sales carry no VA type); EDJ, AMER and AFS firms' sales out. Q28 waits for a channel cut of sales: no sale
is placed on a channel here. Sellers with no territory (Q17) show as `SELLS, HOLDS NO OPPORTUNITY`. DuckDB test
`02_sales_test.sh` runs 01 then 02: 33 checks; ten mutations each fail it (a list over a direct company, IMO not on
IFA, held without the seller, out-of-scope sales kept, net-zero policies in the raw check, firm 2's RVP key not
cleaned, a territory code not read back, the product bucket or firm 2's year not filtered, a split guessed).
Snowflake: SPLIT_PART (https://docs.snowflake.com/en/sql-reference/functions/split_part) and CROSS JOIN
(.../constructs/join) read 2026-10-30.

### 2026-10-30: layer 02 carries the sale's own channel and ties to the sales tables

> **Owner, 2026-10-30:** "where did the old channel go? I want to validate against the original dist_ch at the firm level since that is what we have in [firm 1's base sales table]. in [firm 1's base sales table] we get ~$[amount] in sales for product_line2 <> 'FIXED' and dist_ch in ('WH', 'FI', 'IFA'). which we must be able to exactly replicate in this new table"

(The carrier's table name and the sales amount masked.) Settled carries it. The first version grouped the sale's own
channel away (`TMP_O2_DATASET` kept only the new channel; `TMP_O2_SALES` had it trimmed and upper-cased) and left the
out-of-scope firms' sales out of the dataset, so the owner's figure could not be rebuilt from it. Now `TMP_O2_DATASET`
has `OLD_CHANNEL` (on opportunity the cell's, from `TMP_O1_DATASET`; on sales the sale's own as its sales table has
it, firm 1's `DIST_CH`), `OLD_CHANNEL_S1` and `SCOPE`, and every 2025 sale: `SCOPE` 'OUT: ...' marks the EDJ, AMER
and AFS firms' sales (`TMP_O1_DATASET` has only in-scope opportunity, so those rows carry sales only); an in-scope cut
filters `SCOPE = 'IN'`. `TMP_O2_SALES` keeps the sales table's firm (`SALES_FIRM_ID`, `SALES_FIRM`), product and
channel as they are, for a firm-level check. Both sources' amounts are cast to DECIMAL(38, 6) before the union:
Snowflake's set operators want one type per column (https://docs.snowflake.com/en/sql-reference/operators-query, read
2026-10-30), and firm 2's amounts are FLOAT, which would make firm 1's sums inexact. The result set gains `TIE-OUT`
(the owner's cut: the sales table by fiscal year; the dataset's 2025 by scope) and three must-be-0 checks (the cut,
sales table minus dataset; each sales table against `TMP_O2_SALES` by firm x channel x product as the table has
them); `SALES PERIOD` lists firm 1's table by year and product bucket. Sales sit under their recorded channel (λ) in
`OLD_CHANNEL`, so a channel cut of this table places old-state sales by their recorded label; Q28 stays open for the
views. A temporary table lives only in the session that made it
(https://docs.snowflake.com/en/user-guide/tables-temp-transient, read 2026-10-30), so 01 and 02 run in one
worksheet. DuckDB test `02_sales_test.sh`: 46 checks; 16 mutations each fail it (the earlier ones, with out-of-scope
sales now dropped instead of kept; plus firm 1's or firm 2's channel cleaned, the AFS company scope matched on a
firm 2 CRD, wholesaler counts taking out-of-scope sales, firm 2's amounts left FLOAT, the tie-out cut widened).

### 2026-10-30: EDJ, AMER and AFS stay in the master tables, filtered afterwards

> **Owner, 2026-10-30:** "lets actually keep EDJ, AMER, and AFS in first so we have a single master table across all cases which we then filter down afterwards"

Settled, Key decisions and Parked carry it; the scope list (`tmp_scope_out`) is unchanged and now sets a flag, not a
filter. `TMP_O1_DATASET` keeps every cell with `SCOPE` ('IN', 'OUT: EDJ', 'OUT: AMER', 'OUT: AFS'); `TMP_O2_DATASET`
takes its opportunity rows' `SCOPE` from it (the last entry's "only in-scope opportunity" no longer holds) and already
kept every sale. Still filtered to `SCOPE = 'IN'`: 01's views 1, 2a, 2b, 3; 02's `SALES ON CELLS` and `WHOLESALERS`.
In the master tables the three carry what the settled rules give them, no more: EDJ's cells (firm 1) take the EDJ
territories' holder in both states; AMER's have none (no AMER territory, Q41, parked); AFS's take their channel's
holder in the old state and none in the new. DuckDB tests: 01 79 checks, 02 47; dropping the out-of-scope cells
again, a `SCOPE` that is always 'IN' (in 01 or in 02), and wholesaler counts or views that take out-of-scope rows each
fail them, and every earlier mutation still does.

### 2026-10-30: EDJ, AMER and AFS are channels; the SCOPE column is gone

> **Owner, 2026-10-30:** "wait what is scope column? should edj, amer, and afs just be considered like their own channels?"

> **Owner, 2026-10-30:** "yes to 1, and lets work and think through 2 now"

("1" is the session's "drop `SCOPE`, and the scope list behind it, from 01 and 02"; "2" the views showing the three as
their own channels, with their holders.) Settled and Key decisions carry it; Q41 and Q44 move from Parked to the open
index. The flag repeated `NEW_CHANNEL`: in the DuckDB fixture every opportunity row it marked out had new channel EDJ,
AMER or AFS, and no other row did. EDJ and AMER are firm 1 channels in both states; AFS exists only in the new state,
so a cut leaves them out by `NEW_CHANNEL`, never by `OLD_CHANNEL`. 01 and 02 lose `tmp_scope_out`, the `SCOPE`
columns and the in-scope filters: views 1, 2a, 2b, 3 and 02's `SALES ON CELLS` and `WHOLESALERS` cover every cell and
sale, the three as their own rows; the CSVs' `SCOPE` and `SALES SCOPE` parts are gone; the tie-out's dataset side is
one total. `explore/profile.sql` keeps its own scope list for its reports. What the flag caught and the channel does
not: firm 1 sales of company 438 that reach no market metrics firm have new channel UNMAPPED (the session proposed
applying the company-ID list to firm 1's sales directly; not approved yet). DuckDB tests: 01 81 checks, 02 44; views
or sales summaries that hide the three, AFS dropped from the new-channel list, and every earlier mutation fail them.

### 2026-10-30: layers 01 and 02 in one file (`01_opportunity_sales.sql`)

> **Owner, 2026-10-30:** "ok first go ahead and combine the opp and sales query into a single query and push to github. with the current state they are in. we will work on these edj, afs, and amer items in parallel"

`01_opportunity.sql` and `02_sales.sql` become `01_opportunity_sales.sql`, as they stood (AFS still on the
new-channel list; Q41, Q44 open). Statements 1-7 are the opportunity file's, 8-14 the sales file's renumbered (so a
cite "`02_sales.sql` N" in the entries above is now statement N + 7); one SET block holds all five table variables;
statement 15 returns both summaries in one result set under `LAYER` (OPPORTUNITY, SALES). The tests keep their
fixtures and point at the one file: `01_opportunity_test.sh` runs statements 1-7 (81 checks), `02_sales_test.sh` the
whole file including statement 15 (46 checks: two new, that the last statement carries every row of both halves and
the sales tie-out intact; dropping the sales half fails it).

### 2026-10-30: Q29's holder channels are fixed, not the firm's route

> **Owner, 2026-10-30:** "for wells fargo, we have cases where they are originally in IFA, but are then split and mapped to wells WH or wells FI. in those cases, wells WH should go to the WH wholesaler. dont write any new code but just very and check if this is implemented"

Verified, no code changed. `01_opportunity_sales.sql` pins each listed label's holder channel (`tmp_new_label`:
Wells WH → WH, Wells FI → FI, National (Chase) → FI), and a listed firm takes it whatever its own channel or the
override (`TAU`, statement 3); the route serves only unlisted firms. Probe on a copy of the DuckDB fixture: a
company-14 firm recorded IFA moves from its IFA wholesaler to the WH wholesaler. The session's suggestion of the firm's
own route as the holder channel is withdrawn: it would keep an IFA-origin Wells WH firm with its IFA wholesaler.

### 2026-10-30: the transfers script (`explore/transfers.sql`)

> **Owner, 2026-10-30:** "now using this tables format, are we able to easily see how opportunity is transfered between wholesalers as it relates to the channel swaps?"; "no in the new combined dataset"; "push these queries to github in a single script"

`TMP_O2_DATASET` holds each opportunity cell twice, under its old and its new wholesaler, on the same ZIP x firm x
product x old channel x new channel key; `explore/transfers.sql` groups on that key to pair giver and receiver.
One result set: `TRANSFERS` (from -> to wholesaler by old channel in firm 1's names and new channel; (NO HOLDER) for a
side with none) and `BOOKS` (each wholesaler's held opportunity old and new, the change, its credited sales). Firm 2
compares RVPs. Wholesaler names appear, so it is read at work and never brought here. DuckDB test
`explore/transfers_test.sh` (02_sales_test.sh's fixture plus one row: a blank-channel cell beside an IFA cell of the
same firm, ZIP and product): 9 checks; the transfers equal the cell-level old -> new wholesaler of `TMP_O1_DATASET`
(0 mismatches) and the books net to 0 per source. Five mutations fail it (pairing on `<>`, so moves to or from no
holder vanish; the receiver read from the old column; the old channel dropped from the pairing key; the books part left
out; the old book read from the new column). Dropping only `OLD_CHANNEL` from the key survives: `OLD_CHANNEL_S1`
carries it one to one, except where firm 2's NO CHANNEL and an unlisted label would both be blank.

### 2026-10-30: the sales crosswalk (`explore/sales_crosswalk.sql`)

> **Owner, 2026-10-30:** "ok doing validation work now. I need to validate at the sales level for each source firm a complete cross walk across our mappings from [firm 2's sales table] and [firm 1's base sales table] to what is in o2_dataset"

One row per source x the sales table's own key as the table has it (firm 1: `CONSOL_BRKR_DLR_ID`, `CONSOL_BROKER_NM`,
`DIST_CH`, `PRODUCT_LINE2`; firm 2: `FIRM_CRD`, `FIRM`, `CHANNEL`, `PRODUCT`), fiscal year 2025 (firm 1: bucket ALL),
with each step's output from `TMP_O2_SALES`: the channel in firm 1's names, the channel that picks the firm on a split,
the candidate market metrics firms (CRD, broker name, firm 1 route), the firm basis and firm chosen, product, new
channel; and rows, sellers, ZIPs, sales, sales alt, no-ZIP, no-seller, on-cell and held old/new $. Rows outside the
window are listed apart, and four must-be-0 checks per source tie it together: the raw table's keys against the
crosswalk, a raw key on 2+ outputs, the crosswalk against `TMP_O2_DATASET` by firm x product x old channel x new
channel, and the raw table minus crosswalk and out-of-window rows. Run after `01_opportunity_sales.sql` in the same
worksheet; it reads that file's session variables (no SET lines of its own, so an unset one fails loudly). Firm names
and sales $ sit together, so it is read at work only (Conventions, Masking). DuckDB test
`explore/sales_crosswalk_test.sh` (02_sales_test.sh's fixture plus three rows: a firm 2 CRD equal to a firm 1 company
ID, and a firm 2 cell and sale that move from R2 to R1): 16 checks. Six mutations each fail it (the channel cleaned so
variants merge; the out-of-window rows missing other buckets; the raw side keyed without the firm name; the dataset
check without the old channel; candidates joined across sources; held taken from the new state). The session's first
hand value for the held check was wrong (that sale is on a split CRD with two IFA names, so no firm); the check now
uses a one-name firm.
