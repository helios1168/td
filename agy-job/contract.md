# Accepted Contract: Asymmetric Claims-Centered Staffing and FEFx Fairness

Task C0, read-only gate. Status: accepted after Antigravity's read-only decision review on 2026-09-13.
No Python, tests, docs or model files are changed by this document.

Source precedence for this job: the standalone `IMPLEMENTATION_PLAN.md` takes precedence over Beads,
Helios, `STATE.md`, `PLAN.md` and Serena-memory routing. Within the mathematics, the repository
foundations (`docs/foundations/DOMAIN_economic-theory.md`, `docs/foundations/LIT_economic-theory.md`)
are read-only authority and outrank `MATH_REVIEW.md` and `AGY_REVIEW.md`, which are review artefacts
and, as section 7 of the plan states, carry unverified claims.

---

## 0. Findings that change the plan before any dispatch

These are corrections to `IMPLEMENTATION_PLAN.md` sections 2-4 that must be read before A1/R1/M1 are
dispatched. Each is grounded in the current tree, not opinion.

1. **`tools/measure/audits.py` does not exist.** The plan's "replace the classical 13x13 unconstrained
   EF1 matrix in `tools/measure/audits.py`" is a false premise. The only EF1 audit in the tree is
   `td/model.py::fairness` (lines 310-345), which is the plain-EF1 + proportionality-shortfall anchor
   over an `(n_rep, n_zip)` utility matrix. A1 must create the new, scoped module
   `tools/measure/fefx.py`; it must not claim or edit the U6-sel-owned `audits.py`. The existing
   `td/model.py::fairness` stays untouched and is the regression anchor for "plain EF1" (section 12).

2. **The FEFx definition is already settled by the domain theory, and it is band-feasibility, not
   geography.** `docs/foundations/DOMAIN_economic-theory.md` §2.8 (lines 482-510) and the N1/N9
   rows (lines 759, 767) state: "replaced operationally by **FEFx** -- envy only against band-feasible
   bundles", and the deliverable is "the 13x13 matrix `u_i(A_j)` with three verdicts: EF1, FEFx w.r.t.
   the band, proportionality". The feasibility filter is the **capacity band**, not a drivability or
   home-base rule. `MATH_REVIEW.md` §4.4 and plan spec 2 add a geographic condition ("contiguity,
   drivability from home base") that the domain theory does not have.

3. **Proportionality is already REFUTED as a target.** `DOMAIN_economic-theory.md` line 488:
   "Proportionality ... **REFUTED as stated** -- measured `prop_gap_delivered` min is **-12.0248** at
   `k=18` (v1: -7.1351); the starvation is the delivered map's". The plan's DoD items "zero feasible
   envy" and any proportionality success are measurement targets, not guaranteed outcomes, and the
   proportionality row is a **gap** to report, not a pass to claim.

4. **No representative home coordinate exists in the instance schema.** `td/instance.py`,
   `td/channels.py`, `td/model.py` and the projection carry per-zip `state`, `M`, `S` (and
   `S_free`, `cand`) but no rep latitude/longitude or home ZIP. The geographic test
   `d(home_i, center(A_k)) <= D_max` is therefore not computable without new data. The
   band-feasibility rule (finding 2) needs no such data and is the rule the contract adopts.

5. **`barman2023gac`'s FEF is over feasible *subsets*, and the plan's "whole-district filter" is a
   legitimate reduction only for a delivered assignment.** `LIT_economic-theory.md` lines 225-235:
   "feasible envy-freeness (FEF/FEFx) -- envy evaluated only against subsets the envying agent could
   actually have received, given agent-specific sizes and budgets -- ... existence for divisible
   goods and FEFx existence plus a pseudo-polynomial algorithm for indivisible goods, allowing a
   charity set." An audit of a delivered assignment only ever compares against the other agent's
   *held* bundle `A_k`, so `A_k in F_i` (whole district) is the right instantiation; but the paper is
   not a theorem that "the whole-district filter is FEFx". That equivalence must be stated, not
   asserted as inherited (section 14, escalation E1).

6. **`MATH_REVIEW.md` §4.4's FEFx formula is internally inconsistent.** It writes the *existential*
   one-item removal `exists z ... u_i(V_i) >= u_i(V_j \ {z})` (the plain-EF1 quantifier) while naming
   it FEFx. Plan spec 2 writes the *universal* removal `forall z in A_k` (the EFx quantifier). These
   are different tests with different closed forms (section 2). The "x" suffix and `barman2023gac`
   point to the universal reading; the existential formula is flagged for Antigravity (E2).

7. **The terminal re-match's home is `tools/plan_realise.py`, not `tools/full_plan.py`.** The realized
   ZIP sets `A_j` (`to_district`) exist only after Level 2 realization, which runs in
   `tools/plan_realise.py` (a separate command after `full_plan.py`). `full_plan.py` ends before any
   ZIP is assigned to a district (it writes `plan.json` and `staffing.json` at state grain). Plan task
   3.1's "in `tools/full_plan.py`, hook `execute_terminal_rematch`" is misplaced; the hook belongs in
   `tools/plan_realise.py`, which already reads `staffing.json` (`wholesaler_of`, line 199) and owns
   `to_district`.

8. **The centered and uncentered objectives can move the assignment in opposite directions.** A
   concrete 2x2 toy (section 13) shows the centered optimum picks one matching while the uncentered
   optimum picks the other, with `delta_uncentered = -0.025533` nats and `delta_centered = +0.064539`
   nats. The two deltas must be separately named and never assumed to share a sign.

---

## 1. (Item 1) Exact FEFx definition

**Plain EF1 (legacy anchor, unchanged).** For an ordered pair `(i, j)`, `i != j`, rep `i` does not
envy rep `j` up to one good iff `u_i(A_i) >= u_i(A_j) - max_{z in A_j} u_i(z)`. This is exactly
`td/model.py::fairness`, evaluated over **all** ordered pairs with **no** feasibility filter. The
existential removal quantifier is `exists z`; because utilities are additive, it reduces to removing
the single most valuable item (`max`).

**FEFx (new).** For `i != j`, if district `A_j` is feasible for rep `i` (`A_j in F_i`), then
`u_i(A_i) >= u_i(A_j) - min_{z in A_j} u_i(z)`. The removal quantifier is **universal** (`forall z`);
by additivity this reduces to removing the single *least* valuable item (`min`), which is the binding
item. If `A_j not in F_i`, the pair is **not applicable** (see section 3), not a pass and not a fail.

**Feasibility filter `F_i` (settled).** `F_i` is the **capacity band** of the district's bundle:
`A_j in F_i  <=>  L_{B_j} <= M(A_j) <= U_{B_j}` (plus the bundle's declared state-cap allowances `a_s`,
the same relaxation `tools/full_plan.py` uses). Because there is no per-rep capacity in the model, the
filter is agent-independent: `F[i,j] = band_ok[j]` for every `i`. The contracted primary result is
the band-only audit. A second, explicitly named band-plus-book-overlap diagnostic uses
`S_i(A_j) > 0`. Both results are reported side by side; neither result uses geography, because no
rep-home data exists.

**Valuation convention.** The audit must use the **same** valuation the matching uses:
`u_i(z) = c2*T_z + c_free*S_free(z) + lam*M_z + (c1 - c2)*S_i(z)` with `S_i(z) = 0` when `i` holds no
book at `z`. This is `td/channel.py::gain_matrix`'s "every rep prices every district" convention. It is
**not** `td/model.py::utilities`, which masks non-candidates to 0 and would silently zero a non-holder's
valuation of the ambient `c2*T_z + ...` term. The audit reuses `channel.gain_matrix`'s output `g[i,j]`
and additionally needs, per pair, `TOP[i,j] = max_z u_i(z)` and `BOT[i,j] = min_z u_i(z)` over `z in A_j`.

**Zero-valued zips.** `u_i(z) >= 0` always (all coefficients and masses are non-negative). Under the
`gain_matrix` convention a non-holder contributes `u_i(z) = common_z`, so `min_z u_i(z)` may be
strictly positive. Under the legacy masked convention a non-candidate is assigned zero utility, so
the minimum may be zero. The audit must record its valuation convention and must not silently mix the
two. No zip is skipped for being zero-valued; the arithmetic is uniform.

**Empty bundles.** `A_j` empty (`n_zips == 0`) -> `G = TOP = BOT = 0`, and the pair is `not_applicable`
(reason `empty_bundle`). `A_i` empty (rep `i` unmatched, the rectangular `|R| > |J|` case) -> every
row is `not_applicable` (reason `empty_own_bundle`). A realized district is never empty (Level 2 repairs
non-emptiness), so this is a defensive branch, not a normal one.

**Diagonal.** `i == j` is `not_applicable` (reason `self`). Self-envy is never evaluated.

**Timing of the feasibility test.** Feasibility is tested on the **whole** district `A_j`, before
removal, exactly once. Removing one ZIP for the envy check does **not** re-run feasibility, and
`u_i(A_j \ {z})` is never itself checked against `F_i`. This is the standard reading (the feasible set
is over bundles the agent could hold; the audit compares against the held bundle).

**FEFx is strictly stronger than EF1.** `TOP >= BOT`, hence `u_i(A_j) - BOT >= u_i(A_j) - TOP`, so
FEFx pass implies EF1 pass; EF1 can pass while FEFx fails (section 13 toy). A wide EF1 failure that is
**not** an FEFx failure is the meaningful diagnostic (`DOMAIN_economic-theory.md` N1: "the programme has
been reporting the wrong fairness notion, not an unfair map").

---

## 2. (Item 2) Candidate eligibility, band selection, geography, agent count, not-applicable reasons

- **Eligibility rule (settled):** `F_i = { A_j : M(A_j) in [L_{B_j}, U_{B_j}] }`, the district's own
  bundle band. This is documented in `DOMAIN_economic-theory.md` §2.8 and N1, and is the primary
  computable rule. The plan's "distance OR book overlap" example is **not** adopted as-is.
- **Band selection:** per-bundle bands from `params.json` (`bands`), else the global
  `--band-lo/--band-hi` (`0.8`/`1.2`) around the bundle `tau`. State-cap allowances `a_s`
  (`band_break`) extend the upper band exactly as in Level 0. The audit must read the same bands the
  run wrote; it must not re-derive them.
- **Geography:** **not implemented.** There is no rep home coordinate (finding 4), so no centroid or
  drivability test exists. Report two explicitly named results: the primary band-only audit and a
  band-plus-book-overlap diagnostic using `S_i(A_j) > 0` (`td/channel.py::gain_matrix` already computes
  `S_i(z)`). Neither result may silently substitute for the other, and the geographic condition
  contributes **nothing** to `F_i`.
- **Missing geography:** a rep without a home location is *not* a failure; the geographic test is
  simply absent for everyone. Recorded as a non-applicable capability, not a per-rep verdict.
- **Explicit agent count for proportionality (settled):** `n = |R_selected|`, the number of retained
  (matched) reps = the number of staffed districts. The share is `u_i(Z) / n`, where
  `u_i(Z) = sum_j G[i,j]` over the delivered districts (which partition the footprint). The plan's
  reuse of `k` both as an agent index and as this divisor is a name collision: the contract renames
  the divisor to `n` and renames any agent index in the audit to `i`, `j`. The domain theory's
  "13" is the delivered roster of that unit; the audit is parameterized by the actual roster size,
  **not** hard-coded to 13 (the current `full_plan.py` default is `k=18` districts).
- **Not-applicable reasons (enum):** `self`, `empty_bundle`, `empty_own_bundle`,
  `infeasible_for_agent` (with `mass`, `band` in the record), `unmatched_rep` (the envier is not
  retained). Every non-evaluated pair carries exactly one reason; none of these count toward a
  pass or a fail total.

---

## 3. (Item 3) Reservation inputs, units, modes, edge cases

**The reservation is a per-rep scalar disagreement point** `d_i` (descaled gain units, same as `g`):

```
d_i = alpha * S_i(Z) + d_floor          (claims)
d_i = d_floor                           (uniform)
d_i = 0                                 (none, legacy anchor)
```

- **`S_i(Z)`** = rep `i`'s total historical book over the contested region `Z`, summed over states and
  channels: `cells.S[i].sum()` at state grain (`cells.S` is `(R, S, C)`), or `sum_z S_i(z)` at ZIP grain.
- **`d_floor = gamma * G0_floor`**, where `G0_floor = min_j G0_j` and
  `G0_j = sum_{z in A_j} [ c2*T_z + c_free*S_free(z) + lam*M_z ]` is the ambient (rep-independent)
  district gain. R1 computes this at state grain from the state-share approximation; M1 recomputes it
  at ZIP grain from the realized districts. Each stage records its `reservation_grain`, and a
  state-grain reservation is never mixed with a ZIP-grain welfare delta. `gamma = 0.60` (valid range
  `[0.5, 0.8]` per `MATH_REVIEW.md` §4.5; contract range `[0, 1)`).
- **`alpha = min(1.0, region_M / region_T) * (1 - epsilon)`**, a single scalar (not per-rep; the plan's
  subscript `i` is a typo), where `region_M = M(Region)`, `region_T = sum_k S_k(Region)` over the
  staffing candidate set (the same `R` the match uses, i.e. `cells.reps`). `epsilon = 0.05`.
- **Units:** everything descaled (gain units). `alpha` dimensionless, `d_floor` and `d_i` in gain units.
  No dollar conversion; the instance is descaled by the median ZIP opportunity (`MATH_REVIEW.md` §3.1).

**Edge cases (settled behavior):**

- **Zero claims:** `S_i(Z) = 0` -> `d_i = d_floor` (the ambient floor protects the rep even with no book).
- **Zero ambient floor:** `G0_floor == 0` -> `d_floor = 0`. The report-only log-domain floor remains
  `eps_floor = max(1e-6 * d_floor, 1e-12)`; it is not used to turn an infeasible assignment edge into
  a feasible one.
- **Empty region:** `region_M == 0` -> `alpha = 0`; `region_T == 0` -> every `S_i = 0`, so `d_i =
  d_floor` and `alpha` is irrelevant (defined as 0 to avoid 0/0).
- **Non-finite inputs:** any NaN/inf in `S`, `M`, or resulting `d_i`/centered gain raises `ValueError`
  (reject). No silent propagation.
- **Parameter ranges:** `gamma in [0, 1)`, `epsilon in [0, 1)` (so `alpha in [0, 1-eps]`), `mode in
  {"none", "uniform", "claims"}`. Out-of-range raises `ValueError`.
- **Uniform semantics:** "uniform" is a common ambient floor for every rep, `d_i = d_floor`. For
  `gamma in [0, 1)`, this mode is the documented clip-free fallback.

**Positive-surplus-on-every-edge vs feasible-complete-matching (settled).** The spec-1 guard
`g_{i,j} - d_i >= 1e-6 * d_floor > 0` for **all** `(i,j)` is "positive surplus on every edge", which is
strictly stronger than "there exists a complete matching with positive surplus on its matched edges".
The clip is a numerical guard, **not** a bargaining-feasibility certificate. Logging the clip does not
establish feasibility. The assignment must use the raw centered surplus and an allowed-edge mask. A
complete matching on that mask is the bargaining-feasibility certificate.

**reject / mask / clip / adjust (settled):**

- **reject:** raise `ValueError` on non-finite inputs, out-of-range parameters, or failure to find a
  complete matching on the strictly positive centered-surplus mask.
- **mask:** set `ok[i,j] = (g[i,j] - d_i) > positivity_tol` and run the existing
  `td/stage2_state.py::_match_masked` dominance-penalty path on the raw centered values. Check the
  returned matching length against the number of used slots, which is the Hall shortfall test.
- **clip:** never clip a forbidden edge into the assignment matrix. Keep `clipped_edges = 0` for
  schema compatibility and report `nonpositive_edges` separately. `eps_floor` is report-only for this
  path, not a feasibility certificate.
- **adjust:** no per-rep or per-edge adjustment is allowed. A future relaxation may use one documented
  global scalar haircut or an explicit downgrade to uniform mode, but neither is implicit.

---

## 4. (Item 4) Centered welfare vs uncentered distortion

The terminal re-match optimizes the **centered** objective `sum_i log(g_discrete[i,pi(i)] - d_i)`. The
"Spatial Aggregation Distortion Metric" in spec 3 is **uncentered** `sum_i log g_discrete`. These are
different functions and their deltas can have opposite signs (finding 8, section 13).

**Distinct output keys (settled), all in gain/nats units:**

- `value_centered` = `sum_i log(g_discrete[i, pi_terminal(i)] - d_i)` at the terminal assignment.
- `welfare_uncentered_terminal` = `sum_i log g_discrete[i, pi_terminal(i)]`.
- `welfare_uncentered_level0` = `sum_i log g_discrete[i, pi_level0(i)]`, where `pi_level0` is the
  state-grain assignment **re-scored on the realized matrix** (not the state-share approximation).
- `delta_uncentered` = `welfare_uncentered_terminal - welfare_uncentered_level0`.
- `delta_centered` = `value_centered - value_centered_at_level0_assignment`.

**Both assignments are compared on the same realized ZIP gain matrix** `g_discrete` (`channel.gain_matrix`
on `to_district`). No silent substitution, and no claim that `delta_uncentered` and `delta_centered`
share a sign.

---

## 5. (Item 5) Eligible edges, held/released reps, rectangular/multi-rep, ties, scale, preservation

- **Eligible edges:** the terminal re-match uses the **same convention** as the Level-0 staffing:
  unconstrained (`candidacy=False`), every rep prices every district. The re-match differs from Level 0
  **only** in the realized gain matrix, not in an eligibility rule. Held/released reps: unavailable reps
  are excluded from candidacy, never passed through `model.release_reps` (CLAUDE.md trap 20); `tools/staff.py`'s
  `held` set is the mechanism, and this job adds no new release path.
- **Rectangular:** if `|R| > |J|`, the unmatched reps are the not-retained reps; if `|J| > |R|`,
  unmatched districts are unstaffed. Both carried in `unmatched_reps` / `unstaffed_districts` exactly as
  `td/channel.py::stage2` does.
- **Multi-rep districts:** out of scope. The model is one rep per district (`sum_j w_ij <= 1`). No
  district gets more than one rep; the re-match preserves this. Flagged as an explicit non-goal.
- **Deterministic ties:** `scipy.optimize.linear_sum_assignment` is deterministic on a fixed matrix and
  dtype. No secondary tie-break is added (adding one would need its own definition; the contract does
  not invent one).
- **Scale invariance:** when all gains and the reservation are recomputed at the same `kappa > 0`,
  scaling adds `n log kappa` to the centered objective and `n log kappa` to the uncentered objective.
  The positive-surplus mask and assignment are therefore invariant away from the absolute
  `positivity_tol` boundary. Passing an absolute reservation, or changing the reservation grain,
  breaks this comparison. Record the scale and grain with every result.
- **Preservation of fixed membership and capacity:** the re-match re-assigns **reps to districts only**;
  it never moves a ZIP between districts, never edits `to_district`, `M(A_j)`, or the bundle bands. The
  district mass and capacity compliance are therefore bit-identical before and after the re-match. The
  re-match output carries the realized district -> rep map and the migration statistics.

---

## 6. (Item 6) Numerical tolerances and "strict convexity"

- **Tolerances (settled):** the repository has two certificate tiers -- `base.CERT_TOL = 1e-8` nats
  (tier 1) and `base.EPS_CERT = 5e-3` nats (tier 2, data-noise floor). The centered Hungarian solve is a
  matching, not an LP/MILP certificate, so it needs no new gap tolerance; it needs only **strict
  positivity** of every matched centered gain. The clip floor `eps_floor = max(1e-6 * d_floor, 1e-12)` is
  a model constant for the log domain, not a certificate tolerance, and is recorded separately.
- **"Strict convexity" is a category error and is dropped.** Plan task 2.4 asserts "`C_{i,j}` remains
  strictly convex". A fixed Hungarian cost matrix `C_{i,j} = -log(g_{i,j} - d_i)` has no convexity
  property; `log(x - d)` is strictly concave in `x`. Verify instead: (P1) every matched centered gain
  is strictly positive, (P2) the positive-surplus graph has a complete matching, (P3) the assignment
  polytope is totally unimodular, and (P4) conditioning is reported near the reservation boundary.
  No convexity proof against a matrix is required.

---

## 7. (Item 7) Evidence required for "zero feasible envy" and "improved retention"

Both are **measured** claims, not theorems, and not supplied by maximizing Nash welfare (traps 2 and 4).

- **Zero feasible envy:** after A1, measure the FEFx verdict over the delivered roster and report
  `n_fefx_failures`, `n_fefx_applicable`, and the worst normalized envy. "Zero feasible envy" is the
  outcome iff `n_fefx_failures == 0`. The plan's DoD item is reworded to a *measurement*, not a promise.
  If the measured result has feasible envy, report it and leave the target unmet.
- **Improved retention:** report `share_of_book_kept` per retained rep (already computed in
  `tools/plan_realise.py::_write_wholesalers`, column `share_of_book_kept`) before and after the claims
  reservation and the terminal re-match, on the **same** realized matrix. "Improved" is a comparison of
  those measurements, not an assertion that the reservation guarantees it.
- **No weakening, no threshold changes, no theorem substitution:** if either target fails, the audit and
  thresholds are unchanged, and the result is reported as unmet. The claim that Nash maximization
  "automatically supplies" a fairness certificate is rejected (Nash gives PO/EF1 only under the
  unconstrained, `d=0` hypotheses that the band already voids; `DOMAIN_economic-theory.md` §2.8).

---

## 9. Proposed APIs, types, axes, units, defaults, output keys

### `td/stage2_state.py` (R1)

```python
def compute_reservation_vector(
    S_book: np.ndarray,            # (R,) rep total book over region, cells.reps order, gain units
    *, region_M: float,            # M(Region), gain units
    region_T: float,               # sum over reps of S_book, gain units (== S_book.sum())
    G0_floor: float,               # min_j G0_j (ambient), gain units
    mode: str = "none",            # "none" | "uniform" | "claims"
    gamma: float = 0.60,
    epsilon: float = 0.05,
) -> np.ndarray                    # (R,) d_i, gain units
```
Validates `gamma`, `epsilon`, `mode`, and non-finite inputs; raises `ValueError` (reject).

`state_stage2` and `state_gain_matrix` gain a keyword `reservation: np.ndarray | None = None`
(`None` == legacy `d=0`). With a reservation, construct the raw centered surplus
`centered = g - d_i[:, None]`, set `ok = centered > positivity_tol`, and run the existing
`_match_masked` dominance-penalty path on the raw values. Do not pass clipped forbidden edges to
`channel.match`; verify that the returned matching saturates every used slot. New output keys:
`value_centered`, `reservation_mode`, `reservation_grain`, `clipped_edges` (always zero in this path),
`nonpositive_edges`, `hall_shortfall`, and `epsilon_floor` (report-only). Existing keys `assignment`,
`gains` (now centered surplus), `value`, `reps`, `districts`, `unmatched_reps`, `unstaffed_districts`,
`balance` are preserved.

### `tools/full_plan.py` (R2)

New CLI: `--stage2-reservation {none,uniform,claims}` (default `none`), `--reservation-gamma`
(default `0.60`), `--reservation-epsilon` (default `0.05`). Threaded through to `state_stage2`.
`staffing.json` gains `reservation_mode`, `reservation_grain`, `clipped_edges`, `nonpositive_edges`,
`hall_shortfall`, and `epsilon_floor`. Default run (`none`) is byte-for-byte the legacy staffing path
(regression anchor), apart from explicitly documented metadata keys.

### `tools/measure/fefx.py` (A1, new file)

```python
@dataclass(frozen=True)
class PairVerdict:
    i: str; j: str; reason: str | None  # None when applicable; otherwise "self" | "empty_bundle" | "empty_own_bundle"
                                     # | "infeasible_for_agent" | "unmatched_rep"
    ef1: bool | None                 # None when not applicable
    fefx: bool | None
    applicable: bool

def district_extrema(G: "nx.Graph", to_district: dict, reps_order: list,
                     districts: list, *, theta=0.40, lam=0.30,
                     filler_capture="theta") -> "tuple[np.ndarray, np.ndarray, np.ndarray]":
    # returns (G[i,j], TOP[i,j], BOT[i,j]) with the gain_matrix valuation convention

def compute_envy_matrix(G: "nx.Graph", to_district: dict, reps_order: list,
                        districts: list, *, feasible: np.ndarray | None = None,
                        # (n_rep, n_district) bool; defaults to all-True (plain, unfiltered)
                        quantifier: str = "efx",   # "ef1" | "efx" for the filtered audit
                        valuation: str = "gain_matrix",  # "gain_matrix" | "masked"
                        slack: float = 0.0,
                        theta=0.40, lam=0.30, filler_capture="theta",
                        ) -> dict:
    # -> { "ef1": bool, "n_ef1_failures": int, "fefx": bool, "n_fefx_failures": int,
    #      "n_applicable": int, "prop_gap": np.ndarray, "prop_gap_min": float,
    #      "pairs": list[PairVerdict], "n": int }
```

The new FEFx audit uses `valuation="gain_matrix"` and reports the band-only and
band-plus-book-overlap masks separately. The filtered audit (`feasible` given) marks ineligible pairs
not applicable. `quantifier="efx"` uses `BOT`, `"ef1"` uses `TOP` for the filtered verdict. The
legacy regression anchor is an explicit call with `valuation="masked"`, `quantifier="ef1"`,
`slack=1e-12`, and proportionality divisor `n = U.shape[0]`; that call must reproduce all keys from
`td/model.py::fairness`, including `envy_over_umax` and normalized `prop_shortfall`. New gain-matrix
FEFx results use the selected retained roster for their proportionality divisor. Every result records
the valuation convention.

### `tools/plan_realise.py` (M1/M2)

```python
def execute_terminal_rematch(G, to_district: dict, reps_order: list | None,
                             *, reservation: np.ndarray | None = None,
                             criterion="nash", theta=0.40, lam=0.30,
                             filler_capture="theta") -> dict:
    # -> { "assignment": {district: rep}, "value_centered": float,
    #      "welfare_uncentered_terminal": float, "welfare_uncentered_level0": float,
    #      "delta_uncentered": float, "delta_centered": float,
    #      "reps_swapped": int, "unmatched_reps": list, "unstaffed_districts": list }
```
Hooked behind `--stage2-rematch` (default off), run after realization/repair so it sees `to_district`.
It must not move zips between districts (section 5). Output updates (`M2`) rewrite `staffing.json`
(terminal assignment) and the wholesaler column of `assignment.csv`/`districts.csv` and
`wholesalers.csv`, and add the migration statistics (`reps_swapped`, `delta_uncentered`,
`delta_centered`, `value_centered`).

---

## 10. Source locations

- EF1 anchor: `td/model.py::fairness` (310-345); `td/model.py::utilities` (137), `coefficients` (124),
  `books` (73), `free_book` (68), `reps` (81), `gains` (217).
- Stage-2 matching: `td/channel.py::gain_matrix` (252), `match` (285), `stage2` (312);
  `td/stage2_state.py::state_stage2` (191), `state_gain_matrix` (122), `_match_masked` (137),
  `_check_staffable` (164), `_slot_mass` (98).
- Level-0 driver: `tools/full_plan.py` `build_argparser` (193), stage-2 call (1851-1858),
  `_plan_object` (564).
- Level-2 realization: `tools/plan_realise.py` `wholesaler_of` (199), `_write_assignment` (948),
  `_write_districts` (976), `_write_wholesalers` (987), `realise`/`repair` (627).
- Reservation/utility coefficients: `td/model.py::coefficients`; `td/channels.py::CellTable` (339),
  `aggregate` (350) (`S` is `(R,S,C)`, `S_free` is `(S,C)`, `M` is `(S,C)`).
- Tolerances: `td/solvers/base.py` `CERT_TOL=1e-8` (72), `EPS_CERT=5e-3` (81).
- Domain authority: `docs/foundations/DOMAIN_economic-theory.md` §2.8 (482-510), N1 (759), N9 (767),
  N3 (761); `docs/foundations/LIT_economic-theory.md` barman2023gac (225-235).
- Unit collision: `docs/units/U6-sel.md` (owns `tools/measure/audits.py`, `tests/test_audits.py`,
  gated on ★5/★6, "not launched").

---

## 11. File/test map (A1..V1) with corrections

| ID | Plan | Model | Corrected owned files | Notes |
| --- | --- | --- | --- | --- |
| A1 | 1.1 | v4-pro | `tools/measure/fefx.py` (new) | Creates the scoped FEFx/EF1/proportionality module; does not claim or edit U6-sel's `audits.py`. |
| A2 | 1.2, 1.3 | v4.1-flash | `tests/test_fefx.py` (new) | Adversarial + fixture; includes the §13 toys and both valuation conventions. Luna reruns. |
| R1 | 2.1, 2.2 | v4-pro | `td/stage2_state.py`; tests `tests/test_stage2_state.py` | Adds `compute_reservation_vector` + centered path. Core numerical tests live here, not only in A2. |
| R2 | 2.3 | mimo | `tools/full_plan.py`; tests `tests/test_full_plan_cli.py` | `--stage2-reservation` parsing + propagation. |
| G2 | 2.4, 2.5 | Antigravity/Luna | none | Math gate; no convexity proof against a matrix (E5). |
| M1 | 3.1 | v4-pro | `tools/plan_realise.py` (corrected from `full_plan.py`); tests `tests/test_plan_realise.py` | Terminal re-match, fixed geography. |
| M2 | 3.2, 3.3 | v4.1-flash | `tools/plan_realise.py`; integration tests `tests/test_plan_realise.py` | Output updates + migration stats. |
| O1 | 4.1 | mimo | new `tools/measure/audit_compare.py` (or extend `audits.py::main`) | Comparative JSON/tables. |
| Q1 | review | qwen | none | Independent diff/contract review. |
| V1 | 4.2 + final | Antigravity/Luna | none | Full tests, CA/TX/FL + CONUS evidence, sign-off or explicit pending. |
| H1 | 4.3 | Luna | none | Atomic commits on `worktree-agy-math-review`. |

---

## 12. Regression anchors

- **`--stage2-reservation none`** is the legacy `d=0` staffing path; byte-for-byte identical output to
  the current `staffing.json` (modulo the added keys, which are absent in `none` mode or `0`/`false`).
- **`--stage2-rematch` off** is the current pipeline: Level-0 staffing on state shares, no second
  matching. Default is off.
- **`td/model.py::fairness`** is untouched; an explicit `compute_envy_matrix` call using
  `valuation="masked"`, `quantifier="ef1"`, `slack=1e-12`, and divisor `n = U.shape[0]` must reproduce
  its `ef1`, `n_ef1_failures`, `envy_over_umax`, and normalized `prop_shortfall` on the same inputs.
- The full runner is `"$TD_PY" -u tests/run_all.py` (not `rtk test`, which hides FAIL lines).

---

## 13. Independently computed toy expected answers

Computed with `/Users/Shared/sv-ntlee/repos/td/.venv/bin/python3` (numpy 2.5.2, scipy 1.18.1).

**(a) EFx is the "remove min" closed form; EF1 is "remove max".**
`u_i(A_k)` over zips `[5, 3, 2]` = `10`; `u_i(A_i) = 6`.
- EF1 residual = `10 - max = 5` -> pass (`6 >= 5`).
- EFx residual = `10 - min = 8` -> fail (`6 < 8`).

**(b) FEFx stricter than EF1.**
`u_i(A_i)=4`, `u_i(A_k)` over zips `[7, 3]` = `10`.
- EF1: `4 >= 10 - 7 = 3` -> **pass**.
- FEFx: `4 >= 10 - 3 = 7` -> **fail**.

**(c) Reservation (claims mode).**
`S_book = {r0: 40, r1: 25, r2: 5}`, `region_M = 60`, `region_T = 70`, `G0_floor = 55`,
`gamma = 0.60`, `epsilon = 0.05`.
- `alpha = min(1, 60/70) * 0.95 = 0.8142857...`
- `d_floor = 0.60 * 55 = 33.0`
- `d = {r0: 65.571429, r1: 53.357143, r2: 37.071429}`, zero-claim rep `d = 33.0`.

**(d) Centered vs uncentered sign mismatch.**
`g = [[58, 68], [63, 72]]`, `d = [38, 48]`.
- Uncentered: diag `58*72 = 4176`, anti `68*63 = 4284` -> anti wins (Level-0 assignment).
- Centered: diag `(58-38)*(72-48) = 480`, anti `(68-38)*(63-48) = 450` -> diag wins (terminal).
- `delta_uncentered = log(58*72) - log(68*63) = -0.025533` nats (uncentered welfare **drops**).
- `delta_centered = log(480) - log(450) = +0.064539` nats (centered welfare **rises**).
This is the concrete demonstration that the two deltas must be separate keys and can disagree in sign.

---

## 14. Antigravity decision record

Antigravity reviewed this contract, the C0 and Q0 reports, the plan, and the cited mathematical
authority in read-only mode on 2026-09-13. The following decisions are accepted for implementation:

- **E1:** Accept the whole-district band filter as the definition of this delivered-map audit. Do not
  cite `barman2023gac` as an existence guarantee. Report band violations rather than hiding them in
  the not-applicable count.
- **E2:** Use the universal EFX removal quantifier and correct `MATH_REVIEW.md`. Keep the gain-matrix
  and legacy masked valuation conventions explicitly separate, including their zero-valued ZIP rules.
- **E3:** Drop drivability because rep-home data does not exist. Report band-only and band-plus-book-
  overlap results side by side.
- **E4:** Reject an unstaffable claims reservation. Use raw centered surplus with `_match_masked` and a
  Hall-complete matching check. Do not use clipping or per-rep/per-edge adjustment.
- **E5:** Drop strict convexity. Verify positive matched surplus, Hall non-emptiness, total
  unimodularity, and numerical conditioning instead.
- **E6:** Use `tools/measure/fefx.py` and `tests/test_fefx.py` for this job, leaving U6-sel's
  `audits.py` and `test_audits.py` ownership intact.
- **E7:** Define uniform mode as `d_i = d_floor` with `gamma < 1`; use it as the clip-free fallback.

Before implementation, apply these contract corrections: pin the section 12 regression anchor to
`td/model.py::fairness` using masked valuation, the total roster-size divisor, and `1e-12` slack;
record the reservation grain because R1 is state-grain and M1 is ZIP-grain; and log the valuation
convention for every audit result. Antigravity authorizes A1, R1, and M1 after these corrections.

---

## Execution

This is the accepted C0 deliverable. The E1-E7 gate is resolved. The plan's `## Execution` schedule and
model allocation in section 8 stand with the corrections in sections 0, 9, 11, and 12 applied. A1 may
now be dispatched; R1 and M1 remain ordered by their declared dependencies.
