# N-way division — adapting the two-player machinery to 3+ reps per zip

**Opened:** 2026-08-31 · **Branch:** `wt/adapt-8-31-2026` · **Status:** design + Phase 1 landed + real-instance data route + national-channel reframing

The problem in practice has taken a new shape: **a single ZCTA can be claimed by three or more
wholesalers**, not one legacy A-rep against one legacy B-rep. This file is the design for
adapting the existing programme to it, and the record of what breaks.

This is **not** PLAN.md G.4 / W12. That unit assumed a component spanning 3+ reps in which
every *zip* still had exactly two candidate owners (`rep_a`, `rep_b`), so the decision stayed
one binary per zip. Here the candidate set per zip is itself ≥ 3, which changes the decision
variable. G.4 becomes the special case `|cand(z)| = 2 ∀z`.

---

## 1. The model generalises cleanly — this is the good news

### Utilities

The two-rep model reads, with `c1 = 1 - lam`, `c2 = theta*(1 - lam)`:

```
u_a(z) = c1*A_z + c2*B_z + lam*M_z
u_b(z) = c2*A_z + c1*B_z + lam*M_z
```

`A_z` and `B_z` are *whose book it is*, not which firm — the merger is the reason there are
two. Replace them with a per-rep book `S_{i,z}` and let `T_z = Σ_j S_{j,z}` be all booked
production at `z`:

```
u_i(z) = c1*S_{i,z} + c2*(T_z - S_{i,z}) + lam*M_z
```

The inheriting rep keeps `c1` of their own book and captures `c2` of everyone else's. At two
reps with `S = {a: A_z, b: B_z}` this is *identically* the current formula — `u_a` expands to
`c1*A + c2*(A+B-A) + lam*M = c1*A + c2*B + lam*M`. **Phase 1 asserts this reduction in a
test**, so the whole existing corpus of results stays interpretable.

Headroom generalises the same way:

```
M_z  >=  max_i ( S_{i,z} + theta*(T_z - S_{i,z}) )
```

which at two reps is `max(A + theta*B, B + theta*A)`, unchanged.

`theta` keeps its meaning and stays the one parameter resting on unfinished identification
work. Note it is now doing more work: it is the capture rate against a *pool* of departing
books rather than one counterparty, so if capture differs by which rep is displaced,
`theta` should become `theta_{i←j}`. **Flagged, not built** — see §6.

### Objective

Maximum Nash welfare over n agents, still at `d = 0`:

```
max  Σ_i log g_i  -  rho * perimeter        g_i = Σ_{z : owner(z) = i} u_i(z)
```

`log` is concave, `g_i` is linear in the assignment, so this is still a convex MINLP and
outer approximation is still a finite global method with a real certificate. Nothing in the
OA argument was two-player. Caragiannis et al. (2019) state EF1 for n agents, so the fairness
claim survives the move — it was never the two-agent case that carried it.

### Schema

```python
G.nodes[z] = {
    "cand": (rep_id, ...),        # candidate owners, len >= 2, superset of {i : S_i > 0}
    "S":    {rep_id: float},      # per-rep booked production at z
    "M":    float,
    "state": "NE",                # optional, unchanged
}
```

Two-rep graphs are read through a shim: `cand = (rep_a, rep_b)`, `S = {rep_a: A, rep_b: B}`.
Existing instances, the zip50 anchor and every committed result keep working untouched.

---

## 2. What actually breaks

| Piece | Two-player form | N-way form | Severity |
|---|---|---|---|
| Decision variable | one binary `x_z` | `y_{z,i}` per candidate + `Σ_i y_{z,i} = 1` | **structural** |
| `base.Result.to_a: set` | membership = the whole answer | needs `to_owner: dict[node → rep]` | **contract change** |
| Separator cuts | an `a` branch on `x`, a `b` branch on `1-x` | one uniform family per rep — *simpler* | low |
| OA tangents | 2 terms `za + zb` | n terms `Σ z_i` | low |
| `brute.py` | `2^n`, T0 at n ≤ 20 | `k^n` — n ≤ 13 at k=3, n ≤ 10 at k=4 | **acceptance** |
| `_ratio_prefix` warm start | `u_a/u_b` ordering | no N-way analogue exists | medium |
| F1 spanning-tree start | 2-way tree splits | k-way tree partition | medium |
| ILS / local search | flip `x_z` | reassign `z` to another candidate | low |
| `overlap_graph` | bipartite A-reps × B-reps | hypergraph, one hyperedge per zip | medium |
| `census` shape verdict | `1-1 pair` / `kA x kB` | rep-set components over the hypergraph | medium |
| `fairness` | `ef1_ab` / `ef1_ba` | pairwise over all ordered rep pairs | low |

Three consequences deserve calling out:

**The brute-force oracle shrinks.** `TEST_PLAN.md` §3 acceptance is "brute-force match on
n ≤ 20". At three candidates per zip that is `3^20 ≈ 3.5e9` — gone. The tier has to be
re-cut by *candidate-weighted* size `Π_z |cand(z)|` rather than by `n`, with a budget of
roughly `1e6`–`1e7` leaves. This is the one acceptance criterion the new shape genuinely
costs us, and it needs your sign-off rather than a quiet redefinition.

**The prefix heuristic has no N-way analogue.** The ratio rule `u_a(z)/u_b(z)` orders zips on
a *scalar* exchange rate; with three claimants there is no total order to sort on. This is
not a loss of a solver — `nash_exact`'s outer approximation never used it — but it removes
the O(n log n) preview, the `warm.py` F3 threshold start, and the discrete-OT upper bound in
Appendix B. The fractional relaxation still gives a valid bound; it just stops being
computable by sorting.

**Empty bundles become live.** With two reps, `Σ x ≥ 1` and `Σ (1-x) ≥ 1` were enough to keep
both gains positive. With n reps, insisting every rep gets a non-empty contiguous bundle is a
real and possibly infeasible constraint, and one rep at `g_i = 0` sends `Σ log g_i` to `-inf`.
The standard treatment (Caragiannis et al. §3) is lexicographic: **maximise the number of reps
with positive utility first, then maximise MNW among those.** Recommended, needs your call —
see §6.

---

## 3. What does *not* break

Worth stating plainly, because it is most of the machinery:

- **Outer approximation** — the concavity argument is per-term and indifferent to n.
- **`scip_tree`'s architecture** — single tree, lazily separated cuts, the `Conshdlr`
  plumbing, the feastol ladder, `_short_stop`, the W6b/W6d fixes. All of it carries.
- **Every trap.** Traps 12–15 are about tolerances, dual reductions and abort handling, none
  of which is two-player. Trap 13's rule — *one root per pair component* — becomes *one root
  per rep per component*, the same fix in a wider index.
- **The two-tier acceptance criterion** (tier 1 `CERT_TOL=1e-8`, tier 2 `EPS_CERT=5e-3`). The
  noise floor should be re-measured on an N-way instance, but the framework stands.
- **`cert_exact.py`** — the exact post-hoc certificate. Its pruning is re-derived in integer
  arithmetic over gains; the AM–GM/product OA generalises to n terms (the n-term AM–GM is
  where W6e's two-term version came from anyway).
- **Contiguity itself.** Per-rep connectivity is the same constraint, just instantiated n
  times instead of twice.

---

## 4. Engine sketch (`scip_tree`, N-way)

```
y[z][i] in {0,1}   for i in cand(z)
Σ_{i in cand(z)} y[z][i] == 1                        # assignment

g_i <= Σ_z u_i(z) * y[z][i]                          # `<=` not `==`  (trap: multi-aggregation)
z_i <= log(ghat_i) + (Σ_z u_i(z) y[z][i] - ghat_i)/ghat_i     # OA tangent, per rep

max  Σ_i z_i  -  rho * Σ_e w_e                       # w_e = 1 iff e is a boundary edge
```

Separator cut for rep `i`, separator `C` between `u` and `v` both assigned to `i`:

```
Σ_{w in C} y[w][i]  >=  y[u][i] + y[v][i] - 1
```

Note this is *more uniform* than the current code, which carries a special `1-x` branch for
side b in `_cut_expr`, `_frac_values` and `_violations`. The N-way form has one branch.

Gain lower bound comes from the incumbent as today (`exp(LB0)/Π_{j≠i} ...` generalises to
holding the other gains at their incumbent values); the 1e-9 floor is still forbidden, for
the same reason — the log's gradient blows up and destabilises the LP.

---

## 5. Phasing

| Phase | Deliverable | Gate |
|---|---|---|
| **1 — landed** | `contig_methods/nway.py`: schema shim, `utilities`, `gains`, `objective`, `perimeter`, `pieces`, `fairness`, `is_feasible`. `tests/test_nway.py` incl. the **2-rep reduction test** against `base.py`. No existing file touched. | tests green |
| 2 | `synth.py` N-way knob → 3-candidate instances; `nway_brute.py` k-ary enumeration with a leaf budget; re-cut T0 by `Π|cand|` | brute matches `base` on 2-rep instances |
| 3 | `base.py` contract extension — `to_owner`, per-rep validators, `evaluate`. **Main session, serial** (frozen contract, `CLAUDE.md` rule) | existing 230 fast tests still green |
| 4 | `scip_tree` N-way variant per §4 | brute match on Phase-2 tier; per-rep contiguity; certificates at `CERT_TOL` |
| 5 | `overlap_graph`/`census` hypergraph; `cert_exact` n-term AM–GM | census verdict on 3-way instances |
| 6 | Re-measure the ε noise floor; N-way S1/S2 screening | RESULTS.md section |

Phase 1 deliberately adds a **new module rather than editing `base.py`**: the contract is
frozen and serial-only, so the primitives get proved out standalone first and the contract
edit lands once, in the main session, with the reduction test already passing.

---

## 5b. Data route — settled 2026-08-31

**The synthetic twin is superseded for this problem.** With PII and firm masked upstream, and
the dollar scale removed, the *real* instance can be exported: real ZCTAs, real adjacency,
real territory structure, real share patterns. That is strictly better than a twin calibrated
to aggregates, and it skips the rank-jitter and fidelity-audit apparatus entirely.

The justification is algebraic, not statistical. `u_i(z) = M_z · [c1·s_i + c2·(t_z − s_i) + λ]`
with `s_i = S_i/M_z`, so `M_z` factors out; and `Σ_i log g_i` shifts by `n·log κ` under a
global rescale. At ρ = 0 the descaled instance and the real one have the **same** optimal
allocation, gaps and certificates. Removing the scale drops a constant the solver never reads.

- `tools/instance_export/export_instance.py` — work-machine exporter, single file, auditable.
  Emits shares in [0,1] plus `m_rel = M/median(M)`; surrogate rep ids; guards that refuse to
  write a currency amount or the divisor.
- `battery/code/descaled.py` — repo-side loader; `S_i = share_i · m_rel` reconstructs the
  instance to within the exporter's 6-sig-fig rounding.

Two consequences to carry forward:

1. **ρ > 0 is not scale-invariant.** `Σ log g_i − ρ·perimeter` mixes a log-scale term with a
   raw count. ρ = 0 is the model, so this only touches the legacy `current` ρ=2e-3 continuity
   column — but any ρ carried over from dollar-scaled data is meaningless here and must be
   re-derived. Same for κ's units in W11.
2. **Tail fits move to share space.** The dPlN/lognormal calibration and `S7_heavytail` were
   fitted to sales *values*; shares are bounded in [0,1] with different tail behaviour. The
   generator's tail knobs need recalibrating, not re-pointing.

`cand(z) = {i : S_i(z) > 0}` — a rep is a candidate only where it has sales (settled
2026-08-31). This makes `cand` derivable from the sales table alone, with no coverage source.

### Vacancies: the filler key (2026-08-31)

Some territories have no official rep and their sales are booked under a **filler key** — a
rep-shaped sentinel that is not a person. It carries real sales, real opportunity and a real
firm. It must **never** become a candidate: an objective term for a vacancy has the solver
bargaining on behalf of an empty chair, and `Σ log g_i` would trade real reps' welfare away
to feed it.

The schema already separates the two roles, which is what makes this cheap: `utilities`
computes `T_z` from *all* books but loops over `cand` only. So filler book arrives as a
separate node attribute `S_free`, is excluded from `cand`, and every candidate capitalises it:

```
u_i(z) = c1·S_i + c2·(T_z − S_i) + c_free·S_free + λ·M_z
```

That gives **four** node classes:

| class | `cand` | book | meaning |
|---|---|---|---|
| contested | ≥ 2 | real | the decision problem |
| uncontested | 1 | real | owner forced, no binary |
| **vacant** | 0 | filler only | real book, no incumbent — nobody can claim it by legacy |
| untapped | 0 | none | opportunity with no book at all |

Vacant zips are commercially the most interesting: they are genuinely up for grabs, with no
legacy claim on either side. They are also, under the candidacy rule, ownable by nobody — so
they need an allocation rule, same as untapped. See §6.6.

## 6. Open — needs your call

1. **Empty bundles.** Lexicographic (maximise count of positive-utility reps, then MNW among
   them) is the standard and my recommendation. The alternative is to require every rep
   non-empty and report infeasibility, which will bite on components where a rep's candidate
   zips are all interior to someone else's territory.
2. **`theta` directionality.** Is capture the same regardless of *which* rep is displaced? If
   not, `theta` becomes `theta_{i←j}` and the identification problem multiplies. The current
   code assumes a single scalar.
3. **Brute-force tier.** Re-cutting T0 by `Π_z |cand(z)| ≤ 1e6` instead of `n ≤ 20` — this
   weakens a stated acceptance criterion, so it is yours to accept.
4. **Where do the extra candidates come from?** Three-way merger, sub-territory overlap within
   one firm, or something else? It changes what the generator should produce and whether
   `cand(z)` correlates with geography. Phase 2 needs this. **Still open** — but less urgent
   now that real instances can be exported rather than generated.
5. ~~Does a rep's bundle stay inside its candidate zips?~~ **Settled 2026-08-31:** yes, and
   `cand(z) = {i : S_i(z) > 0}`, so candidacy is derivable from sales alone.
7. **How is vacancy book capitalised?** `filler_capture` selects `c_free`:
   - `theta` → `c2`, the same discount as a live rep's book. Conservative; assumes vacant
     business is as person-sticky as anyone's.
   - `full` → `c1`. **My recommendation.** `theta < 1` exists because a *departing* rep pulls
     relationships away with them; a vacancy has nobody left to pull. Whatever book survives
     an already-departed rep has, by definition, survived the departure.
   - `opportunity` → `λ`, treating orphaned book as untapped market. Defensible if the
     "sales" in vacant territories are house or inbound business with no relationship at all.

   These give materially different allocations, so the exporter reports the vacant count and
   `nway.utilities` takes the mode explicitly rather than defaulting quietly. The default is
   `theta` only because it is the no-change case; it is probably not the right answer.

6. **What owns an untapped zip?** `cand(z) = ∅` there, so no rep can take it under the rule
   above, yet it carries opportunity and it holds the graph together (regime (d) glue).
   Options: leave unallocated, assign by adjacency to the owner of a neighbouring zip, or
   admit a wider candidate set for these zips only. The exporter reports the count so the
   magnitude is visible before this is decided.


---

## 7. The national channel — reframing, decided 2026-08-31

The business is standing up a **new "national" channel**, carving the two largest firms out
of the financial-institutions and wirehouse channels, with territories targeted at roughly
equal opportunity — about **$1B each**.

That is not the two-player merger problem, and it is not quite the N-way problem either. It
is **greenfield balanced districting**. Decided: **two-stage**, with the $1B as an emergent
target rather than a constraint.

### 7.1 Nash welfare on a common measure *is* equal-size districting

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

### 7.2 The welfare decomposition

```
Σ_i g_i = Σ_z [ λ·M_z + c2·T_z + c_free·S_free ]     ← partition-invariant
        + Σ_z (c1 − c2)·S_owner(z)(z)                ← maximised by keeping zips with their incumbent
```

The objective splits into **balance the territories** and **where there is slack, leave
business with the rep who already has it**. At ~5% saturation with λ=0.3 the opportunity term
is roughly 90% of `u_i` and the book differentiation roughly 10% — so a balanced map with a
modest continuity tilt. *Check the ratio against real saturation*: it decides how much the
legacy books move the map at all.

### 7.3 Two stages

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

### 7.4 What this does to the data requirement

**Stage 1 needs almost none of the confidential data** — only `(zip, M)` and the adjacency
graph. No books, no rep ids, no shares. Opportunity is plausibly third-party market sizing.

**Stage 2 can run entirely on the work machine**, since it needs only the returned district
map plus internal books.

The descaled-export route (§5b) stays correct and is still the right channel for anything
that does need to travel, but the national-channel problem needs a fraction of it.

### 7.5 What is now the open risk

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

**Open, and gating stage 1: how many ZCTAs carry business for these two firms, and what is
the total opportunity?** The second gives `k`; the first decides whether certified optimality
is reachable at all.
