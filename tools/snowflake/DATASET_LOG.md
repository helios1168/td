# The union and territories tables: what we know, what we asked

A running record of how `data_withnewchannel_union_w_joinkeys` (the union table) and `territories`
are built and how they relate, from exploring the coded extract. Append a dated entry; never rewrite an
old one. When the owner answers a question, add the answer under it (with the date) and copy the
resulting rule to "Settled".

Values are the codes from `20_synthetic_tables.sql`: `firm_1` / `firm_2` (`SOURCE`), `D1_01..` /
`D2_01..` (`DIST_CH` and `territories.CHANNEL`), `N1_01..` (`NEW_DIST`), `PR01..` (`PRODUCT_V2`).
Amounts appear only as percentages. No names, IDs or dollar amounts go in this file.

## Settled

Decisions made before this log, still in force (from the session record):

- `SOURCE` is the firm key; `firm_1` carries `MM_OPP`, `firm_2` carries none.
- Original channel = `DIST_CH` (= `territories.CHANNEL`); target channel = union `CHANNEL`.
- `SALES_WHOLESALER_TERRITORY_ID` joins `territories.CLEAN_ID`. Sales = `ACTUAL_SALES_AMOUNT`.
- A `SOURCE`'s product set is the `PRODUCT_V2` values where it has positive sales.
- `firm_2` opportunity: the carrier's `MM_OPP` per (`ZIP_CODE`, `CHANNEL`), own products, split over its
  held `DIST_CH` by national sales mix (`sales_mix_held`, chosen with `17`).
- A ZIP absent from the union table has zero opportunity; territories `DIST_CH` values absent from the
  union table are out of scope (owner, 2026-10-19).
- Distribution company (`FIRM`, `CBD_ID`) was dropped as a cross-firm key (`12` rejected). **Reopened
  by Q1 below.**

## 2026-10-20: first look at the coded extract

Source: `data/safe/extract_2026-10-20/` (gitignored), loaded as `ssdb.duckdb` under the real table
names. Union: 97,361 rows, 18 of 23 columns (no `FISCAL_YR`, `TERR_WHOLESALER`, `SALES_WHOLESALER`,
`SALES_AMOUNT`, address IDs). Territories: 448,617 rows, 5 of 7 columns (no `NAME`, `CLEAN_NAME`).
Amounts loaded as the exported integers / 10,000 (assumed factor). `15`'s checks all pass; its
out-of-scope count (154,442) equals the count from the real run at work, so territories is complete.

### Findings

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

### Questions for the owner

Q1. **Can the distribution company join the two firms after all?** We dropped `FIRM`/`CBD_ID` as a
cross-firm key. In this extract `CBD_ID` matches across `SOURCE`s (370 shared, same `FIRM` and
`CHANNEL`), and 88.8% of `firm_2`'s own-product sales sit in a (`ZIP_CODE`, `CBD_ID`) that has carrier
`MM_OPP`. Is `CBD_ID` the same distribution company in both firms' data (the table's "join keys")? If
yes, `firm_2` opportunity can be taken per (`ZIP_CODE`, `CBD_ID`) instead of estimated per
(`ZIP_CODE`, `CHANNEL`) with a sales-mix split.

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

## 2026-10-21: what `CBD_ID` would change in the `firm_2` opportunity

Compared, per `firm_2` person, the current rule (A, as in `15`) with a `CBD_ID` rule (B): `MM_OPP` in
`firm_2`'s products per (`ZIP_CODE`, `CBD_ID`), given to the `DIST_CH` that `firm_2` sells that
distribution company through in that ZIP; where it does not sell it there, by that distribution
company's national `DIST_CH` mix; where it never sells it, by the `CHANNEL` mix (as A). Query:
`explore/cbd_vs_channel.sql`. Assumes Q1 is "yes".

### Findings

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

### Questions for the owner

Q9. **Opportunity at distribution companies a firm has never sold to** (21% of `firm_2`'s): count it
in that firm's territories (spread by `CHANNEL` mix, as now), or only where the firm already does
business with that company?

Q10. **Vacant territory:** report its opportunity and sales as unassigned (a "vacant" row per ZIP), rather
than giving it to another holder in the same ZIP?
