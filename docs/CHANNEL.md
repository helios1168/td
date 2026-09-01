# The national channel — the problem as it now stands

**Opened:** 2026-08-31 · **Split out of `NWAY.md` on 2026-08-31.** Companion files: `CHANNEL.md` (the problem), `MODEL.md` (the model), `DATA.md` (the export route).

Read this first. `MODEL.md` has the N-way maths this rests on; `DATA.md` has the export route.


The business is standing up a **new "national" channel**, carving the two largest firms out
of the financial-institutions and wirehouse channels, with territories targeted at roughly
equal opportunity — about **$1B each**.

That is not the two-player merger problem, and it is not quite the N-way problem either. It
is **greenfield balanced districting**. Decided: **two-stage**, with the $1B as an emergent
target rather than a constraint.

### 1 Nash welfare on a common measure *is* equal-size districting

Every zip lands in exactly one district, so `Σ_j M_j` is the same for every partition.
Maximising `Σ_j log M_j` subject to a fixed sum equalises the terms (`∂/∂M_j → 1/M_j = μ`).
So the Nash objective already *is* the balance objective — the same optimum, not an
approximation of it. Set `k = total_opportunity / $1B` and balance falls out.

This is why the target does not need to be a hard band. It also sidesteps **trap 2**:
explicitly minimising a spread can leave everyone worse off, whereas Nash reaches the same
balance as the maximiser of a concave objective and stays Pareto efficient. The battery's
own equalisation finding (an unconstrained equaliser reaching KS gap 5.2e-8 but
Pareto-dominated by Nash) is the same phenomenon from the other side.

`test_channel.py::test_nash_welfare_is_equal_size_districting` brute-forces every contiguous
3-way cut of P₁₂ and confirms the argmax is the balanced one.

### 2 The welfare decomposition

```
Σ_i g_i = Σ_z [ λ·M_z + c2·T_z + c_free·S_free ]     ← partition-invariant
        + Σ_z (c1 − c2)·S_owner(z)(z)                ← maximised by keeping zips with their incumbent
```

The objective splits into **balance the territories** and **where there is slack, leave
business with the rep who already has it**. At ~5% saturation with λ=0.3 the opportunity term
is roughly 90% of `u_i` and the book differentiation roughly 10% — so a balanced map with a
modest continuity tilt. *Check the ratio against real saturation*: it decides how much the
legacy books move the map at all.

### 3 Two stages

| stage | problem | status |
|---|---|---|
| **1 — draw** | k balanced contiguous districts on opportunity alone | **the hard part**; balanced contiguous districting |
| **2 — match** | assign retained reps to districts | **built** — `contig_methods/channel.py`, exact |

Stage 2 is a max-weight matching on **log** weights: `g_ij = Σ_{z∈A_j} u_i(z)`, maximise
`Σ_i log g_{i,σ(i)}` by the Hungarian algorithm. Same objective as stage 1, O(n³), exact.
Nash rather than utilitarian matching matters — a utilitarian match will hand one rep a
district holding almost none of their book if the total looks good.

**Rectangular matching selects the retained set.** With more reps than districts the unmatched
reps are the ones not retained, and the choice is well-posed precisely because k is fixed
(§6.3's objection does not bite).

**Known cost of the split.** Stage 1 cannot see relationships, so a good matching may not be
available at stage 2 — the same objection CLAUDE.md raises to "decouple fairness from
compactness": it relocates the difficulty rather than removing it. Mitigation, cheap because
stage 2 is milliseconds: generate a *portfolio* of stage-1 draws and keep the one that staffs
best (`channel.score_draws`). Not the joint optimum, but close to free.

### 4 What this does to the data requirement

**Stage 1 needs almost none of the confidential data** — only `(zip, M)` and the adjacency
graph. No books, no rep ids, no shares. Opportunity is plausibly third-party market sizing.

**Stage 2 can run entirely on the work machine**, since it needs only the returned district
map plus internal books.

The descaled-export route (§5b) stays correct and is still the right channel for anything
that does need to travel, but the national-channel problem needs a fraction of it.

### 5 What is now the open risk

Stage 1 destroys the census decomposition. The bilateral pair structure came from *overlap
between two legacy rep maps*; a greenfield channel has no such structure, so stage 1 is one
k-way partition over the whole footprint.

- `scip_tree` certifies to **135 zips**. Validi, Buchanan & Lykhovyd certify ~**1,500 units**
  for political districting, which is the published state of the art for exactly this problem.
- If the footprint is larger than that, the options are pre-aggregation (cluster ZCTAs, or
  work at county/CBSA level), ε-certified acceptance (tier 2, already in the harness), or a
  heuristic with a reported bound.
- **Symmetry** is the new hazard: k anonymous districts are interchangeable labels, which
  costs branch-and-bound its pruning. The standard remedy is the centre-based (Hess)
  formulation — assign each zip to one of k *centres* — which breaks the symmetry by
  construction and is what the districting literature uses.

### 6 The instance, sized (2026-08-31)

| | |
|---|---|
| zips carrying sales | **2,232** |
| distinct reps | **72**, including the "open" (vacancy) key → 71 real |
| total opportunity | **≈ $6.2B** |
| footprint | west coast, east coast, Texas, Florida — **midwest uncovered** |
| ⇒ `k` | **≈ 6** at $1B, or 7 at ~$886M |

Two consequences, and the second is the important one.

**Scale is at the frontier but not past it.** 2,232 units × 6 districts ≈ 13,392 binaries.
Validi, Buchanan & Lykhovyd certify ~1,500 units for political districting, so this is the
same order of magnitude as the published state of the art — attemptable, not routine.

**The footprint is disconnected, and that is a gift.** No contiguous district spans
California and Florida, so the adjacency graph has ≥ 4 major components and **the problem
separates**: allocate an integer district count to each component, then solve each
independently. Failure mechanism (a) — pre-existing graph disconnection, the thing that
broke the legacy cut loop — arrives here as the structure that makes the problem tractable.
At roughly 500 zips per region the subproblems are far closer to where `scip_tree` already
works than the 2,232-zip whole would be.

### 7 Balance has a geometric ceiling — compute it first

`channel.allocate_districts(component_M, k)` maximises `Σ_c k_c·log(M_c/k_c)` over integer
allocations with `k_c ≥ 1`. Within a component the best conceivable outcome is `k_c` equal
districts, so this is an **upper bound on any real partition** — a free dual bound for
stage 1, available before a solver runs (`test_ceiling_is_an_upper_bound_on_any_real_partition`).

It is also the answer to whether the target is reachable at all. Illustrative splits of
$6.2B (real regional totals still needed):

| split | k=6 | k=7 | k=8 |
|---|---|---|---|
| even-ish (2.0 / 2.2 / 1.1 / 0.9) | **19.4%** | 41.4% | 55.9% |
| east-heavy (1.6 / 3.0 / 0.9 / 0.7) | 87.1% | 33.9% | **25.8%** |
| coast-heavy (2.6 / 2.6 / 0.6 / 0.4) | 87.1% | 101.6% | **60.2%** |

(spread = (max−min)/mean across districts, at the **objective-optimal** budget)

**Caveat, added 2026-08-31.** Those are the spreads at the budget maximising
`Σ_c k_c·log(M_c/k_c)`, which is not always the *most even* budget. East-heavy at k=6 is the
worked case: the objective optimum allocates W/E/TX/FL = 1/3/1/1 for 87.1% spread, while
2/2/1/1 reaches 77.4%. `allocate_districts` now returns both — `ceiling_spread_rel` at the
dual-bound budget and `min_spread_rel` at the spread floor, with `spread_optima_agree` saying
whether they coincide. The conclusion is unchanged (77.4% is still nowhere near ±10%), but the
two numbers answer different questions and should not be quoted interchangeably.

Three things follow:

1. **$1B ± 10% is probably not reachable.** Even the friendliest split tops out near 20%
   spread, because a ~$0.9B region gets exactly one district and cannot be subdivided.
2. **The best `k` depends entirely on the regional composition** — the table moves in
   opposite directions across scenarios. `k` is a balance decision, not just headcount.
3. **This is four numbers of work.** Regional opportunity totals answer it immediately, with
   no solver and no confidential per-zip data.

**Next input needed: opportunity by region (west / east / TX / FL).** Everything above is
illustrative until those land.

**Also to confirm:** 71 real reps against ~6 territories is a 12:1 ratio. The reading that
makes sense is that the national channel is a *specialist* carve-out staffed by a handful of
senior wholesalers, while the other reps keep covering the remaining firms in the existing
FI/wirehouse channel — i.e. stage 2's "unmatched" reps are *not selected for this channel*,
not released. If that is wrong the framing of stage 2 needs revisiting.
