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

**User decisions of 2026-09-11 late night (the FI 21 run).**
- FI 21 grid: national k 10 to 16, WH 11, FI 21, v4 CONUS, full rules; split caps
  CA 3, TX 2, NY 2, FL 2 (replacing CA 3 TX 2 NY 3) and band break CA, TX, NY, FL.
- Every solved cell re-realised with the contiguous cut on all seven bundles.
- Full group lists: G1 = TX NY FL NJ IL AZ NC PA MI OH VA GA CO MD; G2 = G1 + WA UT IN LA MN CT;
  other-first MT, WA, WY kept; no WA 1,200 km relaxation.
- The "national cover" rule (`--cover-national`: national covered by any national-carrying
  bundle in the planned stages) with N_WH finishing in seq_WH proved infeasible at every k, and
  route joint found no incumbent. The user then chose "finish in seq_N plus other-first": the
  group's national in pure N (`--force-national`) except CO (G1) or WA, CO, LA (G2), which go
  in the other-first all-channel district. Under it TX needs one N district at k 10 to 13 (G1)
  and 10 to 14 (G2). Numbers: `mem:facts/fi21-cover-grid`.

**The question the FI 21 run answers (user, 2026-09-11, durable).** Which states must get a
national-only district. G1 and G2 are candidate pools; national-only districts must not spread
into other states (unforced runs put $5.8B of non-group national, CA $4.1B, into N districts,
which the user rejected as missing the point). Every other state's national rides with its WH
and FI (WH_PLUS / FI_PLUS pairs or all-channel WIFI). Answer so far: `mem:facts/fi21-cover-grid`.

Open at the night checkpoint (user's calls): the "other" floor, ND SD NE on FI alone, the
900 km / 6-state cap or none, counts 16/11/20 or 18/11/19, route R (parked), WH_03's CT-end
piece, ★B WHFI⁺, ★C rep pool against district count, ★D η and the tie-break, ★E cross-plan
state splits.

Source: host memory td-full-problem-overnight-2026-09-10 (modified 2026-09-11);
`worktree-full-problem:PLAN.md`.
