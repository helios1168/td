2026-10-14 · branch m5-studio/six-files · commit 572bd60 · Agent: D-sixfiles (claude-sonnet-5-5)

# Summary: main-map overnight grid plan (rpiv plan, 2026-10-13)

Original (247 KB, almost all code to paste): `docs/archive/rpiv/2026-10-13_04-04-35_main-map-overnight-grid-plan.md`, written on `m5-studio/national-overnight` at 5939e04. Parent design: `notes/2026-10-13_main-map-overnight-grid-design.md`. The result is in `docs/RESULTS.md` ("Main-map overnight grid 2026-10-13").

## The seven phases (one per design slice, each depends on the earlier ones)

1. Dollar-scaled extract and `export_long` reversal: `tools/exp/contig/dollarize.py`, `export_long.py`, `tests/test_dollarize.py`.
2. Per-district dollar gate: `tools/looks/score.py`, `tests/test_looks_score.py`.
3. Gap-width audit: `td/audit.py`, `tests/test_neck_gapwidth.py`, `score.m1_both`.
4. #133 land term and `land.csv`: `draw.py`, `run.py`, `land.py`, `tests/test_land.py`.
5. Grid launcher core: `tools/exp/contig/overnight.py`, `tests/test_overnight.py`.
6. Collect, morning report and smoke: same files plus `docs/CODE_MAP.md` rows.
7. Pre-launch gates: the five specs `scenarios/main_{ne_plains,west8,nw49,nw34,w1}.toml`.

## Desired end state

Per Studio: build the $M extract (`dollarize.py`), check it is gitignored, run `overnight.py smoke --point ne-48-bal` and compare the two Studios; launch with an 8 h hard stop (m5 15 points, m2 6); in the morning run `collect` and `morning` on m5; `tools/mandates/check.py` gates any run folder.

## Not doing

Merge or sealing, a dollar repair arm, the #131 gap builder, the G2 floor, a repair land term, any edit to PROBLEM.md or the mandates, any merge to main, shortlist registration (a morning step after review), and any resolution of #111, #112, #119 or the #133 ladder.
