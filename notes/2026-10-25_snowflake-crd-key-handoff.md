2026-10-25 · m5-studio/snowflake-safe-dataset · 0c0c490 · Agent: session (claude-opus-5-5)

# Handoff: firm_2 opportunity on firm_1's layout (`24`), CRD becomes the key, owner runs four things at work

Supersedes `notes/2026-10-25_snowflake-firm2-opp-handoff.md` (c42b5de). Work is in `~/.pi/worktrees/td-snowflake`, all
under `tools/snowflake/`; the owner runs SQL at work, every file is tested first in DuckDB on the coded extract. Goal:
each wholesaler's numbers in the current state (`DIST_CH`) and new state (`CHANNEL`), then the three rankings.

## Tasks

- Done: `24` rebuilt in `firm_1`'s layout: file `MM_OPP` on the `firm_2` holder's sales row, else an opp-only row; `ROW_ORIGIN` lineage.
- Done: found the owner's excess firm_2 opportunity (an earlier load already in the work union); `23`/`24` now read `union_base`.
- Done: `CBD_ID` '0' = no company; `FIRM` filled from `crd_cbd`'s `firm`, `PARENT` blank.
- Done: docs audit of every Snowflake construct not yet run at work; `EXCEPT` checks replaced (HASH multisets in `24`, NULL-safe `NOT EXISTS` in `22`); four injected faults each caught.
- Done: read the owner's `firm_1` union query; wrote copies that carry `FIRM_CRD` and build the vendor crosswalk `crd_cbd_mm` (hub root, git-excluded).
- Partial: truncation of amounts in `UNION_OPP`: diagnostic written (`explore/amount_precision.sql`), owner has not run it.
- Not started: coded export of `crd_cbd_mm`; `23` keyed on CRD; `CELL` rebuild on `UNION_OPP`; `31_cell_person.sql`; `40_person_rank.sql`.
- Dropped by owner: using the personal Snowflake account to replicate work.

## Critical references

- `tools/snowflake/DATASET_LOG.md`: Conventions `:18` (Snowflake rule `:56`), Settled `:82`, Open questions `:138`, the 2026-10-25 entries from `:841`.
- `tools/snowflake/24_union_opp.sql:24` (table), `:136` (checks); `tools/snowflake/23_crd_match.sql:47`.
- Hub root `/Users/Shared/sv-ntlee/td/`: `mm_query.sql` (owner's), `mm_query_crd.sql`, `mm_query_crosswalk.sql` (session copies, CRLF kept), `opp_original` / `om0-4` / `synthetic_crd_to_cbd` files; all git-excluded, never commit.

## Changes

- `tools/snowflake/23_crd_match.sql:113`: METHOD 'no company' for CRDs whose tables give only '0'; reads `union_base`.
- `tools/snowflake/24_union_opp.sql:64`: `cn`, `FIRM` from `crd_cbd` where `union_base` has none.
- `tools/snowflake/24_union_opp.sql:82`: `PICK`, one holder sales row per opportunity key.
- `tools/snowflake/24_union_opp.sql:160`: row identity by `HASH(* EXCLUDE ...)` counts, no `EXCEPT`.
- `tools/snowflake/22_code_opp_firm2.sql:148`: new key rows by `NOT EXISTS` + `IS NOT DISTINCT FROM`.
- `tools/snowflake/explore/`: `crd_split_c00130.sql`, `opp_totals_check.sql`, `null_firm.sql`, `amount_precision.sql`.
- `tools/snowflake/DATASET_LOG.md:56`: Snowflake rule (docs or owner, never assumed).

## Learnings

- Owner rule (2026-10-25): settle Snowflake behaviour from the docs (cite page and date) or ask; quality over cost. The docs say nothing on how `MINUS`/`EXCEPT` treat NULLs or duplicates; `HASH` never returns NULL. Docs show CTAS only as `AS SELECT`; the crosswalk file uses the owner's own `AS ( ... )` form.
- All data is fiscal year 2025. The 2026-10-20 export factor was 1,000 (extract rescaled; old copy `ssdb.pre-factor-1000.duckdb`).
- Both firms' opportunity is the same vendor table, so equality is exact on most cells and the vendor's `FIRM_CRD` -> `cbd_id` is the real crosswalk.
- At work `opp_original` and `crd_cbd` are views over the owner's real tables; the real names stay out of the repo. The union at work (152,246 rows) differs from the extract (97,361).
- Corrections to the 2026-10-21 note still apply: the worker agent was not broken; "39% of firm_1 sales" counted any row (5.8% with positive sales).
- Follow-up, not ours: ponytail/caveman prompt blocks do not reach Claude through claude-bridge.

## Next steps

1. Owner runs `td/mm_query_crosswalk.sql` and sends its final check (rows, CRDs, `cbd_id`s, CRDs with 2+ `cbd_id`, share of opportunity with no CRD).
2. Write the coded export of `crd_cbd_mm` the way `22` works (key insert-only, CRD and broker name clear); load it; rebuild `23` to key `firm_2`'s file on CRD, equality and the owner's two tables as cross-checks; rerun `24`.
3. Owner runs `explore/amount_precision.sql`; fix the truncation where its counts drop to 0.
4. Owner reruns `23`, `24` and `explore/opp_totals_check.sql` statement 1 on `union_base`: line A 0, F + G = D, line B = `union_base` rows.
5. Rebuild `30_cell.sql` on `UNION_OPP` (market = larger firm per ZIP x `CBD_ID` x product), then `31` and `40`.

## Open owner decisions

- Q25: does `opp_matched` name its VA column `VA_PRODUCT_TYPE` (export header) or `VA_PRODUCT_LINE` (`22`)?
- Q21: default `CHANNEL` of `D2_04` for companies with no `firm_2` rows: IFA (proposed) or WH.
- Q8 / Q12: is `firm_2`'s `PR05` the product `firm_1` calls `PR02`?
- Q20: the split CRD, `C00130` (recommended; `firm_2` sells 4.2% there) or `C00312` (no union rows); lookup in `explore/crd_split_c00130.sql`.
- Q24: origin of `firm_2`'s union `CBD_ID`s (owner: unknown; CRD route does not need it). Others: see the index.
