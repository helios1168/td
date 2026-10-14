2026-10-14 · branch m5-studio/six-files · commit 572bd60 · Agent: D-sixfiles (claude-sonnet-5-5)

# Summary: main-map overnight grid design (rpiv design, 2026-10-13)

Original (247 KB, mostly code fences): `docs/archive/rpiv/2026-10-13_01-09-34_main-map-overnight-grid-design.md`, written on `m5-studio/national-overnight` at e82d6a4. Parent: the research note `notes/2026-10-12_main-map-joint-wifi-grid-research.md`. The result is in `docs/RESULTS.md` ("Main-map overnight grid 2026-10-13").

## What it designed

21 main-map points (five WIFI structures: ne_plains, west8, nw49, nw34, w1, times main-map K totals 48-52) drawn by the `set125.sh` chain (support master, draw, repair), unsealed on the full polygon graph, on m5 (15 points) and m2 (6 west8 points). A Python launcher, `tools/exp/contig/overnight.py` (`run`, `collect`, `morning`, `smoke`), writes `GRID.json` and `MORNING.md/.pdf`.

## Decisions it recorded (D1-D15)

- D1 lands on the topic branch; merging to main is the owner's.
- D2/D3 masses become $M in a derived extract `instance_descaled_usd.json.gz` (gitignored) at the E1 rates, so master, draw, repair and audit balance dollars with no band-row change (G5/B1); `export_long.py` reverses to `m_rel`.
- D5 a per-district dollar gate in `tools/looks/score.py` (national $1,000-1,437.5M, WH $850-1,150M, FI $765-1,035M, WIFI $850-1,150M, a whole-state WIFI district up to $1.6B).
- D6 gap-width audit (`d312834`) lands with `check_m1(gap_width=)` and `score.m1_both`; maps are gated with the flag on and both verdicts reported (G3).
- D7 #133 land-balance term in `draw.py`, soft penalty at R = 10, reported in `land.csv`.
- D8-D14 launcher policy: plan 10 min per channel, draw 75 min with one retry at delta + 0.05, repair pass 2 only if M1 still fails, a dollar-gate failure re-runs once at K-1 or K+1, renders of $M runs use a unit `fac`.
- D15 #111, #112, #119 stay open and are taken as assumptions, written into `GRID.json` and the `MORNING.md` header.

## Not built

Main-map merge or state sealing, a dollar repair arm, the #131 dry-land gap builder, the G2 thin-unit floor, any Manhattan rule on the main map, a land term in `repair.py`, and edits to PROBLEM.md or the mandates (the new dollar windows were left for the owner to file).
