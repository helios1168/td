# Contiguity options — implementation and test plan

**Date:** 2026-08-28. **Status:** plan only; no code written. Implementation happens elsewhere.
Companion: `OPTIONS.md` (what each option is and why), `raw/*.md` (sources).

Decisions already taken (from the 2026-08-28 checkpoint): options cover formulations *and*
architecture; open-source solvers only; deviation from global optimality is a headline metric;
state borders are **off** for this study but must be a one-flag rerun; real opportunity data
will be supplied by zip and the battery machinery must ingest it; 180 wholesalers across both
firms (≈90 per firm) sets the scale target; overnight runs on the 12-core M2 Max are acceptable.

---

## 1. Harness

One driver, one interface, every option a plug-in. Nothing touches `battery/figures/` (primary
artifacts).

```
battery/code/contiguity_bench.py          driver: instances × options × settings → JSON rows
battery/code/contig_methods/
    __init__.py                           REGISTRY = {"current": ..., "flow": ..., ...}
    base.py                               Result dataclass + gap computation + validators
    current.py                            wraps districting.solve_contiguous_nash (control)
    flow.py                               Option D  (scipy/HiGHS; Shirabe flow, fixed roots)
    flow_pwl.py                           Option D+C (one MILP, PWL log)
    scip_tree.py                          Option A  (PySCIPOpt Conshdlr; A′ native-log variant)
    cbc_tree.py                           Option B  (python-mip lazy_constrs_generator)
    prep.py                               Option E1/E2/E3 as wrappers around any method
    warm.py                               Option F1 spanning-tree bisection, F2 cut-and-choose, F3 OT-threshold
    bounds.py                             method-independent UBs: fractional (discrete-OT) bound, free-Nash value
    loop_v2.py                            Option G  (in-out, minimal-separator cuts, highspy)
    frontier.py                           Option H  (audit only, small instances)
    brute.py                              ground truth, n ≤ 20
battery/code/real_opportunity.py          C10 loader + instance generator (§6)
battery/results/contiguity/<run_id>/      rows.jsonl, summary.csv, per-instance assignment .npz
research/contiguity/RESULTS.md            written by hand from summary.csv after each stage
```

**Method interface.** `solve(G, nodes, *, theta, lam, rho, respect_state, time_limit, seed,
warm_start=None, reductions=None) -> Result`. Every method receives the same pair subgraph and
returns:

| field | meaning |
|---|---|
| `status` | `optimal` / `time_limit` / `iteration_limit` / `infeasible` / `error` |
| `to_a` | zip set assigned to a (may be empty on failure) |
| `g_a, g_b, product, perimeter` | recomputed by the harness from `to_a`, never trusted from the method |
| `LB` | true objective `log g_a + log g_b − ρ·perimeter` of the returned incumbent |
| `UB` | tightest valid bound the method produced (`None` for heuristics) |
| `UB_free` | harness-computed, method-independent: the fractional (discrete-OT / convex-hull) bound from the ratio threshold with one split zip, `O(n log n)` via `prefix_table`; and the exact free-Nash value from `nash_exact`. Both bound the contiguous optimum from above; recorded on every row for the cross-method gap |
| `gap` | `(UB − LB)/|UB|`, or `None` |
| `eps` | a-priori approximation bound for ε-methods (Option C), else 0 |
| `t_first_feasible, t_total, iters, n_cuts, n_tangents, nodes` | effort profile |
| `pieces_a, pieces_b` | harness-computed component counts (must be 1/1 on `optimal`) |
| `trace` | list of `(t, LB, UB)` at each improvement, for gap-vs-time curves |

**Validators (run on every row).** Assignment is a partition; both sides connected (or the
status is not `optimal`); `product_contiguous ≤ product_free` where the free Nash value comes
from `territory.nash_exact`; `LB` recomputed matches the method's claim to 1e-9; `respect_state`
implies no cross-state edge inside either side.

**Parallelism.** `multiprocessing.Pool(11)`, one (instance, option) job per worker, each job
single-threaded (set `threads=1` in every solver so 11 jobs do not oversubscribe). Time caps are
per job. Results append to `rows.jsonl` as they finish so a killed run loses nothing.

**Reproducibility.** Instances are regenerated from `synth.scenario(name, n, seed, **overrides)`
with the exact `params` blocks stored in `battery/figures/C*.json`; the harness asserts the
regenerated pair sizes match those JSONs before running (guards against generator drift).

---

## 2. Instance set

| tier | source | pairs | zips/pair | purpose |
|---|---|---|---|---|
| **T0 ground truth** | synth n=40–60, 4×4 reps, seeds 1–10, keep pairs with n ≤ 20 | ~15 | 8–20 | brute-force optimum; every option must match |
| **T1 battery** | C1, C2, C3(ms02), C4, C5-free, C6, C9 as in `battery/figures/*.json` | ~65 | 30–82 | regression vs. current solver; mechanism (a) and (c) cases |
| **T2 scale** | C7 (n=400) + new C7b (n=800, seeds 1–2) | ~12 | 44–400 | mechanism (b) |
| **T3 real-opportunity** | C10 (§6), tiers 200 / 400 / 800 raw zips per pair | ~16 | 200–800 | mechanism (d); the production regime |
| **T4 state borders** | C5-resp and C10 with `respect_state=True` | ~12 | 30–800 | the one-flag rerun; not in the headline table |

Named failure instances are tracked individually: C1-seed2 A0/B0 (69), C5-resp A2/B2 (61),
C7 A3/B3 (205), A0/B0 (125), A1/B1 (44), C9-seed2 A2/B2 (31).

---

## 3. Metrics — deviation from global optimality

Reported per (instance, option, ρ), then aggregated per option.

1. **Certified gap** `(UB − LB)/|UB|` from the method's own bound. Exact methods: pass iff
   `gap ≤ 1e-8` (matches `CLAUDE.md`'s acceptance criterion). ε-methods: pass iff
   `gap ≤ eps + 1e-8` with `eps` stated.
2. **Cross-method gap** `(UB* − LB)/|UB*|` where `UB*` is the tightest valid UB from *any*
   option on the same instance. This is the score for heuristics (F1/F2, E3) and for any run that
   stopped on a time cap. A row whose LB exceeds another method's claimed UB flags a bug.
3. **Ground-truth gap** on T0: `(OPT − LB)/|OPT|` from `brute.py` (enumerate subsets containing
   `root_a`, both sides connected, bitset BFS; n ≤ 20 → ≤ 5·10⁵ subsets, seconds each). Any
   nonzero value for an "exact" method is a formulation bug, not a performance result.
4. **Gap-vs-time profile**: gap at 5 s, 20 s, 60 s, 300 s (and 1200 s in Stage 2) from `trace`.
   This is what separates "certifies in 4 s" from "reaches 1e-4 in 5 s but never certifies".
5. **Cost of contiguity** `1 − product_contiguous / product_free` (already in the battery), and
   the **welfare fraction** `product_contiguous / product_free` reported alongside the
   theoretical MMS price-of-connectivity for the component's vertex connectivity (4/3 on
   biconnected, k at a k-way cut vertex — Bei et al. 2022) so the paper can compare.
6. **Structure covariates** per pair, to explain failures: n, active-zip fraction, number of
   articulation points, block-tree shape (path or not), free-Nash component count,
   Gini / top-5 share of `u_a + u_b` (the value-concentration dial), perimeter of the free
   solution.

Primary ranking of options = share of instances certified within cap, then median time to
certificate, then median cross-method gap where not certified.

---

## 4. Stages, caps, and wall time

Machine: 12 cores / 32 GB → 11 workers. Failures run to the cap; successes take seconds, so the
cap sets the cost of a stage.

| stage | instances | options | ρ | cap | jobs | wall (worst / typical) | when |
|---|---|---|---|---|---|---|---|
| **S0 smoke** | T0 + 6 named failures | current, flow, warm | 2e-3 | 60 s | ~65 | 6 min / 2 min | as each method lands |
| **S1 screening** | T0 + T1 + T2 | all 8 (A, B, C-on-D, D, E1+A, E3+current, F1, G, H on T0/T1 only) | 2e-3 | 60 s | ~700 | 65 min / 20 min | daytime, repeatable |
| **S2 finalists** | T1 + T2 + T3 | top 3 from S1, each with and without E1/E2/F1 | {2e-3, 2e-4, 1e-5} | 20 min | ~450 | 14 h / 3 h | overnight |
| **S3 production dry run** | all real pairs (~90) | winner | 2e-3 | 60 min | ~90 | 8 h / 1 h | overnight |
| **S4 state borders** | T4 | winner | 2e-3 | 20 min | ~12 | 20 min | daytime |

Plus, **as soon as the opportunity file arrives (before any new option exists):** run the
*current* solver on T3 with a 20-min cap overnight — the baseline gap-vs-time on the real regime.
It tells us whether we are fixing a 2× or a 50× problem, and it is the number every option is
compared to.

Turnaround: the compute above fits in two nights. The critical path is engineering — Stage 0
methods ½ day, Options A/B/C ~2–3 days, E/F ~2 days — so S1 can run on day 3, S2 night 3–4,
S3 night 4–5.

---

## 5. State-border switch

One flag, threaded everywhere, default off:

- `contiguity_bench.py --respect-state` sets `respect_state=True` for every method; the harness
  (not the method) deletes cross-state edges from the pair subgraph *before* dispatch, so every
  option sees identical topology and no method can forget the flag. The validator checks it.
- Real ZCTAs get `state` from the Census ZCTA→state relationship file (ZCTAs straddling states
  are assigned to the state holding the largest share, with a `multi_state` attribute kept).
- Rerun = `contiguity_bench.py --stage S4 --respect-state`; results land in a separate
  `run_id` so the two regimes are never mixed in one summary.
- Reported separately: edge share deleted, resulting component count per pair, and pairs that
  become infeasible (a side with no in-state path) — C5 showed 18.6% of edges cut and 5-piece
  fragmentation; on real data this is expected to be the binding constraint if it is ever on.

---

## 6. C10 — real-opportunity instances (new battery machinery)

**Input.** A file of `(zip, opportunity)`; confirm columns, units, and whether keys are ZIPs or
ZCTAs. ZIP→ZCTA: use the HUD/UDS or Census crosswalk; report the share of opportunity that
lands on ZCTAs with no polygon (PO-box ZIPs) and where it was reassigned (nearest ZCTA centroid).

**Graph.** Nodes = ZCTAs present in the file plus every ZCTA needed for adjacency (zero
opportunity). Edges = Rook adjacency from the Census TIGER ZCTA5 2020 shapefile via
`geopandas`/`shapely` (`touches` with length > 0 to exclude corner-only contacts). Add
`geopandas`, `shapely`, `pyogrio` to `requirements.txt` for the loader only; cache the adjacency
as `data/zcta_adjacency.parquet` so nothing downstream needs GIS libraries. Fallback if the
shapefile is not wanted: Delaunay on ZCTA centroids with a documented caveat.

**Territories.** Real `rep_a`/`rep_b` are not available. Synthesise ~90 seeds per firm on real
geography: seeds drawn with probability ∝ opportunity (so reps sit where the business is), zips
assigned by opportunity-weighted Voronoi on the adjacency graph (multi-source BFS with
opportunity-weighted distances), then the existing `synth` misalignment dial `alpha` applied to
firm B's seeds. This reproduces the census structure the battery already exercises.

**Values.** `M_z` = real opportunity. `A_z, B_z` synthesised conditional on `M_z` by the existing
`synth.py` machinery (saturation, `rho_books` correlation, lognormal or dPlN tail) with the
headroom constraint `M_z ≥ max(A_z + θB_z, B_z + θA_z)` enforced pointwise. Two variants per
instance: lognormal (C10-ln) and heavy-tail (C10-ht) so mechanism (c) is crossed with (d).

**Scale tiers.** Choose pairs from the census by size: ~200, ~400, ~800 raw zips (2 pairs each,
2 seeds) = 12 instances, plus the four largest pairs at whatever size they come. Report active-zip
fraction (nonzero `A+B+M`) per pair — the number that decides whether E1 matters.

**Scaling.** Opportunity is in dollars; the current solver seeds tangents at absolute
`g0 ∈ {1,…,11}` and bounds `z ∈ [−50, 50]`. The harness rescales utilities so that
`Σ(u_a + u_b) = 100` per pair before dispatch (objective invariant up to a constant; gaps
unaffected) and records the scale factor.

**Deliverables.** `real_opportunity.py` (loader, crosswalk, adjacency cache, instance generator),
`battery/data/README.md` (provenance, counts, dropped/reassigned zips), and C10 entries in
`RESEARCH_PLAN.md` mirroring C1–C9's format. Figures via the existing `case_pipeline.py`
three-panel map for the four largest pairs only.

---

## 7. Per-option implementation notes and acceptance

| option | build | acceptance to advance from S1 |
|---|---|---|
| **D flow** | flow vars per side with fixed roots; capacities `≤ n_side_max·x`; reuse `districting.py`'s tangent loop | matches brute force on T0; certifies all T1 ≤ 82 zips within 60 s |
| **D+C flow_pwl** | log-spaced breakpoints on `(g_min, Σu]`, SOS2 via Vielma–Nemhauser; UB from tangent envelope | `gap ≤ eps` on T0/T1; report eps sensitivity 1e-4 / 1e-6 |
| **A scip_tree** | `Conshdlr` with `conscheck` (connectivity on both sides) + `consenfolp` (min-cut separator cut + tangent at incumbent); `chckpriority=-10` for lazy semantics; `threads=1`; A′ variant with `model.addCons(z_a <= log(g_a))` via `exp` reformulation | matches D on T0/T1; certifies C7 A0/B0 (125) within 60 s |
| **B cbc_tree** | `ConstrsGenerator` adding both families; `model.start` from F1 | as A |
| **E1 prep** | networkx pass: contract zero-value degree-2 chains, absorb zero-value leaves, record articulation points; expand assignment afterwards | optimum unchanged on T0/T1 (bit-identical `to_a` after expansion) |
| **E2 fixing** | after root LP + incumbent: fix `x_z` with reduced cost > gap; re-check on each UB improvement | optimum unchanged; report fixed fraction |
| **E3 quotient** | fix stray free-Nash components; solve quotient; report gap vs. unfixed UB | cross-method gap reported; never labelled `optimal` |
| **F1 warm** | 50 random spanning trees × best cut + boundary-swap local search; contiguity-preserving | feasible on 100% of instances in < 5 s at n=800; cross-method gap reported |
| **F2 cut-and-choose** | st-numbering of each biconnected block; best prefix | EF1 check passes on T0 where block-tree is a path |
| **F3 OT-threshold warm** | smooth `u_a, u_b` on the graph (k neighbour-averaging steps, k∈{1,2,4}); threshold `ũ_a/ũ_b ≥ g_a/g_b` at the free-Nash ratio; attach stray components to the side of their largest-boundary neighbour; boundary-swap local search as F1 | feasible on 100% of instances; cross-method gap reported next to F1; kept only if it beats F1 on median gap or on time-to-certificate when used as MIP start |
| **G loop_v2** | in-out tangent step (λ=0.5), min vertex-cut separators, `highspy` warm start + `threads`, quantile-seeded tangents | iteration count on C9 pairs vs. current; no regression on T1 |
| **H frontier** | ε-constraint on `g_a` with contiguity via D; Nash-best frontier point | agrees with D on T0/T1 ≤ 50 zips |

Every method must also pass: T0 ground truth exact (or ≤ eps); `pieces = 1/1` whenever
`optimal`; `product ≤ free product`; deterministic under fixed `seed`.

---

## 8. Reporting

`RESULTS.md` after each stage: one table per stage (option × {certified %, median t-to-cert,
median gap@60 s, worst gap, named-failure outcomes}), the gap-vs-time curves for the six named
failures, a mechanism matrix (which options fixed which of (a)/(b)/(c)/(d) in practice), and the
recommendation. Feed the final numbers into the paper's §5 contiguity table and into
`CLAUDE.md` Trap 11.

---

## 9. Dependencies to add (all pip, all permissive licences)

| package | for | licence |
|---|---|---|
| `pyscipopt` (≥ 5.0, SCIP bundled) | Option A | Apache-2.0 |
| `mip` (≥ 1.17, `cbcbox`) | Option B | EPL-2.0 |
| `highspy` | Option G3 warm start / threads | MIT |
| `geopandas`, `shapely`, `pyogrio` | C10 adjacency only (cached to parquet) | BSD |

---

## 10. Checkpoint questions before code

1. **Opportunity file**: columns, units, ZIP vs ZCTA, any state column — and can it be dropped
   into `battery/data/` today so the baseline overnight run (§4) happens tonight?
2. **Adjacency**: TIGER shapefile (correct, ~500 MB download, GIS libs in the loader only) or
   centroid Delaunay (same-day, caveated)? Recommendation: shapefile.
3. **Territories**: synthesised on real geography as in §6, or do you have real rep maps?
4. **Stage-2 caps**: 20 min per job overnight is the proposal; say if you want longer.
5. **Scope of S1**: all eight options, or drop H (audit) and G (loop engineering) to save a day?
   Recommendation: keep G2/G4 hygiene, drop the rest of G and H unless A/B are blocked.
