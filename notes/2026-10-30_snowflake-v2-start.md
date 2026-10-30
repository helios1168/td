2026-10-30 · m5-studio/snowflake-v2 · c0079a1 · Agent: session (claude-opus-5-5)

# Start: opportunity and sales by channel and territory, rebuilt on `DATA_MODEL.md`

The Snowflake thread starts over on this branch (from `main`). Read `tools/snowflake/DATA_MODEL.md` and
`tools/snowflake/DATASET_LOG.md` first; nothing before 2026-10-30 is needed, and it is all in the tag
`archive/snowflake-2026-10`. The owner runs SQL at work in Snowflake; every query is tested first in DuckDB on an
extract in `data/safe/extract_<date>/` (gitignored).

## Tasks

- Done: the conceptual model (`DATA_MODEL.md`): sets, measures, maps, two states, views, invariants, per source on
  the market metrics schema; three gromov passes behind it (`notes/2026-10-29_snowflake-conceptual-model-research.md`).
- Done: fresh log; settled, parked and open questions triaged with the owner (log, 2026-10-30).
- Done: old branch frozen in the tag and deleted; old worktree retired; old extract and synthetic files moved to
  `data/safe/_archive_2026-10/` (with `hub_root/` for the git-excluded files that sat at the hub root).
- Partial: `tools/snowflake/explore/schema.sql` written (columns of every table from `INFORMATION_SCHEMA`); not run.
- Not started: the extract request as a Run All file; conformance per source (layer `01`).

## Critical references

- `tools/snowflake/DATA_MODEL.md`: the distributor key per dataset, the maps' status, the pipeline.
- `tools/snowflake/DATASET_LOG.md`: conventions, Settled, the open index (Q2-Q32), the 2026-10-30 entry with the
  sorted transformations of the owner's query.
- `/Users/Shared/sv-ntlee/td/mm_query.sql`: the owner's source 1 query, git-excluded, never committed.

## Changes

- `tools/snowflake/DATA_MODEL.md:27`: the distributor key per dataset and its five checks.
- `tools/snowflake/DATA_MODEL.md:41`: maps, with ρ_s and τ_s per cell (settled for override-listed distributors).
- `tools/snowflake/DATA_MODEL.md:64`: views 2a reclassified and 2b reassigned.
- `tools/snowflake/DATASET_LOG.md`: new file; question numbers continue the archived log's.
- `tools/snowflake/explore/schema.sql`: three statements; carrier-named tables are `<...>` placeholders.

## Learnings

- The owner declines popup questions; ask in plain text with a recommendation.
- Results pasted through a spreadsheet turn "1 : 1" into "1:01" and split columns; ask for text output.
- The owner's query (`mm_query.sql`) covers source 1 only. Its new state carries the current label forward except
  for listed distributors and keeps the current holder (`:706`, `:718`); whether that is intended is Q27 and Q29.
- Source 1's raw vendor rows carry CRD and broker name, so `mm_map` is needed only for source 1's sales.
- Rules from the owner on Snowflake behaviour: docs or the owner, never assumed (log, Conventions).
- The 2026-10-25 rule keeps table names that name a carrier out of the repo; SQL uses placeholders for them.

## Next steps

1. Owner runs `tools/snowflake/explore/schema.sql` at work (types the placeholders), sends statement 3's output.
2. Write the tier-1 export file against the real names: E1 channel values per dataset (dataset, value, rows, $); E2
   source 1 vendor feed distinct `cbd_id`, `client_firm_id`, CRD, broker name with rows and $; E3 `mm_map` whole;
   E4 source 1 sales distinct company ID and firm name with rows and $; E5 source 2 opportunity distinct CRD and
   broker name; E6 source 2 sales distinct CRD and firm name; E7 source 2's CRD map whole. Fiscal year 2025, CSV.
3. From tier 1: the shared-channel question (do the feeds use the same channel values?), `mm_map` uniqueness and
   coverage by $, the split-CRD candidates (Q27), and the real labels for the source 2 channel and product maps
   (log, Settled).
4. Tier 2 at cell grain: E8 source 1 vendor rows (ZIP, IDs, product line, VA type, feed channel, `territory`, $);
   E9 source 2 opportunity rows; E10 source 1 sales after the query's source-internal steps, with the label before
   and after the IMO step; E11 source 2 sales; E12 territories, both sources (source, ZIP, channel, holder ID); E13
   source 1 regions tied to one distributor (the ones `mm_query.sql:691` filters out).
5. Build layer `01`, conformance per source, in DuckDB with the five key checks; then the unified facts.

## Open owner decisions

- Q27: which CRDs the channel rules split by broker name; I3 for every distributor or only listed ones.
- Q28: in the current state, a sale placed by its recorded label or by its cell's channel.
- Q29: how a new channel such as National reaches holders: by ZIP, by distributor-tied territories, or the current
  holder kept.
- Q31: a wholesaler's market share, territory share or credited sales over held market.
- Q32: whether a source's market includes products it does not sell.
