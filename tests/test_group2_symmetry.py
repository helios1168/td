"""Focused checks for Group 2's safe root symmetry reduction."""
from types import SimpleNamespace

import numpy as np

from td.solvers import level0
from tools.group2_symmetry import canonicalize_slot_symmetry


def _problem(states: int, slots: int = 1, *, anchors=None) -> level0.Level0Problem:
    cells = SimpleNamespace(
        M=np.ones((states, 1)),
        channels=("N_WH",),
        state_list=[f"S{s}" for s in range(states)],
    )
    return level0.build_level0(
        cells,
        {"N": ("N_WH",)},
        edges=[(s, s + 1) for s in range(states - 1)],
        L=0.5,
        U=float(states),
        eta=0.05,
        anchors=anchors,
        fixed_used={"N": slots},
        max_used={"N": slots},
    )


def _point(
    problem: level0.Level0Problem,
    contacts: list[set[int]],
    roots: list[int],
) -> np.ndarray:
    """Build SCF witnesses for connected intervals in the path test graph."""
    S, K = problem.n_state, problem.k
    x = np.zeros(problem.n_var)
    arc_of = {(a, b): 2 * edge + direction
              for edge, (u, v) in enumerate(problem.edges)
              for direction, (a, b) in enumerate(((u, v), (v, u)))}
    for j, (chosen, root) in enumerate(zip(contacts, roots)):
        if not chosen:
            continue
        x[problem.off_u + j] = 1.0
        for s in chosen:
            x[problem.off_z + s * K + j] = 1.0
            x[problem.off_y + s * K + j] = 1.0
        x[problem.off_r + root * K + j] = 1.0

        # A path interval has one unique route from the root.  Flow on an arc
        # is the size of the child-side subtree, matching level 0's SCF rows.
        for s in sorted(chosen):
            if s == root:
                continue
            parent = s + 1 if s < root else s - 1
            descendants = ({t for t in chosen if t <= s} if s < root
                           else {t for t in chosen if t >= s})
            arc = arc_of[(parent, s)]
            x[problem.off_f + arc * K + j] = float(len(descendants))
    return x


def test_every_connected_contact_set_has_a_canonical_equivalent() -> None:
    problem = _problem(4)
    reduced = canonicalize_slot_symmetry(problem)
    assert problem.A is not None and reduced.A is not None
    before_shape = problem.A.shape
    reduced_shape = reduced.A.shape
    assert before_shape is not None and reduced_shape is not None
    before_rows = before_shape[0]
    assert reduced_shape[0] == before_rows + 3
    assert before_shape[0] == before_rows
    assert (reduced.A[:before_rows] != problem.A).nnz == 0
    assert np.array_equal(reduced.lb[:before_rows], problem.lb)
    assert np.array_equal(reduced.ub[:before_rows], problem.ub)
    assert np.array_equal(reduced.var_lb, problem.var_lb)
    assert np.array_equal(reduced.var_ub, problem.var_ub)

    for lo in range(4):
        for hi in range(lo, 4):
            chosen = set(range(lo, hi + 1))
            old = _point(problem, [chosen], [hi])
            canonical = _point(problem, [chosen], [lo])
            level0.check_point(problem, old)
            level0.check_point(reduced, canonical)
            if hi > lo:
                try:
                    level0.check_point(reduced, old)
                except ValueError as exc:
                    assert "root_min_N" in str(exc)
                else:
                    raise AssertionError("a nonminimum root survived canonicalization")


def test_root_canonicalization_composes_with_mass_ordering() -> None:
    problem = _problem(3, slots=2)
    assert "order_mass" in problem.rows
    reduced = canonicalize_slot_symmetry(problem)

    # The heavier first slot has minimum root 1, while the lighter second slot
    # has minimum root 0.  An independent inter-slot root ordering would cut
    # this map, but within-slot root canonicalization correctly keeps it.
    point = _point(problem, [{1, 2}, {0}], [1, 0])
    level0.check_point(problem, point)
    level0.check_point(reduced, point)


def test_refuses_anchored_roots_and_is_idempotent() -> None:
    anchored = _problem(3, anchors=[(1, 0)])
    try:
        canonicalize_slot_symmetry(anchored)
    except ValueError as exc:
        assert "anchored root" in str(exc)
    else:
        raise AssertionError("anchored root was silently canonicalized")

    reduced = canonicalize_slot_symmetry(_problem(3))
    assert canonicalize_slot_symmetry(reduced) is reduced
