# CODEVERIFY U8-band — adversarial verification of `td/solvers/eg_band.py`, `tools/measure/frontier.py`

**Date:** 2026-09-04 · **Worktree:** `.claude/worktrees/A1` (`wt/A1`, landing `69997ac`) ·
**Verifier:** `code-verify` · **Spec:** `docs/MODEL_U8-band.md` · **Brief:**
`docs/tracks/A1/units/U8-band.md` · **Interpreter:** `/Users/ntlee/projects/td/.venv/bin/python3`
(CPython 3.13.15; numpy 2.5.2, scipy 1.18.1, highspy 1.15.1, pyscipopt 6.2.1, matplotlib 3.11.1)

## 0. Summary

**20 rows: 18 VERIFIED, 2 REFUTED, 0 INCONCLUSIVE.**
**Type check:** `uvx pyright --pythonpath …/.venv/bin/python3 td/solvers/eg_band.py
tools/measure/frontier.py tests/test_eg_band.py` → **0 errors, 0 warnings** (pyright 1.1.411;
without `--pythonpath` it reports 9 spurious `reportMissingImports`).
**Tests:** `tests/run_all.py` → **208 passed, 0 failed, 0 skipped** in 6.3 s (184 pre-existing + 24
new); `tests/test_eg_band.py` reads no gitignored input.
**Anchors:** `figures/u8_band/frontier.png` re-generated **byte-identically**
(sha256 `c9d377793e1f6d7969681464ca919ab0b9562e7e74167388e9199c66d49f49e4`) by two fresh full runs;
`figures/` was clean in `git status` before the runs, so the check is valid.
**D1′ "NOT SOFT" stands**, and stands on a certified *lower* bound, not on the slope.

| # | row | verdict |
|---|---|---|
| 1 | §1 program `EG^bal_S(δ)` ↔ `solve_band` / `band_rhs` | VERIFIED |
| 2 | §1 unmasked utility convention ↔ `frontier.utility_matrix`, `frontier.gate` | VERIFIED |
| 3 | §1 hard gate `EG_{S₁₃} = 60.6974156139` ↔ `gate()` | VERIFIED |
| 4 | §2 dual `D(p, μ)` ↔ `eg_band_dual_bound` | VERIFIED |
| 5 | §2 solver-free `O(nk)` check ↔ `check_dual` | VERIFIED |
| 6 | §2 modified budget identity ↔ `check_dual.budget_residual` | VERIFIED |
| 7 | §2 gauge pinning / `q` as the primary price ↔ `BandDuals.prices`, `vertex_report` | VERIFIED |
| 8 | §2 cleaning + split cap `k−1+t ≤ 2k−1` ↔ `clean_vertex`, `vertex_report` | VERIFIED |
| 9 | §3 supergradient `s_min = (T/k)Σ|ν_i|` ↔ `BandSolution.slope`, `curve_bound` | VERIFIED |
| 10 | §4 D1′ certificate + §10.A guard ↔ `frontier.softness` | VERIFIED |
| 11 | §4 integral witness (non-empty feasible set) ↔ `evaluate` | VERIFIED |
| 12 | §5.1 OA safety property (upper bound at every iteration) ↔ `solve_band` | VERIFIED |
| 13 | §5.1 `ĝ > 0` at every iterate "guaranteed by P5.3" ↔ `solve_band` pool check | **REFUTED** |
| 14 | §5.1 stall floor = LP feasibility tolerance ↔ `_solve_master` ladder | VERIFIED |
| 15 | §5.2 SCIP cross-check ↔ `solve_scip` | VERIFIED |
| 16 | §6 grid, `δ₀` as max deviation ↔ `build_setting.delta0`, `GRID` | VERIFIED |
| 17 | §7/§9.6 first movers, P2.5 vs the published ratio ↔ `good_side_scores`, `first_movers` | VERIFIED |
| 18 | §9.4 N8 band duals / §9.5 N9 proportionality ↔ `Point.nu`, `Point.prop_gap` | VERIFIED |
| 19 | §9.3 `δ*` ↔ `bisect_delta_star` | VERIFIED |
| 20 | §1 "the masked bound lands ≈ 27 nats" ↔ `MODEL_U8-band.md:47`, `frontier.py:13` | **REFUTED** |

Acceptance criteria **1–6 all PASS** (§3 below; #4 with a noted deviation from the brief's two
anticipated answers, which the unit records and justifies).

## 1. Mapping table (model object → code symbol → the number it must reproduce)

| model | code | number |
|---|---|---|
| §1 program | `eg_band.py:414 solve_band`, `:225 band_rhs`, `:381 _tangent_rows` | §9.1 five brackets |
| §1 `u_i(z)` unmasked | `frontier.py:177 utility_matrix` | 96.75 % entries differ, 13.4× mass |
| §1 hard gate | `frontier.py:230 gate` | `60.6974156139 ± 1e-6` |
| §2 `q_{zi}` | `eg_band.py:92 BandDuals.prices` | §9.4 `q` ranges |
| §2 `D(p, μ±)` | `eg_band.py:231 eg_band_dual_bound` | `dual_check.bound` per point |
| §2 `viol` / `cs` | `eg_band.py:254 check_dual` | `−1.33e-5` / `1.33e-5` rel |
| §2 budget identity | `eg_band.py:274` | `budget_residual ≈ 5.0e-5` |
| §2 cleaning, rank | `eg_band.py:294 clean_vertex`, `:307 vertex_report` | splits 19/20/16/16/10, `t` 12/11/10/8/0 |
| §3 `s_min` | `eg_band.py:182 slope`, `:197 curve_bound` | `0.5609/0.4942/0.3710/0.2663/0` |
| §4 D1′ | `frontier.py:287 softness`, `:134 Softness` | gaps `0.69198/0.70880/0.73685` |
| §4 §10.A guard | `frontier.py:299 tangent_valid`, `:589 raise` | slack `+5.80e-4/+4.67e-3/+1.66e-2` |
| §4 witness | `frontier.py:270-272` | `integral_witness_in_band: true` ×5 |
| §5.1 OA | `eg_band.py:479-509` | tangents 15/23/35/44/57 |
| §5.1 polish | `eg_band.py:510-531 P5.4` | `polish_delta ≤ 0` |
| §5.2 SCIP | `eg_band.py:547 solve_scip` | `60.6288653576`, `60.6974156182` |
| §6 `δ₀` | `frontier.py:225 delta0` | `0.0039460106`, spread `0.0078126145` |
| §7 movers | `eg_band.py:354/362`, `frontier.py:347` | 75 ties, 2.90 % of `T`; top-25 0.83 % |
| §9.4 N8 | `frontier.py:278-279`, `Point.nu` | 6/6/1 at `δ₀`; all `ν=0` at 0.33 |
| §9.5 N9 | `frontier.py:280 prop_gap` | `+9.0899 … +13.3569`; delivered `−7.1351` |
| §9.3 `δ*` | `frontier.py:303 bisect_delta_star` | `δ* ≤ δ₀`, 0 solves |
| §7 provenance | `frontier.py:417 _jsonable`, `:630 payload` | byte-identical re-run |

## 2. The rows

```
CLAIM     MODEL §1's program EG^bal_S(δ) ↔ eg_band.py:414 solve_band / :225 band_rhs
ATTACK    Wrote the program out again from the MODEL text and solved it with a different
          algorithm and a different implementation (scipy SLSQP, 40 multi-starts, constraints
          coded straight from §1) plus an exhaustive fractional-simplex grid written from
          scratch, on the MODEL_U7-meas toy at k=2 and k=3, at δ ∈ {0, .02, .05, .10, .33, .9,
          None}.  Also fed the solver a zero-M zip, two identical agents, k=1, n=1, a mis-shaped
          M, a zero utility entry and a negative δ.
VERDICT   VERIFIED
BASIS     Numeric-equality tier.  k=2: OA and SLSQP and the grid all give 6.1788043249 at every
          δ (|OA − SLSQP| ≤ 8.9e-16).  k=3: OA − SLSQP ∈ [−3.6e-15, +6.2e-9] at all seven δ, and
          OA.upper ≥ grid lower bound everywhere.  The toy's delivered value 6.178804 reproduces
          MODEL_U7-meas §4's pinned V = 6.1788.  Degenerate inputs: k=1 exact (log ΣU), zero-M
          zip agrees with SLSQP to 5.9e-9, ties agree to 2.4e-9 and break deterministically by
          lowest agent index, mis-shaped M and u ≤ 0 raise ValueError, δ<0 raises RuntimeError
          (an infeasible LP is never returned as a bound).
ARTIFACT  /tmp/u8verify/oracle_toy.py, /tmp/u8verify/attack_edges.py
CAVEATS   SLSQP is a local method; it is an oracle here only because the program is concave over
          a convex set.  n=1 with k=2 does not converge (bracket 1.4e-4, reported honestly as
          "stalled", never as a bound) — outside the unit's scope but worth knowing.
```

```
CLAIM     MODEL §1's unmasked utility convention ↔ frontier.py:177 utility_matrix
ATTACK    Rebuilt U for the real 1229×13 instance from the raw `instance_descaled.json.gz`
          columns (`m_rel`, `share`, `share_free`) with the model formula written out by hand,
          bypassing td/model.py, td/channel.py and td/instance.py entirely; then compared with
          the masked form and tried to make the gate accept the masked matrix.
VERDICT   VERIFIED
BASIS     max |U_hand − U_code| = 1.11e-16 over 15,977 entries; M identical to the last bit;
          node order identical.  On the toy, U summed over a district equals channel.gain_matrix
          exactly (the scoring convention).  Masked vs unmasked: 96.7453 % of entries differ
          (MODEL says 96.75 %), total mass ratio 13.439× (MODEL says 13.4×).  Feeding the masked
          matrix to `gate()` raises, as designed.
ARTIFACT  /tmp/u8verify/oracle_real.py, /tmp/u8verify/attack_masked.py
CAVEATS   —
```

```
CLAIM     MODEL §9.0's gate: EG_{S₁₃} = 60.6974156139 reproduced to 6.11e-9 ↔ frontier.py:230
ATTACK    Recomputed the unconstrained Eisenberg–Gale value by **proportional response dynamics**
          (Fisher-market PR, budgets 1) — no LP, no solver, no shared code with eg_band — with
          its own closed-form dual for an upper bound.
VERDICT   VERIFIED
BASIS     Numeric-equality tier.  PR: primal 60.69741561378444, dual 60.69741563095106
          (bracket 1.7e-8) in 31,907 iterations; the published anchor 60.6974156139 sits
          1.16e-10 above the PR primal and inside the PR bracket.  The unit's gate bracket
          [60.697415611321, 60.697415620014] overlaps it; |upper − anchor| = 6.11e-9 as reported.
ARTIFACT  /tmp/u8verify/oracle_real.py
CAVEATS   PR is a first-order method; its bracket (1.7e-8) is looser than the OA's (8.7e-9), so
          it confirms the anchor to ~1e-8, not to 1e-12.
```

```
CLAIM     MODEL §2's dual D(p, μ⁺, μ⁻) ↔ eg_band.py:231 eg_band_dual_bound
ATTACK    Re-derived the Lagrangian by hand (eliminate x ≥ 0: sup_x [log(u·x) − q·x] = log
          max_z(u_z/q_z) − 1), wrote D out in an independent function, and evaluated it on the
          *manifest's* published p and ν at all five grid points — no solver of any kind in that
          path.  Then attacked the guards: μ < 0, q ≤ 0, μ ≠ 0 with δ=None.
VERDICT   VERIFIED
BASIS     D_hand equals the manifest's `dual_check.bound` **bit for bit** at all five δ
          (60.62044080416445 / 60.62886535430431 / 60.64160128275832 / 60.65772534424423 /
          60.697415614302656), with min q > 0 and min μ = 0 verified in the same script.  Weak
          duality then makes each a valid upper bound independently of HiGHS.  μ<0 → inf,
          q ≤ 0 → inf, μ≠0 at δ=None → ValueError.
ARTIFACT  /tmp/u8verify/oracle_real.py, /tmp/u8verify/attack_dualres.py
CAVEATS   The bit-identity is because I deliberately used the same fsum ordering; the
          *derivation* is independent, the arithmetic is not maximally so.
```

```
CLAIM     MODEL §2's solver-free O(nk) check, and whether `dual_violation_rel ≈ −1.33e-5` is a
          tolerance leak ↔ eg_band.py:254 check_dual
ATTACK    (a) Recomputed the whole certificate at every grid point from the solver's *outputs*
          only: audited X for x ≥ 0, Σ_i x_zi = 1 and band feasibility myself → a lower bound;
          computed D myself → an upper bound.  (b) Measured how the reduced-cost residual scales
          with the objective bracket on a random 60×5 instance across eight tolerance rungs.
          (c) Tried to make the check certify a dual that is not feasible.
VERDICT   VERIFIED
BASIS     (a) Certified brackets, entirely mine: 2.801e-9 / 1.282e-9 / 1.720e-9 / 1.226e-9 /
          5.379e-9 nats — all tier 1 — with max |Σ_i x − 1| = 0 and band excursions ≤ 2.3e-13 on
          a span of ~212–281.  So the five §9.1 values hold without trusting HiGHS's status.
          (b) |viol|/√bracket stays in [0.09, 0.38] across five decades while cs_rel and
          budget_residual fall like √bracket (bracket 6.6e-6 → cs 6.8e-4; bracket 4.0e-10 → cs
          6.7e-6).  So ~1e-5 at a ~3e-9 bracket is the √bracket law for a first-order condition,
          not a leaked tolerance; and it cannot invalidate the bound, because D needs only μ ≥ 0
          and q > 0, both checked directly.  (c) Shifting μ by −1e-13 gives `feasible=True` with
          `bound=inf`; a finite bound is never returned with any μ < 0, and
          `Point.certified_upper` guards on `isfinite`, so no reported number can come from an
          infeasible dual.
ARTIFACT  /tmp/u8verify/certify_points.py, /tmp/u8verify/attack_scaling.py,
          /tmp/u8verify/attack_dualres.py
CAVEATS   Cosmetic defect: `DualCheck.feasible` can be True while `bound` is inf (its docstring
          says feasible "is what makes bound a bound" — inf is a bound, so nothing is false, but
          the flag is looser than the bound's own guard).  Not reachable from the CLI, which
          clips μ at 0 (eg_band.py:489).  Contrast with centers.py:372-377: there `viol` is
          −5e-17 because a transportation LP's duals are an exact vertex; here the residual is
          O(√bracket) because q is compared against 1/g of an outer-approximated log.  The two
          are not comparable magnitudes and the MODEL's use of centers.py "in that style" refers
          to the reporting shape, which does match.
```

```
CLAIM     MODEL §2's modified budget identity Σ_z p_z = k − Σ_i ν_i m_i ↔ eg_band.py:274
ATTACK    Evaluated both sides in aggregate form from the manifest's p, ν and m — a different
          contraction from the per-agent residual the code reports.
VERDICT   VERIFIED
BASIS     Residuals +/−: −8.9e-6, +2.0e-5, +2.9e-5, +2.4e-5, +1.0e-4 at the five δ, against
          Σ_z p_z ≈ 13.0–13.5 — i.e. ~1e-6 relative, the same first-order accuracy as the KKT
          residual and consistent with the manifest's per-agent `budget_residual` (2.7e-5–8.4e-5).
          At δ = 0.33, ν ≡ 0 and Σ_z p_z = 13.00010 against k = 13.
ARTIFACT  /tmp/u8verify/attack_dualres.py
CAVEATS   The identity is reported as a residual, never assumed, exactly as MODEL §2 says.
```

```
CLAIM     MODEL §2's gauge pinning (U9 P2b) and q as the primary price ↔ eg_band.py:92, :343-347
ATTACK    Checked that at every δ at least one agent is strictly slack on both bands and that
          its ν is exactly 0; and re-derived q from the manifest's p and ν myself.
VERDICT   VERIFIED
BASIS     `n_agents_band_slack` = 1/2/3/5/13 at δ = δ₀/.02/.05/.10/.33, `gauge_pinned: true`
          everywhere, and the slack agent's ν is 0.0 exactly (at δ₀ that is index 10 = R0008,
          which §9.4 names).  My q reproduces the manifest's q_min/q_max to the last printed
          digit (1.626649e-05 … 2.209911e-01 at δ₀).  U9's P2b failure mode — an unpinned gauge
          overstating Σ|ν| — therefore cannot arise here.
ARTIFACT  /tmp/u8verify/oracle_real.py
CAVEATS   Pinning fixes the *gauge*; it does not fix the combinatorial non-uniqueness of the dual
          vertex, which is real here (see Finding F2).
```

```
CLAIM     MODEL §2's clean-then-count and the split cap k−1+t ≤ 2k−1 = 25 ↔ eg_band.py:294, :307
ATTACK    Re-implemented the whole audit — clean at 1e-6, renormalise, count support and splits,
          identify tight bands, build the (supply | tight band | gain) matrix on the support and
          take its rank — in a separate script, at all five δ.
VERDICT   VERIFIED
BASIS     Support and rank reproduce exactly at δ₀/.02/.05/.33 (1248/1249/1247/1240, rank =
          support at all of them, so each is a vertex of the optimal face); splits ≤ k−1+t and
          ≤ 25 hold in every reconstruction.  Raw and cleaned split counts are identical in the
          manifest (no phantom splits), and cleaning moved g by ≤ 1.3e-11 and no mass out of band.
ARTIFACT  /tmp/u8verify/attack_vertex.py
CAVEATS   The *values* of splits and t are not invariants — see Finding F2: a 1e-16 perturbation
          of U moves splits by ±1 and t by 1 at some δ.  The cap holds in every case observed.
```

```
CLAIM     MODEL §3's s_min = (T/k)Σ_i|ν_i| is a supergradient; §9.1's five values ↔
          eg_band.py:182 slope, :197 curve_bound
ATTACK    Three independent attacks.  (a) Numerical differentiation: solved φ at 17 δ' values
          including six BELOW δ₀ — the direction the unit never tests, and the one that catches
          an s_min that is too LARGE.  (b) Secant squeeze: concavity gives slope(a,δ₀) ≥ φ'(δ₀−)
          ≥ φ'(δ₀+) ≥ slope(δ₀,b), so a two-sided secant brackets the whole superdifferential.
          (c) Reproducibility: re-solved with the code's U and with my hand-built U (differing
          in 37 of 15,977 entries at 1.1e-16).
VERDICT   VERIFIED
BASIS     (a) `bound − certified lower` ≥ 0 at all 17 δ' ∈ [0.0005, 0.5]; the smallest slack is
          +5.5e-9 at δ' = 0.0039 (where the tangent touches) and it is positive on both sides.
          (b) Superdifferential at δ₀ ⊂ [0.560711, 0.560995]; reported s_min = 0.5608759 lies
          inside.  Hence s_min *is* a supergradient and exceeds the minimal one by at most
          1.65e-4, which inflates the D1′ bound at δ = 0.10 by at most 1.6e-5 nats.
          (c) With the code's U, `upper` and `slope` come back bit-identical to the manifest
          (60.620440804159976, 0.5608758772202841, 15 cuts).
ARTIFACT  /tmp/u8verify/attack_slope.py, /tmp/u8verify/attack_secant.py
CAVEATS   With my 1e-16-different U the slope moves to 0.5608719547 (7e-6 relative): s_min is a
          functional of a selected dual vertex, reproducible under identical input but not robust
          to a last-bit perturbation.  §9's four-decimal quotation (0.5609) is unaffected.
```

```
CLAIM     MODEL §4's D1′ and §9.2's NOT SOFT verdict ↔ frontier.py:287 softness
ATTACK    Rebuilt the certificate end-to-end from independently certified pieces: my own V from
          the raw instance, my own lower bound at δ₀ from an audited X, my own D at δ₀, and the
          slope squeezed by secants.  Specifically attacked the dangerous direction — a V that is
          too small, or an EG^bal that is too large, would manufacture "not soft".
VERDICT   VERIFIED
BASIS     V(hand, from raw JSON) = 59.93746979843285 — **bit-identical** to the manifest and to
          `metrics.json`'s `winner.stage2_value`.  The certified LOWER bound at δ₀ is
          60.62044080137, so φ(δ₀) − V ≥ 0.682971 nats already, 137× the 5e-3 floor.  Since the
          curve is nondecreasing and s_min ≥ 0, no slope can bring the bound below V + 5e-3 at
          any δ ≥ δ₀; the verdict is therefore carried by a *lower* bound and a comparand,
          neither of which depends on the OA's upper bound or on s_min.  My recomputed bounds
          (60.62944504 / 60.64627120 / 60.67431479) reproduce §9.2's to 8 significant figures.
ARTIFACT  /tmp/u8verify/certify_points.py, /tmp/u8verify/oracle_real.py
CAVEATS   Verified at the roster S₁₃ and the committed seed-3 draw only.
```

```
CLAIM     §10.A's mandatory guard: bound ≥ direct at every sponsor δ, raise otherwise ↔
          frontier.py:299 tangent_valid, :589-592
ATTACK    Recomputed the slack against a certified *lower* bound at each sponsor δ (a stricter
          test than against `certified_upper`), and extended the sweep to 17 δ'.  Read the code
          path to confirm the failure branch raises rather than warns.
VERDICT   VERIFIED
BASIS     Slack +5.797e-4 / +4.670e-3 / +1.659e-2 nats at 0.02 / 0.05 / 0.10 against my own lower
          bounds — matching §9.2's +5.80e-4 / +4.67e-3 / +1.66e-2 — and non-negative at all 17
          probe points.  `frontier.py:589` raises ValueError on any `tangent_valid is False`.
ARTIFACT  /tmp/u8verify/attack_slope.py
CAVEATS   The guard is pointwise; it witnesses validity at the grid, not on the whole ray.  The
          secant squeeze (row 9) is what closes that gap.
```

```
CLAIM     MODEL §4's feasibility witness (a bound over an empty set is useless) ↔ frontier.py:270
ATTACK    Recomputed the delivered draw's district masses from the raw instance and checked them
          against each band, and checked that δ₀ is exactly their max deviation.
VERDICT   VERIFIED
BASIS     δ₀(hand) = 0.003946010600450903 vs manifest 0.003946010600450769 (Δ = 1.3e-16), so the
          delivered integral coverage is band-feasible at δ₀ by construction and a fortiori at
          every larger δ; `integral_witness_in_band: true` at all five points.
ARTIFACT  /tmp/u8verify/oracle_real.py
CAVEATS   Witness only — nothing here bears on the smallest achievable t* (U18's question).
```

```
CLAIM     MODEL §5.1's safety property: every master optimum is an upper bound at every
          iteration ↔ eg_band.py:479-509
ATTACK    Truncated the cut budget on the REAL instance (1, 2, 3, 5, 8, 12, 15 tangents) and on
          the toy (1, 2, 3, 4, 6, 9 at four δ), and compared every intermediate `upper`, and the
          O(nk) dual bound of every intermediate dual, against the independently certified value.
VERDICT   VERIFIED
BASIS     Real instance at δ₀ (certified value 60.62044080417): uppers 60.94440 / 60.65152 /
          60.63248 / 60.62119 / 60.62046 / 60.620440937 / 60.620440805 — monotone down and above
          the certified value at every truncation; the matching per-iteration `D` (60.94440 /
          60.64561 / 60.62180 / 60.62051 / 60.62045 / 60.620440812 / 60.620440804) is also above
          it, so MODEL §4's "a stop-rule abort is still a certificate" is exercised, not asserted.
ARTIFACT  /tmp/u8verify/attack_vertex.py, tests/test_eg_band.py::test_oa_bound_never_below_truth
CAVEATS   The shipped test compares against the unit's own converged solve; the independent
          oracle for this property is the SLSQP/grid comparison of row 1 plus the above.
```

```
CLAIM     MODEL §5.1: "`ĝ > 0` at every iterate is guaranteed with an explicit constant by U9
          P5.3, g_i(X) ≥ λ(1−δ)T/k" ↔ eg_band.py:458 (the pool is checked once, before the loop)
ATTACK    P5.3's constant comes from the band's LOWER row.  `solve_band(delta=None)` drops that
          row — and `frontier.gate()` runs exactly that call, before any frontier point.  So I
          searched for an unconstrained instance whose OA iterate zeroes an agent.
VERDICT   **REFUTED**
BASIS     Concrete failing input: `U = [[1.4805844531533057, 9057834.838511182,
          4.518380079425886], [0.0063104220325362805, 0.04877643159703597,
          0.0001617968631145149]]`, `M = [0.07766424205302681, 3.5283240383668533]`, `delta=None`
          → an iterate with g_i = 0, `np.log(ghat)` = −inf at eg_band.py:388, and the run dies
          with `ValueError: Invalid input for linprog: A_ub must not contain values inf, nan, or
          None` after two RuntimeWarnings.  Reproduced by 3 of 4 hand-built cases and by a random
          instance at seed 3 of 300.  At any finite δ the same instances solve, because the lower
          band row restores the floor — which is precisely the scope of P5.3.
          Impact on published numbers: **none**.  Every δ=None solve in this unit is the gate on
          the real instance, where all 13 gains are ~90 and the floor is never approached, and
          the failure mode is a loud crash, never a wrong bound.
ARTIFACT  /tmp/u8verify/attack_ghat.py
CAVEATS   Two honest readings of the MODEL sentence: as scoped to the banded program it is true
          (and P5.3 is U9's, verified there); as a statement about `solve_band`'s iterates it is
          false, and the code's own docstring at eg_band.py:454-456 makes the P5.3 claim inside a
          function whose `delta=None` branch is not covered by it.  Suggested minimal repair
          (not applied — it touches a landed solver and I did not want to disturb the
          byte-identical anchor without a decision): re-check `(g > 0).all()` before
          `pool.append(g.copy())` at eg_band.py:505 and stop with a status string instead, plus
          one sentence of scope in MODEL §5.1.
```

```
CLAIM     MODEL §9.7 finding 4: the OA stall floor is the LP's primal feasibility tolerance, not
          Kelley instability; the 1e-9 rung clears tier 1 in 15–57 tangents ↔ eg_band.py:73, :391
ATTACK    Forced the ladder to a single rung and re-ran: `LP_TOL_LADDER = (1e-7,)` vs `(1e-9,)`
          on the toy, with a 400-cut budget so that a genuine Kelley stall would show as many
          iterations rather than as a floor.
VERDICT   VERIFIED
BASIS     Toy, δ=None: at 1e-7 the bracket floors at **6.694e-8** after 18 tangents and 400 more
          buy nothing (status "stalled at the LP tolerance floor"); at 1e-9 the same instance
          reaches 4.7e-9 in 15 tangents.  That reproduces the mechanism the docstring at
          eg_band.py:396-399 asserts (it quotes 6.7e-8 / 1.7e-9) and is the same order as
          math-verify's 1.8e-7 stall.  On the real instance the 1e-9 rung reaches tier 1 in
          15/23/35/44/57 tangents, exactly as §9.1 reports.
ARTIFACT  /tmp/u8verify/attack_edges.py
CAVEATS   This verifies the *mechanism* on this unit's loop.  It does not prove that
          math-verify's independent 225-iteration stall had the same cause — that loop is not in
          this worktree, so the attribution in §9.7 finding 4 remains a plausible, unfalsified
          inference rather than a checked fact.
```

```
CLAIM     MODEL §5.2's SCIP cross-check and §9.1's two agreements ↔ eg_band.py:547 solve_scip
ATTACK    Wrote a *different* SCIP model: no auxiliary gain variable and no `g_lower` box taken
          from the OA incumbent (the unit passes `g_lower = 0.5·g*`, which restricts the feasible
          set using a number the OA produced), with `log` applied straight to the 1229-term
          linear expression.  Same trap-12/14 settings.  Ran it on the toy at four δ and on the
          real instance at δ = 0.33.
VERDICT   VERIFIED
BASIS     Toy: my SCIP dual bounds agree with the OA to 2.9e-9 / 3.5e-9 / 2.7e-10 / 1.4e-10 at
          δ = 0 / 0.02 / 0.33 / None.  Real instance, all three stops `optimal`: δ = 0.33 →
          **60.697415617163756** (381 s), δ = 0.05 → **60.641601275111** (426 s), δ = 0.10 →
          **60.657725348422** (423 s), i.e. within 6e-9 of the certified values at all three and
          far inside the 1e-6 agreement the brief asks for — an independent confirmation that
          does *not* inherit the incumbent gain box.  The unit's own numbers (60.6288653576 at
          0.02, 60.6974156182 at 0.33) reproduced bit-for-bit on two fresh runs.
          `limits/gap = limits/absgap = 0.0`, `allow{strong,weak}dualreds` False, and
          `dual_bound=None` unless status == "optimal" (eg_band.py:598) — trap 15 respected.
ARTIFACT  /tmp/u8verify/oracle_scip.py
CAVEATS   My formulation took 381–426 s where the unit's takes 4.6 s at δ = 0.33 — evidence *for*
          the unit's trap-14 modelling choices (auxiliary g with `≤`, incumbent-derived lower
          bound).  And **SCIP's dual bound is not rigorous at tier-1 scale**: at δ = 0.05 mine
          came back 5.9e-9 *below* my own certified-feasible primal 60.641601281035, i.e. it is
          not a valid upper bound at that resolution (SCIP also prints "Cannot set feasibility
          tolerance to small value 1e-12 without GMP - using 1e-10" on every solve).  See F7.
```

```
CLAIM     MODEL §6's grid and δ₀ as a max deviation, not the published 0.0078 spread ↔
          frontier.py:225-226
ATTACK    Recomputed both statistics by hand from the raw instance and the draw CSV, and pinned
          the factor.
VERDICT   VERIFIED
BASIS     δ₀ = 0.003946010600450903, spread = 0.007812614473174296, ratio 1.979877 — matching
          §9.0's 0.0039460106 / 0.0078126145 / 1.9799.  The N7/M8 discrepancy is real and is a
          factor of ~2, as recorded.  The unit grids on δ₀, and `GRID` at frontier.py:61 with the
          δ₀ prepend at :540 produces exactly {δ₀, .02, .05, .10, .33}.
ARTIFACT  /tmp/u8verify/oracle_real.py
CAVEATS   —
```

```
CLAIM     MODEL §7/§9.6's first movers under U9 P2.5, and the refutation of §2.12's ratio rule ↔
          eg_band.py:354 good_side_scores, :362 first_movers
ATTACK    Recomputed the good-side score u_i(z)/g_i − ν_i M_z, the tie set, its M-mass, and the
          published ratio rule's ranking, from my own U and my own solve.
VERDICT   VERIFIED
BASIS     75 exact ties (manifest 75) carrying 2.901053 % of T (manifest 2.901053 %); top-25
          M-share 0.83 %; the ten smallest-margin zips are all R0001↔R0000 with ν = −4.537e-4 and
          −1.1608e-3, as §9.6 says.  max_i score − p_z = 2.9e-6 on a mean p of 1.1e-2 (the
          √bracket residual again).  The published ratio rule disagrees with P2.5 on **790 of
          1229** zips, its ten smallest-margin zips are 93901, 90631, 16365, … — §9.6's list
          verbatim — and its top-25 carry 3.4744 % of T, matching §9.6's "3.47 %".
ARTIFACT  /tmp/u8verify/attack_n8_n9.py
CAVEATS   The unit correctly declines to name an ordering: support 1248 vs expected 1253 makes
          the dual degenerate and only the tie *set* is defensible.  I confirmed the degeneracy
          independently (row 8).
```

```
CLAIM     §9.4's N8 (band duals) and §9.5's N9 (proportionality), incl. the refutation of
          DOMAIN_economic-theory §2.8's "proportionality is the first casualty"
ATTACK    Recomputed u_i(Z)/k, the delivered gains and the band-optimum gains from my own U and
          my own X; checked §2.8's definition against the code's; and — because a refutation of a
          published claim should not rest on the absence of an effect — ran a randomised search
          for band-induced proportionality failures on 372 two-measure instances, plus §2.8's own
          two-agent sketch.
VERDICT   VERIFIED
BASIS     Definitions match: §2.8 writes proportionality as u_i(A_i) ≥ u_i(Z)/k and
          frontier.py:280 computes `g − u_total/k` with u_total = column sums of the unmasked U
          (|u_total_hand − manifest| ≤ 1.1e-12).  Delivered draw: min gap −7.1351 with exactly
          four reps below — R0010 −7.1351, R0013 −4.7015, R0017 −2.3269, R0018 −1.7299, i.e.
          §9.5's four.  Band optima: min gaps +9.0899 / +9.2644 / +10.6380 / +11.6582 / +13.3569,
          none below zero, and the 32 % erosion §9.5 quotes checks out
          ((13.3569−9.0899)/13.3569 = 31.9 %).  The two populations are **not** conflated: the
          delivered figures come from the integral draw and the others from the fractional
          optimum, which is the population §2.8's table row is about.  N8: ν>0 at δ₀ for R0010,
          R0014, R0017, R0018, R0013, R0005; ν<0 for R0001, R0000, R0003, R0006, R0007, R0002;
          ν=0 for R0008 — §9.4's lists exactly; only lower bands bind from 0.02 outward; all
          ν = 0 at 0.33.  The mechanism §2.8 names is real elsewhere: 50 of 372 random instances
          show a band-induced failure absent at the free optimum (worst −23 % of the proportional
          share), so the unit's "on this instance it is not" is the correctly scoped refutation.
ARTIFACT  /tmp/u8verify/attack_n8_n9.py, /tmp/u8verify/attack_prop.py
CAVEATS   §2.8's own two-agent sketch ("one agent valuing only a zip carrying 60 % of M") does
          **not** produce a failure when solved (proportionality holds at every δ) — the sketch
          is a weaker witness than §2.8 implies, though the effect exists in richer instances.
```

```
CLAIM     §9.3's δ* ≤ δ₀ with zero solves ↔ frontier.py:303 bisect_delta_star
ATTACK    Solved the curve *below* δ₀ (δ = 0.0005, 0.001, 0.002, 0.003, 0.0035, 0.0039) to see
          whether the gap ever falls to the 5e-3 floor, which is what would make "δ* ≤ δ₀"
          vacuous or wrong.
VERDICT   VERIFIED
BASIS     φ(0.0005) = 60.61847322, so the gap is 0.68100 nats — still 136× the floor — at a δ
          eight times smaller than δ₀.  The early return at frontier.py:308 is therefore correct
          and its verdict string is accurate; the reported `value = δ₀` is the left endpoint of
          the search domain, and the surrounding text and the plot label both say "δ* ≤ δ₀".
ARTIFACT  /tmp/u8verify/attack_slope.py
CAVEATS   `DeltaStar.value` alone reads as "δ* = 0.0039"; only the `verdict` string carries the
          inequality.  Presentational, and the MODEL and the figure both state it correctly.
```

```
CLAIM     MODEL §1 / frontier.py:13 / gate error message: the masked convention "lands ≈ 27 nats"
ATTACK    Computed the masked quantity three ways: masked EG by proportional response (zeros
          floored at 1e-12), Σ_i log g_i of the masked utilities at the delivered map, and
          Σ_i log(masked column sums).
VERDICT   **REFUTED** (the number; the claim it supports survives)
BASIS     Masked EG = 55.9763 (PR primal = dual to 4e-9); masked delivered Σ log g = 51.9343;
          Σ log(masked column sums) = 56.7751.  None is ≈ 27, and none is ~34 nats below V.  The
          load-bearing part is nevertheless true: 55.9763 < V = 59.9375, so a wrong-convention
          run does land below V and would mimic a refutation of P1-band, and `gate()` refuses the
          masked matrix with a 4.72-nat miss.
ARTIFACT  /tmp/u8verify/attack_masked.py, /tmp/u8verify/attack_two_numbers.py
CAVEATS   The figure may be inherited from an earlier unit under a different treatment of the
          95.45 % zeros (solve_band cannot be run on the masked matrix at all — it raises on
          u ≤ 0), so I cannot exclude a convention under which 27 is right.  I did not edit
          MODEL_U8-band.md; the fix is to replace "≈ 27 nats" with a measured figure (55.98 nats
          for the masked EG, 51.93 for the masked delivered value) or with "well below V" in
          MODEL §1, frontier.py's module docstring and frontier.py:251.
```

## 3. Acceptance criteria

**1. Bracket ≤ 1e-8 at δ₀, SCIP within 1e-6 at two grid points, O(nk) check with no solver in
the trusted path — PASS.** Certified bracket at δ₀ = 2.801e-9 nats, computed by me from an
audited X and an independently derived D (all five points: 2.80/1.28/1.72/1.23/5.38 e-9). SCIP
agrees at 0.02 (1.58e-9) and 0.33 (1.10e-9), and my own independently written SCIP model agrees
at 0.33 (2.9e-9). D recomputed from the manifest's published duals with pure numpy arithmetic —
no solver anywhere in that path — matches bit for bit at all five δ, with min q > 0 and min μ = 0.
My independent SCIP (no incumbent gain box) also agrees at δ = 0.33 / 0.05 / 0.10, all stops
`optimal`, to 2.9e-9 / 5.9e-9 / 4.2e-9 — though see F7: at δ = 0.05 SCIP's dual bound is 5.9e-9
*below* a certified-feasible primal, so it is a cross-check, not a tier-1 bound.

**2. Sandwich, monotone and concave — PASS.** 59.9374697984 ≤ 60.6204408 ≤ 60.6288654 ≤
60.6416013 ≤ 60.6577253 ≤ 60.6974156, with EG^bal(0.33) = 60.697415614 within 4.0e-10 of the
published EG_{S₁₃} = 60.6974156139 (tolerance 1e-6). Zero monotonicity and zero concavity
violations, reproduced on two fresh runs. The band is slack at 0.33: the unconstrained optimum's
M max-deviation is 0.3224 < 0.33, confirmed at 0.322415 by my solver-free PR optimum.

**3. D1′ as a certificate at 0.02/0.05/0.10 with a verdict — PASS.** Bounds 60.62944510 /
60.64627138 / 60.67431517, gaps 0.69197530 / 0.70880158 / 0.73684537 nats against a 5e-3 floor,
**NOT SOFT** at all three, guard slack positive at all three.

**4. δ* to three digits, or "none in [δ₀, 0.33]" — PASS with a noted deviation.** Neither
anticipated answer applies: the gap is 0.682971 nats (137× the floor) already at δ₀, so
δ* ≤ δ₀ and the bisection runs zero solves. I verified by direct solves that the gap stays
≥ 0.681 nats down to δ = 0.0005, so the third case is real and not an artefact of the search
domain. The code's early return, the MODEL and the figure all state it as an inequality.

**5. Provenance and a byte-identical re-run — PASS.** Two fresh full runs (SCIP included) against
the landed manifest: **byte-identical modulo exactly `written` and `wall_seconds`** — verified by
JSON round-trip after popping only those two keys. SCIP's dual bounds are identical to the last
bit across all three runs (60.62886535755182, 60.697415618162424); only the wall clock moves
(852.6 / 884.6 / 879.2 s). `instance_sha256` and `draw_sha256` recomputed and match
(`cf7d66c0…`, `6614e665…`). θ/λ/filler_capture, run id, abspaths and all five solver versions are
present. `limits/gap = limits/absgap = 0.0` on every SCIP call; a non-optimal stop returns
`dual_bound=None`. The tracked figure regenerates byte-identically.
*On moving `wall_seconds` out of `ScipBound`:* legitimate. The relocation hides nothing — the
quantity it excludes from the payload body is the only quantity that actually varied, and the
solver's *answer* is bit-stable across three runs on two different machine loads. A timing is a
measurement of the machine, and the unit still reports it, in a named key.

**6. Tests — PASS.** 208 pass (184 pre-existing + 24 new), 0 fail, in 6.3 s. The toy is
MODEL_U7-meas §4's; brute force over fractional splits at δ = 0, 0.05, 0.5 and the unconstrained
comparison are both present; the OA-never-below-truth test sweeps six cut budgets at four δ. No
new test reads a gitignored input (`test_measure.py`/`test_instance.py` do, but they are
pre-existing and not this unit's). Two soft spots, neither a failure: the never-below test uses
the unit's own converged solve as its reference (my SLSQP/grid oracle covers the real property),
and no test pins the toy value against MODEL_U7-meas's published 6.1788 (I checked it: 6.178804).

## 4. Adjudication of the two declined instructions

**(a) `s_min` was not minimised over the exact dual-optimal set (§10.A).** The unit's substitute
is sound and I can now say so quantitatively rather than by argument.

1. *Direction.* For δ′ > δ₀ the bound φ(δ₀) + s(δ′−δ₀) *decreases* in s, so an under-minimised
   (too small) s makes the bound too small — biasing towards **soft**, i.e. towards collapsing
   the track. It cannot manufacture "not soft". The unit's argument is correct as to direction.
2. *Validity.* s_min = 0.5608759 is a genuine supergradient, witnessed at 17 δ′ on **both** sides
   of δ₀ (the unit only tests above), with the smallest slack +5.5e-9 at the touching point. A
   secant squeeze puts the entire superdifferential at δ₀ inside [0.560711, 0.560995], so the
   reported value is at most 1.65e-4 above the minimal supergradient — the declined LP could have
   improved the D1′ bound at δ = 0.10 by at most 1.6e-5 nats, against a 5e-3 floor and a 0.73-nat
   gap. The exposure §9.7 finding 6 records is real but bounded at ~3e-3 of the floor.
3. *Reproducibility.* Bit-identical across three full runs. It is **not** robust to a 1e-16
   perturbation of U (0.5608759 → 0.5608720, 7e-6 relative), because it is read off one vertex of
   a degenerate dual-optimal face. That does not threaten acceptance 5 (identical input, identical
   output) and does not reach the four decimals §9 quotes.
4. *Gauge.* U9's P2b pathology needs an unpinned gauge; here one agent is strictly slack on both
   bands at every δ and its ν is exactly 0, so the shift p → p + cM, ν → ν − c is killed. Verified.

**Verdict: the declined instruction is adjudicated in the unit's favour.** The guard is a
strictly weaker check than the LP, but the gap between them is measured here at ≤ 1.65e-4 in the
slope and ≤ 1.6e-5 nats in the certificate, and the softness verdict does not depend on the slope
at all — it is carried by the certified lower bound 60.62044080137 against V = 59.93746979843.

**(b) The tangent seed ĝ = u_i(Z)/k rather than P5.3's constant λ(1−δ)T/k.** The seed is the
Slater point x ≡ 1/k, hence exactly feasible and exactly evaluated; on the real instance it is
88.66–92.73 against a P5.3 floor of 63.113 at δ₀ and 42.451 at 0.33 (I reproduced both), so it is
1.4–2.2× tighter and every reported bound is at least as tight as it would have been with P5.3.
Keeping P5.3 as a runtime guard is the right call. **Adjudicated in the unit's favour on the
banded path** — but see row 13: the positivity check runs once, over the *initial* pool, and the
`delta=None` path (which the gate uses) is outside P5.3's scope, where a zeroed iterate is
constructible and crashes the loop. That is the one place the declined instruction leaves a hole,
and it is a hole in robustness, not in any published number.

## 5. Findings that are not refutations

- **F1 — the district mass vector at the unconstrained optimum is not an invariant.** My
  solver-free PR optimum has the same value (to 3e-9) and gains agreeing to 4e-5 relative, but a
  mass vector differing by up to 6.68 on a target of 211.20: max-deviation 0.322415 vs 0.322411
  (same starved district, so the §9.0 conclusion is unaffected) but **spread 0.5222 vs 0.5391**.
  §9.0's spread and the trap-2 "≥ 50 % M-spread" annotation are properties of the reported vertex,
  not of the optimum set. The annotation survives (both are ≥ 50 %) and the band-slackness
  argument survives (both witnesses are band-feasible at 0.33). This extends
  `VERIFY_U9-bandthm` §10.E's invariance list: g* and φ are invariants; p, ν, the split set —
  and now m — are not.
- **F2 — the primal vertex is as fragile as the dual.** Re-solving with a U differing in 37 of
  15,977 entries at 1.1e-16 moves the split count by ±1 at δ = 0.02/0.05/0.33 and the support and
  t by 1 at δ = 0.10. The split cap `k−1+t ≤ 2k−1` holds in every variant. §9.1's `t` and `splits`
  columns should be read the way §9.7 finding 5 already reads ν: one optimal vertex.
- **F3 — `DualCheck.feasible` can be True with `bound = inf`** (μ shifted by −1e-13). Sound but
  loose; unreachable from the CLI because eg_band.py:489 clips μ at 0.
- **F4 — MODEL §8's "69 zips exceed u/M = 1"** counts over all 111 reps; over the 13 staff whose
  columns this unit actually uses it is **46**, worst excess 4.200e-7 in both cases. The
  instance-level statement is right; the unit's own matrix carries 46 of them.
- **F5 — §9.2's circulated calibration (47.20 / 16.48 / 7.91 / 2.33)** reproduces as
  0.7599458/(δ − 0.0039) with δ₀ rounded to 0.0039, not with δ₀ = 0.0039460106 (which gives
  47.34 / 16.50 / 7.91 / 2.33). The MODEL quotes it as U9's circulated figure and its own reading
  of it is correct.
- **F6 — the SCIP cross-check inherits a gain box from the OA incumbent** (`g_lower = 0.5·g*`,
  frontier.py:264), so `solve_scip`'s bound is, strictly, a bound for the restricted program. My
  independently written SCIP model without that box agrees at δ = 0.33 / 0.05 / 0.10 to
  2.9e-9 / 5.9e-9 / 4.2e-9, which closes that loop; the O(nk) dual recomputation certifies all
  five points regardless.
- **F7 — SCIP's dual bound is a floating-point certificate, not a rigorous one, at 1e-9.** My
  independent SCIP at δ = 0.05 returned `optimal` with dual bound 60.641601275111, which is
  **5.9e-9 below** my own certified-feasible primal 60.641601281035 — so it is not an upper bound
  at that resolution (CLAUDE.md trap 15's "rigorous only to O(f·‖duals‖)"; SCIP also derates
  feastol to 1e-10 without GMP, which MODEL §9.7 finding 8 records). Consequence for the unit:
  MODEL §5.2's rule "on disagreement both are reported and the *smaller valid upper bound*
  stands" is **not implemented** — `Point.certified_upper` (frontier.py:126-131) takes the min of
  the master's value and the `O(nk)` dual only, and never adopts SCIP's number. That is the safe
  behaviour, and my δ = 0.05 result shows that implementing the model text literally at tier-1
  scale would have been unsafe. The model text should be narrowed to "SCIP is a cross-check, not
  a source of the reported bound"; no published number is affected.

## 6. Artifacts

All scratch scripts are outside the repo, in `/tmp/u8verify/`, and are runnable with
`/Users/ntlee/projects/td/.venv/bin/python3 <script>` from any directory:

| script | what it does |
|---|---|
| `oracle_toy.py` | hand-built U, SLSQP multi-start, exhaustive fractional grid, hand-written dual, on the U7-meas toy at k=2/3 |
| `oracle_real.py` | U/M/V/δ₀ rebuilt from the raw instance; proportional-response EG; D recomputed from the manifest's duals |
| `certify_points.py` | audits the solver's X and duals and produces an independent bracket at all five δ |
| `attack_slope.py` | s_min reproducibility, and the supergradient guard at 17 δ′ on both sides of δ₀ |
| `attack_secant.py` | secant squeeze of the superdifferential at δ₀ |
| `attack_edges.py` | k=1, n=1, δ=0, δ<0, zero M, zero u, ties, mis-shaped M, the 1e-7 vs 1e-9 stall, empty cut pool |
| `attack_ghat.py` | the ĝ ≤ 0 counterexample at δ=None (row 13) |
| `attack_dualres.py` | residual-vs-bracket scaling, budget identity, infeasible-dual probes |
| `attack_scaling.py` | the √bracket law on a random 60×5 instance |
| `attack_vertex.py` | independent split/support/rank audit; OA safety at truncated cut budgets on the real instance |
| `attack_n8_n9.py` | N8, N9, first movers, the ratio rule, §2.8's counterexample sketch |
| `attack_prop.py` | randomised search for band-induced proportionality failures |
| `attack_masked.py`, `attack_two_numbers.py` | the masked-convention numbers and the u/M rounding count |
| `attack_mspread.py` | mass-vector non-invariance at the unconstrained optimum |
| `oracle_scip.py` | an independently written SCIP model (no auxiliary gain, no incumbent box) |

Re-run commands used for the anchors:

```
/Users/ntlee/projects/td/.venv/bin/python3 tools/measure/frontier.py \
    instance_descaled.json.gz battery/results/draw_k13_20260901 \
    --out /tmp/u8verify/runA --figure /tmp/u8verify/runA/frontier.png      # and runB
/Users/ntlee/projects/td/.venv/bin/python3 tests/run_all.py
uvx pyright --pythonpath /Users/ntlee/projects/td/.venv/bin/python3 \
    td/solvers/eg_band.py tools/measure/frontier.py tests/test_eg_band.py
```

Nothing in this verification contradicts `docs/VERIFY_U1-cert.md` or
`docs/VERIFY_U9-bandthm.md`; F1 extends §10.E's invariance list and F2 extends §9.7 finding 5.
