# Map and power-cell contiguity of the committed k = 18 draw (2026-09-06)

Draw `draw_k18_v2_20260904/k18`, 3,704 plotted zips, total M 8,468.3. These measurements
predate the 2026-09-09 move to real ZCTA polygons (`mem:geo/zcta-geometry`) and used the 2020
gazetteer.

**Voronoi catchment dissolve** (`tools/us_maps.py --regions-voronoi`, worktree `ca5-map`):
D02's largest piece is 48% of its territory, D11 53%, D17 55%, D06 73%; D01/D03/D08/D09/D10/
D13/D14/D16 (plus near-solid D07/D15/D18) are 98 to 100% one piece.

**Power cells.** Ceiling `k·log(M/k)` = 110.766768 (a different base from the atom ceiling).
- Committed draw: 258 zips (7.0%, 1.66% of M) outside their own power cell at own-masses
  targets and 266 (7.2%) at exactly-equal-split targets. These are two measurements; before
  2026-09-06 they were quoted as one number. Spread 1.2902%, `Σ log M` 110.766686, gap 0.000082.
- Snapped at equal-split targets: 0 outside by construction, spread 4.0041%, gap 0.000724.
- Best of 20 snap then recentroid iterates (iteration 15): spread 2.1051%, `Σ log M` 110.766485,
  gap 0.000283. There is **no fixed point**: 20 iterations, no exact repeat, non-monotone, band
  spread 2.1 to 5.6%, gap 0.00028 to 0.00128.
- Split zips: 17 = `k-1` at both target choices, carrying 17.03% of a mean district at
  equal-split and 22.08% at own-masses.
- Six cells are under 1% of the map (D14, D01, D12, D10, D07, D18); "three metro slivers" was
  the k = 13 v1 count.
- Largest contiguous piece by area, snapped: D01 55%, D09 96%, D14 97%, D10/D13 98%, D07/D08
  99%, twelve districts 100%; committed: nine districts under 80% (min D14 51%). **Area
  misreports dense metros**: by mass the snapped worst is D17 92.72% and D01 is 99.86%; the
  committed worst is D09 90.03%. The two orderings disagree. D01's second part by area is one
  rural zip about 85 km from its NY/NJ core; moving it would make D01 one piece at negligible
  cost but put one zip outside its own cell, so the draw was left alone and both denominators
  are reported.
- Border segments 1,591 committed, 636 snapped.
- **The zero is relative to one diagram.** Rebuilt from the snapped labels, 16 of 3,704 fall
  outside at own-masses targets and 15 at equal-split, and the split count drops from 17 to 10.
  `--regions-fixed` holds centres and weights and displays the guarantee; every other
  rendering recentroids. See `mem:model/corrections`.

Source: `main:STATE.md` `## Facts` (a3924e8).
