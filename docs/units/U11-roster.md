# Unit U11-roster — roster enumeration under the (★) screen, the Nash-tie margin, and tie-aware intervals

`DOMAIN_optimization` §2.14–§2.15, §4 Stage 4, §5 rows 0c and 5; `DOMAIN_economic-theory` §2.10,
N11; `LENS_GROMOV` ledger U16, U17, U19; decides the report format ★10 (D7). Gated on U8-band
for the `EG^bal` solver; the margin and the enumeration order need only the gain matrix.

## Spec (verbatim from `docs/DOMAIN_optimization.md` §2.14, §2.15)

> ```
> EG^bal_S(δ)  ≤  EG_S  ≤  k · log( (B_tot + w·P_S) / k ).                    (★)
> ```
> Enumerate rosters in decreasing `P_S` (no-good cuts on the `P₁₃` master), solving
> `EG^bal_S(δ)` only for those whose (★) exceeds the best value found so far. **This is
> branch-and-bound over rosters with a valid bound.**
> (i) The margin itself, exactly: the second-best assignment value, obtained by `k` Hungarian
> re-solves each forbidding one matched edge and taking the best — milliseconds. (ii) The *set*
> of rosters within the tier-2 floor of the optimum … (iii) A tie-aware report: each
> `S₁₃`-conditional number as an **interval over that set**, not a point.

## Files owned

`td/solvers/roster_enum.py` · `tests/test_roster_enum.py` · `docs/MODEL_U11-roster.md` (spec,
first) · `docs/CODEVERIFY_U11-roster.md` · `battery/results/u11_roster_<date>/`.

## Files forbidden

Every other unit's owned files (`td/solvers/eg_band.py`, `tools/measure/premium.py` by import
only) · `docs/FRAME.md` · `docs/BRIEF.md` · `docs/APPROACHES.md` · `docs/LENS_*.md` ·
`docs/DOMAIN_*.md` · `docs/LIT_*` · `CLAUDE.md` · existing `td/` modules · `battery/figures/`.

## Agent → verifier

`python-typed` → `code-verify` (launch from a session started in `.claude/worktrees/A1`).

## Acceptance

1. The exact Nash-tie margin on both draws (seed 3: expect 1.37e-2; seed 9: 8.1e-3, the
   `CODEVERIFY_U7-meas` numbers) by `k` Hungarian re-solves, and the near-optimal roster sets at
   5e-3 and 1.5e-2 nats with their cardinalities (N11).
2. The (★) screen recomputed (60.7615 at `P_S`, 60.8025 at `P₁₃`, FRAME §6) and used as the stop
   rule: the enumeration log lists every roster visited, its `P_S`, its (★), and whether
   `EG^bal_S(δ)` was solved; the `P₁₃` roster (R0009, R0012 in for R0017, R0018) is solved first.
3. `max_S EG^bal_S(δ)` over the survivors at `δ ∈ {0.02, 0.05, 0.10}` with the (★) upper bound
   beside it, so the roster-free bound is a bracket, not a point (U19).
4. The tie-aware report: `P_S`, U4, U8, `EG^bal_{S}(δ)` as intervals over the 5e-3 set.
5. Tests: on a seeded 6-rep / 12-zip fixture, the margin equals brute force over all second-best
   assignments; the (★) bound is never below the true `EG_S` (brute-force EG on the toy); the
   enumeration with the stop rule returns the same argmax as exhaustive enumeration; existing
   tests green. `mip_rel_gap = 0.0` on the `P₁₃` master; provenance and byte-identity as U7-meas.

## Numbers to compute first

The margin (0c) · `|{S : V_S ≥ V_{S₁₃} − 5e-3}|` (N11) · (★) at every enumerated roster · the
count of rosters actually solved.

## Inputs to read (paths and sections only)

`docs/DOMAIN_optimization.md` §2.14–§2.15 · `docs/DOMAIN_economic-theory.md` §2.10, N11, §4
step 7 · `docs/MODEL_U7-meas.md` §1, §3.1, §6 · `docs/CODEVERIFY_U7-meas.md` (the tie finding,
row 4 caveats) · `docs/LIT_optimization.md` §5 (absence A: no submodularity for `S ↦ EG_S`), §7
(stability radius / `k`-best assignments) · `tools/measure/premium.py` (`book_matrix`,
`best_roster`, `coverage_premium`, the `P₁₃` MILP) · `td/channel.py::match`.

## Open questions for ★0

★10 (tie-break policy) is decided *on* this unit's evidence; the unit reports both the disclosed
tie-break and the near-optimal set so either choice is served. ★2 (audited book) bears on
deployability of the selection, not on the computation.

## Branch

`wt/A1` (or `wt/U11-roster` from `wt/A1`)

## Stop rule

If the near-optimal roster set at 5e-3 nats exceeds 100, stop enumerating `EG^bal` at that
point and report the cardinality — the tie-break is then doing the selecting and the report
must lead with that (`DOMAIN_economic-theory` §2.10 failure mode). If (★) at `P₁₃` is below the
best `EG^bal` found (it cannot be, by validity), report the contradiction rather than the number.

**stop and report rather than improvise**
