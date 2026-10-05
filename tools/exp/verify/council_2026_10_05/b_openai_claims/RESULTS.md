# #91 verification, lane b_openai_claims (p1-sol, p1-astra; pass-2 refinements)

Verifier: Opus 5.5 (Anthropic), independent of the claims' authors (OpenAI seats). m5-studio,
2026-10-05, td `main` 8875bf7 (SPLITS.md as of 470c18f), Python 3.13.15, highspy 1.15.1.

**Command.** `"$TD_PY" -u tools/exp/verify/council_2026_10_05/b_openai_claims/run_all.py`
runs all five scripts in 61 s and reports `ALL OK`. Each check prints one line, `[ok]` or
`[MISMATCH]`. `[ok]` means the brute force matched the verdict below, including when that verdict
is "refuted".

**What the model is.** `model.py` is the master of MODEL §3 with μ ≡ 0. It carries the coverage,
η, band, mode, count-cap, corrected border-cap (C7) and component-versus-rest corridor rows, with
the F2 binaries `1 + s_v ≤ r_v ≤ 1 + (U_v − 1)s_v` and `U_v = min(K, ⌊1/η⌋, |Z_v|)`. Options add
Hall rows, the F4 floor, η = 0, a zero-share contact mode, fixed n, forbidden supports and extra
rows. MILPs run on highspy with `mip_rel_gap = mip_abs_gap = 0` and `threads = 1` (traps 12, 18).

There are two brute forces:
- **Plans.** Every integer n over the family with Σn = K passes the n-only rows, and a share LP
  checks each one (or minimises δ for it).
- **Drawings.** Every partition of the ZIPs into exactly K blocks, each connected on the ZIP graph.

The random suites are fixed seeds of `random_inst`: 110 instances with 6–8 units, 7–19 ZIPs,
K = 2–5 and size cap 2–3, each with at least one feasible plan (`common.SEEDS_A`, `SEEDS_B`). The
hand instances are written out below and in the scripts.

**Readings I used.**
- A "split" in the master is r_v ≥ 2.
- On drawings there are two split counts: *ownership* (owner decision 1: ≥ 2 districts own a ZIP
  of v) and *positive* (≥ 2 districts hold positive mass in v).
- D = Σ_S w_S n_S, with w the diameter, and W = K · max_S w_S.
- F6's "make every other unit whole" means setting its mode to whole.
- F7 is the parent instance with every crossing support fixed to 0, plus Σ_{S⊆R1} n_S = k1 for
  each k1. The parent τ and band are kept.

## Summary

| claim | verdict | script |
|---|---|---|
| p1-sol T1 | holds (indicator, projection, state rows; pairwise row invalid; η cap is not a state cap) | check_t1_t3 |
| p1-astra T1 | holds (same; the astra fixture refutes the pairwise row) | check_t1_t3 |
| p1-sol T2 | holds with stated conditions: lex exact; the bound covers only 𝒳_c(δ), the matching-policy class | check_t2 |
| p1-astra T2 | holds with stated conditions (same; B = 0 case checked) | check_t2 |
| p1-sol T3 | holds | check_t1_t3 |
| p1-astra T3 | holds | check_t1_t3 |
| p1-sol T4 | holds (F6 exact under μ = 0; F7 exact only for noncrossing supports; counterexample confirmed) | check_t4_t5 |
| p1-astra T4 | holds (F6; F7 confined; F4 only for floor-obeying drawings; counterexample confirmed) | check_t4_t5 |
| p1-sol T5 | holds with stated conditions (F4 keeps Claim 1 and Prop D only for floor-obeying plans and drawings) | check_t4_t5 |
| p1-sol T6 | holds (star; disconnected unit part in a valid M1 map) | check_m1 |
| p1-astra T5 | holds (star; equal-target lift fails, fibre not empty) | check_m1 |
| p1-astra T6 | holds (metro: one read-back, state splits 0 or 2) | check_m1 |
| Extra (a): s* bounds the ownership split count of every M1 map | **refuted.** Holds for maps in 𝒳_c(δ). Fails when a district's footprint share is 0 (zero-mass ZIPs) or in (0, η) | check_extra |
| Extra (b): δ* bounds the best drawn balance of M1 maps | **refuted** under the same conditions; holds over 𝒳_c(δ) | check_extra |
| p2 C1 (sol, astra, opus, fable) | confirmed under the positive key. Under decision 1 their instances no longer break the bound, but CE1 and CE3 do. Opus's "master infeasible at δ = 0" is **false as stated** (true only with Hall rows) | check_extra |
| p2 C2 (Hall rows) | Hall rows are valid. The opus star is closed by Hall + corridor. The astra border-star is **not** closed: Hall rejects {a,v}+{b,v}, but {a,v,b}+{v} stays feasible with no drawing. The sol and fable stars are not closed; their paths lift | check_m1 |
| p2 C3 (no-good scope) | confirmed on the instances: equal targets fail with a non-empty fibre; per-unit connectivity is not necessary | check_m1 |
| p2 C4 (forced-set arithmetic) | the logic holds on toys: up-closure, Φ ⊆ F, s ≥ \|Φ\|+1. The shrink caveat is real (hand instance). The national, WH and FI numbers are not checkable here | check_t4_t5 |
| p2 C5 (F7) | confirmed: restriction, ≥ s*, exact iff some optimal plan is region-confined | check_t4_t5 |
| p2 C6 (top layer) | confirmed: only C(\|P\|−\|Φ\|, s*−1−\|Φ\|) sets need checking under μ = 0 | check_t4_t5 |

## Claims

### p1-sol T1 and p1-astra T1: the F2 split indicator

**Verdict.** Holds.

**Proof checked.**
- For integer r ∈ [1, H]: s = 0 forces r = 1, and s = 1 allows 2 ≤ r ≤ H. Astra's
  `r ≤ 1 + (U−1)s, s ≤ r − 1` defines the same set.
- s_v enters no (n, t) row. s_v = 1 is feasible whenever r_v ≤ U_v, and U_v is a valid cap
  (⌊1/η⌋ from summing the η rows; |Z_v| from the count cap). So the projection onto (n, t) is
  unchanged.
- State rows: each copy's footprint is S (Claim 1(1)), so a copy meets state σ iff
  S ∩ P(σ) ≠ ∅, and a support holding two pieces of σ counts once.
- A unit's η cap does not bound the districts touching a state.

**Instances.** 156 (H, r, s) triples, H = 1..12. 110 random instances and 9,145 candidate n
vectors: the MILP with n fixed is feasible iff the share LP is, and the MILP split optimum equals
the enumerated one on all 110.

**Fixtures.**
- sol: free v with ZIPs 1, 1, .5 on a path, the .5 ZIP bordering a; whole a .5; four isolated
  whole mass-1 units; K = 7, η = .1, δ = 0.
  - The unique plan is {v}×2 + {a,v} + four singletons, with s* = 1.
  - The pairwise row s_v ≥ n_v + n_va − 1 = 2 makes the MILP infeasible.
  - The plan lifts to an 𝒳_c drawing.
- astra: free v of three unit ZIPs, five whole mass-1 units, v3–u1 adjacent; K = 8, η = .2,
  δ = 0. The plan is n_{v} = 3. The unused {v,u1} gives s ≥ 3 + 0 − 1 = 2, and the MILP is
  infeasible.
- State pieces: state S = pieces p1, p2, plus whole x of state X.
  - η = .5, K = 5, ZIPs of mass 1: S is touched 4 > ⌊1/η⌋ = 2 times. Capping the state at 2
    makes the master infeasible.
  - η = .25, K = 4, ZIPs of mass .5: the plan {p1}, {p1,p2}, {p2}, {x} has state count 3 against
    Σ r_v = 4.
  - The MILP state-split minimum equals the enumeration, and the count equals the drawn ZIP
    owners of S in every 𝒳_c drawing.

### p1-sol T2 and p1-astra T2: splits then diameter; the bound with s_v

**Verdict.** Holds with stated conditions.
- The lexicographic part holds unconditionally.
- The bound holds only over 𝒳_c(δ), as both authors say: same family, η, modes, caps and band,
  μ = 0. See Extra (a) for what lies outside it.

**Proof checked.**
- If S1 < S2 then S1 + εD1 ≤ S1 + εW < S1 + 1 ≤ S2 + εD2 when εW < 1. With W = 0, D ≡ 0.
- Prop D's read-back of an 𝒳_c drawing satisfies every row. Setting ŝ_v = 1[r̂_v ≥ 2] satisfies
  F2, so (s*, D*) ≤lex the drawing's (splits, D).
- Inside 𝒳_c every footprint share is ≥ η > 0, so the ownership and positive split counts coincide
  with r̂.
- Claim 3's proof (MODEL §5) reads no objective; I checked this by reading, and nothing here tests it.

**Instances.** 110 random instances, 49 of them with several split levels.
- The pinned two-pass and the one pass with ε = 0.999/W both return the enumerated lex optimum on
  all 110. ε = 1000/W departs from lex on 2 of them, so the condition is needed.
- W = 0 instance (all centroids equal): D = 0, splits alone.
- 126 𝒳_c drawings: every read-back is feasible in the MILP (including s_v) with no row violated,
  and its (splits, D) is ≥lex the master's.
- One connected in-band drawing outside 𝒳_c had fewer splits than s*. This is informational; the
  claim does not cover it.

### p1-sol T3 and p1-astra T3: cuts bound → split bound

**Verdict.** Holds.

**Proof checked.** Every split v has r_v − 1 ≤ H_v − 1, so C = Σ_split (r_v − 1) ≤ the sum of
the |split| largest (H_v − 1). With B ≤ C, the least such q is a lower bound.

**Instances.** 110 random instances, with B the exact minimum number of cuts (enumeration, and
equal to the MILP with the `cuts` objective). The bound holds on all 110 and is tight on 103. The
per-plan inequality holds for every feasible plan.

### p1-sol T4 and p1-astra T4: F6 and F7 exactness, and F4 (astra part 3)

**Verdict.** Holds.

**F6 proof checked.**
- Under μ = 0, a free unit that ends unsplit has r_v = 1, a single copy with t = 1, so it
  satisfies the whole-mode rows. Hence min |F| = s*.
- The feasible F form an up-set (a larger allowed set is a relaxation).

**F6 evidence.** 110 instances, 1,508 allowed sets each solved as a MILP:
- min |F| = s* on all 110.
- The up-set property holds.
- Every feasible F contains Φ(δ) = {v splittable : M_v > U_c}.

**F7 proof checked.** F7 is the master with every crossing support fixed to 0, so its count is
≥ s*, and it is exact iff some optimal plan uses no crossing support.

**F7 evidence.** 110 instances, with regions = the first half and the second half of the unit
list:
- F7 ≥ s* always.
- Equality held exactly when an enumerated optimal plan is region-confined: 14 instances.
- 96 were region-infeasible while the parent was feasible.
- On a noncrossing family, F7 over all allocations equals the master.

**F7 counterexamples confirmed.**
- sol: six-unit path, unit masses, whole, size cap 2, K = 3, ±15%.
- astra: masses .6/.4/.6/.4/.6/.4, no size cap.
- In both, the parent plan pairs {1,2}, {3,4}, {5,6} with s* = 0, and every allocation
  (0,3), (1,2), (2,1), (3,0) of regions {1,2,3} / {4,5,6} is infeasible at the parent τ.

**F4.** See p1-sol T5.

### p1-sol T5 (and p1-astra T4 part 3): the F4 piece floor

**Verdict.** Holds with stated conditions.

**Proof checked.** The aggregate row M_v t_{v,S} ≥ ρτ n_S divided by n_S is the per-copy floor
for the decoder's equal shares. Summing per-copy floors gives the aggregate row (Claim 1(iii)).

**Instances.** ρ = 0.3, 110 instances and 9,145 n vectors:
- The aggregate LP is feasible iff the explicit per-copy LP is.
- The F4 MILP equals the enumeration.
- All 66 floor-obeying 𝒳_c drawings read back as F4-feasible.

**Scope counterexample.**
- Whole a .8 – z0 .2 – z1 1.0, with v = {z0, z1} free; K = 2, δ = .05, η = .1.
- {a,z0} | {z1} is in 𝒳_c (masses 1.0 and 1.0), but its v-piece .2 is below ρτ = .3.
- The master without F4 is feasible (s* = 1); with F4 it is infeasible.
- So Prop D extends only to floor-obeying drawings.

### p1-sol T6: master feasibility vs M1; per-unit connectivity

**Verdict.** Holds.

**Star.**
- v is a six-ZIP unit-mass star, clipped or free, plus five isolated whole mass-3 units; K = 7,
  δ = .15, η = .05.
- The master is feasible: {v}×2 at mass 3, s* = 1.
- Of the 5 connected 7-partitions, none is in band: 0 M1 maps.

**Local connectivity.**
- Free v is the path z1..z5 with masses 1, 1.5, 1.5, 1.5, 1. A (.5) borders z1, B (.5) borders
  z5, C (1.5) borders z1 and z5; P and Q are isolated, mass 4.5 each. K = 4, ±15%.
- {z1,z5,A,B,C} | {z2,z3,z4} | {P} | {Q} is an M1 map, all masses 4.5, and its v-part {z1,z5}
  is disconnected.
- Of the 3 M1 maps, 2 have every district∩unit connected. A per-unit connectivity rule would
  delete the third.

### p1-astra T5: finite optimum without M1; equal targets vs fibre

**Verdict.** Holds.

**Star.** As in p1-sol T6.

**Second case.**
- v is two adjacent ZIPs .9 and 1.1, plus five isolated whole mass-1 units; K = 7, η = .1, ±15%.
- The plan n_{v} = 2 has targets 1 and 1, and no assignment of v's two ZIPs hits them.
- The drawing {.9} | {1.1} is in 𝒳_c with the same read-back.

### p1-astra T6: a metro's (n, t) does not fix state splits

**Verdict.** Holds.

**Instance.**
- A 2×2 unit-mass ZIP grid is one metro unit; the columns are states X and Y. Five isolated
  whole mass-2 units; K = 7, ±15%, η = .1.
- Both 𝒳_c drawings read back as n_m = 2, t = 1.
- The column split gives 0 state splits; the row split gives 2.

## The extra question (owner decision 1)

**Setting.** Every unit is free and the family is every connected unit set, so modes, family and
caps match and η is the only difference between M1 and 𝒳_c(δ). M1 maps are all connected
K-partitions of the ZIP graph with mass in band. Three masters are compared:
- **std:** MODEL §3, with t ≥ η n.
- **zero:** η only on positive contact. n_S = p + q, η p ≤ t ≤ p, Σ_S q_{v,S} ≤ #zero-mass ZIPs
  of v, and the contact cap is widened by that number.
- **eta0:** η = 0.

On 472 random instances (seeded), the MILP form of each master equals its plan enumeration at
δ = .15.

### (a) Is s* a lower bound on the ownership split count of every M1 map?

**No.** It is a lower bound exactly over M1 maps whose every footprint share is ≥ η, which is
𝒳_c(δ): Prop D, checked on 126 drawings and on every 'eta'-class map in both searches. Below,
"zero share" means a district owns only zero-mass ZIPs of a unit, and "tiny share" means its share
lies in (0, η).

**Counterexamples.**
- **CE1 (zero share; master infeasible).**
  - Instance: whole a .9 – z0 0 – whole b .1, with z0 – z1 1; v = {z0, z1} free; K = 2, η = .15.
  - M1 map {a,z0,b} | {z1}: masses 1 and 1, 1 ownership split.
  - std master: δ* = .05 (enumeration and MILP bisection agree). At δ < .05 it is infeasible, so
    it gives no finite bound below the map's 1 split.
  - zero and eta0 masters: s* = 1 at δ = 0.
- **CE3 (zero share; finite gap).**
  - Instance: a = {a0 .85, a1 .05} free; v = {z0 0, z1 1} free; whole b .1. Edges a0–a1, a0–z0,
    a1–z1, z0–b, z0–z1. K = 2, η = .15, δ = 0.
  - M1 map {a0,a1,z0,b} | {z1}: exact balance, 1 ownership split.
  - std master: s* = 2, via {a,v} + {a,v,b}.
  - zero and eta0 masters: s* = 1.
- **CE2 (tiny share; the smallest counterexample).**
  - Instance: whole a .9 – z0 .1 – z1 1.0; v = {z0, z1} free; K = 2, η = .15.
  - M1 map {a,z0} | {z1}: exact balance, 1 split, v-share .1/1.1 = .091 < η.
  - std and zero masters: infeasible below δ* = .065.
  - eta0 master: s* = 1 at δ = 0.

**Smallest.** An exhaustive search over ≤ 3 ZIPs (3,272 instances: every connected ZIP graph and
connected unit partition, masses in {0, .1, .5, .9, 1}, K ∈ {2, 3}, η = .15):
- finds counterexamples only of the tiny-share kind, the smallest being 3 ZIPs and 2 units
  (CE2's shape);
- finds none with ≤ 2 ZIPs, none from 𝒳_c and none from zero shares.

No zero-share counterexample can have ≤ 3 ZIPs. A district with a zero share needs a second unit
to carry its mass, and with 2 units the master's {a},{v} draws the same masses with fewer splits.
CE1 has 4 ZIPs. A 700-draw random search over 4–6 ZIPs found zero-share counterexamples
(smallest: 6 ZIPs) and no finite-gap case; CE3 is hand-built.

**Which master change restores the bound.**
- **zero-share contact mode.** Restores it for M1 maps whose shares are all 0 or ≥ η: no
  counterexample in either search, and CE1 and CE3 are closed. It still fails on tiny shares (CE2).
- **η = 0 in the bounding master.** Restores it for every M1 map with matching modes and family:
  no counterexample in 3,272 + 472 instances. Every row in Prop D's proof except η holds without
  η; for the Hall, border and count rows this was checked on 141 drawings with η = 0.
- **What I did not check.** The cost of either change: Claim 1(1) decoding for zero-share copies,
  or the realizer.
- **Label.** With η > 0 as built, the honest label is "a lower bound over 𝒳_c(δ)" (fable C1). An
  M1 map in which a district holds a sliver below η of some unit (common at η = .05 with a single
  small ZIP of a large state) is not covered.

### (b) Is δ* a lower bound on the best drawn balance of M1 maps?

**No, under the same conditions.**
- CE1: δ* = .05, but an exact M1 map exists.
- CE2: δ* = .065, but an exact M1 map exists.
- Over 𝒳_c(δ) it holds (MODEL §4.7 Corollary), and the zero and eta0 masters restore it for the
  same classes as in (a).

**Opus pass-2 C1, checked as asked.**
- Instance: whole a .5, b .5; v = {z0 0, z1 1}; z0 borders a and b; K = 2, η = .05.
- At δ = 0 the MODEL §3 master is **feasible**: {a,v} + {v,b} at t = .5, masses 1 and 1. It
  passes the border cap (1 ≤ 1) and the count cap (2 ≤ 2).
- So "the master is infeasible at δ = 0" is false for the master as specified. It becomes true
  once the pass-2 Hall row is added (|∂_a ∪ ∂_b| = |{z0}| = 1 < 2).
- The conclusion Opus drew (δ* is not a bound on M1 balance) is still right, by CE1.

## Pass-2 items that bear on the claims

- **C1 (sol, astra, opus).**
  - Each instance has an M1 map with 0 positive-opportunity splits against s* = 1, so the bound
    fails under the old key.
  - Its ownership count is 1, so under decision 1 these three instances no longer refute the
    bound. CE1 and CE3 above do.
  - Fable's three conditions for the label match what the brute force shows.
- **C2.**
  - The Hall row holds on all 141 connected in-band drawings whose footprints are in the family,
    checked with η = 0.
  - sol: the lone six-ZIP star is feasible with or without Hall and has no drawing; the six-ZIP
    path lifts.
  - astra border-star (hub and two unit leaves, a and b .5 on the hub, K = 2, ±15%):
    - Hall rejects {a,v}+{b,v}.
    - But {a,v,b}+{v} (corridor floor 1, mass 2) stays feasible, and there is no drawing.
    - So Hall does not close this star, contrary to the implication of "Hall gives 2 ≤ 1,
      rejecting plan".
  - opus star (masses 1/3, δ = .1): feasible without Hall, infeasible with it, no drawing. Hall
    plus the corridor floor close it.
  - opus path .1/.8/.1: feasible with Hall, no drawing. With 1/3 each it lifts.
  - fable star (c, l1..l4; u at l1, w at l2): feasible with Hall (2 ≤ 2), no drawing. The 5-ZIP
    path lifts.
- **C3.**
  - astra's .9/1.1 instance: the fixed-target lift fails while the fibre is non-empty.
  - The sol T6 fixture: per-unit connectivity is not necessary.
- **C4.**
  - On toys, feasible split sets are up-closed and contain Φ(δ), and forced-only infeasibility
    gives s ≥ |Φ|+1.
  - Hand instance for the shrink caveat:
    - Instance: path x–w–v1. Whole x .83 borders w0. w = {w0 .17, w1 .88} free.
      v1 = {.56, .56} free, so v1 = 1.12τ. K = 3, δ = .15.
    - Φ(1.15τ) = ∅ ⊊ Φ(1.10τ) = {v1}.
    - Allowing only {v1} is infeasible, yet s* = 1 via {w}.
    - So "|Φ_1.10| + 1" would be a false bound.
  - One random instance (rand55) shows the same.
  - The WH ≥ 3, FI ≥ 6 and national 4 figures depend on the extract and are not checkable here.
- **C5.** Confirmed: see p1-sol T4.
- **C6.** Confirmed: under μ = 0 only the top layer F ⊇ Φ with |F| = s* − 1 needs checking. It
  has C(|P|−|Φ|, s*−1−|Φ|) sets, and on 110 instances all 38 such sets were infeasible.

## Residual risks

- **Solver-relative.** The share LPs and the MILPs are both HiGHS. The integer side is enumerated
  exhaustively, but the continuous feasibility of each plan is HiGHS's LP answer at default
  tolerances. Fixtures at δ = 0 sit exactly on band edges with exact decimal masses; none was
  near a tolerance boundary I could see.
- **Coverage.**
  - The random suites are small: 110 instances, 126 𝒳_c drawings, 141 drawings for Hall.
  - Hall structure and multi-copy splits are sparse in them: s* is 0, 1 or 2 on 67, 36 and 7
    instances.
  - The "smallest" claims hold only within the stated search grid.
- **Not tested.**
  - The Menger row (optional, off) and contact caps.
  - μ > 0.
  - Claim 3's objective-independence (read, not run).
- **The zero master was checked as a bound only.** Whether its zero-share copies decode and
  realize is not checked.
