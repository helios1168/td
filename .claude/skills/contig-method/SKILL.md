---
name: contig-method
description: The frozen contiguity-harness contract for battery/code/contig_methods/. Use when writing, reviewing, debugging, or benchmarking a contiguity solver method (scip_tree, flow, flow_pwl, loop_v2, cbc_tree, current, brute, warm, prep), when a method returns a wrong status or a bad certificate, or when adding a new method module to the registry. Covers what solve() receives, what it must return, component-wise feasibility, certificate rules, and the four solver traps that have already cost a debugging cycle each.
---

# Contiguity harness contract

Every method in `battery/code/contig_methods/` implements one frozen interface. It was frozen
at the U1a merge (PLAN.md Part C.1) and **every later unit implements against it** — changing it
is a main-session decision, not something to work around inside a method.

## Read first

- **`battery/code/contig_methods/base.py`** — its module docstring *is* the contract, and it is
  the authority. Read it before writing a line. Don't rely on this file's summary where the two
  disagree; `base.py` wins.
- `battery/code/contig_methods/__init__.py` — auto-discovery registry. A module is registered
  simply by exposing `NAME` and `solve`; `VARIANTS = {key: {kwargs}}` adds variant keys verbatim.
- `references/solver-traps.md` (here) — the four hard-won solver traps, collected from CLAUDE.md
  traps 12–15. Read it before debugging a certificate or a premature stop.

## The interface

```python
NAME: str                 # registry key
EXACT: bool               # True if the method can certify (produces a global UB)
MAX_N: int | None         # optional size cap (brute force)
VARIANTS: dict[str, dict] # optional {variant_name: extra kwargs for solve}

def solve(G, nodes, *, theta, lam, rho, respect_state, time_limit, seed,
          warm_start=None, reductions=None, trace=None, kappa=0.0, **opts) -> Result
```

## Hard rules — each of these has bitten someone

1. **Never recompute `u_a` / `u_b`.** Always `base.utilities(G, nodes, theta, lam, kappa)`.
   W11's travel-cost κ changes them; a method with its own copy silently diverges.
2. **Never mutate `G`.** It's a copy, already state-filtered and rescaled by the harness
   (`filter_pair`, `rescale_pair`).
3. **Never delete edges.** `respect_state` is *always* `False` by the time a method sees it —
   the harness has already removed cross-state edges (C.0 #5). Filtering again double-counts.
4. **Feasibility is component-wise, not global.** For every connected component `K` of the
   filtered pair graph, `S∩K` and `K∖S` must each be connected *or empty*. A pair graph is
   often already disconnected before contiguity is imposed. This is the single most important
   line in the contract — see trap 13 in `references/solver-traps.md` for the invalid-cut
   failure it causes.
5. **Self-enforce `time_limit`, one solver thread, deterministic in `seed`.**
6. **Report progress through the trace.** `trace.incumbent(to_a, obj)` on every improved
   feasible allocation, `trace.bound(ub)` on every tightened global bound. The harness fills
   `Result.trace` and `t_first_feasible` from it.
7. **`rho` defaults to 0 everywhere.** Contiguity is a hard constraint (decision 2026-08-28);
   the perimeter penalty is a secondary axis for the `current` control only.

## Statuses — claim them precisely

| status | when |
|---|---|
| `optimal` | **only** when the method's own `UB - LB <= CERT_TOL (1e-8) + eps` on a feasible allocation. The validator rejects anything looser. |
| `gap_limit` | the loop converged but the *engine* stopped on a relative-gap tolerance. Carries a valid UB. |
| `time_limit` / `iteration_limit` | last iterate, feasible or not (`LB=None` if not). |
| `heuristic` | `UB=None`. |
| `infeasible` / `error` | may carry no allocation. |

`ub_scope="rooted"` means the bound covers a *restriction* (a root-fixed formulation). The
harness downgrades a rooted `optimal` to `status_eff="optimal_rooted"` with
`valid_certificate=False`. Declare it honestly — the downgrade is the design, not a penalty.

`EPS_CERT = 5e-3` nats is a **programme-level** second tier for production sizes (T2+), grounded
in the objective's own measured noise floor. It does **not** change method semantics: `optimal`
still requires `CERT_TOL`. Only harness scoring reads it.

## What the harness recomputes vs. trusts

- **Recomputed, never trusted:** `g_a`, `g_b`, product, perimeter, `LB`, `pieces_*`,
  `excess_pieces`, the fairness audit, `cost_of_contiguity`, gaps, `t_total`.
- **Trusted:** `status`, `UB`, `ub_scope`, `eps`, `iters`, `n_cuts`, `n_tangents`, `nodes`,
  `t_first_feasible`, `extra`.

So there is no point massaging the recomputed fields, and a dishonest `status` or `UB` is the
one thing that can corrupt a result set.

## Verifying a method

```
.venv/bin/python3 battery/code/tests/run_all.py
```

Plus: cross-check against `brute` at n ≤ 20 (the only ground truth), and check agreement with
another exact method where both certify. A certificate from a loosened tolerance rung is a
*floating-point* certificate — rigorous only to O(f·‖duals‖) — and the harness cannot tell that
from a real one. Cross-method agreement is what catches it.

**Never write under `battery/figures/`** — those are primary artifacts. Harness output goes to
`battery/results/contiguity/<run_id>/`.

## When you're stuck

Stop and report rather than improvise. The contract is frozen; if a method genuinely cannot be
expressed within it, that's a finding for the main session, not a local workaround.
