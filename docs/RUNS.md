# The pin-cost catalogue — results

**Date:** 2026-09-04 · **Branch:** `wt/runs` · **Instance:** `instance_descaled_v2.json.gz`
(gitignored; provenance and validation in `docs/RUNS_PLAN.md` §2) · **Artifact:**
https://claude.ai/code/artifact/f903ee01-eefc-40cf-bd32-8f5536b6e65f

This is the plan's §4–§8: the 14+1 scenario catalogue actually run, plus one solver fix found
along the way. `docs/RUNS_PLAN.md` is the plan; this file is the result.

## What ran

15 runs of `tools/run_draw.py instance_descaled_v2.json.gz --k 14-22 --seeds 0-9` — the unpinned
baseline plus each of 7 regions × {`fix`, `anchor`}. Every run: 0 unstaffed districts, district
masses sum to the instance total (3,748 zips, total M 8,523.2). Scenario specs are committed at
`docs/artifacts/runs/scenarios/*.json`; the driver is `docs/artifacts/runs/run_all.sh`; maps via
`docs/artifacts/runs/make_maps.sh`; the artifact generator is `docs/artifacts/runs/build_artifact.py`.

`fix` is a closed district (exactly those states, never touched by the solver, k reduced by
one); `anchor` is open (those states locked in, the solver fills the rest toward the common
target through water-fill). A consequence worth stating plainly: **a `fix` district's mass is
invariant to k** — it is always the sum of M over its pinned states, regardless of how many
districts the rest of the country is cut into. Only the target (`total / k`) moves, so a `fix`
region's deviation from target is a pure function of k, computable without re-running anything:
`M_region · k / total − 1`, crossing zero at the region's own natural k = `total / M_region`.

## The solver fix (found mid-run, not part of the original plan)

The catalogue hung — a single stage-1 draw took **0.08s on the old instance and up to 214s on
the new one**, a slowdown far beyond what the ~3× larger instance should cost. Isolated to
`td/solvers/centers.py::assign()`'s `scipy.optimize.linprog(method="highs")` call: on
`scipy` 1.18.1, the auto-selecting `"highs"` method (and `"highs-ds"` called with no `options`
at all) can hang indefinitely on this instance's transportation LP, confirmed via
`faulthandler.dump_traceback_later` — the process never returns from HiGHS's C++ solver. Calling
the identical LP with `method="highs-ds"` **and any `options` dict** (even a non-binding
`time_limit`) solves it in well under a second. Root cause not fully explained (a scipy/HiGHS
option-merging quirk, not real problem hardness — ruled out the two Alaska/Hawaii zips'
extreme LAEA coordinates as a cause first), but the fix is narrow and defense-in-depth: pin
`method="highs-ds"` with `options={"time_limit": 60.0}`, and raise loudly if that limit is ever
hit rather than silently returning a suboptimal split.

**Verification, with the user's sign-off before proceeding each time:**
- `tests/run_all.py` → 184 pass, 0 fail (unchanged).
- Old-instance regression (`--k 8-16 --seeds 0-9`) against `sweep_20260902_s10`: 8 of 9 k-values
  byte-identical; **k=9 differs at the noise floor** — all ten seeds are near-exact ties (nash
  51.484791–51.484797, spread ~6e-6) and the new LP method flips which tied seed wins, moving
  nash by ~3e-6 — about 1,000× below the project's established 5e-3 nat tolerance
  (`CLAUDE.md`'s two-tier acceptance). Accepted as expected tie noise, not a defect.
- New-instance sanity check (`--k 14-22 --seeds 0-2`): 9 k-values × 3 seeds in 14.6s, 0
  unstaffed, balance within 1.4–1.9% — matches the plan's original ~56s/run estimate once the
  hang was removed. The full 15-run catalogue then completed in line with that estimate.

## Region table, recomputed from the catalogue

Total M = 8,523.2; target at k=18 is 473.5. `nash Δ` and `stage-2 Δ` are against the unpinned
baseline at k=18, in nats — exact at fixed k because every scenario partitions the same total
into the same number of districts (`CLAUDE.md`'s scale-invariance argument).

| region | pinned M | vs target (k=18) | natural k | fix: nash Δ | fix: stage-2 Δ | anchor: nash Δ | anchor: stage-2 Δ |
|---|---:|---:|---:|---:|---:|---:|---:|
| CALIFORNIA | 1,953.8 | +312.6% | 4.36 | −2.037 | −2.126 | −2.037 | −2.217 |
| TEXAS | 972.1 | +105.3% | 8.77 | −0.368 | −0.430 | −0.368 | −0.412 |
| MIDWEST | 876.5 | +85.1% | 9.72 | −0.257 | −0.224 | −0.257 | −0.223 |
| NEWYORK | 849.6 | +79.4% | 10.03 | −0.229 | −0.409 | −0.229 | −0.413 |
| FLORIDA | 661.9 | +39.8% | 12.88 | −0.068 | **+0.029** | −0.068 | −0.019 |
| SOUTHWEST | 606.8 | +28.1% | 14.05 | −0.036 | −0.089 | −0.036 | −0.013 |
| CAROLINAS | 535.2 | +13.0% | 15.92 | −0.008 | −0.013 | −0.008 | +0.012 |

**Findings:**
- Cost tracks distance from natural k, as designed: CALIFORNIA (natural k 4.36, far from the
  14–22 sweep) costs ~2 nats; CAROLINAS (natural k 15.92, inside the sweep) costs ~0.01 — about
  250× less. This is the "V" the catalogue was built to price.
- `nash Δ` (balance cost) is identical between `fix` and `anchor` for every region — expected,
  since both pin the same mass to the same district and Σ log M only sees district masses, not
  which mechanism produced them.
- `stage-2 Δ` (the staffed objective) is where `fix` and `anchor` diverge, and isn't always
  negative: **FLORIDA `fix` staffs +0.029 nats *better* than the unpinned baseline**, and
  CAROLINAS `anchor` staffs +0.012 better. Stage 2 sees rep books that stage 1 doesn't — a
  hand-drawn district can occasionally staff better than a balance-only solver's split, even
  though it can never staff better on *balance* alone. This is the mechanism `channel.score_draws`
  exists for, now measured directly rather than argued.
- Every region is still oversized as a single district at k=18 (all natural k below 18, per
  `RUNS_PLAN.md` §3's earlier finding) — CAROLINAS is closest, CALIFORNIA furthest.

## What's not resolved here

- **Which states are hand-drawn** (FRAME §0's open item) — this catalogue is the price list, not
  the decision. The sponsor still needs to pick, informed by cost-vs-k above.
- The mid-run solver fix's root cause (why scipy 1.18.1's HiGHS wrapper hangs with no `options`)
  was not chased further than what's needed to confirm the fix is correct and narrow.

## Reproduce

```bash
.venv/bin/python3 tools/run_draw.py instance_descaled_v2.json.gz --k 14-22 --seeds 0-9 \
  --workers 8 --out battery/results/runs_<date>/baseline
bash docs/artifacts/runs/run_all.sh      # all 15 runs
bash docs/artifacts/runs/make_maps.sh    # 15 power-diagram maps at k=18
.venv/bin/python3 docs/artifacts/runs/build_artifact.py --date <date>
```
