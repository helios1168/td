# The split problem: a brief for the council

Draft, 2026-10-04 (#90). Input to the four-seat council and its verification (#91); nothing here
is settled until triage moves it into `PROBLEM.md` or `UNKNOWNS.md`. It restates `docs/MODEL.md`
in MODEL's notation; MODEL has the proofs. Citations are `path:line` on `main`; `archive:` means
`git show archive/pre-support-2026-09:<path>`. Papers are cited by key and result and listed in
`docs/REFERENCES.md`. Tags follow MODEL §0: **[proved]**, **[tested]**, **[claimed]**,
**[policy]**; a **[note]** is this brief's own observation, unverified, and is a claim for the
council to check.

## 1. The question

The owner ranks maps looks first (`docs/problem/PROBLEM.md:39`, 2026-10-04): every district inside
a plain ±15% band, then **fewest split units**, then visual defects, then shape, then balance.
Today's master minimises support diameter only, so it splits a free unit at no cost. **How should
the support master count split units and minimise them, exactly and with a certificate, without
losing what Claims 1–3 and Proposition D guarantee?** And which of the candidate layouts (§5) is
an exact method and which a heuristic?

**Under M1 (added 2026-10-05).** Since 2026-10-04 every district must be one connected piece on the
drawn ZCTA polygons, with no tolerance (M1, `docs/problem/PROBLEM.md` "The goal"). Today's maps all
fail it: the power diagram places a split state's share with no requirement to touch the rest of
its district. So every split count, floor and δ* in this brief is a unit-level result. Each is a
lower bound for a contiguous map, since a tighter constraint can only raise it, not a value a
contiguous map is known to reach. A formulation is useful only if it stays exact, or says what it
loses, once the realizer must draw each share connected to the rest of its district (SU9).

## 2. The problem

### 2.1 What is counted (owner, 2026-10-04)

For a planning channel c and a unit v ∈ V_c, let r_v be the number of districts whose ledger
holds positive opportunity in v. **v is split when r_v ≥ 2.** The rank-1 key is

  splits(map) = Σ_c #{v ∈ V_c : r_v ≥ 2},

counted per channel: PA split in WH and in FI counts 2, and CA in 5 districts counts 1 (owner on
#90, 2026-10-04). Two other counts appear in td's sources and must not be confused with it
(`docs/memory/facts/scenario-sweeps-2026-10.md`; the vocabulary of #90's digest):

| name | formula | where it is used |
|---|---|---|
| split units (the key) | Σ_c #{v : r_v ≥ 2} | the owner's ranking; the sweeps' "13-split map" |
| cuts | Σ_c Σ_v (r_v − 1) | the archive's minimum-splits MILP (`archive:docs/HEADLINE.md:184`); #80's λ·\|S\| |
| distinct states split | #{states split in any channel} | #81's summary (8 on the 18-split map, `docs/RESULTS.md`) |

The archive's "8 splits" at δ = 5% are 8 cuts in 4 states, CA 5, NY 3, TX 2 and FL 2
(`archive:docs/HEADLINE.md:221-224, 239-242`). The literature makes the same distinction:
fewest split counties and fewest county splits are different optima (`shahmizad2026` §1).

A unit is a state, a county-built piece or a metro piece (`docs/MODEL.md:28-33`). The key names
*states*: on a map with pieces, a state is split when two or more districts touch any of its
units, and the scorer counts a district holding a cross-state metro as splitting each state the
metro touches (`docs/memory/facts/scenario-sweeps-2026-10.md:42`). Until pieces are used (#59,
#98), units and states coincide.

### 2.2 The rest of the ranking

Eligibility: the ledger audit passes at a plain ±15% band; the main map's total K is 48–54; each
channel's $ per district is within ±10% of its target (national $1.25B, WH $1.0B, FI $900M; IFA a
separate map at $1.25B) **[policy, owner 2026-10-04]** (`docs/lenses/COUNCIL_2026-10-01.md`
§ Triage). Ranks after splits: visual defects (thin links, pieces under 20% of τ, crowded split
states, ZIP-contiguity pieces), then shape, then worst and mean deviation. A map with one split
more than the best and strictly fewer defects than every best-split map stays on the shortlist,
flagged for the owner **[policy]**. The scorer that implements this is #93.

## 3. Today's master

One block per channel, with n_S ∈ ℤ≥0 copies of support S and shares t_{v,S} ∈ [0, 1]
(`docs/MODEL.md:90-113`):

```
Σ_S n_S = K_c
Σ_{S∋v} t_{v,S} = 1                                  v ∈ V_c
η_c n_S ≤ t_{v,S} ≤ n_S                              v ∈ S
(L_c + μ_S) n_S ≤ Σ_{v∈S} M_v t_{v,S} ≤ (U_c − μ_S) n_S
mode rows (whole, clipped, free); contact, corridor, border, count and Menger rows (§4)
min Σ_S w_S n_S,   w_S = diameter(S)
```

What matters for splits:
- **Contacts are linear in n.** With η_c > 0 a copy on S holds at least η_c of every v ∈ S, so its
  footprint is S (Claim 1(1), `docs/MODEL.md:325-328`), and the planned number of districts
  touching v is r_v = Σ_{S∋v} n_S **[proved]**. The η row also caps it: r_v ≤ ⌊1/η_c⌋
  (`docs/MODEL.md:130`).
- **Only splittable units can split.** A whole unit, and a clipped unit inside a multi-unit
  support, has exactly one owner (Claim 1(2), `docs/MODEL.md:330-336`) **[proved]**. On the 51
  the free units number 12 / 16 / 17 / 0 (national / WH / FI / WIFI,
  `docs/memory/facts/scenario-sweeps-2026-10.md:6`).
- **The objective is blind to splits.** A copy of a single free unit, {CA}, has diameter 0, so
  dividing CA among more copies costs nothing; diameter is also blind inside a free unit
  (#81, `docs/RESULTS.md`). Any w_S ≥ 0 that depends on S alone keeps Claims 1–3 and every
  proposition (`docs/MODEL.md:148-154`) **[proved]**; an objective with split indicators does not
  depend on S alone and is not covered.
- **The margin is off in every map since 2026-10-01.** All split numbers below come from runs with
  μ ≡ 0 patched in memory and ZIP 13027's FI cell zeroed; #84 and #86 make that reproducible. With
  μ ≡ 0 the master's optimum and smallest δ bound every connected drawing (Proposition D and its
  corollary, `docs/MODEL.md:266-293`) **[proved]**; with μ_S > 0 they bound nothing
  (`docs/MODEL.md:294-303`).
- **It solves fast.** On the 18-split scenario each channel solves at gap 0 in 0.05–7.55 s
  (5k–25k columns) (`docs/RESULTS.md`, #81) **[tested]**.

## 4. Prior art

### 4.1 In td

- **Measured split counts [tested, m5 runs; not certified].**

  | map | K (national / WH / FI / combined) | split units n / WH / FI = total | within ±10% |
  |---|---|---|---|
  | 18-split, no WIFI, 1,600 km | 16 / 12 / 24 | 5 / 5 / 8 = 18 | 52/52 |
  | NE only combined | 15 / 12 / 22 / 2 | 5 / 3 / 8 = 16 | 51/51 |
  | NE + plains combined | 15 / 12 / 20 / 3 | 4 / 3 / 6 = 13 | 50/50 |
  | same, forced splits only | 15 / 12 / 20 / 3 | 4 / 1 / 4 = 9 | 32/50 |
  | IFA alone | 49 | 22 | 49/49 |

  Sources: `docs/memory/facts/scenario-sweeps-2026-10.md:28, 37-39`; IFA from the 2026-10-01 grid
  (NY in 6, CA 5, NJ 5). 13 is "the minimum found for this design", a search result, and the
  13-split map fails the $ rule on WH 12 ($845M).
- **Forced splits are necessary, not sufficient.** States over 1.1τ number 10 for 16/12/24 and 11
  with New England combined (`scenario-sweeps-2026-10.md:32`). Forced-only plans fail: WH 12 with
  only CA is infeasible even at ±20%, FI 24 needs ±12% (`:29`), and on NE + plains WH cannot plan
  below ±19.6% nor FI below ±17.5% (`:38`). #94 recomputes forced splits at 1.15τ with the
  connected-parts floor.
- **Each connected part of a domain takes a whole number of districts**, so the part's mass sets a
  balance floor (WH's west island: −19.25% at K 11, council 2026-10-01, U40)
  (`docs/lenses/COUNCIL_2026-10-01.md`; `docs/problem/UNKNOWNS.md`).
- **Plans sit on the band edge, and drawing drifts.** Under diameter, the plan deviation equals the
  planning band in every sweep pick; drawing adds 1–3 points and sometimes up to 15% of τ
  (`scenario-sweeps-2026-10.md:8, 29`). A split objective pushes plans to the edge harder
  (`archive:docs/HEADLINE.md:246-247`). Drift is conserved within exchange components (council,
  U41), which #85's swap pass exploits.
- **The archive's minimum-splits MILP** (explicit districts, a single channel, state graph;
  `archive:docs/HEADLINE.md:182-273`, `archive:td/solvers/state_splits.py`):
  - Objective: cuts Σ_s(Σ_j z_sj − 1) plus ε·compactness, with η z ≤ y ≤ z, a hard band,
    single-commodity-flow contiguity and home-state anchors.
  - **ε bound [verified in the archive].** ε = ½ / Σ_s M_s max_j D_sj keeps the compactness term
    in [0, ½), so the tie-break never buys a split (`archive:docs/HEADLINE.md:211-216`). A first
    draft scaled ε at one map's composition and bought 2 splits on a 4-state counterexample
    (`archive:docs/units/state_splits.md:64`).
  - **Exact certificate by cutoff.** `with_cutoff` appends Σ z ≤ n_state + s* − 1; an infeasible
    answer certifies s* without closing a gap (`archive:td/solvers/milp_engines.py:159-176`).
    Level 0 pins each pass's value with an appended row and a small tolerance
    (`archive:td/solvers/level0.py:1228-1330`).
  - **Anchors** remove the k! symmetry (an unanchored one-split gap stayed open 600 s; anchored, it
    closed in 168 s) but are a restriction (`archive:docs/HEADLINE.md:218-221`).
  - **Balance pass.** With z fixed, two LPs: minimise the worst deviation, then the spread; a
    one-LP pass widened the spread 18% on a counterexample
    (`archive:docs/HEADLINE.md:244-273`; `archive:docs/units/state_splits.md:66`).
  - **Refuted.** A contacted state with y = 0 can bridge and leave a district disconnected
    (`archive:docs/units/state_splits.md:63`); "seconds" was false, a 7×7 grid at k = 18 left a
    10.9% gap after 300 s (`:88`).
  - **Certified cuts** at δ = 10%, CONUS, anchored: k 10 → 4, 12 → 4, 14 → 5, 16 → 7, 18 → 7,
    20 → 10, in 1.4–150 s (`archive:docs/memory/facts/level1-certified-splits.md:10-13`). Pre-2025
    data; never re-measured on the v3 extract.
- **#80** holds three objective forms: w_S = diameter(S) + λ·|S|; a two-pass at δ* + ε; a per-piece
  floor ρτ (#80 body and comments).
- **A correction.** #80 and the 2026-10-04 plan said λ·|S| counts splits. It counts cuts:
  Σ_S |S| n_S = Σ_v r_v = |V_c| + Σ_v (r_v − 1) (#90 comment, 2026-10-04) **[note, double
  counting]**. CA in 5 costs 4λ; CA in 4 plus NV in 2 also costs 4λ, but is 2 split units.

### 4.2 In the literature

- **Minimum county splits, exactly** (`shahmizad2025` §2.2, §4, §5.1). Splits are counted as
  cuts, Σ_c (|districts touching c| − 1). Weak split duality: the minimum is at least K minus the
  maximum number of connected county clusters each holding a whole number of districts within the
  band (Thm 1); it was tight on all 140 US instances (§5.1) but the gap can be arbitrarily large
  (Prop. 2). The method is Cluster → Sketch → Detail. Its Sketch MIP has continuous shares z_ij
  capped by touch binaries x_ij with Σ_j x_ij = s_i + 1 (eqs. 3a–3f), td's fractional-share
  setting. The obvious bound Σ_c (⌈p_c / U⌉ − 1) is often weak (Prop. 1, §5.2).
- **Whole units versus splits** (`shahmizad2026` §1, §3). Maximising whole counties and
  minimising county splits are "truly distinct" problems. A hierarchy is solved by pinning the
  first optimum as an equality and re-optimising.
- **Ranking rules change the answer** (`carter2020` Def. 1, Table 1). North Carolina's court rule
  (most 1-county clusters, then most 2-county clusters, …) and the maximum-cluster rule give
  different optima.
- **Territory design produces at most p − 1 split units and removes them** (`kalcsics2005`
  §5.1–5.2). At a basic solution of the transportation relaxation at most p − 1 basic areas are
  split, and the split adjacency is a forest. Splits are a by-product there, never an objective;
  balance is a side constraint and compactness the objective (§4.1), as in commercial territory
  design (`riosmercado2009` §3, eq. 1).
- **Packing with fragmentation** (`casazza2016` Thm 2.1). An optimal solution always exists in
  which each item is fragmented at most once; the compact model's LP bound is trivial.
- **ε-constraints** (`swamy2022` §4.2) are the other standard way to order objectives.
- **Looks.** No classical compactness measure tracks human judgement reliably; convex hull tops
  the correlations in only 54.5% of data sets (`kaufman2021` p. 546). Cut edges "reasonably agree
  with the eyeball test" (`validibuchanan2022`, abstract). Thin strips appear in statute
  (`kaufman2021` fn. 3) and in measure sensitivity (`duchin2018` §3.1), in no exact model.
- **Solver.** HiGHS optimises lexicographically for linear objectives by bounding each
  higher-priority objective; its guide does not say this applies to a MIP (HiGHS user guide,
  "Multi-objective optimization", read 2026-10-04).

Four sources were not read and nothing here rests on them: the equivalent-weights results of
Sherali (1982) and Sherali and Soyster (1983), the Kalcsics–Ríos-Mercado survey chapter (2019) and
Hess and Samuels (1971).

## 5. Candidate formulations

All candidates keep today's rows and change the objective, add rows, or change the layout. The
experiment lanes that test them are #99 (B1), #103 (B2), #104 (B4), #100 (C1) and #101 (C2).

- **F1, a cut charge (#80 form 1; lane B1).** w_S = diameter(S) + λ·|S|. A per-support weight, so
  Claims 1–3 and Proposition D hold unchanged **[proved, MODEL §3.5]**. It prices cuts, not split
  units (§4.1). With Σ_S n_S = K_c, the diameter term is at most K_c·max_S diameter(S) at every
  feasible point, so λ above that makes the order cuts-then-diameter **[note]**; such a λ makes the
  blended objective large, and a relative MIP gap of 1e-4 can then hide a cut (trap 12).
- **F2, split units with a binary (lane B2; the archive's form ported).** For each splittable v, a
  binary s_v and
  ```
  Σ_{S∋v} n_S ≤ 1 + (U_v − 1) s_v,    U_v = min(K_c, ⌊1/η_c⌋, cap_v, |Z_v|)
  ```
  Pass 1 minimises Σ_v s_v; pass 2 pins Σ s_v = s* and minimises diameter, or cuts then diameter.
  Alternatively one pass with ε < 1 / (K_c·max_S w_S) on diameter **[note]**. A certificate is the
  archive's cutoff, Σ s_v ≤ s* − 1 infeasible. s_v enters no (n, t) row and s_v = 1 is always
  feasible, so the (n, t) projection is unchanged **[note]**. Valid fixings: s_v = 1 when
  M_v > U_c; s_v = 0 for whole units **[note]**. With pieces, a state-level count is linear too:
  the districts touching state σ number Σ_{S∩P(σ)≠∅} n_S, where P(σ) is σ's units, because each
  copy's footprint is S **[note]**. A metro piece across states has no such count.
- **F3, a two-pass at δ* + ε (#80 form 2).** Bisect δ*, then minimise splits at δ* + ε. Under a
  plain ±15% band the bisection step drops out, and what stays is the choice of internal planning
  band (SU4).
- **F4, a piece floor (#80 form 3; lane B4).** Each copy's share of a free unit at least ρτ_c:
  M_v t_{v,S} ≥ ρ τ_c n_S for free v ∈ S. η bounds a piece relative to its *unit*, ρ relative to
  the *district* (`scenario-sweeps-2026-10.md:32`). A restriction, like η: Claim 1(iii) then holds
  only for drawings that obey it.
- **F5, the archive's explicit-district lexicographic form.** z_sj contact binaries per (state,
  district), η z ≤ y ≤ z, cuts plus ε·compactness, anchors and flow contiguity (§4.1). A model of
  a different kind: districts are labelled, so it carries k! symmetry the support master does not.
- **F6, split set first (lane C1).** Choose the set F of units allowed to split, make every other
  unit whole, and test whether M_c(δ) is feasible; minimise |F|. Under μ ≡ 0 a free unit that ends
  unsplit satisfies the whole-mode rows, so min |F| equals the minimum split count when the outer
  search is exact **[note]**. A greedy outer search, or one driven by mass arithmetic alone, is a
  heuristic; the forced-only failures (§4.1) show arithmetic is not enough. With μ_S > 0 the
  equivalence fails, because a free unit pays its heaviest ZIP in μ_S even when unsplit
  (`docs/problem/BALANCE.md:328-330`).
- **F7, regions first (lane C2).** Group whole states into regions, give each region an integer
  number of districts, plan each region. Exact only if it enumerates the K allocation and keeps
  the parent τ_c **[note]**; a per-part solve otherwise plans around its own mean and is not the
  joint solve (`docs/lenses/COUNCIL_2026-10-01.md`, Sol and Astra). The hand-carved NE + plains
  region is the best result so far (18 → 13 splits).

Every candidate that minimises splits needs a balance pass after it, splits fixed, worst deviation
then spread (§4.1).

## 6. Constraints and non-goals

- **Masked:** sales, rep names and firm names never enter the repo, an issue or anything online;
  descaled opportunity and dollars may.
- Runs are reproducible from git: margin off through #84's switch, not an in-memory patch. A
  claimed minimum must carry its certificate or be called a search result.
- Solver settings: `mip_rel_gap = 0` and `mip_abs_gap = 0` for a certificate (trap 12); one
  thread count per process (trap 18); never drop the objective to find a feasible point (trap 19).
- Non-goals: staffing; new channels (#76, #77). The realizer's geometry is out of scope here, but
  M1 is not: a formulation must be judged on the contiguous maps it allows (SU9).

## 7. Unknowns

Numbered SU here; triage gives each a U-number or folds it into an existing one. Grades: **E**
settleable by computation, **B** needs a business answer, **T** needs a theorem. #91 checks every
T claim with a proof sketch and a brute force over all plans on 6–10 units.

| id | unknown | grade |
|---|---|---|
| SU1 | **The split count in the master.** Is F2's big-M row with U_v the right statement of split units, or is a disaggregated form (for example s_v ≥ n_S + n_T − 1 over supports containing v) needed for a usable LP bound? Which LP relaxation is stronger, F2 or F1's cuts, and what are the root gaps on the 51 and on NE + plains? With pieces: is the state-level row of F2 correct, and what replaces it for a metro across states? | T/E |
| SU2 | **Splits first, then diameter.** Is F2's pinned two-pass exactly lexicographic, and is one pass with ε < 1 / (K_c·max_S w_S) exact as well? Do Claims 1–3 and Proposition D survive with s_v (the read-back sets s_v = 1[r̂_v ≥ 2]), so that with μ ≡ 0 the pass-1 optimum is a lower bound on the split units of every connected drawing? What gap settings does each need, and does HiGHS's lexicographic mode work on a MIP? | T |
| SU3 | **A lower bound on split units per channel and K.** Beyond the mass floor (M_v > 1.15τ) and the connected-parts floor: is there a split-unit analogue of weak split duality (`shahmizad2025` Thm 1 bounds cuts), and how weak is it under ±15%, where any connected set of mass at least 2.55τ fits a whole number of districts? | T/E |
| SU4 | **The internal band.** How tight must a plan be inside the ±15% audit band so that drawing drift fits, how many split units does each point of internal band cost, and do drawn split units equal planned ones (repair can add an owner; a tiny share can vanish)? | E |
| SU5 | **Symmetry and degeneracy.** s_v is indexed by unit, so it adds no label symmetry, but many n give the same split set. Does that slow the proof that no smaller split count exists, and how long do F2's passes take on 1.4k–1.9k supports? | E |
| SU6 | **Which layouts are exact.** Prove or refute: F6 is exact under μ ≡ 0 with an exact outer search; F7 is exact only when it enumerates the K allocation and keeps τ_c. What does each lose when it is not exact? | T |
| SU7 | **Defects in the master.** Which visual defects can be rows or weights (F4's piece floor; a cap on districts per split state, which bounds cuts), and which stay in the scorer? Does F4 keep Claim 1 and Proposition D as η does, as a restriction? | T/B |
| SU8 | **Exchange rates.** Is CA in 5 worse than CA in 4, so cuts are rank 1b? Should a district holding a cross-state metro count as splitting each state? What is a split worth against one point of balance inside the band? | B |
| SU9 | **Splits under M1.** Which candidate formulations keep their guarantees when every drawn district must be ZIP-connected on the polygon graph? Does a split unit's share need a contiguity condition in the master (for example, the share must border the district's whole units), and how far can the unit-level minimum split count understate the minimum for contiguous maps? | T/E |

## 8. What we want back

- **Pass 1, each seat independently:** an answer to SU1–SU9 in your own terms, with a confidence
  and what would change it, and a recommendation for the master's objective: which formulation
  lane B2 (#103) builds, whether lane B1 (#99) stays as a cuts proxy, what lane B4 (#104) adds, and
  the certification protocol (passes, pins, gaps, cutoff).
- **Pass 2:** each claim from pass 1 marked agreed, contested or refuted, with evidence.
- **For #91's verification:** every T-graded claim stated precisely enough to brute-force over all
  plans on 6–10 units against the MILP, under `tools/exp/verify/`, by a seat of a different vendor
  than the claim's author.
- **Evidence:** this brief; `docs/MODEL.md` (§3, §4.6–§4.7, Claims 1–3); `docs/problem/BALANCE.md`;
  `docs/lenses/COUNCIL_2026-10-01.md`; `docs/memory/facts/scenario-sweeps-2026-10.md`; the archive
  files cited in §4.1; issues #80, #81, #84, #85 and #90's comments.
