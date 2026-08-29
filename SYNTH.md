# Synthetic battery and the census stress test

**Read `HANDOFF.md` first.** This records the extension of the synthetic data beyond
`zip50.py`'s single fixed instance, and what stress-testing `T.census()` against it
found — including one bug in shipped code, now patched. Written before any real ZCTA
data has been loaded; the point is that the instruments are calibrated before the one
shot at the live gate.

---

## 1. Why extend the synthetic data

`zip50.py` generates one instance: 50 zips, no rep structure at all (implicitly one A
rep vs one B rep), corr(A_z,B_z) frozen at +0.685. Every review finding rests on it.
The census critique (review objection 6 / kill criterion 1) is precisely that the real
national problem will NOT look like this — it will decompose into overlap components,
most likely dense ones — and none of the four kill criteria could even be instantiated
on the old instance, let alone swept.

`code/synth.py` generates instances matching `territory.py`'s schema, with each dial
aimed at a named gate:

| dial | gate |
|---|---|
| `alpha` (rep-territory alignment) | kill criterion 1: B-rep territories interpolate from copied-from-A (`alpha=1`, clean 1-1 pairs) to independent (`alpha=0`, dense components) |
| `sliver` (boundary noise) | the census `min_share` default — overlap edges near the trim threshold |
| `rho_books` in [-1,1] | kill criterion 4: realized corr(A_z,B_z) from ~0 to ~0.93; negative values cancel the shared-market floor; realized corr reported in `G.graph["corr_AB"]` |
| `n_states` | kill criterion 3: state-scoped edges vs contiguity |
| `saturation`, `tight` | pointwise headroom stress |
| `tail` | heavy-tailed M_z, unlike zip50's smooth mixture |
| `cap_corr` | objection 2 follow-up: per-rep capacity field with controllable correlation to book size |

Geography is a metro-cluster + rural-scatter mixture with a real planar adjacency
graph (trimmed Delaunay, reconnected), so `validate()`'s island and component checks
finally have something to look at. Six named scenarios (`SCENARIOS` /
`scenario(name)`): S1_aligned, S2_entangled, S3_slivers, S4_separate, S5_states,
S6_tight — each instantiating one gate. Sanity anchor: S1 censuses as 100% 1-1 pairs;
S4 realizes corr(A,B) ≈ −0.10.

---

## 2. The finding that mattered: census() could only ever answer "dense"

**As shipped, `census()` trimmed weak edges only when *labelling* a component's shape
— never to *split* the component.** One sliver edge therefore glued two clean 1-1
pairs into a single permanently "dense" component, and `min_share` had no effect on
anything but a string. Measured on the battery (`code/census_stress.py`, 8 seeds):

- **Sliver scenario** (`alpha=1`, 3% boundary noise — ground truth 100% 1-1 by
  construction): shipped census reported **1% of opportunity in 1-1 components at
  every `min_share` value from 0 to 15%.** The threshold was decorative.
- **Alpha sweep**: at `alpha=0.9` (nearly clean pairings) shipped census reported a
  mean 3% of opportunity in 1-1 components when the recoverable truth was 43%.

This matters beyond the synthetic world: the review's §11 designates "run `census` on
real data" as the sole remaining gate, and kill criterion 1 fires on "dense components
covering most of the opportunity." **The gate would have been evaluated with an
instrument that can only return one answer.** The `HANDOFF.md` claim that census
"drops edges under 2% ... so map slivers do not masquerade as entanglement" described
the intent, not the behaviour.

**Patch (in `territory.py`, default behaviour):** `census(G, min_share, split=True)`
trims sub-threshold edges *before* componentization. Weak edges inside a surviving
group still count toward its opportunity (same reps, same solve); weak edges crossing
groups are orphaned, and `1 - sum(r["share"])` over the returned rows is the orphaned
share needing manual adjudication. `split=False` reproduces the old behaviour for
comparison.

After the patch, on the sliver scenario:

| min_share | 1-1 share (patched) | opportunity orphaned |
|---|---|---|
| 0.5% | 18% | 0.3% |
| 1% | 56% | 1.2% |
| **2% (default)** | **75%** | **1.8%** |
| 4% | 89% | 2.3% |
| 8% | 96% | 4.2% |
| 15% | 91% | 9.3% |

The threshold is now a real dial with a real trade: verdict recovery against orphaned
opportunity. It is also *contested by construction* — the verdict moves materially
between 0.5% and 4% — so on real data the census should be reported at several
thresholds with the orphan share alongside, not at 2% alone. (Same implicit-parameter
discipline the review applied to the disagreement point: 2% is a default nobody chose;
now at least it does something, and its sensitivity is measurable.)

---

## 3. What the patch does NOT change

**Genuine entanglement is still genuinely dense.** With independent territories
(`alpha ≤ 0.5`) the patched census still finds ≤3–4% of opportunity in 1-1 components
— the re-split only removes the *false-positive* channel where map noise manufactured
density. So the strategic picture in `HANDOFF.md` §5 stands: expect dense on real
data, and the leximin-over-components machinery remains unbuilt and remains the gap.
What changed is that "dense" will now be a measurement, not an artefact.

Other battery results (`census_stress.py`, 8 seeds each):

- **corr dial**: realized corr(A_z,B_z) spans +0.05 (rho=−0.5) to +0.93 (rho=+1.0),
  monotone, with wide per-instance spread at the low end (sd ≈ 0.3) — filter on
  `G.graph["corr_AB"]` when a scenario needs a specific regime.
- **state binding** (6 states, `alpha=0.7`): state lines cut a mean 16% of adjacency
  edges and fragment the average rep-pair overlap zone into 2.4 pieces before
  contiguity is even priced — kill criterion 3 is live in the battery and cheap to
  check on real data the same way.

---

## 4. Scope

Synthetic findings calibrate instruments; they settle nothing about the real book.
The alpha at which real territories sit, the real sliver profile, and the real corr
are all unknowns that only the data load answers. The claim this file supports is
narrower: **when the real census runs, its answer will now reflect the data rather
than a componentization artefact, its threshold sensitivity can be reported, and every
kill criterion has a synthetic instance that demonstrates what firing looks like.**

## 5. Files

```
code/synth.py           the generator + SCENARIOS battery (self-test: python3 synth.py)
code/census_stress.py   the four experiments; numbers above reproduce from it
code/mkfig_census.py    figure generation
figures/census_stress.png
```

---

## 6. Generator v2 (U5, 2026-08-29) — new dials, new scenarios

`research/contiguity/PLAN.md` Part G lists four things the generator could not produce:
dense components by design, zero-value zips, real value concentration, and real geography.
All four are now dials. **Every one defaults to a no-op**, and S1–S7 at every seed are
byte-for-byte what they were — see *Verification* below.

### 6.1 The new dials

| dial | default | effect |
|---|---|---|
| `split_b: int` / `split_a: int` | `0` | plant an intruding seed of the other firm inside k host territories → designed 1A×2B / 2A×1B components |
| `split_pos` | `"core"` | intruder sits on the territory's metro core (argmax `M`) or its periphery (`"edge"`) |
| `split_weight` | `"M"` | host territories drawn ∝ their opportunity, or `"uniform"` |
| `activity: dict` | `None` | three states per zip from a graph-smoothed field tilted by log density: **glue** (`A=B=M=0`), **untapped** (`M>0, A=B=0`), **active**. Keys: `p_glue, p_untapped, slope, smooth_k, mode, p_untapped_by_decile` |
| `metro_weights="zipf"`, `zipf_s` | `None`, `1.0` | metro *m* gets cluster count and density mass ∝ `m^-s` instead of equal shares |
| `gamma` | `1.0` | `M ∝ dens^γ` before noise (superlinear urban scaling; γ ∈ [1.1, 1.3] in the scaling literature) |
| `dens_floor` | `0.20` | the rural floor the legacy code hard-coded |
| `core_tail=(alpha, frac)`, `core_cap` | `None`, `50.0` | capped Pareto multiplier mixed into the densest `frac` of zips |
| `assign="graph"`, `b_hops` | `"euclid"`, `4` | multi-source BFS Voronoi on the adjacency graph instead of nearest-seed-in-the-plane; B bases copy A's with probability `alpha`, else a `b_hops` random walk |
| `share_curve: dict` | `None` | `log(A/M) ~ Normal(mu[d], sd[d])` by M-decile — the form `twin_stats` measures. Keys: `mu`/`sd` (or `mu_a/sd_a/mu_b/sd_b`), `w_spatial` |
| `graph`, `pos`, `density_field`, `states` | `None` | adopt real geography: caller-supplied adjacency, coordinates, per-node density and state labels (U8 regional instances, the twin) |
| `validate_self` | `True` | assert `territory.validate(G) == []` inside `make_instance` whenever a knob is on |

`activity_report(G)` reports `active_frac, booked_frac, glue_frac, untapped_frac,
active_pieces, largest_active_share, M_share_untapped, gini_M, gini_u, top1_share_M,
top10_share_M`. **`active` means `A+B+M > 0`**, matching `contig_methods/base.covariates`
(which calls a zip active when `u_a+u_b > 0`); an untapped zip has `u > 0`, so
`active_frac == 1 - glue_frac`.

### 6.2 New scenarios

| scenario | what it instantiates |
|---|---|
| `S8_twin`, `S8_twin_ln`, `S8_twin_ht` | fitted to `twin_stats.json`; `_ln`/`_ht` are the same instance under the lognormal and dPlN sales tails |
| `S9_dense` | designed dense components (`split_b=2, split_a=1, split_pos="core"`) |
| `S10_glue` | mechanism (d): 45 % glue, 15 % untapped |
| `S11_metro` | value concentration (Zipf metros, γ=1.2, `core_tail=(1.5, .05)`) |
| `S12_regional` | real geography — raises `NotImplementedError` naming U8 / `battery/code/regions.py` |

`calibrate(stats, n=…)` turns `twin_stats.json` into overrides. `stats=None` (the situation
until U3's export lands) returns literature/repo fallbacks with `calibrated=False`,
`calib_source="literature"` and every key listed in `calib_missing`; `strict=True` raises
instead, for use once the real file exists. `fit_rho_books` inverts the `rho_books` dial by
probing — `rho_books` moves the *latent* fields while the shared `M_z` factor and the share
curve both move realised `corr(log A, log B)`, so a fitted target can only be hit by
bisection. It lives in `calibrate`, never inside `make_instance`.

**`CALIB_MAP` is a map of knob → tuple of candidate paths into `twin_stats.json`**, because
U3 writes that file on a different machine in a different session. The first path of each
tuple is canonical; a spelling drift is a one-line fix here, never a silent wrong number.

### 6.3 Two deviations from the U5 plan, and why

1. **`core_tail` renormalises the mean, not the max.** The plan said `dn /= dn.max()` after
   the Pareto boost. That divides the whole field by the single largest draw, so `dn`
   collapses towards zero, `dens_floor` dominates, and the instance comes out *more* uniform
   than with `core_tail=None`: Gini(M) 0.16 vs 0.43 at the S11 settings. Restoring the
   pre-boost mean keeps the floor at its intended size and gives Gini(M) ≈ 0.55.
2. **`S9_dense` is 8×8 reps, not 4×4.** With four reps on a unit square every intruder's
   Voronoi cell spills across its neighbours and the whole map collapses into one chained
   4A×5B blob — one dense census row, the opposite of the designed small components. At 8×8
   the cells stay local: 2–3 dense rows per seed, including clean `1A × 2B` and `2A × 1B`.

### 6.4 Verification

`battery/code/tests/test_synth_compat.py` (fast, ~8 s) has three layers.

- **Layer A — bit identity.** `tests/anchors/synth_baseline.json` was generated from the
  *untouched* generator and holds the sha256 of the raw bytes of `M, A, B, pos, rep_a,
  rep_b, state, edges` plus the `repr` of `corr_AB, Sa, Sb, Mtot, cap_a, cap_b`, for the 17
  battery cases and S1–S7 × seeds 1–2. It ran after every single step of the build. **A
  failure is never a reason to re-anchor.**
- **Layer B — battery compatibility.** Every `battery/figures/C*.json` regenerates:
  `params` as a subset (U0c added four keys after the run), `corr_AB/Sa/Sb/Mtot` to 1e-12,
  census shapes exactly with shares to 1e-12, the pair set as a dict keyed by `(ra, rb)`,
  free-Nash product to 1e-9. Read-only — nothing under `battery/figures/` is ever written,
  and `run_battery.py` is never imported (its `CASES` table is copied into the test).
- **Layer C — targets.** S10 `active_frac` 0.5500 exactly at n ∈ {200, 2000}, seeds 1–3,
  with `active_pieces` 26–47 at n=2000; S11 mean Gini(M) 0.571 (0.589/0.586/0.540) against
  the 0.55 ± 0.05 target and top-10 % M share 0.45–0.51; S9 2–3 dense census rows per seed;
  per-decile share-curve `sd` recovered to ±0.11 at n=4000; n=8000 builds in 0.28 s.

`S11_GINI_TARGET = 0.55` carries a `TODO(U8)`: re-pin it from public ZCTA population ×
income once `data/public/` exists.

**One solver finding, recorded not fixed.** Under the pinned `scipy==1.18.1` /
`highspy==1.15.1`, `territory.nash_exact` fails on exactly one recorded battery pair —
`C4_contested` A0/B0, 27 zips — with `HiGHS Status 4: Solve error` after two
outer-approximation rounds, and `territory.solve` then falls back to the prefix heuristic
*without saying so* (product 8.961104634 against the recorded exact 8.963157397). The
instance is byte-identical, so this is a solver-environment regression, not a generator one;
the likeliest cause is the two options scipy reports as unrecognized and forwards to HiGHS
verbatim at `territory.py:223`. Layer B asserts the weaker real invariant for such pairs
(heuristic product ≤ recorded exact optimum) and prints a banner. `territory.py` is
main-session/serial, so U5 left it alone.
