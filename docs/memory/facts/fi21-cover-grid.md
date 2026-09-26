# The FI 21 grid on v4 CONUS, 2026-09-11 late night

Instance `instance_descaled_v4_conus.json.gz` (sha256 `484e705a2e74596c...`), code
`worktree-full-problem` at `da124ae` (grids ran from snapshots of `a87b86c` with the realiser of
`4fd87fc`; `_newcut` re-realised with the realiser of `a87b86c`). National k 10 to 16, WH 11,
FI 21, full rules, caps CA 3 TX 2 NY 2 FL 2, band break CA TX NY FL, 180 s per pass, 2 threads.

- Plus-pair bug, fixed in `a87b86c`: with WH_PLUS unused, the FI stage's greedy put a state in
  FI_PLUS against a zero target, solved cold and stopped at 180 s on the empty plan; every cell
  came back "ok" with no FI district. After the fix cover_FI is about 8,520, certified in 2 to
  5 s. `cec2617` now fails such a pass as no_incumbent.
- `--cover-national` with N_WH finishing in seq_WH: 14 of 14 cells infeasible in seconds. After
  seq_N the listed states' national left is TX 4 to 13%, CO 100%, LA 100% (k 10, 11), AZ partly
  (k 12+); a WH_PLUS share is bounded by the state's national residual, so the slot cannot reach
  L = 430. Route joint (168 slots): no incumbent at 180 or 600 s.
- Finish in seq_N plus other-first (grid `_S`): TX=2 infeasible at k 10 to 13 (G1) and 10 to 14
  (G2), the last k of each proven at 600 s; TX=1 solves all of them. TX=2 solves G1 14 to 16
  and G2 15 to 16. `force_check.py` OK on all 14 solved cells.
- Unforced: 43 to 47 districts; N opened below the ceiling (10 at k 10 and 11, 11 at 12 and 13,
  13 or 14 at 14 to 16), WH 10 of 11, FI 20 of 21. Unheld mass 0 on every channel everywhere.
- Districts in pieces, before and after the border-aware cut and the DC-VA edge: 25 to 15 over
  the 8 unforced cells, 78 to 70 over the 14 S cells. WH_03's (G2: WH_04's) 113-zip CT end
  stays in every cell but S1 n14 and n15: the district is CT, NJ and 5% of NY, and NY's share
  cannot join NJ to CT. A bridge seed in the cut joined it (15 to 2) but carried 14 times the
  share and starved neighbours (cut deviation to 1,371%), so it was reverted (`8e7b027`).
  - Addendum, 2026-09-25 (m5 session 01a0d8f6, for td#52): this is the old realizer's only clean contiguity measurement (graph cut and repair, no healing), so the after figures, 15 districts in pieces over 8 maps and 70 over 14, are about 2 and 5 per map. The catalog's "100% Contiguous" came from healing with no band check and is not a baseline (MATH_REVIEW §3.4–3.5).

- The border-aware seed (`9439874`) has a defect (bead `td-9ek.20.7`): over the 22 cells it
  leaves a district's share of FL or NY under 25% of target in 7 cells (old cut: 4). Worst U n16
  N_11 gets 12 of a 370 FL share and ends at mass 114. The "25 to 15" pieces figure above is
  bought with that; figures in `fi21_summaries/` carry both cuts.

## The national-only study (2026-09-11, done)

The point of the FI 21 run is to find which states must get a national-only (N) district. N
districts may hold only a named pool (`--national-states`, `b6d7deb`); the N band divides only
the pool's national (`8de37ed`); a state still holding all its national after seq_N is closed
to pure WH / FI / WHFI slots, so its national rides in WH_PLUS / FI_PLUS or WHFI_PLUS
(`cca6be9`); the sweep never takes a non-pool state's WH or FI into a slot without its
residual national (`8bf4a43`; before it VT's 1.8 units were unheld in every cell and NM's 15.2
at G1 k 12, because the pure WH / FI sweep went first and stranded the national). Grid
`grid_20260911_fi21_P5`, v4, k 10 to 16, WH 11, FI 21, caps CA 3 TX 2 NY 2 FL 2, pool = group
+ DE DC SC CA; unheld mass 0 in all 14 cells (22,922 units).

- G1: every G1 state gets N districts except IL and CO, at every k. TX partly N to k 13 (81,
  74, 75, 69%), wholly from k 14 with two TX districts. N used 9, 9, 10, 11, 12, 12, 13;
  wholesalers 46, 47, 47, 50, 48, 48, 50.
- G2: IL wholly N (IN opens the route to MI and OH); CT joins NY; LA joins TX's second district
  from k 14; CO, WA, UT, MN none (MN in WIFI to k 13, WH+ / FI+ from k 14). TX 88, 82, 68,
  65%, then 100%. N used 9, 10, 10, 11, 13, 13, 14; wholesalers 45, 47, 47, 48, 51, 51, 53.
- Why: IL (G1), CO, WA, UT have no pool neighbour in the model's state graph (IL: WI IA MO KY
  IN, no Lake Michigan edge; CO and UT meet AZ only at the Four Corners point; WA: ID OR) and
  each is below the N floor alone (IL 322, CO 164, WA 121, UT 107 against 658 at k 10, 411 at
  k 16; a lone IL district needs k about 21).
- Enclaves DE (MD NJ PA), DC (MD VA), SC (NC GA) are wholly surrounded by G1 states; a
  WH_PLUS district cannot pass through N-only states, so they must be in the N pool.
- CA must be in the N pool under cap CA 3: its national (1,984) cannot fold into FI_PLUS with
  three CA districts (the band-break allowance is read off the pure FI bundle). With CA cap 6,
  or with plus-pair off, the FI stage passes too.
- A hard cover row on every non-pool state (`--cover-national` all states) is the wrong tool:
  SD and ND reach the other-first WIFI district only through the sweep, so their national is
  still uncovered at seq_WH and the stage is infeasible.
- Non-pool national with no rule at all is left unheld (2,891 units at k 10, CA alone 1,984).

## The dollar-target study (2026-09-11, worktree-full-problem-usd)

Bands pinned: national, WH, WH+FI, WIFI at 481.81 units ($1B), FI at 433.63 ($900MM), plus or
minus 10%, counts free (`--band-target`). G1: 47 wholesalers, 12 N; G2: 48, 14 N; unheld 0.
State answer unchanged from the count bands, except AZ only 24% national-only (rest in the AZ
CO NM WIFI district). Districts sit at the top of the band: with the count free the cover pass
fills to U and the contacts pass prefers fewer districts, then the re-draw and sweep add up to
5%; outside the capped states G1 FI realises $958MM to $1,008MM and N $1,070MM to $1,118MM, G2 N
$899MM to $987MM and FI $794MM to $996MM. CA (cap 3) N districts $1.3B to $1.5B, CA FI one
district $1.49B, TX WH+FI $1.47B, FL and NY N $1.12B to $1.17B (band break). To centre on the
targets: band (0.9, 1.0) of a target 5% above the goal, or a mass-balance pass after cover.

Source: `worktree-full-problem:HANDOFF.md` (the FI 21 section and table), beads `td-9ek.20.*`;
the national-only study in `PLAN.md ## Next step` and bead `td-9ek.20.8`.
