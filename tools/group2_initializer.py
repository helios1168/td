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

from td.solvers import level0


DEFAULT_BUNDLES = ("N", "WH", "FI")
_NATIONAL_ANCHOR_PATTERNS = (
    ("CA", "CA", "CA", "TX", "TX", "NY", "NY", "FL", "NJ", "AZ", "IL", "MI", "GA", "VA"),
    ("CA", "CA", "CA", "TX", "TX", "NY", "NY", "FL", "NJ", "AZ", "IL", "NC", "OH", "MD"),
)


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
               ) -> tuple[np.ndarray, np.ndarray, np.ndarray, sparse.csc_matrix, np.ndarray,
                          np.ndarray, list[tuple[int, str]]]:
    """Return the purity-selector extension with the stage's coverage objective."""
    selectors = [(s, bundle) for s in range(problem.n_state) for bundle in bundles]
    n_selector = len(selectors)
    n_total = problem.n_var + n_selector
    objective = np.concatenate((base_objective, np.zeros(n_selector)))
    if not np.any(objective):
        raise ValueError("coverage pass has a zero objective")

    assert problem.A is not None
    original = sparse.hstack((problem.A, sparse.csc_matrix((len(problem.lb), n_selector))),
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
    assert isinstance(matrix, sparse.csc_matrix)
    row_lower = np.concatenate((problem.lb, np.zeros(n_selector)))
    row_upper = np.concatenate((problem.ub, np.zeros(n_selector)))
    var_lb = np.concatenate((problem.var_lb, np.zeros(n_selector)))
    var_ub = np.concatenate((problem.var_ub, np.ones(n_selector)))
    integrality = np.concatenate((problem.integrality, np.ones(n_selector)))
    return objective, var_lb, var_ub, matrix, row_lower, row_upper, selectors


def _solve_auxiliary(c: np.ndarray, var_lb: np.ndarray, var_ub: np.ndarray,
                     matrix: sparse.csc_matrix, row_lb: np.ndarray, row_ub: np.ndarray,
                     integrality: np.ndarray, *, time_limit: float, threads: int,
                     mip_rel_gap: float = 0.0, heuristic_effort: float | None = None,
                     ) -> tuple[np.ndarray | None, int, str]:
    """Solve directly with highspy, isolated from scipy's separate HiGHS pool."""
    import highspy

    lp = highspy.HighsLp()
    lp.num_col_ = len(c)
    lp.num_row_ = len(row_lb)
    lp.col_cost_ = c.tolist()
    lp.col_lower_ = var_lb.tolist()
    lp.col_upper_ = var_ub.tolist()
    lp.row_lower_ = row_lb.tolist()
    lp.row_upper_ = row_ub.tolist()
    lp.integrality_ = [highspy.HighsVarType.kInteger if integer else highspy.HighsVarType.kContinuous
                       for integer in integrality]
    data = matrix.tocsc()
    coefficients = highspy.HighsSparseMatrix()
    coefficients.format_ = highspy.MatrixFormat.kColwise
    coefficients.start_ = data.indptr.tolist()
    coefficients.index_ = data.indices.tolist()
    coefficients.value_ = data.data.tolist()
    lp.a_matrix_ = coefficients
    lp.sense_ = highspy.ObjSense.kMinimize
    highs = highspy.Highs()
    highs.setOptionValue("output_flag", False)
    highs.setOptionValue("mip_rel_gap", mip_rel_gap)
    highs.setOptionValue("time_limit", time_limit)
    highs.setOptionValue("threads", threads)
    if heuristic_effort is not None:
        highs.setOptionValue("mip_heuristic_effort", heuristic_effort)
    if highs.passModel(lp) == highspy.HighsStatus.kError:
        return None, -1, "HiGHS rejected the auxiliary model"
    highs.run()
    model_status = highs.getModelStatus()
    message = highs.modelStatusToString(model_status)
    info = highs.getInfo()
    if info.primal_solution_status != highspy.kSolutionStatusFeasible:
        return None, int(model_status), message
    return np.asarray(highs.getSolution().col_value, float), int(model_status), message


def _exact_national_count(problem: level0.Level0Problem) -> int | None:
    """Read the exact N count from its fixed slot bounds, if this is an N stage."""
    if "N" not in problem.slots:
        return None
    lo, hi = problem.slots["N"]
    lower = problem.var_lb[problem.off_u + lo:problem.off_u + hi]
    upper = problem.var_ub[problem.off_u + lo:problem.off_u + hi]
    fixed = lower >= 1.0 - 1e-9
    closed = upper <= 1e-9
    if not fixed.any() or not np.all(fixed | closed):
        return None
    return int(fixed.sum())


def _validated_vector(problem: level0.Level0Problem, x_aux: np.ndarray | None,
                      exact_national: int | None) -> tuple[np.ndarray | None, str | None]:
    """Strip selectors and check the untouched original model and exact N count."""
    if x_aux is None:
        return None, "no_incumbent"
    vector = np.asarray(x_aux[:problem.n_var], float)
    if not np.isfinite(vector).all():
        return None, "nonfinite_vector"
    integer_values = vector[np.asarray(problem.integrality, bool)]
    if not np.all(np.abs(integer_values - np.rint(integer_values)) <= 1e-6):
        return None, "fractional_integer"
    if exact_national is not None:
        lo, hi = problem.slots["N"]
        used = vector[problem.off_u + lo:problem.off_u + hi]
        if int(np.rint(used.sum())) != exact_national:
            return None, "national_count_mismatch"
    try:
        level0.check_point(problem, vector)
    except ValueError as exc:
        return None, f"validation_failed:{exc}"
    return vector, None


def _anchor_patterns(problem: level0.Level0Problem,
                     exact_national: int | None) -> tuple[tuple[int, ...], ...]:
    """Resolve scenario seed contacts without making them production requirements."""
    if exact_national != 14:
        return ()
    index = {state: s for s, state in enumerate(problem.state_list)}
    if not all(state in index for pattern in _NATIONAL_ANCHOR_PATTERNS for state in pattern):
        return ()
    return tuple(tuple(index[state] for state in pattern)
                 for pattern in _NATIONAL_ANCHOR_PATTERNS)


def build_group2_warm_start(problem: level0.Level0Problem, passes: Iterable[level0.Pass], *,
                            time_limit: float = 15.0, threads: int = 2,
                            bundles: Iterable[str] = DEFAULT_BUNDLES) -> Group2InitializerResult:
    """Build one bounded, validated warm start without changing the real model.

    ``problem`` must already carry Group 2's count and conditional-purity
    constraints.  ``passes`` supplies the first nonzero coverage objective,
    normally the Group 2 priority pass. A timeout may still yield a valid
    incumbent; only such an incumbent is returned. The result makes no
    optimality claim. The direct highspy auxiliary solve uses ``threads``, the
    same count as the following production solve, so it does not ask its
    process-global thread pool to resize between the two solves.
    """
    try:
        seconds = float(time_limit)
    except (TypeError, ValueError):
        return Group2InitializerResult("no_seed", None,
                                       dict(reason="invalid_time_limit", time_limit=repr(time_limit)))
    if not np.isfinite(seconds) or seconds < 0.0:
        return Group2InitializerResult("no_seed", None,
                                       dict(reason="invalid_time_limit", time_limit=repr(time_limit)))
    if isinstance(threads, bool) or not isinstance(threads, (int, np.integer)) or threads <= 0:
        return Group2InitializerResult("no_seed", None,
                                       dict(reason="invalid_threads", threads=repr(threads)))
    selected = _selected_bundles(problem, bundles)
    base: dict[str, object] = dict(bundles=list(selected), time_limit=seconds,
                                   threads=int(threads), n_var=problem.n_var)
    if seconds == 0.0:
        return Group2InitializerResult("disabled", None, base)
    if not selected:
        return Group2InitializerResult("no_seed", None, dict(base, reason="no_slots"))
    try:
        objective = _coverage_objective(problem, passes)
        if objective is None:
            raise ValueError("no nonzero y-only coverage pass")
        c, lb, ub, matrix, row_lb, row_ub, selectors = _auxiliary(problem, selected, objective)
    except ValueError as exc:
        return Group2InitializerResult("no_seed", None, dict(base, reason=str(exc)))
    exact_national = _exact_national_count(problem)
    greedy_failure: str | None = None
    # This is the cheapest deterministic route to an incumbent.  It is still
    # checked against the original constrained model, because the legacy
    # greedy can fail conditional purity on a partial state.
    try:
        greedy, greedy_seeds = level0.greedy_plan(problem, priority=selected)
        vector, invalid_reason = _validated_vector(problem, greedy, exact_national)
        if vector is not None:
            seed_rows = [[problem.state_list[state] if state < len(problem.state_list) else str(state),
                          slot]
                         for bundle in selected for state, slot in greedy_seeds.get(bundle, [])]
            return Group2InitializerResult("seed", vector,
                                           dict(base, status="greedy_feasible", solver_status=None,
                                                solver_message="validated deterministic greedy point",
                                                selector_count=len(selectors), phase="greedy_feasible",
                                                national_exact_count=exact_national,
                                                coverage=float(-c[:problem.n_var] @ vector),
                                                selected=seed_rows, auxiliary_optimal=False))
    except ValueError as exc:
        # An invalid greedy point is expected on some pure-state configurations;
        # continue to the selector MILP without exposing it as a warm start.
        greedy_failure = str(exc)
    try:
        # Try two geographically distributed contact patterns before the free
        # auxiliary search.  They exist only in the seed model: a validated
        # point is handed to the original planner, whose bounds remain free.
        anchor_patterns = _anchor_patterns(problem, exact_national)
        anchor_total = min(seconds * 0.25, 20.0) if anchor_patterns else 0.0
        anchor_seconds = anchor_total / len(anchor_patterns) if anchor_patterns else 0.0
        n_lo = problem.slots.get("N", (0, 0))[0]
        for pattern_index, pattern in enumerate(anchor_patterns, start=1):
            anchored_lb = lb.copy()
            for offset, state in enumerate(pattern):
                anchored_lb[problem.off_z + state * problem.k + n_lo + offset] = 1.0
            x_aux, solver_status, solver_message = _solve_auxiliary(
                c, anchored_lb, ub, matrix, row_lb, row_ub,
                np.concatenate((problem.integrality, np.ones(len(selectors)))),
                time_limit=anchor_seconds, threads=int(threads), mip_rel_gap=1.0,
                heuristic_effort=1.0)
            vector, invalid_reason = _validated_vector(problem, x_aux, exact_national)
            if vector is not None:
                assert x_aux is not None
                chosen = [[problem.state_list[s], bundle]
                          for i, (s, bundle) in enumerate(selectors)
                          if x_aux[problem.n_var + i] > 0.5]
                return Group2InitializerResult(
                    "seed", vector,
                    dict(base, status=solver_status, solver_status=solver_status,
                         solver_message=solver_message, selector_count=len(selectors),
                         phase="anchored_national_feasibility", pattern=pattern_index,
                         anchors=[problem.state_list[s] for s in pattern],
                         national_exact_count=exact_national, greedy_failure=greedy_failure,
                         coverage=float(-c @ x_aux), selected=chosen,
                         auxiliary_optimal=solver_status == 7))
        # The national stage gets a bounded incumbent-first attempt.  It retains
        # the real coverage objective, every count, purity and geometry row, but
        # lets HiGHS stop as soon as its first useful incumbent closes the wide
        # initial gap.  That seed is preferable to spending the whole budget on
        # optimality before the production solver has any start at all.
        feasibility_seconds = min(max(0.0, seconds - anchor_total), 5.0) if exact_national is not None else 0.0
        x_aux = None
        solver_status = -1
        solver_message = ""
        phase = "coverage"
        if feasibility_seconds > 0.0:
            x_aux, solver_status, solver_message = _solve_auxiliary(
                c, lb, ub, matrix, row_lb, row_ub,
                np.concatenate((problem.integrality, np.ones(len(selectors)))),
                time_limit=feasibility_seconds, threads=int(threads), mip_rel_gap=1.0,
                heuristic_effort=1.0)
            vector, invalid_reason = _validated_vector(problem, x_aux, exact_national)
            if vector is not None:
                assert x_aux is not None
                meta = dict(base, status=solver_status, solver_status=solver_status,
                            solver_message=solver_message, selector_count=len(selectors),
                            phase="national_feasibility", national_exact_count=exact_national,
                            greedy_failure=greedy_failure)
                chosen = [[problem.state_list[s] if s < len(problem.state_list) else str(s), bundle]
                          for i, (s, bundle) in enumerate(selectors)
                          if x_aux[problem.n_var + i] > 0.5]
                return Group2InitializerResult("seed", vector,
                                               dict(meta, coverage=float(-c @ x_aux), selected=chosen,
                                                    auxiliary_optimal=solver_status == 7))
            phase = "coverage_after_national_feasibility"
        remaining = max(0.01, seconds - anchor_total - feasibility_seconds)
        x_aux, solver_status, solver_message = _solve_auxiliary(
            c, lb, ub, matrix, row_lb, row_ub,
            np.concatenate((problem.integrality, np.ones(len(selectors)))),
            time_limit=remaining, threads=int(threads))
    except Exception as exc:  # A warm start is optional, including solver setup failures.
        return Group2InitializerResult("no_seed", None,
                                       dict(base, reason="solver_error", error=type(exc).__name__))
    meta = dict(base, status=solver_status, solver_status=solver_status, phase=phase,
                solver_message=solver_message,
                selector_count=len(selectors), national_exact_count=exact_national,
                greedy_failure=greedy_failure)
    vector, invalid_reason = _validated_vector(problem, x_aux, exact_national)
    if vector is None:
        return Group2InitializerResult("no_seed", None, dict(meta, reason=invalid_reason))
    assert x_aux is not None
    chosen = [[problem.state_list[s] if s < len(problem.state_list) else str(s), bundle]
              for i, (s, bundle) in enumerate(selectors) if x_aux[problem.n_var + i] > 0.5]
    return Group2InitializerResult("seed", vector,
                                   dict(meta, coverage=float(-c @ x_aux), selected=chosen,
                                        auxiliary_optimal=solver_status == 7))


def build_group2_feasibility_start(problem: level0.Level0Problem, passes: Iterable[level0.Pass], *,
                                   time_limit: float = 15.0, threads: int = 2,
                                   bundles: Iterable[str] = DEFAULT_BUNDLES
                                   ) -> Group2InitializerResult:
    """Public feasibility-first name for the Group 2 warm-start builder."""
    return build_group2_warm_start(problem, passes, time_limit=time_limit,
                                   threads=threads, bundles=bundles)
