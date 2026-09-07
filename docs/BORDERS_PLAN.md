# State-border snapping of the committed k=18 power-cell draw — build plan

*Written 2026-09-06 for a fresh session to execute. Nothing here is built yet. Resume from
`STATE.md` `## Now`, then this file; branch `worktree-vbl` at `.claude/worktrees/vbl` is the
working tree (locked, hand-made).*

## Context and decisions

The committed k=18 map (`battery/results/draw_k18_v2_20260904/k18`, seed 2) is balanced to
1.29% spread and certified at 8.2e-5 nats against the every-partition ceiling. Its district
borders often run close to state lines without lying on them; 9.15% of mass sits in a district
whose owner set (defined below) belongs to another state (measured by
`tools/borders_report.py` on 2026-09-07 with the owner-set rule as coded; the 9.46% quoted on
2026-09-06 came from a hand count and is superseded).

Sponsor decisions, 2026-09-06:

- Move those borders onto state lines. Balance may be sacrificed for it, with a working cap
  of 10% spread; the run reports where 10% is not enough and the sponsor decides there.
- The state-atom route is abandoned. Do not spend anything on it.
- Exact graph contiguity is not required. Visual (map) contiguity is the bar.
- Warm-start from the committed seed-2 map only, so the result reads as the same map with
  its borders moved; no fresh seeds.
- Home state of a district = the state holding the plurality of its mass.

Two tracks, run side by side overnight, answering different questions:

- **Track 1, the penalised LP**: snap the committed map's borders zip by zip, owner sets
  inherited from the map. Cheap, uncertified, keeps the map recognisable.
- **Track 2, the state-level minimum-splits MILP**: for each δ, the certified minimum number
  of states that must be split, and which, with visual contiguity by construction at the state
  level; then the zip-level realisation inside each split state by the same transportation LP.
  This is the one piece of the VBL line that fits the problem as now framed: the whole-unit
  (minimum county splits) objective of Shahmizad & Buchanan, at a size (52 states, 18
  districts, the 49-node rook graph) where all of their machinery is trivial. Added 2026-09-06
  evening after the question "is VBL still viable"; Options A–D of `docs/CHANNEL_NOTE.md` §8
  stay parked, and Option B went with the atom route.

The two share the band δ, the committed centres, the completion step and the metrics, so the
morning table shows both per δ.

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

## Track 1 — the penalised, banded transportation LP

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

## Track 2 — the state-level minimum-splits MILP

Level 1 decides, per δ, which states split and how their mass is shared; level 2 realises it
at zip level. `s` ranges over the 49 lower-48 states plus DC (AK, HI and the 32 `??` zips,
0.09τ together, are excluded from the MILP and placed afterwards by `channel.place_by_state`);
`M_s` is the state's mass; `c_j` the committed draw's 18 centres, fixed; `D_sj = Σ_{z∈s} M_z
d²(z, c_j) / M_s` the exact moment of state s about centre j, precomputed.

```
min   Σ_s (Σ_j z_sj − 1)  +  ε Σ_s Σ_j M_s D_sj y_sj        (split count; compactness tie-break)
s.t.  Σ_j y_sj = 1                       ∀ s                (all of s placed)
      0 ≤ y_sj ≤ z_sj,  z_sj ∈ {0,1}     ∀ s, j             (z marks contact)
      τ(1−δ) ≤ Σ_s M_s y_sj ≤ τ(1+δ)     ∀ j                (the band)
      {s : z_sj = 1} connected in the state rook graph  ∀ j (contiguity)
```

- **ε** is lexicographic: `ε = 0.5 / Σ_s M_s · max_j D_sj`, so the whole compactness term is
  worth under half a split at every feasible `y` and never buys one. (The first draft scaled by
  the committed map's own `y⁰`; `docs/VERIFY_state_splits.md` refuted that with a four-state
  path where it returns two splits when zero is optimal. The bound must hold over every `y`,
  not only at `y⁰`.)
- **Contact means mass.** `y_sj ≥ η · z_sj` with `η = 0.01`, the same 1% threshold the split
  report uses. Without it `z_sj = 1, y_sj = 0` buys a bridge state for one split while the
  district it "connects" is disconnected in fact (`VERIFY_state_splits.md`, claim 1b).
- **Contiguity** by VBL's single-commodity flow (`scf`), compact, no lazy callbacks and so
  none of the trap-14 SCIP configuration: per district a variable root `r_sj ≤ z_sj`,
  `Σ_s r_sj = 1`, flow on each rook edge bounded by `(N−1)·z_uj` and `(N−1)·z_vj`, and net
  inflow at s at least `z_sj − N·r_sj` (N = 50). Districts are anonymous; the fixed distinct
  centres in the tie-break break the k! symmetry in practice at this size.
- **Size**: S = 49 (lower 48 plus DC): 882 binaries `z`, 882 binary `r` (a continuous root
  admits disconnected sets with components under N/2, so `r` stays integral), 882 continuous
  `y`, 2 × 107 × 18 flow variables; 11,317 rows as built (the `η` block adds 882, and the
  arc capacity is written per directed arc against each endpoint, 3,852 rows per end, which
  is the weaker of the two scf forms; `docs/CODEVERIFY_state_splits.md` 6a).
  `scipy.optimize.milp` on HiGHS with `mip_rel_gap = 0.0` (trap 12).
- **It does not close.** "Seconds" was wrong. On the real instance at δ = 10% HiGHS finds
  17 splits at 1.5 s, 8 at 60 s, 7 at 600 s, and the dual bound sits at 6 from 120 s on;
  the reported `mip_gap` is over an objective that carries the constant S = 49, so a 1.8%
  gap is one whole split. The certified statement per δ is therefore an interval, "between
  ⌈bound⌉ and the incumbent", not a number. `solve(strict=False)` returns the incumbent with
  `status = "time_limit"` for this reason. Anchoring each district to its committed home
  state (`--anchor-homes`, `build_milp(anchors=)`) names the districts and removes the k!
  symmetry, matching sponsor decision (4), but did not close the gap either at 120 s (8
  splits, 1.75%); the weak part is the flow relaxation, not the symmetry. The grid runs both
  forms, free and anchored, at 600 s per δ, five δ in parallel. Tightening (pair-form arc
  capacity, a per-district state-count bound in place of N − 1) is daytime work.
- **The committed map is not a feasible warm start.** Its state composition passes the band
  at δ = 1.3% (max deviation 1.16%) but fails contiguity: D09 holds crumbs in ND, NY and TN
  below 1% that no path of its own states reaches, and D18's CA piece is cut off from ID
  and MT; 28 state–district contacts sit under η. The sanity row prints this and does not
  solve for it. The upper bound on the split count at δ ≥ 1.3% that the plan expected from
  `y⁰` does not exist.
- **Warm start / sanity**: the committed map's composition `y⁰` was expected to be feasible
  at δ = 1.3%; it is not (contiguity fails, see "The committed map is not a feasible warm
  start" below). The sanity row reports the band and connectivity checks directly.
- **Balance pass, lexicographic.** The MILP uses the whole band wherever that saves a split,
  so at δ = 10% it returns a 10% imbalance somewhere even when the chosen splits permit 3%.
  After the MILP, fix `z` and re-solve for `y` in two LPs: first minimise the maximum
  deviation `t ≥ |Σ_s M_s y_sj − τ|`, then, with `t` held at its optimum, minimise the spread
  `u − l` where `u ≥ Σ_s M_s y_sj ≥ l` for every `j`. The second LP is needed: max deviation
  and spread are different numbers (`maxdev ≤ spread ≤ 2·maxdev`, since deviations sum to
  zero), and a single LP can return a wider spread at equal max deviation
  (`VERIFY_state_splits.md`, claim 3b). δ is then a cap, and the shares are the tightest
  balance those splits allow. Report the MILP's spread and the pass's.
- **Level 2**: for every split state s, one `centers.assign(xy_s, M_s, c, targets = y_sj M_s)`
  over that state's zips (the `targets=` argument already exists; a 0 target means "nothing
  from this state", which `assign` already honours) — convex power cells inside the state.
  Every unsplit state goes whole to its district. Then **five Lloyd rounds inside each split
  state**: recentroid every district touching the state from its full membership (whole
  states included), re-solve the state's LP, stop when the state's labels repeat. The
  committed centres were placed for the old shares (D02 is 57% CA plus AZ and NV, D17 61% CA
  plus the Northwest) and can sit in the wrong place for the piece they now own; the rounds
  make the CA/TX/NY cuts compact for the shares actually chosen. Then completion and metrics
  as Track 1. As built, `realise` moves the shared centre array as it goes, so a later split
  state is cut against centres an earlier one already moved: deterministic, order-dependent,
  and not what the plan said (`CODEVERIFY_state_splits.md`, non-verdict findings).
- **Cleanness per split state**, reported: districts touching it, split-zip count (at most
  one fewer than the districts touching), and border-segment count from `us_maps` (the
  committed map has 1,591, the snapped labelling 636). Named cut lines (Manhattan whole, the
  Hudson as the NY/NJ line, county boundaries inside CA) are not in this plan; they need a
  zip-to-region pinning layer at level 2 or county-aggregated units, and the morning maps
  decide whether either is needed.
- **Output per δ**: split count, the split states with their `y` shares, the `z` composition,
  `draw.csv`, and the same metric row as Track 1 (spread will sit at ≤ δ plus the split-zip
  rounding).

New `td/solvers/state_splits.py` (`build_milp`, `solve`, `balance_pass`, `realise`) and a CLI
`tools/state_splits.py` with the same instance / draw / geo-cache / out arguments as Track 1's
driver plus `--incumbency-tiebreak`; tests on a hand-built 6-state, 2-district toy (min splits
= 1 when the band forces it, 0 when it does not; contiguity refuses a disconnected grouping;
the balance pass never changes `z` and never widens the spread).

## Stage 2 (the assignment problem) in this plan

Stage 1 is purely opportunity, by design: Proposition 2 of the channel note makes Nash on a
common measure equal to balance, and the rep-to-district matching is stage 2. Neither track
optimises for staffing. Both **measure** it: every cell runs `channel.stage2` and the table
carries the stage-2 value, the assignment and the unmatched reps beside the committed map's,
so the staffing cost of each δ is visible. The incumbency premium is 0.72 to 0.78 nats and not
soft (`STATE.md` `## Facts`), and moving borders onto state lines moves book across them too.

One optional lever, behind a flag and **off by default**: an incumbency tie-break at level 2.
With the committed map's stage-2 assignment `rep(j)` known from `metrics.json`, add to the
cost of zip `z` in district `j` the term `−μ · S_{rep(j)}(z)`, `S` the rep's book at `z`
(`model.books`), with `μ` scaled so the whole term is under 1% of the compactness cost, so it
only decides near-indifferent zips. Run the grid with it off; run the two shipped δ cells again
with it on and report the difference in stage-2 value and in the maps. A book-aware objective
at stage 1 (the joint problem, §5.2 of the note) is out of scope and undecided.

## Grid (overnight, seed 2 only)

Track 2: δ ∈ {0, 1%, 2%, 5%, 10%}, one MILP each, then the balance pass and level 2.

Track 1:

- δ ∈ {0, 1%, 2%, 5%, 10%} at λ = 100.
- λ ∈ {1, 10} at δ = 2%, to show the soft regime.
- Rows 0 and 1: the committed map, and the pure-snap baseline.

Per cell, on the completed instance (coordinate-less zips placed by
`channel.place_by_state`): `spread_rel`, `max_dev_rel`, nash and gap to `k·log(M/k)` on the
whole-instance base, mass share outside owner sets, number of districts with >1% of their mass
outside their home state, the states split across ≥2 districts with ≥1% of the state's mass
each (excluding states whose own owner set has ≥2 districts: CA with 5, TX, NY and FL with 2
each; NJ has one owner district, D12, so it is not excluded), zips changed
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
3. Full grid: `grid.md` has 9 Track-1 rows; the δ = 0, λ = 100 row has outside share ≤
   committed; the δ = 10% row lists the residual split states (expected: NY or NJ against PA,
   AZ, perhaps one more). Maps present per cell.
4. Track 2: the MILP at δ = 1.3% reports a split count ≤ the committed map's (its own
   composition is feasible there); the count is non-increasing in δ; every district's `z`
   set is connected on the rook graph; the balance pass leaves `z` unchanged and its spread is
   ≤ the MILP's; level-2 spreads sit within the pass's plus the rounding; the Lloyd rounds
   inside a split state never raise its compactness cost.
5. Morning report: one table with both tracks per δ, the split-state list per δ from Track 2
   beside Track 1's residuals, and the maps the sponsor picks between (Track 1 baseline,
   Track 1 and Track 2 at δ = 5% and 10%).

## Out of scope

Per-state power-cell fill (new clipping geometry in `us_maps.py`); other seeds; Route B;
Options A–D of the channel note; the atom route in any form (Track 2 is not it: the solver
chooses which states split, the band caps spread by construction, and the realisation inside
a split state is the committed map's own power-cell LP). Commit on `worktree-vbl`; merge to
`main` only when asked.
