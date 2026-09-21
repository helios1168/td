# CONUS Track 2 anchored grid (2026-09-07)

Run `battery/results/borders_k18_v2conus_20260907/track2_anchored/` on the CONUS draw
`draw_k18_v2conus_20260907/k18` (seed 3 committed by stage 2 at 95.7312, spread 1.585%
completed, nash 110.7954), flags `--anchor-homes --time-limit 600 --rounds 5 --eta 0.01`.
Branches `worktree-conus-d05`, `-d07`, `-d10` hold the figures and each run's `PLAN.md`. Max
deviation and spread are realised on the 3,713 zips; the level-1 pass is the fractional balance
the band was checked on.

| δ | level 1 | splits | split states | level-1 pass | spread | max dev | outside band | nash gap | stage 2 | wall |
|---|---|---|---|---|---|---|---|---|---|---|
| 5% | optimal, gap 0 | 8 | CA 5, NY 3, TX 2, FL 2 | 4.68% | 12.02% | 6.26% | 4 (D09, D12, D14, D15) | 0.0145 | 95.654 | 187 s |
| 7% | optimal, gap 0 | 8 | CA 5, NY 3, TX 2, FL 2 | 6.97% | 12.87% | 7.08% | 1 (D09) | 0.0222 | 95.647 | 166 s |
| 10% | time limit, gap 1.75% | 8 | CA 5, NY 2, TX 2, FL 2, NJ 2 | 9.52% | 18.97% | 10.02% | 1 (D12) | 0.0523 | 95.802 | 609 s |

- The δ = 5% map is the shipped whole-instance partition on 17 districts; only New York's
  three-way cut moved (29 zips, 0.99% of M). δ = 7% differs on 69 zips (1.9%), δ = 10% on 562
  (17.0%).
- Every band is overshot after level-2 rounding, so the realised map never sits inside the band
  level 1 certified; the overshoot is 1.26 points at δ = 5%.
- D11's home state MO holds 17.6% of its mass under every δ (IN 22%, LA 20%). The anchor
  guarantees inclusion, not plurality.
- 113 reps on the CONUS instance, 95 unmatched.
- The shipped headline map re-measured on the CONUS set: spread 12.02%, max deviation 6.26%
  (D18 -6.26%, D17 +5.76%, D16 +5.18%), against 8.98% / 5.25% on the whole instance.

Related: `mem:facts/shipped-map`, `mem:facts/state-border-snapping`,
`mem:facts/instance-versions`.

Source: `main:STATE.md` `## Facts` (a3924e8).
