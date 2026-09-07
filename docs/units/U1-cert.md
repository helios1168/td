# Unit U1-cert — does the Eisenberg–Gale dual subsume the four existing certificates?

Status: done

## Spec (verbatim from `docs/foundations/DOMAIN_optimization.md`:§3 and §2.2)

> **Verification handed to `math-verify`:**
> […]
> - that the fractional relaxation's value upper-bounds every integral coverage with the same
>   roster (§2.2) — the lens marks this `[claim, immediate but unverified]`;
> - that the four existing certificates are degenerations of §2.2's dual at `u_i ≡ λM` (Groth §3
>   descent) — **this is the "five collapse into one" claim and it is the load-bearing one**;
> - the `≤ k−1` split-zip descent, if §6 does not return a citation.

Supporting statement of the object, verbatim from `docs/foundations/LENS_GROTHENDIECK.md`:§"The general case,
stated":

> **Fibre.** For a staff set `S`, the relaxation over fractional assignments `X` supported on `S`
> is concave; it is the Eisenberg–Gale program of the Fisher market `(S, Z, M, budgets ≡ 1, u)`
> penalised by `ρ·C`. Its value upper-bounds every integral coverage with `im σ = S` `[claim]`;
> its duals are prices on `Z`; at a basic optimum at most `|S| − 1` units are split `[standard]`.
>
> **Degeneration.** At `u_i ≡ λM` for all `i` the fibres become isomorphic and staff-independent;
> the optimum is `k·log(λM(Z)/k)` — the analytic balance ceiling — every equal-mass partition
> attains it, and the `ρ`-term selects a power diagram of the centers with the duals as weights.

## Files owned

- `docs/MODEL_U1-cert.md` (the model; created by `modeler`)
- `docs/VERIFY_U1-cert.md` (the verdict; created by `math-verify`)
- `tools/verify/U1-cert/**` (throwaway runnable artifacts — the toy instances and the symbolic
  or numeric checks `math-verify` requires)

## Files forbidden

Every other unit's owned files (`docs/MODEL_U2-stab.md`, `docs/MODEL_U3-inv.md`,
`docs/foundations/LIT_optimization.md`, `docs/RESEARCH_ADDITIONS.bib`, …) · `docs/foundations/FRAME.md` ·
`docs/foundations/BRIEF.md` · `docs/foundations/LENS_*.md` · `docs/foundations/DOMAIN_*.md` ·
`docs/channel_note/**` · `CLAUDE.md` · **all of `td/`, `tests/`,
`tools/`, `figures/`, `battery/`** (read-only at most; this unit writes no project code) ·
`instance_descaled.json.gz` is **present** at this worktree's root and ★6 is lifted in full
(2026-09-03), so the numbers under "Numbers to compute first" are computable here — read it
through `td/instance.py`, write nothing outside the owned files.

## Agent → verifier

`modeler` → `math-verify`

## Acceptance

`math-verify` returns **VERIFIED or REFUTED** (not INCONCLUSIVE) on **both** of the following,
each backed by a runnable artifact under `tools/verify/U1-cert/`:

- **P1 (the relaxation bound).** For a fixed staff set `S`, `EG_S ≥ V(π,σ)` for every integral
  coverage with `im σ = S` — stated with its hypotheses, including what `ρ > 0` does to it
  (`DOMAIN_economic-theory.md` §2.1 failure mode (i) warns the fairness reading lapses at `ρ > 0`;
  state whether the *bound* does too).
- **P2 (the collapse).** Each of the four existing certificates — the analytic balance ceiling,
  the integer balance floor, assignment optimality at pinned centers, and `cert_power_diagram` —
  is a degeneration or restriction of `EG_S`'s dual, obtained by a **named** specialisation
  (`u_i ≡ λM`; `ρ` on/off; centers pinned). A certificate that does *not* arise this way must be
  named as such — a partial collapse is a legitimate and useful result, an unstated one is not.

Additionally required, at PLAUSIBLE-or-better standing:

- **P3 (the integrality gap in value, not count).** The `≤ k−1` split-unit bound is a *count*.
  `DOMAIN_economic-theory.md` §2.2 failure mode: FRAME §6 records the largest single zip at 1.07%
  of total `M` ≈ **14% of one territory**, so 12 splits is not obviously negligible. Give a bound
  on the *value* of the gap in terms of the largest split unit's mass, or state explicitly that
  none exists and the bound is therefore quotable only alongside the split masses.
- A one-paragraph statement of **what the bound does not cover** — misreporting, and error in `M`
  (`DOMAIN_optimization.md` §3.4).

## Numbers to compute first

From `DOMAIN_optimization.md` §5 — **all blocked on ★6 and on the instance's absence** (FRAME §5).
Do **not** attempt to reach the instance. Instead, for each, state the threshold that would flip
this unit's conclusion, so the measurement (when it runs) either confirms or refutes without
rework:

| § 5 # | number | what this unit must state about it |
|---|---|---|
| 7 | `EG_R` — the concave relaxation over all 111 reps | at what looseness the outer term of the sandwich `V ≤ max_S EG_S ≤ EG_R` becomes useless |
| — | largest split-unit mass at a basic EG optimum | the value at which P3's gap swamps the ~3.7-nat premium and the bound becomes decorative |
| 2 | spread of realized gains `g_i` vs the published 0.781% spread of `M` | which of the two the certificate is a statement about (`LENS_GROMOV.md` M3 consequence 1) |

Numbers this unit **may** compute: anything on a hand-built toy instance of its own construction
(3–5 reps, 6–12 zips) under `tools/verify/U1-cert/`. Toy instances are how P2's specialisations
get checked and how a refutation gets its counterexample.

## Inputs to read (paths and sections only)

- `docs/foundations/DOMAIN_optimization.md` §2.2, §3, §8 Q4 (the load-bearing framing)
- `docs/foundations/LENS_GROTHENDIECK.md` §2 (the τ-deformation and step 2), §4 (relativisation, the sandwich),
  "The general case, stated", descent 3
- `docs/foundations/LENS_GROMOV.md` Move 3 (the fibration; what the certificates certify)
- `docs/MODEL.md` (the N-way model — `u_i(z)`, `c1`, `c2`, `λ`, `θ`, the headroom condition)
- `docs/foundations/FRAME.md` §6 (the four certificate numbers; the 1.07% largest zip), §10 Q3
- The 2026-09-01 Gromov review R3, which proposed the EG bound as "certificate 5" — this unit's
  claim is that it is not a fifth but *the* one. (`docs/REVIEW_GROMOV.md` was deleted 2026-09-07;
  recover with `git show 81bd59f:docs/REVIEW_GROMOV.md`.)
- `docs/foundations/LIT_economic-theory.md` §1 and §2 (`atkinson1970` for the fibration identity — **cite, do
  not re-derive**; `budish2011` for the honest approximate-CEEI form of the equal-budget claim)
- `docs/foundations/LIT_optimization.md` §Q1/§Q5 **if U0-lit has landed** — otherwise proceed and mark the
  `≤ k−1` descent as proved-here-pending-citation
- Read-only, for the four certificates' actual contracts: `td/solvers/cert_draw.py`,
  `td/channel.py::allocate_districts`. **Read only. No edits.**

## Open questions for ★0

- **★6** — if code against the instance is later permitted, this unit's P3 threshold becomes a
  measurement rather than a conditional.
- Not a blocker but worth surfacing on report: if P2 **refutes** — the four certificates do not all
  collapse — then `LENS_GROTHENDIECK.md`'s central reframing is weaker than it reads
  (`DOMAIN_optimization.md` §8 Q4) and the note keeps its five-certificate structure. Report that
  in those words; do not soften it.

## Branch

`wt/A1` (from `national-channel` at `a4eb488`); this is the A1 track's first unit

## Stop rule

If P1 turns out to require a hypothesis the instance may not satisfy (e.g. strict positivity of
every `g_i`, or `ρ = 0`), **state the hypothesis and stop** — do not weaken the claim until it is
provable, and do not assume the instance satisfies it. If P2 collapses three of four certificates
and the fourth resists, report three-of-four with the obstruction named; do not force the fourth.
If the `≤ k−1` descent cannot be proved and U0-lit has not returned a citation, mark it
**open** and carry P1/P2 without it — it is a supporting fact, not a premise.

**stop and report rather than improvise**

## Model

From `docs/MODEL_U1-cert.md` (2026-09-03). Headline: three of the four certificates collapse; the
fourth does not, and its resistance is informative rather than a defect. Measured on the real
instance, the fibre bound at the delivered roster is `EG_{S₁₃} = 60.697416` against a delivered
`V = 59.937470` — a 0.7599-nat optimality gap on the objective the business signs, where the
analytic balance ceiling gives only 9.6491 nats.

**Propositions.**

> **P1 (fibrewise relaxation bound).** Fix a staff set `S ⊆ R`, `|S| = k`. Let `Ĉ` be any
> extension of `C` to fractional assignments with `Ĉ(X_π) ≤ C(π)` at every integral `X_π`
> **(H3)**. Then for every integral coverage `(π,σ)` with `im σ = S`,
> `V(π,σ) ≤ EG_S`, with the convention `log 0 = −∞`. This holds at **every** `ρ ≥ 0`. `[proved]`

> **P1a (H3 is not decoration).** There exist instances and extensions `Ĉ` with
> `Ĉ(X_π) > C(π)` for which `max V > EG_S` by an arbitrary margin. `C_TV` satisfies H3 with
> equality. `[proved; counterexample in tools/verify/U1-cert/check_p1_p3.py]`

> **P1b (finiteness).** If `min_z M_z > 0` and `λ > 0` then `u_i(z) ≥ λ M_z > 0` for every `i,z`
> and `EG_S ∈ ℝ` for every `S`. On the instance `min_z M_z = 1.80577e-3 > 0`. `[proved; hypothesis
> verified on the instance]`

> **P1c (the closed-form outer bound).** If the headroom condition holds in the strong form
> `u_i(z) ≤ M_z` for all `i,z`, then for every staff set `S`, `EG_S ≤ k log(M(Z)/k)` — the
> analytic balance ceiling — and the same bound holds for the cardinality-relaxed perspective
> relaxation `EG_R`. `[proved]`

> **P2 (the collapse — three of four).** Of the four certificates in `td/solvers/cert_draw.py`:
> - **P2.1 `cert_balance_ceiling` is a degeneration of `EG_S`'s dual.** `[proved]`
> - **P2.2 `cert_integer_balance_floor` is NOT a degeneration or restriction of the dual.** Its LP
>   relaxation has optimum `t = 0`, so its LP root bound is vacuous — which is what rules out its
>   being a degeneration of a linear dual. *(Corrected 2026-09-03 per `VERIFY_U1-cert` §4: an
>   earlier version said "carries no dual bound at all", which is too strong — when the MILP
>   closes, branch-and-bound does return a valid `t_lower > 0`.)* `[proved]`
> - **P2.3 `cert_assignment_at_centers` is a restriction, by a named triple specialisation.**
>   `[proved]`
> - **P2.4 `cert_power_diagram` is the KKT system of the same `τ = 0`, `ρ > 0` fibre.** Every
>   optimum `X*` of that fibre is supported on the power (Laguerre) diagram of the pinned centers
>   with weights `ω_j = 1/(ρ m*_j)`, and `ω` is dual-optimal **iff that LP is nondegenerate**.
>   `[proved; the nondegeneracy caveat is new and is a caveat on an existing certificate]`

> **P3a (the split-unit count) — corrected 2026-09-03 per `VERIFY_U1-cert`.** At `ρ = 0`, every
> vertex of the optimal face splits at most `k − 1` units, heterogeneous `u` or not.
> `brieden2017 Lem. 4`'s `≤ |S| − 1` therefore needs no replacement and is not a `τ = 0`
> privilege. `[proved — VERIFY_U1-cert §5; the standard linear-Fisher-market / transportation
> forest argument, to be cited rather than re-proved]`

> **P3a′ (the coarser rank statement, kept as true but non-minimal) — corrected 2026-09-03.**
> `rank(A) = n + k` in general and `n + k − 1` exactly when the `u_i` are mutually proportional;
> `A` is not a minimal description of the face, so the `≤ k` reading is valid but never attained.
> `[proved; superseded as a bound by P3a]`

> **P3b (the gap in value, not count).** `0 ≤ EG_S − max_integral V ≤ −Σ_{i∈S} log(1 − L_i/g*_i)
> ≤ −log(1 − M(F)/min_i g*_i)`. `[proved]`

> **P3c (the a-priori form of P3b is vacuous on this instance).** Bounding `M(F)` a priori by the
> `k−1 = 12` largest zips gives `M(F) ≤ 249.392`, so `M(F)/g_min = 2.407 > 1` and the bound is
> `+∞`. With the measured `F` (10 units, `M(F) = 66.168`) the bound is `1.018` nats; the gap
> actually realised is `5.131e-4` nats. `[measured]`

> **P4 (what the fibre bound says about the instance).** At the delivered roster `S₁₃`,
> `EG_{S₁₃} = 60.697416` (certified bracket width 7.1e-15 nats), so no coverage staffed by those
> 13 reps is worth more than 0.7599 nats above the delivered draw — but the rounded EG vertex
> abandons balance (`M`-spread `≥ 50 %`). `[measured; bracket corrected 2026-09-03 per
> VERIFY_U1-cert]`

**Numbers computed** (§4 of the model; interpreter `.venv/bin/python3`, CPython 3.13.15, numpy
2.5.2, scipy 1.18.1).

| quantity | value |
|---|---|
| `T = M(Z)` | `2745.611187` |
| analytic balance ceiling `k log(T/k)` | `69.5865251441` |
| `V(delivered)` | `59.9374697984` |
| `EG_{S₁₃}` primal / dual | `60.6974156139` (both) |
| certified bracket width | `7.1e-15` (VERIFY, fsum); `1.35e-13` at this unit's iterate |
| `EG_{S₁₃} − V(delivered)` | `0.7599458154` nats |
| `k log(T/k) − EG_{S₁₃}` | `8.8891095303` nats |
| tightness factor `(ceiling − V)/(EG − V)` | `12.6970` |
| spread of `M_j` / spread of realised `g_i` on the delivered draw | `0.7813 %` / `60.65 %` |
| split units `|F|` (this unit's vertex / VERIFY's vertex) | `10` / `10` (both `≤ k−1 = 12`) |
| `M(F)` (this unit's vertex / VERIFY's vertex) | `66.1681` (`2.410 %`) / `87.6585` (`3.193 %`) |
| integrality gap realised | `5.131e-4` nats / `1.919e-3` nats (vertex-dependent, `≤` both bounds) |

**Open (what this unit could not settle).**

1. `max_S EG_S` and `EG_R` — only `EG_{S₁₃}` was solved; bracketed in `[60.697416, 69.586525]`.
2. The balance-constrained fibre `EG^bal_S` — bracketed only as `[59.9375, 60.6974]`; this became
   U8-band's object.
3. `ρ`-aware fibres — nothing here computes an `EG_S` with `ρ > 0` on the real instance.
4. ~~The `≤ k` heterogeneous split-unit bound's provenance.~~ Closed 2026-09-03 — not a result;
   `≤ k − 1` holds heterogeneously via the MBB-restricted face (`VERIFY_U1-cert` §5).
5. The displacement modulus — the prices `p_z` are computed but not converted into a lower bound
   on displacement-to-any-better-coverage; this became U4-disp's question.
6. `filler_capture` (FRAME §9) — P1c's applicability is conditional on it; the sharp correction is
   `+0.258438` nats at `"full"`.

Full report: `git show 8b14eee:docs/MODEL_U1-cert.md`.

## Verify

From `docs/VERIFY_U1-cert.md` (2026-09-03, `math-verify`). Brief acceptance: **P1 VERIFIED**, **P2
VERIFIED** (three-of-four collapse confirmed, the fourth's resistance confirmed), **P3 at better
than PLAUSIBLE — VERIFIED with one refutation inside it** (P3a's `≤ k` reading).

| # | proposition | verdict |
|---|---|---|
| 1 | P1 — the relaxation bound | **VERIFIED** |
| 2 | P4 / headline — `EG_{S₁₃} = 60.697415613859555`, bracket `7.1e-15` | **VERIFIED** (bracket tighter than claimed) |
| 3 | P2.1 — `cert_balance_ceiling` is `D(p)` at `p_z = (k/T)M_z` | **VERIFIED** |
| 4 | P2.2 — the integer floor is not a degeneration of the dual | **VERIFIED, with one over-statement corrected** |
| 5 | P1c — `EG_S ≤ k log(T/k)` under `u_i ≤ M_z`; same for `EG_R` | **VERIFIED as an implication**; instance-side numbers coarser than the proposition |
| 6 | P3a — rank `n+k`; splits `≤ k`; "`≤ k−1` is a `τ=0` privilege" | **split verdict: rank claim VERIFIED, `≤ k` VERIFIED (never attained), the interpretive claim REFUTED** |
| 7 | P3b / P3c — the value bound, and its a-priori vacuity | **VERIFIED**; §4.3's split-set numbers are vertex-dependent, not instance invariants |
| 8 | P2.4 — power weights are the EG multipliers, with the nondegeneracy caveat | **VERIFIED** (strengthened) |
| 9 | P2.3 — assignment at pinned centers is the ε-constraint integral restriction | **VERIFIED numerically**; one specialisation step over-sold |
| 10 | P1a / P1b — H3's necessity, and finiteness | **VERIFIED** (P1a strengthened) |

**REFUTED row, one-line reason.** Row 6, P3a's interpretive half: the model's claim that the
lens's `[standard, brieden2017 Lem. 4]` `≤ |S| − 1` split-unit bound is a `τ = 0` privilege, with
the honest heterogeneous statement being `≤ k`, is REFUTED — the equilibrium/forest argument on
the MBB-restricted face gives `≤ k − 1` with no hypothesis on the `u_i`, so the lens's citation
stands untouched and the unit contributes no new split-unit result.

**Two things the model was told to change** (both applied in place in `MODEL_U1-cert.md`, 2026-09-03).
(a) P3a's headline claim of a `≤ k` heterogeneous result is false; `≤ k−1` holds heterogeneously.
(b) The `+3.360`-nat `filler="full"` correction was `k·log ν_max`, not the `Σ_{i∈S} log ν_i` P1c
actually states; the sharp figure at `S₁₃` is `+0.2584` nats.

**Artifacts**, moved out of the deleted per-unit artifacts directory to `tools/verify/U1-cert/`:
`eg.py` (the fibre program, its dual, the toy), `check_p1_p3.py`,
`check_p2.py`, `instance_numbers.py`, `verify_instance.py`, `verify_props.py`, `verify_split.py`,
`verify_p23_p24.py`. Re-run:

```
tools/verify/U1-cert/verify_instance.py
tools/verify/U1-cert/verify_props.py
tools/verify/U1-cert/verify_split.py
tools/verify/U1-cert/verify_p23_p24.py
```

All four print `FAILURES: none` and exit `0`.

Full report: `git show 8b14eee:docs/VERIFY_U1-cert.md`.

## Code verify

none yet
