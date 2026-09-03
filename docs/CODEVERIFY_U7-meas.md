# CODEVERIFY U7-meas — `tools/measure/premium.py` against `docs/MODEL_U7-meas.md`

**Date:** 2026-09-03 · **Branch:** `wt/A1` · **HEAD:** `74eff38` · **Verifier:** `code-verify`
**Spec:** `docs/MODEL_U7-meas.md` · **Brief:** `docs/units/U7-meas.md` · **Code:**
`tools/measure/premium.py`, `tools/measure/__init__.py`, `tests/test_measure.py`
**Interpreter:** `/Users/ntlee/projects/td/.venv/bin/python3` (3.13.15; numpy 2.5.2, scipy 1.18.1,
networkx 3.6.1, pyscipopt 6.2.1) · **Instance:** `instance_descaled.json.gz`
sha256 `cf7d66c09b28be1e032b0cad96f3995455197f92366d840d0f517da84845a522`

## Summary

**15 VERIFIED · 2 REFUTED · 0 INCONCLUSIVE.** Both REFUTED rows are defects in the *model
text*, not in the code, and neither moves a number: (R1) §3's `S₁₃ = im σ₀` contradicts §4's
own worked example when `σ₀` is a hand roster — the code implements the reading §4's numbers
pin, which is also the only one under which the ladder stays valid; (R2) §3.1's "the greedy
`(1 − 1/e)` solution seeds it" is not implemented and cannot be — `scipy.optimize.milp` has no
warm-start option; greedy is computed and reported alongside, never used as a seed.

| # | claim | verdict |
|---|---|---|
| 1 | §1 `P₀ = Σ_j b_{σ₀(j),j}` ↔ `roster_premium` — 432.0507 / 37.8164% on seed 3 | VERIFIED |
| 2 | §1 decomposition `g = B_j + w·b`, `w = 0.42` ↔ `book_matrix` vs `channel.gain_matrix` | VERIFIED |
| 3 | §3 `P*(A)` ↔ `best_roster` (Hungarian on `−b`) | VERIFIED |
| 4 | §3 `P_S = Σ_z max_{i∈S₁₃} S_i(z)` ↔ `coverage_premium` at the Nash image | VERIFIED |
| 5 | §3 `P₁₃` ↔ `max_k_coverage` MILP — 598.0103, staff swaps R0009/R0012 in for R0017/R0018 | VERIFIED |
| 6 | §3 `P_free` ↔ `coverage_premium(range(n))` — 907.6440 / 79.44% | VERIFIED |
| 7 | §3 ladder `P₀ ≤ P*(A) ≤ P_S ≤ P₁₃ ≤ P_free` | VERIFIED (justification text imprecise) |
| 8 | §3.1 MILP formulation, trap 12 (`mip_rel_gap=0.0`), trap 15 (no bound on a non-optimal stop) | VERIFIED |
| 9 | §3.1 "the greedy solution **seeds** it" | **REFUTED** (model text) |
| 10 | §4 worked example — ladder 24/28/28/28/33, `g`, `V = 6.1788`, roster (A, C) | VERIFIED |
| 11 | §3/§4 `S₁₃ = im σ₀` under an explicit roster override | **REFUTED** (model text; code correct) |
| 12 | §5 U1 realised-gain spread beside the `M`-spread | VERIFIED |
| 13 | §5 U4 — 83 zips, 6.1209% of `M` | VERIFIED |
| 14 | §5 U8 — `corr(T,M) = 0.6500` pooled, per-rep over held zips | VERIFIED |
| 15 | §5 `V` at `σ₀` and at the `P*(A)` roster | VERIFIED |
| 16 | §6 verdict conversion `w·ΔP/ḡ` and the `small` flag at 5e-3 | VERIFIED |
| 17 | §7 provenance, both draws, byte-identical re-run, stop rule | VERIFIED |

**Mechanical gates.** `uvx pyright 1.1.411 --pythonpath …/.venv/bin/python3 tools/measure/premium.py
tools/measure/__init__.py tests/test_measure.py` → **0 errors, 0 warnings, 0 informations**.
`.venv/bin/python3 tests/run_all.py` → **184 passed, 0 failed, 0 skipped** (5.5 s), of which
10 are `test_measure.py`. Byte-identical re-run of both draws: the committed
`battery/results/meas_20260903/*.json` reproduce line-for-line apart from `"written"`.

**Oracles used (all independent of the implementation).** A second reader of
`instance_descaled.json.gz` (gzip+json, `S_i = share·m_rel`, no `td.instance`); the assignment
**LP** through `scipy.optimize.linprog` instead of the Hungarian; **SCIP** (pyscipopt) instead of
scipy/HiGHS for the `P₁₃` MILP; a **submodular branch-and-bound** with no solver at all, itself
self-tested against exhaustive enumeration on 200 random matrices; brute-force enumeration of
every roster and every `k`-subset on small instances; a 4 000-instance randomized search.

## Mapping table (model object → code symbol)

| model | code | note |
|---|---|---|
| `P(π,σ)`, §1 | `premium.py:99 roster_premium` | `Σ_j b[σ(j),j]` |
| `b_ij`, §1 | `premium.py:76 book_matrix` | same accumulation as `channel.gain_matrix:281-284`, `common` dropped |
| `S_i(z)`, §1 | `premium.py:63 book_by_zip` | via `model.books` |
| `w = (1−λ)(1−θ)`, §1 | `premium.py:251` | 0.42 at the defaults |
| `P*(A)`, §3 | `premium.py:106 best_roster` | `linear_sum_assignment(-b)`, rectangular 111×13 |
| `P_S`, §3 | `premium.py:121 coverage_premium` at `staff` (`:271`) | `staff = sorted(set(nash.values()))` |
| `P₁₃`, §3/§3.1 | `premium.py:152 max_k_coverage` | scipy MILP, `mip_rel_gap=0.0` |
| `P_free`, §3 | `premium.py:276` | `coverage_premium(S, range(len(R)))` |
| `V(π,σ)`, §2/§5 | `premium.py:204 roster_value` | `Σ_j log g[σ(j),j]` |
| U1, §5 | `premium.py:212 spread` on `gains` and `M_district` | |
| U4, §5 | `premium.py:292` | `|cand(z) ∩ S₁₃| ≥ 2`, plus `M`-share |
| U8, §5 | `premium.py:195 pearson`, `:296-300` | pooled `corr(T,M)`, per-rep over `S_i>0` |
| §6 conversion | `premium.py:221 gap` | `nats = w·ΔP/ḡ`, `small = nats ≤ 5e-3` |
| §7 provenance | `premium.py:333 sha256`, `:419-430` | run id, instance/draw sha256, params, timestamp |

No model object is unimplemented. Code with no model counterpart is provenance plumbing
(`resolve_draw_dir`, `read_draw`, `read_metrics`, the CLI flags), which §7 covers.

---

## Rows

```
CLAIM     §1/§3 P₀ = Σ_j b_{σ₀(j),j} = 432.0507 (37.8164% of total book), seed-3 draw
          ↔ tools/measure/premium.py:99 roster_premium via measure():272
ATTACK    Recomputed from the raw gz (gzip+json, S_i = share·m_rel — never td.instance),
          draw.csv and metrics.json winner.assignment, summing per district by hand.  Also
          recomputed on the seed-9 draw, whose roster is different.
VERDICT   VERIFIED
BASIS     Numeric-equality tier.  seed 3: oracle 432.050719692444 vs produced
          432.050719692444 (|Δ| 5.7e-14, rel 1.3e-16 — summation order only); share
          0.378163982868 vs 0.378163982868 (|Δ| 5.6e-17).  seed 9: 448.733400542030 vs
          448.733400542031.  total_book 1142.4956877592515 identical.
ARTIFACT  docs/artifacts/U7-meas/oracle_ladder.py
          .venv/bin/python3 docs/artifacts/U7-meas/oracle_ladder.py instance_descaled.json.gz \
            battery/results/draw_k13_20260901 \
            battery/results/meas_20260903/draw_k13_20260901.json
CAVEATS   The oracle shares the *file* with the code; it does not re-derive the export from
          source data.  The instance's own defects (FRAME §5) are inherited by both.
```

```
CLAIM     §1 decomposition u_i(z) = common(z) + w·S_i(z), so g_ij = B_j + w·b_ij with w = 0.42
          ↔ premium.py:76 book_matrix against td/channel.py:252 gain_matrix
ATTACK    Not only the §4 toy the test fixture pins: computed g on the real 111×13 instance
          from the definition (c1 = 0.7, c2 = 0.28, c_free = c2 for filler_capture="theta")
          in the oracle and checked max_ij |(g − w·b) − (g − w·b)[0]| over all 111 rows.
VERDICT   VERIFIED
BASIS     Real instance, both draws: row deviation 1.42e-14 on gains of order 1e2 (rel 1e-16),
          i.e. exactly the rep-independent B_j.  Toy: rows identical to 1e-12, g reproduces
          [[22.82,16.10],[17.78,19.46],[16.10,21.14]] to 1e-9.
ARTIFACT  docs/artifacts/U7-meas/oracle_ladder.py (g_minus_wb_row_deviation),
          docs/artifacts/U7-meas/oracle_toy_and_monotonicity.py
CAVEATS   Checked at filler_capture="theta" (the run parameter) and "full" (boundary probe);
          "opportunity" not exercised on the real instance.
```

```
CLAIM     §3 P*(A) = max_σ Σ_j b_{σ(j),j} ↔ premium.py:106 best_roster (Hungarian on −b)
ATTACK    Replaced the Hungarian with the assignment LP (scipy.optimize.linprog/HiGHS on the
          totally-unimodular polytope, Σ_j x_ij ≤ 1, Σ_i x_ij = 1) — a different algorithm and
          a different optimality proof — and compared value *and* roster.  On small instances,
          brute force over every injective roster (itertools.permutations).
VERDICT   VERIFIED
BASIS     seed 3: LP 432.050719692444 = produced, roster identical (and equal to σ₀, so the
          matching gap is genuinely zero — the JSON's 5.68e-14 is summation noise, not
          premium).  seed 9: LP 450.312186781403 = produced (|Δ| 5.7e-14), roster identical,
          including R0004 which is *outside* S₁₃.  LP max fractionality 0.0 both draws.
          4 000 random instances × 2 roster modes: exact agreement with brute force.
ARTIFACT  docs/artifacts/U7-meas/oracle_ladder.py, oracle_toy_and_monotonicity.py
CAVEATS   The LP oracle is HiGHS-based, as `linear_sum_assignment` is not; both are scipy.
          An adversarial degenerate cost matrix could tie two optimal rosters — none seen here.
```

```
CLAIM     §3 P_S = Σ_z max_{i∈S₁₃} S_i(z) = 587.5485 (51.4268%) ↔ premium.py:121
          coverage_premium at staff = sorted(set(nash.values())) (premium.py:271)
ATTACK    Direct per-zip max over the 13 selected rows of an independently built S matrix.
          Then attacked the *definition* of S₁₃: is the Nash roster unique?  Forced every one
          of the 98 outside reps onto every one of the 13 districts and re-solved the matching
          (1 274 solves per draw), looking for an alternative optimum with a different S₁₃.
VERDICT   VERIFIED
BASIS     Oracle 587.548459129279 = produced, exactly, on both draws (both draws select the
          same 13).  Uniqueness: best outside-S₁₃ alternative loses 1.371e-2 nats (seed 3) and
          8.118e-3 nats (seed 9) — strictly worse, so S₁₃ is well defined here.
ARTIFACT  docs/artifacts/U7-meas/oracle_ladder.py, docs/artifacts/U7-meas/oracle_nash_ties.py
          .venv/bin/python3 docs/artifacts/U7-meas/oracle_nash_ties.py \
            instance_descaled.json.gz battery/results/sweep_20260902_s10/k13
CAVEATS   **The margin is thin on seed 9: 8.1e-3 nats is 1.6× the 5e-3 tier-2 floor.**  P_S,
          U4 and U8 are functions of the *set* S₁₃, and a Nash tie would make them
          tie-break-dependent; a 4 000-instance random search found 20 tied instances (trap 4:
          every rep with no book in a district values it identically).  Neither real draw is
          tied, but nothing in the code detects or reports a tie.
```

```
CLAIM     §3/§3.1 P₁₃ = max_{|S|=13} Σ_z max_{i∈S} S_i(z) = 598.0103 (52.3425%), staff
          R0009/R0012 in for R0017/R0018 ↔ premium.py:152 max_k_coverage
ATTACK    Three independent optimality proofs, none of them scipy.milp: (a) SCIP 6.2.1
          (pyscipopt) on the same formulation at limits/gap = limits/absgap = 0; (b) a
          solver-free depth-first branch and bound with the submodular top-marginals bound,
          seeded by an independently written greedy; (c) exhaustive enumeration on small
          instances.  The B&B was itself self-tested against exhaustive enumeration on 200
          random matrices (200/200 agree).
VERDICT   VERIFIED
BASIS     SCIP 598.0103106411004 = produced, same staff set; B&B 598.0103106411 (1 375 nodes,
          0.1 s), same set; independent greedy 598.0103106411004 — greedy attains the optimum,
          so the (1−1/e) bound is not binding here.  The set is
          {R0000,R0001,R0002,R0003,R0005,R0006,R0007,R0008,**R0009**,R0010,**R0012**,R0013,R0014};
          S₁₃ has R0017/R0018 where this has R0009/R0012.  598.0103 > 587.5485 = P_S, i.e. the
          claimed 13 is strictly better than the staffed 13 (gap 10.4619 book).
ARTIFACT  docs/artifacts/U7-meas/oracle_ladder.py (SCIP),
          docs/artifacts/U7-meas/oracle_p13_bnb.py
          .venv/bin/python3 docs/artifacts/U7-meas/oracle_p13_bnb.py instance_descaled.json.gz 13
CAVEATS   All three oracles read the same S matrix; a defect in the export would fool all of
          them.  Optimality is over staff sets only — P₁₃ ignores balance by construction,
          exactly as §2 says.
```

```
CLAIM     §3 P_free = Σ_z max_{i∈R} S_i(z) = 907.6440 (79.4440%) ↔ premium.py:276
ATTACK    Direct column max over the full 111×1229 matrix; also the toy, where the answer is
          10+6+8+9 = 33 by hand.
VERDICT   VERIFIED
BASIS     Oracle 907.644027467863 = produced exactly; share 0.7944397840555556.  Toy 33.0 and
          82.5%, matching §4.
ARTIFACT  docs/artifacts/U7-meas/oracle_ladder.py, oracle_toy_and_monotonicity.py
CAVEATS   None beyond the shared input file.
```

```
CLAIM     §3 the ladder P₀ ≤ P*(A) ≤ P_S ≤ P₁₃ ≤ P_free holds
ATTACK    Tried to break the second inequality specifically: §3 calls each step "a
          restriction", but P*(A) is a Hungarian over **all 111 reps** while P_S is a ceiling
          over the 13 selected ones, so the chain is not a restriction chain — the seed-9
          P*(A) roster does in fact use R0004 ∉ S₁₃.  Searched 4 000 random instances
          (3–5 reps, 3–7 zips, k = 2–4) × 2 roster modes (Nash, hand override) for a
          violation, with every rung cross-checked against brute force.
VERDICT   VERIFIED
BASIS     0 monotonicity violations in 8 000 evaluations; both real draws monotone.  The
          mechanism is an exchange argument on the Nash matching, not §3's "restriction":
          optimality of σ₀ implies b_{c,j} ≤ b_{σ₀(j),j} for every unmatched c and every j, so
          each column max of b is attained inside S₁₃ and P*(A) ≤ Σ_j max_{i∈S₁₃} b_ij ≤ P_S.
          Verified directly on both real draws: 0 of 98×13 unmatched (rep, district) pairs beat
          the assigned rep; the column max is attained inside S₁₃ in all 13 columns.
ARTIFACT  docs/artifacts/U7-meas/oracle_toy_and_monotonicity.py
          .venv/bin/python3 docs/artifacts/U7-meas/oracle_toy_and_monotonicity.py
CAVEATS   §3's stated justification for `P*(A) ≤ P_S` is wrong as written (it is not a
          restriction); the inequality is true for a different reason, and only because S₁₃ is
          the *Nash* image — see the REFUTED row on §3/§4's `S₁₃ = im σ₀`.  The search is
          randomized, not a proof; the exchange argument above is the proof.
```

```
CLAIM     §3.1 MILP: y binary, w_zi ∈ [0,1] on S_i(z) > 0 pairs, Σ_i w_zi ≤ 1, w_zi ≤ y_i,
          Σ y_i = 13, mip_rel_gap = 0.0 (trap 12); a non-optimal stop is no bound (trap 15)
          ↔ premium.py:152-191
ATTACK    Read the constraint matrices against §3.1 term by term; confirmed the pair set is
          exactly {(z,i) : S_i(z) > 0} (1 891 pairs on the real instance — §3.1 says "a few
          thousand"); confirmed no time_limit is passed and that the value returned is a
          *re-evaluation* of the chosen staff, not −res.fun; drove the non-optimal branch by
          making the head-count constraint infeasible.
VERDICT   VERIFIED
BASIS     `options=dict(mip_rel_gap=0.0)` at premium.py:183; SCIP at gap 0 returns the same
          optimum, so the tolerance is not hiding a gap.  Infeasible probe:
          max_k_coverage(S, ["A","B"], 3) → Coverage(value=None, status='infeasible',
          staff=None, greedy_value=3.0).  Payload probe with max_k_coverage monkeypatched to
          return status='limit': ladder.P13 = {"book": null, "share": null}, gaps.roster =
          null, P13_solve = {"status": "limit", "staff": null, "greedy_book": 28.0, …} —
          greedy stays in its own field and is never promoted to P₁₃.
ARTIFACT  docs/artifacts/U7-meas/oracle_boundaries.py
          .venv/bin/python3 docs/artifacts/U7-meas/oracle_boundaries.py
CAVEATS   A true `time_limit` stop was not induced (no limit is ever set, so the status can
          only arise from node limits or numerics); the branch is shared with `infeasible`,
          which was exercised.
```

```
CLAIM     §3.1 "The greedy (1 − 1/e) solution **seeds** it and is reported alongside"
          ↔ premium.py:160 greedy_staff / :179 milp
VERDICT   REFUTED  (defect in the model text; no numerical consequence)
ATTACK    Looked for the warm start.  `greedy_staff` is called at premium.py:160 and its result
          flows only into the returned `Coverage.greedy_value/greedy_staff`; nothing is passed
          to `milp`.  `scipy.optimize.milp`'s supported options are
          {disp, presolve, time_limit, node_limit, mip_rel_gap} — there is no initial-solution
          argument, so the spec's method is not implementable through this call.
BASIS     `inspect.signature(scipy.optimize.milp)` = (c, *, integrality, bounds, constraints,
          options); `scipy.optimize._milp._milp_iv` rejects any other option key.  grep for
          "greedy" in premium.py shows uses at 129/148/149/160/161/163/186/191/312-315/438 —
          all reporting, none feeding the solve.
ARTIFACT  .venv/bin/python3 -c "from scipy.optimize import milp; import inspect;
          print(inspect.signature(milp))"; grep -n greedy tools/measure/premium.py
CAVEATS   Harmless here: the MILP proves optimality unaided and greedy happens to attain it
          (598.0103106411004 both ways).  Fix is one line of §3.1 ("is computed and reported
          alongside as a lower bound"), not a code change.
```

```
CLAIM     §4 worked example: ladder 24 ≤ 28 ≤ 28 ≤ 28 ≤ 33, P*(A) roster (A, C), shares
          60% / 82.5%, g = [[22.82,16.10],[17.78,19.46],[16.10,21.14]], stage 2 picks (A, C)
          with V = 6.1788 ↔ tests/test_measure.py::test_toy_ladder and friends
ATTACK    Rebuilt the example from the §4 table by hand, enumerated every roster and every
          2-subset, and computed g from the definition — all without importing premium.py —
          then compared with premium.measure(sigma={"D1":"A","D2":"B"}).
VERDICT   VERIFIED
BASIS     Brute force gives b = [[16,0],[4,8],[0,12]]; rungs [24, 28, 28, 28, 33]; P*(A) roster
          {D1:A, D2:C}; Nash roster {D1:A, D2:C} with V = 6.1788; shares 0.60 and 0.825;
          g exactly [[22.82,16.10],[17.78,19.46],[16.10,21.14]] with g − 0.42·b = 16.10
          everywhere.  premium.measure agrees on every one.
ARTIFACT  docs/artifacts/U7-meas/oracle_toy_and_monotonicity.py (section 1)
CAVEATS   The example is 4 zips / 3 reps; it pins the definitions, not the scale behaviour.
```

```
CLAIM     §3 "selected staff S₁₃ = im σ₀" together with §4's use of a hand roster as σ₀
          ↔ premium.py:271 staff = sorted(set(nash.values())) — always the Nash image, even
          when `sigma` overrides σ₀ for P₀, V and U1
VERDICT   REFUTED  (the model text is internally inconsistent; the code implements the only
          coherent reading, and both real runs are unaffected because σ₀ = σ_nash there)
ATTACK    Applied §3's definition literally to §4's own instance.  §4 declares the hand roster
          D1→A, D2→B to be "the committed σ₀", so `im σ₀ = {A, B}` and the literal §3 reading
          gives P_S = 24; §4 then reports P_S = 28 at {A, C} = im σ_nash and relegates the
          literal reading to a parenthesis.  The two cannot both hold.
BASIS     Concrete failing input: the §4 toy with sigma={"D1":"A","D2":"B"}.  Literal §3
          reading → ladder [24, 28, **24**, 28, 33], which *violates* §3's own
          P*(A) ≤ P_S at 28 > 24.  Code (Nash image) → [24, 28, 28, 28, 33] = §4's pinned
          numbers and a monotone ladder.  The exchange argument in row 7 needs S₁₃ = im σ_nash
          precisely; with S₁₃ = im σ_hand it fails.
ARTIFACT  docs/artifacts/U7-meas/oracle_toy_and_monotonicity.py (toy_check), and
          `premium.measure(..., sigma={"D1":"A","D2":"B"})` in oracle_boundaries.py
CAVEATS   No effect on either published run: `sigma0 == sigma_nash` in both JSONs, so P_S, U4
          and U8 are the same under either reading.  Recommended model fix: §3 should read
          "S₁₃ = im σ_nash, the model's own stage-2 roster, whatever roster σ₀ is being
          scored", and §4 should say so where it introduces the hand roster.  The code already
          documents this at premium.py:238-241.
```

```
CLAIM     §5 U1: min/max/(max−min)/mean of the realised gains beside the same three on M(A_j)
          ↔ premium.py:212 spread on gains (:285) and M_district (:288)
ATTACK    Recomputed the 13 realised gains from the hand-built g (definition, not
          channel.gain_matrix) at the recorded roster, and M(A_j) by summing M over each
          district from the raw instance.
VERDICT   VERIFIED
BASIS     seed 3: gains min 81.86867978033479, max 143.79116450478435, mean
          102.09749455733724, spread 0.606503469972 (produced: identical to 2.2e-16); M spread
          0.007812614473 (= FRAME §6's 0.781%).  seed 9: gain spread 0.594735816016, M spread
          0.008360651445.  The A0 soft kill fires: 60.7% vs 0.78%, two orders of magnitude.
ARTIFACT  docs/artifacts/U7-meas/oracle_ladder.py
CAVEATS   U1's M-spread and `balance.spread_rel` differ in the last 2 ulp (different summation
          order through channel.district_opportunity); irrelevant at 1e-16.
```

```
CLAIM     §5 U4 = 83 zips, 6.1209% of M — "#{z : |cand(z) ∩ S₁₃| ≥ 2}" ↔ premium.py:292
ATTACK    Counted directly from the raw export's share dicts (cand(z) = keys with share > 0),
          intersected with the 13 selected reps — no model.candidates, no networkx.
VERDICT   VERIFIED
BASIS     Oracle 83 zips, ΣM = 168.057197, share 0.06120939402283135; produced identical
          (exact).  Matches §5's read-only probe (83 of 675 contested, 6.12%).  675 contested
          confirmed independently by the loader summary and the export's meta
          (`zips_contested: 675`).
ARTIFACT  docs/artifacts/U7-meas/oracle_ladder.py
CAVEATS   Depends on S₁₃ — see the tie caveat in the P_S row.  Both draws give the same 83
          because both select the same 13.
```

```
CLAIM     §5 U8: pooled corr(T_z, M_z) and per-rep corr(S_i(z), M_z) over zips with S_i(z) > 0
          ↔ premium.py:195 pearson, :296-300, :328
ATTACK    Recomputed with numpy.corrcoef on independently built T, M and per-rep rows,
          restricted to the same held-zip masks.
VERDICT   VERIFIED
BASIS     Pooled 0.6499792475446389 = produced exactly; all 13 per-rep values match exactly
          (e.g. R0000 0.9317659784306184, R0017 0.22736739100406947).
ARTIFACT  docs/artifacts/U7-meas/oracle_ladder.py
CAVEATS   `pearson` returns None on < 2 points or zero variance; no real rep hit that branch.
```

```
CLAIM     §5/§2 V at σ₀ and V rescored at the P*(A) roster ↔ premium.py:204 roster_value,
          :322-323, and the CLI's assertion against metrics.json winner.stage2_value
ATTACK    Recomputed Σ log g from the hand-built g at both rosters; separately compared with
          each draw's recorded stage2_value, and with FRAME §0's "+0.103 nats" claim for
          seed 9 over seed 3.
VERDICT   VERIFIED
BASIS     seed 3: V(σ₀) = V(P*(A)) = 59.937469798433 (same roster), recorded 59.93746979843285.
          seed 9: V(σ₀) = 60.040099444093 vs recorded 60.040099444093315 (|Δ| 5e-15, well
          inside the CLI's 1e-9 gate), V(P*(A)) = 60.031981202356 — the premium-optimal relabel
          *costs* 0.0081 nats of Nash value, which is §2's balance-cost point.  Seed-9 minus
          seed-3 V = 0.10262964566, reproducing FRAME §0's +0.103 nats.
ARTIFACT  docs/artifacts/U7-meas/oracle_ladder.py
CAVEATS   The V assertion pins map+roster+parameters against the recorded run, and is the real
          proof that this `instance_descaled.json.gz` is the file the draws were made from
          (metrics.json records a path in the `national-channel` worktree).  It does *not*
          assert σ₀ is Nash-optimal — by design, so a U10 baseline roster can be scored.
```

```
CLAIM     §6 ΔP → nats through w·ΔP/ḡ with ḡ the mean realised gain, `small` iff ≤ 5e-3
          ↔ premium.py:221 gap, SMALL_NATS = 5e-3
ATTACK    Redid the arithmetic outside the code and checked each flag against the threshold,
          including the direction of the inequality (≤, not <) and the ḡ used (mean at σ₀, not
          at the compared roster).
VERDICT   VERIFIED
BASIS     seed 3: 0.42·155.497739436835/102.09749455733724 = 0.6396733910722323 (map, LARGE);
          0.42·10.46185151182135/102.097494557337 = 0.04303707602244186 (roster, LARGE);
          match 2.34e-16 (small).  seed 9: match 0.42·1.5787862393725618/102.63647347709312 =
          0.006460570965393384 → LARGE, i.e. the seed-9 matching gap is 1.29× the floor.  All
          reproduced to ≤ 8.7e-19.  Verdict per §6: not all three small ⇒ A1 stays `running`,
          and the largest gap is the **map** (0.64 nats, 13.6% of book) on both draws.
ARTIFACT  docs/artifacts/U7-meas/oracle_ladder.py; arithmetic rerun in the report's shell log
CAVEATS   §6 itself calls this a first-order conversion, not a certificate; nothing here
          validates the first-order step.  The script emits the three flags but no explicit
          `verdict` field — the §6 reading is left to the human, which matches "record
          `abandoned` in APPROACHES.md" being a human action.
```

```
CLAIM     §7 provenance and the brief's acceptance: run id + instance hash on every number,
          both k=13 draws, byte-identical re-run, stop rule on data defects
          ↔ premium.py:373 main, :419-430 payload
ATTACK    Re-ran the CLI for both draws into a scratch directory and diffed against the
          committed outputs; recomputed both sha256s with `shasum -a 256`; ran the
          `--sigma-nash` branch as well; checked the draws' metrics.json parameters against the
          CLI defaults; audited the instance for FRAME §5 defects that could bite.
VERDICT   VERIFIED
BASIS     `diff <(grep -v '"written"' rerun.json) <(grep -v '"written"' committed.json)` empty
          for both draws.  instance_sha256 cf7d66c0…45a522 and draw_sha256 6614e665…a3e334 /
          2466f119…13b220 match `shasum -a 256`.  `--sigma-nash` output identical apart from
          `sigma_source`/`sigma_from_metrics`.  metrics.json records θ=0.4, λ=0.3,
          filler_capture="theta" for both draws = the CLI defaults used.  Data defects: the 6
          coordinate-less zips (1 223 of 1 229 with coordinates) touch no U7 number — nothing
          here is geometric; the 6-significant-figure rounding shows up as 69 zips missing the
          headroom condition M_z ≥ max_i(S_i + θ(T_z − S_i) + θ·S_free) by a factor
          1.0000006, i.e. rounding only.  Nothing blocked a number, so the stop rule does not
          fire.
ARTIFACT  /tmp/u7v_rerun (rerun outputs and log); commands recorded in the summary above
CAVEATS   The re-run was on the same machine, same wheels; byte-identity across platforms is
          untested.  The script performs no data-defect audit of its own — if a future
          instance did violate headroom materially, nothing in premium.py would notice.
```

```
CLAIM     Degenerate and boundary inputs behave (spec domain: a partition into k ≤ |R|
          districts, σ injective into R)
ATTACK    k = 1; k = |R|; all books zero; exact ties between two reps; filler book with
          filler_capture="full"; empty map; non-injective roster; roster missing a district;
          roster naming a rep outside R; unknown filler_capture; k > |R|; max_k_coverage at
          k = 0 and at k > n_reps.
VERDICT   VERIFIED
BASIS     k=1 → [16,16,16,16,33] with S₁₃ = {A} (monotone, and P₀ = P*(A) = P_S = P₁₃ as it
          must be at k=1); k=|R|=3 → [26,26,33,33,33] with P_S = P_free; zero books → all
          rungs 0, gaps 0 nats, small=True, no division by zero; ties → all rungs 10;
          filler "full" → [28,28,28,28,33]; empty map → all rungs 0.0, no crash; the three
          bad rosters raise ValueError with the offending districts/reps named; unknown
          filler_capture raises ValueError from the model layer; k=0 → Coverage(0.0,
          "optimal", ()).
ARTIFACT  docs/artifacts/U7-meas/oracle_boundaries.py
CAVEATS   **Outside the spec's domain**: k > |R| (more districts than reps holding book) fails
          with a bare `KeyError: 'D2'` at premium.py:285 rather than a named error, because
          `channel.stage2` returns a partial roster.  Not reachable from the CLI on this
          instance (k=13 ≪ 111) and not a spec case, but a one-line guard would make it a
          clean message.
```

## Findings for the model author

1. **§3/§4 `S₁₃`** — say once, in §3, that `S₁₃` is the image of the model's own stage-2 (Nash)
   roster regardless of which roster is being scored, and drop the phrase that makes a hand
   roster the σ₀ whose image is taken.  Otherwise §4's `P_S = 28` and the ladder contradict §3.
2. **§3 "each inequality is a restriction"** — true for `P₀ ≤ P*(A)`, `P_S ≤ P₁₃`, `P₁₃ ≤ P_free`,
   false as stated for `P*(A) ≤ P_S`: `P*(A)` ranges over all 111 reps and the seed-9 optimum
   really does use R0004 ∉ S₁₃.  The inequality still holds, by the exchange argument on the
   Nash matching (row 7); one sentence would make it a proof instead of an assertion.
3. **§3.1 "seeds it"** — scipy cannot warm-start; say "computed and reported alongside as a
   lower bound".
4. **Ties in `S₁₃`** — worth one line in §3: `S₁₃` is unique only when the Nash matching has a
   strict optimum, which it does on both draws by 1.4e-2 and 8.1e-3 nats, the latter only 1.6×
   the tier-2 floor.  A tie would make `P_S`, U4 and U8 tie-break-dependent.

## Reproduction

```
cd /Users/ntlee/projects/td/.claude/worktrees/A1
P=/Users/ntlee/projects/td/.venv/bin/python3
$P docs/artifacts/U7-meas/oracle_ladder.py instance_descaled.json.gz \
    battery/results/draw_k13_20260901 battery/results/meas_20260903/draw_k13_20260901.json
$P docs/artifacts/U7-meas/oracle_ladder.py instance_descaled.json.gz \
    battery/results/sweep_20260902_s10/k13 battery/results/meas_20260903/sweep_20260902_s10.json
$P docs/artifacts/U7-meas/oracle_p13_bnb.py instance_descaled.json.gz 13
$P docs/artifacts/U7-meas/oracle_nash_ties.py instance_descaled.json.gz battery/results/draw_k13_20260901
$P docs/artifacts/U7-meas/oracle_toy_and_monotonicity.py      # ~30 s
$P docs/artifacts/U7-meas/oracle_boundaries.py
$P tests/run_all.py
uvx pyright --pythonpath $P tools/measure/premium.py tools/measure/__init__.py tests/test_measure.py
```
