# The union and territories tables: conventions, definitions, decisions, history

One file for everything we track about the two source tables and the analysis built on them. Sections:
**Conventions** (naming), **Definitions** (every `DEF_` column, current), **Settled** (decisions in
force), **Open questions** (index), **Log** (dated findings, append-only).

- Log entries are never rewritten. A wrong finding is corrected by a later entry that names it.
- An owner answer goes under its question in the log (quoted, dated), its rule into Settled, and the
  question leaves the Open questions index.
- A definition is never edited in meaning: a revision is a new column (`_V2`) and a new row.

**Purpose** (owner, 2026-10-21): "Firm 1 and firm 2 are large annuity carriers merging into a single company. I've been tasked ... to design the combined territory. Identifying who should be assigned to which channel and what the new territories should look like on the map." And: "For now we don't need to assign individuals to the new channels at the moment. But do want to see what their numbers look like in the current state with dist_ch as well as the new state with channel"

Values are the codes from `20_synthetic_tables.sql`: `firm_1` / `firm_2` (`SOURCE`), `D1_01..` /
`D2_01..` (`DIST_CH` and `territories.CHANNEL`), `N1_01..` (`NEW_DIST`), `PR01..` (`PRODUCT_V2`).
Amounts appear only as percentages. No names, IDs or dollar amounts go in this file.

## Conventions

Agreed with the owner 2026-10-21.

**Database.** Everything lives in the dedicated database and schema, so tables carry no prefix. Every
reference uses the full `database.schema.table` path; CTEs are exempt.

**Files.** `<NN>_<layer>.sql`, one per layer, continuing the numbering: `30_cell.sql`,
`31_cell_person.sql`, `40_person_rank.sql`. Each file's first statement builds its table, the next is its
checks grid. One-off digging: `explore/<topic>.sql`.

**Tables.** Named for their grain, singular: `CELL` (one row per `ZIP_CODE` x `CBD_ID` x `CHANNEL` x
`PRODUCT_V2`), `CELL_PERSON` (cell x `SOURCE` x person), `PERSON_RANK` (one row per person).

**Columns.**

| kind | rule | examples |
|---|---|---|
| source columns | keep their names exactly | `SOURCE`, `ZIP_CODE`, `CBD_ID`, `CHANNEL`, `PRODUCT_V2`, `DIST_CH`, `MM_OPP`, `ACTUAL_SALES_AMOUNT`, `CLEAN_ID` |
| one amount per firm (wide layers) | source name + `_FIRM_1` / `_FIRM_2`; `FIRM_1` is the first `SOURCE` in sort order, `FIRM_2` the second | `ACTUAL_SALES_AMOUNT_FIRM_1` |
| derived amounts | source name + what was done to it | `MM_OPP_ASSIGNED` |
| definitions | `DEF_<subject>_<rule>`; BOOLEAN for yes/no, text for labels; a revision adds `_V2` | `DEF_CONTESTED_SOLD`, `DEF_CHANNEL_GROUP` |
| ratios | `SHARE_` for 0-1, `PCT_` for 0-100, naming what is divided by what | `SHARE_SALES_OF_MM_OPP`, `PCT_OF_SOURCE_SALES` |
| rankings | `RANK_<within>_<by>` | `RANK_SOURCE_SALES`, `RANK_ALL_SHARE_SALES_OF_MM_OPP` |
| checks | `CHECK_NAME`, `VALUE`, `MUST_BE_ZERO` (as in `15`) | |

**Codes.** The coded values in this file and in the coded extract (`20_synthetic_tables.sql:7-14`):

- `firm_1` / `firm_2`: `SOURCE`.
- `D1_xx` / `D2_xx`: `DIST_CH` and `territories.CHANNEL`; the digit is the `SOURCE`, the suffix is numbered largest first.
- `N1_xx`: `NEW_DIST`.
- `PRxx`: `PRODUCT_V2`.
- `Cxxxxx`: `CBD_ID`.
- From `22_code_opp_firm2.sql` (new values of firm_2's opportunity file): `O2_xx` (`DIST_CH` labels of firm_2's file),
  `Lxx` (`PRODUCT_V2`), `Vxx` (`VA_TYPE`, a new kind), more `Cxxxxx`.
- `Pxxxxx`: `FIRM` and `PARENT` (one numbering).
- `W` person IDs, `M` names, `A` address IDs.

**Snowflake.** How a Snowflake function or clause behaves is settled by the Snowflake docs (page cited, with the
date read) or by asking the owner, never assumed; a construct the owner has run at work counts as confirmed (owner,
2026-10-25).

**Words.** Both firms are annuity carriers, so "carrier" never means a `SOURCE`. Say `firm_1` (the
`SOURCE` whose rows hold `MM_OPP`) or `firm_2`. Log entries before 2026-10-21 use "carrier" for
`firm_1`. "Sells" means positive net `ACTUAL_SALES_AMOUNT` over the scope named. `DIST_CH`, `NEW_DIST`
and `CHANNEL` are all sales channels; call each by its column name or "sales channel", never "desk". Log
entries of 2026-10-21 say "desk" for a sales channel. A row is identified by its sales channel and distribution
columns (`CHANNEL`, `DIST_CH`, `NEW_DIST`, `PARENT`, `FIRM`, ...); `MM_OPP` and `ACTUAL_SALES_AMOUNT` are amounts the row
carries. Never say "`MM_OPP` row" (owner, 2026-10-21).

## Definitions

Columns of `CELL` (`30_cell.sql`). Counts are on the coded extract of 2026-10-20.

| column | type | rule | decided | coded-extract count |
|---|---|---|---|---|
| `DEF_ZIP_VALID` | BOOLEAN | `ZIP_CODE` is 5 digits and not `00000` | session, 2026-10-21 | false: 217 cells, 0.1% of `firm_1` sales |
| `DEF_CHANNEL_GROUP` | text | `'IFA'` for IFA; `'National+WH+FI'` for the other three; NULL for any other `CHANNEL` | owner, 2026-10-21 | IFA: 52,077 cells, 59.8% of `MM_OPP`, 26.4% / 62.0% of `firm_1` / `firm_2` sales |
| `DEF_PRODUCT_SCOPE` | text | which firms sell this `PRODUCT_V2` anywhere: `'both'`, `'firm_1 only'`, `'firm_2 only'`, `'neither'` | settled product-set rule | both: 48.8% of `MM_OPP`, 17.9% / 82.2% of sales |
| `DEF_CONTESTED_SOLD_V2` | BOOLEAN | A without `CHANNEL`: both firms have positive net sales summed over all `CHANNEL`s of this `ZIP_CODE` x `CBD_ID` x `PRODUCT_V2`; set on every `CHANNEL` row of that cell | owner, 2026-10-21, Q15 | true: 568 cells (494 `ZIP_CODE` x `CBD_ID` x `PRODUCT_V2`), 6.0% of `MM_OPP`, 7.7% / 13.3% of sales |
| `DEF_CONTESTED_OFFERED_V2` | BOOLEAN | B without `CHANNEL`: both firms sell this `PRODUCT_V2` to this `CBD_ID` in any ZIP and any `CHANNEL`; set on every `CHANNEL` row of that `CBD_ID` x `PRODUCT_V2` | owner, 2026-10-21, Q15 | true: 16,469 cells, 31.3% of `MM_OPP`, 17.4% / 63.7% of sales |

Combine definitions by grouping or filtering on several `DEF_` columns at once.

## Settled

- `SOURCE` is the firm key; `firm_1` holds `MM_OPP`, `firm_2` holds none.
- Original channel = `DIST_CH` (= `territories.CHANNEL`); target channel = union `CHANNEL`.
- `SALES_WHOLESALER_TERRITORY_ID` joins `territories.CLEAN_ID`. Sales = `ACTUAL_SALES_AMOUNT`.
- A `SOURCE`'s product set is the `PRODUCT_V2` values where it has positive sales.
- `firm_2` opportunity in `15`: `firm_1`'s `MM_OPP` per (`ZIP_CODE`, `CHANNEL`), own products, split over
  its held `DIST_CH` by national sales mix (`sales_mix_held`, chosen with `17`). Under review now that
  `CBD_ID` joins the firms; superseded for a `CBD_ID` the firm never sells to by Q9 (below);
  superseded for firm_2 by its own opportunity file (owner, 2026-10-24).
- firm_2's opportunity comes from its own file, not from `15`'s split (owner, 2026-10-24). Market
  opportunity = the larger of the two firms' opportunity, compared within the same distribution firm,
  `ZIP_CODE` and product: owner, 2026-10-24: "it will be the larger of the two"; "within the same firm,
  zip_code, and product, the opporunity number should be the same for both firms" (opp-file questions 3, 4).
- firm_2's opportunity goes in a new table; the source union is untouched (owner, 2026-10-24: "yes new
  table"). `synthetic_key` is reused and extended insert-only by `22_code_opp_firm2.sql`, never rebuilt.
- `BROKER_NAME` and `FIRM_CRD` are clear in the coded export of the opportunity file (owner, 2026-10-24 for
  `BROKER_NAME`; session decision for `FIRM_CRD`, a public firm ID). Never in this repo, this log, notes or issues.
- A ZIP absent from the union table has zero opportunity; territories `DIST_CH` values absent from the
  union table are out of scope (owner, 2026-10-19).
- `CBD_ID` is the same distribution company in both `SOURCE`s and joins them (owner, 2026-10-21, Q1).
  This supersedes the earlier rejection of distribution company as a cross-firm key (`12`).
- The unit of market is the cell `ZIP_CODE` x `CBD_ID` x `CHANNEL` x `PRODUCT_V2`. `CHANNEL` =
  map(`DIST_CH`) with overrides per `FIRM`: the sales channel the firm assigns the row, not a property of the company. It stays
  in the key for channel-group reporting, each firm under its own `CHANNEL`; head-to-head matches
  on `ZIP_CODE` x `CBD_ID` x `PRODUCT_V2` (owner, 2026-10-21, Q15).
- Head-to-head is reported under two definitions side by side (owner, 2026-10-21, Q11), matched without
  `CHANNEL` (owner, 2026-10-21, Q15): **A, sold** (`DEF_CONTESTED_SOLD_V2`), both firms sell this product to
  this distribution company in this ZIP; **B, offered (strict)** (`DEF_CONTESTED_OFFERED_V2`), both firms
  sell this product to this distribution company in any ZIP.
- Naming: see Conventions (owner, 2026-10-21).
- `DIST_CH` is each firm's original sales channels; `NEW_DIST` breaks out distribution companies from the old ones;
  those `NEW_DIST` values are merged into `CHANNEL` `National`, and WH and FI no longer hold the opportunity or
  sales associated with them (owner, 2026-10-21; log entry of that day).
- Q3 closed: no reassignment. Each row keeps its `MM_OPP` on its own `DIST_CH`; a person's numbers are reported in
  the current state (`DIST_CH`) and the new state (`CHANNEL`) (owner, 2026-10-21).
- Opportunity at distribution companies a firm never sells to is reported as uncovered opportunity, not spread
  into territories (owner, 2026-10-21, Q9). Likely moot for firm_2 once its own opportunity is in (owner,
  2026-10-24, opp-file question 5); check.
- Territories rows whose `CHANNEL` is not a `DIST_CH` in the union for that `SOURCE` are out of scope (`D1_04`-`D1_07`)
  (owner, 2026-10-21; Q4 stays open).
- Names are matched within `SOURCE` by the `ZIP_CODE` x `DIST_CH` a name covers, not by edit distance
  (`21_name_match.sql`, owner, 2026-10-21).
- `L01` in the opportunity file is fixed annuity, out of scope: its rows are dropped (owner, 2026-10-24).
- `23` and `24` read `union_base`, the union without `firm_2`'s opportunity; the current
  `data_withnewchannel_union_w_joinkeys` already carries an earlier load of it (owner, 2026-10-25).
- `CBD_ID` '0' in `opp_matched` or `crd_cbd` is no company (`23` METHOD 'no company', `CBD_ID` blank). A `firm_2`
  opp-only row whose company has no `union_base` row takes `FIRM` from `crd_cbd`'s `FIRM` column; `PARENT` stays blank
  (owner, 2026-10-25).
- At work `opp_original` and `crd_cbd` are views over the real tables; the real table names stay out of this repo,
  since one names the carrier (owner, 2026-10-25). The SQL files use the two view names.
- Opportunity-file `DIST_CH` to union `DIST_CH`: `O2_01` = `D2_01`, `O2_02` = `D2_02`, `O2_03` = `D2_04`, `O2_04` =
  `D2_03`; `O2_05` is no channel and its rows are dropped (owner, 2026-10-25, Q19).
- Opportunity-file product to `PRODUCT_V2`: `L02` (indexed annuity) = `PR03`; `PR05` x `V01` / `V02` / `V03` =
  `PR04` / `PR01` / `PR02` (owner, 2026-10-24, Q22; found by the equality test of that day).

## Open questions

| Q | question | log entry |
|---|---|---|
| Q2 | What does `MM_OPP` measure: whole market or what `firm_1` can address? | 2026-10-20 |
| Q4 | What are `D1_04`-`D1_07`; rank their 34 people? | 2026-10-20 |
| Q6 | Do real `NEW_DIST` values match across `SOURCE`s? | 2026-10-20 |
| Q7 | Same ZIP basis for `MM_OPP` and sales? (period: fiscal year 2025 only, owner 2026-10-25) | 2026-10-20 |
| Q8 | What is `PR05`; leave it out of market share? | 2026-10-20 |
| Q10 | Is the `firm_2` TX/NY block with no `CLEAN_ID` W00155/W00171's territory? (check territories `NAME` at work; folds in Q5) | 2026-10-21 |
| Q12 | `firm_2` `PR05`: contribution only? | 2026-10-21 |
| Q13 | Compare National, WH, FI per distribution company rather than per ZIP? | 2026-10-21 |
| Q14 | Is there a record of selling agreements per distribution company? | 2026-10-21 |
| Q16 | `N1_06` has `D1_01` (IFA) rows: a firm-level override, IFA business of those companies counted as National? | 2026-10-21 |
| Q17 | Sellers with no territory (2.8% of `firm_2` sales): whose numbers? | 2026-10-21 |
| Q18 | Which union name column and which territories name column to match? | 2026-10-21 |
| Q20 | `FIRM_CRD` to `CBD_ID`, our own match: cardinality both ways; agreement with `opp_matched` and `crd_cbd`; same crosswalk as the union's firm_2 `CBD_ID`s? CRDs with no `CBD_ID`? Proposed rule in `23`. | 2026-10-24 |
| Q21 | `NEW_DIST` and `CHANNEL` for an opportunity row with no `CBD_ID`, and for companies with several `CHANNEL`s (`D2_04`'s default?) Proposed rule in `24`. | 2026-10-24 |
| Q23 | Is firm_2's `OPP` the same measure as `MM_OPP`? Test equality within distribution firm x `ZIP_CODE` x product where both exist (links Q2, Q7) | 2026-10-24 |
| Q24 | Where do `firm_2`'s union `CBD_ID`s come from? (owner: unknown) | 2026-10-25 |
| Q25 | Does `opp_matched` have `VA_PRODUCT_TYPE` (its export header) rather than `VA_PRODUCT_LINE` (`22`)? | 2026-10-25 |

## Log

### 2026-10-20: first look at the coded extract

Source: `data/safe/extract_2026-10-20/` (gitignored), loaded as `ssdb.duckdb` under the real table
names. Union: 97,361 rows, 18 of 23 columns (no `FISCAL_YR`, `TERR_WHOLESALER`, `SALES_WHOLESALER`,
`SALES_AMOUNT`, address IDs). Territories: 448,617 rows, 5 of 7 columns (no `NAME`, `CLEAN_NAME`).
Amounts loaded as the exported integers / 10,000 (assumed factor). `15`'s checks all pass; its
out-of-scope count (154,442) equals the count from the real run at work, so territories is complete.

#### Findings

**The union table is two tables stacked.**

| `SOURCE` | rows with `MM_OPP` only | sales only | both | neither |
|---|---|---|---|---|
| `firm_1` | 74,303 | 5,349 | 4,569 | 0 |
| `firm_2` | 0 | 12,842 | 0 | 298 |

- `firm_1` rows are mostly opportunity rows; `firm_2` rows are all sales rows.
- Row grain: `ZIP_CODE` x `DIST_CH` x `CHANNEL` x `PRODUCT_V2` x `CBD_ID` x seller. Rows repeating that
  key are extra sales rows (sum them), or an opportunity row next to a sales row. `MM_OPP` is not repeated
  across rows: 50 keys carry it twice, 25 with equal values (0.2% of `MM_OPP`, possible double count).
- On opportunity rows, `SALES_WHOLESALER_TERRITORY_ID` = `TERRITORY_WHOLESALER_TERRITORY_ID`.
- `TERRITORY_WHOLESALER_TERRITORY_ID` is the territories holder of the row's (`ZIP_CODE`, `DIST_CH`) on
  99.9% of sales rows (`firm_2`: 430 rows sit in cells with no holder).
- `SALES_WHOLESALER_HAS_TERRITORY` = 0 exactly where the seller ID is NULL (304 `firm_2` rows, 2.8% of
  its sales).

**`CHANNEL` is a property of the distribution company.**

- Each `CBD_ID` has one `FIRM`, one `CHANNEL` and one `NEW_DIST`, in both `SOURCE`s.
- 370 `CBD_ID` values occur in both `SOURCE`s, with the same `FIRM` (369) and the same `CHANNEL` (356).
- Distribution companies per `CHANNEL` (`MM_OPP` rows): IFA 340, FI 28, WH 13, National 3. The largest
  one holds 50% of National's `MM_OPP` and 40% of WH's.
- `NEW_DIST` splits National by distribution company: each National `NEW_DIST` is one `CBD_ID`.
  IFA, FI and WH each have one `NEW_DIST` per `SOURCE`.

**`DIST_CH` follows the distribution company for `firm_1`, the ZIP for `firm_2`.**

- `firm_1`: every `CBD_ID` is sold through exactly one `DIST_CH`. People are specialists: 30 hold
  `D1_01` (IFA) only, 18 hold `D1_02`+`D1_03`, 11 `D1_02`, 6 `D1_03`.
- `firm_2`: a `CBD_ID` can be served by several `DIST_CH`, but within one ZIP by one (18 of 3,826 IFA
  cells have two). 47 people hold `D2_01`+`D2_02`+`D2_03` together; in 81% of ZIPs the same person holds
  all three. 12 people hold `D2_04` only, a different person from the main holder in 96% of ZIPs.
- So the `firm_2` opportunity split over `DIST_CH` changes a person's total only between the main holder
  and the `D2_04` holder (and in the 19% of ZIPs where `D2_01`-`D2_03` are held by different people).

**`DIST_CH` -> `CHANNEL`.**

| `DIST_CH` | `CHANNEL` (`NEW_DIST`) | % of `firm_1` sales | % of `MM_OPP` |
|---|---|---|---|
| `D1_01` | IFA (`N1_01`) | 26.4 | 59.8 |
| `D1_01` | National (`N1_06`) | 2.1 | none |
| `D1_02` | FI (`N1_02`) | 20.0 | 14.1 |
| `D1_02` | National (`N1_04`, `N1_05`) | 36.1 | 12.0 |
| `D1_03` | WH (`N1_03`) | 12.7 | 10.2 |
| `D1_03` | National (`N1_04`, `N1_06`) | 2.6 | 4.0 |

- `firm_1` National: on `N1_04`, `MM_OPP` sits half on `D1_02` and half on `D1_03`, but only `D1_02` sells
  there; on `N1_06`, `D1_01` sells with no `MM_OPP` and the `MM_OPP` sits on `D1_03`.
- `firm_2`: `D2_01` is IFA (94.7% of `firm_2` IFA sales), `D2_02` FI + National, `D2_03` WH + some IFA
  and National, `D2_04` IFA + WH (small). 209 rows have no `DIST_CH` (208 of them `ZIP_CODE` `00000`,
  no amounts).

**Products.**

| `PRODUCT_V2` | % of `MM_OPP` | % of `firm_1` sales | % of `firm_2` sales |
|---|---|---|---|
| `PR01` | 48.8 | 17.9 | 82.2 |
| `PR02` | 21.6 | 8.6 | 0 |
| `PR03` | 26.8 | 73.5 | 0 |
| `PR04` | 2.8 | 0 | 10.1 |
| `PR05` | none | 0 | 7.7 |

**Sales against opportunity.**

- Per `ZIP_CODE` x `CHANNEL`, log sales and log `MM_OPP` correlate only 0.27-0.50, and 55-84% of cells
  with `MM_OPP` have no sales.
- 86% of `firm_2`'s sales fall in a (`ZIP_CODE`, `CHANNEL`, `FIRM`) with carrier `MM_OPP`; 88.8% of its
  own-product sales in a (`ZIP_CODE`, `CBD_ID`) with `MM_OPP` in those products.
- Negative `MM_OPP`: 119 rows, -0.03% of the total. Negative sales: 23 rows, under 0.04%.

**Territories.**

- One holder per (`ZIP_CODE`, `DIST_CH`) in both firms, and every `DIST_CH` covers about 41,600-42,300
  ZIPs (all of CONUS and more); `D1_07` covers 29,558. People hold large areas: median 1,842 ZIPs and
  3 states (`firm_1`), 843 ZIPs (`firm_2`).
- `D1_04`-`D1_07` have no union rows. 34 `firm_1` people hold only those; 9 of them still sell 4.7% of
  `firm_1`'s sales, in `D1_01`-`D1_03` rows.
- `firm_2` has 4,281 rows with no `CLEAN_ID`: whole ZIPs in `D2_01`-`D2_03` (1,300-1,700 ZIPs, 1-2
  states), where nobody else holds the ZIP.
- Sales vs holders: 85% of each firm's sales are by the holder of the (`ZIP_CODE`, `DIST_CH`), 10% by
  another person of the firm who holds it, 2-5% by a seller who holds the ZIP in another `DIST_CH`.

#### Questions for the owner

Q1. **Can the distribution company join the two firms after all?** We dropped `FIRM`/`CBD_ID` as a
cross-firm key. In this extract `CBD_ID` matches across `SOURCE`s (370 shared, same `FIRM` and
`CHANNEL`), and 88.8% of `firm_2`'s own-product sales sit in a (`ZIP_CODE`, `CBD_ID`) that has carrier
`MM_OPP`. Is `CBD_ID` the same distribution company in both firms' data (the table's "join keys")? If
yes, `firm_2` opportunity can be taken per (`ZIP_CODE`, `CBD_ID`) instead of estimated per
(`ZIP_CODE`, `CHANNEL`) with a sales-mix split.

> **Answer (owner, 2026-10-21):** "Cbd_id is indeed the same distribution company across both source
> firms." Moved to Settled.

Q2. **What does `MM_OPP` measure?** The whole market at that distribution company, ZIP and product (all
providers), or what `firm_1` can address? This decides whether `firm_2` can use it as is for `PR01`, and
whether `PR04` (`MM_OPP`, no `firm_1` sales) is a market both firms face.

Q3. **Who should get `firm_1`'s National opportunity?** On `N1_04` half of it sits on `D1_03`, which
sells nothing there; on `N1_06` the seller (`D1_01`) has none. Is the `DIST_CH` on an `MM_OPP` row
assigned by a rule? Should National opportunity follow the `DIST_CH` that sells to that distribution
company?

Q4. **What are `D1_04`-`D1_07`?** Territory channels with no union rows. Their 34 people: rank them, or
leave them out? (9 of them sell 4.7% of `firm_1`'s sales in other `DIST_CH`.)

Q5. **Is the `firm_2` block with no `CLEAN_ID` a vacancy?** 4,281 rows, one region; 430 `firm_2` sales
rows fall in cells with no holder.

Q6. **Do the real `NEW_DIST` values match across `SOURCE`s?** The codes are per `SOURCE`, so the extract
cannot show it. If they match, the National sub-channels line up across firms.

Q7. **Same period?** Are `MM_OPP` and sales for the same fiscal year, and is a sale booked at the ZIP of
the advisor's office (the same ZIP `MM_OPP` uses)? The weak sales-`MM_OPP` correlation could be either.

Q8. **What is `PR05`?** 7.7% of `firm_2`'s sales, no `MM_OPP` anywhere. Leave it out of market share?

### 2026-10-21: what `CBD_ID` would change in the `firm_2` opportunity

Compared, per `firm_2` person, the current rule (A, as in `15`) with a `CBD_ID` rule (B): `MM_OPP` in
`firm_2`'s products per (`ZIP_CODE`, `CBD_ID`), given to the `DIST_CH` that `firm_2` sells that
distribution company through in that ZIP; where it does not sell it there, by that distribution
company's national `DIST_CH` mix; where it never sells it, by the `CHANNEL` mix (as A). Query:
`explore/cbd_vs_channel.sql`. Assumes Q1 is "yes".

#### Findings

- How much of `firm_2`'s opportunity B can place by distribution company: 39.1% in cells where `firm_2`
  sells that `CBD_ID` in that ZIP, 39.8% where it sells it elsewhere, 21.1% at distribution companies
  `firm_2` never sells (still placed by the `CHANNEL` mix).
- The 47 generalists (`D2_01`+`D2_02`+`D2_03`) barely move: median 4.4%, all between -10.5% and -0.3%,
  because they hold all three `DIST_CH` in their ZIPs and the split among them stays with them.
- The 12 `D2_04` holders move a lot: 2-5x more opportunity under B (median +273%, outside the vacant
  ZIPs). A gives `D2_04` its national sales share of IFA and WH (under 1% of `firm_2` sales), so low
  sales mean low opportunity and a flattering market share: the circularity recorded with `17`. B gives
  them the opportunity of the distribution companies they actually cover.
- Overall: correlation 0.963 between A and B per person; 4.8% of the opportunity changes hands; 18 of
  72 people move more than 10%.
- Vacant ZIPs (the `firm_2` block with no `CLEAN_ID`, Q5) hold 5.6% of `firm_2`'s opportunity. A hands
  the IFA and WH part of it to whoever holds `D2_04` there (1.5% of the total) and drops the rest; B
  drops most of it. Neither should assign it silently: vacant opportunity needs its own row in `15`.
- `firm_1` is unchanged by B: its `DIST_CH` is already fixed per distribution company. The exception is
  National (Q3), where `CBD_ID` would let opportunity follow the `DIST_CH` that sells that company.

#### Questions for the owner

Q9. **Opportunity at distribution companies a firm has never sold to** (21% of `firm_2`'s): count it
in that firm's territories (spread by `CHANNEL` mix, as now), or only where the firm already does
business with that company?

Q10. **Vacant territory:** report its opportunity and sales as unassigned (a "vacant" row per ZIP), rather
than giving it to another holder in the same ZIP?

### 2026-10-21: head-to-head vs uncontested at `ZIP_CODE` x `CBD_ID` x `PRODUCT_V2`

Owner's idea: compare the firms only where they compete directly, using the cell's own `MM_OPP` for
both (no imputation), and handle each firm's uncontested part separately. Query:
`explore/contested_cells.sql`. Sales are net per cell; bad ZIPs left out (0.08% of `firm_1` sales).

#### Findings

Contested = both firms have positive sales in the cell:

| cell class | cells | % of `MM_OPP` | % `firm_1` sales | % `firm_2` sales |
|---|---|---|---|---|
| both sell | 494 | 6.0 | 7.7 | 13.3 |
| `firm_1` only sells | 6,437 | 14.3 | 92.3 | 0 |
| `firm_2` only sells | 7,104 | 13.3 | 0 | 86.7 |
| nobody sells (`MM_OPP` only) | 64,409 | 66.4 | 0 | 0 |

- Only `PR01` is sold by both firms, so every contested cell is `PR01`. `firm_1`'s main product (`PR03`,
  73% of its sales) and `firm_2`'s `PR04`/`PR05` are uncontested by construction.
- Too thin to rank people: the median seller has 6% (`firm_1`) / 8% (`firm_2`) of their sales in
  contested cells; 53 of 72 `firm_1` sellers have under 10%.
- At `ZIP_CODE` x `CBD_ID` (any product) both sell in cells with 17.7% of `MM_OPP` and 38.5% / 34.7% of
  each firm's sales.
- Defining "contested" by who sold is circular: a cell a firm failed to win drops out of its
  contested market. A definition by what both firms offer avoids that. Product both firms sell (`PR01`)
  x `CBD_ID` both firms sell to (anywhere): 35.9% of `MM_OPP`, 17.5% of `firm_1` sales, 75.8% of `firm_2`
  sales; median seller 18.5% (`firm_1`) / 73% (`firm_2`) of their sales in it. There `firm_1` sells 0.17x
  what `firm_2` sells against the same `MM_OPP`.
- In contested cells each firm's `DIST_CH` is on its own rows (one per cell in 98% / 84%), so the holder
  of a contested cell needs no attribution.

#### Questions for the owner

Q11. **Contested by outcome or by offer?** "Both sold there" (6% of `MM_OPP`) or "both offer the product
to that distribution company" (36%)? The second is apples to apples without favouring whoever already
won the cell.

> **Answer (owner, 2026-10-21):** "Let's go with both definitions A and B" (see the 2026-10-21 Q11
> entry: A sold, B offered strict). Moved to Settled.

Q12. **Uncontested opportunity of `firm_2`.** `PR04` has `MM_OPP` but only `firm_2` sells it; that is
uncontested but still measured. `PR05` has no `MM_OPP`: rank `firm_2` on it by sales contribution only?

### 2026-10-21: the same split, IFA apart from National + WH + FI

Query: the IFA section of `explore/contested_cells.sql`.

| group | % of `MM_OPP` | % `firm_1` sales | % `firm_2` sales | distribution companies |
|---|---|---|---|---|
| IFA | 61.2 | 31.4 | 63.5 | 362 |
| National + WH + FI | 38.8 | 68.6 | 36.5 | 53 |

Definition 2 (shared product x shared `CBD_ID`), shares within each group:

| group | % of group `MM_OPP` | % of group `firm_1` sales | % of group `firm_2` sales | `firm_1` / `firm_2` sales | median seller's share of their group sales |
|---|---|---|---|---|---|
| IFA | 35.9 | 25.5 | 67.5 | 0.14 | `firm_1` 22.6%, `firm_2` 66.0% |
| National + WH + FI | 36.0 | 13.9 | 90.4 | 0.22 | `firm_1` 10.1%, `firm_2` 91.6% |

- Definition 1 (both sold in the cell) stays thin in both: 6.8% of IFA `MM_OPP` (14.1% / 11.8% of the
  firms' IFA sales), 4.7% of non-IFA `MM_OPP` (4.8% / 15.9%).
- Non-IFA `firm_1` business is `PR03` (83.6% of its non-IFA sales), which `firm_2` does not sell; 32 of 64
  `firm_1` sellers have under 10% of their non-IFA sales in the contestable segment. `firm_2`'s
  non-IFA business is almost all contestable (`PR01` at shared distribution companies).
- Non-IFA is a few large distribution companies (National 4, WH 13, FI about 28), IFA many small ones;
  the largest company holds 50% of National `MM_OPP` and 40% of WH's.
- By channel within definition 2, `firm_1` / `firm_2` sales: FI 0.07, IFA 0.14, National 0.27, WH 0.42.

#### Questions for the owner

Q13. **Is non-IFA a key-account market?** With 53 distribution companies, should National, WH and FI be
compared per distribution company (both firms' sales against that company's `MM_OPP`) rather than per
ZIP? Who covers a key account may be set by relationship, not by the ZIP of the office.

### 2026-10-21: Q11, three readings of "both firms compete in this cell"

Cell = `ZIP_CODE` x `CBD_ID` x `PRODUCT_V2`. "Sells" = positive `ACTUAL_SALES_AMOUNT` in the fiscal year.

| reading | test on the data | cells | % `MM_OPP` | % `firm_1` sales | % `firm_2` sales | `firm_1` / `firm_2` sales |
|---|---|---|---|---|---|---|
| A sold | both firms sell this product to this company in this ZIP | 494 | 6.0 | 7.7 | 13.3 | 0.43 |
| B offered, strict | both firms sell this product to this company, in any ZIP | 15,632 | 31.3 | 17.4 | 63.7 | 0.20 |
| C offered, loose | both firms sell this product (anywhere) and both sell to this company (any product) | 18,899 | 35.9 | 17.5 | 75.8 | 0.17 |

- 107 distribution companies have sales from both firms; at 56 of them both sell `PR01`.
- A doubles `firm_1`'s apparent standing (0.43 against 0.20) because it keeps only cells `firm_1` already
  won: the selection effect of defining the market by outcome.
- C counts a company as contested for `PR01` even where `firm_1` sells it only `PR03`; B does not.
- "Offered" is inferred from a year of sales. A selling agreement with no sales this year reads as not
  offered; one stray sale reads as offered.

Q14. **Is there a record of selling agreements or approved products per distribution company** (who is
allowed to sell what to whom)? It would replace the inference from sales for "offered".

### 2026-10-21: correction, a distribution company can sit in several `CHANNEL`s

The 2026-10-20 finding "each `CBD_ID` has one `FIRM`, one `CHANNEL` and one `NEW_DIST`" is wrong for
`CHANNEL`: that query counted `NEW_DIST` per `CBD_ID` within a `CHANNEL`, so it could not see a
`CBD_ID` in two channels. Checked directly:

- 18 `CBD_ID` values have rows in 2+ `CHANNEL`s (mostly IFA with FI or WH). They are large: the biggest
  holds 10.3% of `MM_OPP` and 12.4% of positive sales; together 20% of `MM_OPP`.
- 1,982 of 80,376 `ZIP_CODE` x `CBD_ID` x `PRODUCT_V2` cells have 2+ `CHANNEL`s (4.3% of `MM_OPP`, 7.9% of
  positive sales); 587 of them have both firms.
- `FIRM` and `PARENT` are one per `CBD_ID` (one exception each); `STATE` is one per `ZIP_CODE`.
- So `CHANNEL` goes into the cell key. The 2026-10-21 contested and IFA-split figures took one `CHANNEL`
  per cell and are approximate on these cells; `30_cell.sql` recomputes them.

Q15. **For a distribution company in several channels, what decides a row's `CHANNEL`?** The office or
branch (so the same company is truly in two markets), or each firm's own classification (so the same
business can be IFA for one firm and FI for the other)? If the latter, a cross-firm comparison should
match on `CBD_ID` without `CHANNEL`.

### 2026-10-21: `30_cell.sql` built; figures on the cell key with `CHANNEL`

`CELL` on the coded extract: 82,367 cells; checks all 0 (totals of `MM_OPP` and each firm's sales match
the source exactly; no duplicate keys). 88 cells have a NULL `CBD_ID`; 217 an invalid ZIP.

With `CHANNEL` in the key, the IFA split moves from the 2026-10-21 approximation: IFA is 59.8% of
`MM_OPP` (was 61.2), 26.4% of `firm_1` sales (31.4), 62.0% of `firm_2` sales (63.5). B covers 30.4% of
`MM_OPP` (31.3), A 5.8% (6.0).

A and B by channel group, valid ZIPs, shares within the group:

| group | A | B | % of group `MM_OPP` | % `firm_1` | % `firm_2` |
|---|---|---|---|---|---|
| IFA | no | no | 68.3 | 72.5 | 41.4 |
| IFA | no | yes | 25.1 | 11.9 | 47.6 |
| IFA | yes | yes | 6.6 | 15.6 | 11.0 |
| National+WH+FI | no | no | 71.5 | 86.3 | 32.3 |
| National+WH+FI | no | yes | 24.0 | 9.2 | 52.0 |
| National+WH+FI | yes | yes | 4.6 | 4.5 | 15.7 |

### 2026-10-21: Q15 answered, `CHANNEL` is a per-firm mapping

Q15 (2026-10-21 correction entry) asked what sets a row's `CHANNEL` when a `CBD_ID` appears in several.

> **Answer (owner, 2026-10-21):** "It is a mapping from dist_ch in combination with specific firm level
> overrides"

Proposed rule: keep `CHANNEL` in the `CELL` key (channel-group reporting stays, each firm under its own
desk's channel), and match the firms head-to-head on `ZIP_CODE` x `CBD_ID` x `PRODUCT_V2` without `CHANNEL`,
through new columns `DEF_CONTESTED_SOLD_V2` and `DEF_CONTESTED_OFFERED_V2`.

> **Approval (owner, 2026-10-21):** "Yes"

Queries: `explore/channel_mapping.sql`, rerun on the coded extract of 2026-10-20.

#### Evidence

- `CHANNEL` is a function of `SOURCE` x `DIST_CH` x `FIRM`. By `SOURCE` x `DIST_CH`: 9 groups, 8 map to 2+
  `CHANNEL`s. By `SOURCE` x `DIST_CH` x `FIRM`: 873 groups, 2 map to 2+ `CHANNEL`s. Those 2 are `firm_2`
  groups with a NULL `DIST_CH` (2 rows each, no amounts, no `MM_OPP`); with NULL `DIST_CH` left out, 666
  groups and none map to 2+ `CHANNEL`s. (The brief that set this check said the 2 were NULL-`FIRM` groups;
  the extract shows NULL `DIST_CH`, `FIRM` is set.)
- Of the 18 `CBD_ID`s in 2+ `CHANNEL`s, only 2 (`C00110`, `C00358`) have each `SOURCE` in one `CHANNEL`,
  with the two `SOURCE`s in different ones. In the other 16, at least one `SOURCE` itself uses 2+
  `CHANNEL`s for the company ("uses" = has a row, opportunity or sales).
- Within one `ZIP_CODE` x `CBD_ID` of these 18 companies, `firm_1` uses 2+ `CHANNEL`s in 1,395 of 10,878
  pairs (those pairs hold 39.0% of its positive sales at these companies), `firm_2` in 62 of 2,266 (4.7%).
- At `ZIP_CODE` x `CBD_ID` x `PRODUCT_V2` with positive net sales by both firms (494 cells): 466 have both
  firms selling in the same `CHANNEL`, 28 more have both selling but only in different `CHANNEL`s.

#### Both definitions with and without `CHANNEL` in the match

`30_cell.sql` statement 3 on the coded extract (cells are `CELL` rows, one per `CHANNEL`; checks all 0).
The V2 columns move 102 cells into A (568 against 466 `CELL` rows; the 494 cells above) and 840 into B
(16,469 against 15,629).

| definition | true: cells | % `MM_OPP` | % `firm_1` sales | % `firm_2` sales |
|---|---|---|---|---|
| `DEF_CONTESTED_SOLD` (A, with `CHANNEL`) | 466 | 5.8 | 7.4 | 12.8 |
| `DEF_CONTESTED_SOLD_V2` (A) | 568 | 6.0 | 7.7 | 13.3 |
| `DEF_CONTESTED_OFFERED` (B, with `CHANNEL`) | 15,629 | 30.4 | 17.3 | 62.1 |
| `DEF_CONTESTED_OFFERED_V2` (B) | 16,469 | 31.3 | 17.4 | 63.7 |

- The `_V2` figures equal the 2026-10-21 head-to-head table that matched on `ZIP_CODE` x `CBD_ID` x
  `PRODUCT_V2` (A 6.0 / 7.7 / 13.3, B 31.3 / 17.4 / 63.7), so that table was the right one for head-to-head;
  the `CHANNEL`-keyed figures differ from it only by splitting a company across its desks.
- Every `_V1` true row is `_V2` true (two must-be-zero checks in `30_cell.sql`).

### 2026-10-21: `CHANNEL`-keyed head-to-head columns removed

Owner, on removing the "V1 implies V2" checks and claim: "Yes". On the `CHANNEL`-keyed head-to-head columns: "Old columns go".
`DEF_CONTESTED_SOLD`, `DEF_CONTESTED_OFFERED` and the two V1-implies-V2 checks are gone from `30_cell.sql`. The
line above, "Every `_V1` true row is `_V2` true", is withdrawn: `_V2` sums net sales over `CHANNEL`s, so a firm
positive in one `CHANNEL` with larger returns in another is `_V1` true and `_V2` false. The extract passed by chance.

### 2026-10-21: owner on purpose, rows and the `DIST_CH` -> `NEW_DIST` -> `CHANNEL` flow

Owner statements, recorded in Conventions (Purpose, Codes, Words) and here.

> **Owner, 2026-10-21:** "mm_opp is an opportunity number but is not how we think about rows. We think about rows from the channel, dist_ch, new_dist, parent, firm, etc. and each of those has an associated mm_opp or opportunity amount"

`DIST_CH` is each firm's original sales channels (`firm_1`: `D1_01` IFA, `D1_02` banks, `D1_03` wirehouses).
`NEW_DIST` breaks one distribution company out of banks, and a second split between wirehouses and banks.
Those `NEW_DIST` values are merged into `CHANNEL` `National`.

> **Owner, 2026-10-21:** "Wirehouses (WH) and Banks (FI) no longer holding the opportunity or sales associated with the items we merged into National."

`firm_1`, rerun on the coded extract of 2026-10-20: distinct `CBD_ID`, share of all `MM_OPP`, share of `firm_1` sales.
"none" = no `MM_OPP` / no positive sales on those rows.

| `CHANNEL` | `NEW_DIST` | `DIST_CH` | `CBD_ID` | % of `MM_OPP` | % of `firm_1` sales |
|---|---|---|---|---|---|
| IFA | `N1_01` | `D1_01` | 350 | 59.8 | 26.4 |
| FI | `N1_02` | `D1_02` | 30 | 14.1 | 20.0 |
| WH | `N1_03` | `D1_03` | 15 | 10.2 | 12.7 |
| National | `N1_04` | `D1_02` | 1 | 4.2 | 15.2 |
| National | `N1_04` | `D1_03` | 1 | 3.8 | none |
| National | `N1_04` | NULL | 1 | 0.0 | none |
| National | `N1_05` | `D1_02` | 1 | 7.8 | 20.9 |
| National | `N1_06` | `D1_01` | 1 | none | 2.1 |
| National | `N1_06` | `D1_03` | 2 | 0.2 | 2.6 |

- The National rows agree with the 2026-10-20 `DIST_CH` -> `CHANNEL` table (`D1_02` National 12.0 / 36.1, `D1_03`
  National 4.0 / 2.6).
- `N1_06` has rows from `D1_01` (IFA): 2.1% of `firm_1` sales and no `MM_OPP`.

Q16. **Is the `N1_06` IFA business a firm-level override?** Are the IFA rows of these companies (`D1_01` -> `National`)
counted as National by a rule on the firm, so that the IFA sales of those companies leave IFA?

### 2026-10-21: owner answers, Q3, Q9 and the territories scope

**Q3** (who gets `firm_1`'s National `MM_OPP` that sits on a `DIST_CH` that does not sell there). Asked whether the
`DIST_CH` on such a row is assigned by a rule:

> **Answer (owner, 2026-10-21):** "It is set for that row's own dist_ch."

The owner framed the reassignment: "That is precisely the open question. The ultimate goal of this analysis and
this broader report and project is to define this exactly." Q3 is closed: no
reassignment. Each row keeps its `MM_OPP` on its own `DIST_CH`. People's numbers are reported in both the current
state (`DIST_CH`) and the new state (`CHANNEL`).

**Q9** (opportunity at distribution companies a firm never sells to, 21% of `firm_2`'s; count it in that firm's
territories or only where it does business):

> **Answer (owner, 2026-10-21):** "Yes for Q9"

Taken as: that opportunity is reported as uncovered opportunity, not spread into territories. It supersedes the
`firm_2` split of `15` for a `CBD_ID` the firm never sells to (Settled).

**Territories scope.**

> **Owner, 2026-10-21:** "territories table contains additional channels out of scope at this stage."

Territories rows whose `CHANNEL` is not a `DIST_CH` in the union for that `SOURCE` are out of scope (`D1_04`-`D1_07`).
Q4 (what they are, and their 34 people) stays open.

### 2026-10-21: Q10 reframed, the `firm_2` block with no `CLEAN_ID`

Restricted to the in-scope `DIST_CH`, on the coded extract:

- 4,281 `firm_2` territories rows, 1,689 ZIPs, in TX and NY, `D2_01`-`D2_03`, have no `CLEAN_ID`.
- 430 union rows (118 ZIPs, 3.68% of `firm_2` sales) fall there. Every one names `W00155` or `W00171` as territory
  wholesaler, and neither has any territories row.
- So this is most likely a failed name match between the union and territories, not a vacancy. Q10 now asks whether
  the block is their territory (check territories `NAME` at work); Q5 is folded into it.
- 12 `firm_2` `ZIP_CODE` x `DIST_CH` have 2 holders.
- 2.8% of `firm_2` sales (305 rows, `SALES_WHOLESALER_HAS_TERRITORY` = 0) have a NULL
  `SALES_WHOLESALER_TERRITORY_ID`.

Q17. **Sellers with no territory: whose numbers?** A sale by a seller with no territory has no holder to credit. Report
it apart, give it to the territory holder of the cell, or something else?

### 2026-10-21: name matching by geography, `21_name_match.sql`

The owner's old method:

> **Owner, 2026-10-21:** "I was using editdistance and running stages where we would successively cross join the firm specific union and territory datasets, takes the best match for each at any given step by lowest editdistance, then dropping the matches from the dataset and rerunning the step again on the unmatched names."

Proposed: match each union territory-wholesaler name to the territories name that covers the same `ZIP_CODE` x
`DIST_CH`, within `SOURCE`, with name similarity only as a check.

> **Approval (owner, 2026-10-21):** "Yes"

**Geography check** on the coded extract (union `TERRITORY_WHOLESALER_TERRITORY_ID` against the territories holder
of the same `ZIP_CODE` x `DIST_CH`): 138 of 141 union territory-wholesaler IDs agree with the current match.
`firm_1`: median cover 1.0, minimum 0.781; `firm_2`: all 1.0 for the 72 that agree. (`21_name_match.sql` counts
only rows with a `ZIP_CODE` and `DIST_CH`: the `firm_1` minimum there is 0.784.) The 3 exceptions: `W00155` and
`W00171` (all of their `ZIP_CODE` x `DIST_CH` sit in the block with no `CLEAN_ID`, Q10) and `W00035` in `firm_2`
(best overlap 0.2 with `W00074`).

**`21_name_match.sql` on the coded extract.** The extract has no territories `NAME` and its names are coded, so the
test used `NAME` = `CLEAN_ID` (`'NULL_BLOCK'` where NULL), which also makes name scores meaningless there. The union
names and `TERRITORY_WHOLESALER_TERRITORY_ID` are 1:1 within `SOURCE` (141 pairs); `W00035` carries the same name in
both `SOURCE`s.

| check | value |
|---|---|
| `NAME_MATCH` keys appearing twice (must be 0) | 0 |
| union names missing from `NAME_MATCH` (must be 0) | 0 |
| rows with `METHOD` geography / review | 138 / 3 |
| geography rows where `AGREES_WITH_CURRENT` is false | 0 |
| rows whose matched `CLEAN_ID` is NULL | 2 |
| territories names matched by 2+ union names | 2 |

- Review list (4 rows): `firm_1` `W00035` (cover 0.784, just under the 0.8 threshold, agrees with current);
  `firm_2` `W00035` (cover 0.333 with `W00074`, 1 of 3 `ZIP_CODE` x `DIST_CH`; 0.2 once the 208 rows with ZIP
  `00000` and NULL `DIST_CH` are counted); `W00171` (cover 1.0, the NULL block, mutual: METHOD geography, on the list for its
  NULL `CLEAN_ID`); `W00155` (cover 1.0, the NULL block, not mutual because `W00171` takes the block: review).
- The extract's NULL block is one fake name, so only one of `W00155` and `W00171` can be mutual; with real names in the block both may be.
- The name normalization (swap "LAST, FIRST", strip punctuation, drop suffix tokens) was tested alone on made-up names:
  scores 96-100, one pair lower (a middle initial, 96; "Tom Brown" vs "Tim Browne", 91).

Q18. **Which name columns?** The file matches union `TERR_WHOLESALER_CLEAN_NAME` to territories `NAME`; confirm at
work. The owner also mentioned an `updated_wholesaler2026` column in each firm's source dataset: should it be the
name to match?

### 2026-10-24: firm_2 opportunity file, owner answers

The owner has a firm_2 opportunity file at work (`opp_original`), a first-attempt match of it (`opp_matched`) and
the original CRD-to-`CBD_ID` table (`crd_cbd`). `22_code_opp_firm2.sql` codes all three with the key of
2026-10-20, extended insert-only. Questions are numbered "opp-file question N" so they do not clash with Q1-Q18.

**Opp-file question 1.** Does `synthetic_key` still exist at work, unchanged since the export of 2026-10-20? If it was dropped or rebuilt,
everything has to be re-exported together.

> **Answer (owner, 2026-10-24):** "yes"

**Opp-file question 2.** What is `broker_name`: the firm (broker-dealer) name, or an individual broker? If a person, it is coded as a name
(`M`) and stays at work.

> **Answer (owner, 2026-10-24):** "broker_name is equivalent or should be firm name. we do not need to mask it"

Flagged to the owner: a clear name beside a coded `CBD_ID` decodes the `C` and `P` codes outside work. The owner chose
"Keep broker_name in clear". `FIRM_CRD` is also clear (session decision: a public firm ID, so with the name clear
coding it hides nothing). Neither enters this repo, this log, notes or issues.

**Opp-file question 3.** Is firm_2's opportunity the same measure as firm_1's `MM_OPP` (same vendor, definition, year)? Where both firms have
opportunity on the same ZIP x company x product, are they two estimates of one market, or each firm's own share?

> **Answer (owner, 2026-10-24):** "I am not entirely sure we will have to investigate this ourselves. but in theory, within the same firm, zip_code, and product, the opporunity number should be the same for both firms. but remember they both sell in separate places the other doesnt so aggregates won't align."

Becomes Q23.

**Opp-file question 4.** If they are the same market, which number is the market for the combined company: firm_1's, firm_2's, or the
larger of the two?

> **Answer (owner, 2026-10-24):** "it will be the larger of the two"

**Opp-file question 5.** Does this file replace the derived firm_2 opportunity in `15` (firm_1's `MM_OPP` split by firm_2's sales mix)? Does it
make Q9's "uncovered" category moot for firm_2?

> **Answer (owner, 2026-10-24):** "yes it does, and likely render's q9's uncovered catgeory moot."

`15`'s split is superseded for firm_2; Q9 stays in Settled with "likely moot for firm_2; check".

**Opp-file question 6.** What are `opp_original`'s column names, its row count and its amount column? What is one row: ZIP x `firm_crd` x
`dist_ch` x `product_line`, or finer? Are keys repeated?

> **Answer (owner, 2026-10-24):** "channel (which is all null - disregard), dist_ch (which needs to be mapped to original union dist_ch), zip_code, firm_crd, broker_name, product_line (needs to be mapped to uni's product_line), va_product_type (i believe is used to distinguish VA from RILA-type of VA), and opp."

`CHANNEL` is dropped from the coded copy. Becomes Q19 (`DIST_CH`) and Q22 (`PRODUCT_LINE`, `VA_PRODUCT_TYPE`).

**Opp-file question 7.** `dist_ch`: how many distinct labels, and is each exactly one of `D2_01`-`D2_04`? Is there a label for `D2_04`, and
are there labels with no union equivalent?

> **Answer (owner, 2026-10-24):** "you will have to check this yourself"

**Opp-file question 8.** CRD to `CBD_ID`: was `opp_matched`'s match made from a reference table or by name? Is there a master table at work
with both? Can one CRD map to several `CBD_ID`s, or the reverse? Are the union's firm_2 `CBD_ID`s from the same
crosswalk?

> **Answer (owner, 2026-10-24):** "I believe much was matched by hand but I don't know if it is trustworth. But I can also give you are original crd_cbd mapping table, although I want us to craft our own. not sure about the other subquestions here. be sure we track and check them in the dataset"

> **Answer (owner, 2026-10-24), to including `crd_cbd` in the export:** "Yes, include it"

Becomes Q20.

**Opp-file question 9.** `NEW_DIST` / `CHANNEL` when a CRD has no `CBD_ID`: proposed default `D2_01` IFA, `D2_02` FI, `D2_03` WH, National only
through a known company. What does `D2_04` default to? For the 12 firm_2 companies with several `CHANNEL`s, which
one does a new opportunity row get?

> **Answer (owner, 2026-10-24):** "keep these open for investigation once I transfer the data"

**Opp-file question 10.** `product_line` to `PRODUCT_V2`: many-to-one? Product lines with no `PRODUCT_V2`? Does any map to `PR05` (Q8, Q12)?

> **Answer (owner, 2026-10-24):** "no clue you will have to check, keep these open"

**Opp-file question 11.** Output: a new table, the current union plus firm_2 opportunity rows appended as their own rows (the shape firm_1
uses), territory holder filled from territories, the source union untouched?

> **Answer (owner, 2026-10-24):** "yes new table"

**Opp-file question 12.** What is in `opp_matched` beyond the three mapped columns (a match score, a method, unmatched rows)?

> **Answer (owner, 2026-10-24):** "opp_matched hsa firm_crd, broker_name, product_line, va_product_line, opp, channel_adjusted (which matches firm 2's original dist_ch but may not be faithful we will have to investigate), product_v2, cbd_id, dist_ch, and zip_code."

#### Open questions raised

Q19. **Opportunity-file `DIST_CH` labels to the union's firm_2 `DIST_CH`.** Is the map one-to-one? Which labels
have no union value? Is `CHANNEL_ADJUSTED` faithful to the file's own `DIST_CH`? (`22` codes a label already in the
key with its `D2_xx`, a new one `O2_xx`; the coded files show which are which.)

Q20. **`FIRM_CRD` to `CBD_ID`, our own match.** Cardinality both ways; agreement with `opp_matched` and with
`crd_cbd`; are the union's firm_2 `CBD_ID`s from the same crosswalk; which CRDs have no `CBD_ID`.

Q21. **`NEW_DIST` and `CHANNEL` for an opportunity row with no `CBD_ID`, and for companies with several
`CHANNEL`s.** Proposed: `D2_01` IFA, `D2_02` FI, `D2_03` WH; what does `D2_04` default to? (Baseline below: 12 of 388 firm_2 `CBD_ID`s have several `CHANNEL`s; 144 firm_2
rows have no `CBD_ID`.)

Q22. **`PRODUCT_LINE` (+ `VA_PRODUCT_TYPE`) to `PRODUCT_V2`.** Many-to-one? Which values are unmapped? Where does `PR05`
(Q8, Q12) land? Is `VA_PRODUCT_TYPE` the same column as `VA_PRODUCT_LINE` (new kind `VA_TYPE` in `22`)?

Q23. **Is firm_2's `OPP` the same measure as `MM_OPP`?** Test equality within distribution firm x `ZIP_CODE` x product
where both exist. `22` statement 7 prints the union's `MM_OPP` total in coded units, to compare outside work with the
opportunity files' totals (settles the assumed x10,000 factor of the 2026-10-20 load). Links Q2, Q7.

#### Baseline on the extract of 2026-10-20, for the join

Rerun on `data/safe/extract_2026-10-20/ssdb.duckdb`, firm_2 rows of the union. "% firm_2 sales" = positive
`ACTUAL_SALES_AMOUNT` over firm_2's positive total (net sales differs by at most 0.01 on every line). "none" = no
positive sales. Rows with NULL `DIST_CH` have no sales.

| `DIST_CH` | `NEW_DIST` | `CHANNEL` | rows | `CBD_ID` | % firm_2 sales |
|---|---|---|---|---|---|
| `D2_01` | `N2_01` | IFA | 7,784 | 162 | 58.77 |
| `D2_02` | `N2_02` | National | 1,726 | 1 | 17.28 |
| `D2_02` | `N2_03` | FI | 1,621 | 23 | 13.04 |
| `D2_03` | `N2_01` | IFA | 489 | 13 | 2.40 |
| `D2_03` | `N2_04` | WH | 446 | 11 | 3.36 |
| `D2_02` | `N2_05` | National | 412 | 1 | 2.41 |
| NULL | `N2_01` | IFA | 194 | 194 | none |
| `D2_03` | `N2_06` | National | 149 | 2 | 1.13 |
| `D2_04` | `N2_01` | IFA | 147 | 7 | 0.43 |
| `D2_04` | `N2_04` | WH | 70 | 4 | 0.46 |
| `D2_02` | `N2_01` | IFA | 49 | 15 | 0.45 |
| `D2_02` | `N2_04` | WH | 12 | 2 | 0.08 |
| NULL | `N2_03` | FI | 10 | 10 | none |
| `D2_01` | `N2_03` | FI | 7 | 3 | 0.02 |
| `D2_02` | `N2_06` | National | 6 | 1 | 0.04 |
| `D2_03` | `N2_03` | FI | 5 | 2 | 0.10 |
| `D2_01` | `N2_02` | National | 3 | 1 | 0.01 |
| NULL | `N2_04` | WH | 3 | 3 | none |
| `D2_01` | `N2_04` | WH | 3 | 1 | 0.01 |
| `D2_01` | `N2_06` | National | 2 | 1 | 0.00 |
| `D2_03` | `N2_02` | National | 1 | 1 | 0.00 |
| NULL | `N2_05` | National | 1 | 1 | none |

- `CBD_ID` in both `SOURCE`s / firm_1 only / firm_2 only: 370 / 20 / 18.
- firm_2 sales at the 18 `CBD_ID`s firm_1 has no row for: 1.55%. Add the 144 firm_2 rows with no `CBD_ID` (0.62% of
  sales) and the share firm_1 cannot join is 2.17%.
- firm_2 `CBD_ID`s with more than one `CHANNEL`: 12 of 388.
- Shared `CBD_ID`s (370) whose set of `CHANNEL`s differs between the firms: 14. Of these, 2 have one `CHANNEL` in each
  firm and no common one (`C00110`, `C00358`: FI in firm_1, IFA in firm_2); 12 have several `CHANNEL`s in at least one
  firm and share one. 16 shared companies have several `CHANNEL`s in at least one firm; 4 of them have equal sets.
- firm_2 rows with no `CBD_ID`: 144, 0.62% of sales.

### 2026-10-24: correction, the 2026-10-20 export's amount factor was 1,000

> **Owner, 2026-10-24:** "the old factor was 1000"

The entry of 2026-10-20 loaded amounts as the exported integers / 10,000 (assumed). The factor was 1,000, so every
amount in `ssdb.duckdb` was 10 times too small. Rescaled in place on 2026-10-24: `MM_OPP` and `ACTUAL_SALES_AMOUNT` =
`ROUND(x * 10000) / 1000` (every loaded value was an exact integer / 10,000; the pre-fix file is kept beside it as
`ssdb.pre-factor-1000.duckdb`). Shares, ratios and counts in this log are unchanged: both amounts moved by the same
factor. Union `MM_OPP` total in coded units is now 55,404.3: `22` statement 7 must print the same at work, which also
confirms the opportunity files are on the extract's scale.

### 2026-10-24: `opp_original` and `crd_cbd` arrive; first checks

Files from `22` (hub root, git-excluded): `synthetic_opp_original_0..2`, `synthetic_crd_to_cbd`, loaded into
`ssdb.duckdb` as `lr_strategy.opp_original` (306,530 rows) and `lr_strategy.crd_cbd` (455 rows), all text but `OPP`.
The three `synthetic_opp_matched_*` files are byte-identical to `synthetic_opp_original_*` (same md5): `opp_matched`
has not arrived.

- `ZIP_CODE` lost its leading zeros at work (30,915 rows of 3-4 digits): stored as a number. Joins pad it to 5.
- Grain: each `DIST_CH` x `ZIP_CODE` x `FIRM_CRD` x `BROKER_NAME` comes with the same 5 product slots
  (`PRODUCT_LINE` x `VA_PRODUCT_TYPE`: `L01`, `L02`, `PR05` x `V01`/`V02`/`V03`, 61,306 rows each); 64% of rows have
  `OPP` 0, 178 negative. 46,435 keys repeat (43.6% of `OPP`); 32,527 rows are exact copies.
- `DIST_CH`: 5 labels, `O2_01`-`O2_05`, none equal to a union `DIST_CH` (Q19).
- `crd_cbd`: 227 of 455 rows have a CRD; 1 CRD has 2 `CBD_ID`s, 3 `CBD_ID`s have several CRDs. It maps 223 of the
  file's 475 CRDs, 97.6% of its `OPP` (Q20).
- Q23, first test. `OPP` summed per `CBD_ID` x `ZIP_CODE` x product (CRDs with one `CBD_ID` in `crd_cbd`) against
  `firm_1`'s `MM_OPP`, nonzero cells, equal to 0.0015 coded units:

| file product | equals `firm_1` | cells compared | % exactly equal | median ratio |
|---|---|---|---|---|
| `L02` | `PR03` | 13,280 | 70.1 | 1.0 |
| `PR05` / `V01` | `PR04` | 2,985 | 85.1 | 1.0 |
| `PR05` / `V02` | `PR01` | 17,311 | 72.3 | 1.0 |
| `PR05` / `V03` | `PR02` | 14,944 | 73.8 | 1.0 |
| `L01` | none | | 0.3-0.6 against each | 2.0-6.6 |

- Every other product pair is under 1% equal. So the two files carry one opportunity measure, and the product map
  is the table above. `L01` (35.2% of the file's `OPP`) has no `firm_1` counterpart.
- Summing repeated keys matches more cells than taking the largest row (72.9% against 66.3% over the four pairs);
  dropping exact copies changes nothing.
- Per company: 112 `CBD_ID`s are at least 95% equal (19.9% of the compared `MM_OPP`), 68 are 50-95% (55.0%),
  13 under 50% (25.1%, `firm_2` higher, median ratio 1.45). Unequal cells are mostly `firm_2` higher.
- The file's `PR05` is the union's `PR05` text (same key value), split by `VA_PRODUCT_TYPE` into `firm_1`'s `PR01`,
  `PR02`, `PR04`: a lead for Q8 (what `firm_2`'s `PR05` sales are).

### 2026-10-24: `L01` is fixed annuity, out of scope

Asked what `L01` is (35.2% of the file's `OPP`, no `firm_1` counterpart):

> **Answer (owner, 2026-10-24):** "l01 is FA standing in for 'FIXED'. fixed annuity opportunity is excluded from this
> analysis all together and is already reflected in the union table"

`L01` rows are dropped (Settled). That leaves 245,224 rows and `OPP` of 58,597.4 coded units, against `firm_1`'s
`MM_OPP` of 55,404.3. The rest of the product map (`L02` = `PR03`; `PR05` x `V01` / `V02` / `V03` = `PR04` / `PR01` /
`PR02`) comes from the equality test of the entry before; Q22 stays open until the owner confirms it against the key.

### 2026-10-24: Q22 answered, the product map

Asked to confirm the map from the equality test against the key (`L02` = `PR03`; `PR05` x `V01` / `V02` / `V03` =
`PR04` / `PR01` / `PR02`):

> **Answer (owner, 2026-10-24):** "l02 = IA which should map to product_v2 INDEX, and yes to the rest"

`L02` is indexed annuity, and the test puts it on `PR03` (70.1% of cells exactly equal), so `PR03` is the union's
index product. Q22 is closed (Settled); Q8 (what `firm_2`'s `PR05` sales are) stays open.

### 2026-10-25: `opp_matched` arrives; its maps against ours and against the data

Files `om0`-`om4` (hub root; `/om[0-9]*` added to the hub's local `.git/info/exclude`, since they hold firm names),
loaded as `lr_strategy.opp_matched`: 306,530 rows, the same rows as `opp_original` on the shared columns (`OPP` to 3
decimals), plus `CHANNEL_ADJUSTED`, `PRODUCT_V2` and `CBD_ID`.

**Product map.** Same as Settled except `PR05` x `V03`: `opp_matched` says `PR05`, Settled says `PR02` (73.8% of cells
exactly equal to `firm_1`'s `PR02`; `firm_1` has no `PR05` `MM_OPP`). `L01` (fixed, out of scope) is `L03` there.

**`DIST_CH` map (`CHANNEL_ADJUSTED`).** Cells of the file matched to `firm_2`'s union rows at the same `CBD_ID` x
`ZIP_CODE` (via `crd_cbd`):

| file `DIST_CH` | `CHANNEL_ADJUSTED` | union `DIST_CH` at the same cells | CRDs | % of non-fixed `OPP` |
|---|---|---|---|---|
| `O2_01` | `D2_01` | `D2_01` 92.7% | 300 | 49.5 |
| `O2_02` | `D2_02` | `D2_02` 76.8%, `D2_01` 21.7% | 33 | 27.3 |
| `O2_03` | `D2_04` | `D2_04` 88.7% | 11 | 8.5 |
| `O2_04` | `D2_03` | `D2_03` 93.8% | 15 | 11.9 |
| `O2_05` | NULL | `D2_01` 60.9%, `D2_04` 27.8% | 123 | 2.7 |

So the two agree on `O2_01`-`O2_04`; Q19 narrows to `O2_05`.

**CRD to `CBD_ID`.** `opp_matched` maps all 475 CRDs (2 CRDs to 2 `CBD_ID`s; 4 `CBD_ID`s from several CRDs; 421
`CBD_ID`s, 383 in the union). Our own match (Q20): for each CRD, the `CBD_ID` whose `firm_1` `MM_OPP` its `OPP`
equals in the most `ZIP_CODE` x product cells (cells of at least 0.01, settled product map). Of 429 CRDs with such
cells:

| our match | CRDs | % of comparable `OPP` |
|---|---|---|
| clear: at least 80% of cells equal, runner-up under 20% | 310 | 50.7 |
| likely: 50-80% | 25 | 10.2 |
| weak: under 50% | 26 | 38.5 |
| no equal cell | 68 | 0.5 |

- Clear and likely (335 CRDs): all three agree on 181 (56.7% of comparable `OPP`); ours = `opp_matched` where
  `crd_cbd` has no row on 144 (2.0%); ours = `opp_matched` against `crd_cbd` on 1 (0.9%); ours differs from both
  on 9 (1.3%).
- Weak (26 CRDs, 38.5%): on 15 of them (36.8%) both tables give the same `CBD_ID`, but only about a quarter of the
  cells are equal. These are large companies where the match is right and the values differ.
- Per company (`opp_matched`'s `CBD_ID`, its CRDs summed): 16 companies are under 50% equal, 23.9% of the compared
  `MM_OPP` (IFA 12, FI 2, WH 1, National 1), with `firm_2` 1.4-1.9 times `firm_1` in total. About 30% of their cells
  are equal, the rest mostly `firm_2` higher. Summing both firms to `FIRM` instead of `CBD_ID` raises the equal cells
  from 72.1% to 79.8%: part of the gap is a company split into several `CBD_ID`s on one side only. Q23 stands: one
  measure, with these companies to explain.

### 2026-10-25: Q19 answered, `O2_05` is no channel

> **Answer (owner, 2026-10-25):** "it's no channel, we can drop those rows"

Dropped: 10,464 non-fixed rows, `OPP` 1,603.9 coded units (2.7% of the non-fixed `OPP`), 123 CRDs, 120 of which have
no other `DIST_CH`. Left after dropping fixed and `O2_05`: 234,760 rows, `OPP` 56,993.5 coded units. Q19 is closed
(Settled: `O2_01`-`O2_04` as `CHANNEL_ADJUSTED` and the data give them).

### 2026-10-25: `23_crd_match.sql` and `24_union_opp.sql` built

Run on the coded extract (identity key, divisor 1; the files read every map in codes and translate through
`synthetic_key`, so they run unchanged on real values). Checks all 0. Q20 and Q21 stay open: `23` and `24` hold
proposed rules, for the owner to confirm.

**`23`.** `OPP_MAPPED` (`opp_original` with the `DIST_CH` map, the product map and `ZIP_CODE` padded to 5, one
row each, with the reason a row is dropped) and `CRD_MATCH` (one row per `FIRM_CRD` left after the drops: 355 of
the 475 CRDs; the other 120 have only dropped rows). `CBD_ID` is the equality match where it equals in at least half of the
cells, else `opp_matched` and `crd_cbd` when they agree or one has none, else `opp_matched` provisional ('review').

| `METHOD` | CRDs | % of `OPP` |
|---|---|---|
| equality | 281 | 60.5 |
| tables agree | 21 | 35.0 |
| `opp_matched` only | 50 | 0.6 |
| review | 3 | 3.9 |

- No CRD has a NULL `CBD_ID`. `AGREES` is false for 10 CRDs (6.1% of `OPP`).
- The entry of 2026-10-25 (`opp_matched` arrives) counted 335 CRDs with at least half the cells equal; this is 281.
  The difference is the `O2_05` drop of the same day (Q19), which that count predates. Rerun with the `O2_05` rows
  kept, the file reproduces the entry exactly: 429 CRDs with cells, 335 at half or more (181 agree with both tables, 144
  with `opp_matched` where `crd_cbd` has none, 1 with `opp_matched` against `crd_cbd`, 9 differ from both), 26 weak
  (38.5% of the comparable `OPP`), 68 with no equal cell. With the drop, 281 (177 / 97 / 1 / 6). The 54 are not CRDs that
  fell under half: the 120 CRDs with only `O2_05` rows leave `CRD_MATCH` (475 to 355), 54 of them equality matches and
  66 not (140 under half or without cells before, 74 now; session check, 2026-10-25). So 54 "no channel" CRDs equal
  `firm_1`'s `MM_OPP` at their company: dropping them removes only `firm_2`'s copy of that opportunity.
- Weak CRDs whose two tables give one `CBD_ID`: 14 here, 15 in the entry of 2026-10-25.

**`24`.** `UNION_OPP` is the union (97,361 rows, unchanged; an `EXCEPT` against the source is 0) plus 69,045 appended
rows, and four lineage columns. Left out: 61,306 fixed rows (31,833.9 coded units of `OPP`), 10,464 no-channel rows
(1,603.9), 107,979 keys that sum to 0. Appended `MM_OPP` is 56,993.5 coded units, equal to the file after drops;
`firm_1`'s is 55,404.3.

| appended rows by | rows | % of `MM_OPP` |
|---|---|---|
| `CHANNEL_RULE` company x `DIST_CH` | 55,637 | 84.9 |
| `CHANNEL_RULE` company | 3,979 | 5.5 |
| `CHANNEL_RULE` `DIST_CH` default (proposed, Q21) | 9,429 | 9.6 |
| `CBD_METHOD` equality | 39,734 | 60.5 |
| `CBD_METHOD` tables agree | 25,532 | 35.0 |
| `CBD_METHOD` review | 3,170 | 3.9 |
| `CBD_METHOD` `opp_matched` only | 609 | 0.6 |
| `N_HOLDERS` 1 | 67,094 | 96.6 |
| `N_HOLDERS` 0 (the block of Q10) | 1,951 | 3.4 |

- No appended row has `N_HOLDERS` 2: the 12 `firm_2` ZIP x `DIST_CH` pairs with two holders (entry of 2026-10-21) are
  in territories, but no appended row falls in them (session check, 2026-10-25).
- 6,002 appended rows (8.7%; 5.2% of appended `MM_OPP`) have NULL `FIRM` and `PARENT`: their `CBD_ID` has no row in
  the union.
- Appended `MM_OPP` against `firm_2`'s positive sales in the same cell, by `DIST_CH` x `NEW_DIST` x `CHANNEL`:

| `DIST_CH` | `NEW_DIST` | `CHANNEL` | rows | `CBD_ID`s | % of appended `MM_OPP` | % of `firm_2` sales |
|---|---|---|---|---|---|---|
| `D2_01` | `N2_01` | IFA | 33,673 | 281 | 49.59 | 58.77 |
| `D2_02` | `N2_03` | FI | 11,761 | 26 | 15.50 | 13.04 |
| `D2_03` | `N2_04` | WH | 3,956 | 6 | 7.92 | 3.36 |
| `D2_02` | `N2_02` | National | 4,256 | 1 | 7.56 | 17.28 |
| `D2_04` | `N2_01` | IFA | 6,617 | 6 | 6.94 | 0.43 |
| `D2_02` | `N2_05` | National | 2,773 | 1 | 4.09 | 2.41 |
| `D2_03` | `N2_05` | National | 1,153 | 1 | 2.41 | none |
| `D2_03` | `N2_01` | IFA | 1,875 | 8 | 1.88 | 2.40 |
| `D2_04` | `N2_04` | WH | 1,130 | 4 | 1.84 | 0.46 |
| `D2_01` | `N2_05` | National | 843 | 1 | 1.23 | none |
| `D2_02` | `N2_01` | IFA | 905 | 4 | 0.95 | 0.45 |
| `D2_01` | `N2_03` | FI | 71 | 1 | 0.06 | 0.02 |
| `D2_01` | `N2_04` | WH | 32 | 1 | 0.02 | 0.01 |
| `D2_03` | `N2_06` | National | none | none | none | 1.13 |
| `D2_03` | `N2_03` | FI | none | none | none | 0.10 |
| `D2_02` | `N2_04` | WH | none | none | none | 0.08 |
| `D2_02` | `N2_06` | National | none | none | none | 0.04 |
| `D2_01` | `N2_02` | National | none | none | none | 0.01 |

  (Two more `D2_03` / `D2_01` National cells and four cells with NULL `DIST_CH` have no appended rows and 0.00 or
  no sales.) The default rule puts `D2_04` rows into IFA, 6.94% of appended `MM_OPP` against 0.43% of `firm_2` sales; the National cells
  `N2_05` under `D2_03` and `D2_01` come from the 'company' rule, not the default.

### 2026-10-25: `24_union_opp.sql` rebuilt in `firm_1`'s layout

> **Owner, 2026-10-25:** "no it needs to match the layout of firm 1's data. there needs to be a join so that mm_opp
> and sales exists for firm two on the same rows so we can do analytics ar the wholesaler level"

The first `24` appended every `firm_2` opportunity key as its own row (entry above), so `firm_2` `MM_OPP` and sales
never shared a row. `firm_1` does (session check on the extract). Key = `ZIP_CODE` x `DIST_CH` x `CHANNEL` x
`PRODUCT_V2` x `CBD_ID`; `MM_OPP` sits on one row per key:

| `firm_1` rows | rows | % `MM_OPP` | % sales |
|---|---|---|---|
| `MM_OPP` + sales, seller = holder (`SALES_WHOLESALER_TERRITORY_ID` = `TERRITORY_WHOLESALER_TERRITORY_ID`) | 4,546 | 15.1 | 62.3 |
| `MM_OPP` + sales, seller not holder | 23 | 0.2 | 0.6 |
| `MM_OPP` only (holder IDs on it) | 74,303 | 84.8 | |
| sales only, seller = holder | 3,597 | | 22.8 |
| sales only, seller not holder | 1,752 | | 14.3 |

4,510 keys have `MM_OPP` on a sales row (4,493 of those rows seller = holder); 993 have `MM_OPP` on its own row and
sales on other rows. Other sellers' sales are always separate rows without `MM_OPP`.

**New rule.** `UNION_OPP` = `firm_1` union rows unchanged + `firm_2` union rows (every column unchanged except
`MM_OPP`) + opp-only rows.
- `firm_2` opportunity key = `ZIP_CODE` x `DIST_CH` x `CBD_ID` x `PRODUCT_V2` (the file after the drops, `CBD_ID` from
  `CRD_MATCH`, summed; zero sums left out, as before). `CHANNEL` is not in the join: a key that joins takes the
  `CHANNEL` of the sales row it lands on.
- A key goes on exactly one `firm_2` union row with that key whose seller is the holder: the one with the largest
  `ACTUAL_SALES_AMOUNT` (ties on the remaining columns). No such row: an opp-only row, built as before (holder from
  territories, `CHANNEL_RULE` as before). A `firm_2` union row that gets no key keeps its NULL `MM_OPP` (it is NULL on
  all 13,140 source rows).
- Lineage: `OPP_FILE` is replaced by `ROW_ORIGIN` (`union`, `union + opp file`, `opp file`); `CHANNEL_RULE` is
  `sales row` on `union + opp file` rows. Statement 2 compares every column except `MM_OPP` with `EXCEPT` both
  ways plus a row count (Snowflake has no `EXCEPT ALL`), checks `firm_1` unchanged, the sales cells, and one `MM_OPP` row per key.

Run on the coded extract (identity key, divisor 1, `23` then `24`): all `MUST_BE_ZERO` rows 0. Row counts against the
first build: opp-only rows 64,197 (was 69,045 appended) + 4,848 `firm_2` sales rows now carrying `MM_OPP` = 69,045
keys. `firm_2` `MM_OPP` is 56,993.5 coded units, equal to the file after drops: 18.2% on sales rows, 81.8% on
opp-only rows. `firm_2` sales on rows that carry `MM_OPP`: 49.4% (`firm_1`: 62.9%).

`firm_2` in `UNION_OPP`, the five `firm_1` row classes (sales = `ACTUAL_SALES_AMOUNT` not NULL):

| `firm_2` rows | rows | % `MM_OPP` | % sales |
|---|---|---|---|
| `MM_OPP` + sales, seller = holder | 4,834 | 18.2 | 49.4 |
| `MM_OPP` + sales, seller not holder | 0 | | |
| `MM_OPP` only | 64,211 | 81.8 | |
| sales only, seller = holder | 6,640 | | 39.2 |
| sales only, seller not holder | 1,368 | | 11.4 |

(The same query on `firm_1` reproduces the table above. The 14 rows between 4,848 and 4,834 are picked rows with NULL
`ACTUAL_SALES_AMOUNT`: they are `union + opp file` but count as `MM_OPP` only here. 284 `firm_2` rows have neither.)

Statement 3, `firm_2` file `MM_OPP` by `DIST_CH` x `NEW_DIST` x `CHANNEL`, next to positive sales (rows on sales rows
/ opp-only rows):

| `DIST_CH` | `NEW_DIST` | `CHANNEL` | rows on sales rows | rows opp-only | `CBD_ID`s | % of `MM_OPP` | % of `firm_2` sales |
|---|---|---|---|---|---|---|---|
| `D2_01` | `N2_01` | IFA | 2,665 | 31,008 | 281 | 49.59 | 58.77 |
| `D2_02` | `N2_03` | FI | 768 | 10,993 | 26 | 15.50 | 13.04 |
| `D2_03` | `N2_04` | WH | 124 | 3,832 | 6 | 7.92 | 3.36 |
| `D2_02` | `N2_02` | National | 817 | 3,439 | 1 | 7.56 | 17.28 |
| `D2_04` | `N2_01` | IFA | 11 | 6,606 | 6 | 6.94 | 0.43 |
| `D2_02` | `N2_05` | National | 214 | 2,559 | 1 | 4.09 | 2.41 |
| `D2_03` | `N2_05` | National | 0 | 1,153 | 1 | 2.41 | none |
| `D2_03` | `N2_01` | IFA | 202 | 1,673 | 8 | 1.88 | 2.40 |
| `D2_04` | `N2_04` | WH | 39 | 1,091 | 4 | 1.84 | 0.46 |
| `D2_01` | `N2_05` | National | 0 | 843 | 1 | 1.23 | none |
| `D2_02` | `N2_01` | IFA | 8 | 897 | 4 | 0.95 | 0.45 |
| `D2_01` | `N2_03` | FI | 0 | 71 | 1 | 0.06 | 0.02 |
| `D2_01` | `N2_04` | WH | 0 | 32 | 1 | 0.02 | 0.01 |

The cell shares are the same as in the first build (the join moves `MM_OPP` between rows, not between cells, except
that a key on a sales row takes that row's `NEW_DIST` / `CHANNEL`); the cells with sales and no `MM_OPP` are unchanged
(`D2_03` `N2_06` 1.13, `D2_03` `N2_03` 0.10, `D2_02` `N2_04` 0.08, `D2_02` `N2_06` 0.04, `D2_01` `N2_02` 0.01, two
more at 0.00). Q21 stays open: the `DIST_CH` default still applies to opp-only rows.

Why `firm_2` sales sit on fewer `MM_OPP` rows (session check, 2026-10-25). Sales on rows without `MM_OPP`:

| reason | % of `firm_2` sales | % of `firm_1` sales |
|---|---|---|
| the key's `MM_OPP` is on another row (a second holder row, or seller not holder): the layout | 27.2 | 20.0 |
| product `PR05`, no opportunity product (Q8) | 7.6 | |
| company with no kept file opportunity under `CRD_MATCH` | 8.7 | 17.1 (key without `MM_OPP`) |
| company x ZIP in the file under another `DIST_CH` only | 2.5 | |
| company in the file, not in this ZIP | 2.2 | |
| key in the file, sums to 0 | 1.7 | |
| no `CBD_ID` on the sales row | 0.6 | |

So sales on a key that has `MM_OPP` somewhere: `firm_2` 76.6%, `firm_1` 82.9%. About 4.2 points of the 8.7 are one CRD on
the review list: `opp_matched` splits it over `C00130` (55 ZIPs) and `C00312` (1,313 ZIPs, 2.8% of the kept file
`OPP`), `crd_cbd` says `C00130`, equality is weak (0.2); `CRD_MATCH` takes `opp_matched`'s `C00312` (METHOD 'review'),
which has no union rows, while `firm_2` sells 4.17% of its sales at `C00130` (FI). Owner to decide (Q20).

### 2026-10-25: firm_2 opportunity too high at work; `CBD_ID` '0'; CRD as the key

> **Owner, 2026-10-25:** "using query # 24, we must be duplicating rows as the aggregate opportunity amount by firm is
> almost $100B more than expected" ... "firm 2's opportunity amount is too high" ... "so some of the cbd_id is mapped
> to '0' which I believe is off. I think the path forward is to instead use the crd_id as main key. but I will have to
> get you the crd_id list as an additional extract"

On the coded extract `24` adds nothing: `opp_original` 306,530 rows / 90,431.3 coded units; `OPP_MAPPED` kept rows
234,760 / 56,993.5; `UNION_OPP` `firm_2` `MM_OPP` 69,045 rows / 56,993.5. `explore/opp_totals_check.sql` prints the same
at work.

- Repeated file rows are parts, not copies. Exact duplicate rows hold 3.5 coded units. In the 9,590 `CBD_ID` x ZIP x
  product cells where `firm_2` has 2+ nonzero rows, `firm_1`'s `MM_OPP` equals their sum in 4,164 and their largest in
  511. Taking the largest per CRD x ZIP x `DIST_CH` x product would cut `firm_2` to 53,024.9 (-7%), against the evidence.
- `CBD_ID` '0' is a placeholder, most likely `C00409`: 54 CRDs in `opp_matched`, no union rows. `23` takes it as a
  match ('opp_matched only'): 16 CRDs, 0.12% of the kept `OPP`. A placeholder must count as no match.
- Owner's direction: CRD becomes the main key; a CRD list comes as a new extract.

### 2026-10-25: the extra firm_2 opportunity is already in the union at work

`explore/opp_totals_check.sql` statement 1, run at work by the owner (coded units):

| line | rows | coded units |
|---|---|---|
| A. source union, `firm_2` rows with `MM_OPP` | 70,532 | 56,913.6 |
| B. source union, all rows | 152,246 | |
| C. `opp_original` = `OPP_MAPPED` rows | 306,530 | 90,431.3 |
| D. file after the drops | 234,760 | 56,993.5 |
| E. `UNION_OPP` `firm_2` `MM_OPP`, `ROW_ORIGIN` union | 65,688 | 47,069.7 |
| F. ... union + opp file | 4,844 | 10,374.2 |
| G. ... opp file | 64,201 | 46,619.2 |
| H. key codes used twice | 0 | |

- The union at work is no longer the one exported on 2026-10-20 (97,361 rows, no `firm_2` `MM_OPP`): it has 152,246 rows
  and already carries `firm_2` opportunity of 56,913.6 coded units, 0.14% from the file after the drops. An earlier
  load of the same file, most likely the owner's first attempt (`opp_matched`, the source of `CBD_ID` '0').
- `24` kept that opportunity on 65,688 rows (E) and replaced it on the 4,844 rows where it put the file's (9,843.9 of
  A), so `firm_2` totals 104,063.1, the file counted about 1.8 times. E is the excess (the owner's "almost $100B").
  C = C and H = 0: the mapping itself duplicates nothing.
- The coded extract here predates that load; work beyond `24` needs a fresh export of the union.

Asked what `UNION_OPP` should be built on, the owner chose a union without the earlier load:

> **Answer (owner, 2026-10-25):** "ok yes new table without firm 2 opp is call union_base"

`23` and `24` now read `ssdb_integration.lr_strategy.union_base` (Settled); `explore/opp_totals_check.sql` line A must
be 0 there. Rerun on the extract with `union_base` as a view over the 2026-10-20 union: every check 0, same numbers.

### 2026-10-25: firm_2 rows with no `FIRM` / `PARENT` in `UNION_OPP`

Owner asked why some `firm_2` rows have no `FIRM` / `PARENT`. Only opp-only rows: `24` copies `FIRM` and `PARENT` from
`union_base` rows of the same `CBD_ID`, and 22 `CBD_ID`s of the opportunity file have no row there (neither firm sells
there, `firm_1` has no `MM_OPP` there). On the extract: 6,022 rows, 5.25% of `firm_2` `MM_OPP`. `C00410` holds 3.91% and
`C00447` 0.97%, one CRD each, both tables agree; `C00409` (most likely '0') 0.12% over 16 CRDs; 19 others 0.25%.
`explore/null_firm.sql` lists them with their CRDs and broker names at work.

> **Owner, 2026-10-25:** "crd_to_cbd has firm name in it" ... "in crd_to_cbd it;s called "firm". and leave parent blank"

Done in `23` and `24` (Settled). Rerun on the extract, with '0' put back in place of `C00409` in `opp_matched` and a
`FIRM` column added to `crd_cbd` (harness only): every check 0, totals unchanged. `firm_2` rows with no `FIRM` fall from
5.25% to 0.23% of `firm_2` `MM_OPP`: 16 CRDs of '0' now 'no company' with a blank `CBD_ID` (0.12%), and 16 companies
only `opp_matched` names, absent from `crd_cbd` (0.11%). No row has `CBD_ID` '0'. `24`'s grid reports, for companies in
both `union_base` and `crd_cbd`, the percent whose two firm names are equal (at work: whether the filled names follow
the union's spelling).

### 2026-10-25: how `firm_1`'s half of the union is built (owner's query, kept out of the repo)

The owner shared the query that builds `firm_1`'s rows with `CBD_ID` and `MM_OPP` (hub root, git-excluded: it holds
internal table and firm names). Read in full by the session; what it settles, in neutral terms:

- `firm_1`'s opportunity is a vendor opportunity table with the same columns as `firm_2`'s file (`DIST_CH`, ZIP,
  `FIRM_CRD`, broker name, product line, VA product type, amount), plus the vendor's own `CBD_ID` for `firm_1`. One
  source for both firms explains the exact equality of 2026-10-24 (Q23) and gives a CRD-to-`CBD_ID` crosswalk from the
  vendor's rows instead of matching (Q20).
- `CBD_ID` '0' is a vendor row the vendor could not tie to a `firm_1` broker-dealer. The query uses a list of candidate
  IDs when there is one ('|'-separated, resolved against `firm_1` sales, else the first), and otherwise drops the row:
  `firm_1`'s `MM_OPP` holds no '0' opportunity. So `firm_2`'s opportunity at CRDs with no `CBD_ID` should be left out the
  same way (the owner's expected totals already do).
- Sales and opportunity cover fiscal years 2024 and 2025, one row per year. The coded extract has no `FISCAL_YR`, so
  every total in this log sums both years for `firm_1`; `firm_2`'s file has no fiscal year (Q7).
- `MM_OPP` goes on the sales row whose wholesaler is the vendor's territory for that row, else on its own row: the
  layout of 2026-10-25 that `24` copies.
- Possible duplication, for the owner to check: the opportunity join hits every sales row of a key (two name spellings
  for one company double it: the 50 keys with `MM_OPP` twice, 2026-10-20); the current-territory join doubles rows where
  a ZIP has two wholesalers in a channel; the firm-master join doubles rows where a `CBD_ID` has two active entries.
- The '|' resolution compares an unpadded ZIP to sales ZIPs, so for ZIPs with a leading zero it never sees sales and
  takes the first candidate.
- The session wrote a copy that carries `FIRM_CRD` through the opportunity side and attaches it by `CBD_ID` at the end
  (no row added or split), plus the vendor crosswalk CRD x broker name -> `CBD_ID` (hub root, git-excluded).

### 2026-10-25: Snowflake constructs checked against the docs; fiscal year 2025

> **Owner, 2026-10-25:** "snowflake does include count(distinct...). either way you should be searching the web or
> asking me instead of assuming those kinds of things. tokens or costs is not a factor here, quality is the end goal"

The session had rewritten a check in its copy of the owner's query on the assumption that `COUNT(DISTINCT ...) OVER` is
not supported. The docs (COUNT) allow it; only a multi-column distinct with `ORDER BY` in the window is invalid. Rule
added to Conventions. Every construct in the files not yet run at work, checked (docs read 2026-10-25):

| construct | used in | evidence | result |
|---|---|---|---|
| `REGEXP_REPLACE` default occurrence | `21` | docs: default 0, all occurrences | as written |
| `SPLIT_PART` part 1 | `21` | docs: 1-based | as written |
| `JAROWINKLER_SIMILARITY` | `21` | docs: integer 0-100, case-insensitive | as written |
| `LTRIM(x, '0')`, `COUNT_IF`, `TRUNC`, `LISTAGG(DISTINCT ...)`, `GREATEST` | `22`, explore | docs | as written (GREATEST is NULL if an input is; inputs are COALESCEd) |
| `UNION ALL BY NAME` with unequal column lists | `24` | docs: a missing column is NULL; owner's run | as written |
| `MINUS` / `EXCEPT` and NULLs, duplicates | `22` statement 7, `24` statement 2 | docs say neither | replaced: `24` compares row multisets by `HASH(* EXCLUDE ...)` (docs: never NULL, NULL inputs included; NUMBER hashes alike across precision and scale); `22` uses `NOT EXISTS` with `IS NOT DISTINCT FROM` (docs: NULL-safe) |
| `GROUP BY` with NULL keys | `24` statement 2 | docs (aggregate functions and NULL): NULL rows kept as a group | as written |
| window ordered by `SUM()` in a grouped query | session's copy of the owner's query | docs: windows run after `GROUP BY`, but no example orders by an aggregate | moved the sum into a subquery |
| everything in `22` statements 1-6, `23` statements 1-2, `24` statement 1, `explore/opp_totals_check.sql` statement 1 | | owner's runs at work | confirmed |

`24` statement 2 also gains a check that `union_base` holds no `firm_2` `MM_OPP`. Tested on the coded extract: all checks
0; four faults put in by hand are each caught (a repeated union row, a changed `firm_1` `MM_OPP`, a NULL column given
a value, `firm_2` `MM_OPP` left in `union_base`); in `22`, a changed old key row with NULL `SOURCE` is caught and the
NULL-`SOURCE` rows are not miscounted as new.

Truncation (pending `explore/amount_precision.sql`): by the docs (arithmetic operators) addition keeps the larger
scale and division adds 6 digits up to 12 and rounds; `COALESCE` turns a text argument into NUMBER(18,5). No step of
`23` or `24` can drop the decimals of an amount unless a source column has scale 0, which statement 1 of that file shows.

> **Owner, 2026-10-25:** "all fiscal years is 2025 only. I have no clue where firm 2's cbd_id comes from."

Correction to the entry "how `firm_1`'s half of the union is built": its line "every total in this log sums both years
for `firm_1`" is wrong; all data is fiscal year 2025. Q7 keeps only its ZIP part. Q24 is new: 370 of the 388 `firm_2`
`CBD_ID`s are `firm_1`'s IDs (2026-10-24); the vendor crosswalk from the owner's query keys `firm_2`'s file by CRD
without depending on them. Q25 is new: the `opp_matched` files arrived with a `VA_PRODUCT_TYPE` column where `22`
writes `VA_PRODUCT_LINE`, every other column in `22`'s order; `22` is unchanged until the owner confirms.

### 2026-10-25: `crd_cbd_mm` built at work; `22` statements 12-15 code it

> **Owner, 2026-10-25:** "the output is 404, 382, 393, 13, null"

The check query at the end of the session's copy of the owner's query (kept out of the repo), fiscal year 2025:

| | value |
|---|---|
| rows (CRD x broker name x `CBD_ID`) | 404 |
| CRDs | 382 |
| `CBD_ID`s | 393 |
| CRDs with 2+ `CBD_ID`s | 13 |
| share of `MM_OPP` with no CRD | NULL, read as 0: `SUM` of no non-NULL values is NULL (docs, SUM, read 2026-10-25), so no row has a NULL CRD |

The query drops vendor rows whose ID is '0' with no client firm ID before this table, so opportunity the vendor gives
no company is not in it. `firm_2`'s kept rows (no `L01`, no `O2_05`) have 355 CRDs, 360 CRD x broker name; how many of
them, and how much of their `OPP`, the crosswalk covers is measured once `synthetic_crd_cbd_mm` is loaded (Q20).

`22` statements 12-15 are new: 12 inserts `crd_cbd_mm`'s `CBD_ID`s not yet in the key (insert-only, next C codes), 13
builds `synthetic_crd_cbd_mm` (`CBD_ID` coded, `MM_OPP` / the divisor, CRD and broker name clear), 14 checks it after a
rerun of 7, 15 is the one download. Every construct in them already ran at work in `22` statements 2, 3 and 7. Tested
on the extract with a stand-in `crd_cbd_mm` (real values made different from codes, two new `CBD_ID`s): the new codes
follow the largest, a second run of 12 adds nothing, every check is 0, a `CBD_ID` left out of the key is caught.

### 2026-10-25: can the owner's query give `firm_2`'s opportunity rows their `NEW_DIST`?

> **Owner, 2026-10-25:** "can we use the mm_query_crosswalk.sql to also get the correct new_dist channels while we're at it?"

What the owner's `firm_1` query sets: `new_dist` = the row's `dist_ch`, except five named `cbd_id`s broken out by a
`CASE`; `dist_ch` on opportunity rows = the vendor's, with overrides by `cbd_id` and broker name. It sets no `CHANNEL`
(a later step does). Its result is already in `union_base`'s `firm_1` rows, so the query needs no change for this.

On the coded extract (union, and `UNION_OPP` rebuilt from `23` and `24` statement 1):
- The four companies broken out into `National` are the same in both `SOURCE`s: `N1_04` = `N2_05` (`C00143`), `N1_05` =
  `N2_02` (`C00094`), `N1_06` = `N2_06` (`C00141`, `C00191`). Bears on Q6.
- Companies in both `SOURCE`s, main `CHANNEL` by rows: the same for 363 of 370; 7 differ (`firm_1` / `firm_2`: FI / IFA 3,
  WH / IFA 2, National / IFA 1, IFA / FI 1).
- `firm_2` file `MM_OPP` that `24` places by the `DIST_CH` default (9.6%, Q21), against `firm_1`'s main `CHANNEL` for
  the company: same `CHANNEL` 4.30%; different 0.06% (one company, `firm_1` IFA, default FI); no `firm_1` rows for the
  company 5.13% (21 companies); no company 0.12%.

So `firm_1`'s channel would change 0.06% of the file's `MM_OPP`. The 5.13% at companies with no `firm_1` rows is what
the default really decides; the CRD-keyed `23` (from `crd_cbd_mm`) may move those CRDs to other companies.

### 2026-10-25: firm_2's opportunity file through the opportunity steps of the owner's query

> **Owner, 2026-10-25:** "think about all the datasets and the transformations we're doing. lets map as much as we can as early on as we can so that firm 2's data matches firm 1's data as much as possible before ever touching union"

> **Owner, 2026-10-25:** "as long as we have dist_ch we can get to new_dist and then channel. lets work on getting dist_ch first. [...] lets run firm 2's opportunity file through the logic in that query and make sure everything matches up, then we can think about the rest."

The owner approved a `firm_2` copy of the query, kept out of the repo beside it (its rule lists hold firm names). It
runs both firms' rows through one copy of the query's first opportunity step, so both are judged by the same rules,
then takes `firm_2`'s rows through the remaining opportunity steps. `firm_2`'s file has no company, client firm ID or
state: it takes the ones `firm_1`'s vendor rows give at the same ZIP x CRD x broker name, else `crd_cbd_mm` by CRD x
broker name. Other changes, each marked in the file: RILA is a VA type in `firm_2`'s file but a product line in the
vendor table (settled map, `V02` -> `PR01`); `|` lists resolve against `firm_2`'s sales in `union_base`, without the
channel and territory conditions. `dist_ch` is per CRD in `firm_2`'s file (471 of 475 CRDs have one).

Checks that must be 0: rows and `OPP` of the file kept; `firm_1`'s vendor rows kept; no product left without a branch;
products as the settled map; `OPP` kept through to the last step. For reading: where each company came from, the share
dropped for no company (as `firm_1`'s are), `|` lists, `dist_ch` changed by the rules, `dist_ch` and `OPP` against
`firm_1` at the same key. A last query lists `firm_2`'s file `dist_ch`, the rules' result and `firm_1`'s side by side.

Tested in DuckDB on the extract, with a stand-in vendor table built from `opp_matched` (real-like labels, a `|` list,
'0' with and without a client firm ID, ZIPs missing): every must-be-zero check 0, and the broker-name overrides change
`firm_2` rows (1.01% of `OPP`). A product label no branch knows and a missing key row are each caught. `22` statements
12-15 are on hold: the copy reads `crd_cbd_mm` at work directly.

### 2026-10-25: first run of the `firm_2` copy at work; `dist_ch` taken from `firm_1`'s vendor rows

Owner's run of statement 3 (file `td/Untitled 14_2026-10-25-2051.csv`), `firm_2`'s file through the query's steps:

| check | value |
|---|---|
| every must-be-zero row (rows and `OPP` kept, `firm_1` rows kept, products, last step) | 0 |
| % of `OPP` with a company from `firm_1`'s vendor rows at the same ZIP x CRD x broker name | 99.87 |
| % from `crd_cbd_mm` (no vendor row there) | 0.13 |
| % with no company, dropped as `firm_1`'s are | 1.04 |
| % at a ZIP x CRD x broker name where `firm_1`'s rows name 2+ companies | 52.26 |
| % with a `\|` list of companies | 5.76 |
| % whose `dist_ch` the query's rules changed | 3.59 |
| % with the same `dist_ch` as `firm_1` at the same ZIP x CRD x broker name | 3.58 |
| % in cells (ZIP x CRD x broker name x product) whose `OPP` equals `firm_1`'s within 1 | 6.89 |

- Products: the query's `CASE` on `firm_2`'s file gives the settled map exactly, so the labels are `PR01` RILA, `PR02`
  VARIABLE, `PR03` INDEX, `PR04` IOVA (the query's own output labels; the earlier hypothesis holds).
- `dist_ch`: `firm_2`'s file names its channels differently from the vendor table. Only the rows the rules rewrite
  (3.59%) end on `firm_1`'s names (3.58%), so `firm_2`'s own label cannot go through the rules.
- The 52.26% says one ZIP x CRD x broker name is not one company in `firm_1`'s rows.

Changed (local copy, statement 1): each `firm_2` row now takes company, client firm ID and `dist_ch` from `firm_1`'s
vendor rows of the same ZIP x CRD x broker name x product (the query's product `CASE`, once more, as the key), else of
the same ZIP x CRD x broker name, else the company only from `crd_cbd_mm` with no `dist_ch`. Then the query's rules run
on it as on a `firm_1` row. `firm_2`'s own label is kept beside it, for the current state. Statement 4 now lists
`firm_2`'s label, `firm_1`'s and the rules' result. Tested on a stand-in built from `firm_2`'s rows (`firm_1`'s own
channel names, a company that changes by product, cells and ZIPs missing): must-be-zero rows 0; 80.4% / 3.6% / 15.9%
by the three sources as built; the product key brings the 2+ companies share to 1.2%.
