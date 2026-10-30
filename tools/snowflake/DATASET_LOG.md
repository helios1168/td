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
- **Files.** One Run All file per layer, numbered from `01`; intermediates are temporary tables, only the layer's
  final table is kept; the checks grid is the last statement. One-off digging: `explore/<topic>.sql`.
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
- **Masking.** No person, firm or carrier names in the repo, this log or notes; this file gives amounts as
  percentages and counts.

## Settled

- The analysis is rebuilt from scratch on `DATA_MODEL.md` (owner, 2026-10-29: "we're starting from scratch").
- Territories stay fixed; a sale stays with the wholesaler credited; opportunity is tied to ZIP and channel (owner,
  2026-10-29). `DATA_MODEL.md` I1, I2.
- The two source firms are analysed separately, each with its own datasets, mapped to the common market metrics
  schema (owner, 2026-10-29 and 2026-10-30). Each source's market is its own opportunity estimate.
- The distributor key is the market metrics schema's: CRD, plus broker name on a CRD a rule splits (session, on the
  owner's 2026-10-30 description; the split list is Q27).
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
  version is in the tag; the real labels go here from the new extract.
- Extracts may carry real values; the owner includes only relevant non-sensitive columns (owner, 2026-10-30: "do not
  worry about masking I will only include relevent non-sensitive columns"). Names still stay out of the repo.

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
| Q6 | Is N one set of new labels for both sources (ρ₂ for source 2)? | 2026-10-20 |
| Q7 | Same ZIP basis for opportunity and sales? Source 1's sales ZIP is the advisor's primary address (`mm_query.sql:100`). | 2026-10-20 |
| Q17 | Sellers with no territory: whose numbers? | 2026-10-21 |
| Q21 | Opportunity and sales with no distributor (⊥_D): which new channel? | 2026-10-24 |
| Q23 | Does source 2's file match the market metrics data on the cells both have? (now a conformance check) | 2026-10-24 |
| Q27 | Which CRDs do the channel rules split by broker name (the split list)? Does I3 hold for every distributor, or only listed ones (the rest carry their current label forward)? Can product split a distributor's new channel? Folds in Q16 and Q20. | 2026-10-29 |
| Q28 | λ_s vs κ_s: in the current state, is a sale placed by its recorded label (which can depend on the seller) or by its cell's channel? | 2026-10-29 |
| Q29 | τ_s for new channels such as National: covered by ZIP, by distributor-tied territories (`mm_query.sql:691` filters them out), or the current holder kept (`mm_query.sql:718`)? Listed distributors: settled 2026-10-28. Folds in Q13. | 2026-10-29 |
| Q31 | A wholesaler's market share: territory share (sales placed in held cells ÷ their market) or credited sales ÷ held market? | 2026-10-29 |
| Q32 | Does a source's market include products it does not sell? (Settled before as "the products where it has positive sales"; reopened 2026-10-30.) | 2026-10-30 |
| Q33 | Source 1's split-policy labels `IFA/IMO` and `FI/IMO` (`owner_sql/s1_sales.sql:18`, `:21`): which channel's territories hold them, and does the IMO rule apply to them? | 2026-10-30 |

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
