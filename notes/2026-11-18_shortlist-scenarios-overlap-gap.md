2026-11-18 · m5-studio/maps · 2430977 · Agent: session (claude-opus-5-5)

# Shortlist scenarios, scenario maps, overlap and gap (#147, #148)

Picks up after `notes/2026-11-09_snowflake-phase-close.md`. In this phase the territories stay as they are: assignments are labels only, and nothing is redrawn until the bargaining and optimization phase.

## Tasks

- **Feed the shortlist sheet into 03: done.** The sheet is `ssdb_integration.lr_strategy.channel_contacts`. Every name is matched (0 unmatched): 166 slots, 98 open.
- **Owner's Windows developer experience: done.**
  - Helix F5 runs the whole file through `run_sql.py`.
  - F6 pipes the selection.
  - `sql_session.ps1` gives one login per session.
  - `--then` chains files.
  - These rules are in the AGENTS.md section "Developer experience".
- **#147, scenarios and local scenario maps: done.**
  - The owner said "maps are looking good".
  - The scenarios are CA1_R105N, CA2_R105N and CA1_R105R. Each is defined by keys in 03's key-edit block.
- **#148, overlap and gap: partial.**
  - 07 is built and run once.
  - The split-state fix (dd0b4d5) and the area-adjusted load (2430977) were pushed. The owner is rerunning `scenario_maps.ps1 -All` with them.
  - The write-up for the owner is not written yet.
- **Next-phase plan issues (Nash bargaining, gap-fill and reshape): in progress.**
  - A `reader` is gathering the context.
  - The issues get posted for owner approval.
- **`tools/maps/gap_report.py`: in progress.** It turns the uploaded CSVs into the write-up. A `worker` is writing it.
- **Reviewer pass on ad45c6a..2430977: in progress.**

## Critical references

- `tools/snowflake/DATASET_LOG.md`: every owner decision, quoted. The newest entries start at line 2001.
- `tools/snowflake/07_overlap_gap.sql`: its header defines the classes and the TD_GAP_* tables.
- `tools/maps/scenario_maps.py`: the maps, the gaps PDF and the CSVs.

## Changes

- `tools/maps/scenario_maps.py:581` USD_PER_MM: MM_OPP holds raw dollars despite its name. The PDFs divide by 1e6.
- `tools/maps/scenario_maps.py:218` BETA, and `:226` gap_load: the area-adjusted load. It writes `<scenario>_gap_load.csv`.
- `tools/snowflake/07_overlap_gap.sql:117` COVERED now means the cell's single holder is any of the people assigned to it. DOUBLE ASSIGNED is gone.
- `AGENTS.md:39`: every file named to the owner gets its full Windows path. The run prints the absolute paths of the files that are safe to send.

## Learnings

- **Split states are the sheet's design.**
  - The sheet has 56 NATIONAL and 60 REGIONAL rows over 50 states, so large states are split between two people of one channel.
  - Classing those cells as a conflict put about $18B of national and $30B of regional per estimate into DOUBLE ASSIGNED.
  - So a class is judged against the set of people assigned to the cell.
- **MM_OPP is in dollars.** Example: 04 reads 41,337,760,848.76 for $41.3B. The $MM figures in the older DATASET_LOG tables are divided by 1e6.
- **The owner wants full paths.** Say `C:\Users\ntlee\td-maps\data\safe\maps\<run time>\<file>`, never a bare name.
- **The first 07 run (CRBG estimate, CA1_R105N, $106.6B):**
  - OVERLAP is small, $2.6B regional, because most other holders are not on the shortlist.
  - HELD BY ANOTHER is $5.6B.
  - GAP is $5.5B: regional $3.9B, WH $1.5B, national $0.2B.
  - OPEN SEAT is $11.4B.
  - R105 as regional moves about $1.8B from open seat into regional.
  - CA1 and CA2 do not differ at the class level, because R47 and R108 both hold only FI.
- **Leftover branches and worktrees in the hub.** The okf/nightly worktrees hold memory-store proposals that were staged but never committed, about 4 to 12 per night from 2026-10-24 to 2026-11-10. Do not delete them. They need store-writer and `/review`.

## Next steps

1. When the owner uploads the rerun CSVs (three `_gap_summary.csv` files, plus `CA1_R105N_gap_pair.csv`, `_gap_person.csv` and `_gap_load.csv`):
   - run `tools/maps/gap_report.py` on them;
   - write the answer to #148: bargaining pairs and their $, gaps and open seats by state and channel, and heavy or light territories for their area;
   - post it on #148.
2. Apply the reviewer's findings. Tell the owner if a rerun is needed.
3. Post the two next-phase plan issues for approval:
   - (a) Nash bargaining on TD_GAP_PAIR;
   - (b) gap-fill and reshape with the support-master pipeline, aiming for an area-adjusted load near 1.
4. Clean up, after the owner approves the list:
   - the 16 `pi-subagents/stage-*` branches (0 commits ahead of main, no worktree, not on GitHub);
   - `worker/gaps-pdf` and `worker/overlap-gap` (their content is in m5-studio/maps);
   - the paused worker 0c68e4f3.
5. The nightly okf proposals: a separate task, routed to the owner.

## Open owner decisions

- **Basis for the national and WH targets:** the channel's attributed $ ÷ 11 and ÷ 12, until the stakeholders give figures.
- **Optional:** ask the Snowflake admins for `ALLOW_ID_TOKEN = true`. Ask GitHub Support to purge the commits from before the history rewrite.
