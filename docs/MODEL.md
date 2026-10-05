# The support-master model

This file states td's model: the support master, the ZIP realizer, the ledger and the audit. It
is #52 §4 (revision 7) written out in full, with the council's corrections of 2026-09-28
([memo](https://github.com/helios1168/td/issues/52#issuecomment-5865965201)) applied here as the
owner's answer OQ1 (i) directs. B2 (#65) verifies it. The C-numbers refer to the memo, the
S-numbers to the decisions in `docs/memory/decisions/support-refactor-2026-09-25.md`, and the OD
and U-numbers to `docs/problem/PROBLEM.md` and `docs/problem/UNKNOWNS.md`.

## 0. Tags

Every statement that could be false carries one tag. Definitions and algorithm steps carry none.

- **[proved]**: the proof is in this file, and B2 (#65) checks it; or, written **[proved, *key*
  *result*]**, the proof is the cited result's own, read at its source and listed as `verified` in
  `docs/REFERENCES.md`.
- **[claimed U*n*]**: not proved here; the unknown U*n* tracks it.
- **[policy *X*]**: a choice, not a fact. *X* names the owner decision that sets it or will set it:
  an open OD, or a settled S-decision, council item or issue.

Papers are cited by key and result and listed in `docs/REFERENCES.md`.

## 1. Cells, units, planning channels

**Cells.** A cell is a pair (z, f) of a ZIP z ∈ Z and a fine channel f ∈ F, with opportunity
M_{z,f} ≥ 0. The fine channels come from the extract's `channels.json`.

**Units.** Every ZIP belongs to exactly one unit u(z) ∈ V. A unit is one of:
- a state, with its carved-out pieces removed;
- a county-built piece, a union of counties inside one state (§6);
- a metro piece, which may cross state lines (§6).

Because every ZIP has exactly one unit, the loader rejects a spec whose pieces overlap. Z_v is the
set of v's ZIPs, and G_v is the ZIP graph induced on Z_v. The ZIP graph is the one OD2 names
**[policy OD2]**. The unit graph G joins two units when some ZIP of one shares a ZIP-graph edge
with some ZIP of the other.

**Planning channels.** A channel c has:
- fine channels F_c and a domain D_c ⊆ V × F. The domains of a scenario's channels partition
  V × F, and the loader rejects a gap or an overlap. Fallback opportunity is assigned before
  solving, so it counts in the bands **[policy S11]**;
- units V_c = {v : (v, f) ∈ D_c for some f}, ZIP masses m_z = Σ_{f : (u(z), f) ∈ D_c} M_{z,f},
  and unit masses M_v = Σ_{z ∈ Z_v} m_z (#52 writes M^c_v; the channel is implicit here);
- a district count K_c, a positive integer, the target τ_c = Σ_{v ∈ V_c} M_v / K_c, and the
  planning band [L_c, U_c] = τ_c[1 − δ_c, 1 + δ_c] with δ_c ≥ 0;
- a mode per unit, mode_c(v) ∈ {whole, clipped, free} (S9). A unit is *splittable* when its mode
  is clipped or free;
- support parameters (§2), η_c (§3.2) and optional contact caps (§3.3).

**Zero opportunity.** A unit with M_v = 0 in channel c, and a channel whose units all have zero
opportunity (τ_c = 0), are out of scope of this model: the loader drops such units from V_c, and
such channels from the run, before solving, and reports each one **[policy #65 F1]**. So M_v > 0
for every v ∈ V_c and τ_c > 0 for every channel solved. This is what the drawn shares (§4.1, §8),
Proposition D and the divided formulas of Claim 2 need. ZIPs with m_z = 0 inside a unit with
M_v > 0 stay in scope. No share convention for a zero-opportunity unit is assumed: a dropped
unit's cells in D_c carry no opportunity and are not drawn in c. They, and the cells of a dropped
channel, keep their ledger rows with the district blank and the reason `dropped: zero
opportunity` (§8), and the audit lists them without failing (§9).

A **final tolerance** [L^fin_c, U^fin_c] ⊇ [L_c, U_c] is declared per scenario and judges the
drawn map **[policy OD1]**.

## 2. Supports and closure

A support is a set of units that one district may draw from. With centroids p_u in the plane of
the ZIP points and d(u, v) = ‖p_u − p_v‖, 𝒮_c is the family of sets S ⊆ V_c such that:
- G[S] is connected;
- |S| ≤ s̄_c, the size cap;
- d(u, v) ≤ R_c(u, v) for all u, v ∈ S, the distance cap. #52 writes R_c as D_c(u, v), which
  collides with the domain.

The size and distance caps are the extent caps of #16 **[policy OD6]**. Under the rurality option,
R_c(u, v) = base_c · g(r_u, r_v) (§6). Supports listed in the spec are added together with all
their connected subsets.

**Closure.** 𝒮_c is *closed under connected subsets*: if S ∈ 𝒮_c, T ⊆ S and G[T] is connected,
then T ∈ 𝒮_c. The family above is closed **[proved]**. A connected subset of S is still connected
and no larger, and its pairs are pairs of S, so the pairwise distance condition is inherited
whatever R_c is. The listed extras are closed by construction.

A filter that removes supports must keep the family closed. C2 (#67) tests closure on the final
family, after the extras and any filters (C19). Porting notes, read at the tag
`archive/pre-support-2026-09` (`1251534`):
- The legacy enumerator `generate_valid_supports` builds this closed family: connected sets up to
  the size cap, then a pairwise distance filter (`tools/group2_support.py:27–63`) **[proved]**.
- The legacy National filter `filter_contiguous_supports` breaks closure: it keeps NE+NY but drops
  every support with only part of New England, including the singletons
  (`tools/group2_support.py:80–86, 115–119`) **[proved]**. It is not ported unchanged (C19).

## 3. The master

The master is one block per channel, with variables n_S ∈ ℤ≥0 (the number of districts drawn on
support S) and t_{v,S} ∈ [0, 1] (their total share of unit v):

```
Σ_S n_S = K_c
Σ_{S∋v} t_{v,S} = 1                                          v ∈ V_c
η_c n_S ≤ t_{v,S} ≤ n_S                                      v ∈ S
(L_c + μ_S) n_S ≤ Σ_{v∈S} M_v t_{v,S} ≤ (U_c − μ_S) n_S       band with rounding margin (§4.6)
whole v ∈ S:                   n_S ≤ 1,  t_{v,S} = n_S
clipped v ∈ S, |S| > 1:        n_S ≤ 1,  t_{v,S} = n_S
clipped v, S = {v}:            t_{v,S} continuous, n_S ∈ ℤ≥0
free v ∈ S:                    t_{v,S} continuous
contact cap (optional):        Σ_{S∋v} n_S ≤ cap_v
corridor floor (§4.2):         M_v t_{v,S} ≥ c_v(S) n_S                       v a cut vertex of G[S]
border cap (§4.3):             Σ_{S∋v, N(v)∩S={u}} n_S ≤ b_{uv}              free v, u ∈ N(v)
count cap (§4.4):              Σ_{S∋v} n_S ≤ |Z_v|
Menger row (§4.5, optional):   n_S ≤ κ_v(S)                                   v a cut vertex of G[S]
objective:                     min Σ_S w_S n_S
```

N(v) is v's neighbourhood in G. The band row with μ_S = 0 is #52's band row. The margin is
written into it here, as #52 does in its drawability block.

### 3.1 Decoding

The decoder expands each support with n_S ≥ 1 into copies j = (S, r), r = 1, …, n_S. Each copy
gets the planned share ȳ_{v,j} = t_{v,S} / n_S of each v ∈ S, and the planned mass
a_{v,j} = M_v ȳ_{v,j}. J_v is the set of copies with ȳ_{v,j} > 0. Decoded shares must sum to exactly
1 per unit, and anything else stops the run. There is no rescaling and no `other` pseudo-district
**[policy S26]**.

### 3.2 η (#47)

The row η_c n_S ≤ t_{v,S} gives every copy at least η_c of every unit in its support, so a copy's
footprint is its whole support (Claim 1). η_c > 0 is required by Claim 1 **[proved, §5]**. Its
value, a spec parameter per channel, is a choice **[policy C3, #47]**:
- The row removes plans. A district holding less than η_c of a unit in its support is excluded,
  so Claim 1(iii) holds only for plans that obey the same row (C3). The owner confirms this
  framing on B1's review.
- It implies a contact cap: summing the row over S ∋ v gives Σ_{S∋v} n_S ≤ ⌊1/η_c⌋ **[proved]**.
- The legacy solvers set it at articulation vertices: 0.25, or 0.10 and 0.05 in the grid
  solver (MATH_REVIEW §3.2 at the tag). They used it as a stand-in for a corridor, which it does
  not prove exists. Here η_c applies to every unit of a support, and the corridor floor (§4.2)
  does the corridor's job.

### 3.3 Extent and contact caps

- The size cap s̄_c and the distance cap R_c shape 𝒮_c (§2) **[policy OD6]**.
- A contact cap bounds how many districts touch unit v **[policy OD6]**.

### 3.4 Modes

A whole unit has one owner. A clipped unit is either whole inside one multi-unit district or split
among districts that lie inside it. A free unit may be split among any supports that contain it
**[policy S9; per spec]**. Claim 1(ii) shows that the rows above enforce these meanings.

### 3.5 Objective

w_S is the diameter of S, max_{u,v∈S} d(u, v). Alternatives are open **[claimed U38; the
business choice goes to OD6]**. Claims 1–3 and every proposition here hold for any weights w_S ≥ 0
that depend on S alone **[proved]**. Claim 1 carries the objective across unchanged, Claim 2
replaces it (exact form) or keeps it without using its values (bisection), and Claim 3 and §4 do
not involve it.

## 4. Drawability rows (S27)

S27 settles drawability in planning. This section states each row, what it is necessary for, and
the correction the council requires.

### 4.1 Drawings and read-back

A **drawing** of channel c gives every ZIP of every unit in V_c to one of K_c districts. District
j's *footprint* is the set of units in which it owns at least one ZIP. Its *drawn share* of v is
(Σ of m_z over its ZIPs in v) / M_v, defined because M_v > 0 for every v ∈ V_c (§1), and its
*drawn mass* is the sum of m_z over its ZIPs.

The **read-back** of a drawing is the plan (n̂, t̂):
- n̂_S is the number of districts whose footprint is S;
- t̂_{v,S} is the sum of their drawn shares of v.

A drawing is **connected** when every district's ZIPs induce a connected subgraph of the ZIP
graph.

𝒳_c(δ) is the set of connected drawings in which:
- every footprint is in 𝒮_c;
- every drawn mass lies in [L_c, U_c];
- the drawn shares obey η_c, the modes and the contact caps.

In short, these are the connected drawings that obey the same support family and policy rows as
the master.

### 4.2 The corridor floor (U39; #7, #14)

Take S ∈ 𝒮_c and a cut vertex v of G[S]. Let A_1, …, A_r (r ≥ 2) be the components of G[S] − v, and
∂_i ⊆ Z_v the ZIPs of v that have a ZIP-graph edge into a unit of A_i. Let ∂_{−i} = ∪_{k≠i} ∂_k.
Define:
- c^i_v(S): the least total mass Σ_{z∈P} m_z of a path P in G_v that starts in ∂_i and ends in
  ∂_{−i}. A single ZIP in both sets is a path. With no such path, c^i_v(S) = ∞, and the row forces
  n_S = 0.
- c_v(S) = max_i c^i_v(S), the **component-versus-rest floor**.

C2 (#67) computes it by node-weighted shortest paths on G_v.

**C6 (the corridor floor as printed is not necessary).** #52 printed c_v(S) as the largest, over
pairs of components, of the lightest chain between them. That value is not a necessary condition
when v separates three or more components, because a district can pass between two of them through
a third.
- Counterexample: v's ZIPs form the unit-mass path z1–z2–z3–z4–z5. A touches z1, B touches z5, and C
  touches both. The printed floor is 5 (the chain A to B), but {z1, z5} together with C is a
  connected district with mass 2 in v **[proved]**.
- The pairwise floor is valid when v separates exactly two components. There it equals the
  component-versus-rest floor **[proved]**.
- The corrected row uses the component-versus-rest floor, which is valid in general (Proposition D)
  but weaker: the counterexample gets floor 1, below the true need of 2 **[proved]**.
- C2 keeps the counterexample as a regression test.

This floor replaces the flat articulation share floor of 0.25. Whether it is the right necessary
condition, and how often it binds on the real extract, stay open **[claimed U39: the T part is
Proposition D, which B2 checks; the E part is measured in D1 (#73)]**. A corridor piece left by the
realizer means the floor missed a case, which is a master question.

### 4.3 The border cap

b_{uv} is the number of v's ZIPs that have a ZIP-graph edge into unit u.

**C7 (the border cap sums over S ∋ v).** #52 printed the sum as Σ_{S : N(v)∩S = {u}} n_S. That sum
also counts supports that do not contain v, such as the singleton {u}, which use none of v's ZIPs,
so the printed row is not necessary. The corrected row is
Σ_{S∋v, N(v)∩S = {u}} n_S ≤ b_{uv}, for free v and u ∈ N(v) **[proved, Proposition D]**. For whole or
clipped v the row holds automatically, since at most one active multi-unit support contains v and
b_{uv} ≥ 1 **[proved]**. C2 keeps a counterexample to the printed row as a regression test: a free
v adjacent only to u, with b_{uv} = 1, in a drawable plan that uses {u} twice and {u, v} once.
The printed sum is 3 and the corrected sum is 1.

### 4.4 The count cap

**C8 (the count cap is conditional).** Σ_{S∋v} n_S ≤ |Z_v| says every district planned on v can
own a ZIP of v. It is necessary only if every planned share must be drawn as at least one ZIP. The
audit merely lists a planned share that vanishes (§9), so as the audit stands this is a policy row
**[policy C8, S27]**. In the read-back sense of Proposition D it never excludes a drawing
**[proved]**.

### 4.5 The Menger row (optional)

**C9 (copies crossing a cut vertex need disjoint corridors).** For a cut vertex v of G[S] with
components A_i, let κ^i_v(S) be the largest number of vertex-disjoint paths in G_v from ∂_i to
∂_{−i}. By Menger's theorem this equals the size of the smallest set of ZIPs of v that meets every
such path.
Set κ_v(S) = min_i κ^i_v(S); min(|∂_i|, |∂_{−i}|) is a cruder bound that is also valid. The row
n_S ≤ κ_v(S) is necessary for the two-component case and for component versus rest **[proved,
Proposition D]**. It strengthens the drawability rows; it does not make them sufficient. It is
optional and off by default. C3 (#68) may add it; its acceptance does not require it.

### 4.6 The rounding margin μ_S (U33)

μ_S = Σ_{v∈S splittable} max_{z∈Z_v} m_z is the sum, over the splittable units of S, of the
heaviest ZIP in each.
- **Sufficient for the mass band.** Take a plan that is feasible with μ_S in its band row. Then
  every copy's drawn mass after transport and tree rounding (§7, steps 2–3) lies in [L_c, U_c],
  before repair, and strictly inside (L_c, U_c) when μ_S > 0 **[proved, Claim 3 and Corollary
  3]**. With μ_S = 0 (a support of whole units) the drawn mass equals the planned mass, which may
  sit on an endpoint.
- **Conservative.** It uses the heaviest ZIP in each unit rather than the heaviest one actually
  split, which is unknown before solving. It also counts a clipped unit in a multi-unit support,
  which is never split there. Using only the free units of S, plus v itself when S = {v} is
  clipped, is also sufficient, with the same closed and strict cases **[proved, Corollary 3]**.
  D1 (#73) reports the smallest δ with the
  margin, without it, and limited to units actually split (N2).
- **A policy.** It removes plans that could be drawn, and it can make lumpy units infeasible at
  tight tolerances. The planning band sits inside the final tolerance by the margin **[policy OD1,
  C3]**. A channel turns it off with `margin = false`, which sets μ ≡ 0 for that channel only;
  the default is on, and `run.json` records the setting per channel (§4.8) **[policy #84]**.

### 4.7 What the rows are necessary for

**Proposition D.** Let (n̂, t̂) be the read-back of a connected drawing in 𝒳_c(δ), with M_v > 0 for
every v ∈ V_c (§1). Then (n̂, t̂)
satisfies every row of §3 with μ ≡ 0, including the corrected corridor floor, the corrected border
cap, the count cap and the Menger row, and its objective equals the drawing's Σ_j w_{footprint(j)}
**[proved]**.

*Proof.* The coverage, band, η, mode and contact rows restate the definition of 𝒳_c(δ), summed over
the districts with each footprint. Let district j have footprint S ∋ v.
- *Count cap.* j owns a ZIP of v, and distinct districts own distinct ZIPs.
- *Border cap.* Suppose N(v) ∩ S = {u} and |S| ≥ 2. j's ZIPs in v can reach j's other ZIPs only
  through ZIPs of u. j is connected, so one of its ZIPs in v has an edge to a ZIP of u, and that ZIP
  is among the b_{uv}. Distinct districts, whatever their support, use distinct such ZIPs.
- *Corridor floor.* Let v be a cut vertex of G[S], and take the components of j's ZIPs inside v,
  called pieces. Contract each piece to a node, and the ZIPs of j in the units of each A_i to one
  node i. No ZIP edge joins two different A_i, because they are different components of G[S] − v,
  and pieces are not joined to each other. Since j is connected, the contracted graph is connected
  and bipartite, pieces against classes. Every class is present, because the footprint is S. A
  shortest path from class i to another class is i–P–k with k ≠ i. The piece P is connected in G_v
  and contains a ZIP in ∂_i and a ZIP in ∂_k ⊆ ∂_{−i}. Hence j's mass in v is at least
  M(P) ≥ c^i_v(S), for every i. Summing over the copies of S gives M_v t̂_{v,S} ≥ c_v(S) n̂_S.
- *Menger row.* The pieces P found above for distinct copies of S are disjoint and each contains a
  ∂_i–∂_{−i} path, so n̂_S ≤ κ^i_v(S) for every i. ∎

**Corollary (the master as a bound).** With μ ≡ 0 and the corrected rows, the master's optimum is at
most the least objective over 𝒳_c(δ), and its smallest feasible δ is at most the smallest δ for
which 𝒳_c(δ) is non-empty **[proved]**. #52 §4 claimed this for the printed rows, which C6 and C7
show to be false. It holds with the corrections.

With μ_S > 0 the band row is strengthened by the margin, and that row is a policy (§4.6), not a
necessary condition. A connected unit v of two unit-mass ZIPs, free, with K_c = 2, η_c = 0.5 and
band [0.5, 1.5], draws as one ZIP per district with drawn mass 1 each. But μ_{{v}} = 1 asks each
planned mass to lie in [1.5, 0.5], which is empty **[proved]**. So the master with μ_S > 0 is a
restriction of the master with μ ≡ 0, whose feasible set it shrinks, and neither its optimum nor
its smallest δ bounds the drawings. What stays necessary for the read-back of every drawing in
𝒳_c(δ) is the rest: the corrected corridor floor, the corrected border cap, the count cap, the
Menger row and the other rows of §3 with μ ≡ 0 (Proposition D). No set of rows here is
sufficient (§5, C10). A plan that passes every row can still fail to draw, and S28 makes that
failure loud.

### 4.8 The margin off (#84; council 2026-10-01, Est. 4)

With `margin = false` a channel's band row is #52's, L_c n_S ≤ Σ_{v∈S} M_v t_{v,S} ≤ U_c n_S, and
every other row is unchanged. Write μ°_S for the value §4.6's formula gives, which the master no
longer uses. What still holds:
- **Claim 1** holds with μ_S = 0: each copy's footprint is S, the modes hold, and each planned mass
  lies in [L_c, U_c]. Its proof uses no property of μ_S. (iii) now covers plans that obey the
  rows with μ ≡ 0, a larger set **[proved]**.
- **Claim 2** holds: the exact MILP's δ rows lose the μ term, and bisection stays valid because
  μ ≡ 0 does not depend on δ **[proved]**.
- **Proposition D and its Corollary** apply to this master as it stands, since they are stated
  for μ ≡ 0. Its optimum and its smallest δ are lower bounds over 𝒳_c(δ), but only for drawings
  with the same support family, modes, η_c, caps and drawability rows. With free units the bound
  is the bisection's `lower`, a δ proved infeasible; its upper end is a feasible δ, not a bound
  **[proved]**. Nothing here bounds a drawing under other supports or rules.
- **Claim 3 and Corollary 3** still bound the rounding: before repair, a copy's drawn mass differs
  from its planned mass by at most μ°_S, and by strictly less when μ°_S > 0, because Claim 3
  never reads the band row **[proved]**. What is lost is the band: a plan at an edge of
  [L_c, U_c] can draw anywhere in (L_c − μ°_S, U_c + μ°_S), so no row guarantees that a drawn mass
  lies in the band. The audit's final-band check is then the only judge of drawn balance
  **[policy S28, OD1]**.

On the 51 scenario (extract of 2026-10-01), national's smallest δ is 0.0675 with the key set
to false, as with the earlier in-memory zeroing of `supports.margin`, against 0.165 with the
margin on.

## 5. Claims

### Claim 1 (decoding; U30)

Assume η_c > 0 and 𝒮_c closed under connected subsets. Then **[proved]**:
1. The decoder of §3.1 turns every feasible (n, t) into K_c copies. Each copy's footprint is
   exactly its support S, so it is connected in G, and each copy's planned mass
   Σ_{v∈S} a_{v,j} lies in [L_c + μ_S, U_c − μ_S].
2. Each whole unit has exactly one owner. Each clipped unit is either whole in one multi-unit copy
   or split only among copies of {v}.
3. Every explicit-copy plan that obeys the same support family and the same policy rows maps to a
   feasible (n, t) with the same objective. An explicit-copy plan has K_c districts, each with a
   connected footprint contained in some member of 𝒮_c, and positive shares y_{v,j} on the
   footprint that sum to 1 per unit. The same rows are the per-copy
   forms of every row in §3: y_{v,j} ≥ η_c, the band with margin, the modes, the caps, and the
   drawability rows.

**C3 (Claim 1(iii) is conditional).** (iii) holds only for plans that obey the same support family
and the same policy rows. The row η_c n_S ≤ t_{v,S} removes plans, so η_c is a policy, as μ_S is
(§3.2, §4.6).

*Proof.*
- (1) If n_S ≥ 1, then t_{v,S} ≥ η_c n_S > 0 for every v ∈ S, so the footprint is S, which is
  connected by the definition of 𝒮_c. The band row divided by n_S is the per-copy band. Every other
  row divided by n_S is its per-copy form.
- (2), whole units. Take v whole. Every S ∋ v has t_{v,S} = n_S ∈ {0, 1}, and coverage gives
  Σ_{S∋v} n_S = 1, so exactly one copy holds v, with ȳ = 1.
- (2), clipped units. Take v clipped. If some S ∋ v with |S| > 1 has n_S = 1, then t_{v,S} = 1, and
  coverage makes t_{v,T} = 0 for every other T ∋ v. The η row then forces n_T = 0. Otherwise every
  share of v lies in copies of {v}.
- (3) Set n_S = |{j : footprint(j) = S}| and t_{v,S} = Σ_{j : footprint(j) = S} y_{v,j}. Each
  row of §3 is the sum of its per-copy form over the copies of S. Whole and clipped ownership make
  n_S ≤ 1 wherever the mode rows require it. The objective is Σ_j w_{footprint(j)} in both.
  Closure is used here: a connected footprint contained in some member of 𝒮_c is itself in 𝒮_c. ∎

η_c > 0 is what makes each footprint exactly S in (1). Without it, a copy could hold 0 of a unit
and its footprint could be disconnected.

### Claim 2 (smallest δ; U31)

S10: when clipped mode is infeasible, the run reports the smallest feasible δ. Throughout, K_c is a
positive integer, δ ≥ 0, and τ_c > 0 (§1), so the formulas below that divide by τ_c are defined.
- **Whole and clipped units only.** Minimising δ over the master is an exact MILP **[proved]**:
  - For |S| > 1, and for S = {v} with v whole, every unit of S is held whole, so n_S ∈ {0, 1} and
    t_{v,S} = n_S. The band row becomes δ ≥ (|M(S) − τ_c| + μ_S) n_S / τ_c, which is linear.
  - For S = {v} with v clipped, coverage makes t_{v,{v}} = 1 − Σ_{S∋v, |S|>1} n_S ∈ {0, 1}, and the
    η row forces n_{{v}} = 0 when it is 0. Otherwise n_{{v}} = k copies of mass M_v / k each.
    Binaries z_{v,k} with Σ_k z_{v,k} = t_{v,{v}} and n_{{v}} = Σ_k k z_{v,k} choose k from
    {1, …, min(K_c, |Z_v|, ⌊1/η_c⌋, cap_v if set)}, and δ ≥ (|M_v/k − τ_c| + μ_{{v}}) z_{v,k} / τ_c.
  - The remaining rows do not involve δ. The feasible set of this MILP, projected onto (n, t), is
    the union over δ of the master's feasible sets.
- **With free units,** the band row multiplies δ by a general integer n_S, so the run bisects on δ.
  Each step solves the normal model **with its objective kept** (trap 19). Bisection is valid
  because the feasible set grows with δ: L_c falls, U_c rises, and μ_S does not depend on δ
  **[proved]**. It needs fixed supports, modes and margins (C4), including OD5's metro
  classification (§6).
- A step that times out with a validated incumbent is feasible. A step that times out without one
  is **unknown**, never infeasible (C4).

**C4 (the smallest δ is a property of the master).** The exactness above belongs to the fixed,
restricted whole/clipped master. It says nothing about whether the plan can be drawn on ZIPs.
What does connect the two is the following **[proved]**:
- By the Corollary of §4.7, the master's smallest δ with μ ≡ 0 is at most the smallest δ at which a
  connected drawing in 𝒳_c exists.
- By Corollary 3, a plan feasible with μ_S draws, before repair, with every mass in its band
  [L_c, U_c], and strictly inside it when μ_S > 0. Connectivity is not implied.

The price of clipping, U35, is reported as a property of the master.

### Claim 3 (rounding; U33)

For a splittable unit v shared by the copies J_v (|J_v| ≥ 2), the realizer solves the transport LP
(§7, step 2):

```
min Σ_{z,j} m_z ‖p_z − c_j‖² f_{zj}   s.t.   Σ_j f_{zj} = 1  (z ∈ Z_v),   Σ_z m_z f_{zj} = a_{v,j}  (j ∈ J_v),   f ≥ 0.
```

It is feasible: f_{zj} = ȳ_{v,j} works, since Σ_j ȳ_{v,j} = 1 and Σ_z m_z ȳ_{v,j} = M_v ȳ_{v,j} =
a_{v,j}. Let x_{zj} = m_z f_{zj}. A ZIP is *split* when two or
more of its f_{zj} are positive.

**Lemma 3a (forest).** At a vertex (basic solution) of this LP **[proved]**:
- the edges {(z, j) : f_{zj} > 0} form a forest on Z_v ∪ J_v;
- no ZIP with m_z = 0 is split;
- at most |J_v| − 1 ZIPs are split.

*Proof.* At a vertex, the columns of the positive variables are linearly independent. Column (z, j)
is e_z + m_z e'_j. For m_z > 0, multiplying row z by m_z, which preserves the linear independence
of any set of columns, turns it into m_z(e_z + e'_j), a multiple of the bipartite incidence
column. For m_z = 0 every column of z equals e_z, so at most one is positive and z is not split.
An even cycle of incidence columns sums to zero with alternating signs, so the positive edges form
a forest. A forest on |Z_v| + |J_v| nodes has at most |Z_v| + |J_v| − 1 edges. Every ZIP has at
least one edge and every split ZIP at least two, so |Z_v| + s ≤ |Z_v| + |J_v| − 1, that is,
s ≤ |J_v| − 1. ∎

**Rounding along the forest.** Give each unsplit ZIP to its one district. The split ZIPs and J_v
span a forest H.
1. Root each tree of H at a district and visit its districts from the root down. Every split ZIP
   has a parent district and at least one child district.
2. District j's running error e_j starts at 0 at a root. Otherwise it starts at m_{z0} − x_{z0,j} if
   its parent ZIP z0 was passed to j, and at −x_{z0,j} if it was not.
3. j then visits its child ZIPs z in any order. It *takes* z when e_j < 0, adding m_z − x_{zj} to
   e_j, and *passes* z otherwise, adding −x_{zj}. A passed ZIP goes to one of its child districts.
   Where taking and passing both keep the bound below, the realizer picks the cheaper one under the
   transport cost.

**Claim 3.** A district j that touches no split ZIP draws exactly a_{v,j} in v. For a district j
that touches a split ZIP in H, let m*_j be the heaviest such ZIP; j's drawn mass in v differs
from a_{v,j} by strictly less than m*_j, in either direction **[proved]**.

*Proof.* e_j is exactly j's drawn mass in v minus a_{v,j}. If j touches no split ZIP, every ZIP
with x_{zj} > 0 is unsplit, so x_{zj} = m_z and j gets all of it; j is an isolated root of H, and
e_j = 0. Otherwise, a split ZIP has m_z > 0 (Lemma 3a) and 0 < x_{zj} < m_z, so the starting error,
0 at a root, lies in (−m*_j, m*_j). If e < 0, taking gives
e + m_z − x_{zj} ∈ (e, m_z) ⊂ (−m*_j, m*_j). If e ≥ 0, passing gives e − x_{zj} ∈ (−m_z, e)
⊂ (−m*_j, m*_j). So the sign rule always has a move that keeps the bound, and the refinement only
chooses between moves that keep it. ∎

**Corollary 3.** In each unit of S, a copy's error is 0 or less than the heaviest split ZIP it
touches there, hence at most that unit's heaviest ZIP, and 0 in a unit it holds whole. So its total
drawn mass differs from its planned mass by at most μ_S, and by strictly less when μ_S > 0: some
splittable unit of S then has a heaviest ZIP M* > 0, and the copy's error there is 0 or below the
heaviest split ZIP it touches, either way below M*. If its planned mass lies in
[L_c + μ_S, U_c − μ_S], its drawn mass lies in [L_c, U_c], and in (L_c, U_c) when μ_S > 0
**[proved]**. With μ_S = 0 the endpoints can be reached: two whole singleton units of mass 1 and
3, K_c = 2 and δ = 0.5 give the band [1, 3] and drawn masses 1 and 3 **[proved]**. In a unit the
copy holds alone there is no error, so the sum may run over the units actually split, as §4.6
says, with the same closed and strict cases.

**C5 (the scope of Claim 3).** The argument holds for an exact transport vertex, before repair,
including a split ZIP with several child districts. Summing the per-unit bounds is valid. It does
not guarantee connectivity, and repair (§7, step 4) may move mass afterwards. A floating-point
basis is checked, and a fractional graph that is not a forest stops the run (§7).

**Origin.** This adapts the forest structure behind Lenstra–Shmoys–Tardos rounding: the support of
a vertex of their assignment LP is a pseudoforest **[proved, `lenstra1990` Thm 1 and its proof]**.
Their rounding is one-sided. Each machine gets at most one job it held only fractionally, and the
theorem bounds its load from above only, by d_i + t **[proved, `lenstra1990` Thm 1]**. That suits
a makespan bound but not a two-sided band. Here a ZIP's mass is the same whichever district takes
it, which makes the support a forest rather than a pseudoforest and makes the two-sided bound
possible.

**Per-ZIP argmax has no such bound.** `centers.assign` at the tag takes each ZIP's largest share.
Let a district hold 0.45 of each of s unit-mass split ZIPs, a star with s + 1 districts that is a
valid vertex. Argmax gives every one of them away and misses by 0.45 s, which exceeds one ZIP from
s = 3 **[proved]**. Claim 3 keeps every district within less than 1, the heaviest split ZIP each
touches.

*Tested:* #52 ran 400 random units on 2026-09-25, and the worst error was 0.998 of the bound. A
fresh run for this file on 2026-09-29 covered 400 units with heavy-tailed and zero ZIP masses and
2–7 districts, with `highs-ds`. Every vertex was a forest, and the worst error was 0.996 of the
bound. Neither script was kept **[claimed U33]**. C4 (#69) adds the tests.

### C10 (clipped mode can fail to draw for connectivity)

#52 said that lumpy ZIPs are the only way a clipped unit can fail to draw. That is false.
- **Counterexample.** A clipped unit is a six-vertex star of unit-mass ZIPs, with K = 2, band [2, 4]
  and μ = 1. The planned shares are 3 each, inside [L + μ, U − μ]. But any connected part that
  avoids the centre is a single leaf of mass 1, so no connected in-band split exists **[proved]**.
- **What holds.** For an exact transport vertex rounded by Claim 3, the margin protects the mass
  band before repair (Corollary 3). It does not guarantee connected clipped districts.
- C4 (#69) runs this star, reports the disconnected district with its cause, and keeps both masses
  inside the final band.

## 6. Geography options

All are off by default (S13), and all geography is 2025 vintage (S17).
- **County-built pieces.** A piece is a union of counties inside one state, listed in the spec
  **[policy OD4]**. A ZIP belongs to the piece when its 2025 county in the reference table (G1) is
  in the list. The state's unit keeps its other ZIPs.
- **Metro pieces.** A metro piece holds the ZIPs whose county is in the metro's outline. The
  outline, and the rule for a metro too big for one district, are set by OD5 **[policy OD5]**.
  A whole unit lies inside one district, so a metro can be `whole` in channel c only if
  M_v ≤ U_c **[proved]**. A larger metro is an ordinary splittable unit (OD5).
- **The metro exception in clipped mode (S14).** A metro that crosses a state line keeps its own
  unit, and the audit logs each such crossing **[policy S14, OD5]**. It stays whole only when OD5's
  classification makes it whole. Each channel classifies every metro once, against the scenario's
  declared U_c: a metro with M_v ≤ U_c is whole and never split, and a larger one keeps its unit
  and is split under the scenario's clipped or free mode. The classification stays fixed through a
  smallest-δ search (`docs/memory/decisions/open-decisions-2026-09-28.md`, OD5).
- **Rurality caps (U36).** R_c(u, v) = base_c · g(r_u, r_v). Here r_v ∈ [0, 1] is v's rurality,
  built from its 2025 urban-area share and its counties' metro status (S19). The schedule g is
  symmetric, g ≥ 1, and nondecreasing in each argument, so caps loosen with rurality. g ≡ 1 when
  the option is off. Any such R_c keeps 𝒮_c closed (§2) **[proved]**. The schedule itself, the
  formula for r_v and the values of g are open **[claimed U36: B/E, D1 (#73)]**.

The state-level context is from the v2 whole instance at δ = 5% on the pre-2025 graph: every state
except CA, TX, NY and FL fits whole in one district (`docs/memory/facts/state-border-snapping.md`,
2026-09-07). It is not re-measured on the fresh extract **[claimed U35]**.

## 7. The realizer (S21)

Whole units need no realizer. If every unit is connected on the ZIP graph, a district made only of
units it holds whole is connected **[proved]**: each unit is connected, its support is connected in
G, and adjacent units in G share a ZIP edge.
C2 checks every unit after pieces and metros are carved (C11), and a disconnected `whole` unit stops
the run, naming the unit and its components **[policy OQ6]**. A district's part of a unit need not
be connected: pieces are reported with their cause, and S28 still applies **[policy OQ6]**.

For each splittable unit v with |J_v| ≥ 2:
1. **Centres.**
   - Clipped mode: k-means on v.
   - Free mode, j a copy of S with |S| ≥ 2: border-aware centres (S24). j's border in v is the set
     of v's ZIPs that have a ZIP-graph edge into a unit of S − v. It is never empty, since G[S] is
     connected and adjacent units share a ZIP edge. c_j is the mass-weighted centroid of the border
     when its mass is positive, and the unweighted centroid of the border's ZIPs when its mass is 0.
   - Free mode, the k ≥ 1 copies of the singleton {v}: the centres of opportunity-weighted k-means
     on v's ZIPs. For k = 1 this is v's opportunity-weighted centroid. The k-means is
     deterministic, so a run reproduces: its initial centres are chosen by weighted farthest-point
     from the heaviest ZIP, ties broken by ZIP id, and its iterations are capped at a fixed number.

   **[policy S24, #65 F6]**
2. **Transport LP** (Claim 3), solved with dual simplex (`highs-ds` with an explicit options dict;
   trap 14) so the solution is basic. A fractional graph that is not a forest stops the run.
   - ZIPs with m_z = 0 have zero cost and zero mass in the LP, so it does not place them by
     position. C4 must place them, and where they go affects only contiguity.
   - Before repair, every ZIP with m_z > 0 lies in the convex power cell of the district that
     transport and tree rounding give it to **[proved]**. By LP duality, f_{zj} > 0 with m_z > 0
     only if j minimises ‖p_z − c_k‖² − w_k over k, where w are the duals of the target rows, and
     rounding gives a ZIP only to a district with f_{zj} > 0. The cells form a power diagram, and a
     convex cut across a non-convex unit leaves *shape* pieces. Zero-mass ZIPs, placed separately,
     pieces moved by repair and ZIPs moved by the swap pass are not covered.
3. **Round along the forest** (Claim 3), not ZIP by ZIP.
4. **One repair pass** (S23). Move each detached piece, meaning each component of a district other
   than its heaviest, to an adjacent district only if all of these hold:
   - both districts stay inside the final tolerance **[policy OD1]**;
   - **mode guard (C16):** the target is admissible in every unit the piece touches, under that
     unit's mode. A piece of a clipped unit may go only to another district inside that unit. A
     piece of a free unit may go to any adjacent district.
   - **component guard (#85):** a piece moves between two exchange components (step 5) only when
     the worse of the pair improves, max(|m_j − w − τ_c|, |m_k + w − τ_c|) < max(|m_j − τ_c|,
     |m_k − τ_c|) for a piece of mass w from j to k **[policy #85]**.

   Otherwise the piece stays. The owner may later relax clipped mode so that repair can add an
   owner from outside the unit. That would be a model change, recorded as a policy, with Claim
   1(ii)'s clipped guarantee qualified. Listing the extra owner in the audit does not cure the
   violation.
5. **One swap pass** (#85). Two districts *share* a splittable unit v when both are planned there,
   a_{v,j} > 0. The districts linked through shared units form an *exchange component*. Before
   repair, drawn minus planned mass sums to zero over each one **[claimed U41]**. After repair,
   the pass moves one ZIP z of positive mass at a time from a district j to a district k that
   shares z's unit with j, and accepts the move only if all of these hold **[policy #85]**:
   - the worse of the pair improves by more than 10⁻⁹ τ_c: max(|m_j − m_z − τ_c|,
     |m_k + m_z − τ_c|) < max(|m_j − τ_c|, |m_k − τ_c|);
   - z's neighbours in j stay connected in j without z, and z touches k's main component, its
     heaviest, so neither district gains a piece and no detached piece grows;
   - j keeps a ZIP of positive mass in z's unit, so no planned share vanishes (C8).

   Each step makes the accepted move of largest gain, ties by ZIP id and target. Then
   **[proved]**:
   - every move stays inside one exchange component, so each component's drawn mass is unchanged;
   - no exchange component's worst deviation max_j |m_j − τ_c| grows, since only j and k change and
     both end below the pair's old worse deviation;
   - a district inside the final band whose partner is inside it stays inside, since the band is
     symmetric about τ_c; so if every drawn mass is in the band before the pass, it stays so;
   - the pass ends: each move lowers the districts' deviations, sorted from the worst,
     lexicographically, and there are finitely many maps.

   The pass optimises deviation from τ_c and ignores the plan: a move can raise or lower the target
   error Δ_{v,j}, so Claim 3 and Corollary 3 bound the map before repair and the swap pass, not
   after. How close a pair gets is open **[claimed U45]**.

There is no metro-binding step. A whole metro is its own whole unit, which the realizer never
touches; an oversized metro is an ordinary splittable unit (§6, OD5). Binding a metro inside a
split unit would make it one enormous ZIP and inflate μ_S.

The realizer reports the target error Δ_{v,j} = (j's drawn mass in v) − a_{v,j}. Each piece that
remains is reported with one cause:
- *shape*: a convex cut across a non-convex unit;
- *attachment*: the share does not touch the district's territory outside the unit;
- *corridor*: a share too thin to link the district's other units, as with WH_03 = CT + NJ + 5% of
  NY. This is a master question (U39);
- *tiny share*: a planned share smaller than the ZIPs available, which rounding can leave with no
  ZIP. The margin protects only the district's total mass band (Corollary 3), not the survival of
  each planned contact, and a vanished planned share is listed by the audit (C8, §9). Example: a
  free v of three unit-mass ZIPs at −2, −1 and 1 is shared by copies of {v, A}, {v, B} and {v, C},
  with A, B and C whole of mass 9, K_c = 3, η_c = 0.05, band [8, 12] and μ = 1. Planned masses in v
  of 0.2, 1.9 and 0.9 give district masses 9.2, 10.9 and 9.9, inside [9, 11]. With centres 0, −1.5 and 1 the transport
  vertex gives z1 whole to B and splits z2 (0.1 to A, 0.9 to B) and z3 (0.1 to A, 0.9 to C); the
  target-row duals (0, −0.75, −1) certify it optimal. Rounding from A as root passes both split
  ZIPs to the child that is cheaper under the transport cost, so A draws none of v, with drawn
  masses 9, 11 and 10 **[proved]**;
- *graph gap*: a ZIP not in the graph, or a missing edge.

How many pieces remain, by mode and cause, counted both as pieces and as districts in pieces, is
open **[claimed U34]**. Bugs #1, #7 and #11 become tests in C4.

## 8. The ledger (S25, S26)

The ledger's rules are policies **[policy S25, S26]**, except where a bullet is tagged.

- A cell's owner is the district that its channel's realizer gave the cell's ZIP to. The domains
  partition the cells, so each cell of a unit in V_c of a channel solved has exactly one owner, who
  holds all of its opportunity **[proved]**. A cell of a unit or channel dropped for zero opportunity (§1) has no
  owner in c. It keeps its ledger row, with the district blank and the reason `dropped: zero
  opportunity`.
- The master's shares are targets and are never read as masses after the realizer.
- A district's drawn share of a unit is the opportunity of its ZIPs in the unit divided by the
  unit's opportunity, defined when M_v > 0, as it is for every unit in V_c (§1).
- Planned shares appear only in the run's diagnostics, beside the drawn ones, as Δ.
- Reported shares, masses and bands come from the ledger, and maps are drawn only from it.

## 9. The audit

One `scorecard.md` per run, in the run directory. Each check is a policy of #52 §4, with its
source where one is named **[policy S28, OD1, OD3, C16]**:
- one owner per cell of the retained domain, the cells of units in V_c of the channels solved;
- the district count equals K_c for each channel solved;
- the cells of units and channels dropped for zero opportunity (§1) are listed, each with a blank
  district and the reason `dropped: zero opportunity`, and do not fail the run;
- final bands on the drawn masses, with every breach listed against the final tolerance
  **[policy OD1]**. A breach caused by a share that could not be drawn fails the run and names the
  unit and district **[policy S28]**;
- planned against drawn owners per unit:
  - a planned share drawn as no ZIPs is listed (C8);
  - a whole unit with more than one owner is a hard failure;
  - an extra owner from repair in a free unit is listed;
  - an owner outside a clipped unit is a mode violation and fails the run (C16);
- ZIP contiguity on the declared graph, with a verdict for any ZIP not in the graph. Pieces are
  listed with their cause and their share of the district's mass;
- mode compliance, with the metro exceptions listed (S14);
- the geography manifest is all 2025 (S17);
- the solver's status, bound and gap;
- one name per district;
- the certificate tier: exact, bounded or feasible only **[policy OD3]**.

## 10. Where each council item lands

| item | here |
|---|---|
| C2, C19: closure and the National filter | §2 |
| C3: Claim 1(iii) is conditional; η and μ_S are policies | §5 Claim 1, §3.2, §4.6 |
| C4: the smallest δ is a property of the master | §5 Claim 2 |
| C5: the scope of Claim 3 | §5 Claim 3 |
| C6: the corridor floor | §4.2, Proposition D |
| C7: the border cap | §4.3, Proposition D |
| C8: the count cap is conditional | §4.4 |
| C9: the Menger row | §4.5 |
| C10: clipped mode and connectivity | §5 C10 |
| C11: every unit must be ZIP-connected | §7 |
| C16: the mode guard on repair | §7 step 4, §9 |
