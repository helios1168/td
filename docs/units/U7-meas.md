# Unit U7-meas — the measurement stage *(launched 2026-09-03 on `wt/A1`; ★6 lifted in full)*

Status: done

**This is the unit both domains would have run first.** It was blocked by the plan's own
constraint ("nothing that touches `td/` code yet") and by the instance's absence; both are
lifted — the user answered ★6 in full on 2026-09-03 and the instance is at this worktree's
root. It runs as the A1 track's kill experiment; the spec is `docs/MODEL_U7-meas.md`.

## Spec (verbatim from `docs/foundations/DOMAIN_optimization.md`:§4, Stage 0)

> **Stage 0 — measure before formulating (no solver, hours).** Run §5 in full. Both lenses
> converge on this and it is the only step with no dependency on any open decision. Two of its
> outputs can *cancel the rest of this plan*: if `P₀ ≈ P*(A)` and the contested-among-the-13 count
> is small, the premium is not reachable by redrawing and the two-stage scheme was right all along.

## Files owned

- `tools/measure/__init__.py`, `tools/measure/premium.py` — read-only analysis over `td/`;
  no existing `td/` module changes
- `tests/test_measure.py`
- `docs/MODEL_U7-meas.md` (the measurement spec) · `docs/CODEVERIFY_U7-meas.md`
- `battery/results/meas_20260903/` for outputs (gitignored)

## Files forbidden

Every other unit's owned files · `docs/foundations/FRAME.md` · `docs/foundations/BRIEF.md` · `docs/foundations/LENS_*.md` ·
`docs/foundations/DOMAIN_*.md` · `docs/channel_note/**` · `CLAUDE.md` · **`battery/figures/`** (primary
artifacts, `CLAUDE.md`) · existing `td/` modules except by explicit extension agreed at launch.

## Agent → verifier

`python-typed` → `code-verify`

## Acceptance

Tests pass (the existing 151 stay green), the type checker is clean, and every number is emitted
with the run id and the instance hash that produced it. `mip_rel_gap = 0.0` on any certification
solve (trap 12); a `time_limit` abort must never be reported as a bound (trap 15). Byte-identical
re-run from the same instance.

## Numbers to compute first

`DOMAIN_optimization.md` §5 numbers 1–9 and `DOMAIN_economic-theory.md` §5 N1–N6. In the order the
lenses recommend (`LENS_GROMOV.md` §"Recommended order"): `P₀`, `P*(A)`, the `g`-spread (U1), the
contested-among-the-13 count (U4) — all four from one script — then the hand-drawn baseline (U10),
then the noise floor (U6, if a domain plan exists for it). N1–N3 do not depend on any of these.

## Inputs to read (paths and sections only)

`docs/foundations/DOMAIN_optimization.md` §5 · `docs/foundations/DOMAIN_economic-theory.md` §5 · `docs/foundations/LENS_GROMOV.md`
Move 4 and the U-ledger · `docs/foundations/FRAME.md` §5 (data defects), §6 · `docs/CODE_MAP.md` ·
`docs/foundations/archive/TEST_PLAN.md` · `td/instance.py`, `td/channel.py`, `td/solvers/centers.py`,
`td/solvers/cert_draw.py`

## Open questions for ★0

Answered 2026-09-03: ★6 lifted in full; the instance is at this worktree's root
(`instance_descaled.json.gz`, gitignored, hand-copied) together with the two k=13 draws under
`battery/results/`. The unit runs on `wt/A1`.

## Branch

`wt/A1` (from `national-channel` at `a4eb488`)

## Stop rule

If a number cannot be computed because the instance is malformed or a defect in FRAME §5 bites
(the 6 coordinate-less zips, the headroom repairs, the 6-significant-figure rounding), report the
defect and the affected number — do not repair the data to get a number out.

**stop and report rather than improvise**

## Model

From `docs/MODEL_U7-meas.md` (2026-09-03). Defines the **premium ladder**
`P₀ ≤ P*(A) ≤ P_S ≤ P₁₃ ≤ P_free` — the book that lands with its own holder, at the committed
map/roster, the premium-optimal roster at that map, the ceiling over the selected 13's staff set,
the ceiling over the best 13, and the ceiling over all reps — and reads the gaps as the matching,
map and roster components of unrealised premium. Section 6 states the verdict rule for the A1 kill
experiment: convert a premium gap `ΔP` to nats via `w·ΔP/ḡ`, call it small if `≤ 5e-3`.

**Measured 2026-09-03** (`battery/results/meas_20260903/`, `ḡ = 102.10`):

| draw | `P₀` | `P*(A)` | `P_S` | `P₁₃` | `P_free` | match gap | map gap | roster gap |
|---|---|---|---|---|---|---|---|---|
| seed 3 | 37.82% | 37.82% | 51.43% | 52.34% | 79.44% | 0 nats, small | 13.61% of book, 0.640 nats | 0.92%, 0.043 nats |
| seed 9 | 39.28% | 39.41% | 51.43% | 52.34% | 79.44% | 0.14%, 0.0065 nats | 12.15%, 0.568 nats | 0.92%, 0.043 nats |

**Verdict: A1 is not killed.** The matching is already premium-optimal on the committed map; the
map gap is two orders above the floor; the roster gap is eight times the floor. Cross-read with
`MODEL_U1-cert` P4: at this roster no coverage beats the committed draw by more than 0.760 nats
(the EG bound), and the EG vertex that realises it has an `M`-spread above 50%. Other numbers: U1
`g`-spread 60.65% vs `M`-spread 0.781% (A0's soft kill fires); U4 83 zips, 6.12% of `M`; U8 pooled
`corr(T_z, M_z) = 0.650`.

Full report: `git show 8b14eee:docs/MODEL_U7-meas.md`.

## Verify

none yet

## Code verify

From `docs/CODEVERIFY_U7-meas.md` (2026-09-03, `code-verify`, against `tools/measure/premium.py`).
**15 VERIFIED · 2 REFUTED · 0 INCONCLUSIVE.** Both REFUTED rows are defects in the model text, not
in the code, and neither moves a number.

| # | claim | verdict |
|---|---|---|
| 1 | §1 `P₀ = Σ_j b_{σ₀(j),j}` ↔ `roster_premium` | VERIFIED |
| 2 | §1 decomposition `g = B_j + w·b`, `w = 0.42` | VERIFIED |
| 3 | §3 `P*(A)` ↔ `best_roster` (Hungarian on `−b`) | VERIFIED |
| 4 | §3 `P_S` ↔ `coverage_premium` at the Nash image | VERIFIED |
| 5 | §3 `P₁₃` ↔ `max_k_coverage` MILP | VERIFIED |
| 6 | §3 `P_free` ↔ `coverage_premium(range(n))` | VERIFIED |
| 7 | §3 ladder `P₀ ≤ P*(A) ≤ P_S ≤ P₁₃ ≤ P_free` | VERIFIED (justification text imprecise) |
| 8 | §3.1 MILP formulation, trap 12, trap 15 | VERIFIED |
| 9 | §3.1 "the greedy solution seeds it" | **REFUTED** (model text — `scipy.optimize.milp` has no warm-start option; greedy is reported alongside, never used as a seed) |
| 10 | §4 worked example | VERIFIED |
| 11 | §3/§4 `S₁₃ = im σ₀` under an explicit roster override | **REFUTED** (model text is internally inconsistent between §3 and §4; the code implements the only coherent reading — `S₁₃` is always the Nash image — and both real runs are unaffected because `σ₀ = σ_nash` there) |
| 12 | §5 U1 realised-gain spread beside the `M`-spread | VERIFIED |
| 13 | §5 U4 — 83 zips, 6.1209% of `M` | VERIFIED |
| 14 | §5 U8 — `corr(T,M) = 0.6500` pooled | VERIFIED |
| 15 | §5 `V` at `σ₀` and at the `P*(A)` roster | VERIFIED |
| 16 | §6 verdict conversion `w·ΔP/ḡ` and the `small` flag at 5e-3 | VERIFIED |
| 17 | §7 provenance, both draws, byte-identical re-run, stop rule | VERIFIED |

Mechanical gates: `uvx pyright` → 0 errors/warnings/informations; `tests/run_all.py` → 184
passed, 0 failed (10 in `test_measure.py`). Byte-identical re-run of both draws.

**Artifacts**, moved out of the deleted per-unit artifacts directory to `tools/verify/U7-meas/`:
`oracle_ladder.py`, `oracle_nash_ties.py`, `oracle_p13_bnb.py`,
`oracle_toy_and_monotonicity.py`, `oracle_boundaries.py`.

Full report: `git show 8b14eee:docs/CODEVERIFY_U7-meas.md`.
