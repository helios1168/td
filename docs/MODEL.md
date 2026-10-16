# Territory-design formulations

F0 (§0) is the national reference problem. The stage IDs identify what each algorithm actually
solves; none silently substitutes its objective or restrictions for F0. The support-master
material retains #52 §4 (revision 7), with the council's corrections of 2026-09-28
([memo](https://github.com/helios1168/td/issues/52#issuecomment-5865965201)) applied here as the
owner's answer OQ1 (i) directs. B2 (#65) verifies it. The C-numbers refer to the memo, the
S-numbers to the decisions in `docs/archive/memory/decisions/support-refactor-2026-09-25.md`, and the OD
and U-numbers to `PROBLEM.md` and `docs/archive/problem/UNKNOWNS.md`.

## Reading conventions and formulation map

The inherited support-master proofs retain these tags. New stage contracts state their
domain and either a proof, inspected implementation or saved-result evidence explicitly.
Definitions and algorithm steps carry no empirical certificate.

- **[proved]**: the proof is in this file, and B2 (#65) checks it; or, written **[proved, *key*
  *result*]**, the proof is the cited result's own, read at its source and listed as `verified` in
  `docs/REFERENCES.md`.
- **[claimed U*n*]**: not proved here; the unknown U*n* tracks it.
- **[policy *X*]**: a choice, not a fact. *X* names the owner decision that sets it or will set it:
  an open OD, or a settled S-decision, council item or issue.

Papers are cited by key and result and listed in `docs/REFERENCES.md`.

Formulation IDs are stable even when section numbers move. The older §4 drawability rows
are now §3.6; their S27 label and all C/S/OD/U labels are retained. Sections 5–10 keep their
numbers so the Claim 3, S21 and S25/S26 references in code remain usable.

| stage | ID | section | certificate domain |
|---|---|---|---|
| national reference | F0 | §0 | complete routed national ledger; objective evaluators still inputs |
| support family, master and drawability | F2 | §§2–3, proofs §5 | continuous support plans; bounds only over the stated drawing domain |
| complete group / DAG / sequential draw | F4 / F4.DAG / F4.SEQ | §4 | fixed bodies, allowed owners and modeled band; P only |
| window and neck repair | F4.W / F4.N / F4.S | §4 | window and checked districts, outside fixed; strong rows unproven |
| single-district plan check / policy bans | F2.B / F2.C | §3.6.9 | current-M1 single-support test / no global certificate |
| transport, rounding, repair, territory | F7 | §7 | exact transport theorem versus numerical heuristic implementation |
| ledger and audit | F8 / F9 | §§8–9 | recorded assignment and supplied audit inputs |
| glue, warm start and sealed assembly | F11 | §11 | final audited ledger, not drawing optimality |
| branch-and-cut comparison | F142 | §12 | exported fixed group; no neck constraint |

Agent: modeler (openai-codex/gpt-6-astra). #143 phases 1–2: formulation contracts and
small-instance Pyomo specifications; these are not production solver backends.

## 0. F0 — national reference program

**F0 is stated authoritatively in [F0.tex](F0.tex), rendered as [F0.pdf](F0.pdf).**
It assigns the complete routed national ledger to 48–54 districts, with hard dollar windows,
connectivity and neck rules, and only the stated Manhattan exceptions. Shape, then balance,
then state splits define its priority; the numerical shape and balance evaluators remain owner inputs.
Model-sync updates the TeX source and rebuilds the PDF; the pipeline stages below are not F0 optimizers.

## 1. Cells, units, planning channels

These are the support pipeline's F2/F7 conventions, not additional restrictions or
coverage exceptions in F0. In particular, F0 does not drop zero-opportunity territory.

**Cells.** A cell is a pair (z, f) of a ZIP z ∈ Z and a fine channel f ∈ F, with opportunity
M_{z,f} ≥ 0. The fine channels come from the extract's `channels.json`.

**Units.** Every ZIP belongs to exactly one unit u(z) ∈ V. A unit is one of:
- a state, with its carved-out pieces removed;
- a county-built piece, a union of counties inside one state (§6);
- a metro piece, which may cross state lines (§6).

Because every ZIP has exactly one unit, the loader rejects a spec whose pieces overlap. Z_v is the
set of v's ZIPs, and G_v is the ZIP graph induced on Z_v. The ZIP graph is M1's polygon graph
(`td.geo.polygon_graph`): its vertices are every CONUS ZCTA, and two are adjacent when their 2025
TIGER polygons share a boundary of positive length or an owner-approved connector joins them
**[policy M1, OD2; #114]**. A ZCTA with no cell in the extract is a vertex with m_z = 0, so Z_v
is every ZCTA of v. The unit graph G joins two units when some ZIP of one shares a ZIP-graph edge
with some ZIP of the other, so a corner touch or a crossing with no approved connector joins no
two units, and every M1 graph edge between units is an edge of G: on the same ZIPs, E(M1) ⊆
E(G), which is sufficient for the units an M1-connected district touches to be connected in G
(`docs/archive/lenses/COUNCIL_2026-10-05.md` finding 13; a unit dropped for zero opportunity is not in
V_c, #119). Unit centroids (§3.5, the distance cap) weigh
only the extract's ZIPs, as before #114.

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
for every v ∈ V_c and τ_c > 0 for every channel solved. This is what the drawn shares (§3.6.1, §8),
Proposition D and the divided formulas of Claim 2 need. ZIPs with m_z = 0 inside a unit with
M_v > 0 stay in scope. No share convention for a zero-opportunity unit is assumed: a dropped
unit's cells in D_c carry no opportunity and are not drawn in c by the master or the realizer.
Zero-opportunity ZIPs are territory (owner, 2026-10-04, M1): the territory pass (§7 step 6) owns
a dropped unit's ZIPs in c, and its cells keep the reason `dropped: zero opportunity` with that
owner. A dropped channel has no districts; its cells keep their ledger rows with the district
blank and the same reason (§8), and the audit lists them without failing (§9).

A **final tolerance** [L^fin_c, U^fin_c] ⊇ [L_c, U_c] is declared per scenario and judges the
drawn map **[policy OD1]**.

## 2. F2 inputs — supports and closure

The family used by F2 is

$$
\mathcal S_c=\{S\subseteq V_c:G[S]\text{ connected},\ |S|\le\bar s_c,
\ d(u,v)\le R_c(u,v)\ (u,v\in S)\},
$$

augmented by listed supports and their connected subsets, then by the explicitly stated
filters below. These are stage inputs/restrictions, not F0 geography requirements.

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

**Width-aware contact (#124 A; `contact_min_km = W`, off by default).** This is a policy row
**[policy #124; the owner sets the default]**. Two units u, v count as touching in a support S
only where the ZIP-graph edges between them share at least W of land border, or where an approved
connector joins them that M1's land-passage rule leaves at unlimited width. Width is measured
as M1 measures it: `border_cm` per edge, floored to whole cm, summed over the edges between u and
v, and compared with W in whole cm. A connector counts unless land within states(S) replaces it
(`audit.NeckGraph.land_would_do`: joined by polygon edges alone through a passage at least 10 km
wide; this is the rule before 2026-10-14, M1 now counts every connector, §9). This is M1's district-level rule applied to the plan: it reads the states of S, not the
states a drawn district actually ends up owning ZIPs in, so it is an approximation of M1, not
M1 itself. With A on, 𝒮_c is the family above with "G[S] connected" replaced by "S connected in
its own contact graph C(S)". `td.supports` enumerates on the most permissive contact graph P,
which reads each pair's own states, and then drops each S that is not connected in C(S).
- The family stays closed under subsets connected in their own contact graph **[proved]**. Take
  S in the family and T ⊆ S with T connected in C(T). Then T is enumerated, because
  states(T) ⊇ states(u) ∪ states(v) for every pair u, v of T. More states can only make land
  replace a connector, never make one count again, so C(T) ⊆ P. The caps are inherited as above.
  T contains no forbidden pair because S contains none, and T passes the filter by assumption.
- C(S) ⊆ G, so Claim 1(i) still holds. In Claim 1(iii), "a connected footprint" now means one
  that is connected in its own contact graph.
- `Family.adj` stays G, so the drawability rows (§3.6) and Proposition D do not change. A support
  dropped by A is out of 𝒮_c, and so is every drawing that uses it as a footprint.

## 3. F2 — the support master

**Relation to F0: heuristic overall**, not a relaxation of national ZIP design. The master
relaxes ZIP indivisibility and does not enforce M1, but also fixes routing/K and restricts
supports, modes, eta, caps and possibly margins/bans. Its objective is support diameter,
not F0's lexicographic objective. With $\mu=0$, Proposition D gives a relaxation **over
$\mathcal X_c(\delta)$ only**, with the same policies and admissible bans; a positive margin
removes drawable plans. With arbitrary policy bans, include them in that domain or exclude
them from the bound (trap 24).

**Certificate.** `exact`, `bounded`, `feasible only` describe the numerical master solve,
not ZIP feasibility. A smallest-$\delta$ certificate is for this fixed master, not F0;
window bands have no delta search. No master incumbent certifies M1. Entry:
`td/master.py:140`
`def build(inst, channel: str, delta: float | None = None, fam=None, banned=()) -> Model:`.
Here $V_c$ denotes units (unlike F0's ZCTA set $Z$), $\mathcal S_c$ is §2's family,
and $M_v$, $K_c$, $[L_c,U_c]$ are §1's data.

The master is one block per channel, with variables n_S ∈ ℤ≥0 (the number of districts drawn on
support S) and t_{v,S} ∈ [0, 1] (their total share of unit v):

$$
\begin{aligned}
\min\quad&\sum_{S\in\mathcal S_c}w_S n_S,\\
\sum_S n_S&=K_c, & \sum_{S\ni v}t_{v,S}&=1,\\
\eta_c n_S&\le t_{v,S}\le n_S &(v\in S),\\
(L_c+\mu_S)n_S&\le\sum_{v\in S}M_vt_{v,S}\le(U_c-\mu_S)n_S,\\
n_S&\le1,\quad t_{v,S}=n_S
&&(v\in S\text{ whole, or clipped with }|S|>1),\\
\sum_{S\ni v}n_S&\le\operatorname{cap}_v
&&\text{(optional contact cap)},\\
M_vt_{v,S}&\ge c_v(S)n_S
&&\text{(cut vertex }v\text{ of }G[S]),\\
\sum_{S\ni v:\,N(v)\cap S=\{u\}}n_S&\le b_{uv}
&&\text{(free }v,\ u\in N(v)),\\
\sum_{S\ni v}n_S&\le|Z_v|,\\
n_S&\le\kappa_v(S)&&\text{(optional Menger row)},\\
n_S&=0&&\text{(banned support)}.
\end{aligned}
$$

Here $n_S\in\mathbb Z_{\ge0}$ and $0\le t_{v,S}\le1$. The hold equality is imposed for
each held unit $v$, not for the free units sharing its support. For a clipped singleton,
$t_{v,\{v\}}$ is continuous and $n_{\{v\}}$ integer; free-unit shares are continuous.
The redundant eta cap $\sum_{S\ni v}n_S\le\lfloor1/\eta_c\rfloor$ is also written by
`build`. The Menger row remains a specification option (§3.6.5), not a row emitted by
`td.master.build`. The optional support bans are B or C (§3.6.9).


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
  not prove exists. Here η_c applies to every unit of a support, and the corridor floor (§3.6.2)
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
replaces it (exact form) or keeps it without using its values (bisection), and Claim 3 and §3.6 do
not involve it.

### 3.6 Drawability rows (S27; F2)

S27 settles drawability in planning. This section states each row, what it is necessary for, and
the correction the council requires.

#### 3.6.1 Drawings and read-back

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

#### 3.6.2 The corridor floor (U39; #7, #14)

$$
c_v^i(S)=\min_{P:\,\partial_i\leadsto\partial_{-i}\ \text{in }G_v}\sum_{z\in P}m_z,
\qquad c_v(S)=\max_i c_v^i(S),
$$

with the minimum of an empty path family equal to $+\infty$. Take S ∈ 𝒮_c and a cut vertex v of G[S]. Let A_1, …, A_r (r ≥ 2) be the components of G[S] − v, and
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

#### 3.6.3 The border cap

b_{uv} is the number of v's ZIPs that have a ZIP-graph edge into unit u.

**C7 (the border cap sums over S ∋ v).** #52 printed the sum as Σ_{S : N(v)∩S = {u}} n_S. That sum
also counts supports that do not contain v, such as the singleton {u}, which use none of v's ZIPs,
so the printed row is not necessary. The corrected row is
Σ_{S∋v, N(v)∩S = {u}} n_S ≤ b_{uv}, for free v and u ∈ N(v) **[proved, Proposition D]**. For whole or
clipped v the row holds automatically, since at most one active multi-unit support contains v and
b_{uv} ≥ 1 **[proved]**. C2 keeps a counterexample to the printed row as a regression test: a free
v adjacent only to u, with b_{uv} = 1, in a drawable plan that uses {u} twice and {u, v} once.
The printed sum is 3 and the corrected sum is 1.

#### 3.6.4 The count cap

**C8 (the count cap is conditional).** Σ_{S∋v} n_S ≤ |Z_v| says every district planned on v can
own a ZIP of v. It is necessary only if every planned share must be drawn as at least one ZIP. The
audit merely lists a planned share that vanishes (§9), so as the audit stands this is a policy row
**[policy C8, S27]**. In the read-back sense of Proposition D it never excludes a drawing
**[proved]**.

#### 3.6.5 The Menger row (optional)

**C9 (copies crossing a cut vertex need disjoint corridors).** For a cut vertex v of G[S] with
components A_i, let κ^i_v(S) be the largest number of vertex-disjoint paths in G_v from ∂_i to
∂_{−i}. By Menger's theorem this equals the size of the smallest set of ZIPs of v that meets every
such path.
Set κ_v(S) = min_i κ^i_v(S); min(|∂_i|, |∂_{−i}|) is a cruder bound that is also valid. The row
n_S ≤ κ_v(S) is necessary for the two-component case and for component versus rest **[proved,
Proposition D]**. It strengthens the drawability rows; it does not make them sufficient. It is
optional and off by default. C3 (#68) may add it; its acceptance does not require it.

#### 3.6.6a The window band (`band_lo`, `band_hi`) **[policy, owner #112 comment, 2026-10-14]**

A channel may set `band_lo` and `band_hi` (0 < band_lo < 1 < band_hi). Its band is then the
dollar window [L_c, U_c] = [τ_c · band_lo, τ_c · band_hi] itself, not [τ_c(1 − δ), τ_c(1 + δ)]:
the master's band rows (§3), the realizer's internal band, B's `drawable` test, the repair's
final band and the audit's final band all read it, and `delta` and `final_delta` are kept for
reporting only (the equivalent δ is max(1 − band_lo, band_hi − 1)). The band is hard and never
widened: there is no wider-δ retry, `--diag-final-delta` is capped at it, and there is no δ to
search, so the smallest-δ searches (§5 Claim 2) solve the window once and report that
(`master.window_feasibility`, method `window`), `exact_delta` too whether or not the channel has free
units (the window branch comes before the free-unit rejection). Without the two keys everything is as before.

#### 3.6.6 The rounding margin μ_S (U33)

$$
\mu_S=\sum_{v\in S:\ v\text{ splittable}}\max_{z\in Z_v}m_z.
$$

μ_S = Σ_{v∈S splittable} max_{z∈Z_v} m_z is the sum, over the splittable units of S, of the
heaviest ZIP in each.
- **Sufficient for the mass band under Claim 3's exact LP hypotheses.** Take a plan that is
  feasible with μ_S in its band row. Then every copy's drawn mass after exact-vertex transport
  and tree rounding (§7, steps 2–3) lies in [L_c, U_c],
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
  the default is on, and `run.json` records the setting per channel (§3.6.8) **[policy #84]**.

#### 3.6.7 What the rows are necessary for

**Proposition D.** Exclude support-ban rows unless compliance with them is included in
$\mathcal X_c(\delta)$; the same proof holds for any fixed asymmetric window $[L_c,U_c]$.
Let (n̂, t̂) be the read-back of a connected drawing in 𝒳_c(δ), with M_v > 0 for
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

**Corollary (the master as a bound).** With μ ≡ 0, the corrected rows, and bans excluded
or included in the drawing domain as just specified, the master's optimum is at
most the least objective over 𝒳_c(δ), and its smallest feasible δ is at most the smallest δ for
which 𝒳_c(δ) is non-empty **[proved]**. #52 §4 claimed this for the printed rows, which C6 and C7
show to be false. It holds with the corrections.

With μ_S > 0 the band row is strengthened by the margin, and that row is a policy (§3.6.6), not a
necessary condition. A connected unit v of two unit-mass ZIPs, free, with K_c = 2, η_c = 0.5 and
band [0.5, 1.5], draws as one ZIP per district with drawn mass 1 each. But μ_{{v}} = 1 asks each
planned mass to lie in [1.5, 0.5], which is empty **[proved]**. So the master with μ_S > 0 is a
restriction of the master with μ ≡ 0, whose feasible set it shrinks, and neither its optimum nor
its smallest δ bounds the drawings. What stays necessary for the read-back of every drawing in
𝒳_c(δ) is the rest: the corrected corridor floor, the corrected border cap, the count cap, the
Menger row and the other rows of §3 with μ ≡ 0 (Proposition D). No set of rows here is
sufficient (§5, C10). A plan that passes every row can still fail to draw, and S28 makes that
failure loud.

#### 3.6.8 The margin off (#84; council 2026-10-01, Est. 4)

With `margin = false` a channel's band row is #52's, L_c n_S ≤ Σ_{v∈S} M_v t_{v,S} ≤ U_c n_S, and
every other row is unchanged. Write μ°_S for the value §3.6.6's formula gives, which the master no
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

#### 3.6.9 F2.B / F2.C — drawable alone and support bans (#124 B, C)

**F2.B relation to F0: heuristic overall; necessary-condition filter only for its stated
restricted drawing domain.** Its single-district subproblem minimizes a perimeter surrogate,
subject to the set below; it is not an F0 optimizer. Let
$H(S)$ and $F(S)$ be the held and free units, respectively. Its binary set-selection
formulation is

$$
\begin{aligned}
X&=\{z:x_z=1\}\subseteq\bigcup_{v\in S}Z_v,\\
x_z&=1&&(z\in Z_v,\ v\in H(S)),\\
\sum_{z\in Z_v}m_zx_z&\ge\eta_cM_v&&(v\in F(S)),\\
L_c\le\sum_zm_zx_z&\le U_c,\qquad
G[X]\text{ connected},\qquad X\text{ has no raw-gate neck}.
\end{aligned}
$$

For optional ZIPs $F_Z$ and held ZIPs $H_Z$, put $k_{zy}$ equal to polygon border length.
Continuous $c_{zy}\in[0,1]$ satisfy $c_{zy}\ge x_z-x_y$ and $c_{zy}\ge x_y-x_z$.
The objective, up to a fixed-body constant, is

$$
\min\ \sum_{zy\subset F_Z}k_{zy}c_{zy}
+\sum_{z\in F_Z}\left(\sum_{y\notin F_Z\cup H_Z}k_{zy}
-\sum_{y\in H_Z}k_{zy}\right)x_z.
$$

Only adjacency edges enter these sums. This polygon-border objective is not the gate's
width graph; the latter supplies the neck constraints, not perimeter cost. Code:
`tools/exp/contig/plancheck.py:206`
`    for z in F:                     # the perimeter: border to S's held units and to outside S`.
The perimeter is only a search objective: `CHECK_GAP=0.2` permits a 20% relative gap;
`drawable` is a feasibility witness, not a perimeter optimum certificate. `infeasible`
still requires the engine's infeasibility proof; timeout is unknown.
The current default gate-equivalent checks/no-goods support the conditional Proposition B
below, to solver tolerances; **opting into unproven strong rows does not**. Neither the
single-support feasible result nor all such results together certify that districts can
coexist. F0's explicit Manhattan exception is not implemented in this raw-gate filter;
its bans are not proofs excluding authorized exception-bearing F0 sets.
Entry: `tools/exp/contig/plancheck.py:122`
`def drawable(inst, c: str, s, delta: float, ng, time_limit: float = CHECK_TIME,`.

**F2.C relation to F0: heuristic policy restriction.** It adds $n_S=0$ after a proved
infeasible fixed-outside repair window. Such a proof need not exclude other drawings of
$S$; no F0 or unrestricted-$\mathcal X_c$ certificate follows. The master still minimizes
$\sum_S w_Sn_S$ with the new bans. Entry:
`tools/exp/contig/plancheck.py:605`
`def new_bans(found: list, limits: dict, done: dict, banned: dict) -> list:`.

The row $n_S=0$ removes support S. With the valid default rows, B adds it lazily only when
S is proved undrawable by any single district in the stated raw-gate domain. C adds it after a drawing, as a policy. Both are off by default, and the owner
sets the defaults **[policy #124]**. A timeout or an unknown result never adds the row; it is
listed instead.

**The single-district set.** For S ∈ 𝒮_c with |S| ≥ 2 and band [L_c, U_c], let D_c(S, δ) be the
ZIP sets X ⊆ ∪_{v∈S} Z_v such that:
- (a) Z_v ⊆ X for every v ∈ S that is held: whole, or clipped (in a support with |S| ≥ 2 a
  clipped unit is held whole, §3.4);
- (b) Σ_{z∈X∩Z_v} m_z ≥ η_c M_v for every free v ∈ S, which makes X ∩ Z_v non-empty because
  η_c M_v > 0 (§1, §3.2);
- (c) Σ_{z∈X} m_z ∈ [L_c, U_c];
- (d) X is connected in the ZIP graph;
- (e) X has no M1 neck (PROBLEM.md M1: no connected part holding at least 5% of X's land and no
  more land than the rest reaches the rest only through a passage narrower than 10 km, widths
  as M1 measures them).

Write 𝒳^N_c(δ) for the drawings in 𝒳_c(δ) (§3.6.1) in which no district has an M1 neck. M1
requires this of every drawn map.

**Proposition B.** If D_c(S, δ) = ∅, then n̂_S = 0 for the read-back (n̂, t̂) of every drawing
in 𝒳^N_c(δ). So the row n_S = 0 is necessary for 𝒳^N_c(δ) in the sense of Proposition D, and
Proposition D's Corollary holds with B's rows added, for drawings in 𝒳^N_c(δ)
**[proved, Sol verifier 8b0ddc7f, 2026-10-07]**.

*Proof.* Suppose a drawing in 𝒳^N_c(δ) has n̂_S ≥ 1. Take a district j whose footprint is S, and
let X be its ZIPs. Because the footprint is S, X ⊆ ∪_{v∈S} Z_v and X meets every Z_v with v ∈ S.
- (a) The drawing obeys the modes. A whole v has one owner, and j owns a ZIP of v, so j owns
  all of Z_v. A clipped v that a multi-unit district holds is whole inside that district (§3.4),
  so j owns all of Z_v.
- (b) The drawn shares obey η_c (§3.6.1).
- (c) Every drawn mass lies in [L_c, U_c].
- (d) The drawing is connected.
- (e) The drawing is in 𝒳^N_c(δ).

So X ∈ D_c(S, δ), which contradicts D_c(S, δ) = ∅. ∎

**The test** (`tools/exp/contig/plancheck.py::drawable`), with the default no-good rows and
current gate inputs, says `infeasible` in the following cases. The original argument was
verified by Sol (8b0ddc7f, 2026-10-07); #142 supplies the relay/width qualifications below.
The opt-in strong-row path has no such necessary-condition guarantee.
- *Held units only.* By (a), X is the union of S's ZIPs. The test reports a mass outside the
  band by more than 1e-9 τ_c, two or more components, or an M1 neck the exact check proves
  (the gate's: `necks_gate.gate_necks`, which is `td.audit.district_necks` with the channel's
  zero-opportunity ZCTAs as relays, R3, on `necks_gate.gate_graph`; status `proved`; #142). An
  unresolved neck check gives `unknown`.
- *Otherwise.* HiGHS proves infeasible a MILP whose feasible set contains every X ∈ D_c(S, δ).
  Each of its rows holds for every such X:
  - x_z ∈ {0, 1} on the ZIPs of the free units, with the held ZIPs fixed in: this is (a).
  - The η rows are (b), and the band row is (c).
  - A single-commodity flow from the heaviest held component, or from a chosen root ZIP when S
    has no held unit, gives one unit to each chosen ZIP and to each other held component, and an
    arc carries flow only between chosen ZIPs. Every connected X admits such a flow: send along
    a spanning tree of X with the components contracted. So this row is (d).
  - *Wide-passage rows.* Take the heaviest held component b_0 and any other held component b,
    with land areas a_0 and a_b. A flow from b_0 to b of at least 10 km − 0.5 cm must exist. An
    edge's capacity is its width, capped at that value, and an edge carries flow only between
    chosen ZIPs. The row binds only when min(a_0, a_b) ≥ 0.05 (1 − 10⁻⁹) of X's land, through
    a binary q and a row that lets q = 0 only when the share exceeds the smaller body's land.
    Validity: take an X ∈ D_c(S, δ) in which both bodies hold the share, and any edge cut of X
    separating b_0 from b. Let A′ be the component of b_0's side that contains b_0. If A′ holds
    no more land than the rest, it meets the neck definition's side conditions, so by (e) its
    cut is at least 10 km. Otherwise, let B′ be the component of X − A′ containing b. Then B′
    holds the share and less than half the land, and every edge leaving B′ goes into A′, so B′'s
    cut is a sub-cut of A′'s, and by (e) it is at least 10 km. Either way the cut holds a
    sub-cut of at least 10 km. Widths are whole cm in M1's check, so a cut without a neck is at
    least 1,000,000 cm, and the capped capacities sum to at least 10 km − 0.5 cm. By max-flow
    min-cut the flow exists. Contracting a component only removes cuts.
    *Under M1's relays (R3) and gap edges (R2) the argument needs one more condition (#142)*:
    a cut of the gate's graph may then use a relay, or an edge that is no polygon edge or
    connector, which a flow over the held and free ZIPs alone does not carry. The rows are added
    only when `necks_gate.bridged` is False for the district's possible ZIPs: no width edge
    between two nodes (a body is one node) that is not an own edge (`NeckGraph.own_edge`), and
    no connected set of zero-opportunity ZCTAs outside the held ZIPs (a free zero-opportunity ZIP
    left out of X is one) touching two nodes. With nothing bridged, a relay set touching one node
    at most goes with that node at no cost, so a cut of the gate's graph is a cut of the flow's.
    Otherwise no wide-passage row is added (`wide_pairs` 0): the MILP is looser, never wrong.
  - *Neck cuts, the default no-good row* (#142, supervisor ruling 2026-10-15). `repair.neck_cuts`
    builds, for each district j with a proved neck on the incumbent, one row from the incumbent's
    drawing X = (j's ZIPs) ∩ W of the window W (§4.6 of the review on
    `m5-studio/national-approaches`, `notes/2026-10-14_national-approaches-review.md`;
    `necks_gate.nogood_terms`):

    $$
    \sum_{z\in X\cap W}(1-x_{z,j})+\sum_{z\in W\setminus X}x_{z,j}\ge1.
    $$

    the ZIPs outside W being constants. *Validity.* The gate (`check_m1`) judges each district on
    its own: `audit.district_necks` takes the district's ZIPs, the gate's width graph, and the
    channel's zero-opportunity ZIPs as relays (R3), and the relay set depends on zero opportunity
    alone, not on how the other districts are drawn. A drawing of W in which j's part of W is X
    leaves j's ZIPs equal to the incumbent's (everything outside W keeps its owner), so j has the
    neck the gate found there and the gate rejects it. A drawing the gate accepts therefore has
    another j-part of W and meets the row; the row excludes one drawing of j and nothing else. It
    is weaker than a valid width row excluding that drawing (the repair may take more rounds)
    and needs none of its side
    conditions: the neck's side may be large, its relays may be j's or the window's, its rest may
    join it by gap or relay edges alone. `draw.NeckCut` carries it unchanged in form: anchors
    X ∩ W, `single` weight 1 on each ZIP of W∖X, `const` 0, `need` 1, `share` 0, `a_min` 1, so
    that the two NeckCut rows read t + Σ_{z ∈ X∩W}(1 − x_{z,j}) ≥ 1 and Σ_{z ∈ W∖X} x_{z,j} ≥ t, which
    hold for a binary t exactly when the no-good does; an anchor ZIP j cannot own makes the
    row trivially true, as it should.
  - *Neck cuts, the strong row* (`repair.py --neck-rows strong`, `TD_NECK_ROWS=strong`; **off by
    default and unproven**). `necks_gate.cut_terms` builds a width row instead. Its proposed
    argument requires connected anchors and domination of the relevant gate cut capacities;
    those hypotheses have not been proved for the implementation. Its left side counts the gate's
    widths: for the part C of A that holds the anchors, all edges to ZCTAs that are X's, or
    are or may be relays (zero opportunity, whoever owns them), with the relays the gate's cut
    puts with C counted on their edges to the rest, and the edges inside A that may join C to
    the rest of A. A window relay that X may own instead counts the larger of its two sides'
    edges, plus its edges to the relays that stay with C if X owns it. When A holds at most
    half of the land of the held ZIPs outside the window, C holds at most half of X's land in
    every drawing and the gate may cut C off, so this is the whole row. **When A holds more
    than half of it**, C may hold more than half of X's land and the gate then cuts another
    part K of X off instead: the row is widened, and counts also every edge among the held and
    window ZIPs and the possible relays outside A that is no own edge, and every edge from a
    possible relay to them (an edge between two possible relays counts when either is a window
    ZIP of zero opportunity, which X may own). That row is weaker and binds less next to
    large relays, but is still built. **Status:** each round of review found a drawing the gate
    accepts that a version of this row excluded (the last at 8802f6c:
    `neckcut_search.py --seed 1 --graphs 40000 --every-first --p-zero 0.5`, 1 case in 582,968
    drawings, kept as a regression in `tests/test_neck_gate_parity.py`); the present version has
    0 on that run and on seeds 11 and 5, which is a search and not a proof, so the default stays
    the no-good row. `tools/exp/contig/neckcut_search.py --rows nogood|strong` is the brute-force
    search over random 5-ZIP graphs (every drawing of a window against every row built; exit 1 on
    a row that breaks on a drawing the gate accepts); the default rows have 0 on seeds 11 and 5
    (40,000 graphs each) and on the run above. `tests/test_neck_gate_parity.py` checks both kinds on random graphs with
    relays, gap edges and connectors and the strong one by hand on the cases that broke earlier
    versions.
  - *Widths in both kinds of row* are M1's widths (`audit.neck_widths`, through
    `necks_gate.edge_km`): a border or gap edge counts as its floored whole cm, an approved
    connector at full width (#140), capped at the limit less half a cm. With the pre-2026-10-14
    land rule on (`TD_NECK_PRE_2026_10_14_LAND_RULE=1`, §9) a connector counts 0 where land
    replaces it within a set of states that X certainly owns ZIPs in: the held ZIPs' states
    (and, in the wide-passage rows, the state of each free unit that lies in one state; X meets
    it by (b)). M1 reads X's own states, which form a superset, and in a superset land replaces
    a connector at least as often.
- HiGHS proves infeasibility to its feasibility tolerance (1e-7, trap 14). A plan at the edge of
  a band is the same numerical corner as in the master. The verdict is cached monotonically in
  δ: an infeasible verdict at δ also holds at every δ′ ≤ δ, because the band only narrows. A
  drawable verdict at δ also holds at every δ′ ≥ δ.

**B's loop** (`plan_checked`, default valid rows). Solve the master. Test each multi-unit support in use. Add n_S = 0
for each one proved infeasible, and re-solve, until every support in use is drawable or unknown.
A channel left with no plan at its δ moves to the smallest δ up to `final_delta` at which the
loop finds one, by bisection with B inside each probe (`checked_delta`), only on legacy
symmetric-band channels. With a window band it solves that window once, without widening. The report records each
δ change and the B bans that forced it. B is necessary only for drawings without a neck, in the
sense above. It is not sufficient (C10).

**C, support bans after a drawing (`replan_rounds = R`)** **[policy #124]**. The map is drawn
and repaired. A district left in pieces or with a neck counts for C only when the last repair
window on it was proved infeasible: not unknown, and not cut short by the budget. That support
gets n_S = 0 (`ban_supports` in the next round's spec copy), and the map is planned, drawn and
repaired again, for up to R rounds. A window's infeasibility is conditional on everything
outside the window being fixed, so it does not prove that S cannot be drawn. A C ban is
recorded as "window infeasible (outside fixed)". It can remove drawable plans, and the master
with C bans bounds nothing. Each ban names the exact unit set, the channel, the window (attempt,
shape, |W|, and whether the `--max-zctas` cap stopped its growth) and its cost before and after:
δ, the master's objective, and the drawn map's splits and cuts.

## 4. F4 — ZIP draw groups, DAG restriction and window repair

### 4.1 F4 — complete conditional P-connectivity model

**Relation to F0: heuristic overall.** Fixing a plan's K, bodies and allowed owners is a
restriction of assignments, but omitting N-connectivity is a relaxation and the objective
is different. Thus there is no feasible-set containment or F0 bound for the combined stage.
It is **exact for its specified conditional P/band subproblem**, not exact national drawing.
Entry: `tools/exp/contig/draw.py:770`
`def _solve_group(c, zs, allowed, bodies, body_of, fixed, adj, m, p, unit_of, hold, plan, planned,`.

**Sets and data.** For a fixed channel, let $Z_g$ be a coupled group's free ZCTAs, $J_g$ its
districts, $A_z\subseteq J_g$ their allowed-owner lists, $v(z)$ their unit and $m_z$ their
channel mass. Each connected fixed body is contracted to a vertex in $B_j$; $\Gamma_j$ is
the graph of the free ZCTAs allowed to $j$ and its bodies. The fixed mass $F_j$ includes
bodies and any `extra` mass; $[\ell,u]$ is the actual modeled interval. Arm `arm1` keeps the
plan's holders on split units; `split` admits neighboring holders; `move` additionally caps
holders on each already-split unit at the planned count. Exclaves and dropped units have
separate adjacency-derived owner lists. A single-holder unit fixes its largest component;
its other components are free. Root bodies in `draw` are ordered by ZCTA **count**, not
mass: `tools/exp/contig/draw.py:241` `    return sorted(out, key=lambda c: (-len(c), min(c)))`.
The “heaviest body” comment at line 816 does not describe that ordering. Repair orders
bodies by mass instead. Any genuinely connected fixed body can serve as a root.

**Variables and base rows.** Binaries $x_{zj}$ assign free ZIPs; $y_{vj}$ are holder
indicators. Continuous $c_{zw}\in[0,1]$ represent free/free cut edges; land excesses
$e_{vjk}\in[0,1]$ are optional. For absent pairs set $x_{zj}=0$; a body of $j$ has value 1.

$$
\begin{aligned}
\sum_{j\in A_z}x_{zj}&=1 &(z\in Z_g),\\
x_{zj}&\le y_{v(z),j},\\
\ell-F_j\le\sum_{z\in Z_g}m_zx_{zj}&\le u-F_j &(j\in J_g),\\
c_{zw}&\ge x_{zj}-x_{wj} &(z<w,\ zw\in E_P,\ j\in A_z).
\end{aligned}
$$

The code imposes $x\le y$, not a reverse incidence row. The positive new-holder cost makes
unnecessary new holders unfavorable. Before separation, $x_{zj}\le\sum_{w\in N_\Gamma(z)}x_{wj}$
is added unless $z$ touches a body of $j$, or $j$ is rootless and some single allowed ZIP
could meet its residual lower bound. Optional `fixed_targets` adds, for each unit/district,

$$
a_{vj}-m_v^{\max}\le F_{vj}+\sum_{z\in Z_g\cap Z_v}m_zx_{zj}
\le a_{vj}+m_v^{\max},\qquad m_v^{\max}=\max_{z\in Z_v}m_z.
$$

Without that option the planned shares are **not fixed drawing targets**. The `prune`
step removes a pair only if every root-to-ZIP path exceeds $u-F_j$ in free mass, or a
rootless allowed component has mass below $\ell-F_j$. Proof for the fixed-body model:
a connected drawing containing $z$ contains such a path; nonnegative path mass is no larger
than its free mass. This does not validate the prior choice of bodies or owner lists.

**Objective.** Let $Y^+$ be unit/district pairs without a fixed holder, $g_{zj}$ the geodesic
moment coefficient (mass over mean plus area floor, times squared geodesic distance),
$k_{zw}$ free/free border km and $k_{zj}^{B}$ border to $j$'s fixed bodies. A nonfinite
raw moment coefficient is replaced by four times the largest finite one (default 1 if
none is finite), before normalization. Then

$$
\min\ 1000\sum_{(v,j)\in Y^+}y_{vj}
+\beta\left(\sum_{zw}k_{zw}c_{zw}-\sum_{zj}k_{zj}^{B}x_{zj}\right)
+\gamma\sum_{zj}g_{zj}x_{zj}
+\sum_{v,j\ne k}\omega_v e_{vjk}.
$$

$\beta=900/\max(10^{-12},\sum k_{zw}+\sum k_{zj}^{B})$ and
$\gamma=9/\max(10^{-12},\sum_z\max_{j\in A_z}g_{zj})$. The negative body credits omit a
constant, so it is the border term's **range**, not its signed value, that is at most 900.
For each land-term unit $v$, let $H_v$ be its holders planned at least $0.20\tau$ there,
$A_v$ its land and $A_{vj}$ its assigned land, including fixed land. With requested ratio $R$,

$$
e_{vjk}\ge\frac{A_{vj}-R A_{vk}}{A_v}-(1-y_{vk}),\qquad
\omega_v=\frac{900}{(|H_v|-1)|\mathcal V_{\rm land}|}\quad(j,k\in H_v,\ j\ne k).
$$

This is a soft term, not a hard land-ratio rule. Border, moment and land variation can sum
to $900+9+900=1809>1000$: **the scalar objective is not holder-first lexicographic when
land is on**, despite the source comment. It does not optimize balance within the band.
Code: `tools/exp/contig/draw.py:82`
`SPLIT_WEIGHT = 1000.0       # one more holder of a unit outweighs any shape difference`;
`tools/exp/contig/draw.py:906`
`                        cost.append(LAND_WEIGHT / ((len(hs) - 1) * len(terms)))`.

**Complete connectivity rows.** A separator $S$ between selected vertex $a$ and a fixed
root yields $x_{aj}\le\sum_{s\in S}x_{sj}$ (left side 1 for a body). With no fixed root,
use an owned vertex $b$ in another component:

$$
x_{aj}+x_{bj}-\sum_{s\in S}x_{sj}\le1.
$$

The solve/check/cut loop adds the detached component's ring and the main-component ring
reachable from it without entering main; `layers=True` also adds BFS-layer separators.
Every connecting path crosses each separator. At the generating disconnected solution
all separator vertices are unowned, so the row excludes it. There are finitely many
assignments: without time limits, exact separation terminates, possibly exponentially.
Optional `flow=True` adds nonnegative flows on $\Gamma_j$ for districts **with bodies**:

$$
 f^j_{ab}\le C_j x_{bj},\qquad
 \sum_a f^j_{av}-\sum_b f^j_{vb}=x_{vj}\quad(v\ne r_j),
$$

with $x_{vj}=1$ at non-root bodies, no arcs into root, and $C_j$ greater than total demand.
At an unowned vertex all inflow is zero, hence conservation makes outflow zero too. A
spanning-tree flow proves sufficiency for selected connected sets. Rootless districts
still need separator rows. Contracting a disconnected union is not this theorem.

**Certificate.** `optimal` is connected optimality for this group model at
`mip_rel_gap=0` and final absolute gap $10^{-6}$, not symbolic exactness (trap 12).
`connected` is an incumbent, possibly constructed. `infeasible` excludes connected
assignments only for these bodies, owner lists, rows and band. `unknown` proves nothing.
The initial absolute gap is 0.05 until a connected incumbent exists. The start validator
uses $10^{-7}\max(1,u)$ for its stored rows: at FI $u=1035$M this is \$103.50, not an
allowed dollar-window slack. The final dollar gate still decides. Code:
`tools/exp/contig/draw.py:1122` `    tol = 1e-7 * max(1.0, hi)`.
Joint groups share no free ZCTA or district, so P and mass feasibility factor, as does the
sum of the objectives actually assembled per group. This is not separability of arbitrary
F0 map evaluators, or a proof about N-connectivity.

**Pyomo specification:** `td.formulation.f4:prepare` independently prepares pruning,
geodesic and objective coefficients from the group inputs, taking F7 centers as fixed
inputs; `td.formulation.f4:build_model` implements the base, optional move/target/land
rows and complete P-connectivity, without DAG, repair-count or neck rows. Its flow
extension uses $t_j\in\{0,1\}$, $x_v^j\le t_j\le\sum_v x_v^j$,
$\sum_v r_v^j=t_j$, $r_v^j\le x_v^j$ and
$\sum_u f^j_{uv}-\sum_w f^j_{vw}\ge x_v^j-|\Gamma_j|r_v^j$, with both-end capacities
$f^j_{uv}\le|\Gamma_j|x_u^j,|\Gamma_j|x_v^j$; a body fixes $t_j=1$ and its root.
This also permits an empty rootless district when `extra` meets its lower band, as the
production separator loop does; the rootless-component/tree proof above applies to
every nonempty selection. `tests/test_formulation.py` numerically compares optima at
zero relative gap and fixed-point verdicts against the unchanged production solve path
on 38-, 30- and 50-ZCTA grids, a 30-ZCTA multiple-body/pruning path, and a 30-ZCTA
induced FI_PA export slice (slice-specific bodies/lists/band, not the original window).
The spec is capped at 300 ZCTAs including bodies. Entry: `td/formulation/f4.py:115`
`def build_model(data, *, connectivity=True):`.

### 4.2 F4.DAG and F4.SEQ — restricted-first drawing

**F4.DAG relation to F0: heuristic overall; restriction of F4.** With geodesic distance
$d_j(z)$, replace the local neighbor row, except at a body neighbor or a zero-distance seed, by

$$
x_{zj}\le\sum_{w\in N_\Gamma(z):\ d_j(w)<d_j(z)}x_{wj}.
$$

A connected district need not have monotonically descending paths, so DAG infeasibility
is not F4 infeasibility. The same separator loop still checks connectivity. **Certificate:**
a returned drawing is P-connected for the conditional model; any DAG optimum/bound is
only over the DAG restriction. It is never a bound on the complete F4 optimum or F0.
Entry: `tools/exp/contig/draw.py:406` `def _attempt(solve, d, tried, prove: bool = True):`;
`tools/exp/contig/draw.py:412` `    for dag in (True, False):`.
The DAG attempt runs first and can exhaust the budget before the complete model runs.
With `prove=False`, a connected DAG result also skips the complete attempt. The
2026-10-14 first-attempt timeouts are therefore restricted-first pipeline timeouts,
not evidence that the complete model timed out or the group is infeasible (review §3.2).

**F4.SEQ relation to F0: heuristic**, neither a restriction nor a relaxation of joint F4.
One split unit (or a coupled cluster of adjacent units) is processed at a time. A district's
adjacent already-owned ZIPs are contracted as one body even if that union is disconnected;
not-yet-drawn units contribute planned `extra` mass. Its residual band becomes

$$
\max(0,\ell-F_j)\le\sum_{z\in Z_g}m_zx_{zj}\le\max(0,u-F_j).
$$

Thus an already-overweight district is not forced back. **Certificate:** only the local
modeled assignment, not the original district's P-connectivity or full drawn window.
Entry: `tools/exp/contig/draw.py:428`
`def _sequential(inst, plan, c, owner, free, exclave, allowed, hold, planned, support, p, delta,`;
`tools/exp/contig/draw.py:499` `            g = _attempt(solve, d, tried, prove=False) or g`.
The eventual full audit, not the local status, establishes map feasibility.

### 4.3 F4.W — window repair

**Relation to F0: heuristic overall; assignment restriction to a window.** For $W\subseteq Z$,
fix $x_{zj}=\bar x_{zj}$ for $z\notin W$ and solve F4 on $W$. Bodies are genuine outside
components touching $W$, plus the main component of a district being repaired. Other
components remain outside the connectivity model and enter its mass via `extra`.
Allowed districts are owners in/touching $W$, further restricted by `--keep-support` unless
the ZIP's unit is opened. The band is `ch.final_band`; `band_lo`/`band_hi` make it the
hard window, without widening. Legacy `--window` intersects rather than replaces that
band: $[\max(L^{\rm fin},L^\$),\min(U^{\rm fin},U^\$)]$. For example,
$\tau=1200$, $\delta=.15$ gives $[1020,1380]$, not the entire $[1000,1437.5]$.

Entry: `tools/exp/contig/repair.py:385`
`def solve_window(inst, plan, owner: dict, W: set, p: dict, time_limit: float, cap: bool,`.
It calls DAG then complete F4, with at most a quarter of the window limit for DAG,
layer separators, optional flow and the neck callback (§4.4). Ball windows double their
hop radius while proved infeasible, followed by near-shortest-path corridors up to the
size cap. `--jobs` races windows in processes, with one solver thread each (trap 18).

**Equivalent engines (#142 phase 2).** `--engine highs|scip` leaves this model unchanged.
SCIP uses F142.c's separator handler on the actual window matrix, retaining repair-count,
cap, DAG, optional flow and dynamically added neck rows, unlike the stripped phase-0
export. The start is an incumbent hint, not a constraint. Relative gap is zero; SCIP's
absolute objective gap is $10^{-6}$ throughout. The HiGHS path retains its loose first
phase followed by the final $10^{-6}$ solve. An engine's unknown is not a proof; the
DAG-only infeasibility cannot authorize growth. Entry: `tools/exp/bnc/scip_engine.py:120`
`def installed(draw):`; matrix transfer: `tools/exp/bnc/scip_engine.py:51`
`def instance_of(h, loc: dict) -> inst_io.Inst:`.

**Growing the assignment restriction (#142 phase 2).** Previously the cluster stopped at
its last standard uncapped window $W_0$. Now, only after that complete window is proved
infeasible, try up to $N$ strict supersets, each of size at most $C$. Defaults are $N=3$
for SCIP and $N=0$ for HiGHS; $C=2500$. These are search caps, not an M1 tolerance.
Let $J(W)$ be owners in or adjacent to $W$, and $T$ the districts adjacent to any territory
of $J(W)$ but not in $J(W)$. First add free ZIPs owned by $T$, choosing the nearest by
hops through free ZIPs (then ZIP id; unreachable last) if the whole ring exceeds $C$.
Then inspect every ball/corridor proposed at cap $C$ in order. Accept its union with the
current window exactly when the union strictly grows and fits; a candidate need not itself
be larger than the current window. Skip an over-cap union and continue to later candidates.
Only accepted unions consume the $N$-step budget (the adjacent-ring step included).

Precisely, let $V_1$ be the trimmed adjacent ring, followed by the ordered ball/corridor
candidates $V_2,\ldots,V_q$. Start $U_0=W_0$, $k_0=0$ and set

$$
(U_i,k_i)=
\begin{cases}
(U_{i-1}\cup V_i,k_{i-1}+1),&
 k_{i-1}<N\ \land\ |U_{i-1}|<|U_{i-1}\cup V_i|\le C,\\
(U_{i-1},k_{i-1}),&\text{otherwise}.
\end{cases}
$$

The accepted windows satisfy
$W_0\subsetneq W_1\subsetneq\cdots\subsetneq W_k$, $k\le N$ and $|W_i|\le C$.
This is a search-domain recurrence, not a change to any fixed-window MILP row.

Each new window tries the split/holder cap first, then without it if infeasible. A solved
step ends the sequence; an unknown ends growth immediately, including before an uncapped
retry. Only a proved uncapped infeasibility advances to the next larger window. Parallel
workers may solve later steps speculatively, but settle in this order. Neck-window searches
do not grow. Entries: `tools/exp/contig/repair.py:614`
`def proved_infeasible(new: list, last: tuple) -> bool:` and `tools/exp/contig/repair.py:627`
`def grow_windows(pieces: list, owner: dict, W: set, free: set, adj: dict, h0: int,`.

The relation to F0 remains a **window assignment restriction inside a heuristic**. Define
$\mathcal R(W)=\{x:x_{zj}=\bar x_{zj}\ (z\notin W)\}$. Then
$W\subseteq W'\Rightarrow\mathcal R(W)\subseteq\mathcal R(W')$: every old assignment still
fixes the smaller outside set (**proved**). This enlarges the assignment search domain,
not an F0 certificate. Rebuilt bodies, lists, cap rows, callback exemptions and normalized
objective coefficients are conditional on each window; no monotonic local optimum or
infeasibility implication from $W$ to $W'$ is asserted.

**Repair counts/objective.** Let $h_v$ be the number of fixed holders, $Y_v^+$ its candidate
new-holder columns and $s_v\in\{0,1\}$ the split indicator. Fix $s_v=1$ if $h_v\ge2$;
otherwise impose

$$
 h_v+\sum_{j\in Y_v^+}y_{vj}\le1+|Y_v^+|s_v.
$$

Minimize $1000(|Y|+1)\sum_v s_v$ plus F4's holder, border and moment terms (repair does
not pass the land term). With the cap on, let $S_0=\sum_v[|\bar H_v|>1]$ and
$Q_0=\sum_v|\bar H_v|-\sum_vh_v$ over window units. For all window units $V_W$ impose

$$
\sum_{v\in V_W}s_v\le S_0+|O|,\qquad
\sum_{v\in V_W}\sum_{j\in Y_v^+}y_{vj}\le Q_0+|O|,
$$

where $O$ is the set of opened units. If $O\ne\varnothing$, repeat the inequalities on
$V_W\setminus O$ with right sides $S_0,Q_0$, and individually bound each opened unit's
new holders by $|\bar H_v|+1-h_v$. With no opened unit this caps **aggregate** splits and
holders (hence aggregate cuts), not each unit's count. A cap-infeasible attempt is retried
without the cap; no unconditional “repair never adds splits” guarantee follows.

**Certificate.** With valid default neck rows, an infeasibility proof is for the fixed
window, lists, cap setting and band. `optimal` is a numerical optimum of that local
cut-augmented model, not a map optimum. Existing necked districts not being repaired are
exempt from its callback, and remote outside pieces need not be connected by this solve.
A local connected return therefore does not certify all M1 constraints; the full gate is
required. Unknown or DAG-only failure is never an infeasibility certificate.

**Small-instance specification and checks.** `td/formulation/f4w.py:22`
`def build_model(data):` adds the named $V_W,O,h,s,S_0,Q_0$ and cap components to F4's
independent flow model; it rejects DAG/neck callbacks rather than silently omitting them.
`tests/test_formulation_repair.py` checks three nested windows on 60 vertices against
both production engines through `repair.solve_window` (relative gap zero), including optimal
values and chosen feasible and infeasible assignments. The tests independently prescribe the
window, fixed owners, bodies, bands and holder caps and check the group the production adapter builds. Separate checks exercise binding caps, opened units, the
adjacent ring, wider steps, both caps and the infeasible/unknown growth gate in sequential
and raced settlement. `td/formulation/f4w.py:75`
`def growth_sequence(W, candidates, *, limit, cap):` specifies the displayed recurrence.
The 60-vertex growth checks compare the entire accepted sequence, including a smaller
candidate whose union grows and an over-cap candidate followed by one that fits. These
are numerical checks, not a national performance claim.

### 4.4 F4.N / F4.S — default no-good and opt-in strong neck rows

**F4.N relation to F0: exact exclusion of a nonexempt neck-failing ownership set within the
fixed window**, not a stand-alone solver for F0. The #142 default is a no-good, not a
width inequality. For a proved neck of district $j$ at incumbent set $D$, put $X=D\cap W$:

$$
\sum_{z\in X}(1-x_{zj})+\sum_{z\in W\setminus X}x_{zj}\ge1.
$$

**Validity proof:** outside $W$ is fixed; keeping the same $X$ keeps the entire district,
its own P-graph, its land and its width graph unchanged. The zero-opportunity relay set
depends on channel masses, not other districts' owners. The same nonexempt neck remains.
Thus the row excludes no current-M1-feasible completion. The callback uses the raw gate,
which does not implement the Manhattan exception: exception-bearing sets require the
explicit F0 exception record before this is an F0-valid cut. No main-map blanket exemption
is inferred. An unresolved check supplies no proof and no no-good row.

Entry: `tools/exp/contig/repair.py:312`
`def neck_cuts(c: str, owner: dict, W: set, m: dict, ng, own: dict, check, rows: str | None = None) -> tuple:`;
encoding: `tools/exp/contig/necks_gate.py:92` `def nogood_terms(D: set, W: set) -> tuple:`.
It uses one binary $t$ with
$\sum_{z\in W\setminus X}x_{zj}\ge t$ and
$t+\sum_{z\in X}(1-x_{zj})\ge1$. These two rows are equivalent to the no-good after
eliminating $t$. Full implementation details and B's use are retained in §3.6.9.

**F4.S relation to F0: heuristic, unproven restriction**, never a necessary-condition
certificate. `--neck-rows strong` / `TD_NECK_ROWS=strong` opts in; default is off. For anchors
$Q$, fixed land $A^F$, optional land $a_z$, share $\alpha$, and minimum anchor land $a_*$,
the encoded rows use $B=a_*-\alpha A^F>0$, $t\in\{0,1\}$ and continuous pair variables:

$$
\begin{aligned}
0\le u_{zw}&\le x_{zj},&u_{zw}&\le x_{wj},\\
C+\sum_z k_zx_{zj}+\sum_{zw}k_{zw}u_{zw}&\ge W't,\\
\alpha\left(A^F+\sum_z a_zx_{zj}\right)-a_*
&\ge-B\left(t+\sum_{z\in Q}(1-x_{zj})\right).
\end{aligned}
$$

Coefficients come from `cut_terms`' gate widths, including relay and width-only edges;
$W'$ is 10 km less half a cm. In particular, matching the gate's edge data alone does **not**
prove the connected-side/anchor hypotheses under changing ownership. Repeated versions
excluded gate-feasible drawings; the latest finite random searches are evidence, not a
proof. **Certificate:** only the strong-row model's own bound/infeasibility, never absence
of an M1 completion. Entry: `tools/exp/contig/necks_gate.py:117`
`def cut_terms(nk, D: set, fixed: set, W: set, seed: set, ng, zero, states: frozenset,`.

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
(§3.2, §3.6.6).

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

### Claim 2 (F2.delta: smallest δ; U31)

For the fixed whole/clipped symmetric-band master, the objective is $\min\delta$ with
$\delta\ge0$. Multi-unit/whole choices and clipped-singleton choices, respectively, have

$$
\delta\ge\frac{|M(S)-\tau_c|+\mu_S}{\tau_c}n_S,\qquad
\delta\ge\frac{|M_v/k-\tau_c|+\mu_{\{v\}}}{\tau_c}z_{v,k}.
$$

The sets, other rows and conditional certificate are F2's. This is exact for that
restricted master, heuristic relative to F0. Entry: `td/master.py:469`
`def exact_delta(inst, channel: str, fam=None, time_limit: float | None = None,`.
With a window, it instead reports feasibility once; there is no delta to optimize.

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
- By the Corollary of §3.6.7, the master's smallest δ with μ ≡ 0 is at most the smallest δ at which a
  connected drawing in 𝒳_c exists.
- By Corollary 3, a plan feasible with μ_S draws, before repair, with every mass in its band
  [L_c, U_c], and strictly inside it when μ_S > 0. Connectivity is not implied.

The price of clipping, U35, is reported as a property of the master.

### Claim 3 (rounding; U33)

For a splittable unit v shared by the copies J_v (|J_v| ≥ 2), the realizer solves the transport LP
(§7, step 2):

$$
\min_{f\ge0}\sum_{z\in Z_v,j\in J_v}m_z\lVert p_z-c_j\rVert^2f_{zj}
\quad\text{subject to}\quad
\sum_jf_{zj}=1\ (z\in Z_v),\qquad
\sum_zm_zf_{zj}=a_{v,j}\ (j\in J_v).
$$

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
copy holds alone there is no error, so the sum may run over the units actually split, as §3.6.6
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
  smallest-δ search (`docs/archive/memory/decisions/open-decisions-2026-09-28.md`, OD5).
- **Rurality caps (U36).** R_c(u, v) = base_c · g(r_u, r_v). Here r_v ∈ [0, 1] is v's rurality,
  built from its 2025 urban-area share and its counties' metro status (S19). The schedule g is
  symmetric, g ≥ 1, and nondecreasing in each argument, so caps loosen with rurality. g ≡ 1 when
  the option is off. Any such R_c keeps 𝒮_c closed (§2) **[proved]**. The schedule itself, the
  formula for r_v and the values of g are open **[claimed U36: B/E, D1 (#73)]**.

The state-level context is from the v2 whole instance at δ = 5% on the pre-2025 graph: every state
except CA, TX, NY and FL fits whole in one district (`docs/archive/memory/facts/state-border-snapping.md`,
2026-09-07). It is not re-measured on the fresh extract **[claimed U35]**.

## 7. F7 — the realizer (S21)

**Relation to F0: heuristic.** Data are a decoded F2 plan, fixed centers, unit ZIPs and
masses; the transport variables/constraints/objective are the LP in §5 Claim 3. It optimizes
squared distance subject to planned continuous targets, not P/N or F0's objective.
Tree rounding turns that LP into an assignment, followed by local repair, swap and territory
ownership; those passes have no global minimization certificate. Entry:
`td/realize.py:273` `def realize(inst, plan, xy: dict) -> Drawing:`;
LP entry: `td/realize.py:155` `def transport(zs, m: dict, p: dict, c: dict, a: dict) -> dict:`;
territory entry: `td/territory.py:117`
`def own_territory(inst, plan, d, xy: dict, state: dict) -> dict:`.

**Certificate and numerical domain.** Claim 3 is an exact-vertex theorem before repair:
$|\sum_{z:\lambda(z)=j}m_z-a_{v,j}|<m_j^*$ when $j$ touches a split ZIP, else error zero.
The implementation normalizes positive masses by their mean $\bar m$, excludes
$T=\{z:0<m_z<10^{-6}\bar m\}$ from transport, and subtracts $m(T)$ from the last implied
target. It filters flows below $10^{-9}m_z$, checks conservation numerically and requires
a forest. The omitted positive ZIPs are placed by adjacency with zero ZIPs and keep their
mass. Thus neither the exact pre-repair margin guarantee nor the power-cell theorem is an
unqualified floating-point implementation certificate. Those theorems still hold under
their exact LP hypotheses; omitted mass and numerical residuals must be accounted for
separately, and the drawn ledger's bands/M1 decide final feasibility. Code:
`td/realize.py:161` `    tiny = [z for z in zs if m[z] < FLOW_TOL * scale]`;
`td/realize.py:292`
`        owner.update(place_zero([z for z in units.zips[v] if z not in own], own, units.zip_adj, p, c))`.

Whole units need no realizer. If every unit is connected on the ZIP graph, a district made only of
units it holds whole is P-connected, not necessarily neck-free **[proved]**: each unit is connected, its support is connected in
G, and adjacent units in G share a ZIP edge.
C2 checks every unit after pieces and metros are carved (C11). On a caller's own graph (a
fixture's) a disconnected `whole` unit stops the run, naming the unit and its components
**[policy OQ6]**. On the polygon graph it is listed in `disconnected_whole` and the run goes on
**[policy #114]**: an M1 district can hold such a unit whole when its other units reach every
piece of it, which the master does not enforce, and the M1 audit (§9) fails a district that
does not. Historically, before #114's second connector approval on 2026-10-05,
seven states were not connected within on the polygon graph with the then-approved connectors: CA, NV, NY, TN, UT, VA and WY, eleven detached groups; one in-state
connector per group was proposed by `python -m td geo --state-connectors`; proposed rows
added no edge until approved. #114 approved those rows, so this is not a statement that
today's seven states remain disconnected (`PROBLEM.md`, M1 second connector review). A district's part of a unit
need not be connected: pieces are reported with their cause, and S28 still applies
**[policy OQ6]**.

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
     position. C4 must place them; they change no mass but can change contiguity, shape and
     territory-based state incidence.
   - For the exact LP before repair, every ZIP with m_z > 0 lies in the convex power cell of
     the district that transport and tree rounding give it to **[proved]**. The implementation
     qualification above excludes omitted sub-tolerance ZIPs and numerical residuals. By LP duality, f_{zj} > 0 with m_z > 0
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
   - both new masses lie between the old pair's masses, so a common final band is preserved,
     asymmetric windows included. Proof: for fixed pair sum $s$, write $a+b=s$; then
     $\max(|a-\tau_c|,|b-\tau_c|)=|s/2-\tau_c|+|a-b|/2$.
     Strict improvement shrinks $|a-b|$ while leaving the midpoint fixed. This strengthens
     the older symmetric-band-only proof; it does not assert that the pass cures an initial
     band breach;
   - the pass ends: each move lowers the districts' deviations, sorted from the worst,
     lexicographically, and there are finitely many maps.

   The pass optimises deviation from τ_c and ignores the plan: a move can raise or lower the target
   error Δ_{v,j}, so Claim 3 and Corollary 3 bound the map before repair and the swap pass, not
   after. How close a pair gets is open **[claimed U45]**.

6. **The territory pass** (#116, `td/territory.py`), after the swap pass. Channel c's
   *footprint* is every ZIP of the instance in a unit of its domain D_c, the units dropped for zero
   opportunity included. The instance holds every CONUS ZCTA on the polygon graph (#114) and the
   domains partition V × F, so every (CONUS ZCTA, fine channel) lies in exactly one channel's
   footprint **[proved]**. The pass gives every footprint ZIP an owner, on the instance's ZIP
   graph **[policy M1, #116]**:
   - the ZIPs with m_z > 0 keep the realizer's owners; every ZIP of the footprint with m_z = 0 is
     released;
   - *grow*: breadth first from the owned ZIPs, a released ZIP takes the owner of the ZIP it is
     reached from, first only across edges inside one unit, then inside one state, then across a
     state line. A ZIP held by a district with no opportunity in its state splits that state
     (owner, 2026-10-05) and is listed in `run.json`;
   - a ZIP no edge reaches takes the owner of the nearest owned ZIP and stays a detached piece, so
     M1 fails on it; it is listed, never patched;
   - *join*: a district in pieces takes a shortest path of zero-mass ZIPs, inside the units where
     it holds opportunity, from one piece to another of its ZIPs, whoever holds the path, when the
     total pieces of the district and of the districts it takes ZIPs from fall and none of those
     districts is left in more pieces. No district is emptied.

   Then **[proved]**: no ZIP of positive mass changes owner, so drawn masses, bands, drawn shares
   and Δ are the realizer's; a grown ZIP joins the component of the ZIP it was reached from, so
   growth adds no piece to the components of the ZIPs with opportunity; each join lowers the total
   piece count, so the pass ends; and a path stays inside units its district holds opportunity in,
   so the join adds no owner to a unit (C16). Growth across a unit can, and the audit lists it
   (§9). The pieces reported after the pass are its own.

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

## 8. F8 — the ledger (S25, S26)

**Relation to F0: heuristic pipeline output**, an exact read-back of the produced owners,
not an optimization stage. For a solved channel, its assignment is
$\lambda(z,f)=(\rho(z,f),\operatorname{owner}_{\rho(z,f)}(z))$ and its drawn dollar mass is
$D_j=\sum_{(z,f):\lambda(z,f)=j}r_fm_{zf}$. There is no objective or independent solver
certificate. The rows below define the ledger's representation; F9 checks it. The legacy
blank rows for a dropped channel are not an F0 coverage certificate. Entry:
`td/output.py:333` `def ledger(inst, drawings: dict, extract, reference) -> list:`.

The ledger's rules are policies **[policy S25, S26]**, except where a bullet is tagged.

- The ledger has one row per (ZIP, fine channel) cell of the extract and one per cell of the
  scenario's fine channels at every other ZIP of the instance, at zero opportunity with the reason
  `no cell in the extract: territory at zero opportunity` (#116). So each channel's rows cover its
  footprint (§7 step 6), and, the instance holding every CONUS ZCTA (#114), every CONUS ZCTA has
  one row per fine channel.
- A cell's owner is the district that its channel's realizer and territory pass gave the cell's ZIP
  to. The domains partition the cells, so each cell of the footprint of a channel solved has
  exactly one owner, who holds all of its opportunity **[proved]**. A cell of a unit dropped for zero opportunity (§1) keeps the reason `dropped: zero
  opportunity` with the territory pass's owner. A cell of a channel dropped for zero opportunity
  has no owner, since the channel has no districts; it keeps its row with the district blank and
  that reason.
- The master's shares are targets and are never read as masses after the realizer.
- A district's drawn share of a unit is the opportunity of its ZIPs in the unit divided by the
  unit's opportunity, defined when M_v > 0, as it is for every unit in V_c (§1).
- Planned shares appear only in the run's diagnostics, beside the drawn ones, as Δ.
- Reported shares, masses and bands come from the ledger, and maps are drawn only from it.

## 9. F9 — the audit

**Relation to F0: heuristic pipeline certification boundary**, not a solver of its
objective. The mathematical checks are coverage, counts, drawn bands and per-district
P/N from F0, plus the scenario's stage-specific modes/policies. Entry:
`td/audit.py:1229` `def audit(run: Run) -> list:`; M1 entry is cited in [F0.tex](F0.tex), “Implementation boundary”. There is no map
objective in this stage; the neck search minimizes cut width subject to a connected own
side and the 5%–50% area range. **Certificate:** only the supplied ledger, graph, channel
masses, routing and numerical checks. The raw gate does not apply the authorized Manhattan
exception, and dropped-channel blanks in the legacy audit are not full F0 coverage.
The run-folder gate delegates routing to the source audit:
`tools/looks/score.py:406`
`                                    polygon=g.polygon, fine=None if fine is None else tuple(fine)),`.
A reported M1 pass therefore needs that matching source audit and immutable scenario/mass
inputs for a routing claim. A neck timeout is an unresolved failure of certification,
not a mathematical neck witness. Gap-width monotonicity holds for mathematical witnesses,
not necessarily the time-limited statuses or the particular witness the search selects.

One `scorecard.md` per run, in the run directory. Each check is a policy of #52 §4, with its
source where one is named **[policy S28, OD1, OD3, C16]**:
- one owner per cell of the footprints of the channels solved; a row the extract has no cell for
  passes only at zero opportunity with the reason `no cell in the extract` or `dropped: zero
  opportunity` (#116);
- the district count equals K_c for each channel solved;
- the cells of units and channels dropped for zero opportunity (§1) are listed with the reason
  `dropped: zero opportunity`, and do not fail the run: a dropped unit's cell is owned by the
  territory pass in a channel solved, and a dropped channel's cell has a blank district;
- final bands on the drawn masses, with every breach listed against the final tolerance
  **[policy OD1]**. A breach caused by a share that could not be drawn fails the run and names the
  unit and district **[policy S28]**;
- planned against drawn owners per unit, the owners of its cells with opportunity, since the
  modes split opportunity (#116):
  - a planned share drawn as no ZIPs is listed (C8);
  - a whole unit with more than one owner is a hard failure;
  - an extra owner from repair in a free unit is listed;
  - an owner outside a clipped unit is a mode violation and fails the run (C16);
- ZIP contiguity on the declared graph, with a verdict for any ZIP not in the graph. Pieces are
  listed with their cause and their share of the district's mass. A run on the extract declares
  the polygon graph it planned on (#114), so these pieces are M1's (#116);
- M1, ZIP contiguity on the drawn map **[policy M1, `PROBLEM.md` ## Mandates; #108]**: in
  every channel, each district's ZCTAs in the ledger are one component of the polygon graph (the
  rook graph of the 2025 TIGER ZCTA polygons over every CONUS ZCTA, an edge only for a shared
  boundary of positive length, plus the owner-approved connectors across gaps), and every CONUS
  ZCTA has an owner in every channel that holds it. A channel holds its footprint (§7 step 6): every
  (ZCTA, fine channel) cell of the scenario's F that the domains give it. Each cell has a row in
  that planning channel and exactly one owned row, no gap, no double and no row elsewhere; two
  districts of one channel owning one ZCTA fail too. F and the cell's planning channel come from
  the scenario, never from the ledger; the run-folder gate, which has no units, reads F from
  `run.json` and leaves the routing to the run's own audit, which the looks scorer also requires
  to pass. Coverage is counted per footprint, not
  over all CONUS in each planning channel, because the ledger is keyed (ZIP, fine channel) and
  the owner's domain partition (WIFI's region in the 51 and NE + plains layouts) is settled frame
  (orchestrator decision under the owner's autonomy grant, 2026-10-05, #116, for owner review). A
  dropped channel's blank rows are excused: it has no districts. A blank row in a solved channel
  is never excused, and no row excuses a double. **A detached piece fails the
  map**, and so does a ZCTA with no owner or no row; no tolerance, and listing a piece is not
  enough. The audit's piece list is the one piece count: `run.json`, `districts.csv` and the looks
  scorer count the same pieces, and no display fill sizes them (#116). Each piece is listed with its ZIP count, its mass
  over τ_c and its cause. A run without the polygon graph leaves M1 unverified, never passed;
  a run on the extract always has it. The looks scorer makes an M1 failure ineligible. A
  multipart ZCTA is one vertex; a drawn piece only it makes is a looks defect, not an M1
  failure (owner, 2026-10-05);
- **M1's neck passage widths (owner, 2026-10-14; `td.audit.NeckGraph`, `district_necks`,
  `check_m1`)** **[policy #131; owner's words, "(a) Any water crossing. A neck or detached piece
  passes if its narrow passage is an approved water connector (bridge, tunnel or ferry)... Narrow
  land necks (Cincinnati, El Paso, Utah) would still fail", "(a) except we should treat necks that
  are surrounded by empty or zero-opportunity zips the same way we treat water", "keep the
  manhattan exception and in general those water split cases are ok"]**. The 5% land share and the
  10 km threshold are unchanged; three rules set a passage's width:
  - R1: every approved connector (bridge, tunnel, ferry, a road across land in no ZCTA, an island's
    `nearest` row) is unlimited, always. The rule before (a connector 0 km wide where land within
    the district's states would do through 10 km, `NeckGraph.land_would_do`) is the opt-in
    `NeckGraph(pre_2026_10_14_land_rule=True)` / `TD_NECK_PRE_2026_10_14_LAND_RULE=1`.
  - R2: land in no ZCTA counts (G1, `NeckGraph(gap_width=True)`, the default); opt out with
    `gap_width=False` / `TD_NECK_GAP_WIDTH=0`. The width source is the one the maps have been gated
    with since G1 (owner, 2026-10-08, #131; accepted for widths): the land-only rows of
    `polygon["gaps"]` when present, else the Voronoi `dropped` rows (`polygon["voronoi_gaps"]` or
    `zcta_polygon_vs_voronoi.csv.gz`), which carry no land or water marker and can cross water.
    Neck width only: the pieces check (R5) never reads the Voronoi rows.
  - R3: ZCTAs of zero opportunity in the district's planning channel count, whoever owns them.
    `check_m1` finds them as the ZCTAs all of whose rows in that channel have m = 0 (a ZCTA with
    no row in the channel, or a ledger with no opportunity, has none). `district_necks(free=)`
    adds those that reach the district through free ZCTAs alone as relay vertices of the width
    graph, with the same edge widths, no land area and no mass: a cut may put a relay on either
    side, so a passage through them is as wide as its narrowest link. A ZCTA of positive
    opportunity that another district owns is never a relay. The cut-off part is connected on the
    district's own ZCTAs (polygon edges, connectors, R5 gap edges), never through a relay: three
    2% fringes that touch only through a relay are no 6% neck. The detached-piece check is not
    changed by R3 (a district joined only through empty land is still in pieces).
  - R5 (owner, 2026-10-14, #140): the pieces check reads the land-only gap edges too
    (`audit.adjacency(gaps=True)`, `geo.polygon_graph()["gaps"]`): two ZCTAs of one state that face
    each other across land in no ZCTA are adjacent, never across water (the Voronoi rows, which can
    cross water, only widen necks, never join pieces), behind G1's switch. `reference/2025/zcta_gap_land.csv.gz` is not
    shipped yet, so R5 is inactive on the real graph and `check_m1` says so.
  Since #142 the checks that run before the gate read this model: `repair.py`, `plancheck.py`,
  `wholeplan.py` and `glue.py` call `tools/exp/contig/necks_gate.py` (`gate_graph`, `gate_necks`
  with the channel's zero-opportunity ZCTAs from `channel_mass`, `edge_km`, `nogood_terms`,
  `cut_terms`, `bridged`), which wraps `audit.district_necks(free=)`, `audit.neck_relays` and
  `audit.neck_widths`, so §3.6.9's widths are M1's again, and the default `repair.neck_cuts` row, the
  no-good of a district's drawing of the window, is valid under the relays and the #140 connector
  rule (§3.6.9). For example, the review's C14 has $X=\{a,b\}$, equal land, a 1 km
  own edge and a zero-opportunity relay $r$ with two 20 km edges. The gate's cut costs
  $1+\min(20,20)=21$ km, not 1 km; omitting $r$ falsely rejects $X$. The regression is
  `tests/test_neck_gate_parity.py:92`
  `def test_a_zero_opportunity_relay_owned_elsewhere_is_accepted_by_every_check_c14():`.
  The master side (`td.supports.contact`)
  still reads the pre-2026-10-14 land rule (§2 contact): it drops a connector that land
  replaces, so its rows can reject a drawing M1 now accepts (a plan it accepts is still accepted
  by M1's connector rule; a follow-up, not changed here);
- mode compliance on the owners of cells with opportunity, with the metro exceptions listed
  (S14); a zero-opportunity ZCTA the territory pass gave to a district holding no opportunity in
  its unit is listed, not failed (#116; a state crossing is a split, owner 2026-10-05);
- the geography manifest is all 2025 (S17);
- the solver's status, bound and gap;
- one name per district;
- the certificate tier: exact, bounded or feasible only **[policy OD3]**.

### 9.1 F9.I — IFA index acceptance of fixed gate evidence

**Relation to F0: heuristic certification boundary**, not an optimizer or an independent
routing/mass audit. The index runs the gate fresh, records its actual neck/piece sides,
and excepts an item only if it is a proved neck or detached piece whose side intersects
$H=\{z:\operatorname{primaryCounty}(z)=36061\}$. This replaces the district-name waiver;
it does not change the raw F9 gate. Entry:
`tools/exp/contig/ifa_index_night.py:171`
`def m1_verdict(status: str, summary: str, items: list, sides: dict, manhattan, diagnostic=None) -> dict:`.
Unresolved necks, coverage/ownership items, unverified status, diagnostics and unexplained
failure block acceptance. Informational mass-neck items are ignored. The sealed and warm
drivers (§11.3) take the same adjudication from evidence recorded in the gate stage's own
child process (`ifa_index_night.py --gate`), never from audit hooks installed in the driver's
threads.

For this section and the fixed-evidence certificates F11.G/R/W and F142.P, let $P$ be the
named predicates below, with supplied truth values $q_p\in\{0,1\}$. A small specification
uses $a\in\{0,1\}$ and

$$
a\le q_p\quad(p\in P),\qquad a\ge\sum_{p\in P}q_p-|P|+1.
$$

Its test objective is $\max a$, **not a territory objective**. These rows force exactly the
conjunction (if any $q_p=0$, $a=0$; otherwise the lower row forces $a=1$), a direct proof.
The spec only checks acceptance of supplied evidence; it does not prove that the gate has
found every neck. Entry: `td/formulation/certificates.py:12`
`def build_model(formulation, predicates):`. Each builder returns its own named model.

F9.I's predicates are verified status, nondiagnostic input, explained failure, admissibility
of every noninformational item, matching mass provenance, and every district's window. With
current mass $m_j$ (the folder's ledger joined to the full extract), fixed IFA rate
$r=1.2519681558$ million dollars per mass unit, and recorded window flag $w_j$, the
implemented window predicate is exact in real dollars:

$$
10^9\le 10^6rm_j\le1.4375\,10^9,
\qquad w_j\notin\{\text{under},\text{over}\}.
$$

Entry: `tools/exp/contig/ifa_index_night.py:199`
`        usd = v["m_rel"] * RATE * 1e6`.
There is no rounding: a sub-dollar breach (for example \$999,999,999.75) is under the floor.
The index does not trust `run.json`'s saved mass: `current_masses` sums the extract's $m_{zf}$
over the ledger's cells $(z,f)$ of each district, `checked_districts` raises when the district
sets differ or a saved mass $\bar m_j$ fails
$|\bar m_j-m_j|\le\max(10^{-12},10^{-9}\max(|\bar m_j|,|m_j|))$, and a
ledger cell with no extract mass raises, with one convention: a ledger row whose reason is
`NO_CELL` (a footprint cell the extract lacks, territory at zero opportunity,
`output.ledger`) and whose `m_rel` is 0 adds mass 0 to its district, so a district of such
territory keeps its place in the district set. A `NO_CELL` row with opportunity, or whose
cell the extract does hold, raises like any other unexplained omission. A ZIP's duplicate
extract cells are summed, as the ledger does. This tolerance compares saved and recomputed
mass, not the dollar window. Entry: `tools/exp/contig/ifa_index_night.py:248`
`    off = sorted(j for j in saved if not math.isclose(saved[j]["m_rel"], now[j], rel_tol=MASS_RTOL, abs_tol=1e-12))`.
The predicate "matching mass provenance" is that check passing; a stale in-window
`run.json` cannot keep a pass after a material ownership change. The cell-level specification
`td/formulation/certificates.py:46`
`def ifa_ledger_model(*, owned_cells, extract_mass, saved, no_cell=(), **gate):`
independently sums the same ledger cells and checks this predicate. Its 30-vertex production conformance covers a connected boundary transfer,
updated totals, missing extract cells/districts, summation roundoff, zero-mass `NO_CELL`
territory (accepted) and a `NO_CELL` row with mass or in the extract (refused).
No numerical tolerance is added to F0 here.
`tests/test_formulation_certificates.py` numerically checks the spec against the production
gate/side recorder and verdict on 30-vertex maps, including Manhattan and non-Manhattan
pieces, coverage failure, unresolved necks, diagnostics and window breaches. It compares
the acceptance optimum at relative gap zero and both fixed acceptance-point verdicts.

## 10. Where each council item lands

| item | here |
|---|---|
| C2, C19: closure and the National filter | §2 |
| C3: Claim 1(iii) is conditional; η and μ_S are policies | §5 Claim 1, §3.2, §3.6.6 |
| C4: the smallest δ is a property of the master | §5 Claim 2 |
| C5: the scope of Claim 3 | §5 Claim 3 |
| C6: the corridor floor | §3.6.2, Proposition D |
| C7: the border cap | §3.6.3, Proposition D |
| C8: the count cap is conditional | §3.6.4 |
| C9: the Menger row | §3.6.5 |
| C10: clipped mode and connectivity | §5 C10 |
| C11: every unit must be ZIP-connected | §7 |
| C16: the mode guard on repair | §7 step 4, §9 |

## 11. F11 — glue, warm start and sealed assembly

### 11.1 F11.G — zero-opportunity glue

**Relation to F0: heuristic**, with invariant dollar masses, not a substitute P-connectivity
rule. Data are an existing owner map $\bar\lambda$, own-adjacency graph, channel masses and
the gate's static zero set. For a detached component of district $j$, search a shortest
P-path $Q$ to its other owned ZCTAs through zero-opportunity ZCTAs owned by other districts.
The trial assignment is

$$
\lambda'(z)=\begin{cases}j&z\in Q,\\\bar\lambda(z)&z\notin Q,\end{cases}
\qquad m_z=0\ (z\in Q),\qquad D'_k=D_k\ (\text{every }k).
$$

Reject if a donor empties, its detached components cannot be injectively matched to
containing pre-move components, its post-move neck check is unresolved, or its **returned
neck witness sets** fail the analogous containment test. Require fewer recipient components and no increase in its returned neck
count. These predicates define the search; there is no optimization objective or optimality
certificate. A positive-mass ownership change raises an error. Entry:
`tools/exp/contig/glue.py:110`
`def glue_channel(owner: dict, adj: dict, mass: dict, necks_of, tries: int = TRIES,`;
`tools/exp/contig/glue.py:188` `    positive = sorted(z for z in moved if mass.get(z, 0.0) != 0.0)`.

**Certificate.** Zero-only movement preserves dollar masses by the displayed equality.
Piece containment has an injective witness. Neck-witness containment is **not** a theorem
that every possible neck is preserved: the checker returns selected witnesses, not the
entire forbidden-cut family. A clean donor is checked clean again; for an already-failing
donor, “no new or enlarged neck” remains stronger than what this witness comparison proves.
Unknown neck checks are not clean: their status now survives witness conversion and any
unresolved post-move donor check vetoes the path, even if its set matches an old witness.
The recipient still uses returned neck **counts**, not a resolved-status requirement;
accepting a path therefore does not certify recipient M1. The final full gate is required.
For the fixed-candidate F11.G spec, $P$ comprises zero path mass, nonempty donors, donor
piece/witness containment, resolved donors, fewer recipient pieces and nonincreasing
recipient neck count. The conjunction in §9.1 specifies this acceptance, not the path
search or an all-neck theorem. The 30-vertex conformance case executes `glue_channel`
with clean and unresolved donor evidence and with R5 gap edges on/off, checking unchanged
dollar mass and both acceptance points.

The historical §18 branch review correctly found missing relays and opt-in gap reading in
old glue. #142 replaces that with the gate's graph and zero set:
`tools/exp/contig/glue.py:214` `    ng = necks_gate.gate_graph(polygon)` and
`tools/exp/contig/glue.py:215`
`    return (lambda zs: [frozenset(n.zips) if n.status == "proved" else UnresolvedNeck(n.zips)`.
Piece/path adjacency now also follows the gate's R5 switch:
`tools/exp/contig/glue.py:203`
`def gate_adjacency(polygon: dict, gap_width: bool | None = None) -> dict:`.
These fix input/status mismatches, not the all-witness guarantee.

### 11.2 F11.W — warm-start chain and provenance

**Relation to F0: heuristic.** Start from a completed first drawing, including F7 fallback
owners where F4 did not draw; then apply local repair, glue, assembly and the full gate:

$$
\lambda^0\ \xrightarrow{\ F4.W\ }\ \lambda^1
\ \xrightarrow{\ F4.W\ \text{if needed}\ }\ \lambda^2
\ \xrightarrow{\ F11.G\ }\ \lambda^3
\ \xrightarrow{\ \text{assemble/audit}\ }\ \lambda.
$$

There are no new global variables, feasibility rows or optimization objective beyond the
stages invoked. **Certificate:** a passing final ledger is gate-verified with its matching
source routing audit and fixed mass inputs. It has no global optimality certificate and
is not “fully exact drawn” just because the inherited master tier is `exact`.
Entry: `tools/exp/contig/warm.py:141` `def cmd_point(a) -> int:`.
Repair/glue now read the source region's cut extract if present, rather than the full
extract's outside-channel cells; final scoring uses the full dollar extract (§11.3).
Entry: `tools/exp/contig/warm.py:103`
`def source_extract(main_dir: str, pid: str, run_name: str, full: str) -> str:`.
F11.W's acceptance specification is F11.R's conjunction below, since it invokes the same
driver, including the Manhattan item-side exception (§11.3).
`final_undrawn` reads the source count, not final ZIP-by-ZIP provenance:
`tools/exp/contig/warm.py:116`
`    return {c: v["undrawn_zctas"] for c, v in sorted(ch.items()) if v.get("undrawn_zctas")}`.
The label “N ZCTAs placed by the realizer heuristic, not the exact draw” is therefore an
inherited source-undrawn count (an upper bound on still-heuristic placements), not a
measurement that N current owners escaped subsequent exact local repair. Units whose
attempt never began may be absent from the per-group list even though they enter N.

### 11.3 F11.R — regional restrictions and cellwise assembly

**Relation to F0: restriction for pure sealing; heuristic for the implemented pipeline.**
Given a per-channel regional partition $Z_c=\dot\bigcup_r Z_{cr}$, sealing asks for
$X_{cj}\subseteq Z_{cr}$ for one region $r$ and fixes regional K with
$\sum_r K_{cr}=K_c$. This implies unsealed feasibility **only when** physical dollar
windows, support families, modes, $\eta$, margins, caps, bans and geography are unchanged,
and each regional support belongs to the national family. Equal relative bands around
different regional means do not satisfy that premise. The implemented driver changes
parameters and uses F2/F4/repair; it has no national optimum certificate.

Entry: `tools/exp/contig/sealed.py:392`
`def region_plan(sp, states, ks: dict, cells: dict, rule: str, window_band: bool = False,`.
Independent channel partitions are supported; equal-or-disjoint state sets are **not**
a driver requirement. When they are not aligned, combine cells using their designated
channel/state source:

$$
\lambda(z,f)=\operatorname{rename}_{r}\bigl(\lambda_r(z,f)\bigr),
\qquad r=\operatorname{source}(\rho(z,f),s(z)).
$$

Entry: `tools/exp/contig/sealed.py:667`
`def combine_point(runs: list, folders: dict, out: str, spec_path: str, extract_path: str) -> dict:`.
`merge.py` alone still requires ZIP-disjoint sources. The strict driver accepts group
statuses `optimal`/`connected`; its label “no connected drawing” also covers unknown/time
limits and is not an infeasibility proof. The historical sealed runs did not test sealing
with window bands; blaming symmetric bands alone was an inference, not a controlled result.
Optional hard shape-limit files are experimental restrictions, not F0 mandates.

**Final label certificate (F11.R/W).** A pass requires a completed exact gate, M1 acceptance,
every district's dollar window, scorer eligibility, and no hard-shape breach. M1 acceptance
is the raw pass (gate exit 0) or, for a gate that exited 1, the shared item-side adjudication
of §9.1 (`manhattan_verdict` applies `m1_verdict` to the status, items and neck/piece sides
that the gate stage's own child process wrote, `ifa_index_night.py --gate`, beside the point's
`merged` folder; the file names its folder and exit code and the merge deletes a stale one):
every item must be a proved neck or detached piece whose side holds a primary-county-36061
ZCTA, and an unresolved neck, any other item, an unverified status, a diagnostic folder or
missing, unreadable or mismatched evidence still vetoes. These are $P$ in §9.1's
conjunction. Missing gate completion (no exit code, or a code other than 0 or 1) is failure,
not success; a saved passing `m1.json` cannot override a nonzero exit. Entry:
`tools/exp/contig/sealed.py:958`
`def label_point(m1: dict, rows: list, breaches: list, hard: bool, eligible: bool = True, why=(),`.

**Eligibility after the adjudication.** The looks scorer adds its own raw-M1 reason
(`M1: fail, ...`) to `score.txt`'s eligibility. The adjudication replaces that one veto and
no other: after a gate that exited 1 and passed the adjudication, `scorer_eligibility` drops
the scorer's `M1:` reasons (not `M1: not checked`); any remaining reason, a reason-less
`eligible: no`, or a gate that did not exit 1 keeps the point `ineligible`. So the labels
and F9.I accept the same Manhattan-excepted maps unless another eligibility rule fails.
Entry: `tools/exp/contig/sealed.py:947`
`def scorer_eligibility(eligible: bool, why, verdict: dict | None, gate_rc: int | None) -> tuple:`;
the spec `td/formulation/certificates.py:78`
`def assembly_model(*, gate_rc, m1_pass, windows, eligible, hard, breaches, warm=False, manhattan_pass=False,`
states it independently from the scorer's reasons.

**Windows are exact.** The label's windows are judged on unrounded dollars: each district's
$D_j=\sum_{(z,f):\lambda(z,f)=j}r_fm_{zf}$ with the full dollar extract's cell masses
$m_{zf}$ (a ledger cell the extract lacks raises, except the zero-mass `NO_CELL`
territory above) and its whole-extract rates $r_f$, against the applicable bounds with the
edges in: $L\le D_j\le U$, where $U$ is the window ceiling, or the whole-state cap for a
district owning whole states alone (`score.dollar_gate`'s structure). A sub-dollar breach
such as \$849,999,999.75 against the \$850M WH floor is outside. Entry:
`tools/exp/contig/sealed.py:917` `        inside = lo is not None and lo <= x <= hi`.
`tools/looks/score.py:337`
`        inside = lo is not None and round(lo) <= round(x) <= round(hi)`
still rounds both sides to whole dollars (the scorer's `dollars.csv`, `score.txt` and its own
window eligibility reasons); that is scorer behavior, which can only accept more than the
exact comparison, and it decides nothing in the label. Entry for the scoring command:
`tools/exp/contig/sealed.py:617` `def score_cmd(folder: str, extract: str) -> list:`
(the full extract, not the CONUS-cut merged extract, so $r_f$ is whole-extract).

The sealed cut extracts carry no sales data
(`state_extract.strip_sales`); `merge.py`'s merged extracts and `dollarize.py`'s dollar
extracts are written by other modules and are not covered here.
The 30-vertex conformance test calls the production dollar window and label function,
including a district below its floor by less than a dollar, missing/nonzero gate exits, a
Manhattan-only failed gate that stays eligible and one that keeps another eligibility
reason, and checks the full-extract argument in the production command chain.

For arithmetic screening only, a channel without conditional caps needs

$$
\left\lceil\frac{M_c}{U_c}\right\rceil\le K_c\le
\left\lfloor\frac{M_c}{L_c}\right\rfloor.
$$

For footprint components $i$, analogous integers require $k_i\ge1$, $\sum_i k_i=K_c$ and
$k_iL_c\le M_i\le k_iU_c$. These are necessary, not sufficient; components must include
zero-opportunity connecting territory and use the actual graph and physical window.
Dropping zero-mass units can create artificial components. WIFI's conditional 1600 cap
requires F0's ownership logic, not substitution of 1600 for every upper bound. The
legacy symmetric `fit_delta` rounds downward; for $K>1$ it can reject small positive
headroom, and its $K=1$ special case need not return an interval contained in the window.

## 12. F142 — branch-and-cut comparison arms (#142 phase 0)

The phase-0 comparison was originally read on **`m5-studio/bnc` at `ae0b1b7`**;
`tools/exp/bnc/` is now present in this checkout. The historical experiment exports a
stripped group model. Phase 2 additionally reuses its SCIP handler on F4.W's full window
matrix (§4.3); that does not strip window-specific rows or change their certificate domain.

### 12.1 Common conditional model and certificates

**Relation to F0: heuristic overall**, for the same mixed restriction/relaxation reasons
as F4. With fixed exported bodies/lists/band, it is an **exact P-connectivity subproblem**,
and a **relaxation of that same window's M1 problem** because N is omitted. Never use its
bound as a national F0 bound. Variables, base rows and scalar objective are F4's, exported
column-for-column; neck and repair count/cap rows are stripped, while sequential `extra`
and residual-band semantics are retained if present in the source call. Code on `m5-studio/bnc`:
`tools/exp/bnc/capture.py:241`
`    kw = dict(extra=snap["extra"], dag=False, start=None, count=None, layers=False, flow=False,`.
The round-trip reconstructs those base columns/rows/objective, not an F0 formulation.
Width data is exported but does not add N-constraints.

For district $j$, let $\Gamma_j$ contain its allowed free ZIPs and fixed-body vertices;
$x^j_v=1$ at bodies. Every vertex separator $S\subseteq V(\Gamma_j)\setminus\{a,b\}$
between $a,b$ gives

$$
x^j_a+x^j_b-\sum_{s\in S}x^j_s\le1.
$$

**Proof:** any selected $a$–$b$ path crosses $S$; a disconnected selected pair has a
separator of unselected vertices and violates the row. Thus the full finite family
characterizes connectivity of selected sets. Minimality strengthens a row, not its
validity. Entry on `m5-studio/bnc`: `tools/exp/bnc/sepcuts.py:102`
`    def row(self, j: str, a: str, b: str, sep) -> Row:`. Integer separation uses a
component's boundary reduced from each endpoint's side; optional fractional separation
uses vertex-capacity max flow and checks the resulting inequality numerically.

**Pyomo specification:** `td.formulation.f142:build_model` shares the F4 base rows and
objective, with named separator sets $S$ and the displayed inequalities; no branch-only
module is imported. Because the full family is exponential, the builder returns its base
relaxation and `td.formulation.f142:separate` materializes violated integer rows using
component boundaries in $\Gamma_j$. A solve is certified only after an optimal integer
solution has no violated separator; an intermediate relaxation's optimal objective is
merely a lower bound on this fixed conditional group. Every failed round removes that integer assignment,
so exact unlimited separation terminates and agrees with the finite-family formulation.
The five F4 conformance instances compare its optimum and point verdicts with both the
independent-flow F4 spec and production F4 (the mathematical model of arm a). An extra
locally feasible disconnected point exercises nonempty separator generation; ordinary
neighbor rows alone accept it. Those original checks do not execute the SCIP handler.
The additional `tests/test_formulation_repair.py` checks execute that handler through the
production window adapter and compare it with the independent F4.W flow specification;
its feasible and infeasible point verdicts agree on the tested 60-vertex instances.
Entries: `td/formulation/f142.py:17` `def build_model(data):` and
`td/formulation/f142.py:28` `def separate(M, *, tolerance=1e-6):`.

**Certificate domain for every arm:** `optimal` is numerical connected optimality of the
exported model (relative gap 0, absolute gap $10^{-6}$); `feasible` is a connected incumbent;
`infeasible` is absence of a connected assignment under the exported restrictions;
`unknown` and `not usable` give no feasibility conclusion. N, full actual dollar masses,
coverage and routing still require the full audit chain. A sequential export's `extra`
can differ from actual mass elsewhere on the map. The post-solve gate substitutes group
owners into the full source ledger with full-graph relays; its group verdict can exclude
proved pre-existing failures outside the group, while `map_m1` remains the raw whole-map
verdict. A group pass is not automatically a whole-map pass.

**F142.P — campaign provenance acceptance.** Relation to F0: heuristic evidence filter,
not an optimization formulation or a new connectedness proof. A result is now admitted
only with a nonempty source-content fingerprint matching the newest campaign result,
as well as matching commit/dirty flag/limits/threads, same-arm settings and an available
instance file with its recorded hash. These five predicates are $P$ in §9.1's specification;
its sole variable/objective is the test acceptance bit. Entry:
`tools/exp/bnc/report.py:91` `def split(out: str, instances: str | None = None) -> tuple:`.
The source hash includes sorted relative paths and file hashes of the configured source
globs, not timestamps or just Git status. Entry:
`tools/exp/bnc/export.py:125` `def source_fingerprint(root: str = ROOT) -> str:`.
This certifies recorded source/instance identity, not geography/extract identity or absence
of edits during a solve. Independent checks likewise require a source hash, matching the
tabled campaign when one exists. Historical records without it are now excluded, including
the older table entries quoted below; those quotes remain historical, not a rerun of the
current admission filter. The conformance test compares the acceptance optimum and both
fixed points with production `report.split` for missing, changed and matching hashes.

### 12.2 F142.a–d and independent flow verification

Each working arm solves §12.1, with the same objective. The relation/certificate above
applies to each; the implementations differ in how they enforce the same P requirement.

- **F142.a (complete F4):** `dag=False`, optional body-root flow on by default, layer
  separators and F4's outer cut loop. Entry on `m5-studio/bnc`, `tools/exp/bnc/arms.py:67`:
  `def arm_a(inst, time_limit: float, threads: int, log=print, flow: bool = True,`.
  It alone receives the constructed start; its initial absolute gap is F4's 0.05. These
  differences matter for timing comparisons even though the conditional feasible set agrees.
- **F142.b (HiGHS outer loop):** solve the base MILP, separate violated integer rows of
  §12.1, re-solve. Entry on `m5-studio/bnc`, `tools/exp/bnc/arms.py:107`:
  `def arm_b(inst, time_limit: float, threads: int, log=print, max_per_component=None) -> dict:`.
  No compact flow rows. Finite termination without limits follows because every failed
  round excludes its integer assignment; this is not a polynomial guarantee.
- **F142.c (SCIP lazy rows):** enforce the same separator family in the constraint handler;
  `--frac-root` optionally adds fractional root cuts. Entry on `m5-studio/bnc`, `tools/exp/bnc/arms.py:186`:
  `def arm_c(inst, time_limit: float, threads: int, log=print, frac_root: bool = False,`.
  SCIP's handler checks returned integer owners for disconnection. One thread in this build.
  Phase 2 factors this into `tools/exp/bnc/arms.py:192`
  `def scip_solve(inst, time_limit: float, log=print, frac_root: bool = False,`.
  Its optional full-column start does not alter the feasible set. In F4.W the caller supplies
  the current full matrix, so the same separator family enforces P connectivity alongside
  window caps and outer neck cuts; its certificate is F4.W's, not the stripped export's.
- **F142.d (probe only):** no working optimization formulation/backend. The intended model
  is §12.1 but the highspy lazy callback is never invoked in the 20-node probe; status is
  `not usable`. If the probe ever reports usable, the current function raises
  `NotImplementedError`, rather than silently solving without connectivity. Entry
  at `tools/exp/bnc/arms.py:313`:
  `def probe_highs_lazy(log=print) -> dict:`. It picks four vertices of a 20-node path at
  minimum cost with cheap disconnected endpoints, so a working callback must exclude that
  assignment. It is a capability test, not a fourth successful solve.

**F142.V (independent flow encoding):** same base model/objective, no handler or separator
rows. For each district route one unit to every selected non-root vertex, with both-end
arc capacities $f^j_{uv}\le n_jx^j_u,n_jx^j_v$. Bodies provide a fixed root; otherwise
choose $\sum_v r^j_v=1$, $r^j_v\le x^j_v$ and impose

$$
\sum_u f^j_{uv}-\sum_w f^j_{vw}\ge x^j_v-n_j r^j_v.
$$

The spanning-tree/rootless-component proof is F0's **when every rootless district is
required to select a vertex**. Entry on `m5-studio/bnc`, `tools/exp/bnc/verify.py:34`:
`def flow_model(inst, log=print):`. **Phase-2 conformance finding:** the unconditional
root row at `tools/exp/bnc/verify.py:51` `            model.addCons(quicksum(rv.values()) == 1)`
excludes an empty rootless district. F4/F142 separators permit it when `extra` already
meets the residual lower bound. A 30-vertex fixed-point check of that root-row restriction
now executes production arm a, `verify.flow_model` and `verify.run` and reproduces the
difference, including sequential overweight-extra semantics: `tests/test_formulation.py:426`
`def test_formulation_rootless_empty_extra_and_sequential_domain():`. Thus this verifier's
infeasibility/optimum is a certificate for the **additional nonempty-rootless restriction**;
it is a common-model certificate only when nonemptiness is implied by the base rows
(e.g. positive residual lower mass for each rootless district). It is independent of
separator-code validity, not of the common exported data. No production code is changed.

### 12.3 Phase-0 result: FI_NY window infeasibility, not F0 infeasibility

The [#142 phase-0 record](https://github.com/helios1168/td/issues/142#issuecomment-6199916342)
reports **FI_NY infeasible by three methods**: HiGHS integer separators (6141 s), SCIP lazy
separators (84 s), and SCIP flow without cuts (522 s). The domain is the `ne-50-bal`
warm-repair window: **223 free ZCTAs, five FI districts, allowed owners fixed, everything
outside fixed, \$765–1035M**. Because P plus that window is a relaxation of M1 under those
same restrictions, an M1 completion there is also impossible. This says nothing about
F0, a larger window, different allowed districts, another K or another routing structure.

**Evidence qualification.** These are read saved results, not new solves in this document
change. The current campaign report admits the two separator proofs:
`runs/exp/bnc_2026-10-15/REPORT.md:23`
`| FI_NY | b | infeasible | 6140.9 | - | 121378 | - | - | - |` and line 24
`| FI_NY | c | infeasible | 83.7 | - | 4490 | - | - | - |` (hub, gitignored).
The third record, `runs/exp/bnc_2026-10-15/FI_NY/verify_flow_scip.json`, says
`"scip_status": "infeasible"`, but lacks code/instance hashes. Consequently the current
report excludes it from campaign-attested checks at line 69:
`- FI_NY/verify_flow_scip.json: no code commit recorded; no instance sha256 recorded`.
The issue's three-method result is retained with that provenance limitation, not upgraded
to three equally attested campaign certificates.

For the other groups no arm found a connected drawing **by search** in two hours at one
thread: FI_FL and WIFI_MD were unknown; FI_PA arm a retained its constructed start
(feasible, 5.27% gap, passes full-map M1 and window), not an optimum. Evidence:
`runs/exp/bnc_2026-10-15/REPORT.md:52`
`- FI_PA arm a: time limit: the constructed drawing stands`.
Arm d was unusable on all four. The #142 record notes simultaneous runs and substantial
host load, so absolute timings are not a clean unloaded-machine benchmark.

## 13. Review reconciliation and remaining owner inputs

The two historical notes were read on `m5-studio/national-approaches`; their review status
and §18 branch checks are incorporated above, not reissued as new decisions. In particular:

1. **Reference versus implementation/older policy prose.** `PROBLEM.md` retains the older
   national lower window, mean-based WIFI band, land-would-do connector rule, positive-mass
   split wording and splits-first ordering. F0 follows the approved review program and
   the later #112/#134/#140 record, while §§3–12 describe code. The scorer still ranks
   splits first (`tools/looks/score.py:550`
   `    return (s["splits"], s["defects"], s["largest_extent_km"], s["states_per_district"], s["worst_dev"],`).
   No `PROBLEM.md` edit is made. Manhattan is not implemented in the raw gate; the IFA index and
   the sealed/warm labels apply the same item-side exceptions, never an all-district waiver. F0's numerical shape/balance functions remain owner inputs, and
   the Manhattan-neck identification needs owner confirmation; [F0.tex](F0.tex) states the
   supervisor's reading explicitly. The detached-piece ruling of 2026-10-15 is encoded in
   the F0 spec, not in the production gate.
2. **Conditional proofs versus national certificates.** Aggregation is lossless for
   continuous explicit-copy plans only (§5 Claim 1), not for indivisible ZIP geography.
   F2's policies, margins and bans qualify its bounds (§3.6.7); F4's complete model is
   distinct from DAG and sequential (§4.2). A master `exact` tier does not certify exact
   drawing (§11.2). The source comment that 1000 outweighs shape is false when the 900 land
   term is also on (§4.1); its “heaviest” root-body comment actually selects largest ZIP
   count. Fixed planned shares do not force fixed drawn shares. The seven disconnected-state
   claim was historical, before #114's connector approvals (§7), not today's graph.
3. **Neck parity and certificate limits.** Historical C14/C15 failures had three causes:
   old connector widths, missing zero relays and missing width-only edges. #142 addresses
   all three in repair, plancheck, wholeplan and glue; default no-goods are valid by locality.
   Strong rows remain opt-in/unproven (the blanket validity wording in the header of
   `tests/test_neck_gate_parity.py` and `draw._solve_group`'s docstring is not a proof for
   strong mode); glue still compares selected witnesses (§§3.6.9,
   4.4, 11.1). `td.supports.contact` still explicitly calls the old rule:
   `td/supports.py:128`
   `                if b in ng.connector.get(a, ()) and not ng.land_would_do(a, b, states[u] | states[v]):`.
   It is a family restriction, not an M1-equivalent test. The run-folder gate delegates
   routing to the matching source audit (§9), rather than certifying it by itself.
4. **Numerical and band claims.** Transport omits sub-tolerance positive masses (§7), so
   exact-vertex power-cell/rounding theorems are not blanket implementation certificates.
   Swap preserves asymmetric windows too, by the fixed-pair-sum proof (§7). `--window`
   intersects existing repair bounds; cap rows are aggregate and can be retried without
   caps (§4.3). The window master still has margins and bans. Arithmetic headroom is not
   feasibility; a zero-unit-deleted component graph is not automatically a valid bound
   (§11.3). MIP absolute gaps and start slacks are numerical parameters, not policy tolerances.
5. **Branch/result corrections.** `sealed.py` supports independent channel partitions via
   cellwise `combined/`, unlike `merge.py` alone. Historical sealed-with-window runs were
   not established by §18; sealing's symmetric-band diagnosis stays an inference. Warm
   source-undrawn counts are not exact final provenance. The review falsified the claim
   that national Florida's \$1004.1M was the whole state: it was a district's part in
   `ne-cmp-tierP`, whereas its cited whole-state result in `ne-48-bal` was \$1370.399M
   (historical review C20, not recomputed here). Neither is a structural F0 requirement.
   #142 now tests unrestricted arms (§12), without retroactively changing the DAG-only
   provenance of the earlier timeouts. The third FI_NY flow record's missing hashes remain
   an evidence limitation, not a reason to infer national infeasibility.

**F0 boundary:** the 2026-10-15 owner ruling on Manhattan detached pieces is incorporated
in [F0.tex](F0.tex); the neck identification is flagged there for confirmation. Choosing $\Phi_{\rm shape}$, $\Phi_{\rm balance}$ or expanding
the Manhattan exception would change or instantiate owner inputs and requires an owner
record. Coarsening, rule C, finite column libraries, eta/free lists and regional sealing
remain explicit restrictions/heuristics; none is silently made part of F0.
