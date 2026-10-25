2026-10-25 · m5-studio/snowflake-safe-dataset · ff07324 · Agent: session (claude-opus-5-5)

# Handoff: firm_2's own opportunity file mapped and appended (`22`-`24`); rankings next

Work lives in `~/.pi/worktrees/td-snowflake`, all under `tools/snowflake/`. Owner runs SQL at work in Snowflake;
everything is tested first in DuckDB on the coded extract. Purpose (owner, quoted in `DATASET_LOG.md`): design the
combined territory for the firm_1 + firm_2 merger; for now show each person's numbers in the current state
(`DIST_CH`) and the new state (`CHANNEL`), without assigning anyone.

## Tasks

- Done: `21_name_match.sql`, union-to-territories name crosswalk by ZIP x `DIST_CH` overlap (owner to run at work, Q18).
- Done: `22_code_opp_firm2.sql`, codes firm_2's opportunity files with the existing key, insert-only, exports in parts under 800 KB. Owner ran it; files received.
- Done: product map (Q22), `DIST_CH` map (Q19), fixed annuity and `O2_05` dropped, amount factor 1,000 (extract rescaled).
- Done: `23_crd_match.sql` (`OPP_MAPPED`, `CRD_MATCH`) and `24_union_opp.sql` (`UNION_OPP`), tested, all MUST_BE_ZERO 0; not yet run at work.
- Not started: rebuild `30_cell.sql` on `UNION_OPP` with market = larger of the two firms' opportunity; `31_cell_person.sql`; `40_person_rank.sql`.

## Critical references

- `tools/snowflake/DATASET_LOG.md`: Settled `:78`, Open questions `:127`, entries of 2026-10-24/25 from `:622`. Read first.
- `tools/snowflake/24_union_opp.sql:16`: the combined table; `23_crd_match.sql:46` the CRD crosswalk.
- `/Users/Shared/sv-ntlee/td/data/safe/extract_2026-10-20/ssdb.duckdb`: coded extract, now also `lr_strategy.opp_original`, `opp_matched`, `crd_cbd` (text columns but `OPP`, loaded as exported).

## Changes

- `tools/snowflake/21_name_match.sql:13`: `NAME_MATCH`, mutual best geography match, Jaro-Winkler as a check.
- `tools/snowflake/22_code_opp_firm2.sql:35`: new key rows (`O2_`, `L`, `V`, more `C`); `:143` checks; `:214` part export by `MOD(ABS(HASH(*)), N)` in a subquery.
- `tools/snowflake/23_crd_match.sql:13`: `OPP_MAPPED`, maps in codes translated through `synthetic_key`; `:46` `CRD_MATCH` rule equality >= 0.5, else tables agree, else one table, else review.
- `tools/snowflake/24_union_opp.sql:16`: `UNION_OPP` = union unchanged + 69,045 firm_2 rows, lineage columns `OPP_FILE`, `CBD_METHOD`, `CHANNEL_RULE`, `N_HOLDERS`.
- `tools/snowflake/DATASET_LOG.md`: owner answers of 2026-10-24/25 quoted; Q3, Q5, Q9 (moot-ish), Q19, Q22 closed.

## Learnings

- Corrections to the 2026-10-21 note: the `worker` agent is not broken (empty `extensions:` is normal; the 2026-10-18 crash was the runner vanishing, cause unknown). Amounts were exported x 1,000, not x 10,000. "39% of firm_1 sales" counted any row; positive-sales rows give 5.8%.
- Both firms' opportunity is one measure: per `CBD_ID` x ZIP x product, 70-85% of cells equal exactly (3 decimals). That equality is also the strongest CRD -> `CBD_ID` evidence and found the product map. 16 large companies (24% of compared opportunity, mostly IFA) match on about 30% of cells with firm_2 1.4-1.9x higher; part is a company split into several `CBD_ID`s on one side (`FIRM` level raises equality 72% -> 80%).
- Work SQL must never compare data to coded literals: maps are written in codes and translated through `synthetic_key` (CODE -> VALUE). DuckDB harness: build an identity key (VALUE = CODE, divisor 1); quote `"SOURCE"` in DuckDB DDL.
- Raw files from the owner land in the hub root (`synthetic_*`, `om0`-`om4`), git-excluded via the hub's `.git/info/exclude` (`/om[0-9]*` added this session). `BROKER_NAME` and `FIRM_CRD` are in clear by owner choice: never in the repo, log, notes or issues.
- Snowflake: `HASH(*)` only in a SELECT list; `UNION ALL BY NAME` allows unequal column lists; keep FULL JOIN conditions plain equality.
- The ponytail and caveman prompt blocks do not reach Claude through claude-bridge (prompt rebuilt from configured parts); follow-up for those packages.

## Next steps

1. Owner runs `23` then `24` at work; get both checks grids (and `22` statement 7: union `MM_OPP` total 55,404.3 coded units).
2. Owner confirms Q21 defaults (`D2_01` IFA, `D2_02` FI, `D2_03` WH, `D2_04` IFA; 9.6% of appended opportunity) and the Q20 rule; review `23` statement 4 (10 CRDs disagree, 6.1% of OPP; 3 review, 3.9%).
3. Rebuild `CELL` (`30`) on `UNION_OPP`: per-firm `MM_OPP`, market = GREATEST per `ZIP_CODE` x `CBD_ID` x `PRODUCT_V2`.
4. Write `31_cell_person.sql`, then `40_person_rank.sql` (current state by `DIST_CH`, new state by `CHANNEL`; three rankings).
5. Later: explain the 16 low-match companies (vintage? affiliates?); independent review of the branch; merge is the owner's call.

## Open owner decisions

- Q21: `NEW_DIST`/`CHANNEL` default for firm_2 opportunity rows whose company has no firm_2 rows (proposed above).
- Q20: CRD -> `CBD_ID` rule in `23` (equality first) and the review list.
- Q12, Q13: `PR05` contribution only; National, WH, FI per distribution company (recommended, unanswered).
- Q10, Q17, Q18: TX/NY block names; sellers with no territory; name columns for `21`.
- Q7 / Q23: same period for both opportunity files? Q8: what firm_2's `PR05` sales are (lead: the VA line without subtype).
- Q2, Q4, Q6, Q14, Q16: see the index.
