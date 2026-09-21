# The shipped map (measured 2026-09-07)

`docs/HEADLINE.md` is the end-to-end write-up. The recommended cell is Track 2 anchored
δ = 5% on the whole v2 instance (`mem:facts/state-border-snapping`).

- Level-1 ground set: 49 units, mass 8,468.3, **tau = 470.459**. States over tau:
  **CA 4.153, TX 2.026, NY 1.805, FL 1.392, NJ 1.043** (`--dump-state-shares`). Do not compare
  these with the state-atom ratios (`mem:facts/state-atoms-retired`): that base keeps the
  coordinate-less zips and divides by tau = 473.513.
- **Realised maximum deviation is 5.25%, outside the nominal 5% band.** The 4.68% that
  satisfies the band is `pass_max_dev`, a state-level quantity on continuous shares, measured
  before `realise` makes whole zips of them and before AK, HI and the coordinate-less zips are
  placed. `grid.csv` carries all three side by side with nothing marking which is authoritative.
  Say "5.25% realised", never "within 5%".
- Recomputed independently from the instance and the shipped draw: stage 2 95.78785, spread
  0.089824, Nash 110.873686, 776 zips changed, every zip assigned once, mass conserved to
  floating precision. Level-1 objective 57.00483235477814, 8 splits, gap 0, byte-identical
  `draw.csv` on a rerun through the override code with no caps.
- On the CONUS set the same map reads spread 12.02%, max deviation 6.26%
  (`mem:facts/conus-track2-grid`).

Per-state caps: `mem:facts/per-state-caps`.

Source: `main:STATE.md` `## Facts` (a3924e8).
