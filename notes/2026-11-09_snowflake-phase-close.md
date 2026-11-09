2026-11-09 · m5-studio/snowflake-v2 · Agent: session (claude-opus-5-5)

# Snowflake v2: the Tableau table phase, closed out

Supersedes `notes/2026-11-01_snowflake-tableau-v2.md`. The owner runs one script,
`tools/snowflake/01_opportunity_sales.sql` (its SET lines now hold the real table names, owner 2026-11-01), and sends
back one CSV. It rebuilds the Tableau table as `DATA_WITHNEWCHANNEL_UNION_W_JOINKEYS_V2` and its territory join
`TERRITORIES_V2`; the live table is never written. Read `tools/snowflake/DATASET_LOG.md` Key decisions first; the
column mapping is statement 17's comment.

## Tasks

- Done since the 2026-11-01 note: Raymond James as the old table (firm 2 FP, BD → IFA, BK → FI by firm name; the
  owner's three Raymond James sales-channel rows removed); Citizens and HSBC firm 2 sales on their firm's channel
  (owner: "option 2"); NULL DIST_CH left NULL (blank-channel firms the old query dropped); TABLEAU parts SCHEMA, IMO
  AND RAYMOND JAMES, BOOK BY CHANNEL folded into the script; `explore/v2_dupes.sql` (Citizens and HSBC: no repeated
  rows within a source, the two sources' opportunity summed); `explore/policy_tables.sql` (no policy grain in what
  the owner can read).
- Open, data: the owner saw firm 1 SALES_AMOUNT with DIST_CH = 'IFA/IMO' at about $23MM in `_v2` against about $1B in
  the old table. The code keeps the raw label and the test data shows it; the full run's CSV (SALES CHANNEL item
  `IFA/IMO -> IFA`, TABLEAU IMO AND RAYMOND JAMES) was never sent. Ask for it first.
- Not run in Snowflake on the current commit, as far as the log shows.

## Critical references

- `tools/snowflake/01_opportunity_sales.sql` statements 8 (`tmp_s2_name_sales_channel`), 12 (new channel order), 17
  (`_v2`, `TERRITORIES_V2`), 18-18b (TABLEAU parts), 19 (the one result).
- `data/safe/legacy_imo_2026-11-01-1808.csv` (the old tables), `data/safe/v2_dupes_2026-11-02-0821.csv`.

## Learnings

- Every query for the owner goes on GitHub before it is given, and into the one script unless it reads only an
  existing table (owner: "put it on github"; "one query, one output file").
- `git grep` misses new files; scan with `grep -r`. Check `git log` for commits you did not make: two sessions once
  wrote this worktree.
- The old union never had firm 2 opportunity: summing MM_OPP across SOURCE in `_v2` counts one market twice.

## Next steps

1. Get the full run's CSV; settle the IFA/IMO $23MM question.
2. The owner's decisions below, then the next phase (not named yet).

## Open owner decisions

- Firm 2's opportunity in `_v2`: keep (filter SOURCE in every sheet) or 0 as the old table (patch offered:
  `UPDATE ... SET mm_opp = 0 WHERE source = 'EQH'`; permanent in statement 17 on the owner's word).
- The address join (`$s1_addr`, `$s2_addr`; ADDRESS parts in the CSV); an old-state territory join.
- Alliance Global; Q41 AMER's holder; Q44 AFS's; the second audit (`audit.js`); landing (owner: not now); the public
  repo now carries carrier table names (owner: "don't worry about masking for now").
