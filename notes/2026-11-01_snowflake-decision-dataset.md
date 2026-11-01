2026-11-01 · m5-studio/snowflake-v2 · 9e2a8ce · Agent: session (claude-opus-5-5)

# The decision dataset: one script, every sale mapped or decided

Supersedes `notes/2026-10-31_snowflake-sales-mga.md`. The owner runs one script, `tools/snowflake/01_opportunity_sales.sql`
(17 statements), and sends back one CSV. The last run's every check was 0 and its tie-out held; nothing since then
has run in Snowflake. Read `tools/snowflake/DATASET_LOG.md` Conventions, Settled and Key decisions first.

## Tasks

- Done: the MGA agent code reaches `TMP_O2_SALES` (the owner's `_temp` base sales table, confirmed clean by the owner;
  `00_base_sales.sql` is a fallback for someone with access). Q45 and Q33 settled, Q42 (`MM_AMOUNT` dropped), Q37 parked.
- Done: sales rules after the channel match: ZIP, MGA code, most opportunity at the ZIP (rule 4), both sources (no
  MGA rule for firm 2). Firm 1's marketing organizations: new channel IMO, out of the review list.
- Done: the review list (statements 15-16, layer REVIEW) and the owner's tables: route overrides (statement 1, by
  CRD x name or whole CRD), manual firm assignments and sales channels (statement 8). 53 manual rows; routes: Cetera
  Wealth FI, Cetera Investment Services (CRD 15340) FI; sales channels: Raymond James IFA/IMO, FI/IMO, five pure IMO.
- Done: the Copilot-in-Excel prompt (`EXCEL_PROMPT.md`); the owner built the workbook and decided from it.
- Partial: the last two edits (Cetera's last keys; CRD 15340) are not run yet. Not started: the second audit (owner:
  wait); a pivot export of `TMP_O2_DATASET`; a FIRM ROUTES part (offered, unanswered).

## Critical references

- `tools/snowflake/01_opportunity_sales.sql:442` `CREATE OR REPLACE TEMPORARY TABLE ssdb_integration.lr_strategy.tmp_sales_firm_override AS` (owner rows between `-- owner rows: begin` and `end`).
- `tools/snowflake/DATASET_LOG.md:168` Key decisions; `:211` the open index.
- `data/safe/opp_sales_2026-11-01-1357.csv` (hub, git-excluded): the last run, wholesaler names in its REVIEW rows.

## Changes

- `tools/snowflake/01_opportunity_sales.sql:133` route overrides; `:520` sales channels; `:559` statement 10 (rules).
- `tools/snowflake/01_opportunity_sales.sql:693` statement 12 (manual rows, new channel order); `:964` 15, review list.
- `tools/snowflake/01_opportunity_sales.sql:1090` statement 17, one result under LAYER (OPPORTUNITY, REVIEW, SALES).
- `tools/snowflake/sales_review_test.sh` (34 checks) replaces the unmapped tests; `02_sales_test.sh` 50 checks.
- `tools/snowflake/EXCEL_PROMPT.md`, `README.md`, `DATA_MODEL.md` (sales key, ν on sales); `$TD_REPO/owner_sql/vars.sql`.

## Learnings

- Snowflake counts an error's line from the start of the failing statement; map it to the file before guessing.
- The owner edits more than the decision columns in the workbook (key IDs, channels): compare each row with the
  workbook's own Extract sheet before taking it. The system python has no openpyxl; `zipfile` + ElementTree read it.
- A channel the owner writes beside a firm meant different things: a firm route (Cetera), sales only (Raymond James),
  pure IMO (Flourish, Gold Coast). Ask which, every time.
- BSD `sed` has no `0,/re/`: mutations that must hit the first or nth match use a short Python replace.
- Owner messages arrive by voice and mid-turn; the latest instruction wins (Citizens and HSBC were withdrawn).

## Next steps

1. Owner reruns `01_opportunity_sales.sql`; read the CSV: 25 checks 0, tie-out $7,730.0MM, firm 1 UNMAPPED $0, the
   route basis row `OWNER OVERRIDE: <old> -> FI` for CRD 15340 (if absent and FIRM NOT IN THE DATA is 1, the CRD is not
   in market metrics); log it.
2. Then the owner's next big step (not named yet). Offered: a no-ZIP rollup of `TMP_O2_DATASET` for pivots (several
   hundred thousand rows with ZIP), a FIRM ROUTES part (firm x old x new channel x basis), a Copilot prompt for the six
   pivots described in chat 2026-11-01.
3. The second audit before numbers reach stakeholders: `audit.js` with `from` "2026-10-30: the first audit (611
   claims); what it corrects" (owner's go needed).

## Open owner decisions

- Citizens (CRD 39550) and HSBC (19585) to FI/IMO: withdrawn for now; as a route FI/IMO has no territory (no holder);
  sales-only like Raymond James?
- Alliance Global ($1.8MM, firm 2, no CRD): CRD 8026 or 8361, and the exact market metrics name; held.
- Unassigned ($0.2MM) undecided; Halo, Triad, Nobles & Richards, PHX, Van Clemens left unmapped by the owner.
- Q41 AMER's holder (Ameriprise's $176.1MM of firm 2 sales sit in AMER), Q44 AFS's new holder, Q43 LPL tie-out
  (`explore/lpl_checks.sql` reads the MGA master, not runnable at work), Q28, Q35, Q2, Q7, Q17, Q21, Q23, Q27, Q34.
- Firm 2's top wholesaler is blank for $318MM: RVPs missing from its territory table (name text match).
- Landing: the branch is not on `main`; only the owner lands, and this thread has no issue for `/skill:land`.
