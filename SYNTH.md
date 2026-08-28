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
