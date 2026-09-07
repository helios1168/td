# State-border snapping of the committed k=18 power-cell draw — build plan

*Written 2026-09-06 for a fresh session to execute. Nothing here is built yet. Resume from
`STATE.md` `## Now`, then this file; branch `worktree-vbl` at `.claude/worktrees/vbl` is the
working tree (locked, hand-made).*

## Context and decisions

The committed k=18 map (`battery/results/draw_k18_v2_20260904/k18`, seed 2) is balanced to
1.29% spread and certified at 8.2e-5 nats against the every-partition ceiling. Its district
borders often run close to state lines without lying on them; 9.46% of mass sits in a district
whose owner set (defined below) belongs to another state.

Sponsor decisions, 2026-09-06:

- Move those borders onto state lines. Balance may be sacrificed for it, with a working cap
  of 10% spread; the run reports where 10% is not enough and the sponsor decides there.
- The state-atom route is abandoned. Do not spend anything on it.
- Exact graph contiguity is not required. Visual (map) contiguity is the bar.
- Warm-start from the committed seed-2 map only, so the result reads as the same map with
  its borders moved; no fresh seeds.
- Home state of a district = the state holding the plurality of its mass.

The VBL options in `docs/CHANNEL_NOTE.md` §8 (reviewed and corrected the same day) are not
part of this; Option B was for the atom route and is retired with it.

## What the numbers say a 10% cap buys

τ = 473.513 (v2, k = 18). State masses in τ units: CA 4.126, TX 2.020, NY 1.794, FL 1.398,
NJ 1.037, IL 0.677, AZ 0.550, NC 0.546, PA 0.534, MI 0.465, VA 0.420, OH 0.411, GA 0.390,
CO 0.337; forty states below 0.26; unknown state (`??`, 32 zips) 0.070.

Committed draw, district → states by mass share (≥1%): D01 NY 79 NJ 21 · D02 CA 57 AZ 29 NV 13
· D03 TX 97 LA 3 · D04 NY 62 CT 18 MA 10 NH 5 RI 2 NJ 2 · D05 PA 53 MD 23 NY 11 NJ 9 DE 3 ·
D06 CO 34 AZ 26 UT 22 TX 6 NM 3 NE 3 OK 2 KS 2 · D07 FL 100 · D08 NC 46 VA 42 DC 4 WV 3 MD 2
· D09 MI 45 OH 37 IL 9 IN 8 · D10 CA 99 · D11 IL 52 MN 21 WI 12 IA 5 SD 3 ND 3 NE 2 · D12
NJ 72 NY 27 · D13 MO 17 LA 17 IN 13 KY 13 AL 10 TN 7 IL 6 AR 4 GA 4 OH 4 MS 2 KS 1 · D14 CA 100
· D15 FL 39 GA 35 SC 16 NC 9 AL 1 · D16 TX 99 · D17 CA 61 WA 25 OR 6 ID 4 NV 4 · D18 CA 96
ID 2 HI 1.

Where 10% suffices: TX (2.02τ, two districts at +1%); FL/GA/SC (D15 → ~0.94τ); the CA block
(four pure-CA districts at about +7%); the twelve-state D13 (→ ~1.0τ). Where it does not:
NY+NJ+New England is 3.19τ for three districts (+6%) while PA+MD+DE is 0.82τ (−18%), so a
border stays inside NY or NJ against PA; D06 without AZ and its TX sliver is 0.68τ (−32%), so
AZ stays split. With 52 states and 18 districts a few states must be split; the LP picks the
fewest at the cheapest place, and the table lists them per δ.

## Model

Keep the transportation LP of `td/solvers/centers.py` and change two things in it. Both keep
it a transportation problem: duals, and at most k−1 split zips (Lemma 6 of the channel note).

- **Owner set per state.** From a labelling: `home(j)` = the state holding the plurality of
  district j's mass. `O(s) = {j : home(j) = s}`; if empty, `O(s)` is the single district
  holding the most of state s's mass. A state with its own districts is split only among
  them; a state without one lies wholly inside one district. Zips with unknown state have no
  owner and pay no penalty. (Home-per-district alone would leave VT splittable between a NY
  district and a MA district; the owner set is what closes that.)
- **Penalised cost.** `cost_zj = M_z · (d²(z, c_j) + λ · 1[j ∉ O(state(z))])`, λ given as a
  multiple of the committed draw's mass-weighted mean d² (`compactness / ΣM`), so it is
  scale-free. λ = 100 is effectively hard: cross only where the band forces it, at the
  cheapest border.
- **Band.** `τ(1−δ) ≤ Σ_z M_z x_zj ≤ τ(1+δ)`. δ is the balance sacrifice. At δ = 0 CA's
  remainder (4.126τ is not a multiple of τ) must cross somewhere; at δ = 5% the CA districts
  run light and nothing crosses.
- **Alternation from the committed map.** labels → owner sets → banded, penalised LP →
  recentroid (`centers._centroids`), 10 rounds, stop early when labels repeat. No Nash polish
  (`centers.improve`) at λ > 0: it would pull zips back across borders for balance. Every
  iterate is saved; the last (or the repeat) is the cell's answer.
- **Baseline with no LP.** Pure snap of the committed map: every zip outside its state's
  owner set moves to the nearest owner district by d² to centre. Zero parameters; shows what
  snapping alone costs in spread.

## Grid (overnight, seed 2 only)

- δ ∈ {0, 1%, 2%, 5%, 10%} at λ = 100.
- λ ∈ {1, 10} at δ = 2%, to show the soft regime.
- Rows 0 and 1: the committed map, and the pure-snap baseline.

Per cell, on the completed instance (coordinate-less zips placed by
`channel.place_by_state`): `spread_rel`, `max_dev_rel`, nash and gap to `k·log(M/k)` on the
whole-instance base, mass share outside owner sets, number of districts with >1% of their mass
outside their home state, the states split across ≥2 districts with ≥1% of the state's mass
each (excluding states whose own owner set has ≥2 districts: CA, TX, NY, FL, NJ), zips changed
vs the committed map, compactness `ΣM d²`, `n_fractional`, stage-2 value (`channel.stage2`).
Output `grid.csv` and `grid.md`, one `draw.csv` per cell, one `iterates/` directory per cell.

Maps per cell, by subprocess to `tools/us_maps.py` as `app/runner.py::render_maps` does:
`--districts` (dots) and `--regions-voronoi` (catchment fill). **Not `--regions`**: the
unpenalised power diagram no longer matches the labelling. The penalised cells are a power
diagram per state; drawing that exactly is daytime work.

## Files

**New `td/solvers/state_borders.py`.** Keeps `centers.py`'s "pure functions on arrays"
contract; states enter as an int array per zip.

- `owner_sets(labels, state_idx, M, k, n_states) -> (home (k,) int, owners (n_states, k) bool)`
- `penalty_matrix(state_idx, owners, lam_abs) -> (n, k) float`, 0 for unknown state
- `pure_snap(xy, M, labels, state_idx, k) -> labels`
- `refine(xy, M, labels0, state_idx, k, *, lam_rel, delta, rounds=10) -> dict` with `labels`,
  `centers`, `iterates`, `rounds_used`, `converged`, `n_fractional`, and `centers.metrics`.

**Edit `td/solvers/centers.py`**, surgically:

- `assign(xy, M, centers, targets=None, *, penalty=None, band=0.0)`: `d2 = _dist2(...) +
  penalty` when given; when `band > 0` the mass rows become two `A_ub` rows per district
  (`(1−band)·t ≤ · ≤ (1+band)·t`) instead of the `A_eq` row. `penalty=None, band=0.0` must
  reproduce the current path bit-for-bit (same matrices, same solver call), so the committed
  draw stays reproducible.
- `power_labels(xy, centers, weights, penalty=None)`: `+ penalty` in the argmin.
- `power_weights(..., penalty=None)`: `+ penalty` in `d2`, `labels` via the penalised
  `power_labels`. No band here tonight.

**New `tools/state_borders.py`**, the CLI driver. Arguments: instance, `--draw <committed
draw.csv>`, `--k 18`, `--delta 0 0.01 0.02 0.05 0.10`, `--lam 100`, `--soft-lam 1 10
--soft-delta 0.02`, `--rounds 10`, `--out`, `--geo-cache`, `--maps/--no-maps`. Reuse
`run_draw.coordinates`, `run_draw.complete` / `relabel` / `summary_rows`, `us_maps.read_draw`,
`channel.place_by_state`, `channel.stage2`, `centers.metrics`. Committed labels: `D01..D18` →
`0..17` over zips with coordinates; coordinate-less zips re-placed by `complete` per cell.
`lam_abs = lam_rel × committed compactness / ΣM`, computed once.

**Stretch, only if under ~30 lines:** in `tools/us_maps.py` `voronoi_cells`, intersect each
zip's cell with its own state polygon (`geo.states_outline`) behind a `--clip-states` flag,
default off, so `--regions-voronoi` borders lie on state lines where the labelling respects
them. Existing figures unchanged.

**Tests.** `tests/test_centers.py`: `assign` with `penalty=None, band=0` equals the old
result exactly on a random instance; a large penalty forces every zip to an owner district on
a two-state toy; a band is respected on the LP solution. New `tests/test_state_borders.py`:
`owner_sets` gives the plurality rule and the no-home fallback on a hand-built three-state,
two-district toy; `pure_snap` moves exactly the non-owner zips; `refine(lam_rel=0, delta=0)`
from the committed labels reproduces `assign`'s Lloyd step.

## Running it

Data is gitignored and lives in the hub only. Run the worktree's code against hub data with
absolute paths and no `cd`:

```
/Users/ntlee/projects/td/.venv/bin/python3 -u \
  /Users/ntlee/projects/td/.claude/worktrees/vbl/tools/state_borders.py \
  /Users/ntlee/projects/td/instance_descaled_v2.json.gz \
  --draw /Users/ntlee/projects/td/battery/results/draw_k18_v2_20260904/k18/draw.csv \
  --geo-cache /Users/ntlee/projects/td/data/geo \
  --out /Users/ntlee/projects/td/battery/results/borders_k18_v2_20260907 --maps
```

Smoke first: one cell (`--delta 0.02 --lam 100 --rounds 3 --no-maps`) and check the row is
sane. Then the full grid in the background, logging to `run.log` under `--out`. LPs are
sub-second; maps are ~2 min per cell × 9 cells.

## Verification

1. `/Users/ntlee/projects/td/.venv/bin/python3 tests/run_all.py` from the worktree: 275 plus
   the new tests, 0 fail. The bit-for-bit test guards the committed draw's reproducibility.
2. Smoke cell: outside-owner share falls and spread rises to at most δ plus the split-zip
   rounding, versus the committed row.
3. Full grid: `grid.md` has 9 rows; the δ = 0, λ = 100 row has outside share ≤ committed; the
   δ = 10% row lists the residual split states (expected: NY or NJ against PA, AZ, perhaps one
   more). Maps present per cell.
4. Morning report: the table, the residual-split-state list per δ, and the three maps the
   sponsor picks between (baseline, δ = 5%, δ = 10%).

## Out of scope

Per-state power-cell fill (new clipping geometry in `us_maps.py`); other seeds; Route B;
Options A–D of the channel note; the atom route in any form. Commit on `worktree-vbl`; merge
to `main` only when asked.
