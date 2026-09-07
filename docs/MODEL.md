# The N-way model — 3+ candidate reps per zip

**Opened:** 2026-08-31 · **Split out of `NWAY.md` on 2026-08-31.** Companion files:
`docs/PROBLEM.md` (the business problem), `STATE.md` `## Facts` (every measured number),
`docs/CODE_MAP.md` (how to run anything, incl. the export route).

This file owns the settled facts about the **model**: the utilities, the propositions and their
proofs, the two stages as programs, the certificates, and the routes that were assessed with a
verdict. Sections 7 to 13 were folded in on 2026-09-07 from four files that were then deleted: the
markdown channel note, the literature reconnaissance, the power-cell contiguity option register
and the Gromov review. The commit "Step 2: …" carries the full disposition table, and every one
of them is recoverable at `git show 81bd59f:docs/<file>`.

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

**The brute-force oracle shrinks.** `docs/foundations/archive/TEST_PLAN.md` §3 acceptance is "brute-force match on
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
| 6 | Re-measure the ε noise floor; N-way S1/S2 screening | docs/foundations/archive/RESULTS.md section |

Phase 1 deliberately adds a **new module rather than editing `base.py`**: the contract is
frozen and serial-only, so the primitives get proved out standalone first and the contract
edit lands once, in the main session, with the reduction test already passing.

---

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

## 7. The two propositions, formally

Folded from the markdown channel note §3 and §4 on 2026-09-07. Both are also in the LaTeX note,
`docs/channel_note/channel_note.tex` §4 (`sec:equalsize`) and §5 (`sec:decomp`), which stays the
source of record for the typeset statement.

### 7.1 MNW on a common measure equalises

Let `Z` be the footprint with `M_z > 0`, and let `A = (A_1,…,A_k)` be a partition of `Z` into k
districts with masses `M_j = Σ_{z∈A_j} M_z`.

**Proposition 2.** For every partition, `Σ_j M_j = M(Z)` — the total is *partition-invariant*.
Consequently

```
Σ_{j=1..k} log M_j  ≤  k · log( M(Z) / k )
```

with equality iff `M_1 = … = M_k = M(Z)/k`. Hence a partition attaining equal masses, when one
exists, maximises the Nash objective, and every maximiser is as close to equal as the feasible
set permits.

*Proof.* Partition-invariance is immediate. For the inequality, relax to `m ∈ R^k_{>0}` with
`Σ_j m_j = M(Z)` and maximise `Σ_j log m_j`; the objective is strictly concave on a compact
convex set, the Lagrangian is stationary at `1/m_j = μ` for every j, so `m_j = M(Z)/k`.
Equivalently, AM–GM gives `(Π_j m_j)^{1/k} ≤ (1/k) Σ_j m_j = M(Z)/k` with equality iff all `m_j`
are equal. Every partition's mass vector is feasible for the relaxation, so the bound applies to
it, and the equality case identifies exactly the equal partitions. ∎

**Corollary 3 (strict Schur-concavity).** `Φ(m) = Σ_j log m_j` is strictly Schur-concave on
`R^k_{>0}`: if the mass vector of one partition *majorises* that of another, the first has the
lower objective value, strictly unless the two are permutations. *Proof.* `Φ` is symmetric and
strictly concave, and the Schur–Ostrowski condition
`(m_i − m_j)(1/m_i − 1/m_j) = −(m_i − m_j)²/(m_i m_j) ≤ 0` holds with equality only on the
diagonal. ∎

Corollary 3 is what makes the objective usable on a constrained feasible set: among admissible
partitions the criterion orders any two comparable mass vectors by evenness, so the search is a
search for balance even when the perfectly balanced vector is unattainable.

**These are published, named results — cite, do not prove** (literature reconnaissance,
2026-09-01). The divisible form is symmetry plus strict concavity implying strict
Schur-concavity (majorization; Marshall, Olkin & Arnold, *Inequalities*, 2nd ed. 2011, Ch. 3);
the economics name is symmetry plus Pigou–Dalton (Moulin, *Fair Division and Collective
Welfare*, 2003); the networking name is **proportional fairness** (Kelly 1997; Kelly, Maulloo &
Tan 1998).

**The integer form is NP-hard, and the caveat matters.** MNW under identical additive valuations
remains NP-hard — it *is* balanced multiway number partitioning — with a PTAS (Nguyen & Rothe,
DAM 2014) and an additive PTAS via target load balancing (Inoue & Kobayashi, IPCO 2022; Buchem
et al., ICALP 2021), whose error is measured in dollars-per-largest-zip rather than nats. So
"the $1B target needs no constraint, balance falls out" is exact in the relaxation and
misleading at the integer level: a draw's spread should be reported against the
balanced-partition gap, not against zero.

**The choice of `log` is not identified by the balance goal.** Brandl, Suksompong & Teh
(arXiv:2607.10064) show that under a degeneracy of exactly this type MNW, leximin and *every*
strictly concave additive welfarist rule coincide. A `−Σ M_j²` objective (convex quadratic,
SCIP-native, no outer-approximation cuts) has the same equal-split optimum in the degenerate
regime. The decisive test is cheap and has not been run: re-draw with the quadratic and diff the
partition.

### 7.2 Why not minimise a spread

Minimising a dispersion measure is not an efficiency criterion and can leave *everybody* worse
off — the programme's trap 2. Re-verified at `d = 0` on the paper's 50-zip toy instance (not the
channel instance): an unconstrained equalising MILP over all subsets reaches a
Kalai–Smorodinsky gap of 5.2e-8 at 98.1 % of attainable welfare, with gains (7.3226, 7.0699),
and is **Pareto-dominated** by Nash's (7.3715, 7.2318). Proposition 2 gives the balance without
the pathology, because a strictly concave increasing objective stays on the Pareto frontier by
construction. A hard band of $1B ± ε would import the pathology back as an infeasibility risk.

### 7.3 The welfare decomposition

**Proposition 4.** For any allocation `own` of all of `Z`,

```
Σ_i g_i = Σ_z [ λ·M_z + c2·T_z + c_free·S_free(z) ]      ← W_0, partition-invariant
        + (c1 − c2) · Σ_z S_own(z)(z)                     ← the incumbency premium
```

The first term does not depend on `own` at all; the second, since
`c1 − c2 = (1 − θ)(1 − λ) ≥ 0`, is maximised by giving every zip to the candidate holding the
most book there.

*Proof.* `Σ_i g_i = Σ_z u_own(z)(z)`, since each `z` contributes to exactly one rep. Expanding
`u_i(z)` at `i = own(z)` and regrouping,
`u_own(z)(z) = c2·T_z + c_free·S_free(z) + λ·M_z + (c1 − c2)·S_own(z)(z)`, in which only the last
term mentions `own`. ∎

The partition-invariant term is measured: `W_0 = B_tot = 3268.4069219934404`
(`tools/measure/premium.py::measure()`).

Combining Propositions 2 and 4 through AM–GM,

```
Σ_i log g_i = n·log( (W_0 + (c1−c2)·Σ_z S_own(z)(z)) / n )  −  D(g),
D(g) = n·log ḡ − Σ_i log g_i  ≥  0,
```

where `ḡ` is the arithmetic mean of the gains and `D(g)` vanishes exactly at perfect balance.
The measured values on the delivered k = 18 draw, and the resulting inversion of the two terms,
are in `docs/PROBLEM.md` §2 and `STATE.md` `## Facts`.

`D(g)` must not be confused with `D(M)`, the *mass* imbalance: `D(M) = 1.5e-4` nats at a mass
spread of 1.37 %, while `D(g) = 0.148` nats at a realised *gain* spread of 60.17 %. The
decomposition is written on `g`, not on `M`.

## 8. Stage 1 as center-based balanced assignment

Folded from the markdown channel note §6 on 2026-09-07.

Contiguity is unavailable on this footprint (`docs/PROBLEM.md` §5) and was never the
requirement — it was a proxy for one. What a sales territory needs is that a rep can cover it: a
tight cluster of zips around a place. So stage 1 optimises **compactness** directly, in the
centre-based formulation Hess et al. introduced for exactly this problem.

### 8.1 The programme

Let `x_z ∈ R²` be zip `z`'s internal point in an equal-area planar projection, so squared
Euclidean distance is a real area-weighted moment. With k centers `c_1,…,c_k ∈ R²` and binaries
`y_zj = 1` iff zip `z` joins district `j`:

```
min_y   Σ_z Σ_j  M_z · ‖x_z − c_j‖² · y_zj
s.t.    Σ_j y_zj = 1                       ∀ z
        Σ_z M_z y_zj = M(Z)/k              ∀ j          (equal mass, HARD)
        y_zj ∈ {0,1}
```

The mass equalities are hard, so any feasible point is exactly balanced and the objective only
chooses among balanced maps; in the band form used in practice they relax to
`|Σ_z M_z y_zj − M(Z)/k| ≤ δ`. By Proposition 2 this is the right division of labour: balance
*is* the Nash objective on a common measure, and compactness is the tie-break among its optima.
Centers are then updated Lloyd-style to the `M`-weighted centroid of each district and the
program re-solved; the loop stops when the labels repeat.

Two things are bought. The `k!` label symmetry is gone — district `j` is the one at `c_j`, so the
labels are pinned by geography. And the constraint matrix of the relaxation is a network matrix.

### 8.2 The transportation-relaxation lemma

**Lemma 6.** Fix the centers and relax `y_zj ∈ {0,1}` to `y_zj ≥ 0`. Then (1) the substitution
`η_zj = M_z y_zj` turns the constraints into a Hitchcock transportation problem with supplies
`M_z`, demands `M(Z)/k` and no upper bounds (the bounds `y_zj ≤ 1` are implied); (2) the
relaxation is feasible and every basic solution has acyclic support, hence at most `n + k − 1`
positive entries, `n = |Z|`; (3) consequently at most `k − 1` zips are **split**.

*Proof.* (1) `η_zj = M_z y_zj` with `M_z > 0` sends the placement row to `Σ_j η_zj = M_z` and the
mass row to `Σ_z η_zj = M(Z)/k`; supplies and demands both total `M(Z)`, and `η_zj ≥ 0` with
`Σ_j η_zj = M_z` forces `η_zj ≤ M_z`. (2) `η_zj = M_z/k` is feasible and the set is bounded, so a
basic optimum exists; the constraint matrix is the node–arc incidence matrix of the complete
bipartite network on `n` supply and `k` demand nodes, whose independent column sets are exactly
the acyclic edge sets, so a basic support is a forest on `n + k` nodes with at most `n + k − 1`
edges. (3) Every zip node has degree ≥ 1 and a split zip degree ≥ 2, so `n + F ≤ n + k − 1`. ∎

**Corollary 7.** Rounding a basic optimum by giving each split zip to the district holding its
largest share changes at most `k − 1` of the `n` assignments, and no district's mass moves by
more than the total mass of the split zips, at most `(k−1)·max_z M_z`.

The crude bound is not the operative fact; the **count** is, and the live run hits it exactly:
at k = 18 over 3,704 plotted zips, **17 = k − 1 zips split**, at both target choices. Those 17
carry 17.03 % of one mean district at equal-split targets and 22.08 % at own-masses targets. A
greedy repair pass then recovers what the rounding cost. That is why a heuristic can land
0.000082 nats below a bound that holds for every partition: the only unbalanced part of the
answer is `k − 1` zips wide.

**Scope of the split lemma, corrected 2026-09-01 (A3).** The published statement is
Brieden, Gritzmann & Klemm (EJOR 263(1), 2017) Lemma 4 in exactly our mass-weighted generality,
and it reads "there exists a basic optimum with at most `k − 1` splits", **not** "every optimum
has at most `k − 1`". Their Theorem 5 turns it into a quotable rounding bound
(`ε ≥ max_z M_z / κ_j`, a spread bound in business units). The underlying basis fact is
Dantzig 1963 / Ahuja–Magnanti–Orlin 1993; the OT phrasing is Peyré–Cuturi Prop. 3.4. Cite, do
not prove.

### 8.3 The rest of the pipeline

Three components surround the program, each a heuristic that §10 measures rather than trusts.

**Seeding.** `M`-weighted k-means++: the first center is a zip drawn with probability
proportional to `M_z`, each further center proportional to `M_z · d²(z, nearest chosen center)`.
Weighting by `M` rather than by zip count is the right prior when districts are equal in *mass*.

**The Lloyd loop.** Assign, move each center to its district's `M`-weighted centroid, repeat.
Unlike plain k-means there is no drift to a lopsided fixed point, because every round's
assignment is exactly balanced before rounding; the rounds buy compactness only.

**The polish.** A greedy pass over single-zip moves that strictly increase `Σ_j log M_j`,
restricted to destinations among the 3 nearest centers — the compactness guard, without which a
Nash-greedy move would send a California zip to a Florida district for an epsilon of balance.
Ties are broken toward the more compact destination, and a district is never emptied.

**Zips with no coordinates.** 44 of the 3,748 zips are absent from the geometry (41 carry no
gazetteer internal point, 3 sit outside the lower 48). They are placed afterwards by a
state-plurality rule: each goes to the district holding the plurality of already-placed zips
from its own state, ties and unknown states broken toward the district of smallest total mass,
one zip at a time with counts and masses updated after each placement.

### 8.4 The names this construction already has

Recorded 2026-09-01 so it is not presented as bespoke. Stage 1 is the **Aurenhammer–Hoffmann–
Aronov constrained least-squares assignment** (Algorithmica 1998), equivalently **semi-discrete
optimal transport** with squared-Euclidean cost; the full Lloyd loop is **weight-balanced
k-means** (Borgwardt, Brieden & Gritzmann, with iteration count ≤ n^O(dk)), **constrained
k-means** (Bennett, Bradley & Demiriz 2000), and the **generalized Lloyd algorithm for
centroidal power diagrams** (Bourne & Roper 2015, which supplies a convergence theorem and
characterises the fixed points). Cohen-Addad, Klein & Young (SIGSPATIAL 2018) ran exactly this
algorithm on exactly this problem, balanced districting on US census data. In the OR districting
literature the family is the **Hess model** (Hess et al., *Operations Research* 1965 — a
different paper from Hess & Samuels 1971) or the location-allocation heuristic. Naming it buys a
convergence theorem, a redistricting precedent, and an explainability argument (convex cells,
average under six sides) for free.

**One warning from the same literature.** Ríos-Mercado et al. (*Computers & OR* 126, 2021) run
the same location-allocation architecture with *two* balancing activities and report that the
location-allocation theoretical properties no longer hold. Our clean transportation LP, and
Lemma 6 with it, exists *because* only a single attribute is balanced. Adding workload or book
as a second hard balance destroys the structure.

## 9. Stage 2 as a linear assignment problem

Folded from the markdown channel note §5 on 2026-09-07.

**Proposition 5.** Given a drawn map `A_1,…,A_k`, let `g_ij = Σ_{z∈A_j} u_i(z)` and suppose
`g_ij > 0` for all `i,j`. Maximising `Σ_i log g_{i,σ(i)}` over injections `σ` from reps to
districts is a maximum-weight bipartite matching with weights `w_ij = log g_ij`, solved exactly
in `O(max(m,k)³)` by the Hungarian algorithm, `m` the number of reps. When `m > k` the matching
is rectangular and the unmatched reps are exactly those not staffing the channel.

*Proof.* The objective is additively separable over the pairs `(i, σ(i))` that `σ` selects, the
coefficient of `(i,j)` being `log g_ij` independently of the rest of `σ`. The injections are
exactly the matchings of `K_{m,k}` saturating the smaller side, so this is the linear assignment
problem with weight matrix `(log g_ij)`; the rectangular case is the standard padding reduction.
Positivity of `g_ij` is needed for `log g_ij` to be finite and is checked, not assumed. ∎

`g_ij` is evaluated for *every* rep on *every* district, unrestricted by legacy candidacy, which
is the entire point of drawing the map before staffing it.

**Nash and utilitarian matching disagree, and that is the reason to insist on Nash.** Two reps,
two districts, `g = [[100, 10], [90, 1]]`. The identity matching has utilitarian value 101 and
Nash value 4.605; the swap has utilitarian value 100 and Nash value 6.802. The utilitarian rule
picks the identity, handing rep 2 a district worth 1 to them because the *total* looks
marginally better. A staffing that hands a senior wholesaler a territory containing almost none
of their book is exactly the failure mode the channel cannot afford.

**What the literature calls this, and where the tractability ends** (2026-09-01). Stage 2 is
**Nash social welfare matching** (Jain & Vaish, AAAI 2024; Gokhale et al., AAMAS 2025). Our
exactness is an artifact of capacity 1 per district, which makes `Σ log` separable; the problem
is NP-hard already at capacity 2 with values in `{0,1,2}`. The MNW axiomatisations (Suksompong,
*Economics Letters* 2023; Yuen & Suksompong 2023: MNW is the unique welfarist rule satisfying
EF1) are for **endogenous** bundles and do not automatically transfer to our fixed-bundle
matching. Two consequences the note must not paper over:

- **EF1 is vacuous at stage 2 as posed.** Stage 2 is unit-demand — one district per rep — so
  removing the single good empties the bundle. The n-agent EF1 claim holds for the *joint* MNW
  allocation, not for the fixed-bundle matching except trivially.
- **Once θ > 0, plain envy is the wrong notion.** Velez (*Theoretical Economics* 11(1), 2016)
  shows **swap-based envy** is the correct notion under externalities, because swapping bundles
  is not the same as receiving the other's bundle. The claim should be restated in that form.

**Envy-freeability has a hidden cost.** Halpern & Shah (SAGT 2019): an assignment is
envy-freeable by transfers **iff** it maximises *utilitarian* welfare over bundle
reassignments. So whenever the Nash matching differs from the utilitarian one — the very case
that motivates Nash — no compensation scheme can make it envy-free. The two-line test (Hungarian
on `g` versus on `log g` over the certified districts) has not been run.

**Incentives.** On our linear domain every strategyproof and Pareto-optimal rule is dictatorial
(Schummer, *Social Choice and Welfare* 1996), so there is no strategyproof-and-efficient stage 2
to find. Countervailing: MNW's incentive ratio is exactly 2 (Bei et al., *AIJ* 2025) — a
misreport at most doubles the manipulator's utility, which is the governance number to report;
and on **binary** valuations deterministic MNW with lexicographic tie-breaking is *group
strategyproof* (Halpern et al., WINE 2020), so binarising books would buy truthfulness with no
change of rule. Neither has been tested here.

**The "books enter at stage 2 only" invariant has no cited basis (★8, 2026-09-05).** This
invariant was attributed to Fotakis & Tzamos (*ACM TEAC* 2014) — "for k ≥ 3 facilities no
deterministic anonymous strategyproof placement has bounded approximation". That attribution is
an **over-read and is withdrawn**: the theorem's hypotheses are anonymity, a *location* report
on a line or metric, and a location-vector output, and our draw satisfies none of them (it is
rep-indexed, the reported type is a per-agent measure over zips entering an objective, and the
output is a partition plus a roster). Gibbard–Satterthwaite was withdrawn for the same reason.
**Nothing has replaced either, and the basis is an open citation gap.** Losing a justification
is not the same as losing the exposure it was cited against: the 96 of 114 losing majority still
has maximal inflation incentive, and Roth's rural hospitals theorem (*Econometrica* 1986) gives
no invariance cover, because it is a property of *stable* matchings and ours is an optimisation.
The invariant therefore stands as a **prudential design choice pending a citation**, not as a
theorem. Do not re-derive a basis from memory. Audited system-of-record books are the likely
escape: compute selection from system-of-record revenue and use reported books only
within-retained.

## 10. Certifying a draw

Folded from the markdown channel note §7 on 2026-09-07. Nothing in §8 proves anything: the seeding
is random, the rounding of the `k − 1` split zips is arbitrary, and the polish is a local search.
Four post-hoc certificates say how far from optimal a drawn map is, and which questions they
leave open. They are implemented in `td/solvers/cert_draw.py` and exercised against brute force
at small k in `tests/test_cert_draw.py`.

**(i) The balance ceiling — analytic, and valid for every partition.**

**Proposition 8.** For any finite `Z` with `M_z > 0` and any partition into k parts of positive
mass, `Σ_j log M_j ≤ k·log(M(Z)/k)`, with equality iff every `M_j = M(Z)/k`. The gap
`Δ = k·log(M(Z)/k) − Σ_j log M_j ≥ 0` is invariant under a global rescaling `M ↦ κM`, and
`1 − e^{−Δ}` is the equivalent proportional shortfall in the Nash *product*. *Proof.* This is
Proposition 2 with no structural constraint imposed; for invariance, rescaling adds `k log κ` to
both sides. ∎

This needs `M(Z)` and `k` and nothing else — no geometry, no contiguity, no solver — so a draw's
gap to it is an unconditional statement about how much balance was left on the table. What it
does not say is whether the ceiling is *reachable*.

**Two ceilings are in circulation, on different bases, and the difference is not certified.**
The power-cell route's ceiling is `k·log(M/k) = 110.766768` over the 3,704 plotted zips; the
state-atom route's is `cert_draw.cert_balance_ceiling = 110.883247` over the whole instance.
The gaps they induce are two orders of magnitude apart, so the route ranking is unlikely to turn
on the difference, but **recompute on one base before any comparison leaves the project**.

**And one reference is not a ceiling at all.** The contiguity-dropped local search returns a
feasible *relaxed* value below the relaxed optimum, which orders it against the contiguous
optimum not at all. It is named `free_search`, reports 110.812355 (+0.022823 over the draw), and
**must never be quoted as a bound**. An earlier prototype quoted it as "the margin above the
draw", understating the true 0.0937 gap by about fourfold.

**(ii) The integer balance floor — an honest bound pair.** With `τ = M(Z)/k`, the best balance
indivisible zips permit with geometry ignored is the optimum `t*` of
`min t s.t. Σ_j x_zj = 1, |Σ_z M_z x_zj − τ| ≤ t, x binary`. Every real draw's max-deviation is
at least `t*`, so `t*` separates the heuristic's loss from the arithmetic's.

**Proposition 9 (the relaxation is vacuous).** The linear relaxation has optimal value 0 for
every instance and every `k ≥ 1`. *Proof.* `x_zj = 1/k` satisfies the placement rows and gives
`Σ_z M_z x_zj = τ` for every `j`, so `t = 0` is feasible and `t ≥ 0` is imposed. ∎

The root bound therefore carries no information and every nat of the dual side must be earned in
the tree, against the full `k!` symmetry. Two valid symmetry breaks help without fixing it: fix
the heaviest zip into district 0 (a relabelling, so it costs nothing), and force districts
`1,…,k−1` to non-increasing mass. So the certificate is reported as a **pair**: the lower bound
is 0 from Proposition 9, or whatever the solver earns above it within its time limit; the upper
bound is *constructive*, built by longest-processing-time greedy followed by a steepest
single-move/single-swap descent on the max-deviation, and needs no proof beyond arithmetic. The
primal half is the operative one, because it is what says whether a draw's imbalance is
arithmetic or geometry. **Not run on v2** — the conclusion drawn from it at k = 13, that the
residual imbalance is the price of geometry rather than of indivisibility, is not currently
established at k = 18, and nothing else rests on it.

**(iii) The pinned-centers assignment MILP.** Minimise `Σ_zj M_z ‖x_z − c_j‖² y_zj` subject to
`Σ_j y_zj = 1`, `|Σ_z M_z y_zj − τ| ≤ δ` and `y` binary, with `δ` defaulting to the draw's own
max-deviation so the draw is feasible for its own test. Pinning the centers removes the label
symmetry entirely, and what remains is Lemma 6's transportation problem with two side rows per
district, so the relaxation is nearly integral and a real certificate (`mip_rel_gap = 0`, trap
12) closes in minutes at production size. **What it does not certify:** the centers are the
heuristic's, so it proves the *assignment* optimal *given* them, in the sense a k-means
assignment step is optimal given its centroids. The joint problem over centers and assignment is
untouched. Nor does it certify the stage-1 objective, since the constraint is a max-deviation
band and not `Σ_j log M_j`, so a strictly more compact assignment inside the band may have
slightly lower Nash value; both values are returned so the trade is visible. **Not run on v2.**

**(iv) The power-diagram dual — no solver in the trusted path.** Added after the LaTeX note was
written. Dual feasibility for the transportation LP reads `α_z + M_z β_j ≤ M_z d²(z, c_j)`, so an
optimal assignment puts each zip in the district minimising `d²(z, c_j) − β_j` — the **power
(Laguerre) diagram** of the centers with weights `β`. The dual program is

```
max_{α,β}  Σ_z α_z + τ·Σ_j β_j     s.t.   α_z + M_z β_j ≤ M_z ‖q_z − c_j‖²   ∀ z, j
```

Any feasible `(α, β)` is a lower bound on the inner LP by weak duality, so verification is
`O(nk)` arithmetic: dual feasibility plus equality of the two objectives. **Feasibility alone
certifies nothing** — `α = β = 0` is feasible — which is why the objective row is part of the
check. `centers.power_weights` returns the weights and the split zips' row indices, surfaced as
`power_diagram_of_draw`'s `split_zips`; `us_maps.power_cells` draws the territory exactly, as k
convex cells.

**Two traps found in building (iv), both real wrong-answer bugs rather than tolerance issues.**
The bound must be taken at the **draw's own masses**, not the equal split: a draw whose
max-deviation is a fraction of a percent is infeasible for exact equality, the LP bound can then
exceed the draw cost, and the gap comes out negative (pinned by
`test_the_default_targets_are_the_draws_own_masses`). And the LP must be posed with bounds
`[0, inf)`, not `[0, 1]`: the feasible sets are identical, since the placement rows already force
`x ≤ 1`, but with an explicit upper bound HiGHS parks a reduced cost on it and the returned duals
violate dual feasibility by −0.80 instead of −5e-17.

**The two target choices answer different questions and must not be quoted interchangeably.**
Equal-split targets dominate own-masses targets for *producing* a zero-mismatch draw; own-masses
remains the right choice for *auditing* an existing draw, because it holds balance fixed
district by district and so isolates compactness. `power_diagram_of_draw` defaults to own-masses
and takes `targets="equal"` for the other.

## 11. Power-cell contiguity: the routes and their verdicts

Folded from `docs/OPTIONS_power-cell-contiguity.md` on 2026-09-07. The requirement itself, and
what "zero" means, are in `docs/PROBLEM.md` §8; every measurement is in `STATE.md` `## Facts`.
Options 0 and 1 (measure the drift; largest-contiguous-piece fractions) were the measurements
that ranked the rest and are closed; their outputs are in `## Facts`.

**Region contiguity in the plane is already a theorem, and this is the reason the route exists.**
Complementary slackness on the balanced-assignment LP says an optimal assignment sends zip `z`
to the district minimising `d²(z, c_j) − β_j`, which is a power (Laguerre) diagram. Every
bisector is a straight line, so every cell is an intersection of half-planes and therefore a
convex polygon. The territory map the business is shown is `k` convex regions with exact
straight borders. There is nothing to enforce.

**Three sources of drift** separate the shipped labelling from that diagram: `improve()` moves
zips after the LP to repair the balance that integral rounding cost; the LP's basic solution
splits at most `k − 1` zips, each rounded to one side; and `power_weights` returns both `labels`
(the true power cells) and `lp_labels`, which need not agree.

**Option 2 — snap to the diagram. The primary route, and Route A is measured.** Ship
`power_labels(xy, centers, weights)` as the draw instead of the polished labels: zero mismatches
by construction, because the labelling *is* the diagram.

- *Route A, snap post-hoc.* Take the committed draw's centers, get weights from the duals,
  relabel. The single-shot snap is not self-consistent — relabelling moves the `M`-weighted
  centroids — so the object wanted was a fixed point of snap → recentroid → snap. **There is no
  fixed point.** Twenty iterations on the live instance reach no fixed point and no exact
  repeat, the objective is non-monotone, and the iterates wander a band of roughly spread
  2.1–5.6 % and gap 0.00028–0.00128. Read it as a **search, not a convergence**: every iterate is
  a power diagram, so every one has zero mismatched zips and convex cells by construction,
  feasibility is not at stake in choosing among them, and taking the best iterate is legitimate.
  Best of 20 is iteration 15 at spread 2.1051 % and gap 0.000283.
- *Route B, make the diagram the search space.* Remove the `improve()` polish from
  `centers.draw` and close the residual balance error by moving *weights* rather than individual
  zips — weights are the diagram-preserving lever, since a larger `w_j` enlarges cell `j` at its
  neighbours' expense. Closer to the existing code than it sounds: the Lloyd loop already solves
  the LP whose duals are the weights. **Not built.** Judge it against iteration 15's
  2.1051 % / 0.000283, **not** against the 4.0041 % single shot, or it will look better than it
  is.

**The shared hard limit, and it binds both variants.** With indivisible zips no power diagram
hits exact equal masses in general. The LP hits them only fractionally, on at most `k − 1 = 17`
split zips, and rounding those is irreducible. Those 17 carry 17.03 % of a mean district at
equal-split targets (largest, `20814`, 3.699 % of one). That residual, not the mismatch count,
sets the achievable spread floor, and no zero-mismatch route should be expected to return to the
committed draw's 1.2902 %.

**Option 3 — constrain the polish. Hold.** Keep `improve()` but restrict its swaps to moves that
leave each district a power cell, which reduces to a sign check on `d²(z, c_j) − w_j`. Exact zero
mismatch, recovers less balance than the unconstrained polish by construction, about half a day
and a smaller diff than Route B. It is strictly dominated by Route B if Route B works, since
Route B removes the polish rather than constraining it. Keep it as the fallback if removing the
polish costs more balance than the measurements suggest.

**Option 4 — hard graph contiguity in a single SCIP tree. Do not start it for this requirement.**
Lazy minimal-separator cuts (PySCIPOpt) on the center-based Hess formulation. It is the only
route with a certificate on the zip adjacency graph, with the gap reported natively. But it does
not address the zero-mismatch requirement, which options 2 and 3 do; and on v2's 862 components
it needs pre-aggregation to be non-vacuous, at which point it has rebuilt the state-atom route.
Revisit only if graph contiguity itself becomes a stated requirement. Two traps carry over:
separator cuts must be **component-wise**, one root per district per component, or the dual bound
is unsound; and SCIP needs `misc/allow{strong,weak}dualreds` off for any lazily separated model,
`g ≤ Σu·x` rather than `==`, and a gain lower bound from the incumbent.

**Option 5 — make contiguity emergent via a travel term. Out of scope, recorded so it is not
rediscovered as new.** Replace the utility with
`u_i(z) = c1·A_z + c2·B_z + λ·M_z − κ·d(z, p_i)`, `d` the graph shortest-path distance to rep
`i`'s base `p_i`. With `κ` dominating the data-term variation the free Nash solution is an
additively weighted graph-Voronoi partition, whose cells are connected by construction, and `κ`
replaces `ρ` with a behavioural reading. At moderate `κ` the constraint is still needed. The cost
is high and mostly non-technical: it needs rep base locations, changes the settled utility
model, redistributes welfare, and needs distribution sign-off. Assessed 2026-08-28.

**Assessed and rejected.**

| Candidate | Reason |
|---|---|
| Shirabe one-shot flow formulation | Loses to cut-based branch-and-cut above a few hundred units; v2 has 3,748 zips. Still useful as a small-instance cross-check oracle, since it shares no cut-generation code. |
| OR-Tools CP-SAT | No lazy constraints at all, and no continuous log. |
| Zhang–Validi–Buchanan–Hicks linear-size planar formulation | Integral for pure connected partitioning, but the authors report it underperforms Hess once value and balance constraints are added, which is exactly our coupling. |
| METIS / multilevel coarsening | Heuristic, does not preserve connectivity on refinement, and smooths the heavy tail the map exists to show. |

**Cross-route comparison, with its caveat.** The state-atom route sits at gap 0.093715 nats and
30.484 % spread. A zero-mismatch power-cell draw at 0.000283 nats and 2.1051 % spread is better
on both axes by a wide margin, is the only one of the two whose territory is convex and whose
dots agree with its fill, and is ahead on the shared zip-catchment contiguity measure once
snapped. But the two gaps are on different bases (§10), so recompute both on one base before
quoting the comparison to a sponsor.

## 12. The VBL line: how ours differs, and the options for merging

Folded from the markdown channel note §8 on 2026-09-07 (written 2026-09-06; not present in
`channel_note.tex`). The reference line is Validi, Buchanan & Lykhovyd, *Imposing contiguity
constraints in political districting models* (Operations Research 2021, DOI
10.1287/opre.2021.2141) and Validi & Buchanan, *Political districting to minimize cut edges*
(MPC 2022, DOI 10.1007/s12532-022-00221-5).

**What VBL solve.** Hess variables `x_ij = 1` iff unit `i` joins the district *centred at* unit
`j`, with `x_jj = 1` marking `j` a centre and the centres chosen **by the solver**. A linear
compactness objective (cut edges, or a moment-of-inertia sum), extended to a Polsby-Popper
perimeter ratio by Belotti, Buchanan & Ezazipour 2025, which makes it an MISOCP. Balance is a
**hard constraint**, population within ±ε of ideal, ε typically 1 %. Contiguity is lazily
separated cuts, and their comparison of the families (`lcut` / `scf` / `mcf` / Shirabe flow) is
the paper's main contribution — the a–b separator cut with its two branches is the same object
our own `scip_tree` separates. Symmetry is broken by construction, since districts are named by
their centre unit. Their headline: *districting does not get harder when contiguity is imposed*;
on their instances the contiguity constraints often help, by cutting off fractional solutions the
balance rows alone admit.

**Three differences, once the running code rather than the stated problem is compared.**

1. *Centres: chosen versus fixed.* VBL choose the centres inside the same program; we fix them
   by Lloyd iteration and solve only the assignment. That single difference is the entire
   certified/uncertified boundary in this project. The joint problem is a compactness question;
   on the Nash objective Proposition 8 already closes it at 8.2e-5 nats for every partition,
   centres included.
2. *Integrality.* Programme (centers) in §8.1 is the Hess model with integrality dropped and the
   centres fixed. Lemma 6 says the first removal is nearly free — at most `k − 1` zips split,
   measured as exactly 17. The second removal is not free. Note that Lemma 6's near-integrality
   is a property of the fixed-centre problem only: once the centres are decision variables the
   constraint matrix is no longer a transportation matrix and the Hess LP relaxation is weak
   (VBL's fixing and symmetry work exists because of it), so restoring the centres also forfeits
   the free integrality.
3. *Contiguity: cuts versus convex cells.* VBL pay for contiguity with separator cuts on a
   connected unit graph. We cannot: the sold-zip graph has 862 components, so the constraint is
   infeasible rather than hard. Instead we take the geometric property the LP's dual hands us for
   free, the convexity of the power cells. Its three leaks are measured: the labelling is not the
   diagram, the diagram moves when you recentroid, and a convex cell of scattered points is not a
   single served blob.

Two further differences separate the *stated* problem P0 from VBL but not the running code from
VBL, and are discounted. **Objective:** P0 maximises `Σ_j log M_j`, which Proposition 2 says *is*
balance, so the two setups swap which of balance and compactness is the objective; but the
implemented stage 1 minimises the same moment-of-inertia functional VBL use, and the log enters
only in the polish and the certificates. **Balance:** their ±1 % is a feasibility question and in
P0 balance is graded; but the implemented mass rows are a hard equality relaxed to a band, so the
running code and VBL agree. Trap 2's refusal of a band is a two-player fact about reps with
*different* utilities; on a common measure Proposition 2 makes a band at the achievable level
exactly the near-optimal set of the Nash objective, so a tight band is sound for stage 1. The
refusal stands for stage 2, where the utilities differ.

**A difference in the other direction.** The power-diagram dual certificate, the analytic Jensen
ceiling and the exact stage-2 Nash matching are ours; none has a counterpart in the VBL line
(§13).

**Two modelling conventions are load-bearing in any merge.** `g_j ≤ Σ_z M_z x_zj` is written as
an inequality, never an equality: the objective increases in `g_j` so it is tight at every
optimum, but an equality lets presolve aggregate `g_j` out and every in-callback `trySol` then
dies (trap 14). And `log` enters through an epigraph variable `w_j ≤ log g_j`, which a solver
either recognises as convex (SCIP does) or approximates by outer-approximation tangents
`w_j ≤ log ĝ + (g_j − ĝ)/ĝ` at incumbents `ĝ`, generated lazily.

**Two more are forced by combining the log with Hess naming, which VBL never had to do**, because
a linear objective gives an inactive centre a zero contribution for free. Under Hess naming `j`
ranges over units, so for the `n − k` units with `x_jj = 0` the mass is 0 and `w_j ≤ log 0 = −∞`:
the objective is `−∞` for every `n > k`, and a row `g_j ≥ g_min` for all `j` is infeasible. The
fix is the perspective pair

```
w_j ≤ log( g_j + τ·(1 − x_jj) ),      g_j ≥ g_min · x_jj
```

concave in an affine argument, under which an inactive centre contributes exactly `log τ`; there
are exactly `n − k` of them, so the offset is a constant. And `g_min` is **derived from the
incumbent value `V`, not guessed**: any solution worth at least `V` has
`log g_j ≥ V − (k−1)·log(M(Z)/(k−1))`, so
`g_min = exp(V − (k−1)·log(M(Z)/(k−1))) ≈ τ·((k−1)/k)^{k−1} ≈ 0.378 τ` at k = 18, which caps the
log's gradient at `1/(0.378 τ)`. The row is not cosmetic: without it the gradient at the lower
bound is about 1e9 and SCIP's LPs go unstable.

**The five options, with the recommended order.**

- **Option A — exact contiguity on a restored graph.** Separate VBL's contiguity cuts on a graph
  that includes the unsold glue, so "contiguous" means one region of the country rather than one
  component of the sold-zip graph. Three corrections shape it. *Size:* the full ZCTA set is about
  33,000 units, Hess naming squares that (~1e9 binaries) and restricting candidate centres to the
  3,748 sold zips still gives 1.2e8, so A must be a **labelling** model, `j ∈ {1,…,k}`, at
  33,000 × 18 ≈ 600,000 binaries with the `k!` symmetry broken as in §10(ii); or a
  mixed-granularity graph, sold zips as units and unsold ZCTAs contracted to counties as glue,
  roughly 7,000 units and 126,000 binaries. *Objective:* the log objective is flat, and
  astronomically many contiguous partitions sit in the band the draw already occupies, so a
  log-only solver returns an arbitrary one of them, tendrils included — which is why VBL minimise
  cut edges. A needs compactness as the objective and balance as a band at the draw's own `δ`.
  *What it certifies:* not the stage-1 Nash value, which Proposition 8 already certifies, but the
  price of exact region-contiguity against the power-diagram surrogate. *Costs:* districting an
  object the channel does not sell in (a business objection, not a technical one), a solver at
  1e5–1e6 binaries, and the k-way extension of a solver written for two players.
- **Option B — cuts on the atom graph only.** The state-atom route already builds a graph where
  contiguity is meaningful: 56 atoms, 126 edges, one component. VBL separator cuts apply directly
  and at trivial scale, replacing `atom_draw.py`'s local search plus `check_contiguous`
  post-check with a certificate. It says whether the atom route's 0.0937-nat gap and 30.5 %
  spread are the price of contiguity at atom granularity or the local search failing. It keeps
  the log as the objective: at three atoms per district there is no tendril for a compactness
  term to guard against. It must carry the perspective rows. *Risk:* the answer is certified for
  the atom instance, not the zip instance, and the two ceilings sit on different bases —
  reconcile them in the same pass.
- **Option C — pre-aggregate, then B.** Swamy, King & Jacobson (2023, DOI
  10.1287/opre.2022.2311) give a multilevel matching-based contraction; coarsen to a few hundred
  units, solve exactly, uncoarsen. The mathematics is B's on a contracted ground set and the
  content is entirely in the contraction. *Risk:* uncoarsening is where the objection bites —
  a contraction that does not preserve connectivity on refinement returns a disconnected district
  from a certified-contiguous solution, which is exactly why METIS-style coarsening was rejected
  above. Swamy's matching-based version must be checked against that, not assumed to escape it.
- **Option D — low-diameter compactness, no adjacency needed.** Zhang, Silveira, Validi, Smith,
  Buchanan & Hicks (IJOC, DOI 10.1287/ijoc.2025.1448) certify a bounded **metric** diameter
  rather than adjacency connectivity, and metric diameter is defined on a disconnected graph, so
  this is the one piece of their machinery that applies unmodified. The conflict row
  `x_uj + x_vj ≤ 1` for `d(u,v) > D` bounds each district's diameter without mentioning
  adjacency, and sweeping `D` traces a compactness-versus-balance frontier the Lloyd loop cannot
  express. Two defects as written: the districts are anonymous, so the `k!` symmetry returns; and
  the LP relaxation is vacuous (`x_zj = 1/k` satisfies every conflict row for `k ≥ 2`), so as
  with the integer floor every nat is earned in the tree. The radius form under Hess naming,
  `x_zj = 0` whenever `d(z,j) > D/2`, removes both as a *fixing* rather than a row, at the price
  of a stronger constraint than the diameter cap.
- **Option E — leave the two lines apart, and say so.** Keep the power-cell route, cite VBL for
  the cut families already shared, and record the divergence as deliberate. E does not lose the
  claim "this map is balance-optimal", which is supportable today at 8.2e-5 nats against a
  ceiling valid for every partition; only "optimally compact" and "contiguous" stay unsupported.

**Recommended order (2026-09-06).** (1) **Option B**, because it is small, the graph exists, and
it converts the atom route's headline number from "local search against a relaxation" into a
certificate; reconcile the two ceiling bases in the same pass. (2) **Option A**, re-specified as
above and gated on a sponsor question rather than an experiment: run it only if
region-contiguity must be *certified* rather than shown on a map, since the power cells already
give convex regions at 0.0003 to 0.0007 nats. (3) **Option D** only if a diameter cap becomes a
stated business rule. (4) **Option C** only if A is commissioned and its ground set proves too
large, which on the corrected frontier it probably will not. E is the record for the zip instance
until (2) is commissioned. The decision between (1) and (2) is the sponsor's, not mathematical:
which claim beyond balance must be certified, compactness or region-contiguity. Balance is done.

## 13. The niche, and the verified absences

Folded from `docs/RESEARCH_FINDINGS.md` §7 and §8 on 2026-09-07. The full 130-entry annotated
bibliography from the 2026-09-01 overnight reconnaissance is recoverable at
`git show 81bd59f:docs/RESEARCH_FINDINGS.md`; its BibTeX survives as
`literature/RESEARCH_ADDITIONS.bib`; the curated per-domain literature is
`docs/foundations/LIT_optimization.md` and `docs/foundations/LIT_economic-theory.md`, which are
frozen and read-only.

**The five nearest published papers** to "maximum Nash welfare balanced districting without
contiguity, with post-hoc certificates": Brieden, Gritzmann & Klemm 2017 (our stage-1 machinery
including the split lemma, minus the Nash framing); Cohen-Addad, Klein & Young 2018 (our exact
algorithm on our exact problem class, no certificates, no welfare objective); Fravel et al. 2026
(dual bounds for nonconvex districting objectives reported beside heuristics — our certificate
culture, a different objective); Jain & Vaish 2024 (our stage 2, as a computational object);
Mancho, Markakis & Protopapas 2025 (MNW under equal-size-bundle constraints, the nearest theory
result to "Nash + balance").

**Is the niche occupied? No.** Each neighbour holds one or two of the four components
(balance-by-diagram, no-contiguity, Nash objective, post-hoc certificates); none holds three.

**Four absences verified with recorded search provenance, and they are ours to claim.**

1. **No price-of-connectivity bound for Nash welfare exists**, on any graph class including paths
   and trees. The 2026 sequel that would contain it (Bei, Lam, Lu & Suksompong, *DAM* 385) prices
   the egalitarian and utilitarian cases; a full-text scan of the ar5iv rendering of
   arXiv:2405.03467 finds the string "Nash" absent.
2. **No districting paper formulates districting as Nash-welfare maximisation.** Every
   Nash-product paper indexes the product by agents with preferences; Kaneko & Nakamura 1979 is
   the licence for the move, and no precedent executes it.
3. **No application of capacity-constrained power diagrams or semi-discrete OT to commercial or
   sales-territory design.** All applications found are political, graphics or materials.
4. **No model jointly performs territory alignment and rep retention/selection.** Nearest are
   Moya-García & Salazar-Aguilar 2020 (headcount, not identity) and Zoltners 2011. Also: no
   territory paper derives incumbent-preservation *from the objective* — the field's default is
   an explicit change penalty (Bender et al. 2016) — and no sales paper states the `≤ k − 1`
   corollary.

**The flip side, and it must be said with the claim.** Nobody has stress-tested the bridge for
us, and the components individually are all known (§7, §8, §9). Any contribution claim must be
re-scoped to the *combination* and to the open theorems, not to the parts.

**One absence is a research risk rather than an opening:** there is no exact branch-and-price for
districting with a Nash or log master, because the master becomes conic and the pricing duals
need derivation; and no paper solves MNW via mixed-integer exponential-cone programming, with
MISOCP (Saghand & Charkhgard 2022, geometric-mean cones) the proven adjacent route.
