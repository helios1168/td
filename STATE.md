# State — support-master territory design

**Updated:** 2026-09-28 · **Branch:** `main`

## Now

#56 landed: OD1 sets the default final band at 10% per planning channel, declared per scenario, with 1e-9 × τ_c audit slack; old state band breaks are retired. #61 landed; #3 is ready, and #62 is in progress on m5.

## Next

- `/execute 3`: run the fresh v3 extract with new channels.
- `/land 62` when its m5 handoff is landable.

## Blocked

#64 waits on global literature changes. Other owner decisions remain in GitHub Issues. `AGENTS.md` still reports 24 fast tests; 27 now pass (#61).
