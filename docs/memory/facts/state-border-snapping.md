# State-border snapping grids (overnight 2026-09-07, v2 whole instance)

Results `battery/results/borders_k18_v2_20260907/`; build and narrative in
`git show ae2b18d:docs/BORDERS_PLAN.md` and `git show ae2b18d:docs/BORDERS_RESULTS.md`.

Summary. At δ = 5% every state can lie whole in one district except CA, TX, NY and FL (Track 2
anchored: 8 splits, certified minimal; realised spread 9.0%, free form 7.2%). At δ = 10% one
more CA cut goes away (7 splits, certified anchored; bound 6 free) and spread doubles to 17%,
not worth it. Track 1 (snapping the committed map only) never reaches zero residual splits: the
committed owner sets force 5 to 8 small states to stay split at every δ (PA+MD+DE is 18% light
of a full district, D06 without AZ is 32% light); it does cut the outside-owner share from
9.15% to about 3% and border segments from 1,591 to about 700. Stage-2 value stays within 95.70
to 95.93 in every cell (committed 95.755): moving borders onto state lines costs nothing
measurable at staffing.

Track 1 (owner sets from the committed map; δ two-sided; ten Lloyd rounds, no Nash polish;
"split states" excludes CA/TX/NY/FL):

| cell | spread | max dev | outside (committed) | outside (own) | split states | zips changed | border segs | stage 2 |
|---|---|---|---|---|---|---|---|---|
| committed | 1.37% | 1.00% | 9.15% | 9.15% | 24 | 0 | 1591 | 95.755 |
| snap | 51.01% | 29.10% | 0.00% | 2.15% | 0 | 519 | 938 | 95.656 |
| δ 0, λ 100 | 1.75% | 1.30% | 3.72% | 5.83% | 6 | 500 | 720 | 95.813 |
| δ 1%, λ 100 | 2.50% | 1.48% | 3.24% | 3.21% | 8 | 510 | 706 | 95.830 |
| δ 2%, λ 100 | 3.59% | 1.83% | 3.09% | 3.06% | 8 | 523 | 718 | 95.826 |
| δ 5%, λ 100 | 10.33% | 5.50% | 2.34% | 1.92% | 5 | 602 | 700 | 95.797 |
| δ 10%, λ 100 | 19.75% | 10.16% | 1.84% | 3.76% | 8 | 786 | 662 | 95.707 |

λ in {1, 10} at δ = 2% shows the soft regime: spread 4.78% / 3.77%, outside 5.42% / 3.11%,
split states 15 / 8.

Track 2 (state-level minimum-splits MILP, `mip_rel_gap = 0`, 600 s per δ; "certified ≥" is the
dual bound less the tie-break's half-split allowance; bold = closed to optimality):

| form | δ | splits | certified ≥ | pass spread | realised spread | zips changed | stage 2 |
|---|---|---|---|---|---|---|---|
| free | 0 | 17 | 9 | 0.00% | 1.66% | 648 | 95.932 |
| free | 1% | 12 | 9 | 1.36% | 1.75% | 594 | 95.816 |
| free | 2% | 9 | 8 | 3.28% | 3.61% | 783 | 95.765 |
| free | 5% | 8 | 6 | 8.89% | 7.21% | 932 | 95.803 |
| free | 10% | 7 | 6 | 17.27% | 17.08% | 1011 | 95.701 |
| anchored | 0 | 18 | 9 | 0.00% | 1.42% | 932 | 95.810 |
| anchored | 1% | 24 | 9 | 1.51% | 2.76% | 843 | 95.736 |
| anchored | 2% | 9 | 8 | 3.01% | 3.34% | 784 | 95.780 |
| anchored | **5%** | **8** | **8** | 9.30% | 8.98% | 776 | 95.788 |
| anchored | **10%** | **7** | **7** | 18.01% | 16.81% | 978 | 95.880 |

Only anchored δ = 5% and 10% closed (168 s, 386 s); every other cell is a time-limited
incumbent. CONUS re-run: `mem:facts/conus-track2-grid`.

Source: `main:STATE.md` `## Facts` (a3924e8).
