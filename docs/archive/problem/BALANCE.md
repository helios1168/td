# The balance problem: a brief for the lens and the council

Draft, 2026-10-01. Input to a Gromov lens pass and a council; nothing here is settled until
triage moves it into `PROBLEM.md` or `UNKNOWNS.md`. Measured on the fresh extract
(`instance_descaled.json.gz`, format /3) on m5 at `main` f98b9a3, unless marked otherwise. τ_c is
a planning channel's target district size, and a district's **deviation** is m_j / τ_c − 1; §2.2
lists the model's symbols.

## 1. The question

The owner's priority (2026-10-01): **every district's drawn opportunity should be as close to its
channel's target as possible.** How should td produce that, starting with the 51 scenario? Other
combinations and merges of channels are allowed if they are needed. Maps for stakeholders are due
2026-10-02, so the answer has a near-term part (what to show tomorrow) and a durable part (what
the model should become).

## 2. The problem and today's model

This section is laid out the way districting papers state a model: the problem in words (§2.1),
the notation (§2.2), the problem posed (§2.3), the program with each labelled row explained
(§2.4–2.6), and what is proved (§2.7). It restates `docs/MODEL.md` as td `main` runs it, in
MODEL's notation; MODEL has the proofs.

### 2.1 The problem in words

- **Opportunity.** Descaled opportunity `m_rel` per (ZIP, fine channel) cell; no sales or rep data
  is used. The ground set is the 2025 ZCTAs in the 48 contiguous states and DC; ZIPs without a
  ZCTA (PO box, unique, military) are excluded (owner, #63).
- **The 51 scenario** (`scenarios/51_total_13n_11wh_24fi_3wifi.toml`) plans five fine channels,
  national_chase, wells_wh, wells_fi, wh and fi, in four planning channels:

  | planning channel | K | domain |
  |---|---|---|
  | national | 13 | the 41 non-WIFI states × {national_chase, wells_wh, wells_fi} |
  | WH | 11 | the 41 states × wh |
  | FI | 24 | the 41 states × fi |
  | WIFI | 3 | the 8 western states (CO, ID, MT, ND, NE, NM, SD, WY) × all five |

  The five other fine channels in the extract (ifa, career, edj, imo, priafs) are independent
  planning channels, each planned in its own scenario (owner, #76); IFA has one, `50_ifa.toml`.
- **A district** is a set of whole ZIPs in one planning channel. Contiguity is judged on a rook
  graph of Voronoi cells around 2025 ZCTA points, not on the drawn ZCTA polygons.
- **Rules the scenario carries**, ported from the legacy catalog and all policy: states are kept
  whole unless they are on a free list; a district spans at most 6 states, within distance caps
  (900 km, with overrides for large western states); New England pairs only with itself and NY,
  FL stands alone, MS stays apart from the southeast; CA hosts at most 4 districts; a district
  takes no sliver below η = 0.05 of a state; WIFI is exactly the three fixed blocks
  {ND, SD, NE}, {ID, MT, WY} and {CO, NM}.
- **The national fallback** is decided per state. A state on national's list keeps all three
  national fine channels in national; a state off it sends national_chase and wells_fi with FI and
  wells_wh with WH. In the 51 every non-WIFI state is on the list, so the fallback acts only
  inside WIFI.
- **Channels interact only through the scenario**: which cells go to which planning channel (the
  WIFI region, the fallback) and the total headcount, Σ K_c = 51. Each planning channel is
  otherwise solved on its own.

### 2.2 Notation

One planning channel c at a time. Where the channel is clear its subscript is dropped (m_z, M_v),
as in MODEL. The 51 column lists national, WH, FI and WIFI, in that order. Some territory-design
papers write τ for the tolerance and μ for the target; here τ_c is the target, δ_c the tolerance
and μ_S the margin.

**Sets and graphs**

| symbol | meaning | in the 51 | code |
|---|---|---|---|
| z ∈ Z | a ZIP: a 2025 ZCTA in the 48 states or DC, with a 2025 point and positive opportunity in some fine channel of the scenario | 6,623 | `inst.units.unit_of` |
| f ∈ F | a fine channel of the scenario | the five in §2.1 | `fine_channels` |
| v ∈ V; u(z); Z_v | a unit (a state; DC is one); the unit of ZIP z; the ZIPs of v | 49 units | `inst.units.zips` |
| c; D_c ⊆ V × F | a planning channel; its domain. The D_c partition V × F | §2.1's table | `[channels.*]` |
| V_c | the units of D_c with M_v > 0; any other unit is dropped and reported | 41, 41, 41, 8; none dropped | `ch.units` |
| G_Z = (Z, E_Z); G_v | the ZIP graph (OD2): two ZIPs are adjacent when their Voronoi cells, built around the ZCTA points and clipped to each state, share a border. G_v is its subgraph on Z_v | 19,458 edges | `geo.zip_graph` |
| G = (V, E); N(v) | the unit graph: two units are adjacent when a G_Z edge joins them. N(v) is v's neighbours | | `inst.units.unit_adj` |
| 𝒮_c ∋ S | the support family (§2.4). A support is a set of units that one district may draw from | 1,472, 1,931, 1,931, 16 | `supports.family` |
| j = (S, r) | a district: the r-th of the n_S districts on support S | | `master.Copy` |
| J_v | the districts with a positive planned share of v | | |
| 𝒳_c(δ) | the connected drawings whose footprints lie in 𝒮_c and whose drawn masses lie in τ_c[1 − δ, 1 + δ], and that obey η_c, the modes and the caps (MODEL §4.1) | | |

**Data**

| symbol | meaning | in the 51 | code |
|---|---|---|---|
| M_{z,f} ≥ 0 | the descaled opportunity of cell (z, f) | 11,721 cells | `m_rel` |
| p_z | ZIP z's 2025 Gazetteer internal point, in EPSG:5070 (equal-area), km | | `xy` |
| K_c | the number of districts | 13, 11, 24, 3; Σ 51 | `k` |
| δ_c | the planning band's half-width, relative to τ_c | 0.10, 0.10, 0.10, 1.0 | `delta` |
| δ^fin_c ≥ δ_c | the final tolerance's half-width (OD1) | equal to δ_c | `final_delta` |
| η_c | the least share a district takes of each unit of its support | 0.05 | `eta` |
| mode_c(v) | whole (one owner), clipped (split only among districts inside v) or free (split among any supports) | free: 12, 16, 17, 0 units; the rest whole | `mode`, `free` |
| s̄_c | the support size cap | 6 | `max_size` |
| R_c(u, v) | the distance cap, max(R̄_c, ρ_u, ρ_v): a base cap and the two units' own caps (R̄ and ρ are this brief's symbols) | R̄ 900 km; ρ: WA and CA 1,600, TX 1,200, LA 1,150, AZ and UT 1,100, OR 1,000 | `max_dist_km`, `dist_km` |
| P_c | the forbidden pairs: no support holds both units of a pair (this brief's symbol) | national only: a New England unit with any unit outside New England and NY, FL with any unit, MS with AL, FL, GA or SC | `confine`, `forbid_pairs` |
| X_c | the listed supports, added with their connected subsets; WIFI's family is these alone | national: New England + NY; WIFI: {ND, SD, NE}, {ID, MT, WY}, {CO, NM} | `extra_supports` |
| cap_v | the contact cap: at most cap_v districts touch v (∞ if unset) | CA 4 (national, WH, FI) | `contact_caps` |

**Computed parameters**

| symbol | meaning | in the 51 | code |
|---|---|---|---|
| m_z | the mass of ZIP z in c: Σ M_{z,f} over the f with (u(z), f) ∈ D_c | 6,365 ZIPs in the 41 states, positive in 3,561, 1,330, 4,945; WIFI 258 of 258 | `ch.m` |
| M_v; M(S) | unit mass Σ_{z∈Z_v} m_z; support mass Σ_{v∈S} M_v | | `ch.M` |
| τ_c | the target, Σ_{v∈V_c} M_v / K_c | 1,070.5, 782.0, 658.3, 416.4 (m_rel units) | `ch.tau` |
| [L_c, U_c] | the planning band, τ_c[1 − δ_c, 1 + δ_c] | | `ch.band` |
| [L^fin_c, U^fin_c] | the final tolerance, τ_c[1 − δ^fin_c, 1 + δ^fin_c], which judges the drawn map | equal to [L_c, U_c] | `ch.final_band` |
| p_v; d(u, v) | a unit's centroid, the land-area-weighted mean of its ZIP points; the distance between two centroids, km | | `distance_km` |
| w_S | a support's weight: its diameter, max_{u,v∈S} d(u, v), km | | `supports.diameter` |
| μ_S | the rounding margin: the sum, over the splittable units v of S, of max_{z∈Z_v} m_z | up to 0.32τ, 0.40τ, 0.28τ; 0 in WIFI | `supports.margin` |
| c_v(S) | the corridor floor, for a cut vertex v of G[S]: the least mass of a path in G_v from the ZIPs bordering one side of v to those bordering the others, at the worst side; ∞ when there is no path | rows: 2,159, 3,142, 3,142, 1 | `supports.corridor_floor` |
| b_{uv} | the border count: the ZIPs of v with a G_Z edge into u | rows: 51, 80, 86, 0 | `supports.border_count` |

**Variables, and what the decoder and realizer make of them**

| symbol | meaning | in the 51 | code |
|---|---|---|---|
| n_S ∈ ℤ≥0 | the number of districts on support S | 1,472, 1,931, 1,931, 16 columns | `n_col` |
| t_{v,S} ∈ [0, 1] | the total share of v held by the districts on S | 6,772, 9,213, 9,213, 26 columns | `t_col` |
| ȳ_{v,j}; a_{v,j} | district j's planned share of v, t_{v,S}/n_S; its planned mass there, M_v ȳ_{v,j} | | `master.decode` |
| c_j | district j's centre in a split unit | | `realize.centres` |
| f_{zj} ∈ [0, 1]; x_{zj} | the fraction of ZIP z that the transport LP sends to district j; x_{zj} = m_z f_{zj} | | `realize.transport` |
| π_c(z) | the drawing: ZIP z's district. Every cell (z, f) of D_c is owned by π_c(z) | | `ledger.csv` |

**Measures**

| symbol | meaning | code |
|---|---|---|
| m_j | district j's drawn mass, Σ m_z over the z with π_c(z) = j | `districts.csv`, `drawn_mass` |
| dev_j | its deviation, m_j / τ_c − 1 | |
| Δ_{v,j} | the target error: j's drawn mass in v minus a_{v,j} | `realize.Drawing` |
| δ*_c | the smallest δ at which M_c(δ) is feasible: a property of the master, not of the map (C4) | `master.smallest_delta` |

### 2.3 The problem posed

For one planning channel c, a **map** π_c gives every ZIP of V_c one of K_c districts, and each
cell (z, f) of D_c goes with its ZIP. The owner's problem (§1), written the way districting
papers write theirs, is P_c: among the maps such that

1. every ZIP of V_c is in exactly one district;
2. there are K_c districts;
3. every district is connected in G_Z (what connected should mean for a sparse channel is BU13);
4. every district obeys the scenario's rules: its footprint, the units it touches, is in 𝒮_c,
   whole units keep one owner, it holds at least η_c of each unit it touches, and the contact
   caps hold (which of these are must-haves is BU2);

find one that minimises a balance loss ℓ(dev_1, …, dev_{K_c}), with compactness at most a
tie-break. ℓ is open (BU1): the worst |dev_j|, their mean, or the count outside ±x%. So is the
weight of compactness (BU11). The channels are coupled only through the scenario: the domains
D_c and Σ_c K_c = 51 (BU3, BU7).

Today's model answers a different question, in three stages: a master that minimises compactness
inside a band (§2.4), a realizer that draws the plan on ZIPs (§2.5), and an audit that judges the
map (§2.6).

### 2.4 Stage 1: the support master M_c(δ)

**The family.** 𝒮_c is the set of S ⊆ V_c with G[S] connected, |S| ≤ s̄_c, d(u, v) ≤ R_c(u, v)
for all u, v ∈ S, and no pair of P_c inside S, together with the listed supports X_c and their
connected subsets. It must be closed under connected subsets (MODEL §2), and the loader checks
that it is. WIFI's family is X_c and its connected subsets alone.

**The program.** One MILP per channel. Its columns are supports with a multiplicity, as in a
set-partitioning master, rather than assignments of units to centres. With L = τ_c(1 − δ) and
U = τ_c(1 + δ), so that L = L_c and U = U_c at δ = δ_c:

```
M_c(δ):  min   Σ_{S∈𝒮_c} w_S n_S                                                            (M0)
         s.t.  Σ_{S∈𝒮_c} n_S = K_c                                                          (M1)
               Σ_{S∋v} t_{v,S} = 1                       ∀ v ∈ V_c                          (M2)
               η_c n_S ≤ t_{v,S} ≤ n_S                   ∀ S ∈ 𝒮_c, v ∈ S                   (M3)
               (L + μ_S) n_S ≤ Σ_{v∈S} M_v t_{v,S}
                             ≤ (U − μ_S) n_S             ∀ S ∈ 𝒮_c                          (M4)
               t_{v,S} = n_S ≤ 1                         ∀ S ∈ 𝒮_c, v ∈ S held whole        (M5)
               Σ_{S∋v} n_S ≤ min(⌊1/η_c⌋, cap_v, |Z_v|)  ∀ v ∈ V_c                          (M6)
               M_v t_{v,S} ≥ c_v(S) n_S                  ∀ S ∈ 𝒮_c, v a cut vertex of G[S]  (M7)
               Σ_{S∋v : N(v)∩S={u}} n_S ≤ b_{uv}         ∀ v ∈ V_c free, u ∈ N(v)           (M8)
               n_S ∈ ℤ≥0,  t_{v,S} ∈ [0, 1]              ∀ S ∈ 𝒮_c, v ∈ S                   (M9)
```

A unit v is *held whole* in S when it is whole, or when it is clipped and |S| > 1.

- (M0) Compactness is the objective: the total diameter of the districts. Claims 1–3 hold for any
  weights w_S ≥ 0 that depend on S alone (MODEL §3.5).
- (M1) There are K_c districts.
- (M2) Every unit is shared out in full.
- (M3) A district on S holds at least η_c of every unit of S, so its footprint is exactly S
  (Claim 1), and a support with no districts holds nothing.
- (M4) The band, shrunk at each end by the rounding margin: each district's planned mass lies in
  [L + μ_S, U − μ_S]. With μ_S = 0 it is the plain band.
- (M5) A whole unit has one owner, and so does a clipped unit inside a multi-unit support, so a
  clipped unit can be split only among districts on {v}.
- (M6) At most ⌊1/η_c⌋ districts touch v (20 at η_c = 0.05; (M2) and (M3) imply it, and the code
  writes it out), at most cap_v where a contact cap is set, and at most |Z_v|, one ZIP each
  (policy C8).
- (M7) The corridor floor: a district that crosses v must hold enough of v to link v's sides
  (MODEL §4.2). c_v(S) = ∞ forces n_S = 0.
- (M8) The border cap: districts that enter a free v only from u need distinct border ZIPs
  (MODEL §4.3).
- (M9) n_S ≤ 1 when S holds a unit whole, and n_S ≤ K_c otherwise. MODEL §4.5's optional Menger
  row is not built.

A run solves M_c(δ_c) with HiGHS at `mip_rel_gap` = 0, one channel at a time, and reports the
certificate it earned: exact, bounded or feasible only (OD3). The **smallest δ** is
δ*_c = min{δ ≥ 0 : M_c(δ) is feasible}. A channel with no free unit gets it from one exact MILP;
a channel with free units gets it by bisection to 10⁻⁴, which is valid because the feasible set
grows with δ (Claim 2).

### 2.5 Stage 2: decoding and the realizer

**Decoding.** Each S with n_S ≥ 1 becomes the districts j = (S, 1), …, (S, n_S). District j's
planned share of v ∈ S is ȳ_{v,j} = t_{v,S}/n_S, and its planned mass there a_{v,j} = M_v ȳ_{v,j}.
A unit's shares must sum to 1 within 10⁻⁶, or the run stops; the residual goes onto the unit's
largest share, and the decoded plan is checked against every row again.

**Drawing.** A unit held whole goes to its one district. Each splittable unit v with |J_v| ≥ 2 is
divided in five steps (MODEL §7):

1. *Centres.* A district on a multi-unit support is centred on the mass-weighted centroid of its
   border in v, the ZIPs of v adjacent to the rest of S. The k districts on {v} take the centres
   of a deterministic, opportunity-weighted k-means of v's ZIPs. (A clipped unit uses k-means; the
   51 has none.)
2. *Transport.* Solve T_v, below, to a vertex, by dual simplex.
3. *Rounding.* At a vertex the split ZIPs and the districts form a forest, with at most
   |J_v| − 1 split ZIPs (Lemma 3a). Each split ZIP goes whole to one of its districts, walking
   each tree from a root, so that each district's error stays below the heaviest split ZIP it
   touches (Claim 3).
4. *Zero-mass ZIPs* take the district of a placed neighbour, by breadth-first search; any left
   over take the nearest centre.
5. *Repair,* one pass per channel. Each detached piece of a district moves to an adjacent district
   only if both stay in [L^fin_c, U^fin_c] and the receiver may own it under the units' modes
   (C16). The receiver whose mass ends closest to τ_c wins. Otherwise the piece stays and is
   reported with its cause.

```
T_v:  min   Σ_{z∈Z_v} Σ_{j∈J_v} m_z ‖p_z − c_j‖² f_{zj}                      (T0)
      s.t.  Σ_{j∈J_v} f_{zj} = 1                         ∀ z ∈ Z_v           (T1)
            Σ_{z∈Z_v} m_z f_{zj} = a_{v,j}               ∀ j ∈ J_v           (T2)
            f_{zj} ≥ 0                                   ∀ z ∈ Z_v, j ∈ J_v  (T3)
```

(T1) sends every ZIP out in full, and (T2) gives every district exactly its planned mass in v.
The output is the drawing π_c and the ledger, which gives each cell (z, f) of D_c the owner π_c(z).

### 2.6 Stage 3: the audit

The audit (MODEL §9) reads only the ledger. Its balance test is

```
L^fin_c ≤ m_j ≤ U^fin_c        for every district j of every channel c solved,
```

up to a slack of 10⁻⁹τ_c. Any breach fails the run, and every breach is listed. Among its other
checks, the audit fails a cell with no owner or two, a channel without K_c districts, a whole unit
with two owners, and an owner outside a clipped unit. It lists without failing: planned shares
drawn as no ZIP, repair's extra owners in free units, cells dropped for zero opportunity, and the
pieces of districts that are not connected in G_Z, each with its cause (shape, attachment,
corridor, tiny share, graph gap). It reports the solver's status, bound, gap and certificate tier.

### 2.7 What is proved, and what is not

MODEL §4.7 and §5 prove these, and #65 verified them.

- **Decoding (Claim 1).** Every feasible (n, t) decodes into K_c districts. Each district's
  footprint is exactly its support S, so it is connected in G, and its planned mass lies in
  [L + μ_S, U − μ_S]. Each whole unit has one owner.
- **Rounding (Claim 3, Corollary 3).** After steps 2 and 3, before repair, each district's drawn
  mass is within μ_S of its planned mass, and strictly within it when μ_S > 0. So a plan feasible
  for M_c(δ) draws inside [L, U]. That is all that μ_S buys.
- **The master as a bound (Proposition D and its corollary).** With μ ≡ 0, the read-back of every
  connected drawing in 𝒳_c(δ) is feasible for M_c(δ). So δ*_c computed without the margin is a
  lower bound on δ for every connected map that keeps the same supports and policy rows. With
  μ_S > 0 the master is a restriction, and it bounds nothing.
- **Smallest δ (Claim 2).** δ*_c is exact when the channel has no free unit. With free units it
  is bisected, and a step that times out without an incumbent is unknown, not infeasible.
- **Not guaranteed:** that a district's part of a split unit is connected (C10); that every
  planned share survives the drawing (the tiny-share cause); and anything about repair's moves
  beyond the final band, which repair checks itself. Without μ_S nothing keeps drawn masses in
  the band, and §3 measures how far they move.

In one line: P_c minimises a balance loss subject to the rules. M_c(δ) minimises compactness (M0)
subject to a band (M4), and the drawn map keeps that band only through Corollary 3, which needs
μ_S.

## 3. Where balance is lost

§2.4–2.6 state the model, and `docs/RUN_WALKTHROUGH.md` walks through a run of it. Balance is
lost in four places, all measured:

1. **The plan aims at the band's edge.** Compactness (M0) is the objective and balance only a
   constraint (M4), so planned masses sit at exactly ±δ.
2. **The rounding margin μ_S.** It reserves, at each end of the band (M4), the heaviest ZIP of every
   splittable state in a district's support; that guarantees the drawn map stays in the band
   (`MODEL.md` §4.6, Claim 3). It is conservative (the heaviest ZIP anywhere in the state, summed
   over states) and, with it, ±10% is infeasible. The smallest feasible δ, proved by the solver:

   | channel | K | with μ_S | without μ_S |
   |---|---|---|---|
   | national | 13 | 0.165 | 0.067 |
   | WH | 11 | 0.302 | 0.193 |
   | FI | 24 | 0.130 | 0.029 |
   | WIFI | 3 | 0.88 (declared band ±100%) | same |
   | IFA (`50_ifa.toml`) | 50 | 0.454 | 0.000 |

3. **Drawing drift.** Without μ_S, assigning whole ZIPs moved districts up to 8.8% of τ from plan
   in national, 12.2% in WH and 15.4% in FI. In the one full run without μ_S (national and FI at
   δ 0.10, WH at 0.20), 15 of 51 drawn districts landed outside their band: 7 national, 3 WH and
   5 FI. Drawn ranges: national −17.5% to +18.8%, WH −20.0% to +26.3%, FI −11.1% to +10.3%,
   WIFI −61% to +88%. In FI, one district's planned 23% share of GA was drawn as no ZIPs. That run
   was a local diagnostic with two workarounds, a bug each: the one cell below 10⁻⁶ (FI in ZIP
   13027, 1.6 × 10⁻⁸) was zeroed because the transport LP cannot see it, and the ZCTA polygons
   were read in batches because GDAL rejects one 6,623-ZIP filter.
4. **WH's geography.** The WIFI block cuts off AZ, CA, NV, OR, UT and WA, which hold 1.615 WH
   districts' worth at K = 11. One district there is 60% heavy or two are 19% light, whatever the
   free list. At K = 13 the island holds 1.909 and the rest 11.09, which fit. National (4.027 +
   8.973) and FI (3.086 + 20.914) happen to fit at their K.

**Not causes.** Each lever was loosened alone, with and without μ_S (`#73`, 2026-10-01):

| loosened | national | WH | FI |
|---|---|---|---|
| none | 0.165 / 0.067 | 0.302 / 0.193 | 0.130 / 0.029 |
| national rules off | 0.165 / 0.054 | – | – |
| CA contact cap off | same | same | same |
| max size 6 → 8 | same | same | same |
| no distance cap | 0.165 / 0.054 | same | same |
| η 0.05 → 0.02 | same | same | same |
| every state free | 0.207 / 0.067 | 0.366 / 0.193 | 0.142 / 0.029 |

Each cell is the smallest δ with / without μ_S. Making every state free worsens the version with
μ_S, because each newly splittable state adds its heaviest ZIP to the margin. The data is not a
cause either: the legacy v4 extract and today's are nearly identical for these five channels.

## 4. Benchmarks

- **The legacy 51 map** (pre-support pipeline, `archive/pre-support-2026-09`), scored on its own
  data, v4: national −15.7% to +12.5% (8 of 13 within ±10%), WH −27.0% to +22.3% (5 of 11), FI
  −21.7% to +22.4% (18 of 24), WIFI −60.5% to +87.6% (0 of 3): 31 of 51 within ±10%. It always
  produced a map because it never checked the final map against a band. It solved a state-level
  ±10% band with no margin at a 1–5% MIP gap, widened the band by 0.1τ at ZIP level, and then
  healed and routed without a balance guard. Its WH districts came from a nationwide run whose τ
  counted the western states.
- **The support master without μ_S**: the diagnostic run in §3.3.

## 5. Granularity: how close can a district get?

| | heaviest ZIP / τ | ZIPs above 5% τ | ZIPs above 2% τ | mass in ZIPs below 1% τ |
|---|---|---|---|---|
| national (41 states, K 13) | 0.130 | 7 | 92 | 56% |
| WH (41 states, K 11) | 0.217 | 31 | 156 | 21% |
| FI (41 states, K 24) | 0.103 | 14 | 198 | 48% |
| WIFI (8 states, K 3) | 0.198 | 9 | 44 | 18% |
| WH + FI merged (41 states, K 35) | 0.247 | 89 | 401 | 32% |
| national + WH merged (41 states, K 24) | 0.199 | 63 | 264 | 34% |
| all five merged (49 units, K 51) | 0.283 | 148 | 600 | 28% |
| IFA (49 units, K 50) | 0.359 | 145 | 578 | 29% |

- **Vague conjecture (E):** national and FI are mostly fine sand, so a drawing step that
  optimises balance should land their districts within about 1–2% of τ. WH should get close too,
  except where its geography forbids it.
- **Merging channels at the same total K makes ZIPs lumpier relative to τ, not finer,** because
  the channels peak in the same ZIPs. A merge can fix geography (no island) and add flexibility;
  it does not fix granularity.
- **IFA's heaviest ZIPs** (MI and PA at 0.36τ, NY at 0.28τ) are ordinary ZCTAs, 0.2 to 1.7 times
  the median IFA ZIP's land area. Whether their opportunity is territory opportunity or where
  business is booked (a head office, say) is open (BU12).

## 6. Approaches on the table

| # | approach | what changes | guarantee | effort |
|---|---|---|---|---|
| A1 | **Balance-first plan**: minimise the worst deviation (the smallest δ, already computed), then compactness among those plans | the master's objective | as today | small |
| A2 | **Balance the drawing by border swaps**: move ZIPs between neighbouring districts, keeping each contiguous, until sizes converge | a post-pass after the realizer | none; audited result | half a day as a script |
| A3 | **Exact rebalancing per split state**: whole states are exact, so all drift lives in split states; each is shared by 2–5 districts, so a small MIP per state (or coupled group) minimises the worst deviation, with contiguity | the realizer | optimal for the given plan | 1–2 days |
| A4 | **Heavy ZIPs into the plan ("big rocks first")**: ZIPs above ε·τ (ε ≈ 0.02) become master units, so μ_S reserves only the largest remaining ZIP | the master's units | Claim 3's, at near-zero cost | days; family size grows |
| A5 | **Choose the K split for balance**: keep Σ K = 51 and sweep each channel's K (national 11–15, WH 9–14, FI 20–28, WIFI 2–5) | the scenario | as the master's | about 1 h of compute |
| A6 | **Fix WH's island**: choose the WIFI region (a search over connected regions), raise WH's K to 13, or merge WH and FI on the west coast only | the scenario | – | 1–2 h for a search |
| A7 | **Merge channels where structure needs it**: WH + FI where WH is thin, or a per-ZIP national fallback | the planning channels | – | scenario work and business sign-off |
| A8 | **ZIP-first districting**: drop the state structure, split each channel's ZIPs with a capacity-constrained power diagram (the realizer's transport LP at national scale), then A2 or A3 | the whole first stage | near-exact; whole states and national rules lost | 1–2 days |
| A9 | **Share a heavy ZIP between two districts** | the ledger's grain | exact balance | small; one ZIP, two reps |

Every scenario solve takes seconds to minutes, and a drawing a few minutes. m5 (18 cores) and m2
(12 cores) run single-threaded solves in parallel, about 27 at a time.

## 7. Constraints and non-goals

- **Masked:** sales, rep names and firm names never enter the repo, an issue or anything online.
  Descaled opportunity and everything the model makes from it are not confidential (owner,
  2026-09-30).
- Runs must be deterministic and reproducible. A run that claims a certificate must earn it
  (OD1, OD3). A band the model did not meet is reported, never silently loosened.
- Staffing (rep assignment) is out of scope.
- **Non-goals:** changing the exporter or the source data, the five other fine channels beyond
  IFA, and any UI.

## 8. Unknowns

Numbered BU here; triage gives each a U-number or folds it into an existing one. Grades: **E**
settleable by computation, **B** needs a business answer, **T** needs a theorem.

| id | unknown | grade |
|---|---|---|
| BU1 | The balance metric: the worst district (minimax), mean absolute deviation, or the count within ±x%? And what tolerance do stakeholders expect? | B |
| BU2 | Which rules are must-haves: whole states where possible, the national rules, the distance caps, the support size, WIFI's fixed blocks? | B |
| BU3 | Is the headcount 13 / 11 / 24 / 3 fixed, or open within Σ K = 51? | B |
| BU4 | The national fallback: per state (today) or per ZIP by Chase? Per ZIP moves 38.3% of wells_wh and 38.6% of wells_fi out of national. | B |
| BU5 | How close can the drawing get to τ per channel under contiguity and the state structure (the ZIP-level floor)? | E |
| BU6 | The smallest δ as a function of K per channel, and the K split that minimises the worst channel | E |
| BU7 | If the WIFI region may move: the best region, and what it does to WH | E |
| BU8 | Does a balance objective (minimax, or a sum of absolute deviations over copies) keep Claims 1–3? Minimax is a δ variable; a sum needs per-copy masses, which Claim 1's decoding must carry. | T |
| BU9 | With heavy ZIPs promoted to master units (A4), does Claim 3 hold with μ = the heaviest remaining ZIP, and how fast does the support family grow? | T/E |
| BU10 | May a ZIP be shared between two districts? | B |
| BU11 | Is compactness still a goal, and how much stretch is acceptable for balance? | B |
| BU12 | Is the source opportunity complete and correctly placed? National has positive opportunity in only 2,500 of 10,981 ZIPs (national_chase); LA ZIPs 90043, 90254 and 90623 have none in either export, though the owner expects significant national there; IFA's heaviest ZIPs may be booking locations. | B |
| BU13 | What does contiguity mean for a sparse channel? WH has opportunity in 1,330 of the scenario's 6,623 ZIPs, so judged on the scenario's graph, 855 of the 872 audited "pieces" are separated only by ZIPs with no WH. Is a district the region it covers (every ZIP, zero-opportunity ZIPs included) or its set of opportunity ZIPs? | B/T |

## 9. What we want back

- **From the Gromov lens:** read this as a mathematician meeting the problem for the first time.
  What is the problem, in your own terms? What would you do with it, and what do you need to
  know first? Nothing above is a suggestion: the model, the approaches and the unknowns record
  where we have been, not where to look.
- **From the council:** a recommendation in two parts, with confidence and what would change it:
  (a) what to produce for the 2026-10-02 stakeholder maps, using only approaches that can be
  built and audited by then; (b) what the durable model should become. Evidence: this brief,
  `docs/MODEL.md` (§3, §4.6, §7, Claims 1–3), `docs/RUN_WALKTHROUGH.md`, both scenario files,
  `td/master.py`, `td/realize.py`, the comments on #73 and #74, and the local diagnostic run in
  `runs/51_nomargin_wh20/` (`scorecard.md`, `districts.csv`).
