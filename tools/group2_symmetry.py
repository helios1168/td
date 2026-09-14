"""Safe symmetry reduction for the Group 2 national-stage model.

Level 0 already orders otherwise interchangeable slots by nonincreasing mass.
Ordering those same slots independently by root index is not valid: the heavier
district can have a larger root index.  This module instead removes the
single-commodity-flow root symmetry within each district.  A used slot is
rooted at its lowest-index contacted state.  Every connected contact set admits
that root, so the projected feasible set in ``(z, y, u)`` is unchanged.
"""
from __future__ import annotations

import dataclasses

import numpy as np
from scipy import sparse

from td.solvers import level0


_FLOW_ROW_NAMES = ("root", "rz", "flow_tail", "flow_head", "net")


def _validate_free_roots(problem: level0.Level0Problem, slots: range) -> None:
    """Refuse models where roots or flows have acquired extra semantics."""
    matrix = problem.A
    if matrix is None:
        raise ValueError("slot symmetry needs an explicit constraint matrix")
    matrix_shape = matrix.shape
    assert matrix_shape is not None
    S, K = problem.n_state, problem.k
    root_cols = np.concatenate([
        problem.off_r + np.arange(S) * K + j for j in slots
    ])
    if (np.any(problem.var_lb[root_cols] != 0.0)
            or np.any(problem.var_ub[root_cols] != 1.0)):
        raise ValueError("slot symmetry needs unfixed binary root variables")
    if np.any(problem.integrality[root_cols] != 1.0):
        raise ValueError("slot symmetry needs binary root variables")
    if np.any(problem.c[root_cols] != 0.0):
        raise ValueError("slot symmetry cannot change an objective that prices roots")
    if any(problem.slot_root[j] >= 0 for j in slots):
        raise ValueError("slot symmetry cannot canonicalize an anchored root")

    flow_cols = np.concatenate([
        problem.off_f + np.arange((problem.off_u - problem.off_f) // K) * K + j
        for j in slots
    ])
    if np.any(problem.c[flow_cols] != 0.0):
        raise ValueError("slot symmetry cannot change an objective that prices flow")

    allowed_rows = np.zeros(matrix_shape[0], bool)
    for name in _FLOW_ROW_NAMES:
        if name not in problem.rows:
            raise ValueError(f"slot symmetry needs the level-0 {name!r} row block")
        lo, hi = problem.rows[name]
        allowed_rows[lo:hi] = True
    touched = np.unique(matrix[:, np.concatenate((root_cols, flow_cols))].tocoo().row)
    if np.any(~allowed_rows[touched]):
        raise ValueError("slot symmetry found an unexpected constraint on roots or flows")


def canonicalize_slot_symmetry(
    problem: level0.Level0Problem,
    bundle: str = "N",
) -> level0.Level0Problem:
    """Return ``problem`` with each bundle slot rooted at its first contact.

    For every state ``s`` and selected slot ``j`` the added inequality is

    ``z[s,j] <= sum(r[t,j] for t <= s)``.

    The existing ``r <= z`` and one-root rows then make the root exactly the
    lowest-index contacted state.  This changes only the representation of a
    connected district, never its contacts, shares, use, opportunity, purity,
    geography, or count.  In particular, it composes with level 0's existing
    nonincreasing-mass slot ordering instead of imposing a conflicting second
    ordering on district labels.

    The helper deliberately refuses anchored roots, priced roots or flows, and
    unexpected custom constraints on those variable blocks.  Reapplying it is
    an idempotent no-op.
    """
    if bundle not in problem.slots:
        raise ValueError(f"unknown bundle {bundle!r}; expected one of {list(problem.slots)}")
    row_name = f"root_min_{bundle}"
    if row_name in problem.rows:
        return problem
    start, stop = problem.slots[bundle]
    if start == stop or problem.n_state <= 1:
        return problem
    slots = range(start, stop)
    _validate_free_roots(problem, slots)
    matrix = problem.A
    assert matrix is not None
    matrix_shape = matrix.shape
    assert matrix_shape is not None

    S, K = problem.n_state, problem.k
    n_rows = (S - 1) * (stop - start)
    rr: list[int] = []
    cc: list[int] = []
    vv: list[float] = []
    row = 0
    for j in slots:
        for s in range(S - 1):
            rr.extend([row] * (s + 2))
            cc.append(problem.off_z + s * K + j)
            cc.extend(problem.off_r + t * K + j for t in range(s + 1))
            vv.append(1.0)
            vv.extend([-1.0] * (s + 1))
            row += 1
    block = sparse.coo_matrix((vv, (rr, cc)), shape=(n_rows, problem.n_var)).tocsc()
    first = matrix_shape[0]
    rows = dict(problem.rows)
    rows[row_name] = (first, first + n_rows)
    return dataclasses.replace(
        problem,
        A=sparse.vstack((matrix, block), format="csc"),
        lb=np.concatenate((problem.lb, np.full(n_rows, -np.inf))),
        ub=np.concatenate((problem.ub, np.zeros(n_rows))),
        rows=rows,
    )
