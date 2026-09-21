# Region pin-cost catalogue (recomputed 2026-09-04)

`tools/run_draw.py --k 14-22 --seeds 0-9`, 15 runs; v2 whole instance, total M 8,523.2, target
at k = 18 is 473.5. Δ columns are against the unpinned baseline at k = 18 (nash
`110.88310108262327`, stage 2 `95.75519165924106`), in nats. They are exact at fixed k because
every scenario partitions the same total into the same number of districts.

- `fix`: a closed district, never touched by the solver, k reduced by one.
- `anchor`: open, locked in; the solver fills the rest by water-fill.
- `nash Δ` is identical between `fix` and `anchor` for every region (both pin the same mass to
  the same district); `stage-2 Δ` diverges and is not always negative.

| region | pinned M | vs target (k=18) | natural k | fix: nash Δ | fix: stage-2 Δ | anchor: nash Δ | anchor: stage-2 Δ |
|---|---:|---:|---:|---:|---:|---:|---:|
| CALIFORNIA | 1,953.8 | +312.6% | 4.36 | -2.037 | -2.126 | -2.037 | -2.217 |
| TEXAS | 972.1 | +105.3% | 8.77 | -0.368 | -0.430 | -0.368 | -0.412 |
| MIDWEST | 876.5 | +85.1% | 9.72 | -0.257 | -0.224 | -0.257 | -0.223 |
| NEWYORK | 849.6 | +79.4% | 10.03 | -0.229 | -0.409 | -0.229 | -0.413 |
| FLORIDA | 661.9 | +39.8% | 12.88 | -0.068 | **+0.029** | -0.068 | -0.019 |
| SOUTHWEST | 606.8 | +28.1% | 14.05 | -0.036 | -0.089 | -0.036 | -0.013 |
| CAROLINAS | 535.2 | +13.0% | 15.92 | -0.008 | -0.013 | -0.008 | +0.012 |

This table feeds the sponsor's A12 question (which states, if any, are hand-drawn).

Related: `mem:facts/nats-headline`.

Source: `main:STATE.md` `## Facts` (a3924e8).
