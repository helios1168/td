"""tools/exp81/hess.py: #81's Hess-style ZIP planner on toys.

The toy is three units on a line, AL - AR - AZ, AL and AZ whole and AR free, eight unit-mass ZIPs 1 km
apart and K = 2, so each district must hold exactly 4: AL with two of AR's ZIPs, AZ with the
other two.  The loop must end at a fixed point whose assignment is the best one at its own centres,
which brute force over every item assignment confirms.
"""
from __future__ import annotations

import itertools
import math
import os
import sys

from tests import test_master as tm

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                "tools", "exp81"))
import hess  # noqa: E402

ZIPS = {"AL": ["a1", "a2"], "AR": ["b1", "b2", "b3", "b4"], "AZ": ["c1", "c2"]}
ORDER = ["a1", "a2", "b1", "b2", "b3", "b4", "c1", "c2"]


def _line(**channel):
    xy = {z: (float(i), 0.0) for i, z in enumerate(ORDER)}
    edges = list(zip(ORDER, ORDER[1:]))
    inst = tm._toy(ZIPS, edges, dict.fromkeys(ORDER, 1.0), xy, {"AR": "free"}, k=2, **channel)
    return inst, xy


def test_a_whole_items_cost_is_the_sum_of_its_zips_costs():
    inst, p = _line()
    its = hess.items(inst, "X", p)
    assert [it.unit for it in its] == ["AL", "AZ", "AR", "AR", "AR", "AR"]
    for it in its:
        for c in ((0.0, 0.0), (3.5, 2.0)):
            direct = math.fsum(inst.channels["X"].m[z] * ((p[z][0] - c[0]) ** 2 + (p[z][1] - c[1]) ** 2)
                               for z in it.zips)
            assert abs(hess.cost(it, c) - direct) < 1e-9


def test_separators_cut_off_a_disconnected_unit_set():
    inst, _ = _line()
    seps = hess.separators(inst, "X", [{"AL", "AZ"}, {"AR"}])
    assert seps == [("AL", "AZ", frozenset({"AR"})), ("AZ", "AL", frozenset({"AR"}))]


def test_the_loop_ends_at_an_assignment_optimal_at_its_own_centres():
    old = hess.THREADS
    hess.THREADS = None             # the test process's other HiGHS solves set no thread count
    try:
        inst, p = _line()
        ch = inst.channels["X"]
        res, m = hess.plan(inst, "X", p, ch.band, max_iters=10, time_limit=60, total_limit=120,
                           log=lambda msg: None)
    finally:
        hess.THREADS = old
    assert res.stop == "assignment repeats"
    held = {}
    for it, j in zip(m.items, res.assign):
        held.setdefault(j, []).extend(it.zips)
    assert sorted(sorted(zs) for zs in held.values()) == [["a1", "a2", "b1", "b2"],
                                                          ["b3", "b4", "c1", "c2"]]
    best = math.inf
    for combo in itertools.product(range(m.k), repeat=len(m.items)):
        mass = [math.fsum(it.mass for it, j in zip(m.items, combo) if j == d) for d in range(m.k)]
        sets = hess.unit_sets(m, list(combo))
        if all(ch.band[0] <= x <= ch.band[1] for x in mass) and not hess.separators(inst, "X", sets):
            best = min(best, hess.hess_objective(m, list(combo), res.centres))
    assert abs(res.objective - best) <= 1e-9 * max(1.0, best)
    assert all(st["status"] == "optimal" for it in res.iterations[1:] for st in it["steps"])
