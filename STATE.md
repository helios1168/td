# State — support-master territory design

**Updated:** 2026-09-30 · **Branch:** `main`

## Now

#79 landed (1cb1b3e, 209 tests): scenarios now carry only their own fine channels. The first real runs, WIFI 51 and IFA 50 (`runs/`, local), both stopped at δ = 0.10. The causes are measured on #73: the rounding margin μ_S (IFA needs ±45%; with μ_S = 0 it fits at 0%) and WH's west-coast component (1.6 districts at K = 11). Waiting on the owner: the margin policy, and K_WH.

## Next

- After the owner decides, rerun both scenarios and review the maps and scorecards.

## Blocked

#63 needs a HUD User token on both Studios. Owner decisions: #3 channels, #59 county pieces, #75 catalog (after #74), #76 channels/bundles (after #3). The C4b threshold waits on #69's U34 counts. `AGENTS.md` still reports 24 tests; 205 pass.
