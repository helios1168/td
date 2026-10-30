2026-10-30 · m5-studio/snowflake-v2 · f132ac9 · Agent: session (claude-opus-5-5)

# Opportunity routed by firm: every decision settled; the build is next

Supersedes `notes/2026-10-30_snowflake-opp-routing.md`. The first deliverable is opportunity, both source firms,
routed by firm on the market metrics schema; sales later. Every question that moves the opportunity numbers is now
settled. Read `tools/snowflake/DATASET_LOG.md` Conventions, Settled and Key decisions, then `DATA_MODEL.md`
"Opportunity routed by firm" and its Wells example, before writing SQL.

## Tasks

- Done: the opportunity profile run twice at work (`data/safe/profile_2026-10-30-0324.csv`, `-0444.csv`); firm 1's
  rules applied inside it; both runs logged.
- Done: owner decisions, each in Settled with the owner's words. Q6 (firm 1's channels for both), Q38 (route per CRD x
  broker name; `crd_dist_override` fills gaps only; the route wins where they differ, which is Wells), Q19 and Q39
  (source 2's label and territory pairs), NO CHANNEL kept, scope (EDJ, AMER, AFS out), Q29 (Wells WH, Wells FI and
  National (Chase) keep their original channel's holder), Q36 (fiscal year 2025), Q32 (every product). Q40 closed.
- Done: a Key decisions section; `profile.sql` statement 1 holds each answer as an editable table.
- Done: first audit (611 claims: 508 Verified, 77 Weakened, 26 Falsified), corrected in a log entry and in place.
- Done: `override_review.sql` (owner read the cases), `amer_holder.sql` (parked with Q41).
- Not started: the second audit (owner: wait); the opportunity build (layer `01`).

## Critical references

- `tools/snowflake/DATASET_LOG.md:122`: Key decisions: choice, alternative, evidence, where to change, which report.
- `tools/snowflake/DATA_MODEL.md:97`: the opportunity steps per source; `:150` Wells, the split-firm example.
- `tools/snowflake/explore/profile.sql:48`: the key-decision tables; `:269` the checks, `S2 HOLDER MOVES` among them.

## Changes

- `tools/snowflake/DATASET_LOG.md:20`, `:26`, `:43`, `:54`: Conventions for table variables, one result, the audit,
  masking (scoped to `tools/snowflake/`).
- `tools/snowflake/DATASET_LOG.md:60`: Settled; `:137` Parked (Q41, EDJ's holders); `:152` open index, sales only.
- `tools/snowflake/audit.js`: the audit workflow; `reader-sol` and `auditor-sol` (GPT-6.1 Sol, max).
- `tools/snowflake/explore/*_test.sh`: DuckDB tests (profile 81 checks, override review 16, AMER 14).
- sv-ntlee `main`: `62b6f61` codex models at a 1M window; `e0d37cf` the two `-sol` agents; `f0394fd` anvil removed.

## Learnings

- The codemode sandbox has no `subagent` or `subagent_supervisor` tools; answer and steer children with direct calls.
- Auditors stop to ask before running `shasum` or CSV sums; `audit.js` now grants that read-only set in its brief.
- `audit.js` takes `since` as a date, and every entry today is 2026-10-30, so rerunning now repeats about 600 claims.
  Give it an "entries after this heading" cutoff first.
- Subagent output files have no trailing newline: add one between them when concatenating, or rows merge.
- `~/bin/pi` adds `--approve` and reads arguments as a prompt; use `~/.local/bin/pi` for subcommands.
- DuckDB has no `LISTAGG ... WITHIN GROUP`; the tests map it to `string_agg(... ORDER BY ...)` with `sed`.
- The owner's run outputs arrive mode 600 owned by the owner, in `data/safe/`; files left at `/tmp` cannot be read.

## Next steps

1. Add an after-entry cutoff to `audit.js`, then run it on the entries after "the first audit" (owner's go first).
2. Optional profile rerun: `S2 HOLDER MOVES` with the split firms, AFS's share, the scope numbers.
3. Write the layer `01` plan and get approval: a master firm table, one row per CRD x broker name. It holds firm 1's
   route, the override's gaps from distinct keys, UNMAPPED, scope, and the new-channel list re-keyed from company IDs
   off source 1's rows (company 14 among them). Then one opportunity cell table per source with current channel and
   holder and new channel and holder; Q29 holders; source 2 via Q19 and Q39. One result set with checks; DuckDB test.
4. Views 1, 2a, 2b, 3 for opportunity; then sales (Q7, Q17, Q21, Q28, Q31, Q33, Q34, Q35, Q37, Q42).

## Open owner decisions

- None block opportunity. Still open: Q2, Q23, Q27 (can product split a firm's channel), and the sales questions.
- The audit's K2 found a person's name in the author metadata of `notes/2026-10-12_main-map-joint-wifi-grid-discover.md`,
  another thread; left as is until the owner says.
