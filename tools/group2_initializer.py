"""Bounded, purity-aware warm-start construction for the Group 2 MILP.

The auxiliary model is the original model plus one binary selector for every
``(state, pure bundle)`` pair.  A selector equals the sum of that state's
shares in the bundle.  With Group 2's conditional-purity rows this is a
redundant, but useful, explicit branching representation: a state is either
entirely assigned to its pure channel or is not assigned to it at all.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import numpy as np
from scipy import sparse
from scipy.optimize import Bounds, LinearConstraint, milp

from td.solvers import level0


DEFAULT_BUNDLES = ("N", "WH", "FI")


@dataclass(frozen=True)
class Group2InitializerResult:
    """A validated original-model vector, or a reason no seed is available."""

    status: str
    vector: np.ndarray | None
    metadata: dict[str, object]

    @property
    def warm_start(self) -> np.ndarray | None:
        """Alias for callers that pass this directly to ``solve_passes``."""
        return self.vector


def _selected_bundles(problem: level0.Level0Problem,
                      bundles: Iterable[str]) -> tuple[str, ...]:
    requested = tuple(bundles)
    # Small test and scenario models may not carry every Group 2 pure bundle.
    # The real adapter supplies all three, while omission is a clean no-op here.
    return tuple(bundle for bundle in requested if bundle in problem.slots
                 and problem.slots[bundle][0] < problem.slots[bundle][1])


def _coverage_objective(problem: level0.Level0Problem, passes: Iterable[level0.Pass]) -> np.ndarray | None:
    """Use the first real coverage pass, never a feasibility objective."""
    y_lo = problem.off_y
    y_hi = y_lo + problem.n_state * problem.k
    for passed in passes:
        c = np.asarray(passed.c, float)
        if c.shape != (problem.n_var,) or not np.any(c[y_lo:y_hi]):
            continue
        # Group 2's priority and cover passes cost only y.  Refuse an unrelated
        # objective rather than silently turn this into a feasibility solve.
        if np.any(c[:y_lo]) or np.any(c[y_hi:]):
            continue
        return -c if passed.sense == "max" else c.copy()
    return None


def _auxiliary(problem: level0.Level0Problem, bundles: tuple[str, ...], base_objective: np.ndarray
               ) -> tuple[np.ndarray, np.ndarray, np.ndarray, LinearConstraint, list[tuple[int, str]]]:
    """Return the purity-selector extension with the stage's coverage objective."""
    selectors = [(s, bundle) for s in range(problem.n_state) for bundle in bundles]
    n_selector = len(selectors)
    n_total = problem.n_var + n_selector
    objective = np.concatenate((base_objective, np.zeros(n_selector)))
    if not np.any(objective):
        raise ValueError("coverage pass has a zero objective")

    original = sparse.hstack((problem.A, sparse.csc_matrix((problem.A.shape[0], n_selector))),
                             format="csc")
    rr: list[int] = []
    cc: list[int] = []
    vv: list[float] = []
    for row, (state, bundle) in enumerate(selectors):
        lo, hi = problem.slots[bundle]
        cols = problem.off_y + state * problem.k + np.arange(lo, hi)
        rr.extend([row] * (len(cols) + 1))
        cc.extend(cols.tolist() + [problem.n_var + row])
        vv.extend([1.0] * len(cols) + [-1.0])
    selector_rows = sparse.coo_matrix((vv, (rr, cc)), shape=(n_selector, n_total)).tocsc()
    matrix = sparse.vstack((original, selector_rows), format="csc")
    lower = np.concatenate((problem.lb, np.zeros(n_selector)))
    upper = np.concatenate((problem.ub, np.zeros(n_selector)))
    var_lb = np.concatenate((problem.var_lb, np.zeros(n_selector)))
    var_ub = np.concatenate((problem.var_ub, np.ones(n_selector)))
    integrality = np.concatenate((problem.integrality, np.ones(n_selector)))
    return objective, var_lb, var_ub, LinearConstraint(matrix, lower, upper), selectors


def build_group2_warm_start(problem: level0.Level0Problem, passes: Iterable[level0.Pass], *,
                            time_limit: float = 15.0, threads: int = 2,
                            bundles: Iterable[str] = DEFAULT_BUNDLES) -> Group2InitializerResult:
    """Build one bounded, validated warm start without changing the real model.

    ``problem`` must already carry Group 2's count and conditional-purity
    constraints.  ``passes`` supplies the first nonzero coverage objective,
    normally the Group 2 priority pass. A timeout may still yield a valid
    incumbent; only such an incumbent is returned. The result makes no
    optimality claim. ``threads`` is recorded for the caller's run metadata;
    scipy's bounded auxiliary MILP does not expose a thread setting.
    """
    selected = _selected_bundles(problem, bundles)
    base = dict(bundles=list(selected), time_limit=float(time_limit), threads=int(threads),
                n_var=problem.n_var)
    if time_limit <= 0.0:
        return Group2InitializerResult("disabled", None, base)
    if not selected:
        return Group2InitializerResult("no_seed", None, dict(base, reason="no_slots"))
    try:
        objective = _coverage_objective(problem, passes)
        if objective is None:
            raise ValueError("no nonzero y-only coverage pass")
        c, lb, ub, constraints, selectors = _auxiliary(problem, selected, objective)
    except ValueError as exc:
        return Group2InitializerResult("no_seed", None, dict(base, reason=str(exc)))
    try:
        result = milp(c, integrality=np.concatenate((problem.integrality, np.ones(len(selectors)))),
                      bounds=Bounds(lb, ub), constraints=constraints,
                      options={"time_limit": float(time_limit), "mip_rel_gap": 0.0})
    except Exception as exc:  # A warm start is optional, including solver setup failures.
        return Group2InitializerResult("no_seed", None,
                                       dict(base, reason="solver_error", error=type(exc).__name__))
    meta = dict(base, solver_status=int(result.status), solver_message=str(result.message),
                selector_count=len(selectors))
    if result.x is None:
        return Group2InitializerResult("no_seed", None, dict(meta, reason="no_incumbent"))
    vector = np.asarray(result.x[:problem.n_var], float)
    try:
        level0.check_point(problem, vector)
    except ValueError as exc:
        return Group2InitializerResult("no_seed", None,
                                       dict(meta, reason="validation_failed", error=str(exc)))
    chosen = [[problem.state_list[s] if s < len(problem.state_list) else str(s), bundle]
              for i, (s, bundle) in enumerate(selectors) if result.x[problem.n_var + i] > 0.5]
    return Group2InitializerResult("seed", vector,
                                   dict(meta, coverage=float(-c @ result.x), selected=chosen,
                                        certified=bool(result.status == 0)))
