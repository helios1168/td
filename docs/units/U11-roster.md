# Unit U11-roster — roster enumeration under the (★) screen, the Nash-tie margin, and tie-aware intervals

Status: open

`DOMAIN_optimization` §2.14–§2.15, §4 Stage 4, §5 rows 0c and 5; `DOMAIN_economic-theory` §2.10,
N11; `LENS_GROMOV` ledger U16, U17, U19; decides the report format ★10 (D7). Gated on U8-band
for the `EG^bal` solver; the margin and the enumeration order need only the gain matrix.

## Spec (verbatim from `docs/foundations/DOMAIN_optimization.md` §2.14, §2.15)

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

`td/solvers/roster_enum.py` · `tests/test_roster_enum.py` · this file's `## Model` (spec,
first) · `## Code verify` · `battery/results/u11_roster_<date>/`.

## Files forbidden

Every other unit's owned files (`td/solvers/eg_band.py`, `tools/measure/premium.py` by import
only) · `docs/foundations/FRAME.md` · `docs/foundations/BRIEF.md` · `docs/foundations/APPROACHES.md` · `docs/foundations/LENS_*.md` ·
`docs/foundations/DOMAIN_*.md` · `docs/foundations/LIT_*` · `CLAUDE.md` · existing `td/` modules · `battery/figures/`.

## Agent → verifier

`python-typed` → `code-verify` (launch from a session started on `main`).

**Tooling.** `cat`/`head`/`tail`/`sed`/`awk`/`grep` on a file are blocked by the
`enforce-file-tools.sh` hook — use `Read`/`Edit` and the Serena symbol tools instead
(`git show ae2b18d:docs/RUNS_PLAN.md:83-89`).

## Acceptance

1. The exact Nash-tie margin on the single k=18 **seed 2** draw (v1's seed-3/seed-9 pair is
   retired) by `k` Hungarian re-solves, and the near-optimal roster sets at 5e-3 and 1.5e-2 nats
   with their cardinalities (N11). **The v2 margin itself has not been measured** — v1's
   `1.37e-2` / `8.1e-3` numbers do not carry over; do not assume a value, compute it.
2. The (★) screen recomputed on v2 (P0-C, complete, math-verified): `B_tot = 3268.4069219934404`;
   (★) = `96.55406280784752` at `P_S` — the per-roster screen, **this is the rung that drives
   U11's own prune** (the formula above, evaluated at each candidate roster's own `P_S`) — and
   `96.79300971267465` at `P₁₈` — the roster-free bound over all rosters (U19, Acceptance #3), a
   **different rung, not U11's prune** — against `V = 95.75519165924108` and
   `EG_{S₁₈} = 96.53215175`. Used as the stop rule: the enumeration log lists every roster
   visited, its `P_S`, its (★), and whether `EG^bal_S(δ)` was solved; the `P₁₈` roster (R0007,
   R0011, R0012, R0020 in for R0004, R0021, R0028, R0038) is solved first.
   **On the `P_S` rung — the one that drives this unit's prune — the screen tightens on v2.**
   Against `EG_{S₁₃} = 60.6974156139` (v1) / `EG_{S₁₈} = 96.53215175` (v2), the `P_S` slack goes
   `0.0641` (v1) → `0.0219` (v2), **2.9× tighter**, so U11 prunes *more* on v2, not less. The
   `P₁₈` (roster-free bound) slack moves the opposite way, `0.1051` (v1) → `0.2609` (v2), 2.5×
   looser — but that is U19's bound, not this unit's screen; do not conflate the two rungs.
   (P0-C separately reports the roster gap at 0.249 nats on v2, up from 0.043 on v1 — a distinct
   quantity from either slack above.)
3. `max_S EG^bal_S(δ)` over the survivors at `δ ∈ {0.02, 0.05, 0.10}` with the (★) upper bound
   beside it, so the roster-free bound is a bracket, not a point (U19).
4. The tie-aware report: `P_S`, U4, U8, `EG^bal_{S}(δ)` as intervals over the 5e-3 set.
5. Tests: on a seeded 6-rep / 12-zip fixture, the margin equals brute force over all second-best
   assignments; the (★) bound is never below the true `EG_S` (brute-force EG on the toy); the
   enumeration with the stop rule returns the same argmax as exhaustive enumeration; existing
   tests green. `mip_rel_gap = 0.0` on the `P₁₈` master; provenance and byte-identity as U7-meas.

## Numbers to compute first

The margin (0c) · `|{S : V_S ≥ V_{S₁₈} − 5e-3}|` (N11) · (★) at every enumerated roster · the
count of rosters actually solved.

## Inputs to read (paths and sections only)

`docs/foundations/DOMAIN_optimization.md` §2.14–§2.15 · `docs/foundations/DOMAIN_economic-theory.md` §2.10, N11, §4
step 7 · `docs/MODEL_U7-meas.md` §1, §3.1, §6 · `docs/CODEVERIFY_U7-meas.md` (the tie finding,
row 4 caveats) · `docs/foundations/LIT_optimization.md` §5 (absence A: no submodularity for `S ↦ EG_S`), §7
(stability radius / `k`-best assignments) · `tools/measure/premium.py` (`book_matrix`,
`best_roster`, `coverage_premium`, the `P₁₈` MILP — the code keys `P13` / `P13_solve` are kept
unchanged, a naming fossil, `premium.py` still emits them at k=18; don't chase it) ·
`td/channel.py::match`.

## Open questions for ★0

★10 (tie-break policy) is decided *on* this unit's evidence; the unit reports both the disclosed
tie-break and the near-optimal set so either choice is served. ★2 (audited book) bears on
deployability of the selection, not on the computation.

## Branch

`main` (or `wt/U11-roster` from `main`)

## Stop rule

If the near-optimal roster set at 5e-3 nats exceeds 100, stop enumerating `EG^bal` at that
point and report the cardinality — the tie-break is then doing the selecting and the report
must lead with that (`DOMAIN_economic-theory` §2.10 failure mode). If (★) at `P₁₈` is below the
best `EG^bal` found (it cannot be, by validity), report the contradiction rather than the number.

**stop and report rather than improvise**

## Model

none yet

## Verify

none yet

## Code verify

none yet
