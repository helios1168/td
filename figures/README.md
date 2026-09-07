# Figures

Maps are primary artifacts here, so this directory is tracked and its contents are regenerated
with `tools/us_maps.py` alongside the change that motivates them. Renderings made by the
Streamlit app are not reviewed artifacts and go under `battery/results/app/figures/` instead.

## The headline map

Track 2, anchored, δ = 5%: the shipped map. Eight state splits, certified minimal under the
anchors, with California in five districts, New York three, Texas two and Florida two.

- [`borders_track2_anchored_d05_voronoi.png`](borders_track2_anchored_d05_voronoi.png) — the
  territory map. Each ZIP's catchment is clipped to its own state, so this is the rendering that
  shows where the districts meet the state borders.
- [`borders_track2_anchored_d05_districts.png`](borders_track2_anchored_d05_districts.png) — the
  same draw as dots, with bubble area proportional to opportunity.
- [`headline/`](headline/) — one close-up per district, with a share and coverage table.

Both overview maps carry each district's share of national opportunity to two decimals. An equal
share is 5.56%; the map runs from 5.35% to 5.85%. Districts too small to sit under their own
label, D01, D14 and D18, take their label to open ground and keep a leader line back.

The end-to-end write-up, from the committed draw to this map, is
[`docs/HEADLINE.md`](../docs/HEADLINE.md).

## Overrides

Explorations, not proposed maps. Each one holds the headline as its reference and reports the
difference.

- [`overrides/ca4_d10/`](overrides/ca4_d10/) — California capped at 4 districts at a 10% band.
  New York falls to two districts and New Jersey splits, so the total number of splits drops
  from 8 to 7, at the cost of a spread of 16.70% against the headline's 8.98%.

## Older material

`runs_20260904/`, `sweep_20260902_s10/`, `u8_band/` and `u8_band_v2/` hold earlier sweeps. The
loose PNGs at this level (`districts.png`, `district_regions*.png`, `opportunity.png`,
`firm_a.png`, `firm_b.png`, `contestability.png`) belong to the committed power-cell draw and
the instance itself, not to the borders work.
