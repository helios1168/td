# Solver traps — read before debugging a certificate or a premature stop

Four traps, each found the hard way, each costing a debugging cycle. Canonical numbering matches
`CLAUDE.md` traps 12–15; that file is the authority if these drift.

---

## Trap 12 — a "certificate" that is only `mip_rel_gap = 1e-4`

`scipy.optimize.milp` defaults HiGHS to a **1e-4 relative MIP gap**. A loop that stops when its
master value meets the incumbent can therefore sit ~1e-4·|obj| above it and still report success.
On the C8 pair at ρ=0 that was 6.3e-4 nats — six orders of magnitude looser than `CERT_TOL`.

- `nash_exact` sets `mip_rel_gap=0.0`; the legacy `solve_contiguous_nash` loop did not.
- Pass `milp_options=dict(mip_rel_gap=0.0)` for a real certificate. On the C8 pair this also
  **moved the incumbent** (log-product 6.47177 → 6.47234, 9 iterations instead of 14).
- The harness reports the loose case as status `gap_limit`, not `optimal`. That is correct
  behaviour, not a bug to route around.

---

## Trap 13 — root-based separator cuts are *invalid* on a disconnected pair graph

**This is a formulation bug, not a solver bug, and it is the one that produces unsound bounds.**

`solve_contiguous_nash` fixes one root per side. If a cut is generated for a component `S` of a's
side whose outside neighbours lie inside a *stray* component, the cut (e.g. `x_8 ≤ x_11`) forces
growth toward a root that is **unreachable**. It excludes allocations that are feasible under
component-wise contiguity.

Consequences:

1. The master problem is no longer a relaxation. Its "optimal" can sit *below* a feasible iterate
   the loop already saw — observed at 6.283 vs 6.436 (S1_aligned n=50 seed=2, pair A1/B1,
   components `{8,11}` and `{14,15,16,39,44,46}`).
2. The dual bound is **unsound, not merely loose**, whenever `pair_components > 1` — which was
   three of the six named failures.
3. `contig_methods/current.py` detects `LB > UB` after recomputation and downgrades to
   `heuristic` with `UB=None`.

**The rule for every root-based formulation** (flow, SCIP/CBC trees, loop_v2): **one root per pair
component**, or selectable roots. Nothing else fixes it.

---

## Trap 14 — HiGHS 1.15 "Status 4: Solve error" under 1e-9 tolerances

`*_feasibility_tolerance=1e-9` makes HiGHS fail outright on some instances (C4_contested A0/B0,
27 zips, after two OA rounds) — and `territory.solve` then *silently* fell back to the prefix
heuristic (8.96110 vs the exact 8.96316).

- The 1e-9 tolerances exist to stop a 1e-6-default stall, so you cannot simply loosen them.
- 1e-8 solves the same instance exactly.
- `nash_exact` now retries down a ladder (1e-9 → 1e-8 → HiGHS defaults) on "Solve error", and
  `solve` warns when it falls back. **Any new method forwarding tolerance options to HiGHS must
  guard the same way** (W4's `flow` does).

### SCIP-specific (W6)

Any lazily separated SCIP model needs:

- `misc/allowstrongdualreds` and `misc/allowweakdualreds` **off**. With them on, presolve fixed a
  tangent-bounded variable to its bound *before the lazy rows existed* and "certified" a
  suboptimal warm start.
- `numerics/feastol=1e-9` — the residual gap is primal slack ≈ 2·feastol.
- Gains as `ga <= Σu·x`, **not** `==`; with equality, presolve multi-aggregates them and `trySol`
  dies.
- The gain lower bound from the incumbent (`exp(LB0)/Σu_other`), **not** 1e-9 — the log's 1e9
  gradient destabilises the LP.

---

## Trap 15 — an abort reported as `time_limit` silently disables the retry ladder

`scip_tree` maps SCIP's LP abort (`error in LP solver`, status `unknown`) to `time_limit`, so the
harness counts crashes rather than capped runs under `errors`. But its own `solve()` then
continued the 1e-7/1e-6/OA ladder **only on status `error`**. Every S2 pair above ~125 zips
stopped after 1–58 s of a 1200 s budget and the ladder never ran once.

The reported "scale wall at ~125 zips regardless of budget" was this bug.

Rules that follow:

- **A retry decision must key on the engine's stop reason** (`extra["retryable"]`), never on the
  harness-facing status. The two are deliberately different vocabularies.
- SCIP's `limits/time` runs on its own clock; under load it can fire at ~half the wall budget.
  `_short_stop` retries such a stop.
- A certificate from a rung at feastol `f` is a **floating-point** certificate, rigorous only to
  O(f·‖duals‖) — usually far tighter in practice (simplex vertices are exact unless a tolerance
  binds: C1-seed2 A3/B3 certified to 2e-9 from a 1e-6 rung), but a residual of 1.1e-7 / 3.0e-8
  may be *tolerance rather than search*, and **the harness cannot tell**.

The independent checks are cross-method agreement and brute force at n ≤ 20. A rigorous
certificate needs an exact post-hoc bound (candidate unit W6c).
