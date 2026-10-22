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
- `Pxxxxx`: `FIRM` and `PARENT` (one numbering).
- `W` person IDs, `M` names, `A` address IDs.

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
  `CBD_ID` joins the firms; superseded for a `CBD_ID` the firm never sells to by Q9 (below).
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
  into territories (owner, 2026-10-21, Q9).
- Territories rows whose `CHANNEL` is not a `DIST_CH` in the union for that `SOURCE` are out of scope (`D1_04`-`D1_07`)
  (owner, 2026-10-21; Q4 stays open).
- Names are matched within `SOURCE` by the `ZIP_CODE` x `DIST_CH` a name covers, not by edit distance
  (`21_name_match.sql`, owner, 2026-10-21).

## Open questions

| Q | question | log entry |
|---|---|---|
| Q2 | What does `MM_OPP` measure: whole market or what `firm_1` can address? | 2026-10-20 |
| Q4 | What are `D1_04`-`D1_07`; rank their 34 people? | 2026-10-20 |
| Q6 | Do real `NEW_DIST` values match across `SOURCE`s? | 2026-10-20 |
| Q7 | Same period and same ZIP basis for `MM_OPP` and sales? | 2026-10-20 |
| Q8 | What is `PR05`; leave it out of market share? | 2026-10-20 |
| Q10 | Is the `firm_2` TX/NY block with no `CLEAN_ID` W00155/W00171's territory? (check territories `NAME` at work; folds in Q5) | 2026-10-21 |
| Q12 | `firm_2` `PR05`: contribution only? | 2026-10-21 |
| Q13 | Compare National, WH, FI per distribution company rather than per ZIP? | 2026-10-21 |
| Q14 | Is there a record of selling agreements per distribution company? | 2026-10-21 |
| Q16 | `N1_06` has `D1_01` (IFA) rows: a firm-level override, IFA business of those companies counted as National? | 2026-10-21 |
| Q17 | Sellers with no territory (2.8% of `firm_2` sales): whose numbers? | 2026-10-21 |
| Q18 | Which union name column and which territories name column to match? | 2026-10-21 |

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
