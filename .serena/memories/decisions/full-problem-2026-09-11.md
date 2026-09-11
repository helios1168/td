# Full-problem (multi-channel) decisions, 2026-09-10 and 2026-09-11

The full problem: CWIFI, $48B across national, WH and FI on CONUS, each carved into contiguous
districts of about $1B (floor $800MM, cap $1.2B, so U = 1.2 tau), one wholesaler per district
and at most one district per wholesaler, channels designed in priority order national, WH, FI,
the residual called "other". Formulation `docs/FULL_PROBLEM.md` and `docs/MODEL_FULL.md` on the
track; the 2026-09-10 decisions log is in `git show worktree-full-problem:PLAN.md`. Where
things live: `mem:workflow/full-problem-track`.

**What the grid taught (2026-09-10 night).** A fixed count banded on its own mean is a
near-full-cover problem and is infeasible under a cap, so counts are ceilings
(`--k-mode cap`). The 5% band loses to 10% in every pair. Under 900 km / 6 states no single
channel can serve WA, MT or WY at a full book, so "every state served" needs all-channel
"other" districts planned before the channel stages. The user judges scenarios visually
(compact, contiguous, coverable by one person); every state must be in at least one grouping.

**User decisions of 2026-09-11 (durable).**
- National in the v3 file is the sum of three sub-channels: National (Chase), Wells (WH),
  Wells (FI). A merge folds Chase and Wells (FI) into FI and only Wells (WH) into WH. The next
  export carries them as `national_chase`, `national_wells_wh`, `national_wells_fi`, any letter
  case (decision 12 in `docs/FULL_PROBLEM.md`).
- All-three-channel districts are called WIFI (`WHFI_PLUS_nn` displayed as `WIFI_nn`).
- Split caps CA 3, TX 2, NY 3 (`--max-splits`); districts touching CA or TX may break the band
  to hold them (`--band-break CA,TX`): CA national is 3.79 books, three districts cannot hold it
  at U.
- All opportunity is covered: a level-0 sweep attaches every residual (state, channel) to an
  adjacent district whose bundle carries exactly those channels, breaking the band if needed;
  a zip-level sweep in the realiser attaches unclaimed cells. The legal state patterns are
  four: N + WH + FI, N + WHFI, WH_PLUS + FI_PLUS with equal shares (a pairing row), WHFI_PLUS.
- Summary maps: one per bundle, the app's reach layer only, no zip geometry, neighbouring
  districts in clearly different hues, wholesaler counts per state and the total in the title.
- Contiguity-aware split-state cut: adopted for the WH bundle only (fixes WH_10, ten pieces to
  one). Land-clipped contiguity graphs changed nothing that matters and stay unadopted in
  `worktree-contig-cut`.
- Two exploratory cells: national at k 10 and 12; all channels merged at 48 to 53 districts.

Open at the night checkpoint (user's calls): the "other" floor, ND SD NE on FI alone, the
900 km / 6-state cap or none, counts 16/11/20 or 18/11/19, route R (parked), WH_03's CT-end
piece, ★B WHFI⁺, ★C rep pool against district count, ★D η and the tie-break, ★E cross-plan
state splits.

Source: host memory td-full-problem-overnight-2026-09-10 (modified 2026-09-11);
`worktree-full-problem:PLAN.md`.
