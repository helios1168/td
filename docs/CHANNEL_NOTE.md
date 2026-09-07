# Balanced districting for a national sales channel

**The model, the two-stage scheme, and the certified draw.**

A markdown rendering of `docs/channel_note/channel_note.tex`, carrying its sections 1, 2, 4, 5,
6, 7 and 8, plus a new section 8 comparing the setup to the Validi–Buchanan–Lykhovyd (VBL)
districting line and setting out the options for merging the two.

Omitted from the source note: §3 (scale invariance), §9 (the component-allocation ceiling,
demoted there) and §10 (open questions). The two omitted propositions that other sections lean
on are the scale-invariance proposition (§3) and the component balance ceiling (§9); both are
cited below where they are used, and neither is restated.

Source of record for the problem is `docs/CHANNEL.md`; for the model, `docs/MODEL.md`; for the
data route, `docs/DATA.md`. Implementations: `td/model.py` (the n-way primitives),
`td/channel.py` (stage 2 and the ceiling), `td/solvers/centers.py` (stage 1),
`td/solvers/cert_draw.py` (the certificates).

---

## On the numbers

**Every figure here is v2**, the live instance `instance_descaled_v2.json.gz`, sourced from
`STATE.md` `## Facts`. The LaTeX source note is dated 2026-09-01 and its generated macros
(`docs/channel_note/ceiling_numbers.tex`) are still v1, at k = 13 over 1,229 zips; none of those
values appear below.

Three consequences of that substitution, stated rather than papered over:

- **Where v2 has no measurement, the number is dropped and the gap named.** This affects the
  integer-balance-floor certificate, the pinned-centers assignment certificate, the portfolio
  seed comparison, and the regional shares of the footprint. Each is flagged in place.
- **The mathematics is unaffected.** Every proposition is a statement about an arbitrary finite
  instance; only the illustrations move.
- **`ceiling.py` still generates v1 macros.** Rebuilding the PDF from that file reproduces the
  v1 figures, not these. Only `SATURATION` has been carried to v2, which is why the §4.1 sizing
  numbers below agree with both documents.

---

## 1. The instance and the re-scoping

*(`channel_note.tex` §1, `sec:setup`)*

The programme's original problem was bilateral. Two sales forces merge; a national *census*
intersects the two legacy representative maps and decomposes the country into contested
components, each with one A-rep and one B-rep; inside a component the zips are divided between
them by maximum Nash welfare subject to hard contiguity. Everything downstream — one binary per
zip, a scalar exchange rate $u_a(z)/u_b(z)$, the separator cut with its "a branch" and its
"b branch" — inherits that two-sidedness.

The new problem is not a merger. A *national channel* is being created by carving the two
largest manufacturers out of the existing financial-institutions and wirehouse channels, and its
footprint is to be divided into territories of roughly equal opportunity. Two structural
consequences follow.

First, **there is no pair structure to decompose along**: the census's components came from the
overlap of two legacy maps, and a greenfield channel has no such overlap, so what was many
independent 30–500 zip subproblems becomes one k-way partition of the whole footprint.

Second, **the objective's argument changes measure**: what is to be balanced is *opportunity*, a
quantity attached to the territory and not to any representative — the same for every candidate
owner. That single change turns the Nash criterion into a balance criterion exactly (§3), which
is the main structural result of this note.

| | |
|---|---|
| zips carrying sales | 3,748 (3,704 mappable: 41 lack a gazetteer point, 3 sit outside the lower 48) |
| distinct representatives | 114 |
| node classes | 718 contested / 1,447 uncontested / 16 vacant / 1,567 untapped |
| untapped share of opportunity | 15.7% |
| aggregate saturation $\sum T/\sum M$ | 29.588% |
| mapped opportunity | 8,468.3 descaled units over the 3,704 plotted zips |
| footprint | **national** (v2 regional shares not measured) |
| sold-zip Rook adjacency | 862 components, 516 singletons; largest 13.5% of M; 47.6% of M in components under 1% each |
| territory target | ~\$1B ⇒ **k = 18** |
| firms | A = `F0`, 53 reps, 41.1% of book; B = `F1`, 61 reps, 58.9%; both hold book in 671 zips carrying 48.8% of mapped opportunity |

The instance is the descaled real export. `STATE.md` `## Facts` carries the v1-to-v2 comparison
for anyone who needs it; this note does not.

### Three readings of the table

**Scale.** 3,748 units against 18 districts is 67,464 assignment binaries, an order of magnitude
above the 135 zips the programme's own single-tree solver certifies on the two-player problem —
and at k = 18 districts rather than two, which is where the binaries come from. Against the
published exact districting line this is *not* a frontier instance; see §8.1, which corrects the
source note's claim on this point.

**Adjacency contiguity is not a usable constraint on this footprint** — and this is the decisive
reading. The channel sells in 3,748 zips scattered across the country, so the Rook adjacency
graph *restricted to sold zips* has 862 components, 516 of them singletons: the largest holds
13.5% of opportunity and 47.6% of opportunity sits in components holding under 1% each. A
contiguous k-partition of that graph does not exist for any k below several hundred, and at
k = 18 the constraint is not binding-but-hard, it is **infeasible**. Restoring contiguity would
mean re-exporting the unsold "glue" zips — most of the country — and districting an object the
channel does not sell in.

The decision (2026-09-01) is therefore to drop adjacency and keep the geometric requirement that
contiguity was standing in for: **compactness**. Stage 1 becomes center-based balanced assignment
on planar equal-area coordinates (§6).

Contracting the instance graph to states does not rescue it either: that gives only 10 edges over
42 components, which is why a state-level model must import the TIGER state rook graph (49 nodes,
107 edges) that `td/geo.py::state_rook` builds.

**Granularity is benign.** The transportation LP splits exactly 17 zips (§6.2), and those 17
carry 17.03% of one mean district's mass at equal-split targets — the largest of them, `20814`,
is 3.699% of a mean district. So the entire indivisibility problem is under a fifth of one
district wide, and §7 turns that into a certificate rather than leaving it as an intuition.

A fourth reading is a business question rather than a mathematical one: 114 representatives
against 18 territories is a 6.3:1 ratio. The reading that makes sense of it is that the channel
is a *specialist carve-out* staffed by a handful of senior wholesalers while the remaining
representatives keep covering the other manufacturers in the existing channel; the unmatched
representatives of §5 are therefore *not selected for this channel*, not released. If that
reading is wrong, stage 2's framing needs revisiting.

---

## 2. The utility model with n representatives

*(`channel_note.tex` §2, `sec:model`)*

### 2.1 Definition

Fix a zip $z$. Let $S_i(z) \ge 0$ be representative $i$'s booked production at $z$, let

```math
T_z = \sum_j S_j(z) \tag{Tz}
```

be all production booked to a named representative there, let $S_{\mathrm{free}}(z) \ge 0$ be production
booked at $z$ under no named representative (§2.3), and let $M_z > 0$ be the market opportunity.

Two parameters translate these into value: the **transfer capture** $\theta \in [0,1]$, the fraction of
another representative's book an inheriting representative retains, and the **headroom credit**
$\lambda \in [0,1]$, the rate at which untapped opportunity counts against booked production. With the
net headroom convention $c_1 = 1 - \lambda$, $c_2 = \theta (1 - \lambda )$:

```math
u_i(z) = c_1 S_i(z) + c_2\bigl(T_z - S_i(z)\bigr) + c_{\mathrm{free}} S_{\mathrm{free}}(z) + \lambda M_z \tag{util}
```

The inheriting representative keeps $c_1$ of their own book, captures $c_2$ of everyone else's,
capitalises unowned book at a rate $c_{\mathrm{free}}$ decided separately, and is credited $\lambda$ of the whole
opportunity. Note that $T_z$ in (Tz) runs over named representatives only; $S_{\mathrm{free}}$ enters
(util) through its own term.

> The implementation follows this exactly (`model.utilities`). Its headroom validator
> `model.headroom_violations` is deliberately *more* conservative: it folds $S_{\mathrm{free}}$ into $T_z$
> and treats the filler as a possible holder, so a zip whose orphaned book alone exceeds its
> opportunity is still flagged.

Headroom generalises verbatim: the model requires

```math
M_z \ge \max_i \bigl(S_i(z) + \theta (T_z - S_i(z))\bigr) \tag{headroom}
```

An **allocation** is a map $\mathrm{own}: Z \to R$ from zips to representatives, and each representative's
**gain** at disagreement point `d = 0` is the bundle utility

```math
g_i = \sum_{z\,:\,\mathrm{own}(z)=i} u_i(z) \tag{gain}
```

The criterion is maximum Nash welfare (MNW), the Nash bargaining solution (Nash 1950) at
`d = 0`, equivalently the Eisenberg–Gale objective (Eisenberg & Gale 1959):

```math
\max_{\mathrm{own}} \sum_i \log g_i \qquad \text{subject to the geometric constraint.} \tag{mnw}
```

Nothing in the outer-approximation argument that makes (mnw) exactly solvable was ever
two-player: `log` is concave and $g_i$ is linear in the assignment, so this remains a convex
MINLP with a genuine optimality certificate (Duran & Grossmann 1986; Fletcher & Leyffer 1994).
The fairness guarantee survives the move for the same reason — Caragiannis et al. (2019) state
Pareto efficiency and envy-freeness up to one good for n agents, not two.

### 2.2 The model reduces to the two-player one

**Proposition 1 (two-representative reduction).** Let `n = 2` with `R = {a,b}`, $S_a(z) = A_z$,
$S_b(z) = B_z$ and $S_{\mathrm{free}} \equiv 0$. Then (util) is identically the two-player model,

```math
u_a(z) = c_1 A_z + c_2 B_z + \lambda M_z, \qquad u_b(z) = c_2 A_z + c_1 B_z + \lambda M_z,
```

and (headroom) is identically $M_z \ge \max(A_z + \theta B_z, B_z + \theta A_z)$.

*Proof.* $T_z = A_z + B_z$, so $T_z - S_a(z) = B_z$ and $T_z - S_b(z) = A_z$; substituting into
(util) with $c_{\mathrm{free}}\cdot S_{\mathrm{free}} = 0$ gives the two displayed expressions. For (headroom), the maximum
runs over $i \in \{a,b\}$ and gives $\max(A_z + \theta B_z, B_z + \theta A_z)$. ∎

This is not a formality. It is what keeps the entire committed corpus of two-player results —
the paper's worked 50-zip instance, the C1–C9 battery, every certified harness row —
interpretable under the new model, and it is asserted numerically rather than argued:
`test_model.py::test_two_rep_reduction` requires every n-way primitive to agree with the frozen
two-player `base.py` to floating-point equality on a two-representative instance.

### 2.3 Unowned book: the vacancy filler

Some territories currently have no assigned representative, and their production is booked under
a **filler key**: a representative-shaped sentinel that carries real sales, real opportunity and
a real manufacturer, but is not a person. It must never become a candidate owner. A filler key
with an objective term would have the solver bargaining on behalf of an empty chair, and because
$\sum _i \log g_i$ is unbounded below as any $g_i \to 0$, it would trade real representatives' welfare
away to feed it.

The schema separates the two roles, which is what makes the exclusion cheap: $T_z$ is computed
from *all* books, but the assignment ranges over *candidates* only, and candidacy is
$\mathrm{cand}(z) = \{i : S_i(z) > 0\}$ with filler keys removed. Orphaned production therefore arrives as
its own attribute $S_{\mathrm{free}}$ and is capitalised by whoever inherits the zip. Four node classes
result, with the export's counts:

| class | $\lvert\mathrm{cand}(z)\rvert$ | book | count |
|---|---|---|---|
| contested | ≥ 2 | real | 718 |
| uncontested | 1 | real | 1,447 |
| vacant | 0 | filler only | 16 |
| untapped | 0 | none | 1,567 |

Contested zips are the decision problem; an uncontested zip's owner is forced under a legacy rule
but it still carries utility; a vacant zip has real book and no incumbent, so nobody can claim it
by legacy; an untapped zip is opportunity with no book at all. Under the two-stage scheme none of
the four is dropped — stage 1 partitions on $M_z$ alone, so every zip lands in a district by
construction, and candidacy re-enters only at stage 2.

**The untapped class is now the large one.** 1,567 of 3,748 zips are untapped, carrying 15.7% of
opportunity. $\mathrm{cand}(z) = \emptyset$ there, so no representative can take such a zip under the candidacy
rule, yet it carries opportunity and holds the graph together. What owns an untapped zip is an
open decision (`docs/MODEL.md` §6): leave unallocated, assign by adjacency to a neighbour's
owner, or admit a wider candidate set for these zips only.

**Choosing $c_{\mathrm{free}}$.** Three coefficients are defensible, and they give materially different
maps, so the implementation takes the mode explicitly (`filler_capture`) rather than defaulting
quietly.

- `theta` ($c_{\mathrm{free}} = c_2$) discounts orphaned book exactly like a live representative's;
  conservative, and it assumes vacant business is as person-sticky as anyone else's.
- `opportunity` ($c_{\mathrm{free}} = \lambda$) treats it as untapped market; defensible if the sales in vacant
  territories are house or inbound business with no relationship content.
- `full` ($c_{\mathrm{free}} = c_1$) is **the recommended choice**: the reason $\theta < 1$ exists at all is that
  a *departing* representative pulls relationships away with them, and a vacancy has nobody left
  to pull — whatever book has survived an already-departed representative has, by definition,
  survived the departure, so discounting it again double-counts an attrition that has already
  happened.

The current default is `theta`, only because it is the no-change case. It is probably not the
right answer. At 16 vacant zips out of 3,748 the choice is unlikely to move this instance's map;
it is recorded because the model outlives the instance.

---

## 3. Nash welfare on a common measure is equal-size districting

*(`channel_note.tex` §4, `sec:equalsize`)*

This is the centrepiece. In the two-player problem the objective and the balance of the two
territories were different things; the Nash criterion was chosen for its axioms and its
efficiency, and balance was a by-product. On a **common measure** they coincide exactly.

Let `Z` be the footprint with $M_z > 0$, and let $A = (A_1,\dots,A_k)$ be a partition of `Z` into k
districts, with masses $M_j = \sum _{z \in A_j} M_z$.

**Proposition 2 (MNW on a common measure equalises).** For every partition of `Z` into k parts,
$\sum _j M_j = M(Z) := \sum _{z \in Z} M_z$ — the total is *partition-invariant*. Consequently

```math
\sum_{j=1}^{k} \log M_j \;\le\; k \log\frac{M(Z)}{k} \tag{ceilbasic}
```

with equality if and only if $M_1 = \dots = M_k = M(Z)/k$. Hence a partition attaining equal masses,
when one exists, is a maximiser of the Nash objective, and every maximiser is as close to equal
as the feasible set permits.

*Proof.* Partition-invariance is immediate: each $z$ lies in exactly one part, so
$\sum _j M_j = \sum _j \sum _{z \in A_j} M_z = \sum _{z \in Z} M_z$.

For the inequality, relax to $m \in \mathbb{R}^k_{>0}$ with $\sum _j m_j = M(Z)$ and maximise $\sum _j \log m_j$. The
objective is strictly concave and the constraint set is compact and convex, so the maximiser is
unique. The Lagrangian $L(m,\mu ) = \sum _j \log m_j - \mu (\sum _j m_j - M(Z))$ is stationary when $1/m_j = \mu$
for every j, so $m_j = 1/\mu$ for all j, and the constraint forces $m_j = M(Z)/k$. Substituting
gives (ceilbasic).

Equivalently and without calculus, AM–GM gives $\big(\prod_j m_j\big)^{1/k} \le \frac{1}{k}\sum_j m_j = M(Z)/k$ with
equality iff all $m_j$ are equal; take logarithms and multiply by k. Since every partition's mass
vector is feasible for the relaxation, the bound applies to it, and the equality case identifies
exactly the equal partitions. ∎

So the Nash objective **is** the balance objective on a common measure. It is not an
approximation of it, and it is not a proxy: the argmax is the same. That is the whole
justification for treating \$1B as an emergent target rather than a hard band — set
`k = ⌈total opportunity / $1B⌉ = 18` and balance falls out of the criterion the project already
uses for fairness.

Two refinements make the statement useful when perfect equality is unattainable, which on a real
instance it always is.

**Corollary 3 (strict Schur-concavity: the objective always prefers the flatter vector).**
$\Phi (m) = \sum _j \log m_j$ is strictly Schur-concave on $\mathbb{R}^k_{>0}$. Hence if the mass vector $m$ of one
partition *majorises* the mass vector `m′` of another — $m$ is the less even of the two, in the
standard partial order — then $\Phi (m) \le \Phi (m')$, strictly unless $m$ is a permutation of `m′`.

*Proof.* $\Phi$ is symmetric and strictly concave, being a sum of a strictly concave function
applied coordinatewise. A symmetric concave function is Schur-concave: for $i \ne j$ the
Schur–Ostrowski condition

```math
(m_i - m_j)(\partial_i\Phi - \partial_j\Phi) = (m_i - m_j)(1/m_i - 1/m_j) = -\,(m_i-m_j)^2/(m_i m_j) \le 0
```

holds, with equality only at $m_i = m_j$; strictness of the inequality off the diagonal gives
strict Schur-concavity. ∎

Corollary 3 is what makes (mnw) a usable objective on a constrained feasible set: among
admissible partitions the criterion orders any two comparable mass vectors by evenness, so the
solver's search is a search for balance even when the perfectly balanced vector is not
attainable.

**Observation (verified by enumeration).** `test_channel.py`'s
`test_nash_welfare_is_equal_size_districting` brute-forces every way of cutting a 12-vertex path
with uniform opportunity per zip into three *contiguous* blocks and checks that the argmax of
$\sum _j \log M_j$ is the balanced cut `(4,8)`, with reported relative spread exactly zero. It is a
small check, but it is the one that would fail first if the identity were ever broken by a change
to the objective.

### Why not just minimise a spread?

Because minimising a dispersion measure is not an efficiency criterion and can leave *everybody*
worse off — the project's trap 2. Re-verified at `d = 0` on the paper's 50-zip toy instance (not
the channel instance): an unconstrained equalising MILP over all subsets reaches a
Kalai–Smorodinsky gap of 5.2×10⁻⁸ at 98.1% of attainable welfare with gains (7.3226, 7.0699), and
is **Pareto-dominated** by Nash's (7.3715, 7.2318) — both parties strictly prefer the Nash
allocation to the "perfectly fair" one. Proposition 2 gives the balance without the pathology,
because a strictly concave increasing objective stays on the Pareto frontier by construction. A
hard band of \$1B $\pm\,\varepsilon$ would import the pathology back as an infeasibility risk.

---

## 4. The welfare decomposition

*(`channel_note.tex` §5, `sec:decomp`)*

Proposition 2 concerns a common measure. Real utilities (util) are not common — they differ
across representatives through the book terms. The following decomposition says exactly how much
that matters.

**Proposition 4 (welfare decomposition).** For any allocation `own` of all of `Z`,

```math
\sum_i g_i = \underbrace{\sum_{z \in Z}\bigl[\lambda M_z + c_2 T_z + c_{\mathrm{free}} S_{\mathrm{free}}(z)\bigr]}_{W_0,\ \text{partition-invariant}} \;+\; \underbrace{(c_1 - c_2)\sum_{z \in Z} S_{\mathrm{own}(z)}(z)}_{\text{incumbency premium}} \tag{decomp}
```

The first term does not depend on `own` at all. The second, since
$c_1 - c_2 = (1 - \theta )(1 - \lambda ) \ge 0$, is maximised by giving every zip to the candidate holding the
most book there.

*Proof.* By (gain), $\sum _i g_i = \sum _i \sum _{z: \mathrm{own}(z)=i} u_i(z) = \sum _{z \in Z} u_{own(z)}(z)$, since each
$z$ contributes to exactly one representative. Expanding (util) at `i = own(z)` and regrouping,

```math
u_{\mathrm{own}(z)}(z) = c_2 T_z + c_{\mathrm{free}} S_{\mathrm{free}}(z) + \lambda M_z + (c_1 - c_2) S_{\mathrm{own}(z)}(z),
```

in which only the last term mentions `own`. Summing over $z$ gives (decomp). For the
maximisation, $c_1 - c_2 = (1 - \lambda ) - \theta (1 - \lambda ) = (1 - \theta )(1 - \lambda ) \ge 0$, so the sum is maximised
termwise by $\mathrm{own}(z) \in \mathrm{argmax}_i S_i(z)$ over the candidates. ∎

Read plainly: **the objective is "balance the territories", plus "where there is slack, leave
business with the representative who already has it".** That is a reassuringly operational
reading of a Nash bargaining criterion, and it is exact.

The partition-invariant term is measured: $W_0 = B_{\mathrm{tot}} = 3268.4069219934404$
(`premium.py::measure()`).

### 4.1 Sizing the two terms

The relative weight of the two halves of (decomp) decides how much the legacy books can move the
map at all, and it is set by **saturation** $t_z = T_z / M_z$. At the reference parameters
$\theta = 0.40$, $\lambda = 0.30$ — so $c_1 = 0.70$, $c_2 = 0.28$, $c_1 - c_2 = 0.42$ — and the measured
aggregate saturation of 29.588%, a zip whose whole book sits with one incumbent is worth

```math
u_{\text{incumbent}} = 0.507\,M_z, \qquad u_{\text{other candidate}} = 0.383\,M_z.
```

Of the incumbent's utility, 59.1% is the pure opportunity term $\lambda M_z$ and only 24.5% is the
incumbency premium $(c_1 - c_2)S_i(z)$; the utility swing between holding the book and not holding
it is 32.5%.

> `chOppShare` prints 59.1 or 59.2 depending on whether `ceiling.py:75` stores `SATURATION` at
> three significant figures — a rounding-order artefact, not a wrong measurement.

The consequence for the algorithm is decisive. Combining Propositions 2 and 4 through the AM–GM
inequality of (ceilbasic),

```math
\sum_i \log g_i = n\log\!\Bigl(\frac{W_0 + (c_1-c_2)\sum_z S_{\mathrm{own}(z)}(z)}{n}\Bigr) - \underbrace{\Bigl[n\log \bar g - \sum_i \log g_i\Bigr]}_{D(g)\ \ge\ 0} \tag{split}
```

where `ḡ` is the arithmetic mean of the gains and $D(g) \ge 0$, the log of the
arithmetic-to-geometric mean ratio, vanishes exactly at perfect balance.

The first term is bounded within a 24.5%-scale window by the incumbency premium, and **on the
delivered k = 18 draw that window is not small**: to first order the premium ladder's map gap
(this staff's shortfall from its best achievable map) costs 0.663 nats and its roster gap (this
staff's further shortfall from the best-staff ceiling) another 0.249 nats, and evaluating the
first term of (split) exactly at the two ends of that ladder puts the combined window at **0.890
nats exact**. The 0.912 first-order sum differs from it by 0.022, which is 4.5× the tier-2 floor,
so the two must not be quoted interchangeably. On the same draw `D(g) = 0.148` nats.

The 10⁻⁴–10⁻² range one might expect belongs to the *mass* imbalance `D(M)`, which is 1.5×10⁻⁴
nats at a mass spread of 1.37%; (split) is written on $g$, not on `M`, and the realised *gain*
spread on this draw is 60.17%. On the region the programme actually operates in the ordering
therefore **inverts** — by a factor of 6.0, not by orders of magnitude: incumbency, not balance,
is the larger term.

The two-stage scheme survives as a business constraint — *territories shall be
opportunity-balanced* — and **not**, as this section previously claimed, as a consequence derived
from (split).

*This ratio must be checked against real saturation.* The live instance measures 29.588%, which
sits just *below* the 30% threshold the source note set for a "modest continuity tilt":
saturation alone does not settle the question either way. What settles it is the directly measured
premium window above — 0.890 nats against `D(g) = 0.148` — which says incumbency book carries real
weight in the objective whatever side of the 30% line the instance happens to fall on. The
incumbency premium itself measures **0.72–0.78 nats and is not soft**: on the D1′ screen it sits
at 146–155× the 5×10⁻³ tier-2 floor, with no $\delta *$ at which it vanishes.

---

## 5. The two-stage scheme

*(`channel_note.tex` §6, `sec:stages`)*

| stage | problem | status |
|---|---|---|
| 1 — draw | k balanced compact districts on opportunity alone | heuristic, certified |
| 2 — match | assign representatives to districts | exact |

### 5.1 Stage 2 is a linear assignment problem on logs

Given a drawn map $A_1,\dots,A_k$, let

```math
g_{ij} = \sum_{z \in A_j} u_i(z) \tag{gij}
```

be what district $j$ is worth to representative $i$ — evaluated for *every* representative on
*every* district, unrestricted by legacy candidacy, which is the entire point of drawing the map
before staffing it.

**Proposition 5 (Nash-optimal staffing is a linear assignment problem).** Suppose $g_{ij} > 0$ for
all `i,j`. Maximising $\sum _i \log g_{i \sigma (i)}$ over injections $\sigma$ from representatives to districts
is a maximum-weight bipartite matching with weights $w_{ij} = \log g_{ij}$, and is therefore solved
exactly in $O(\max(m,k)^3)$ by the Hungarian algorithm, where $m$ is the number of representatives.
When $m > k$ the matching is rectangular, and the unmatched representatives are exactly those not
staffing the channel.

*Proof.* The objective is additively separable over the pairs $(i, \sigma (i))$ that $\sigma$ selects, the
coefficient of `(i,j)` being $\log g_{ij}$, independent of the rest of $\sigma$. The injections $\sigma$ are
exactly the matchings of the complete bipartite graph $K_{m,k}$ saturating its smaller side.
Hence this is the linear assignment problem with weight matrix $(\log g_{ij})$, which the Hungarian
algorithm solves to optimality in cubic time; the rectangular case is the standard padding
reduction. Positivity of $g_{ij}$ is needed for $\log g_{ij}$ to be finite, and is checked rather than
assumed. ∎

On the live instance the rectangular case is the operative one: 114 representatives against 18
districts, so 96 representatives go unmatched and the matching *is* the retention decision. The
delivered draw's **match gap is 0** — this staff, on this map, is staffed optimally — while its
**map gap is 0.663 nats**, which is where the shortfall actually sits.

This is genuinely a different objective from utilitarian matching, and the difference is the
reason to insist on it.

**Example (Nash and utilitarian matching disagree).** Two representatives, two districts,
`g = [[100, 10], [90, 1]]`. The identity matching has utilitarian value 101 and Nash value 4.605;
the swap has utilitarian value 100 and Nash value 6.802. The utilitarian rule picks the identity,
handing representative 2 a district worth 1 to them because the *total* looks marginally better.
The Nash rule picks the swap. A staffing that hands a senior wholesaler a territory containing
almost none of their book is exactly the failure mode the channel cannot afford.

### 5.2 The cost of splitting, and the portfolio mitigation

Stage 1 cannot see relationships, so a good staffing may simply not be available on the map it
draws. This is the same objection the programme raises to "decouple fairness from compactness": a
two-stage scheme *relocates* the difficulty rather than removing it, and the joint optimum over
(map, staffing) is in general strictly better than the sequential one — it is attained by
first-stage maps that a balance-only stage 1 has no reason to prefer among its own optima.

The mitigation is cheap precisely because stage 2 is milliseconds: generate a **portfolio** of
stage-1 draws — one per random seed, or the incumbent sequence of a branch-and-cut solver, or a
recombination-style sampler (DeFord et al. 2021) — score each by its best staffing value with
`channel.score_draws`, and keep the best pair. This is not the joint optimum and should not be
reported as one; it is a cheap lower bound on it, and the spread between the best and worst draw
in the portfolio diagnoses how much the split is costing.

> **Not measured on v2.** The source note reported a k = 13 run in which the portfolio changed
> the answer — the draw that staffed best was not the stage-1-best draw. No equivalent portfolio
> comparison has been run on v2, and the delivered draw (k = 18, seed 2) is not on record as
> having been selected by stage 2. Relatedly, the state-atom draw has never been through
> `channel.score_draws` at all, so its stage-2 cost is unknown and could exceed its 0.094-nat
> stage-1 gap: pinning CALIFORNIA alone costs 2.04 nats at stage 2, and the atom cut plan forces
> California into five pieces.

A pleasant side effect: stage 1 needs almost none of the confidential data — only $(z, M_z)$ and
public coordinates, with opportunity plausibly third-party market sizing — while stage 2 needs
the books but not the geometry, and can therefore run entirely on the work machine given only the
returned district map.

---

## 6. Stage 1 as center-based balanced assignment

*(`channel_note.tex` §7, `sec:centers`)*

Contiguity is unavailable on this footprint (§1), and it was never the requirement — it was a
proxy for one. What a sales territory actually needs is that a representative can cover it: a
tight cluster of zips around a place, not a connected subgraph of a lattice. So stage 1 optimises
**compactness** directly, in the centre-based formulation Hess et al. (1971) introduced for
exactly this problem and the districting literature has used since (Zoltners & Sinha 2005;
Ríos-Mercado & Fernández 2009; Duque et al. 2011).

### 6.1 The programme

Let $x_z \in \mathbb{R}^2$ be zip $z$'s internal point in an equal-area planar projection, so that squared
Euclidean distance is a real area-weighted moment and not a lat/lon approximation. With k centers
$c_1,\dots,c_k \in \mathbb{R}^2$ and binaries $y_{zj} = 1$ iff zip $z$ joins district $j$:

```math
\begin{aligned}
\min_{y}\;\; & \sum_{z \in Z}\sum_{j=1}^{k} M_z \lVert x_z - c_j \rVert^2 y_{zj}\\
\text{s.t.}\;\; & \sum_{j=1}^{k} y_{zj} = 1 && \forall z \in Z,\\
& \sum_{z \in Z} M_z y_{zj} = \frac{M(Z)}{k} && \forall j \in \{1,\dots,k\},\\
& y_{zj} \in \{0,1\}.
\end{aligned}
\tag{centers}
```

The mass equalities are **hard**, so any feasible point is exactly balanced and the objective only
chooses among balanced maps; in the band form used in practice they are relaxed to
$|\sum _z M_z y_{zj} - M(Z)/k| \le \delta$. By Proposition 2 this is the right division of labour: balance
*is* the Nash objective on a common measure, and compactness is the tie-break among its optima —
exactly the ordering (split) derives. Centers are then updated Lloyd-style, each to the
`M`-weighted centroid of its district, and (centers) re-solved; the loop stops when the labels
repeat.

Two things are bought by the reformulation. The $k!$ label symmetry that would cripple
branch-and-bound on an anonymous-district model is gone — district $j$ is the one at $c_j$, so
the labels are pinned by geography, which is why Hess's formulation is the standard remedy for
it. And the constraint matrix of the relaxation is a network matrix, which is the content of the
next lemma.

### 6.2 The transportation-relaxation lemma

**Lemma 6 (fixed centers: the relaxation is a transportation problem).** Fix the centers and
relax $y_{zj} \in \{0,1\}$ to $y_{zj} \ge 0$ in (centers). Then:

1. the substitution $\eta _{zj} = M_z y_{zj}$ turns the constraints into a Hitchcock transportation
   problem with supplies $M_z$, demands `M(Z)/k` and no upper bounds — the bounds $y_{zj} \le 1$ are
   implied;
2. the relaxation is feasible, and every basic solution has acyclic support, hence at most
   `n + k − 1` positive entries, where $n = |Z|$;
3. consequently at most $k - 1$ zips are **split**, i.e. have $y_{zj} > 0$ for two or more $j$.
   Every other zip is assigned integrally by the relaxation itself.

*Proof.* (1) Substituting $\eta _{zj} = M_z y_{zj}$ ($M_z > 0$) sends $\sum _j y_{zj} = 1$ to
$\sum _j \eta _{zj} = M_z$ and $\sum _z M_z y_{zj} = M(Z)/k$ to $\sum _z \eta _{zj} = M(Z)/k$; supplies and demands both
total `M(Z)`, so the problem is a balanced transportation problem, and $\eta _{zj} \ge 0$ with
$\sum _j \eta _{zj} = M_z$ forces $\eta _{zj} \le M_z$, i.e. $y_{zj} \le 1$.

(2) $\eta _{zj} = M_z/k$ is feasible, so the feasible set is nonempty; it is bounded, so a basic optimal
solution exists. The constraint matrix is the node–arc incidence matrix of the complete bipartite
network on the $n$ supply nodes and $k$ demand nodes, and a set of its columns is linearly
independent iff the corresponding edge set contains no cycle; hence the support of a basic
solution is a forest on $n + k$ nodes and has at most $n + k - 1$ edges.

(3) Let `F` be the number of split zips. Every zip node has degree at least one in the support,
since $M_z > 0$ must be shipped somewhere, and a split zip has degree at least two. Counting
edges, $n + F \le \#\text{edges} \le n + k - 1$, so $F \le k - 1$. ∎

**Corollary 7 (rounding damage is confined to $k - 1$ zips).** Rounding a basic optimum by giving
each split zip to the district holding its largest share changes at most $k - 1$ of the $n$
assignments; every other zip keeps the district the exactly balanced relaxation gave it, and no
district's mass moves by more than the total mass of the split zips, at most $(k-1) \max_z M_z$.

*Proof.* Immediate from Lemma 6(3): the rounded solution differs from the basic optimum only on
split zips, and the basic optimum's masses are exactly `M(Z)/k`, so each district's mass changes
by at most the mass it gains or loses from those $F \le k - 1$ zips. ∎

The crude bound $(k-1) \max_z M_z$ is not the operative fact. What matters is the **count**, and
the live run hits the bound exactly: at k = 18 over the 3,704 plotted zips, **17 = k − 1 zips
split**, at both target choices. Those 17 carry 17.03% of one mean district at equal-split
targets (largest, `20814`, 3.699% of a mean district) and 22.08% at own-masses targets. A greedy
repair pass then recovers what the rounding cost. That is why a heuristic can land 0.000082 nats
below a bound that holds for every partition (§7.4): the only unbalanced part of the answer is
$k - 1$ zips wide.

### 6.3 The rest of the pipeline

Three components surround (centers), and each is a heuristic that §7 then measures rather than
trusts.

**Seeding.** `M`-weighted k-means++: the first center is a zip drawn with probability
proportional to $M_z$, each further center with probability proportional to
$M_z d^2(z, nearest chosen center)$. Weighting by `M` rather than by zip count is the right prior
when districts are equal in *mass*: a dense but light region should not attract centers the way
its zip count would suggest.

**The Lloyd loop.** Assign by (centers), move each center to its district's `M`-weighted
centroid, repeat. Unlike plain k-means there is no drift to a lopsided fixed point, because every
round's assignment is exactly balanced before rounding; the rounds buy compactness only.

**The polish.** A greedy pass over single-zip moves that strictly increase $\sum _j \log M_j$,
restricted to destinations among the 3 nearest centers — the compactness guard, without which a
Nash-greedy move would send a California zip to a Florida district for an epsilon of balance.
Ties in the objective are broken by the more compact destination, and a district is never emptied
(that would send the objective to $-\infty$).

**Zips with no coordinates.** 44 of the 3,748 zips are absent from the geometry: 41 carry no
gazetteer internal point (retired or non-ZCTA codes) and 3 sit outside the lower 48. They are
placed afterwards by a state-plurality rule: each goes to the district holding the plurality of
already-placed zips from its own state, with ties and unknown states broken toward the district of
smallest total mass, one zip at a time with counts and masses updated after each placement.

---

## 7. Certifying a draw

*(`channel_note.tex` §8, `sec:certs`)*

Nothing in §6 proves anything: the seeding is random, the rounding of the $k - 1$ split zips is
arbitrary, and the polish is a local search. Three post-hoc certificates say how far from optimal
a drawn map actually is — and, as importantly, which questions they leave open. They are
implemented in `td/solvers/cert_draw.py` and exercised against brute force at small k in
`tests/test_cert_draw.py`.

> A fourth certificate, `cert_power_diagram`, was added after the source note was written. It
> asks the geometric question of certificate (iii) using the transportation LP's **duals**
> instead of a MILP: dual feasibility reads $\alpha _z + M_z \beta _j \le M_z d^2(z,c_j)$, so an optimal
> assignment puts each zip in the district minimising $d^2(z,c_j) - \beta _j$ — the **power (Laguerre)
> diagram** of the centers with weights $\beta$. That yields a lower bound whose verification is
> `O(nk)` arithmetic with no solver in the trusted path, and the territory map exactly, as k
> convex cells. `power_weights` also returns the split zips' row indices, surfaced as
> `power_diagram_of_draw`'s `split_zips`. See `docs/OPTIONS_power-cell-contiguity.md`.

### 7.1 (i) The balance ceiling: analytic, and valid for every partition

**Proposition 8 (balance ceiling at fixed k).** Let `Z` be any finite set with $M_z > 0$ and let
$A_1,\dots,A_k$ be any partition of it into k parts of positive mass. Then

```math
\sum_{j=1}^k \log M_j \le k\log\frac{M(Z)}{k},
```

with equality iff every $M_j = M(Z)/k$. The gap $\Delta = k \log(M(Z)/k) - \sum _j \log M_j \ge 0$ is
invariant under a global rescaling $M \mapsto \kappa M$, and $1 - e^{-\Delta }$ is the equivalent proportional
shortfall in the Nash *product*.

*Proof.* The inequality is Proposition 2 with no structural constraint imposed, i.e. the case
`C = 1` of the component bound of the source note's §9: the total `M(Z)` is partition-invariant,
and $\sum _j \log m_j$ is maximised over $\{m > 0 : \sum _j m_j = M(Z)\}$ uniquely at $m_j = M(Z)/k$. For
invariance, rescaling sends $\sum _j \log M_j$ to $\sum _j \log M_j + k \log \kappa$ and `k log(M(Z)/k)` to
$k \log(M(Z)/k) + k \log \kappa$, so $\Delta$ is unchanged; the last claim is the definition of $\Delta$ as a
log-ratio of products. ∎

This is a free dual bound: it needs `M(Z)` and $k$ and nothing else — no geometry, no contiguity,
no solver — and it holds for *every* partition of these zips into k districts, so a draw's gap to
it is an unconditional statement about how much balance was left on the table. What it does not
say is whether the ceiling is reachable. Zips are indivisible, so in general it is not, which is
the next certificate's subject.

**Two ceilings are in circulation, on different bases.** The power-cell route's ceiling is
$k\cdot \log(M/k) = 110.766768$ over the 3,704 plotted zips; the state-atom route's is
`cert_draw.cert_balance_ceiling = 110.883247` over the whole instance. They are two orders of
magnitude apart in the gaps they induce, so the route ranking is unlikely to turn on the
difference, but it is **not certified** — recompute on one base before any comparison leaves the
project.

**And one reference is not a ceiling at all.** The contiguity-dropped local search returns a
feasible *relaxed* value below the relaxed optimum, which orders it against the contiguous
optimum not at all. It is named `free_search`, reports **110.812355** (+0.022823 over the draw),
and must never be quoted as a bound. An earlier prototype did quote it as "the margin above the
draw", understating the true 0.0937 gap by about fourfold.

### 7.2 (ii) The integer balance floor: an honest bound pair

Write $\tau = M(Z)/k$ for the target. The best balance indivisible zips permit, with geometry
ignored entirely, is the optimum `t*` of

```math
\begin{aligned}
\min_{x,t}\;\; & t\\
\text{s.t.}\;\; & \sum_j x_{zj} = 1 && \forall z \in Z,\\
& \Bigl\lvert \sum_z M_z x_{zj} - \tau \Bigr\rvert \le t && \forall j,\\
& x_{zj} \in \{0,1\},\quad t \ge 0.
\end{aligned}
\tag{floor}
```

Every real draw's max-deviation is at least `t*`, so `t*` separates the heuristic's loss from the
arithmetic's: it says how much of the gap to Proposition 8's ceiling was ever available. The
trouble is that (floor) is a multiway-number-partitioning problem, and its relaxation is
worthless.

**Proposition 9 (the relaxation of (floor) is vacuous).** The linear relaxation of (floor),
replacing $x_{zj} \in \{0,1\}$ by $x_{zj} \ge 0$, has optimal value 0 for every instance and every $k \ge 1$.

*Proof.* Take $x_{zj} = 1/k$ for all `z,j`. The placement rows hold, and
$\sum _z M_z x_{zj} = M(Z)/k = \tau$ for every $j$, so `t = 0` is feasible; $t \ge 0$ is imposed, so 0 is
optimal. ∎

The root bound therefore carries no information, and every nat of the dual side must be earned in
the tree — against the full $k!$ label symmetry, which is what branch-and-bound cannot prune. Two
valid symmetry breaks help and do not fix it: fix the heaviest zip into district 0 (a
relabelling, so it costs nothing), and force districts `1,…,k−1` to non-increasing mass (valid
because after fixing that one zip those labels remain freely permutable).

So the certificate is a **pair**, and it is reported as one. The lower bound is 0 from
Proposition 9 — or whatever the solver has earned above it within its time limit. The upper bound
is *constructive*: any partition anyone exhibits is an upper bound on `t*`, needing no proof
beyond arithmetic, so one is built directly by longest-processing-time greedy (heaviest zip
first, into the lightest district) followed by a steepest single-move/single-swap descent on the
max-deviation. Both take a fraction of a second, the partition is returned with the certificate,
and its masses are recomputed from it. The primal half is the operative one for judging a draw:
it is what says whether the draw's imbalance is arithmetic or geometry.

> **Not run on v2.** This certificate has not been executed on the live instance. The conclusion
> the source note drew from it — that the draw's residual imbalance is the price of geometry
> rather than of indivisibility — is therefore **not currently established** at k = 18. Nothing
> below rests on it.

### 7.3 (iii) The pinned-centers assignment MILP

The third certificate asks the geometric question with the draw's own centers held fixed:
minimise $\sum _{z,j} M_z \lVert x_z - c_j \rVert ^2 y_{zj}$ subject to $\sum _j y_{zj} = 1$,
$|\sum _z M_z y_{zj} - \tau | \le \delta$ and $y$ binary, with $\delta$ defaulting to the draw's own max-deviation so
that the draw is feasible for its own test. Pinning the centers removes the label symmetry
entirely, and what remains is the transportation problem of Lemma 6 with two side rows per
district — so the relaxation is nearly integral, the root bound is tight, and a real certificate
(`mip_rel_gap = 0`, trap 12) closes in minutes at production size.

**Remark (what (iii) does not certify).** The centers are the heuristic's. Certificate (iii)
proves the *assignment* is optimal *given* them, in exactly the sense a k-means assignment step is
optimal given its centroids; it says nothing about whether those k points are the right ones, and
the joint problem over centers *and* assignment is untouched by anything here. Nor does it certify
the stage-1 objective: the constraint is a max-deviation band, not $\sum _j \log M_j$, so a strictly
more compact assignment inside the band may have slightly *lower* Nash value. Both values are
returned so the trade is visible rather than implied.

> **Not run on v2.** Like (ii), this certificate has no k = 18 run on record.

### 7.4 The live run

Numbers below are the power-cell draw `battery/results/draw_k18_v2_20260904/k18`, k = 18, seed 2,
over the 3,704 plotted zips carrying total mass 8,468.3 in descaled units. Every quoted spread,
ratio and nat is scale-free by the scale-invariance proposition of the source note's §3.

**The ceiling certificate.** Against $k\cdot \log(M/k) = 110.766768$, the committed draw scores
$\sum \log M = 110.766686$ — a gap of **0.000082 nats** at a mass spread of 1.2902%. *Proved:* no
partition of these zips into 18 districts scores above the ceiling, whatever its geometry. *Not
proved:* that the ceiling is reachable.

**The split-zip bound binds exactly.** The final transportation LP splits 17 = k − 1 zips, the
bound of Lemma 6(3), at both target choices.

**Snapping to the power cells is a real trade.** Relabelling every zip to its own power cell
gives 0 mismatches by construction but costs balance: spread rises to 4.0041% and the gap to
0.000724. Iterating snap-then-recentroid 20 times, the best iterate (number 15) reaches spread
**2.1051%** at gap 0.000283. **There is no fixed point** — 20 iterations, no exact repeat,
non-monotone, band spread 2.1–5.6% and gap 0.00028–0.00128.

**How far the labelling sits from the diagram.** On the committed draw, **258 zips (7.0% of
count, 1.66% of mass) fall outside their own power cell** at own-masses targets, and 266 (7.2%)
at exactly-equal-split targets. These are two measurements and were quoted as one number until
2026-09-06.

**The zero is showable, on one held diagram.** `us_maps.py --regions-fixed` builds a single power
diagram from the committed draw's M-weighted centroids and draws both labellings on it: the
committed labelling at **266 of 3,704 outside**, the snapped labelling at **0 of 3,704**, with
max dual violation 1.8×10⁻¹⁸. The zero is relative to that one diagram — rebuild the diagram from
the snapped labels and 15 to 16 of 3,704 fall outside again, with the split count dropping from
17 to 10.

**The state-atom route, for comparison.** 56 atoms, 126 edges, one component under the cut plan
CA 5 / TX 2 / NY+NJ 3 / FL 2; $\sum \log M = 110.789532$ against the whole-instance ceiling
110.883247, a gap of **0.093715 nats** at a spread of **30.484%**. Quote that spread beside the
gap: `log` is flat near the optimum, so a small Nash gap can sit alongside a large operational
spread, and the power-cell route's spread is 1.37%. Quoting the gap alone reads as "contiguity is
nearly free". The two gaps are also on different bases (§7.1).

**Map contiguity is measured and is not uniform.** Dissolving each zip's Voronoi catchment by
district on the atom draw, the largest contiguous piece is 48% of territory for D02, 53% for D11,
55% for D17 and 73% for D06; fourteen other districts run 98–100%. The atom graph's single
component certifies `BORDER_TOL`-proximity reachability, not that every district is one polygon.

**Beware the denominator.** Largest-piece-by-**area** makes D01 read 55% on the snapped power-cell
draw, but D01 is not fragmented: 148 of its 149 zips and 99.86% of its mass are one piece, and the
second "part" is the single rural ZIP `18337`, whose empty catchment is 44.56% of D01's area and
0.14% of its opportunity. By **mass** the snapped worst district is D17 at 92.72% and the committed
worst is D09 at 90.03%. The two denominators disagree about which districts are the problem, on
both labellings, and area is not what stage 1 balances.

---

## 8. The VBL setup, how ours differs, and options for merging them

*New section, written 2026-09-06. Not present in `channel_note.tex`.*

### 8.1 What VBL solve, and the correction to §1's frontier claim

The reference line is Validi, Buchanan & Lykhovyd, *Imposing contiguity constraints in political
districting models* (Operations Research, 2021, DOI 10.1287/opre.2021.2141), and Validi &
Buchanan, *Political districting to minimize cut edges* (Mathematical Programming Computation,
2022, DOI 10.1007/s12532-022-00221-5). Their setup:

- **Decision variables.** The Hess (1965) centre-based assignment model: $x_{ij} = 1$ iff unit $i$
  is assigned to the district *centred at* unit $j$, with $x_{jj} = 1$ marking $j$ as a centre. The
  centres are chosen **by the solver**, from among the units.
- **Objective.** Linear, and a compactness surrogate: minimise cut edges, or a moment-of-inertia
  sum $\sum _{ij} w_i d^2_{ij} x_{ij}$. Belotti, Buchanan & Ezazipour (2025) extend the line to a
  Polsby-Popper perimeter-ratio objective, which makes it an MISOCP.
- **Balance.** A **hard constraint**, not the objective: population within $\pm \varepsilon$ of the ideal
  district size, $\varepsilon$ typically 1% for congressional plans.
- **Contiguity.** Lazily separated cuts. Their comparison of the families (`lcut` / `scf` /
  `mcf` / Shirabe flow) is the paper's main contribution, and the a–b separator cut with its two
  branches is the same object the programme's own `scip_tree` separates.
- **Symmetry.** Broken by construction: districts are named by their centre unit, so there is no
  $k!$ permutation group left to prune against.
- **Their headline.** *Districting does not get harder when contiguity is imposed.* On their
  instances the contiguity constraints often help, by cutting off fractional solutions the
  balance rows alone admit.

**The source note's frontier claim is stale by roughly two orders of magnitude.**
`docs/RESEARCH_FINDINGS.md` §5 records the correction: the group now reports provably optimal
plans for *all* US congressional and legislative instances (whole-counties objective,
combinatorial Benders; Shahmizad & Buchanan, MPC in revision), and experiments at **175,000
vertices** with inexact contiguity (Jolly & Buchanan 2026). Our 3,748 zips is not near any
frontier. The binding difficulty here is the log objective and the shattered graph, not the unit
count — so §1's scale reading is a statement about *our* solver's certified size, not about the
field's.

### 8.2 The five differences

**1. Objective: linear versus log.** VBL minimise a linear (or SOC) compactness functional with
balance as a constraint. We maximise $\sum _j \log M_j$, and Proposition 2 says that objective *is*
balance. So the two setups swap which of balance and compactness is the objective and which is
the tie-break. The consequence is computational: their formulation stays a MILP with a strong LP
relaxation; ours is a convex MINLP needing outer-approximation tangents or a solver with native
`log` recognition (`scip_tree` uses SCIP's).

**2. Centres: chosen versus fixed.** VBL's Hess model chooses the centres inside the same
program. Ours fixes them by Lloyd iteration and then solves only the assignment. That single
difference is the entire certified/uncertified boundary in this project: §7.3's remark states it
plainly, and the joint problem over centres and assignment is untouched by anything in §7.

**3. Contiguity: cuts versus convex cells.** VBL pay for contiguity with lazily separated
separator cuts on a connected unit graph. We cannot: the sold-zip graph has 862 components, so
the constraint is infeasible rather than hard (§1). Instead we take the geometric property the
LP's dual hands us for free — the power diagram's cells are **convex**, hence connected in the
plane. That is a contiguity surrogate bought with no cuts and no tree. Its three leaks are
measured in §7.4: the labelling is not the diagram (266 of 3,704 outside), the diagram moves when
you recentroid (no fixed point in 20 iterations), and a convex cell of scattered points is not a
single served blob (D02 at 48% of its territory).

**4. Balance: hard band versus objective.** Their `± 1%` is a feasibility question; a plan either
satisfies it or does not exist. Our balance is graded, and §3's closing paragraph explains why we
refuse the band: a hard band re-imports the equalisation pathology as an infeasibility risk, and
trap 2 says equalisation can destroy value.

**5. The instance graph.** Theirs are county and tract graphs: connected, planar, ~100 to ~10,000
units. Ours is the sold-zip graph: 862 components, 516 singletons, 47.6% of mass in components
under 1% each. Contracted to states our instance graph gives only 10 edges over 42 components,
which is why a state model must import the TIGER state rook graph (49 nodes, 107 edges).

There is also a difference in the other direction, worth stating because it is the project's
claim to novelty: `docs/RESEARCH_FINDINGS.md` §8 records two verified absences — no districting
paper formulates districting as Nash-welfare maximisation, and no price-of-connectivity bound for
Nash welfare exists. The power-diagram dual certificate, the analytic Jensen ceiling and the exact
stage-2 Nash matching are ours; none has a counterpart in the VBL line.

### 8.3 Where our LP already is their relaxation

The two setups are closer than the differences suggest. Programme (centers) in §6.1 is **the Hess
model with integrality dropped and the centres fixed**. Both removals are what turn a MILP into
an LP, and Lemma 6 says the first removal is nearly free: at most $k - 1$ zips split, measured as
exactly 17 on the live draw. The second removal is not free, and it is the one §7.3's remark
refuses to certify.

So a merge is not a rewrite. It is the restoration of one or both of the things we removed, on a
graph where their cut machinery has something to bite on.

### 8.4 Options

**Option A — Hess MILP with the log objective, on a restored graph.** Put the centres back into
the program as $x_{jj}$ binaries, keep $\sum _j \log M_j$ via SCIP's native `log` (the `scip_tree`
machinery already does this for two players), and separate VBL's contiguity cuts on a
**full-ZCTA** graph rather than the sold-zip graph. This is reframing R-C4 in
`docs/RESEARCH_FINDINGS.md`, and it is the only option that closes the joint centres-and-
assignment question.

*Buys:* a genuine dual bound on stage 1, and the $k!$ symmetry break we currently get only by
accident. *Costs:* districting an object the channel does not sell in (§1's objection, which is a
business objection and not a technical one), plus the k-way extension of a solver currently
written for two players. *Risk:* the log objective plus lazy cuts is the trap-14 configuration —
SCIP needs `misc/allow{strong,weak}dualreds` off for any lazily separated model, $ga \le \sum u\cdot x$ not
`==`, and a gain lower bound from the incumbent.

**Option B — cuts on the atom graph only.** The state-atom route already builds a graph where
contiguity is meaningful: 56 atoms, 126 edges, one component. VBL separator cuts apply there
directly and at trivial scale. `td/solvers/atom_draw.py` currently does local search with a
`check_contiguous` post-check; replacing that with an exact model over 56 nodes is small.

*Buys:* a certified contiguous draw on the coarsened instance, closing the "draws are local
search against a relaxation, not certified optimal" caveat. *Costs:* small. *Risk:* the answer is
certified for the atom instance, not for the zip instance, and the two ceilings sit on different
bases (§7.1). Recompute on one base in the same pass.

**Option C — pre-aggregate, then solve exactly.** Swamy, King & Jacobson (2023, DOI
10.1287/opre.2022.2311) give a multilevel matching-based contraction that shrinks the unit count
before any MILP. Coarsen 3,748 zips to a few hundred units, solve the Hess-plus-cuts model
exactly there, then uncoarsen.

*Buys:* exactness at a size the published machinery handles comfortably. *Costs:* a contraction
step we do not have. *Risk:* `docs/OPTIONS_power-cell-contiguity.md` §8 already rejects
METIS-style coarsening for not preserving connectivity on refinement and for smoothing the heavy
tail the map exists to show; Swamy's matching-based version must be checked against that
objection rather than assumed to escape it.

**Option D — import a compactness certificate that survives disconnection.** Zhang, Silveira,
Validi, Smith, Buchanan & Hicks, *Partitioning a graph into low-diameter clusters* (IJOC, DOI
10.1287/ijoc.2025.1448) certify a bounded **metric** diameter rather than adjacency connectivity.
Metric diameter is defined on a disconnected graph, so this is the one piece of their machinery
that applies to our instance unmodified.

*Buys:* a certified compactness constraint to sit beside the power-diagram bound, and a defensible
answer to "how compact is compact enough" that is not a Lloyd artefact. *Costs:* a new constraint
family. *Risk:* it constrains diameter, not the Nash objective, so it can only tighten the
feasible set — the interaction with balance needs measuring, not assuming.

**Option E — leave the two lines apart, and say so.** Keep the power-cell route, cite VBL for the
cut families we already share, and record the divergence as deliberate, resting on the §8.2
absences.

*Buys:* nothing new, costs nothing, and is honest. *Risk:* the joint centres-and-assignment
question stays open indefinitely, and any sponsor claim of the form "this map is optimal" stays
unsupportable.

Two candidates from the same literature are already assessed and rejected
(`docs/OPTIONS_power-cell-contiguity.md` §8): the Zhang–Validi–Buchanan–Hicks linear-size planar
formulation, which is integral for pure connected partitioning but which its own authors report
underperforms Hess once value and balance constraints are added — exactly our coupling; and the
Shirabe one-shot flow formulation, kept only as a small-instance cross-check oracle since it
shares no cut-generation code.

### 8.5 Every setup and option as one program

One notation throughout, so the programs can be read against each other.

| symbol | meaning |
|---|---|
| $Z$, $n = \lvert Z\rvert$ | units (zips, or atoms, or coarsened units) |
| $M_z \ge 0$ | opportunity at unit $z$; $M(Z) = \sum _z M_z$; $\tau = M(Z)/k$ |
| $q_z \in \mathbb{R}^2$ | unit $z$'s internal point, equal-area planar projection |
| $k$ | district count (18 on the live instance) |
| $x_{zj} \in \{0,1\}$ | unit $z$ is assigned to district $j$ |
| $x_{jj} = 1$ | unit $j$ is a **centre** (Hess naming; districts indexed by their centre) |
| $c_j \in \mathbb{R}^2$ | free centre location (used only where centres are continuous) |
| $g_j = \sum _z M_z x_{zj}$ | district $j$'s mass |
| `G = (Z, E)` | adjacency graph; $S \subseteq Z$ is an *(i,j)-separator* if deleting `S` disconnects $i$ from $j$ in `G` |
| `d(u,v)` | metric distance, defined whether or not `G` is connected |

Two modelling conventions recur and are load-bearing. $g_j \le \sum _z M_z x_{zj}$ is written as an
inequality, never an equality: the objective increases in $g_j$, so it is tight at every optimum,
but an equality lets presolve aggregate $g_j$ out and every in-callback `trySol` then dies
(trap 14). And `log` enters through an epigraph variable $w_j \le \log g_j$, which a solver either
recognises as convex (SCIP does) or approximates by the outer-approximation tangent family
$w_j \le \log \hat{g} + (g_j - \hat{g})/\hat{g}$ at incumbents $\hat{g}$, generated lazily.

---

**P0 — the true stage-1 problem.** What everything below is an approximation of.

```math
\begin{array}{llll}
\max_x & \sum_{j=1}^{k} \log\Big(\sum_z M_z x_{zj}\Big) \\
\text{s.t.} & \sum_j x_{zj} = 1 & \forall z \in Z & \text{(every unit placed)}\\
 & \sum_z x_{zj} \ge 1 & \forall j & \text{(no empty district)}\\
 & x_{zj} \in \{0,1\} \\
 & \text{+ a geometric constraint on each district}
\end{array}
```

Unconstrained geometrically, its optimum is the Jensen ceiling $k\cdot \log(M(Z)/k)$
(Proposition 2). The whole design question is which geometric constraint to write on the last
line, and every option below is one answer to it.

---

**P1 — ours as implemented: alternating, not a single program.** This is the honest statement of
the power-cell route. It is a fixed-point scheme whose inner step is an LP, and the outer step is
a centroid update with no optimality claim attached.

```math
\begin{array}{llll}
\textbf{inner,} & \text{centres } c \text{ fixed:} \\
\min_y & \sum_z \sum_j M_z \lVert q_z - c_j \rVert^2 y_{zj} \\
\text{s.t.} & \sum_j y_{zj} = 1 & \forall z & \text{(every unit placed)}\\
 & \sum_z M_z y_{zj} = \tau & \forall j & \textbf{(equal mass, HARD)}\\
 & y_{zj} \ge 0 & & \textbf{(integrality DROPPED)}\\[4pt]
\textbf{outer:} & c_j \leftarrow \dfrac{\sum_z M_z q_z y_{zj}}{\sum_z M_z y_{zj}}
   & & \text{(Lloyd, } M\text{-weighted centroid)}\\[4pt]
\textbf{stop:} & \text{labels repeat}
\end{array}
```

The inner LP is a Hitchcock transportation problem (Lemma 6), so a basic optimum splits at most
$k - 1$ units; its duals $(\alpha , \beta )$ satisfy $\alpha _z + M_z \beta _j \le M_z \lVert q_z - c_j \rVert ^2$, which makes the
optimal cells the power diagram $\mathrm{argmin}_j ( \lVert q_z - c_j \rVert ^2 - \beta _j )$. **There is no fixed point** on
the live instance: 20 iterations, no exact repeat, non-monotone.

Note what the two programs disagree about. The inner LP minimises compactness at exactly equal
mass; P0 maximises $\sum \log g_j$. They coincide only because the mass rows are hard, which is what
makes compactness the tie-break rather than a competing objective.

---

**P2 — stage 2, exact.** $m$ representatives, $k$ districts, $g_{ij} = \sum _{z \in A_j} u_i(z)$.

```math
\begin{array}{llll}
\max_\sigma & \sum_i \sum_j \big(\log g_{ij}\big)\, \sigma_{ij} \\
\text{s.t.} & \sum_j \sigma_{ij} \le 1 & \forall i & \text{(each rep staffs at most one district)}\\
 & \sum_i \sigma_{ij} = 1 & \forall j & \text{(each district staffed)}\\
 & \sigma_{ij} \ge 0
\end{array}
```

The constraint matrix is a bipartite incidence matrix, hence totally unimodular, so the LP
relaxation is integral and the Hungarian algorithm solves it in $O(\max(m,k)^3)$. With $m > k$ the
unmatched representatives are the ones not staffing the channel: at 114 against 18, the matching
*is* the retention decision.

---

**P3 — VBL, `lcut` form.** Hess variables, linear objective, balance as a hard band, contiguity
as lazily separated separator inequalities.

```math
\begin{array}{llll}
\min_x & \sum_{(u,v) \in E} e_{uv} & & \text{(cut edges; or } \sum M_z d^2_{zj} x_{zj}\text{)}\\
\text{s.t.} & \sum_j x_{zj} = 1 & \forall z & \text{(every unit placed)}\\
 & x_{zj} \le x_{jj} & \forall z, j & \text{(assign only to a chosen centre)}\\
 & \sum_j x_{jj} = k & & \text{(exactly } k \text{ centres)}\\
 & (1-\varepsilon)\tau \le \sum_z M_z x_{zj} \le (1+\varepsilon)\tau & \forall j
   & \textbf{(balance, HARD, } \varepsilon \approx 1\%)\\
 & e_{uv} \ge x_{uj} - x_{vj} & \forall (u,v) \in E,\ j & \text{(cut-edge linearisation)}\\
 & x_{zj} \le \sum_{s \in S} x_{sj} & \forall z, j,\ \forall (z,j)\text{-separator } S
   & \textbf{(LAZY)}\\
 & x \in \{0,1\}
\end{array}
```

Read the separator row: if $z$ joins the district centred at $j$, then every $z$–$j$ separator
must contribute at least one unit to that same district — otherwise $z$ is cut off from its own
centre. Symmetry is broken by the $x_{jj}$ naming, so there is no $k!$ group left. Compare against
P1: same centre-based skeleton, but the centres are decided *inside* the program, integrality is
kept, and balance and compactness have swapped roles.

---

**Option A — Hess + log objective + cuts, on a restored graph.** `Ẑ ⊇ Z` is the full ZCTA set,
`Ĝ` its adjacency graph; $M_z = 0$ for unsold units.

```math
\begin{array}{llll}
\max_{x,w,g} & \sum_j w_j \\
\text{s.t.} & w_j \le \log g_j & \forall j & \text{(concave; SCIP-native or OA tangents)}\\
 & g_j \le \sum_{z \in \hat{Z}} M_z x_{zj} & \forall j & \textbf{(} \le \textbf{, never } = \textbf{, trap 14)}\\
 & g_j \ge g_{\min} & \forall j & \text{(from the incumbent, trap 14)}\\
 & \sum_j x_{zj} = 1 & \forall z \in \hat{Z} \\
 & x_{zj} \le x_{jj} & \forall z, j \\
 & \sum_j x_{jj} = k \\
 & x_{zj} \le \sum_{s \in S} x_{sj} & \forall z, j,\ \forall (z,j)\text{-separator } S \text{ in } \hat{G}
   & \textbf{(LAZY, per component)}\\
 & x \in \{0,1\}
\end{array}
```

This is P0 with the geometric constraint instantiated as VBL contiguity, and it is the only
formulation here that decides centres and assignment jointly. Buys a genuine dual bound; costs
districting ~30,000 ZCTAs the channel does not sell in. The $g_{\min}$ row is not cosmetic: without
it the log's gradient at the lower bound is ~1e9 and SCIP's LPs go unstable.

---

**Option B — the same program, on the atom graph.** `A` the 56 state atoms, $G_A$ their rook
graph (126 edges, one component), $M_a$ each atom's mass.

```math
\begin{array}{llll}
\max_{x,w,g} & \sum_j w_j \\
\text{s.t.} & w_j \le \log g_j & \forall j \\
 & g_j \le \sum_{a \in A} M_a x_{aj} & \forall j \\
 & \sum_j x_{aj} = 1 & \forall a \in A \\
 & x_{aj} \le x_{jj} & \forall a, j \\
 & \sum_j x_{jj} = k \\
 & x_{aj} \le \sum_{s \in S} x_{sj} & \forall a, j,\ \forall (a,j)\text{-separator } S \text{ in } G_A
   & \textbf{(LAZY)}\\
 & x \in \{0,1\}
\end{array}
```

Identical to A except for the ground set. At 56 nodes and 126 edges the separation is trivial and
the whole model is small, which is why this is the cheap option — it replaces
`atom_draw.py`'s local search plus `check_contiguous` post-check with a certificate.

---

**Option C — pre-aggregate, then A.** A contraction $\varphi : Z \to U$ (Swamy multilevel matching)
supplies the ground set; $M_u = \sum _{z: \varphi (z)=u} M_z$ and $G_U$ is the contracted graph.

```math
\begin{array}{llll}
\max_{x,w,g} & \sum_j w_j \\
\text{s.t.} & w_j \le \log g_j & \forall j \\
 & g_j \le \sum_{u \in U} M_u x_{uj} & \forall j \\
 & \sum_j x_{uj} = 1 & \forall u \in U \\
 & x_{uj} \le x_{jj}, \quad \sum_j x_{jj} = k \\
 & x_{uj} \le \sum_{s \in S} x_{sj} & \forall u, j,\ \forall (u,j)\text{-separator } S \text{ in } G_U
   & \textbf{(LAZY)}\\
 & x \in \{0,1\} \\[4pt]
\text{then} & \text{uncoarsen: } A_j = \varphi^{-1}\big(\{u : x_{uj} = 1\}\big)
\end{array}
```

The mathematics is A's; the content is entirely in $\varphi$. Note that the uncoarsening line is where
the objection bites — a contraction that does not preserve connectivity on refinement returns a
disconnected district from a certified-contiguous solution.

---

**Option D — low-diameter compactness, no adjacency needed.** The one VBL-line constraint that
is defined on a disconnected graph, since `d(u,v)` is metric rather than path distance.

```math
\begin{array}{llll}
\max_{x,w,g} & \sum_j w_j \\
\text{s.t.} & w_j \le \log g_j & \forall j \\
 & g_j \le \sum_z M_z x_{zj} & \forall j \\
 & \sum_j x_{zj} = 1 & \forall z \in Z \\
 & x_{uj} + x_{vj} \le 1 & \forall j,\ \forall (u,v) \text{ with } d(u,v) > D
   & \textbf{(LAZY)}\\
 & x \in \{0,1\}
\end{array}
```

The conflict row says two units further apart than `D` never share a district, which bounds each
district's diameter at `D` without ever mentioning adjacency. Sparse: only the pairs violating
`D` generate a row, and they separate lazily. `D` is a policy dial, and sweeping it traces a
compactness-versus-balance frontier that P1's Lloyd loop cannot express.

---

**Option E — status quo, stated as programs.** No new model; P1 plus the certificates that
measure it after the fact.

**(i) Ceiling** — closed form, no solver, valid for *every* partition:

```math
\sum_j \log M_j \;\le\; k \cdot \log\!\Big(\frac{M(Z)}{k}\Big)
```

**(ii) Integer balance floor** — geometry ignored:

```math
\begin{array}{llll}
\min_{x,t} & t \\
\text{s.t.} & \sum_j x_{zj} = 1 & \forall z \\
 & \big\lvert \sum_z M_z x_{zj} - \tau \big\rvert \le t & \forall j \\
 & x \in \{0,1\},\ t \ge 0 & & \text{(LP relaxation } \equiv 0 \text{, Proposition 9)}
\end{array}
```

**(iii) Pinned-centres assignment** — centres $c$ taken from the draw:

```math
\begin{array}{llll}
\min_y & \sum_z \sum_j M_z \lVert q_z - c_j \rVert^2 y_{zj} \\
\text{s.t.} & \sum_j y_{zj} = 1 & \forall z \\
 & \big\lvert \sum_z M_z y_{zj} - \tau \big\rvert \le \delta & \forall j \\
 & y \in \{0,1\} & & (\delta = \text{the draw's own max-deviation})
\end{array}
```

**(iv) Power-diagram dual** — no solver in the trusted path:

```math
\text{find } \alpha, \beta \text{ with } \quad
\alpha_z + M_z \beta_j \;\le\; M_z \lVert q_z - c_j \rVert^2 \quad \forall z, j
```

```math
\Longrightarrow \quad \text{the optimal cell of } z \text{ is } \quad
\mathrm{argmin}_j \big( \lVert q_z - c_j \rVert^2 - \beta_j \big)
```

Certificate (iii) is P1's inner program with integrality restored and the equality row widened to
a band. That is the precise sense in which our LP is a relaxation of a model we can already write
down: the gap between (iii) and Option A is exactly the centres.

---

**What the group shows at a glance.** Every option differs from P0 in one line only — the
geometric constraint — and from P1 in two: integrality, and whether $c$ is data or a decision.

| | geometric constraint | centres | integrality | balance |
|---|---|---|---|---|
| P1 (ours) | none; convexity of the power cells is a by-product | fixed by Lloyd | dropped | hard equality |
| P3 (VBL) | separator cuts on `G` | decided in-model | kept | hard band |
| A | separator cuts on `Ĝ` | decided in-model | kept | objective |
| B | separator cuts on $G_A$ | decided in-model | kept | objective |
| C | separator cuts on $G_U$ | decided in-model | kept | objective |
| D | diameter conflicts, no graph | decided in-model | kept | objective |
| E | none | fixed by Lloyd | dropped | hard equality |

### 8.6 Recommended order

1. **Option B**, because it is small, the graph already exists, and it converts the atom route's
   headline number from "local search against a relaxation" into a certificate. Reconcile the two
   ceiling bases in the same pass.
2. **Option D**, because it is the only piece of the VBL toolkit that applies to the zip instance
   as it stands.
3. **Option A**, gated on the R-C4 experiment. Run the full-ZCTA-graph test first and find out
   whether the connectivity obstruction is an artefact of restricting to sold zips. If it is, the
   whole exact line reopens and (centers) becomes its relaxation rather than its replacement. If
   it is not, A is dead and E is the honest record.
4. **Option C** only if A survives R-C4 and 3,748 units then proves too large — which, on the
   corrected frontier of §8.1, it probably will not.

---

## Where the rest lives

- `docs/CHANNEL.md` — the problem, the two stages, sizing. `docs/MODEL.md` — the N-way model and
  its open decisions (§6).
- `docs/OPTIONS_power-cell-contiguity.md` — the power-cell contiguity register; §1 the measurement
  record, §3a why D01 reads 55% by area, §4a the fixed-diagram figure, §8 assessed-and-rejected,
  §9 the recommended order.
- `docs/RESEARCH_FINDINGS.md` — the literature map, including §5's correction to the frontier
  claim and §8's verified absences.
- `docs/channel_note/channel_note.tex` — the source note, including the three sections omitted
  here. Its generated numbers are still v1; build with `make` after
  `export PATH=/Library/TeX/texbin:$PATH`.
- `docs/math_note/math_note.tex` — the two-player note: outer approximation, separator cuts,
  `scip_tree`, two toy instances.
- `STATE.md` — the resume point and the source of every number in this file.
